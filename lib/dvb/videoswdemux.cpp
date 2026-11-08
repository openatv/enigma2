/* SPDX-License-Identifier: GPL-2.0-only */

#include <cerrno>
#include <ctime>
#include <fcntl.h>
#include <poll.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <linux/dvb/dmx.h>
#include <linux/dvb/video.h>

#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/dvb/videoswdemux.h>

/* frame input of the DreamOne/DreamTwo video decoders */
struct video_frame
{
	int64_t pts;
	int64_t size[8];
	const uint8_t *data[8];
	int64_t reserved[4];
};

static_assert(sizeof(video_frame) == 168, "video_frame must match the driver");

/* reserved[0] of a mosaic decoder frame: the PCR of the service (90 kHz) */
#define VIDEO_FRAME_PCR (1ULL << 63)

static int64_t monotonicUs()
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (int64_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
}

#define VIDEO_SET_FRAME _IOWR('o', 64, struct video_frame)

/* the decoder starts the PiP PTS at 0 with the first frame it outputs, which
 * is the first random access point; the PiP pacing needs the stream PTS */
#define PIP_PTS_STREAM_BASE "/sys/module/amvideo/parameters/pip_pts_stream_base"

eDVBVideoSwDemux::eDVBVideoSwDemux(eDVBDemux *demux, int fd_video, int pes_type, bool with_pcr)
	: m_demux(demux), m_fd_video(fd_video), m_pes_type(pes_type), m_with_pcr(with_pcr)
{
}

eDVBVideoSwDemux::~eDVBVideoSwDemux()
{
	stop();
}

int eDVBVideoSwDemux::start(int pid, Codec codec, int pcr_pid)
{
	stop();
	if (!m_demux || m_fd_video < 0 || pid <= 0 || pid >= 0x1FFF)
		return -1;

	m_fd_demux = m_demux->openDemux();
	if (m_fd_demux < 0)
	{
		eWarning("[eDVBVideoSwDemux] unable to open demux");
		return -1;
	}
	::fcntl(m_fd_demux, F_SETFL, O_NONBLOCK);
	if (::ioctl(m_fd_demux, DMX_SET_BUFFER_SIZE, TapBufferSize) < 0)
		eDebug("[eDVBVideoSwDemux] DMX_SET_BUFFER_SIZE %d failed: %m", TapBufferSize);
	dmx_pes_filter_params flt = {};
	flt.pid = pid;
	flt.input = DMX_IN_FRONTEND;
	flt.output = DMX_OUT_TSDEMUX_TAP;
	/* typed tap: the descrambler of this decoder applies (as DreamOS) */
	flt.pes_type = (dmx_pes_type_t)m_pes_type;
	flt.flags = DMX_IMMEDIATE_START;
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &flt) < 0)
	{
		eWarning("[eDVBVideoSwDemux] unable to tap video PID %04x: %m", pid);
		::close(m_fd_demux);
		m_fd_demux = -1;
		return -1;
	}

	m_pid = pid;
	m_codec = codec;
	m_cc = -1;
	/* the mosaic decoders run the clock of the service from its PCR */
	m_pcr = -1;
	m_pcr_pid = -1;
	if (m_with_pcr)
	{
		m_pcr_pid = (pcr_pid > 0 && pcr_pid < 0x1FFF) ? pcr_pid : pid;
		uint16_t add = m_pcr_pid;
		if (m_pcr_pid != pid && ::ioctl(m_fd_demux, DMX_ADD_PID, &add) < 0)
		{
			eDebug("[eDVBVideoSwDemux] unable to tap PCR PID %04x: %m", m_pcr_pid);
			m_pcr_pid = -1;
		}
	}
	/* the data up to the first PES start belongs to no PES */
	m_pes_broken = true;
	m_synced = codec == OTHER;
	m_base_reported = false;
	m_random_access = false;
	m_partial.clear();
	m_pes.clear();
	/* memory input after VIDEO_PLAY (as DreamOS) */
	if (::ioctl(m_fd_video, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) < 0)
		eDebug("[eDVBVideoSwDemux] VIDEO_SELECT_SOURCE failed: %m");
	m_stop = false;
	run();
	eDebug("[eDVBVideoSwDemux] video PID %04x started", pid);
	return 0;
}

void eDVBVideoSwDemux::stop()
{
	m_stop = true;
	kill();
	if (m_base_reported)
		CFile::writeStr(PIP_PTS_STREAM_BASE, "0");
	m_base_reported = false;
	if (m_fd_demux >= 0)
	{
		::ioctl(m_fd_demux, DMX_STOP);
		::close(m_fd_demux);
		m_fd_demux = -1;
	}
	m_pid = -1;
}

void eDVBVideoSwDemux::thread()
{
	hasStarted();
	std::vector<uint8_t> buffer(TSPacketSize * 512);
	struct pollfd pfd = {m_fd_demux, POLLIN, 0};

	while (!m_stop)
	{
		if (::poll(&pfd, 1, 100) <= 0)
			continue;
		ssize_t length = ::read(m_fd_demux, buffer.data(), buffer.size());
		if (length < 0)
		{
			if (errno == EOVERFLOW)
			{
				m_partial.clear();
				m_pes.clear();
				continue;
			}
			if (errno != EAGAIN && errno != EINTR)
			{
				eWarning("[eDVBVideoSwDemux] read error on PID %04x: %m", m_pid);
				break;
			}
			continue;
		}
		feed(buffer.data(), length);
	}
}

void eDVBVideoSwDemux::feed(const uint8_t *data, size_t length)
{
	m_partial.insert(m_partial.end(), data, data + length);
	size_t pos = 0;
	while (m_partial.size() - pos >= TSPacketSize && !m_stop)
	{
		const uint8_t *packet = &m_partial[pos];
		if (packet[0] != 0x47)
		{
			pos++;
			continue;
		}
		pos += TSPacketSize;
		/* skip transport errors; the hardware descrambler keeps the scrambling bits */
		if (packet[1] & 0x80)
			continue;
		int pid = ((packet[1] & 0x1f) << 8) | packet[2];
		int afc = (packet[3] >> 4) & 3;
		if (pid == m_pcr_pid && (afc & 2) && packet[4] >= 7 && (packet[5] & 0x10))
		{
			m_pcr = ((int64_t)packet[6] << 25) | (packet[7] << 17) | (packet[8] << 9) | (packet[9] << 1) | (packet[10] >> 7);
			m_pcr_time = monotonicUs();
		}
		if (pid != m_pid)
			continue;
		if (!(afc & 1))
			continue;
		/* a missing packet breaks its PES (null packets of the soft
		 * descrambler without a key, overflows): it is left out */
		int cc = packet[3] & 0x0f;
		bool discontinuity = (afc & 2) && packet[4] && (packet[5] & 0x80);
		if (m_cc >= 0 && !discontinuity)
		{
			if (cc == m_cc)
				continue;
			if (cc != ((m_cc + 1) & 0x0f))
			{
				m_pes.clear();
				m_pes_broken = true;
			}
		}
		m_cc = cc;
		int offset = 4;
		if (afc & 2)
			offset += 1 + packet[4];
		if (offset >= TSPacketSize)
			continue;
		/* a payload unit start ends the previous PES packet */
		if (packet[1] & 0x40)
		{
			if (!m_pes_broken)
				writeFrame();
			m_pes.clear();
			m_pes_broken = false;
			m_random_access = (afc & 2) && packet[4] && (packet[5] & 0x40);
		}
		else if (m_pes_broken)
			continue;
		m_pes.insert(m_pes.end(), packet + offset, packet + TSPacketSize);
	}
	m_partial.erase(m_partial.begin(), m_partial.begin() + pos);
}

void eDVBVideoSwDemux::writeFrame()
{
	if (m_pes.size() < 9 || m_pes[0] || m_pes[1] || m_pes[2] != 1)
		return;
	size_t header = 9 + m_pes[8];
	if (header >= m_pes.size())
		return;

	video_frame frame = {};
	frame.pts = -1;
	if ((m_pes[7] & 0x80) && m_pes.size() >= 14)
		frame.pts = ((int64_t)(m_pes[9] & 0x0e) << 29) | (m_pes[10] << 22) | ((m_pes[11] & 0xfe) << 14) | (m_pes[12] << 7) | (m_pes[13] >> 1);

	if (!m_base_reported && m_random_access && frame.pts >= 0)
		reportStreamBase(frame.pts);

	/* the clock of the service now: the last PCR and the time since */
	if (m_pcr >= 0)
		frame.reserved[0] = (int64_t)(VIDEO_FRAME_PCR | ((uint64_t)(m_pcr + (monotonicUs() - m_pcr_time) * 9 / 100) & ((1ULL << 33) - 1)));

	const uint8_t *es = &m_pes[header];
	size_t left = m_pes.size() - header;
	/* the decoder starts with an entry point, not in the middle of a GOP;
	 * the mosaic driver waits for it itself and takes the clock of the
	 * service from the frames before, ahead of the audio */
	if (!m_synced)
	{
		if (entryPoint(es, left))
		{
			m_synced = true;
			eDebug("[eDVBVideoSwDemux] video PID %04x entry point", m_pid);
		}
		else if (!m_with_pcr)
			return;
	}
	/* the driver takes what fits into its buffer; wait for the rest */
	while (left && !m_stop)
	{
		frame.data[0] = es;
		frame.size[0] = left;
		int done = ::ioctl(m_fd_video, VIDEO_SET_FRAME, &frame);
		if (done > 0)
		{
			es += done;
			left -= done;
			frame.pts = -1;
		}
		else if (done < 0 && errno != EAGAIN && errno != EINTR)
		{
			eWarning("[eDVBVideoSwDemux] VIDEO_SET_FRAME failed: %m");
			return;
		}
		else
			usleep(5000);
	}
}

/* parameter sets or a picture to start the decoding with */
bool eDVBVideoSwDemux::entryPoint(const uint8_t *es, size_t length) const
{
	for (size_t i = 0; i + 3 < length; ++i)
	{
		if (es[i] || es[i + 1] || es[i + 2] != 1)
			continue;
		uint8_t code = es[i + 3];
		switch (m_codec)
		{
		case MPEG2:
			/* sequence header */
			if (code == 0xb3)
				return true;
			break;
		case H264:
			/* SPS or IDR picture */
			if (!(code & 0x80) && ((code & 0x1f) == 7 || (code & 0x1f) == 5))
				return true;
			break;
		case HEVC:
		{
			/* IRAP picture, VPS or SPS */
			int type = (code >> 1) & 0x3f;
			if (!(code & 0x80) && ((type >= 16 && type <= 21) || type == 32 || type == 33))
				return true;
			break;
		}
		default:
			return true;
		}
	}
	return false;
}

void eDVBVideoSwDemux::reportStreamBase(int64_t pts)
{
	char value[16];
	snprintf(value, sizeof(value), "%u", (unsigned int)pts);
	CFile::writeStr(PIP_PTS_STREAM_BASE, value);
	m_base_reported = true;
	eDebug("[eDVBVideoSwDemux] stream PTS base %s", value);
}
