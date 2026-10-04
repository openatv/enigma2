/* SPDX-License-Identifier: GPL-2.0-only */

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <linux/dvb/dmx.h>

#include <lib/base/eerror.h>
#include <lib/dvb/hevc_hdr_detector.h>
#include <lib/dvb_ci/dvbci.h>

/*
 * Keep completion outside readData().  Closing the tap from a deferred timer
 * avoids changing notifier/filter lifetime while its read callback is still
 * on the stack.
 */
eHEVCHDRDetector::eHEVCHDRDetector(eDVBDemux *demux, const sigc::slot<void(int)> &result_slot)
	: m_demux(demux),
	  m_timer(eTimer::create(eApp)),
	  m_result_slot(result_slot)
{
	CONNECT(m_timer->timeout, eHEVCHDRDetector::timerExpired);
}

eHEVCHDRDetector::~eHEVCHDRDetector()
{
	stop();
}

bool eHEVCHDRDetector::start(int pid)
{
	stop();
	if (!m_demux || pid <= 0 || pid >= 0x2000)
		return false;

	eDVBCIInterfaces *ci = eDVBCIInterfaces::getInstance();
	if (ci && ci->hasActiveCiRouting())
	{
		eDebug("[eHEVCHDRDetector] scan suppressed for PID %04x "
			"(CI module handles descrambling)", pid);
		return false;
	}

	m_fd = m_demux->openDemux();
	if (m_fd < 0)
	{
		eWarning("[eHEVCHDRDetector] unable to open demux");
		return false;
	}
	::fcntl(m_fd, F_SETFL, O_NONBLOCK);
	if (::ioctl(m_fd, DMX_SET_BUFFER_SIZE, TapBufferSize) < 0)
		eDebug("[eHEVCHDRDetector] DMX_SET_BUFFER_SIZE %d failed: %m", TapBufferSize);

	dmx_pes_filter_params flt = {};
	flt.pid = pid;
	flt.input = DMX_IN_FRONTEND;
	flt.output = DMX_OUT_TSDEMUX_TAP;
	flt.pes_type = DMX_PES_OTHER;
	flt.flags = DMX_IMMEDIATE_START;
	if (::ioctl(m_fd, DMX_SET_PES_FILTER, &flt) < 0)
	{
		eWarning("[eHEVCHDRDetector] unable to tap HEVC video PID %04x: %m", pid);
		::close(m_fd);
		m_fd = -1;
		return false;
	}

	m_parser.reset();
	m_pid = pid;
	m_partial_length = 0;
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;
	m_bytes_received = 0;
	m_notifier = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_notifier->activated, eHEVCHDRDetector::readData);

	m_running = true;
	m_timer->start(ScanTimeoutMs, true);
	eDebug("[eHEVCHDRDetector] scanning HEVC video PID %04x for up to %d ms", pid, ScanTimeoutMs);
	return true;
}

void eHEVCHDRDetector::closeTap()
{
	m_notifier = nullptr;
	if (m_fd >= 0)
	{
		::ioctl(m_fd, DMX_STOP);
		::close(m_fd);
		m_fd = -1;
	}
}

void eHEVCHDRDetector::stop()
{
	if (m_timer)
		m_timer->stop();
	closeTap();
	m_running = false;
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;
	m_bytes_received = 0;
}

int eHEVCHDRDetector::payloadOffset(const uint8_t *packet) const
{
	/* Skip transport errors, scrambled packets and packets without payload. */
	if (packet[0] != 0x47 || (packet[1] & 0x80) || (packet[3] & 0xc0))
		return -1;
	if ((((packet[1] & 0x1f) << 8) | packet[2]) != m_pid)
		return -1;
	const int adaptation_field_control = (packet[3] >> 4) & 3;
	if (!(adaptation_field_control & 1))
		return -1;
	int offset = 4;
	if (adaptation_field_control & 2)
		offset += 1 + packet[4];
	return offset < TSPacketSize ? offset : -1;
}

void eHEVCHDRDetector::readData(int)
{
	std::array<uint8_t, TSPacketSize * 87> buffer;
	std::array<uint8_t, TSPacketSize * 87> payload;

	while (m_running)
	{
		const ssize_t length = ::read(m_fd, buffer.data(), buffer.size());
		if (length < 0)
		{
			if (errno == EOVERFLOW)
			{
				m_partial_length = 0;
				continue;
			}
			if (errno != EAGAIN && errno != EINTR)
				eWarning("[eHEVCHDRDetector] read error on PID %04x: %m", m_pid);
			return;
		}
		if (!length)
			return;

		m_bytes_received += static_cast<size_t>(length);
		size_t payload_length = 0;
		size_t position = 0;

		if (m_partial_length)
		{
			const size_t needed = std::min<size_t>(TSPacketSize - m_partial_length, length);
			memcpy(m_partial.data() + m_partial_length, buffer.data(), needed);
			m_partial_length += needed;
			position = needed;
			if (m_partial_length == TSPacketSize)
			{
				if (const int offset = payloadOffset(m_partial.data()); offset > 0)
				{
					memcpy(payload.data(), m_partial.data() + offset, TSPacketSize - offset);
					payload_length = TSPacketSize - offset;
				}
				m_partial_length = 0;
			}
		}

		while (position + TSPacketSize <= static_cast<size_t>(length))
		{
			if (buffer[position] != 0x47)
			{
				++position;
				continue;
			}
			if (const int offset = payloadOffset(buffer.data() + position); offset > 0)
			{
				memcpy(payload.data() + payload_length, buffer.data() + position + offset, TSPacketSize - offset);
				payload_length += TSPacketSize - offset;
			}
			position += TSPacketSize;
		}

		if (position < static_cast<size_t>(length) && buffer[position] == 0x47)
		{
			m_partial_length = length - position;
			memcpy(m_partial.data(), buffer.data() + position, m_partial_length);
		}

		if (payload_length)
		{
			const int gamma = m_parser.feedPES(payload.data(), payload_length);
			if (gamma != eHEVCHDRParser::GammaUnknown)
			{
				scheduleResult(gamma);
				return;
			}
		}

		if (length != static_cast<ssize_t>(buffer.size()))
			return;
	}
}

void eHEVCHDRDetector::scheduleResult(int gamma)
{
	if (!m_running || gamma == eHEVCHDRParser::GammaUnknown)
		return;
	m_pending_gamma = gamma;
	m_running = false;
	if (m_notifier)
		m_notifier->stop();
	m_timer->start(DeferredResultMs, true);
}

void eHEVCHDRDetector::timerExpired()
{
	int gamma = m_pending_gamma;
	if (gamma == eHEVCHDRParser::GammaUnknown)
		gamma = m_parser.finishPES();

	closeTap();
	m_running = false;
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;

	if (gamma != eHEVCHDRParser::GammaUnknown)
	{
		eDebug("[eHEVCHDRDetector] detected gamma %d (bytes=%zu)", gamma, m_bytes_received);
		m_result_slot(gamma);
	}
	else
	{
		eDebug("[eHEVCHDRDetector] no usable HEVC HDR signalling found (SPS=%d, bytes=%zu)",
			m_parser.hasSPS(), m_bytes_received);
	}
	m_bytes_received = 0;
}
