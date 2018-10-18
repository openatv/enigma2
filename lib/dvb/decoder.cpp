#include <lib/base/cfile.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h>
#include <lib/base/wrappers.h>
#include <lib/dvb/decoder.h>
#include <lib/components/tuxtxtapp.h>
#include <linux/dvb/audio.h>
#include <linux/dvb/video.h>
#include <linux/dvb/dmx.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>

#ifndef VIDEO_SOURCE_HDMI
#define VIDEO_SOURCE_HDMI 2
#endif
#ifndef AUDIO_SOURCE_HDMI
#define AUDIO_SOURCE_HDMI 2
#endif

DEFINE_REF(eDVBAudio);

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev)
	:m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", demux ? demux->adapter : 0, dev);
	m_fd = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd < 0)
		eWarning("[eDVBAudio] %s: %m", filename);
	if (demux)
	{
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
		m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
		if (m_fd_demux < 0)
			eWarning("[eDVBAudio] %s: %m", filename);
	}
	else
	{
		m_fd_demux = -1;
	}

	if (m_fd >= 0)
	{
		::ioctl(m_fd, AUDIO_SELECT_SOURCE, demux ? AUDIO_SOURCE_DEMUX : AUDIO_SOURCE_HDMI);
	}
}

int eDVBAudio::startPid(int pid, int type)
{
	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes;
		memset(&pes, 0, sizeof(pes));

		pes.pid      = pid;
		pes.input    = DMX_IN_FRONTEND;
		pes.output   = DMX_OUT_DECODER;
		switch (m_dev)
		{
		case 0:
			pes.pes_type = DMX_PES_AUDIO0;
			break;
		case 1:
			pes.pes_type = DMX_PES_AUDIO1;
			break;
		case 2:
			pes.pes_type = DMX_PES_AUDIO2;
			break;
		case 3:
			pes.pes_type = DMX_PES_AUDIO3;
			break;
		}
#if defined(__sh__) // increases zapping speed
		pes.flags    = DMX_IMMEDIATE_START;
#else
	 	pes.flags    = 0;
#endif
		eDebugNoNewLineStart("[eDVBAudio%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			eDebugNoNewLine("failed: %m");
			return -errno;
		}
		eDebugNoNewLine("ok");
#if not defined(__sh__) // already startet cause of DMX_IMMEDIATE_START
		eDebugNoNewLineStart("[eDVBAudio%d] DEMUX_START ", m_dev);
		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			eDebugNoNewLine("failed: %m");
			return -errno;
		}
		eDebugNoNewLine("ok");
#endif
	}

	if (m_fd >= 0)
	{
		int bypass = 0;

		switch (type)
		{
		case aMPEG:
			bypass = 1;
			break;
		case aAC3:
		case aAC4: /* FIXME: AC4 most probably will use other bypass value */
			bypass = 0;
			break;
		case aDTS:
			bypass = 2;
			break;
		case aAAC:
			bypass = 8;
			break;
		case aAACHE:
			bypass = 9;
			break;
		case aLPCM:
			bypass = 6;
			break;
		case aDTSHD:
			bypass = 0x10;
			break;
		case aDRA:
			bypass = 0x40;
			break;			
		case aDDP:
#ifdef DREAMBOX
		bypass = 7;
#else
		bypass = 0x22;
#endif
		break;
		}

		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_SET_BYPASS bypass=%d ", m_dev, bypass);
		if (::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
#if not defined(__sh__) // this is a hack which only matters for dm drivers
		freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
#endif
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_PLAY ", m_dev);
		if (::ioctl(m_fd, AUDIO_PLAY) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
	return 0;
}

void eDVBAudio::stop()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_STOP ", m_dev);
		if (::ioctl(m_fd, AUDIO_STOP) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
	if (m_fd_demux >= 0)
	{
		eDebugNoNewLineStart("[eDVBAudio%d] DEMUX_STOP ", m_dev);
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBAudio::flush()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CLEAR_BUFFER ", m_dev);
		if (::ioctl(m_fd, AUDIO_CLEAR_BUFFER) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBAudio::freeze()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_PAUSE ", m_dev);
		if (::ioctl(m_fd, AUDIO_PAUSE) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBAudio::unfreeze()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CONTINUE ", m_dev);
		if (::ioctl(m_fd, AUDIO_CONTINUE) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBAudio::setChannel(int channel)
{
	if (m_fd >= 0)
	{
		int val = AUDIO_STEREO;
		switch (channel)
		{
		case aMonoLeft: val = AUDIO_MONO_LEFT; break;
		case aMonoRight: val = AUDIO_MONO_RIGHT; break;
		default: break;
		}
		eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CHANNEL_SELECT %d ", m_dev, val);
		if (::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

int eDVBAudio::getPTS(pts_t &now)
{
	if (m_fd >= 0)
	{
		if (::ioctl(m_fd, AUDIO_GET_PTS, &now) < 0)
			eDebug("[eDVBAudio%d] AUDIO_GET_PTS failed: %m", m_dev);
	}
	return 0;
}

eDVBAudio::~eDVBAudio()
{
	unfreeze();  // why unfreeze here... but not unfreeze video in ~eDVBVideo ?!?
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	eDebug("[eDVBAudio%d] destroy", m_dev);
}

DEFINE_REF(eDVBVideo);

int eDVBVideo::m_close_invalidates_attributes = -1;

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev)
	: m_demux(demux), m_dev(dev),
	m_width(-1), m_height(-1), m_framerate(-1), m_aspect(-1), m_progressive(-1), m_gamma(-1)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/video%d", demux ? demux->adapter : 0, dev);
	m_fd = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd < 0)
		eWarning("[eDVBVideo] %s: %m", filename);
	else
	{
		eDebug("[eDVBVideo] Video Device: %s", filename);
		m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Priority);
		CONNECT(m_sn->activated, eDVBVideo::video_event);
	}
	if (demux)
	{
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
		m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
		if (m_fd_demux < 0)
			eWarning("[eDVBVideo] %s: %m", filename);
		else
			eDebug("[eDVBVideo] demux device: %s", filename);
	}
	else
	{
		m_fd_demux = -1;
	}

	if (m_fd >= 0)
	{
		::ioctl(m_fd, VIDEO_SELECT_SOURCE, demux ? VIDEO_SOURCE_DEMUX : VIDEO_SOURCE_HDMI);
	}

	if (m_close_invalidates_attributes < 0)
	{
		/*
		 * Some hardware does not invalidate the video attributes,
		 * when we open the video device.
		 * If that is the case, we cannot rely on receiving VIDEO_EVENTs
		 * when the new video attributes are available, because they might
		 * be equal to the old attributes.
		 * Instead, we should just query the old attributes, and assume
		 * them to be correct untill we receive VIDEO_EVENTs.
		 *
		 * Though this is merely a cosmetic issue, we do try to detect
		 * whether attributes are invalidated or not.
		 * So we can avoid polling for valid attributes, when we know
		 * we can rely on VIDEO_EVENTs.
		 */
		readApiSize(m_fd, m_width, m_height, m_aspect);
		m_close_invalidates_attributes = (m_width == -1) ? 1 : 0;
	}
}

// not finally values i think.. !!
#define VIDEO_STREAMTYPE_MPEG2 0
#define VIDEO_STREAMTYPE_MPEG4_H264 1
#define VIDEO_STREAMTYPE_VC1 3
#define VIDEO_STREAMTYPE_MPEG4_Part2 4
#define VIDEO_STREAMTYPE_VC1_SM 5
#define VIDEO_STREAMTYPE_MPEG1 6
#ifdef DREAMBOX
#define VIDEO_STREAMTYPE_H265_HEVC 22
#else
#define VIDEO_STREAMTYPE_H265_HEVC 7
#endif
#define VIDEO_STREAMTYPE_AVS 16

int eDVBVideo::startPid(int pid, int type)
{
	if (m_fd >= 0)
	{
		int streamtype = VIDEO_STREAMTYPE_MPEG2;
		switch (type)
		{
		default:
		case MPEG2:
			break;
		case MPEG4_H264:
			streamtype = VIDEO_STREAMTYPE_MPEG4_H264;
			break;
		case MPEG1:
			streamtype = VIDEO_STREAMTYPE_MPEG1;
			break;
		case MPEG4_Part2:
			streamtype = VIDEO_STREAMTYPE_MPEG4_Part2;
			break;
		case VC1:
			streamtype = VIDEO_STREAMTYPE_VC1;
			break;
		case VC1_SM:
			streamtype = VIDEO_STREAMTYPE_VC1_SM;
			break;
		case H265_HEVC:
			streamtype = VIDEO_STREAMTYPE_H265_HEVC;
			break;
		case AVS:
			streamtype = VIDEO_STREAMTYPE_AVS;
			break;
		}

		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_SET_STREAMTYPE %d - ", m_dev, streamtype);
		if (::ioctl(m_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}

	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes;
		memset(&pes, 0, sizeof(pes));

		pes.pid      = pid;
		pes.input    = DMX_IN_FRONTEND;
		pes.output   = DMX_OUT_DECODER;
		switch (m_dev)
		{
		case 0:
			pes.pes_type = DMX_PES_VIDEO0;
			break;
		case 1:
			pes.pes_type = DMX_PES_VIDEO1;
			break;
		case 2:
			pes.pes_type = DMX_PES_VIDEO2;
			break;
		case 3:
			pes.pes_type = DMX_PES_VIDEO3;
			break;
		}
#if defined(__sh__) // increases zapping speed
		pes.flags    = DMX_IMMEDIATE_START;
#else
		pes.flags    = 0;
#endif
		eDebugNoNewLineStart("[eDVBVideo%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			eDebugNoNewLine("failed: %m");
			return -errno;
		}
		eDebugNoNewLine("ok");
#if not defined(__sh__) // already startet cause of DMX_IMMEDIATE_START
		eDebugNoNewLineStart("[eDVBVideo%d] DEMUX_START ", m_dev);
		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			eDebugNoNewLine("failed: %m");
			return -errno;
		}
		eDebugNoNewLine("ok");
#endif
	}

	if (m_fd >= 0)
	{
#if not defined(__sh__) // this is a hack which only matters for dm drivers
		freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
#endif
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_PLAY ", m_dev);
		if (::ioctl(m_fd, VIDEO_PLAY) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
	return 0;
}

void eDVBVideo::stop()
{
	if (m_fd_demux >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] DEMUX_STOP  ", m_dev);
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}

	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_STOP ", m_dev);
		if (::ioctl(m_fd, VIDEO_STOP, 1) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBVideo::flush()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_CLEAR_BUFFER ", m_dev);
		if (::ioctl(m_fd, VIDEO_CLEAR_BUFFER) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBVideo::freeze()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_FREEZE ", m_dev);
		if (::ioctl(m_fd, VIDEO_FREEZE) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

void eDVBVideo::unfreeze()
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_CONTINUE ", m_dev);
		if (::ioctl(m_fd, VIDEO_CONTINUE) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
}

int eDVBVideo::setSlowMotion(int repeat)
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_SLOWMOTION %d ", m_dev, repeat);
		int ret = ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
		if (ret < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
		return ret;
	}
	return 0;
}

int eDVBVideo::setFastForward(int skip)
{
	if (m_fd >= 0)
	{
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_FAST_FORWARD %d ", m_dev, skip);
		int ret = ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
		if (ret < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
		return ret;
	}
	return 0;
}

int eDVBVideo::getPTS(pts_t &now)
{
	if (m_fd >= 0)
	{
		int ret = ::ioctl(m_fd, VIDEO_GET_PTS, &now);
		if (ret < 0)
			eDebug("[eDVBVideo%d] VIDEO_GET_PTS failed: %m", m_dev);
		return ret;
	}
	return 0;
}

eDVBVideo::~eDVBVideo()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	eDebug("[eDVBVideo%d] destroy", m_dev);
}

void eDVBVideo::video_event(int)
{
	while (m_fd >= 0)
	{
		int retval;
		pollfd pfd[1];
		pfd[0].fd = m_fd;
		pfd[0].events = POLLPRI;
		retval = ::poll(pfd, 1, 0);
		if (retval < 0 && errno == EINTR) continue;
		if (retval <= 0) break;
		struct video_event evt;
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_GET_EVENT ", m_dev);
		if (::ioctl(m_fd, VIDEO_GET_EVENT, &evt) < 0)
		{
			eDebugNoNewLine("failed: %m");
			break;
		}
		else
		{
			if (evt.type == VIDEO_EVENT_SIZE_CHANGED)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventSizeChanged;
				m_aspect = event.aspect = evt.u.size.aspect_ratio == 0 ? 2 : 3;  // convert dvb api to etsi
				m_height = event.height = evt.u.size.h;
				m_width = event.width = evt.u.size.w;
				eDebugNoNewLine("SIZE_CHANGED %dx%d aspect %d\n", m_width, m_height, m_aspect);
				/* emit */ m_event(event);
			}
			else if (evt.type == VIDEO_EVENT_FRAME_RATE_CHANGED)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventFrameRateChanged;
				m_framerate = event.framerate = evt.u.frame_rate;
				eDebugNoNewLine("FRAME_RATE_CHANGED %d fps\n", m_framerate);
				/* emit */ m_event(event);
			}
			else if (evt.type == 16 /*VIDEO_EVENT_PROGRESSIVE_CHANGED*/)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
				m_progressive = event.progressive = evt.u.frame_rate;
				eDebugNoNewLine("PROGRESSIVE_CHANGED %d\n", m_progressive);
				/* emit */ m_event(event);
			}
			else if (evt.type == 17 /*VIDEO_EVENT_GAMMA_CHANGED*/)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventGammaChanged;
				/*
				 * Possible gamma values
				 * 0: Traditional gamma - SDR luminance range
				 * 1: Traditional gamma - HDR luminance range
				 * 2: SMPTE ST2084 (aka HDR10)
				 * 3: Hybrid Log-gamma
				 */
				m_gamma = event.gamma = evt.u.frame_rate;
				eDebugNoNewLine("GAMMA_CHANGED %d\n", m_gamma);
				/* emit */ m_event(event);
			}
			else
				eDebugNoNewLine("unhandled DVBAPI Video Event %d\n", evt.type);
		}
	}
}

RESULT eDVBVideo::connectEvent(const sigc::slot1<void, struct iTSMPEGDecoder::videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

int eDVBVideo::readApiSize(int fd, int &xres, int &yres, int &aspect)
{
	video_size_t size;
	if (!::ioctl(fd, VIDEO_GET_SIZE, &size))
	{
		xres = size.w;
		yres = size.h;
		aspect = size.aspect_ratio == 0 ? 2 : 3;  // convert dvb api to etsi
		return 0;
	}
	return -1;
}

int eDVBVideo::getWidth()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_width == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
	}
	return m_width;
}

int eDVBVideo::getHeight()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_height == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
	}
	return m_height;
}

int eDVBVideo::getAspect()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_aspect == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
	}
	return m_aspect;
}

int eDVBVideo::getProgressive()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_progressive == -1)
		{
			char tmp[64];
			sprintf(tmp, "/proc/stb/vmpeg/%d/progressive", m_dev);
			CFile::parseIntHex(&m_progressive, tmp);
		}
	}
	return m_progressive;
}

int eDVBVideo::getFrameRate()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_framerate == -1)
		{
			if (m_fd >= 0)
			{
				::ioctl(m_fd, VIDEO_GET_FRAME_RATE, &m_framerate);
			}
		}
	}
	return m_framerate;
}

int eDVBVideo::getGamma()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_gamma == -1)
		{
			char tmp[64];
			sprintf(tmp, "/proc/stb/vmpeg/%d/gamma", m_dev);
			CFile::parseIntHex(&m_gamma, tmp);
		}
	}
	return m_gamma;
}

DEFINE_REF(eDVBPCR);

eDVBPCR::eDVBPCR(eDVBDemux *demux, int dev): m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd_demux < 0)
		eWarning("[eDVBPCR] %s: %m", filename);
}

int eDVBPCR::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;
	memset(&pes, 0, sizeof(pes));

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	switch (m_dev)
	{
	case 0:
		pes.pes_type = DMX_PES_PCR0;
		break;
	case 1:
		pes.pes_type = DMX_PES_PCR1;
		break;
	case 2:
		pes.pes_type = DMX_PES_PCR2;
		break;
	case 3:
		pes.pes_type = DMX_PES_PCR3;
		break;
	}
#if defined(__sh__) // increases zapping speed
	pes.flags    = DMX_IMMEDIATE_START;
#else
	pes.flags    = 0;
#endif
	eDebugNoNewLineStart("[eDVBPCR%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebugNoNewLine("failed: %m");
		return -errno;
	}
	eDebugNoNewLine("ok");
#if not defined(__sh__) // already startet cause of DMX_IMMEDIATE_START
	eDebugNoNewLineStart("[eDVBPCR%d] DEMUX_START ", m_dev);
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebugNoNewLine("failed: %m");
		return -errno;
	}
	eDebugNoNewLine("ok");
#endif
	return 0;
}

void eDVBPCR::stop()
{
	eDebugNoNewLineStart("[eDVBPCR%d] DEMUX_STOP ", m_dev);
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebugNoNewLine("failed: %m");
	else
		eDebugNoNewLine("ok");
}

eDVBPCR::~eDVBPCR()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	eDebug("[eDVBPCR%d] destroy", m_dev);
}

DEFINE_REF(eDVBTText);

eDVBTText::eDVBTText(eDVBDemux *demux, int dev)
    :m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd_demux < 0)
		eWarning("[eDVBText] %s: %m", filename);
}

int eDVBTText::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;
	memset(&pes, 0, sizeof(pes));

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	switch (m_dev)
	{
	case 0:
		pes.pes_type = DMX_PES_TELETEXT0;
		break;
	case 1:
		pes.pes_type = DMX_PES_TELETEXT1;
		break;
	case 2:
		pes.pes_type = DMX_PES_TELETEXT2;
		break;
	case 3:
		pes.pes_type = DMX_PES_TELETEXT3;
		break;
	}
#if defined(__sh__) // increases zapping speed
	pes.flags    = DMX_IMMEDIATE_START;
#else
 	pes.flags    = 0;
#endif

	eDebugNoNewLineStart("[eDVBText%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebugNoNewLine("failed: %m");
		return -errno;
	}
	eDebugNoNewLine("ok");
#if not defined(__sh__) // already startet cause of DMX_IMMEDIATE_START
	eDebugNoNewLineStart("[eDVBText%d] DEMUX_START ", m_dev);
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebugNoNewLine("failed: %m");
		return -errno;
	}
	eDebugNoNewLine("ok");
#endif
	return 0;
}

void eDVBTText::stop()
{
	eDebugNoNewLineStart("[eDVBText%d] DEMUX_STOP ", m_dev);
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebugNoNewLine("failed: %m");
	else
		eDebugNoNewLine("ok");
}

eDVBTText::~eDVBTText()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	eDebug("[eDVBText%d] destroy", m_dev);
}

DEFINE_REF(eTSMPEGDecoder);

int eTSMPEGDecoder::setState()
{
	int res = 0;

	int noaudio = (m_state != statePlay) && (m_state != statePause);
	int nott = noaudio; /* actually same conditions */

	if ((noaudio && m_audio) || (!m_audio && !noaudio))
		m_changed |= changeAudio | changeState;

	if ((nott && m_text) || (!m_text && !nott))
		m_changed |= changeText | changeState;

	const char *decoder_states[] = {"stop", "pause", "play", "decoderfastforward", "trickmode", "slowmotion"};
	eDebug("[eTSMPEGDecoder] decoder state: %s, vpid=%04x, apid=%04x", decoder_states[m_state], m_vpid, m_apid);

	int changed = m_changed;
	if (m_changed & changePCR)
	{
		if (m_pcr)
			m_pcr->stop();
		m_pcr = 0;
	}
	if (m_changed & changeVideo)
	{
		if (m_video)
		{
			m_video->stop();
			m_video = 0;
			m_video_event_conn = 0;
		}
	}
	if (m_changed & changeAudio)
	{
		if (m_audio)
			m_audio->stop();
		m_audio = 0;
	}
	if (m_changed & changeText)
	{
		if (m_text)
		{
			m_text->stop();
			if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
				eTuxtxtApp::getInstance()->stopCaching();
		}
		m_text = 0;
	}
	if (m_changed & changePCR)
	{
		if ((m_pcrpid >= 0) && (m_pcrpid < 0x1FFF))
		{
			m_pcr = new eDVBPCR(m_demux, m_decoder);
			if (m_pcr->startPid(m_pcrpid))
				res = -1;
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeAudio)
	{
		if ((m_apid >= 0) && (m_apid < 0x1FFF) && !noaudio)
		{
			m_audio = new eDVBAudio(m_demux, m_decoder);
			if (m_audio->startPid(m_apid, m_atype))
				res = -1;
		}
		m_changed &= ~changeAudio;
	}
	if (m_changed & changeVideo)
	{
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			m_video = new eDVBVideo(m_demux, m_decoder);
			m_video->connectEvent(sigc::mem_fun(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
			if (m_video->startPid(m_vpid, m_vtype))
				res = -1;
		}
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeText)
	{
		if ((m_textpid >= 0) && (m_textpid < 0x1FFF) && !nott)
		{
			m_text = new eDVBTText(m_demux, m_decoder);
			if (m_text->startPid(m_textpid))
				res = -1;

			if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
			{
				uint8_t demux = 0;
				m_demux->getCADemuxID(demux);
				eTuxtxtApp::getInstance()->startCaching(m_textpid, demux);
			}
		}
		else if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
			eTuxtxtApp::getInstance()->resetPid();

		m_changed &= ~changeText;
	}

	if (changed & (changeState|changeVideo|changeAudio))
	{
					/* play, slowmotion, fast-forward */
		int state_table[6][4] =
			{
				/* [stateStop] =                 */ {0, 0, 0},
				/* [statePause] =                */ {0, 0, 0},
				/* [statePlay] =                 */ {1, 0, 0},
				/* [stateDecoderFastForward] =   */ {1, 0, m_ff_sm_ratio},
				/* [stateHighspeedFastForward] = */ {1, 0, 1},
				/* [stateSlowMotion] =           */ {1, m_ff_sm_ratio, 0}
			};
		int *s = state_table[m_state];
		if (changed & (changeState|changeVideo) && m_video)
		{
#if not defined(__sh__) // see comment below
			m_video->setSlowMotion(s[1]);
			m_video->setFastForward(s[2]);
#endif
			if (s[0])
				m_video->unfreeze();
			else
				m_video->freeze();
#if defined(__sh__)
// the VIDEO_CONTINUE would reset the FASTFORWARD  command so we
// execute the FASTFORWARD after the VIDEO_CONTINUE
			if (s[1])
			{
				m_video->setFastForward(s[2]);
				m_video->setSlowMotion(s[1]);
			}
			else
			{
				m_video->setSlowMotion(s[1]);
				m_video->setFastForward(s[2]);
			}
#endif
		}
		if (changed & (changeState|changeAudio) && m_audio)
		{
			if (s[0])
				m_audio->unfreeze();
			else
				m_audio->freeze();
		}
		m_changed &= ~changeState;
	}

	if (changed && !m_video && m_audio && m_radio_pic.length())
		showSinglePic(m_radio_pic.c_str());

	return res;
}

int eTSMPEGDecoder::m_pcm_delay=-1,
	eTSMPEGDecoder::m_ac3_delay=-1;

RESULT eTSMPEGDecoder::setHwPCMDelay(int delay)
{
	if (delay != m_pcm_delay )
	{
		if (CFile::writeIntHex("/proc/stb/audio/audio_delay_pcm", delay*90) >= 0)
		{
			m_pcm_delay = delay;
			return 0;
		}
	}
	return -1;
}

RESULT eTSMPEGDecoder::setHwAC3Delay(int delay)
{
	if ( delay != m_ac3_delay )
	{
		if (CFile::writeIntHex("/proc/stb/audio/audio_delay_bitstream", delay*90) >= 0)
		{
			m_ac3_delay = delay;
			return 0;
		}
	}
	return -1;
}


RESULT eTSMPEGDecoder::setPCMDelay(int delay)
{
	return m_decoder == 0 ? setHwPCMDelay(delay) : -1;
}

RESULT eTSMPEGDecoder::setAC3Delay(int delay)
{
	return m_decoder == 0 ? setHwAC3Delay(delay) : -1;
}

eTSMPEGDecoder::eTSMPEGDecoder(eDVBDemux *demux, int decoder)
	: m_demux(demux),
		m_vpid(-1), m_vtype(-1), m_apid(-1), m_atype(-1), m_pcrpid(-1), m_textpid(-1),
		m_changed(0), m_decoder(decoder), m_video_clip_fd(-1), m_showSinglePicTimer(eTimer::create(eApp))
{
	if (m_demux)
	{
		m_demux->connectEvent(sigc::mem_fun(*this, &eTSMPEGDecoder::demux_event), m_demux_event_conn);
	}
	CONNECT(m_showSinglePicTimer->timeout, eTSMPEGDecoder::finishShowSinglePic);
	m_state = stateStop;

	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", m_demux ? m_demux->adapter : 0, m_decoder);
	m_has_audio = !access(filename, W_OK);

	if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
		eTuxtxtApp::getInstance()->initCache();
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	finishShowSinglePic();
	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();

	if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
		eTuxtxtApp::getInstance()->freeCache();
}

RESULT eTSMPEGDecoder::setVideoPID(int vpid, int type)
{
	if ((m_vpid != vpid) || (m_vtype != type))
	{
		m_changed |= changeVideo;
		m_vpid = vpid;
		m_vtype = type;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setAudioPID(int apid, int type)
{
	/* do not set an audio pid on decoders without audio support */
	if (!m_has_audio) apid = -1;

	if ((m_apid != apid) || (m_atype != type))
	{
		m_changed |= changeAudio;
		m_atype = type;
		m_apid = apid;
	}
	return 0;
}

int eTSMPEGDecoder::m_audio_channel = -1;

RESULT eTSMPEGDecoder::setAudioChannel(int channel)
{
	if (channel == -1)
		channel = ac_stereo;
	if (m_decoder == 0 && m_audio_channel != channel)
	{
		if (m_audio)
		{
			m_audio->setChannel(channel);
			m_audio_channel=channel;
		}
		else
			eDebug("[eTSMPEGDecoder] setAudioChannel but no audio decoder exist");
	}
	return 0;
}

int eTSMPEGDecoder::getAudioChannel()
{
	return m_audio_channel == -1 ? ac_stereo : m_audio_channel;
}

RESULT eTSMPEGDecoder::setSyncPCR(int pcrpid)
{
	/* we do not need pcr on decoders without audio support */
	if (!m_has_audio) pcrpid = -1;

	if (m_pcrpid != pcrpid)
	{
		m_changed |= changePCR;
		m_pcrpid = pcrpid;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setTextPID(int textpid)
{
	if (m_textpid != textpid)
	{
		m_changed |= changeText;
		m_textpid = textpid;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setSyncMaster(int who)
{
	return -1;
}

RESULT eTSMPEGDecoder::set()
{
	return setState();
}

RESULT eTSMPEGDecoder::play()
{
	if (m_state == statePlay)
	{
		if (!m_changed)
			return 0;
	} else
	{
		m_state = statePlay;
		m_changed |= changeState;
	}
	return setState();
}

RESULT eTSMPEGDecoder::pause()
{
	if (m_state == statePause)
		return 0;
	m_state = statePause;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::setFastForward(int frames_to_skip)
{
	// fast forward is only possible if video data is present
	if (!m_video)
		return -1;

	if ((m_state == stateDecoderFastForward) && (m_ff_sm_ratio == frames_to_skip))
		return 0;

	m_state = stateDecoderFastForward;
	m_ff_sm_ratio = frames_to_skip;
	m_changed |= changeState;
	return setState();

//		return m_video->setFastForward(frames_to_skip);
}

RESULT eTSMPEGDecoder::setSlowMotion(int repeat)
{
	// slow motion is only possible if video data is present
	if (!m_video)
		return -1;

	if ((m_state == stateSlowMotion) && (m_ff_sm_ratio == repeat))
		return 0;

	m_state = stateSlowMotion;
	m_ff_sm_ratio = repeat;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::setTrickmode()
{
	// trickmode is only possible if video data is present
	if (!m_video)
		return -1;

	if (m_state == stateTrickmode)
		return 0;

	m_state = stateTrickmode;
	m_changed |= changeState;
	return setState();
}

RESULT eTSMPEGDecoder::flush()
{
	if (m_audio)
		m_audio->flush();
	if (m_video)
		m_video->flush();
	return 0;
}

void eTSMPEGDecoder::demux_event(int event)
{
	switch (event)
	{
	case eDVBDemux::evtFlush:
		flush();
		break;
	default:
		break;
	}
}

RESULT eTSMPEGDecoder::getPTS(int what, pts_t &pts)
{
	if (what == 0) /* auto */
		what = m_video ? 1 : 2;

	if (what == 1) /* video */
	{
		if (m_video)
			return m_video->getPTS(pts);
		else
			return -1;
	}

	if (what == 2) /* audio */
	{
		if (m_audio)
			return m_audio->getPTS(pts);
		else
			return -1;
	}

	return -1;
}

RESULT eTSMPEGDecoder::setRadioPic(const std::string &filename)
{
	m_radio_pic = filename;
	return 0;
}

RESULT eTSMPEGDecoder::showSinglePic(const char *filename)
{
	if (m_decoder == 0)
	{
		eDebug("[eTSMPEGDecoder] showSinglePic %s", filename);
		int f = open(filename, O_RDONLY);
		if (f >= 0)
		{
			struct stat s;
			fstat(f, &s);
#if defined(__sh__) // our driver has a different behaviour for iframes
			if (m_video_clip_fd >= 0)
				finishShowSinglePic();
#endif
#if HAVE_HISILICON
			if (m_video_clip_fd >= 0)
				finishShowSinglePic();
#endif
			if (m_video_clip_fd == -1)
				m_video_clip_fd = open("/dev/dvb/adapter0/video0", O_WRONLY);
			if (m_video_clip_fd >= 0)
			{
				bool seq_end_avail = false;
				size_t pos=0;
				unsigned char pes_header[] = { 0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x80, 0x80, 0x05, 0x21, 0x00, 0x01, 0x00, 0x01 };
				unsigned char seq_end[] = { 0x00, 0x00, 0x01, 0xB7 };
				unsigned char iframe[s.st_size];
				unsigned char stuffing[8192];
				int streamtype;
				memset(stuffing, 0, sizeof(stuffing));
				read(f, iframe, s.st_size);
				if (iframe[0] == 0x00 && iframe[1] == 0x00 && iframe[2] == 0x00 && iframe[3] == 0x01 && (iframe[4] & 0x0f) == 0x07)
					streamtype = VIDEO_STREAMTYPE_MPEG4_H264;
				else
					streamtype = VIDEO_STREAMTYPE_MPEG2;
#if HAVE_HISILICON
				if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, 0xff) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_SELECT_SOURCE MEMORY failed: %m");
#else
				if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_SELECT_SOURCE MEMORY failed: %m");
#endif
#if not defined(__sh__)
				if (ioctl(m_video_clip_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_SET_STREAMTYPE failed: %m");
#endif
				if (ioctl(m_video_clip_fd, VIDEO_PLAY) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_PLAY failed: %m");
				if (ioctl(m_video_clip_fd, VIDEO_CONTINUE) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_CONTINUE: %m");
				if (ioctl(m_video_clip_fd, VIDEO_CLEAR_BUFFER) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_CLEAR_BUFFER: %m");
				while(pos <= (s.st_size-4) && !(seq_end_avail = (!iframe[pos] && !iframe[pos+1] && iframe[pos+2] == 1 && iframe[pos+3] == 0xB7)))
					++pos;
				if ((iframe[3] >> 4) != 0xE) // no pes header
					writeAll(m_video_clip_fd, pes_header, sizeof(pes_header));
				else
					iframe[4] = iframe[5] = 0x00;
				writeAll(m_video_clip_fd, iframe, s.st_size);
				if (!seq_end_avail)
					write(m_video_clip_fd, seq_end, sizeof(seq_end));
				writeAll(m_video_clip_fd, stuffing, 8192);
#if not defined(__sh__)
#if HAVE_HISILICON
				;
#else
				m_showSinglePicTimer->start(150, true);
#endif
#endif
			}
			close(f);
		}
		else
		{
			eDebug("[eTSMPEGDecoder] couldnt open %s: %m", filename);
			return -1;
		}
	}
	else
	{
		eDebug("[eTSMPEGDecoder] only show single pics on first decoder");
		return -1;
	}
	return 0;
}

void eTSMPEGDecoder::finishShowSinglePic()
{
	if (m_video_clip_fd >= 0)
	{
		if (ioctl(m_video_clip_fd, VIDEO_STOP, 0) < 0)
			eDebug("[eTSMPEGDecoder] VIDEO_STOP failed: %m");
		if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_DEMUX) < 0)
				eDebug("[eTSMPEGDecoder] VIDEO_SELECT_SOURCE DEMUX failed: %m");
		close(m_video_clip_fd);
		m_video_clip_fd = -1;
	}
}

RESULT eTSMPEGDecoder::connectVideoEvent(const sigc::slot1<void, struct videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_video_event.connect(event));
	return 0;
}

void eTSMPEGDecoder::video_event(struct videoEvent event)
{
	/* emit */ m_video_event(event);
}

int eTSMPEGDecoder::getVideoWidth()
{
	if (m_video)
		return m_video->getWidth();
	return -1;
}

int eTSMPEGDecoder::getVideoHeight()
{
	if (m_video)
		return m_video->getHeight();
	return -1;
}

int eTSMPEGDecoder::getVideoProgressive()
{
	if (m_video)
		return m_video->getProgressive();
	return -1;
}

int eTSMPEGDecoder::getVideoFrameRate()
{
	if (m_video)
		return m_video->getFrameRate();
	return -1;
}

int eTSMPEGDecoder::getVideoAspect()
{
	if (m_video)
		return m_video->getAspect();
	return -1;
}

int eTSMPEGDecoder::getVideoGamma()
{
	if (m_video)
		return m_video->getGamma();
	return -1;
}
