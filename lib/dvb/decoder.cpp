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
#include <errno.h>

	/* these are quite new... */
#ifndef AUDIO_GET_PTS
#define AUDIO_GET_PTS              _IOR('o', 19, __u64)
#define VIDEO_GET_PTS              _IOR('o', 57, __u64)
#endif

DEFINE_REF(eDVBAudio);

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev): m_demux(demux), m_dev(dev)
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
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eWarning("audio: DMX_SET_PES_FILTER: %m");
		return -errno;
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eWarning("audio: DMX_START: %m");
		return -errno;
	}

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
		eWarning("audio: AUDIO_SET_BYPASS_MODE: %m");

	if (::ioctl(m_fd, AUDIO_PLAY) < 0)
		eWarning("audio: AUDIO_PLAY: %m");
	return 0;
}

void eDVBAudio::stop()
{
	if (::ioctl(m_fd, AUDIO_STOP) < 0)
		eWarning("audio: AUDIO_STOP: %m");
#if HAVE_DVB_API_VERSION > 2
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("audio: DMX_STOP: %m");
#endif
}

#if HAVE_DVB_API_VERSION < 3
void eDVBAudio::stopPid()
{
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("audio: DMX_STOP: %m");
}
#endif

void eDVBAudio::flush()
{
	if (::ioctl(m_fd, AUDIO_CLEAR_BUFFER) < 0)
		eDebug("audio: AUDIO_CLEAR_BUFFER: %m");
}

void eDVBAudio::freeze()
{
	if (::ioctl(m_fd, AUDIO_PAUSE) < 0)
		eDebug("video: AUDIO_PAUSE: %m");
}

void eDVBAudio::unfreeze()
{
	if (::ioctl(m_fd, AUDIO_CONTINUE) < 0)
		eDebug("video: AUDIO_CONTINUE: %m");
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
	if (::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val) < 0)
		eDebug("video: AUDIO_CHANNEL_SELECT: %m");
}

int eDVBAudio::getPTS(pts_t &now)
{
	return ::ioctl(m_fd, AUDIO_GET_PTS, &now);
}

eDVBAudio::~eDVBAudio()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBVideo);

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev): m_demux(demux), m_dev(dev)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/video%d", demux->adapter, dev);
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

int eDVBVideo::startPid(int pid, int type)
{
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;

	if (::ioctl(m_fd, VIDEO_SET_STREAMTYPE,
		type == MPEG4_H264 ? VIDEO_STREAMTYPE_MPEG4_H264 : VIDEO_STREAMTYPE_MPEG2) < 0)
		eWarning("video: VIDEO_SET_STREAMTYPE: %m");

	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = m_dev ? DMX_PES_VIDEO1 : DMX_PES_VIDEO0; /* FIXME */
	pes.flags    = 0;
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eWarning("video: DMX_SET_PES_FILTER: %m");
		return -errno;
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eWarning("video: DMX_START: %m");
		return -errno;
	}
	if (::ioctl(m_fd, VIDEO_PLAY) < 0)
		eWarning("video: VIDEO_PLAY: %m");
	return 0;
}

void eDVBVideo::stop()
{
#if HAVE_DVB_API_VERSION > 2
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
#endif
	eDebug("VIDEO_STOP");
	if (::ioctl(m_fd, VIDEO_STOP, 1) < 0)
		eWarning("video: VIDEO_STOP: %m");
}

#if HAVE_DVB_API_VERSION < 3
void eDVBVideo::stopPid()
{
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
}
#endif

void eDVBVideo::flush()
{
	if (::ioctl(m_fd, VIDEO_CLEAR_BUFFER) < 0)
		eDebug("video: VIDEO_CLEAR_BUFFER: %m");
}

void eDVBVideo::freeze()
{
	if (::ioctl(m_fd, VIDEO_FREEZE) < 0)
		eDebug("video: VIDEO_FREEZE: %m");
}

void eDVBVideo::unfreeze()
{
	if (::ioctl(m_fd, VIDEO_CONTINUE) < 0)
		eDebug("video: VIDEO_CONTINUE: %m");
}

int eDVBVideo::setSlowMotion(int repeat)
{
	m_is_slow_motion = repeat;
	return ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
}

int eDVBVideo::setFastForward(int skip)
{
	m_is_fast_forward = skip;
	return ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
}

int eDVBVideo::getPTS(pts_t &now)
{
	return ::ioctl(m_fd, VIDEO_GET_PTS, &now);
}

eDVBVideo::~eDVBVideo()
{
	if (m_sn)
		delete m_sn;
	if (m_is_slow_motion)
		setSlowMotion(0);
	if (m_is_fast_forward)
		setFastForward(0);
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

void eDVBVideo::video_event(int)
{
#if HAVE_DVB_API_VERSION >= 3
	struct video_event evt;
	if (::ioctl(m_fd, VIDEO_GET_EVENT, &evt) < 0)
		eDebug("VIDEO_GET_EVENT failed(%m)");
	else
	{
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
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eWarning("video: DMX_SET_PES_FILTER: %m");
		return -errno;
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eWarning("video: DMX_START: %m");
		return -errno;
	}
	return 0;
}

void eDVBPCR::stop()
{
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
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
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		eWarning("video: DMX_SET_PES_FILTER: %m");
		return -errno;
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		eWarning("video: DMX_START: %m");
		return -errno;
	}
	return 0;
}

void eDVBTText::stop()
{
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
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
	if (m_changed & changeAudio && m_audio)
		m_audio->stopPid();
	if (m_changed & changeVideo && m_video)
		m_video->stopPid();
	if (m_changed & changePCR && m_pcr)
	{
		m_pcr->stop();
		m_pcr=0;
	}
	if (m_changed & changeAudio && m_audio)
	{
		m_audio->stop();
		m_audio=0;
	}
	if (m_changed & changeVideo && m_video)
	{
		m_video->stop();
		m_video=0;
		m_video_event_conn=0;
	}
	if (m_changed & changePCR)
	{
		m_pcr = new eDVBPCR(m_demux);
		if (m_pcr->startPid(m_pcrpid))
		{
			eWarning("pcr: startpid failed!");
			res = -1;
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeVideo)
	{
		m_video = new eDVBVideo(m_demux, m_decoder);
		m_video->connectEvent(slot(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
		if (m_video->startPid(m_vpid))
		{
			eWarning("video: startpid failed!");
			res = -1;
		}
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeAudio)
	{
		m_audio = new eDVBAudio(m_demux, m_decoder);
		if (m_audio->startPid(m_apid, m_atype))
		{
			eWarning("audio: startpid failed!");
			res = -1;
		}
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
			{
				eWarning("pcr: startpid failed!");
				res = -1;
			}
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeVideo)
	{
		eDebug("VIDEO CHANGED (to %04x)", m_vpid);
		if (m_video)
		{
			eDebug("STOP");
			m_video->stop();
			m_video = 0;
			m_video_event_conn = 0;
		}
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			eDebug("new video");
			m_video = new eDVBVideo(m_demux, m_decoder);
			m_video->connectEvent(slot(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
			if (m_video->startPid(m_vpid, m_vtype))
			{
				eWarning("video: startpid failed!");
				res = -1;
			}
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
			{
				eWarning("audio: startpid failed!");
				res = -1;
			}
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
			{
				eWarning("text: startpid failed!");
				res = -1;
			}
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

eTSMPEGDecoder::eTSMPEGDecoder(eDVBDemux *demux, int decoder): m_demux(demux), m_changed(0), m_decoder(decoder)
{
	demux->connectEvent(slot(*this, &eTSMPEGDecoder::demux_event), m_demux_event_conn);
	m_is_ff = m_is_sm = m_is_trickmode = 0;
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	m_vpid = m_apid = m_pcrpid = pidNone;
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
		FILE *f = fopen(filename, "r");
		if (f)
		{
			int vfd = open("/dev/dvb/adapter0/video0", O_RDWR);
			if (vfd > 0)
			{
				fseek(f, 0, SEEK_END);
				int length = ftell(f);
				unsigned char *buffer = new unsigned char[length*2+9];
				if (ioctl(vfd, VIDEO_FAST_FORWARD, 1) < 0)
					eDebug("VIDEO_FAST_FORWARD failed (%m)");
				if (ioctl(vfd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) < 0)
					eDebug("VIDEO_SELECT_SOURCE MEMORY failed (%m)");
				if (ioctl(vfd, VIDEO_PLAY) < 0)
					eDebug("VIDEO_PLAY failed (%m)");
				int cnt=0;
				int pos=0;
				while(cnt<2)
				{
					int rd;
					fseek(f, 0, SEEK_SET);
					if (!cnt)
					{
						buffer[pos++]=0;
						buffer[pos++]=0;
						buffer[pos++]=1;
						buffer[pos++]=0xE0;
						buffer[pos++]=(length*2)>>8;
						buffer[pos++]=(length*2)&0xFF;
						buffer[pos++]=0x80;
						buffer[pos++]=0;
						buffer[pos++]=0;
					}
					while(1)
					{
						rd = fread(buffer+pos, 1, length, f);
						if (rd > 0)
							pos += rd;
						else
							break;
					}
					++cnt;
				}
				write(vfd, buffer, pos);
				usleep(75000);  // i dont like this.. but i dont have a better solution :(
				if (ioctl(vfd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_DEMUX) < 0)
					eDebug("VIDEO_SELECT_SOURCE DEMUX failed (%m)");
				if (ioctl(vfd, VIDEO_FAST_FORWARD, 0) < 0)
					eDebug("VIDEO_FAST_FORWARD failed (%m)");
				close(vfd);
				delete [] buffer;
			}
			fclose(f);
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

RESULT eTSMPEGDecoder::connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_video_event.connect(event));
	return 0;
}

void eTSMPEGDecoder::video_event(struct videoEvent event)
{
	/* emit */ m_video_event(event);
}
