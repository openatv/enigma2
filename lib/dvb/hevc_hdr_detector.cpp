/* SPDX-License-Identifier: GPL-2.0-only */

#include <lib/base/eerror.h>
#include <lib/dvb/hevc_hdr_detector.h>

/*
 * Keep completion outside eDVBPESReader::data().  Stopping the reader from a
 * deferred timer avoids changing notifier/filter lifetime while its read
 * callback is still on the stack.
 */
eHEVCHDRDetector::eHEVCHDRDetector(eDVBDemux *demux, const sigc::slot<void(int)> &result_slot)
	: m_demux(demux),
	  m_timer(eTimer::create(eApp)),
	  m_result_slot(result_slot),
	  m_running(false),
	  m_pending_gamma(eHEVCHDRParser::GammaUnknown),
	  m_bytes_received(0)
{
	CONNECT(m_timer->timeout, eHEVCHDRDetector::timerExpired);
}

eHEVCHDRDetector::~eHEVCHDRDetector()
{
	stop();
	m_read_connection = 0;
	m_reader = 0;
}

bool eHEVCHDRDetector::start(int pid)
{
	stop();
	if (!m_demux || pid <= 0 || pid >= 0x2000)
		return false;

	if (!m_reader)
	{
		if (m_demux->createPESReader(eApp, m_reader) || !m_reader)
		{
			eWarning("[eHEVCHDRDetector] unable to create PES/ES reader");
			return false;
		}
		m_reader->connectRead(sigc::mem_fun(*this, &eHEVCHDRDetector::data), m_read_connection);
	}

	m_pes_parser.reset();
	m_es_parser.reset();
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;
	m_bytes_received = 0;
	const int result = m_reader->start(pid);
	if (result)
	{
		eWarning("[eHEVCHDRDetector] unable to tap HEVC video PID %04x (error %d)", pid, result);
		/* start() enables the notifier before DMX_SET_PES_FILTER.  Drop the
		 * failed reader so its fd/notifier cannot remain armed. */
		m_read_connection = 0;
		m_reader = 0;
		return false;
	}

	m_running = true;
	m_timer->start(ScanTimeoutMs, true);
	eDebug("[eHEVCHDRDetector] scanning HEVC video PID %04x for up to %d ms", pid, ScanTimeoutMs);
	return true;
}

void eHEVCHDRDetector::stop()
{
	if (m_timer)
		m_timer->stop();
	if (m_reader)
		m_reader->stop();
	m_running = false;
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;
	m_bytes_received = 0;
}

int eHEVCHDRDetector::selectGamma(int pes_gamma, int es_gamma, bool final)
{
	/* HLG wins a conflict with mastering-display SEI.  HLG services may carry
	 * mastering metadata in addition to transfer_characteristics 18. */
	if (pes_gamma == eHEVCHDRParser::GammaHLG || es_gamma == eHEVCHDRParser::GammaHLG)
		return eHEVCHDRParser::GammaHLG;
	if (pes_gamma == eHEVCHDRParser::GammaHDR10 || es_gamma == eHEVCHDRParser::GammaHDR10)
		return eHEVCHDRParser::GammaHDR10;
	if (final && (pes_gamma == eHEVCHDRParser::GammaSDR || es_gamma == eHEVCHDRParser::GammaSDR))
		return eHEVCHDRParser::GammaSDR;
	return eHEVCHDRParser::GammaUnknown;
}

void eHEVCHDRDetector::data(const uint8_t *buffer, int length)
{
	if (!m_running || !buffer || length <= 0)
		return;

	m_bytes_received += static_cast<size_t>(length);

	/* Parse both common Vu+ tap formats.  Feeding ES bytes to the PES parser is
	 * harmless (it waits for a PES start code); feeding complete PES packets to
	 * the Annex-B parser can still find NALs when packet boundaries happen not
	 * to split them.  The first conclusive HDR result ends the scan. */
	const int pes_gamma = m_pes_parser.feedPES(buffer, static_cast<size_t>(length));
	const int es_gamma = m_es_parser.feed(buffer, static_cast<size_t>(length));
	const int gamma = selectGamma(pes_gamma, es_gamma, false);
	if (gamma != eHEVCHDRParser::GammaUnknown)
		scheduleResult(gamma);
}

void eHEVCHDRDetector::scheduleResult(int gamma)
{
	if (!m_running || gamma == eHEVCHDRParser::GammaUnknown)
		return;
	m_pending_gamma = gamma;
	m_running = false;
	m_timer->start(DeferredResultMs, true);
}

void eHEVCHDRDetector::timerExpired()
{
	int pes_gamma = m_pes_parser.finishPES();
	int es_gamma = m_es_parser.finish();
	int gamma = m_pending_gamma;
	if (gamma == eHEVCHDRParser::GammaUnknown)
		gamma = selectGamma(pes_gamma, es_gamma, true);

	if (m_reader)
		m_reader->stop();
	m_running = false;
	m_pending_gamma = eHEVCHDRParser::GammaUnknown;

	if (gamma != eHEVCHDRParser::GammaUnknown)
	{
		eDebug("[eHEVCHDRDetector] detected gamma %d (PES=%d, ES=%d, bytes=%zu)",
			gamma, pes_gamma, es_gamma, m_bytes_received);
		m_result_slot(gamma);
	}
	else
	{
		eDebug("[eHEVCHDRDetector] no usable HEVC HDR signalling found (PES SPS=%d, ES SPS=%d, bytes=%zu)",
			m_pes_parser.hasSPS(), m_es_parser.hasSPS(), m_bytes_received);
	}
	m_bytes_received = 0;
}
