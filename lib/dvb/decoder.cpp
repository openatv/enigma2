#include <config.h>
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
#define DMX_PES_VIDEO DMX_PES_VIDEO0
#define DMX_PES_AUDIO DMX_PES_AUDIO0
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

DEFINE_REF(eDVBAudio);

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev): m_demux(demux)
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
	
int eDVBAudio::startPid(int pid)
{	
	eDebug("setting audio pid to %x", pid);
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;
	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = DMX_PES_AUDIO;  // DMX_PES_AUDIO0
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
	
eDVBAudio::~eDVBAudio()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
}

DEFINE_REF(eDVBVideo);

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev): m_demux(demux)
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
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	m_fd_demux = ::open(filename, O_RDWR);
	if (m_fd_demux < 0)
		eWarning("%s: %m", filename);
}
	
int eDVBVideo::startPid(int pid)
{	
	eDebug("setting video pid to %x", pid);
	if ((m_fd < 0) || (m_fd_demux < 0))
		return -1;
	dmx_pes_filter_params pes;
	
	pes.pid      = pid;
	pes.input    = DMX_IN_FRONTEND;
	pes.output   = DMX_OUT_DECODER;
	pes.pes_type = DMX_PES_VIDEO;
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
	else
		eDebug("video ok");
	return 0;
}
	
void eDVBVideo::stop()
{
	if (::ioctl(m_fd, VIDEO_STOP) < 0)
		eWarning("video: VIDEO_STOP: %m");
#if HAVE_DVB_API_VERSION > 2
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
#endif
}

#if HAVE_DVB_API_VERSION < 3
void eDVBVideo::stopPid()
{
	if (::ioctl(m_fd_demux, DMX_STOP) < 0)
		eWarning("video: DMX_STOP: %m");
}
#endif

eDVBVideo::~eDVBVideo()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
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
	eDebug("setting pcr pid to %x", pid);
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

DEFINE_REF(eTSMPEGDecoder);

int eTSMPEGDecoder::setState()
{
	int res = 0;
	eDebug("changed %x", m_changed);
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
	}
	if (m_changed & changePCR)
	{
		m_pcr = new eDVBPCR(m_demux);
		if (m_pcr->startPid(m_pcrpid))
		{
			eWarning("video: startpid failed!");
			res = -1;
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeVideo)
	{
		m_video = new eDVBVideo(m_demux, 0);
		if (m_video->startPid(m_vpid))
		{
			eWarning("video: startpid failed!");
			res = -1;
		}
		m_changed &= ~changeVideo;
	}
	if (m_changed & changeAudio)
	{
		m_audio = new eDVBAudio(m_demux, 0);
		if (m_audio->startPid(m_apid))
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
				eWarning("video: startpid failed!");
				res = -1;
			}
		}
		m_changed &= ~changePCR;
	}
	if (m_changed & changeVideo)
	{
		if (m_video)
			m_video->stop();
		m_video = 0;
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			m_video = new eDVBVideo(m_demux, 0);
			if (m_video->startPid(m_vpid))
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
		if ((m_apid >= 0) && (m_apid < 0x1FFF))
		{
			m_audio = new eDVBAudio(m_demux, 0);
			if (m_audio->startPid(m_apid))
			{
				eWarning("audio: startpid failed!");
				res = -1;
			}
		}
		m_changed &= ~changeAudio;
	}
#endif
	return res;
}

eTSMPEGDecoder::eTSMPEGDecoder(eDVBDemux *demux, int decoder): m_demux(demux), m_changed(0)
{
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	m_vpid = m_apid = m_pcrpid = pidNone;
	m_changed = -1;
	setState();
}

RESULT eTSMPEGDecoder::setVideoPID(int vpid)
{
	if (m_vpid != vpid)
	{
		m_changed |= changeVideo;
		m_vpid = vpid;
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

RESULT eTSMPEGDecoder::setSyncPCR(int pcrpid)
{
	if (m_pcrpid != pcrpid)
	{
		m_changed |= changePCR;
		m_pcrpid = pcrpid;
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
	return -1;
}

RESULT eTSMPEGDecoder::unfreeze()
{
	return -1;
}

RESULT eTSMPEGDecoder::setSinglePictureMode(int when)
{
	return -1;
}

RESULT eTSMPEGDecoder::setPictureSkipMode(int what)
{
	return -1;
}

RESULT eTSMPEGDecoder::setSlowMotion(int repeat)
{
	return -1;
}

RESULT eTSMPEGDecoder::setZoom(int what)
{
	return -1;
}
