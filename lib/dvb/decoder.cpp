#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/dvb/decoder.h>
#if HAVE_DVB_API_VERSION < 3 
#define audioStatus audio_status
#define videoStatus video_status
#define pesType pes_type
#define playState play_state
#define audioStreamSource_t audio_stream_source_t
#define videoStreamSource_t video_stream_source_t
#define streamSource stream_source
#define dmxPesFilterParams dmx_pes_filter_params
#define DMX_PES_VIDEO0 DMX_PES_VIDEO
#define DMX_PES_AUDIO0 DMX_PES_AUDIO
#define DMX_PES_VIDEO1 DMX_PES_VIDEO
#define DMX_PES_AUDIO1 DMX_PES_AUDIO
#include <ost/dmx.h>
#include <ost/video.h>
#include <ost/audio.h>
#else
#include <linux/dvb/audio.h>
#include <linux/dvb/video.h>
#include <linux/dvb/dmx.h>
#endif

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>

	/* these are quite new... */
#ifndef AUDIO_GET_PTS
#define AUDIO_GET_PTS              _IOR('o', 19, __u64)
#define VIDEO_GET_PTS              _IOR('o', 57, __u64)
#endif

DEFINE_REF(eDVBAudio);

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev)
	:m_demux(demux), m_dev(dev), m_is_freezed(0)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/audio%d", demux->adapter, dev);
#else
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", demux->adapter, dev);
#endif
	m_fd = ::open(filename, O_RDWR);
	if (m_fd < 0)
		eWarning("%s: %m", filename);
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}

#if HAVE_DVB_API_VERSION < 3
int eDVBAudio::setPid(int pid, int type)
{
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;

	int bypass = 0;

	switch (type)
	{
	case aMPEG:
		bypass = 1;
		break;
	case aAC3:
		bypass = 0;
		break;
		/*
	case aDTS:
		bypass = 2;
		break;
		*/
	}

	if (::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass) < 0)
		eDebug("failed (%m)");

	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_AUDIO1 : DMX_PES_AUDIO0; /* FIXME */
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - audio - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");

	return 0;
}

int eDVBAudio::startPid()
{
	eDebugNoNewLine("DEMUX_START - audio - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBAudio::start()
{
	eDebugNoNewLine("AUDIO_PLAY - ");
	if (::ioctl(m_fd, AUDIO_PLAY) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBAudio::stopPid()
{
	eDebugNoNewLine("DEMUX_STOP - audio - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBAudio::setAVSync(int val)
{
	eDebugNoNewLine("AUDIO_SET_AV_SYNC - ");
	if (::ioctl(m_fd, AUDIO_SET_AV_SYNC, val) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}
#else
int eDVBAudio::startPid(int pid, int type)
{
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_AUDIO1 : DMX_PES_AUDIO0; /* FIXME */
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - audio - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - audio - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	int bypass = 0;

	switch (type)
	{
	case aMPEG:
		bypass = 1;
		break;
	case aAC3:
		bypass = 0;
		break;
		/*
	case aDTS:
		bypass = 2;
		break;
		*/
	}

	eDebugNoNewLine("AUDIO_SET_BYPASS - ");
	if (::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
	freeze();

	eDebugNoNewLine("AUDIO_PLAY - ");
	if (::ioctl(m_fd, AUDIO_PLAY) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
	return 0;
}
#endif

void eDVBAudio::stop()
{
#if HAVE_DVB_API_VERSION > 2
	flush();
#endif
	eDebugNoNewLine("AUDIO_STOP - ");
	if (::ioctl(m_fd, AUDIO_STOP) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
#if HAVE_DVB_API_VERSION > 2
	eDebugNoNewLine("DEMUX_STOP - audio - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
#endif
}

void eDVBAudio::flush()
{
	eDebugNoNewLine("AUDIO_CLEAR_BUFFER - ");
	if (::ioctl(m_fd, AUDIO_CLEAR_BUFFER) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBAudio::freeze()
{
	if (!m_is_freezed)
	{
		eDebugNoNewLine("AUDIO_PAUSE - ");
		if (::ioctl(m_fd, AUDIO_PAUSE) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		m_is_freezed=1;
	}
}

void eDVBAudio::unfreeze()
{
	if (m_is_freezed)
	{
		eDebugNoNewLine("AUDIO_CONTINUE - ");
		if (::ioctl(m_fd, AUDIO_CONTINUE) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		m_is_freezed=0;
	}
}

void eDVBAudio::setChannel(int channel)
{
	int val = AUDIO_STEREO;
	switch (channel)
	{
	case aMonoLeft: val = AUDIO_MONO_LEFT; break;
	case aMonoRight: val = AUDIO_MONO_RIGHT; break;
	default: break;
	}
	eDebugNoNewLine("AUDIO_CHANNEL_SELECT(%d) - ", val);
	if (::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

int eDVBAudio::getPTS(pts_t &now)
{
	eDebugNoNewLine("AUDIO_GET_PTS - ");
	if (::ioctl(m_fd, AUDIO_GET_PTS, &now) < 0)
		eDebug("failed (%m)");
	return 0;
}

eDVBAudio::~eDVBAudio()
{
	unfreeze();
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBVideo);

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev)
	:m_demux(demux), m_dev(dev), m_is_slow_motion(0), m_is_fast_forward(0), m_is_freezed(0)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/video%d", demux->adapter, dev);
	m_fd_video = ::open("/dev/video", O_RDWR);
	if (m_fd_video < 0)
		eWarning("/dev/video: %m");
#else
	sprintf(filename, "/dev/dvb/adapter%d/video%d", demux->adapter, dev);
#endif
	m_fd = ::open(filename, O_RDWR);
	if (m_fd < 0)
		eWarning("%s: %m", filename);
	else
	{
		m_sn = new eSocketNotifier(eApp, m_fd, eSocketNotifier::Priority);
		CONNECT(m_sn->activated, eDVBVideo::video_event);
	}
	eDebug("Video Device: %s", filename);
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
	eDebug("demux device: %s", filename);
}

// not finally values i think.. !!
#define VIDEO_STREAMTYPE_MPEG2 0
#define VIDEO_STREAMTYPE_MPEG4_H264 1

#if HAVE_DVB_API_VERSION < 3
int eDVBVideo::setPid(int pid)
{
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_VIDEO1 : DMX_PES_VIDEO0; /* FIXME */
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - video - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBVideo::startPid()
{
	eDebugNoNewLine("DEMUX_START - video - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBVideo::start()
{
	eDebugNoNewLine("VIDEO_PLAY - ");
	if (::ioctl(m_fd, VIDEO_PLAY) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBVideo::stopPid()
{
	eDebugNoNewLine("DEMUX_STOP - video - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}
#else
int eDVBVideo::startPid(int pid, int type)
{
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;

	eDebugNoNewLine("VIDEO_SET_STREAMTYPE %d - ",type == MPEG4_H264 ? VIDEO_STREAMTYPE_MPEG4_H264 : VIDEO_STREAMTYPE_MPEG2);
	if (::ioctl(m_fd, VIDEO_SET_STREAMTYPE,
		type == MPEG4_H264 ? VIDEO_STREAMTYPE_MPEG4_H264 : VIDEO_STREAMTYPE_MPEG2) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_VIDEO1 : DMX_PES_VIDEO0; /* FIXME */
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - video - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - video - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	freeze();
	eDebugNoNewLine("VIDEO_PLAY - ");
	if (::ioctl(m_fd, VIDEO_PLAY) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
	return 0;
}
#endif

void eDVBVideo::stop()
{
#if HAVE_DVB_API_VERSION > 2
	eDebugNoNewLine("DEMUX_STOP - video - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
#endif
	eDebugNoNewLine("VIDEO_STOP - ");
	if (::ioctl(m_fd, VIDEO_STOP, 1) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBVideo::flush()
{
	eDebugNoNewLine("VIDEO_CLEAR_BUFFER - ");
	if (::ioctl(m_fd, VIDEO_CLEAR_BUFFER) < 0)
		eDebug("failed (%m)");
	else
		eDebug("ok");
}

void eDVBVideo::freeze()
{
	if (!m_is_freezed)
	{
		eDebugNoNewLine("VIDEO_FREEZE - ");
		if (::ioctl(m_fd, VIDEO_FREEZE) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		m_is_freezed=1;
	}
}

void eDVBVideo::unfreeze()
{
	if (m_is_freezed)
	{
		eDebugNoNewLine("VIDEO_CONTINUE - ");
		if (::ioctl(m_fd, VIDEO_CONTINUE) < 0)
			eDebug("failed (%m)");
		else
			eDebug("ok");
		m_is_freezed=0;
	}
}

int eDVBVideo::setSlowMotion(int repeat)
{
	eDebugNoNewLine("VIDEO_SLOWMOTION - ");
	m_is_slow_motion = repeat;
	int ret = ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
	if (ret < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
	return ret;
}

int eDVBVideo::setFastForward(int skip)
{
	eDebugNoNewLine("VIDEO_FAST_FORWARD - ");
	m_is_fast_forward = skip;
	int ret = ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
	if (ret < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
	return ret;
}

int eDVBVideo::getPTS(pts_t &now)
{
#if HAVE_DVB_API_VERSION < 3
	#define VIDEO_GET_PTS_OLD           _IOR('o', 1, unsigned int*)
	unsigned int pts;
	int ret = ::ioctl(m_fd_video, VIDEO_GET_PTS_OLD, &pts);
	now = pts;
	now *= 2;
#else
	int ret = ::ioctl(m_fd, VIDEO_GET_PTS, &now);
#endif
	if (ret < 0)
		eDebug("VIDEO_GET_PTS failed(%m)");
	return ret;
}

eDVBVideo::~eDVBVideo()
{
	if (m_sn)
		delete m_sn;
	if (m_is_slow_motion)
		setSlowMotion(0);
	if (m_is_fast_forward)
		setFastForward(0);
	unfreeze();
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
#if HAVE_DVB_API_VERSION < 3
	if (m_fd_video >= 0)
		::close(m_fd_video);
#endif
}

void eDVBVideo::video_event(int)
{
#if HAVE_DVB_API_VERSION >= 3
	struct video_event evt;
	eDebugNoNewLine("VIDEO_GET_EVENT - ");
	if (::ioctl(m_fd, VIDEO_GET_EVENT, &evt) < 0)
		eDebug("failed (%m)");
	else
	{
		eDebug("ok");
		if (evt.type == VIDEO_EVENT_SIZE_CHANGED)
		{
			struct iTSMPEGDecoder::videoEvent event;
			event.type = iTSMPEGDecoder::videoEvent::eventSizeChanged;
			event.aspect = evt.u.size.aspect_ratio;
			event.height = evt.u.size.h;
			event.width = evt.u.size.w;
			/* emit */ m_event(event);
		}
		else
			eDebug("unhandled DVBAPI Video Event %d", evt.type);
	}
#else
#warning "FIXMEE!! Video Events not implemented for old api"
#endif
}

RESULT eDVBVideo::connectEvent(const Slot1<void, struct iTSMPEGDecoder::videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

DEFINE_REF(eDVBPCR);

eDVBPCR::eDVBPCR(eDVBDemux *demux): m_demux(demux)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}

#if HAVE_DVB_API_VERSION < 3
int eDVBPCR::setPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = DMX_PES_PCR;
	pes.flags    = 0;

	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - pcr - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

int eDVBPCR::startPid()
{
	if (m_fd_demux < 0)
		return -1;
	eDebugNoNewLine("DEMUX_START - pcr - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}
#else
int eDVBPCR::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = DMX_PES_PCR;
	pes.flags    = 0;
	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - pcr - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - pcr - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed (%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}
#endif

void eDVBPCR::stop()
{
	eDebugNoNewLine("DEMUX_STOP - pcr - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
}

eDVBPCR::~eDVBPCR()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBTText);

eDVBTText::eDVBTText(eDVBDemux *demux): m_demux(demux)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}

int eDVBTText::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes;

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = DMX_PES_TELETEXT;
	pes.flags    = 0;

	eDebugNoNewLine("DMX_SET_PES_FILTER(0x%02x) - ttx - ", pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eDebug("failed(%m)");
		return -errno;
	}
	eDebug("ok");
	eDebugNoNewLine("DEMUX_START - pcr - ");
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eDebug("failed(%m)");
		return -errno;
	}
	eDebug("ok");
	return 0;
}

void eDVBTText::stop()
{
	eDebugNoNewLine("DEMUX_STOP - ttx - ");
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eDebug("failed(%m)");
	else
		eDebug("ok");
}

eDVBTText::~eDVBTText()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eTSMPEGDecoder);

int eTSMPEGDecoder::setState()
{
	int res = 0;

	int noaudio = m_is_sm || m_is_ff || m_is_trickmode;
	int nott = noaudio; /* actually same conditions */

	if ((noaudio && m_audio) || (!m_audio && !noaudio))
		m_changed |= changeAudio;

	if ((nott && m_text) || (!m_text && !nott))
		m_changed |= changeText;

	bool changed = !!m_changed;
#if HAVE_DVB_API_VERSION < 3
	bool checkAVSync = m_changed & (changeAudio|changeVideo|changePCR);
	if (m_changed & changeAudio && m_audio)
		m_audio->stopPid();
	if (m_changed & changeVideo && m_video)
		m_video->stopPid();
	if (m_changed & changePCR && m_pcr)
	{
		m_pcr->stop();
		m_pcr=0;
		if (!(m_pcrpid >= 0 && m_pcrpid < 0x1ff))
			m_changed &= ~changePCR;
	}
	if (m_changed & changeAudio && m_audio)
	{
		m_audio->stop();
		m_audio=0;
		if (!(m_apid >= 0 && m_apid < 0x1ff))
			m_changed &= ~changeAudio;
	}
	if (m_changed & changeVideo && m_video)
	{
		m_video->stop();
		m_video=0;
		m_video_event_conn=0;
		if (!(m_vpid >= 0 && m_vpid < 0x1ff))
			m_changed &= ~changeVideo;
	}
	if (m_changed & changeVideo)
	{
		m_video = new eDVBVideo(m_demux, m_decoder);
		m_video->connectEvent(slot(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
		if (m_video->setPid(m_vpid))
			res -1;
	}
	if (m_changed & changePCR)
	{
		m_pcr = new eDVBPCR(m_demux);
		if (m_pcr->setPid(m_pcrpid))
			res = -1;
	}
	if (m_changed & changeAudio)
	{
		m_audio = new eDVBAudio(m_demux, m_decoder);
		if (m_audio->setPid(m_apid, m_atype))
			res = -1;
	}
	if (m_changed & changePCR)
	{
		if (m_pcr->startPid())
			res = -1;
		m_changed &= ~changePCR;
	}
	else if (checkAVSync && m_audio && m_video)
	{
		if (m_audio->setAVSync(1))
			res = -1;
	}
	if (m_changed & changeVideo)
	{
		if (m_video->startPid() || m_video->start())
			res = -1;
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeAudio)
	{
		if (m_audio->start() || m_audio->startPid())
			res = -1;
		m_changed &= ~changeAudio;
	}
#else
	if (m_changed & changePCR)
	{
		if (m_pcr)
			m_pcr->stop();
		m_pcr = 0;
		if ((m_pcrpid >= 0) && (m_pcrpid < 0x1FFF))
		{
			m_pcr = new eDVBPCR(m_demux);
			if (m_pcr->startPid(m_pcrpid))
				res = -1;
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeVideo)
	{
		eDebug("VIDEO CHANGED (to %04x)", m_vpid);
		if (m_video)
		{
			m_video->stop();
			m_video = 0;
			m_video_event_conn = 0;
		}
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			m_video = new eDVBVideo(m_demux, m_decoder);
			m_video->connectEvent(slot(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
			if (m_video->startPid(m_vpid, m_vtype))
				res = -1;
		}
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeAudio)
	{
		if (m_audio)
			m_audio->stop();
		m_audio = 0;
		if ((m_apid >= 0) && (m_apid < 0x1FFF) && !noaudio)
		{
			m_audio = new eDVBAudio(m_demux, m_decoder);
			if (m_audio->startPid(m_apid, m_atype))
				res = -1;
		}
		m_changed &= ~changeAudio;
	}
	if (m_changed & changeText)
	{
		if (m_text)
			m_text->stop();
		m_text = 0;
		if ((m_textpid >= 0) && (m_textpid < 0x1FFF) && !nott)
		{
			m_text = new eDVBTText(m_demux);
			if (m_text->startPid(m_textpid))
				res = -1;
		}
		m_changed &= ~changeText;
	}
#endif
	if (changed && !m_video && m_audio && m_radio_pic.length())
		showSinglePic(m_radio_pic.c_str());

	return res;
}

int eTSMPEGDecoder::m_pcm_delay=-1,
	eTSMPEGDecoder::m_ac3_delay=-1;

RESULT eTSMPEGDecoder::setPCMDelay(int delay)
{
	if (m_decoder == 0 && delay != m_pcm_delay )
	{
		FILE *fp = fopen("/proc/stb/audio/audio_delay_pcm", "w");
		if (fp)
		{
			fprintf(fp, "%x", delay*90);
			fclose(fp);
			m_pcm_delay = delay;
			return 0;
		}
	}
	return -1;
}

RESULT eTSMPEGDecoder::setAC3Delay(int delay)
{
	if ( m_decoder == 0 && delay != m_ac3_delay )
	{
		FILE *fp = fopen("/proc/stb/audio/audio_delay_bitstream", "w");
		if (fp)
		{
			fprintf(fp, "%x", delay*90);
			fclose(fp);
			m_ac3_delay = delay;
			return 0;
		}
	}
	return -1;
}

eTSMPEGDecoder::eTSMPEGDecoder(eDVBDemux *demux, int decoder)
	:m_demux(demux), m_changed(0), m_decoder(decoder), m_video_clip_fd(-1), m_showSinglePicTimer(eApp)
{
	demux->connectEvent(slot(*this, &eTSMPEGDecoder::demux_event), m_demux_event_conn);
	CONNECT(m_showSinglePicTimer.timeout, eTSMPEGDecoder::finishShowSinglePic);
	m_is_ff = m_is_sm = m_is_trickmode = 0;
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	finishShowSinglePic();
	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();
}

RESULT eTSMPEGDecoder::setVideoPID(int vpid, int type)
{
	if (m_vpid != vpid)
	{
		m_changed |= changeVideo;
		m_vpid = vpid;
		m_vtype = type;
	}
	return 0;
}

RESULT eTSMPEGDecoder::setAudioPID(int apid, int type)
{
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
			eDebug("eTSMPEGDecoder::setAudioChannel but no audio decoder exist");
	}
	return 0;
}

int eTSMPEGDecoder::getAudioChannel()
{
	return m_audio_channel == -1 ? ac_stereo : m_audio_channel;
}

RESULT eTSMPEGDecoder::setSyncPCR(int pcrpid)
{
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

RESULT eTSMPEGDecoder::start()
{
	RESULT r;
	r = setState();
	if (r)
		return r;
	return unfreeze();
}

	/* preroll is start in freezed mode. */
RESULT eTSMPEGDecoder::preroll()
{
	return setState();
}

RESULT eTSMPEGDecoder::freeze(int cont)
{
	if (m_video)
		m_video->freeze();

	if (m_audio)
		m_audio->freeze();

	return 0;
}

RESULT eTSMPEGDecoder::unfreeze()
{
	if (m_video)
		m_video->unfreeze();

	if (m_audio)
		m_audio->unfreeze();

	return 0;
}

RESULT eTSMPEGDecoder::setSinglePictureMode(int when)
{
	return -1;
}

RESULT eTSMPEGDecoder::setPictureSkipMode(int what)
{
	return -1;
}

RESULT eTSMPEGDecoder::setFastForward(int frames_to_skip)
{
	m_is_ff = frames_to_skip != 0;

	setState();

	if (m_video)
		return m_video->setFastForward(frames_to_skip);
	else
	 	return -1;
}

RESULT eTSMPEGDecoder::setSlowMotion(int repeat)
{
	m_is_sm = repeat != 0;

	setState();

	if (m_video)
		return m_video->setSlowMotion(repeat);
	else
		return -1;
}

RESULT eTSMPEGDecoder::setZoom(int what)
{
	return -1;
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

RESULT eTSMPEGDecoder::setTrickmode(int what)
{
	m_is_trickmode = what;
	setState();
	return 0;
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
		eDebug("showSinglePic %s", filename);
		int f = open(filename, O_RDONLY);
		if (f)
		{
			struct stat s;
			fstat(f, &s);
			if (m_video_clip_fd == -1)
				m_video_clip_fd = open("/dev/dvb/adapter0/video0", O_WRONLY|O_NONBLOCK);
			if (m_video_clip_fd >= 0)
			{
				bool seq_end_avail = false;
				size_t pos=0;
				unsigned char pes_header[] = { 0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x80, 0x00, 0x00 };
				unsigned char seq_end[] = { 0x00, 0x00, 0x01, 0xB7 };
				unsigned char iframe[s.st_size];
				unsigned char stuffing[8192];
				memset(stuffing, 0, 8192);
				read(f, iframe, s.st_size);
				if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) < 0)
					eDebug("VIDEO_SELECT_SOURCE MEMORY failed (%m)");
				if (ioctl(m_video_clip_fd, VIDEO_PLAY) < 0)
					eDebug("VIDEO_PLAY failed (%m)");
				if (::ioctl(m_video_clip_fd, VIDEO_CONTINUE) < 0)
					eDebug("video: VIDEO_CONTINUE: %m");
				if (::ioctl(m_video_clip_fd, VIDEO_CLEAR_BUFFER) < 0)
					eDebug("video: VIDEO_CLEAR_BUFFER: %m");
				while(pos <= (s.st_size-4) && !(seq_end_avail = (!iframe[pos] && !iframe[pos+1] && iframe[pos+2] == 1 && iframe[pos+3] == 0xB7)))
					++pos;
				if ((iframe[3] >> 4) != 0xE) // no pes header
					write(m_video_clip_fd, pes_header, sizeof(pes_header));
				write(m_video_clip_fd, iframe, s.st_size);
				if (!seq_end_avail)
					write(m_video_clip_fd, seq_end, sizeof(seq_end));
				write(m_video_clip_fd, stuffing, 8192);
				m_showSinglePicTimer.start(150, true);
			}
			close(f);
		}
		else
		{
			eDebug("couldnt open %s", filename);
			return -1;
		}
	}
	else
	{
		eDebug("only show single pics on first decoder");
		return -1;
	}
	return 0;
}

void eTSMPEGDecoder::finishShowSinglePic()
{
	if (m_video_clip_fd >= 0)
	{
		if (ioctl(m_video_clip_fd, VIDEO_STOP, 0) < 0)
			eDebug("VIDEO_STOP failed (%m)");
		if (ioctl(m_video_clip_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_DEMUX) < 0)
				eDebug("VIDEO_SELECT_SOURCE DEMUX failed (%m)");
		close(m_video_clip_fd);
		m_video_clip_fd = -1;
	}
}

RESULT eTSMPEGDecoder::connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_video_event.connect(event));
	return 0;
}

void eTSMPEGDecoder::video_event(struct videoEvent event)
{
	/* emit */ m_video_event(event);
}
