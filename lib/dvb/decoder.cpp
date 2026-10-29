#include <lib/base/cfile.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/eenv.h>
#include <lib/base/nconfig.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/wrappers.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/hevc_hdr_detector.h>
#ifdef DREAMNEXTGEN
#include <lib/dvb/videoswdemux.h>
#endif
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
#include <pthread.h>
#include <time.h>
#include <vector>

#include <lib/dvb/fccdecoder.h>
#ifdef DREAMNEXTGEN
#include <lib/dvb/avsync_core.h>
#endif

#ifndef VIDEO_SOURCE_HDMI
#define VIDEO_SOURCE_HDMI 2
#endif
#ifndef AUDIO_SOURCE_HDMI
#define AUDIO_SOURCE_HDMI 2
#endif
#ifndef AUDIO_GET_PTS
#define AUDIO_GET_PTS _IOR('o', 19, __u64)
#endif
#ifndef VIDEO_GET_FRAME_RATE
#define VIDEO_GET_FRAME_RATE _IOR('o', 56, unsigned int)
#endif

#ifdef DREAMNEXTGEN
struct dream_video_frame
{
	uint64_t pts;
	ssize_t bytes[8];
	const uint8_t *data[8];
	int is_phys_addr[8];
};

#define DREAM_VIDEO_SET_FRAME _IOWR('o', 64, struct dream_video_frame)

#define ASPECT_4_3      ((3<<8)/4)
#define ASPECT_16_9     ((9<<8)/16)
#endif

DEFINE_REF(eDVBAudio);

int eDVBAudio::m_debug = -1;

eDVBAudio::eDVBAudio(eDVBDemux *demux, int dev)
	:m_demux(demux), m_dev(dev), m_bypass(-1)
{
	char filename[128];
#ifdef DREAMNEXTGEN
	/* the SoC has no audio decoder; dreamaudiod decodes for this device */
	sprintf(filename, "/dev/dvb/adapter%d/dreamaudio%d", demux ? demux->adapter : 0, dev);
#else
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", demux ? demux->adapter : 0, dev);
#endif
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

	if (eDVBAudio::m_debug < 0)
		eDVBAudio::m_debug = eSimpleConfig::getBool("config.crash.debugDVB", false) ? 1 : 0;

}

int eDVBAudio::startPid(int pid, int type)
{
	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes = {};
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
	 	pes.flags    = 0;
		if(eDVBAudio::m_debug)
			eDebugNoNewLineStart("[eDVBAudio%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			if(eDVBAudio::m_debug)
				eDebugNoNewLine("failed: %m");
			return -errno;
		}
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLine("ok");
			eDebugNoNewLineStart("[eDVBAudio%d] DEMUX_START ", m_dev);
		}
		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			if(eDVBAudio::m_debug)
				eDebugNoNewLine("failed: %m");
			return -errno;
		}
		if(eDVBAudio::m_debug)
			eDebugNoNewLine("ok");
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

		if (m_bypass != bypass) {

			if(eDVBAudio::m_debug)
			{
				eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_SET_BYPASS bypass=%d ", m_dev, bypass);
				if (::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass) < 0)
					eDebugNoNewLine("failed: %m");
				else
					eDebugNoNewLine("ok");
			}
			else
				::ioctl(m_fd, AUDIO_SET_BYPASS_MODE, bypass);
			freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
			m_bypass = bypass;

		}


		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_PLAY ", m_dev);
			if (::ioctl(m_fd, AUDIO_PLAY) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_PLAY);

	}
	return 0;
}

void eDVBAudio::stop()
{
	if (m_fd >= 0)
	{
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_STOP ", m_dev);
			if (::ioctl(m_fd, AUDIO_STOP) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_STOP);

	}
	if (m_fd_demux >= 0)
	{
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] DEMUX_STOP ", m_dev);
			if (::ioctl(m_fd_demux, DMX_STOP) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd_demux, DMX_STOP);
	}
}

void eDVBAudio::flush()
{
	if (m_fd >= 0)
	{
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CLEAR_BUFFER ", m_dev);
			if (::ioctl(m_fd, AUDIO_CLEAR_BUFFER) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_CLEAR_BUFFER);

	}
}

void eDVBAudio::freeze()
{
	if (m_fd >= 0)
	{
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_PAUSE ", m_dev);
			if (::ioctl(m_fd, AUDIO_PAUSE) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_PAUSE);
	}
}

void eDVBAudio::unfreeze()
{
	if (m_fd >= 0)
	{
		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CONTINUE ", m_dev);
			if (::ioctl(m_fd, AUDIO_CONTINUE) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_CONTINUE);
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

		if(eDVBAudio::m_debug)
		{
			eDebugNoNewLineStart("[eDVBAudio%d] AUDIO_CHANNEL_SELECT %d ", m_dev, val);
			if (::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, AUDIO_CHANNEL_SELECT, val);
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
	if(eDVBAudio::m_debug)
		eDebug("[eDVBAudio%d] destroy", m_dev);
}

DEFINE_REF(eDVBVideo);

int eDVBVideo::m_close_invalidates_attributes = -1;
int eDVBVideo::m_debug = -1;

#ifdef DREAMNEXTGEN
/* Serialise video-device ioctls — concurrent VIDEO_* on the AMLogic
 * vdec triggers kernel vdec_disconnect timeouts (main thread spin). */
static pthread_mutex_t s_video_ioctl_lock = PTHREAD_MUTEX_INITIALIZER;
#endif

eDVBVideo::eDVBVideo(eDVBDemux *demux, int dev, bool fcc_enable)
	: m_demux(demux), m_dev(dev), m_fcc_enable(fcc_enable),
	m_width(-1), m_height(-1), m_framerate(-1), m_aspect(-1), m_progressive(-1), m_gamma(-1), m_streamtype(-1),
	m_hdr_detector(0), m_hdr_gamma(-1), m_driver_gamma(-1), m_hdr_gamma_authoritative(false), m_gamma_from_driver_event(false)
#ifdef DREAMNEXTGEN
	, m_sysfs_size_event_sent(false), m_sysfs_poll_attempts(0)
#endif
{

	if (eDVBVideo::m_debug < 0)
		eDVBVideo::m_debug = eSimpleConfig::getBool("config.crash.debugDVB", false) ? 1 : 0;

	char filename[128] = {};
	sprintf(filename, "/dev/dvb/adapter%d/video%d", demux ? demux->adapter : 0, dev);
	m_fd = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd < 0)
		eWarning("[eDVBVideo] %s: %m", filename);
	else
	{
		if(eDVBVideo::m_debug)
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
		{
			if(eDVBVideo::m_debug)
				eDebug("[eDVBVideo] demux device: %s", filename);
		}
	}
	else
	{
		m_fd_demux = -1;
	}

	if (demux && m_dev == 0)
	{
		m_hdr_detector = new eHEVCHDRDetector(demux, sigc::mem_fun(*this, &eDVBVideo::hdr_gamma_detected));
		eDebug("[eHEVCHDRDetector] attached to video decoder %d (FCC=%d)", m_dev, m_fcc_enable);
	}

#ifndef DREAMNEXTGEN
	if (m_fd >= 0)
	{
		::ioctl(m_fd, VIDEO_SELECT_SOURCE, demux ? VIDEO_SOURCE_DEMUX : VIDEO_SOURCE_HDMI);
	}
#else
	/* the hardware demux only feeds the first decoder (as DreamOS) */
	if (demux && m_dev > 0 && m_fd >= 0)
	{
		if (m_fd_demux >= 0)
			::close(m_fd_demux);
		m_fd_demux = -1;
		/* a demux takes one tap per type; the mosaic decoders 2..5 run
		 * without the main and PiP decoder and use all four types */
		static const dmx_pes_type_t tapType[] = { DMX_PES_VIDEO0, DMX_PES_VIDEO1, DMX_PES_VIDEO2, DMX_PES_VIDEO3 };
		m_sw_demux = new eDVBVideoSwDemux(demux, m_fd, tapType[m_dev & 3], m_dev >= 2);
	}
#endif

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

#ifdef DREAMNEXTGEN
	// AMLogic doesn't reliably send VIDEO_EVENTs. Poll until all initial
	// video attributes have settled, then leave the main loop alone.
	m_sysfs_poll_timer = eTimer::create(eApp);
	CONNECT(m_sysfs_poll_timer->timeout, eDVBVideo::sysfs_poll_timeout);
	if (m_fd >= 0)
		m_sysfs_poll_timer->start(500, true);
#endif
}

// not finally values i think.. !!
#define VIDEO_STREAMTYPE_MPEG2 0
#define VIDEO_STREAMTYPE_MPEG4_H264 1
#define VIDEO_STREAMTYPE_VC1 3
#define VIDEO_STREAMTYPE_MPEG4_Part2 4
#ifdef DREAMNEXTGEN
/* meson64 passes a stream type it does not map on as the decoder format */
#define VIDEO_STREAMTYPE_VC1_SM 17
#define VIDEO_STREAMTYPE_MPEG1 0
#else
#define VIDEO_STREAMTYPE_VC1_SM 5
#define VIDEO_STREAMTYPE_MPEG1 6
#endif
#ifdef DREAMBOX
#define VIDEO_STREAMTYPE_H265_HEVC 22
#else
#define VIDEO_STREAMTYPE_H265_HEVC 7
#endif
#ifdef DREAMNEXTGEN
#define VIDEO_STREAMTYPE_AVS 7
#define VIDEO_STREAMTYPE_AVS2 15
#else
#define VIDEO_STREAMTYPE_AVS 16
#define VIDEO_STREAMTYPE_AVS2 40
#endif

int eDVBVideo::startPid(int pid, int type)
{
	if (m_hdr_detector)
		m_hdr_detector->stop();
	m_gamma = -1;
	m_hdr_gamma = -1;
	m_driver_gamma = -1;
	m_hdr_gamma_authoritative = false;
	m_gamma_from_driver_event = false;

	if (type == H265_HEVC)
		eDebug("[eHEVCHDRDetector] HEVC start request decoder=%d PID=%04x FCC=%d detector=%s",
			m_dev, pid, m_fcc_enable, m_hdr_detector ? "yes" : "no");

	if (m_fcc_enable)
	{
		if (type == H265_HEVC && m_hdr_detector)
			m_hdr_detector->start(pid);
		return 0;
	}

#ifdef DREAMNEXTGEN
	/*
	 * The PiP layer cannot line skip compressed 4K frames: the PiP decoder
	 * gets a quarter size double write buffer. The decoder reads the module
	 * parameter when it is created.
	 */
	static const char *doubleWriteMode = "/sys/module/amvdec_h265/parameters/double_write_mode";
	int doubleWriteRestore = -1;
	if (m_dev > 0 && type == H265_HEVC && m_fd >= 0 && CFile::parseInt(&doubleWriteRestore, doubleWriteMode) == 0)
		CFile::writeInt(doubleWriteMode, 2);
	else
		doubleWriteRestore = -1;
#endif

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
		case AVS2:
			streamtype = VIDEO_STREAMTYPE_AVS2;
			break;
		}

		if (m_streamtype != streamtype) {
#ifdef DREAMNEXTGEN
			pthread_mutex_lock(&s_video_ioctl_lock);
#endif
			if(eDVBVideo::m_debug)
			{
				eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_SET_STREAMTYPE %d - ", m_dev, streamtype);
				if (::ioctl(m_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
					eDebugNoNewLine("failed: %m");
				else
					eDebugNoNewLine("ok");
			}
			else
				::ioctl(m_fd, VIDEO_SET_STREAMTYPE, streamtype);
#ifdef DREAMNEXTGEN
			pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
			m_streamtype = streamtype;
		}
	}

	if (m_fd_demux >= 0)
	{
		dmx_pes_filter_params pes = {};
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
		pes.flags    = 0;

		if(eDVBVideo::m_debug)
			eDebugNoNewLineStart("[eDVBVideo%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
		if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
		{
			if(eDVBVideo::m_debug)
				eDebugNoNewLine("failed: %m");
			return -errno;
		}
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLine("ok");
			eDebugNoNewLineStart("[eDVBVideo%d] DEMUX_START ", m_dev);
		}

		if (::ioctl(m_fd_demux, DMX_START) < 0)
		{
			if(eDVBVideo::m_debug)
				eDebugNoNewLine("failed: %m");
			return -errno;
		}
		if(eDVBVideo::m_debug)
			eDebugNoNewLine("ok");
	}

	if (m_fd >= 0)
	{
		freeze();  // why freeze here?!? this is a problem when only a pid change is requested... because of the unfreeze logic in Decoder::setState
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_PLAY ", m_dev);
			if (::ioctl(m_fd, VIDEO_PLAY) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, VIDEO_PLAY);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif

	}
#ifdef DREAMNEXTGEN
	if (doubleWriteRestore >= 0)
		CFile::writeInt(doubleWriteMode, doubleWriteRestore);
	if (m_sw_demux)
	{
		eDVBVideoSwDemux::Codec codec = eDVBVideoSwDemux::OTHER;
		if (type == MPEG2 || type == MPEG1)
			codec = eDVBVideoSwDemux::MPEG2;
		else if (type == MPEG4_H264)
			codec = eDVBVideoSwDemux::H264;
		else if (type == H265_HEVC)
			codec = eDVBVideoSwDemux::HEVC;
		if (m_sw_demux->start(pid, codec, m_pcrpid) < 0)
			return -1;
	}
#endif
	if (type == H265_HEVC && m_hdr_detector)
		m_hdr_detector->start(pid);
	return 0;
}

void eDVBVideo::stop()
{
	if (m_hdr_detector)
		m_hdr_detector->stop();

	if (m_fcc_enable)
		return;

#ifdef DREAMNEXTGEN
	if (m_sw_demux)
		m_sw_demux->stop();
#endif
	if (m_fd_demux >= 0)
	{
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] DEMUX_STOP  ", m_dev);
			if (::ioctl(m_fd_demux, DMX_STOP) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd_demux, DMX_STOP);
	}

	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_STOP ", m_dev);
			if (::ioctl(m_fd, VIDEO_STOP, 1) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, VIDEO_STOP, 1);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
		clearLastFrame();
	}
}

void eDVBVideo::clearLastFrame()
{
#if defined(HWDM900) || defined(HWDM920) || defined(HWDM820) || defined(HWDM7080)
	// These drivers retain the displayed frame despite VIDEO_STOP(1).
	// Replace it before releasing the main decoder, so radio and services
	// without decodable video cannot expose the previous channel's picture.
	if (m_dev != 0 || !m_demux || m_demux->adapter != 0)
		return;

	static const std::vector<unsigned char> blackFrame = []() {
		std::vector<unsigned char> frame;
		CFile file(eEnv::resolve("${datadir}/enigma2/black.mvi"), "rb");
		struct stat status = {};
		if (!file || fstat(fileno(file), &status) || status.st_size < 6 || status.st_size > 65536)
		{
			eWarning("[eDVBVideo] Cannot load black still picture");
			return frame;
		}
		frame.resize(status.st_size);
		if (fread(frame.data(), 1, frame.size(), file) != frame.size())
		{
			eWarning("[eDVBVideo] Cannot read black still picture");
			frame.clear();
		}
		else if ((frame[3] >> 4) == 0xE)
			frame[4] = frame[5] = 0;
		return frame;
	}();
	if (blackFrame.empty())
		return;

	const unsigned char pesHeader[] = {0, 0, 1, 0xE0, 0, 0, 0x80, 0x80, 5, 0x21, 0, 1, 0, 1};
	const unsigned char sequenceEnd[] = {0, 0, 1, 0xB7};
	const unsigned char stuffing[8192] = {};
	bool started = false;
	if (::ioctl(m_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_MEMORY) == 0 &&
		::ioctl(m_fd, VIDEO_SET_STREAMTYPE, VIDEO_STREAMTYPE_MPEG2) == 0 &&
		::ioctl(m_fd, VIDEO_PLAY) == 0)
	{
		started = true;
		m_streamtype = VIDEO_STREAMTYPE_MPEG2;
		bool written = ::ioctl(m_fd, VIDEO_CONTINUE) == 0 && ::ioctl(m_fd, VIDEO_CLEAR_BUFFER) == 0;
		written = written && ((blackFrame[3] >> 4) == 0xE ||
			writeAll(m_fd, pesHeader, sizeof(pesHeader)) == sizeof(pesHeader));
		written = written && writeAll(m_fd, blackFrame.data(), blackFrame.size()) == (ssize_t)blackFrame.size();
		written = written && writeAll(m_fd, sequenceEnd, sizeof(sequenceEnd)) == sizeof(sequenceEnd);
		written = written && writeAll(m_fd, stuffing, sizeof(stuffing)) == sizeof(stuffing);
		if (written)
		{
			// Match the existing still-picture decoder interval. Keep ownership
			// until completion; a timer must never stop the following service.
			struct timespec remaining = {0, 150000000};
			while (nanosleep(&remaining, &remaining) && errno == EINTR) {}
		}
		else
			eWarning("[eDVBVideo] Cannot feed black still picture: %m");
	}
	else
		eWarning("[eDVBVideo] Cannot start black still picture: %m");
	if (started && ::ioctl(m_fd, VIDEO_STOP, 0) < 0)
		eWarning("[eDVBVideo] Cannot stop black still picture: %m");
	if (::ioctl(m_fd, VIDEO_SELECT_SOURCE, VIDEO_SOURCE_DEMUX) < 0)
		eWarning("[eDVBVideo] Cannot restore video demux source: %m");
#endif
}

void eDVBVideo::flush()
{
	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_CLEAR_BUFFER ", m_dev);
			if (::ioctl(m_fd, VIDEO_CLEAR_BUFFER) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, VIDEO_CLEAR_BUFFER);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
	}
}

void eDVBVideo::freeze()
{
	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_FREEZE ", m_dev);
			if (::ioctl(m_fd, VIDEO_FREEZE) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, VIDEO_FREEZE);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
	}
}

void eDVBVideo::unfreeze()
{
	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_CONTINUE ", m_dev);
			if (::ioctl(m_fd, VIDEO_CONTINUE) < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			::ioctl(m_fd, VIDEO_CONTINUE);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
	}
}

int eDVBVideo::setSlowMotion(int repeat)
{
	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		int ret;
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_SLOWMOTION %d ", m_dev, repeat);
			ret = ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
			if (ret < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			ret = ::ioctl(m_fd, VIDEO_SLOWMOTION, repeat);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
		return ret;
	}
	return 0;
}

#ifdef DREAMNEXTGEN
void eDVBVideo::playRecovery()
{
	if (m_fd < 0) return;
	pthread_mutex_lock(&s_video_ioctl_lock);
	if (eDVBVideo::m_debug) {
		eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_PLAY (recovery) ", m_dev);
		if (::ioctl(m_fd, VIDEO_PLAY) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	} else
		::ioctl(m_fd, VIDEO_PLAY);
	pthread_mutex_unlock(&s_video_ioctl_lock);
}

void eDVBVideo::dnxtPostFastForward()
{
	/* DMX_STOP + VIDEO_CLEAR_BUFFER + DMX_START commits the kernel
	 * decoder_set_trickmode change to the screen. */
	if (m_fd_demux < 0 || m_fd < 0) return;
	pthread_mutex_lock(&s_video_ioctl_lock);
	if (eDVBVideo::m_debug)
		eDebug("[eDVBVideo%d] dnxtPostFastForward: DMX_STOP+VIDEO_CLEAR_BUFFER+DMX_START", m_dev);
	::ioctl(m_fd_demux, DMX_STOP);
	::ioctl(m_fd, VIDEO_CLEAR_BUFFER);
	::ioctl(m_fd_demux, DMX_START);
	pthread_mutex_unlock(&s_video_ioctl_lock);
}
#endif

int eDVBVideo::setFastForward(int skip)
{
	if (m_fd >= 0)
	{
#ifdef DREAMNEXTGEN
		pthread_mutex_lock(&s_video_ioctl_lock);
#endif
		int ret;
		if(eDVBVideo::m_debug)
		{
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_FAST_FORWARD %d ", m_dev, skip);
			ret = ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
			if (ret < 0)
				eDebugNoNewLine("failed: %m");
			else
				eDebugNoNewLine("ok");
		}
		else
			ret = ::ioctl(m_fd, VIDEO_FAST_FORWARD, skip);
#ifdef DREAMNEXTGEN
		pthread_mutex_unlock(&s_video_ioctl_lock);
#endif
		return ret;
	}
	return 0;
}

int eDVBVideo::getPTS(pts_t &now)
{
	if (m_fd >= 0)
	{
		if(eDVBVideo::m_debug)
		{
			int ret = ::ioctl(m_fd, VIDEO_GET_PTS, &now);
			if (ret < 0)
				eDebug("[eDVBVideo%d] VIDEO_GET_PTS failed: %m", m_dev);
			return ret;
		}
		return ::ioctl(m_fd, VIDEO_GET_PTS, &now);
	}
	return 0;
}

eDVBVideo::~eDVBVideo()
{
	delete m_hdr_detector;
	m_hdr_detector = 0;

#ifdef DREAMNEXTGEN
	if (m_sysfs_poll_timer)
		m_sysfs_poll_timer->stop();
	delete m_sw_demux;
	m_sw_demux = nullptr;
#endif
	if (m_fd >= 0)
		::close(m_fd);
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	if(eDVBVideo::m_debug)
		eDebug("[eDVBVideo%d] destroy", m_dev);
}

void eDVBVideo::publish_gamma(int gamma)
{
	if (gamma < 0 || gamma > 3 || gamma == m_gamma)
		return;

	struct iTSMPEGDecoder::videoEvent event = {};
	event.type = iTSMPEGDecoder::videoEvent::eventGammaChanged;
	m_gamma = event.gamma = gamma;
	/* emit */ m_event(event);
}

int eDVBVideo::read_driver_gamma()
{
	char tmp[64] = {};
	sprintf(tmp, "/proc/stb/vmpeg/%d/gamma", m_dev);
	int driver_gamma = -1;
	CFile::parseIntHex(&driver_gamma, tmp);
	if (driver_gamma >= 0 && driver_gamma <= 3)
		m_driver_gamma = driver_gamma;
	return m_driver_gamma;
}

void eDVBVideo::hdr_gamma_detected(int gamma)
{
	if (gamma != 0 && gamma != 2 && gamma != 3)
		return;

	if (!m_gamma_from_driver_event && m_driver_gamma < 0)
		read_driver_gamma();

	m_hdr_gamma = gamma;
	m_hdr_gamma_authoritative = gamma == 2 || gamma == 3;

	/* A valid native HDR/HLG value remains the highest-confidence source. */
	if (m_driver_gamma >= 2)
		return;

	if (m_hdr_gamma_authoritative)
	{
		if (eDVBVideo::m_debug)
			eDebug("[eDVBVideo%d] HEVC bitstream gamma %d", m_dev, gamma);
		publish_gamma(gamma);
	}
	else if (!m_gamma_from_driver_event && m_driver_gamma < 1)
	{
		/* Do not replace the native 'traditional HDR' value, which the parser cannot infer. */
		if (eDVBVideo::m_debug)
			eDebug("[eDVBVideo%d] HEVC bitstream gamma 0 (SDR fallback)", m_dev);
		publish_gamma(0);
	}
}

void eDVBVideo::video_event(int)
{
	while (m_fd >= 0)
	{
		int retval;
		pollfd pfd[1] = {};
		pfd[0].fd = m_fd;
		pfd[0].events = POLLPRI;
		retval = ::poll(pfd, 1, 0);
		if (retval < 0 && errno == EINTR) continue;
		if (retval <= 0) break;
		struct video_event evt = {};
		if(eDVBVideo::m_debug)
			eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_GET_EVENT ", m_dev);
		if (::ioctl(m_fd, VIDEO_GET_EVENT, &evt) < 0)
		{
			if(eDVBVideo::m_debug)
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
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("SIZE_CHANGED %dx%d aspect %d\n", m_width, m_height, m_aspect);
				/* emit */ m_event(event);
			}
			else if (evt.type == VIDEO_EVENT_FRAME_RATE_CHANGED)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventFrameRateChanged;
				m_framerate = event.framerate = evt.u.frame_rate;
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("FRAME_RATE_CHANGED %d fps\n", m_framerate);
				/* emit */ m_event(event);
			}
			else if (evt.type == 16 /*VIDEO_EVENT_PROGRESSIVE_CHANGED*/)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
				m_progressive = event.progressive = evt.u.frame_rate;
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("PROGRESSIVE_CHANGED %d\n", m_progressive);
				/* emit */ m_event(event);
			}
			else if (evt.type == 17 /*VIDEO_EVENT_GAMMA_CHANGED*/)
			{
				/*
				 * Possible gamma values
				 * 0: Traditional gamma - SDR luminance range
				 * 1: Traditional gamma - HDR luminance range
				 * 2: SMPTE ST2084 (aka HDR10)
				 * 3: Hybrid Log-gamma
				 */
				const int driver_gamma = evt.u.frame_rate;
				if (driver_gamma >= 0 && driver_gamma <= 3)
				{
					m_driver_gamma = driver_gamma;
					m_gamma_from_driver_event = true;
					int gamma = driver_gamma;
					if (m_hdr_gamma_authoritative && m_hdr_gamma >= 2 && gamma < 2)
						gamma = m_hdr_gamma;
					if(eDVBVideo::m_debug)
						eDebugNoNewLine("GAMMA_CHANGED %d\n", gamma);
					publish_gamma(gamma);
					if (m_hdr_detector && driver_gamma >= 2)
						m_hdr_detector->stop();
				}
				else if(eDVBVideo::m_debug)
					eDebugNoNewLine("invalid GAMMA_CHANGED %d\n", driver_gamma);
			}
#ifdef DREAMNEXTGEN
			else if (evt.type == 32 /*PTS_VALID*/)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
				m_progressive = event.progressive = evt.u.frame_rate;
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("PTS_VALID %d\n", m_progressive);
				/* emit */ m_event(event);
			}
			else if (evt.type == 64 /*VIDEO_DISCONTINUE_DETECTED*/)
			{
				struct iTSMPEGDecoder::videoEvent event;
				event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
				m_progressive = event.progressive = evt.u.frame_rate;
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("VIDEO_DISCONTINUE_DETECTED %d\n", m_progressive);
				if (m_fd >= 0)
				{
					flush();
					if(eDVBVideo::m_debug)
					{
						eDebugNoNewLineStart("[eDVBVideo%d] VIDEO_PLAY ", m_dev);
						if (::ioctl(m_fd, VIDEO_PLAY) < 0)
							eDebugNoNewLine("failed: %m");
						else
							eDebugNoNewLine("ok");
					}
					else
						::ioctl(m_fd, VIDEO_PLAY);
				}
				/* emit */ m_event(event);
			}
#endif
			else
			{
				if(eDVBVideo::m_debug)
					eDebugNoNewLine("unhandled DVBAPI Video Event %d\n", evt.type);
			}
		}
	}
}

#ifdef DREAMNEXTGEN
void eDVBVideo::sysfs_poll_timeout()
{
	int new_width = -1, new_height = -1, new_framerate = -1, new_progressive = -1;
	if (m_sysfs_poll_attempts < 10)
		++m_sysfs_poll_attempts;
	
	CFile::parseInt(&new_width, "/sys/class/video/frame_width");
	CFile::parseInt(&new_height, "/sys/class/video/frame_height");
	CFile::parseInt(&new_framerate, "/proc/stb/vmpeg/0/frame_rate");
	CFile::parseInt(&new_progressive, "/proc/stb/vmpeg/0/progressive");
	
	bool changed = false;
	
	// Always publish the first valid size. readApiSize() can populate the same
	// values before listeners are connected, which otherwise suppresses the
	// only size event on AMLogic.
	if (new_width > 0 && new_height > 0 &&
		(!m_sysfs_size_event_sent || new_width != m_width || new_height != m_height))
	{
		m_width = new_width;
		m_height = new_height;
		
		struct iTSMPEGDecoder::videoEvent event;
		event.type = iTSMPEGDecoder::videoEvent::eventSizeChanged;
		event.width = m_width;
		event.height = m_height;
		event.aspect = m_aspect;
		/* emit */ m_event(event);
		m_sysfs_size_event_sent = true;
		changed = true;
	}
	
	// Check if framerate changed
	if (new_framerate > 0 && new_framerate != m_framerate)
	{
		m_framerate = new_framerate;
		
		struct iTSMPEGDecoder::videoEvent event;
		event.type = iTSMPEGDecoder::videoEvent::eventFrameRateChanged;
		event.framerate = m_framerate;
		/* emit */ m_event(event);
		changed = true;
	}
	
	// Check if progressive changed
	if ((new_progressive == 0 || new_progressive == 1) && new_progressive != m_progressive)
	{
		m_progressive = new_progressive;
		
		struct iTSMPEGDecoder::videoEvent event;
		event.type = iTSMPEGDecoder::videoEvent::eventProgressiveChanged;
		event.progressive = m_progressive;
		/* emit */ m_event(event);
		changed = true;
	}
	
	// Use this poll's values, not cached attributes: a temporary read failure
	// must not stop detection before the decoder supplies complete data.
	const bool attributes_ready = new_width > 0 && new_height > 0 && new_framerate > 0 &&
		(new_progressive == 0 || new_progressive == 1);
	if (m_sysfs_size_event_sent && attributes_ready && !changed)
	{
		m_sysfs_poll_timer->stop();
	}
	else
	{
		// Slow down after the initial five seconds, but keep detecting delayed
		// pictures and metadata until this decoder is released. No busy loop.
		m_sysfs_poll_timer->start(m_sysfs_poll_attempts < 10 ? 500 : 2000, true);
	}
}
#endif

RESULT eDVBVideo::connectEvent(const sigc::slot<void(struct iTSMPEGDecoder::videoEvent)> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

int eDVBVideo::readApiSize(int fd, int &xres, int &yres, int &aspect)
{
	video_size_t size = {};
	if (!::ioctl(fd, VIDEO_GET_SIZE, &size))
	{
		xres = size.w;
		yres = size.h;
#ifdef DREAMNEXTGEN
		//eDebug("[eDVBVideo] readAPIsize xres - %d yres - %d", xres, yres);
#endif
		aspect = size.aspect_ratio == 0 ? 2 : 3;  // convert dvb api to etsi
		return 0;
	}
#ifdef DREAMNEXTGEN
	else
	{
		int w, h;
		CFile::parseInt(&w, "/sys/class/video/frame_width");
		CFile::parseInt(&h, "/sys/class/video/frame_height");
		xres=w;
		yres=h;
		//eDebug("[eDVBVideo] ReadAPIsize xres - %d yres - %d", w, h);
		aspect = 2;	
		return 0;
	}
#endif
	return -1;
}

int eDVBVideo::getWidth()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
#ifdef DREAMNEXTGEN
		int m_width = -1;
		CFile::parseInt(&m_width, "/sys/class/video/frame_width");
		//eDebug("[eTSMPEGDecoder] m_width - %d", m_width);
#endif
		if (m_width == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
	}
#ifdef DREAMNEXTGEN
	// eDebug("[eDVBVideo] m_width - %d", m_width);
#endif
	return m_width;
}

int eDVBVideo::getHeight()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
#ifdef DREAMNEXTGEN
		int m_height = -1;
		CFile::parseInt(&m_height, "/sys/class/video/frame_height");
		//eDebug("[eTSMPEGDecoder] m_height - %d", m_height);
#endif
		if (m_height == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
	}
#ifdef DREAMNEXTGEN
	//eDebug("[eDVBVideo] m_height - %d", m_height);
#endif
	return m_height;
}

int eDVBVideo::getAspect()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
#ifdef DREAMNEXTGEN
		int m_aspect = -1;
		CFile::parseIntHex(&m_aspect, "/sys/class/video/frame_aspect_ratio");
#endif
		if (m_aspect == -1)
			readApiSize(m_fd, m_width, m_height, m_aspect);
#ifdef DREAMNEXTGEN
	m_aspect = 2;
#endif
	}
#ifdef DREAMNEXTGEN
	//eDebug("[eDVBVideo] m_aspect - %d", m_aspect);
#endif
	return m_aspect;
}

int eDVBVideo::getProgressive()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_progressive == -1)
		{
			char tmp[64] = {};
			sprintf(tmp, "/proc/stb/vmpeg/%d/progressive", m_dev);
#ifdef DREAMNEXTGEN
			CFile::parseInt(&m_progressive, tmp);
#else
			CFile::parseIntHex(&m_progressive, tmp);
#endif
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
#ifdef DREAMNEXTGEN
	//eDebug("[eDVBVideo] m_framerate - %d", m_framerate);
#endif
	return m_framerate;
}

int eDVBVideo::getGamma()
{
	/* when closing the video device invalidates the attributes, we can rely on VIDEO_EVENTs */
	if (!m_close_invalidates_attributes)
	{
		if (m_gamma == -1)
		{
			const int driver_gamma = read_driver_gamma();
			if (driver_gamma >= 0)
			{
				m_gamma = driver_gamma;
				if (m_hdr_detector && driver_gamma >= 2)
					m_hdr_detector->stop();
			}
		}
	}
	return m_gamma;
}

DEFINE_REF(eDVBPCR);

int eDVBPCR::m_debug = -1;

eDVBPCR::eDVBPCR(eDVBDemux *demux, int dev): m_demux(demux), m_dev(dev)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd_demux < 0)
		eWarning("[eDVBPCR] %s: %m", filename);

	if (eDVBPCR::m_debug < 0)
		eDVBPCR::m_debug = eSimpleConfig::getBool("config.crash.debugDVB", false) ? 1 : 0;

}

int eDVBPCR::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes = {};
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
	pes.flags    = 0;
	if(eDVBPCR::m_debug)
		eDebugNoNewLineStart("[eDVBPCR%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		if(eDVBPCR::m_debug)
			eDebugNoNewLine("failed: %m");
		return -errno;
	}
	if(eDVBPCR::m_debug)
	{
		eDebugNoNewLine("ok");
		eDebugNoNewLineStart("[eDVBPCR%d] DEMUX_START ", m_dev);
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		if(eDVBPCR::m_debug)
			eDebugNoNewLine("failed: %m");
		return -errno;
	}
	if(eDVBPCR::m_debug)
		eDebugNoNewLine("ok");
	return 0;
}

void eDVBPCR::stop()
{
	if(eDVBPCR::m_debug)
	{
		eDebugNoNewLineStart("[eDVBPCR%d] DEMUX_STOP ", m_dev);
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
	else
		::ioctl(m_fd_demux, DMX_STOP);
}

#ifdef DREAMNEXTGEN
int eDVBPCR::start()
{
	if (m_fd_demux < 0)
		return -1;
	if (::ioctl(m_fd_demux, DMX_START) < 0)
		return -errno;
	return 0;
}
#endif

eDVBPCR::~eDVBPCR()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	if(eDVBPCR::m_debug)
		eDebug("[eDVBPCR%d] destroy", m_dev);
}

DEFINE_REF(eDVBTText);

int eDVBTText::m_debug = -1;

eDVBTText::eDVBTText(eDVBDemux *demux, int dev)
    :m_demux(demux), m_dev(dev)
{
	char filename[128] = {};
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	m_fd_demux = ::open(filename, O_RDWR | O_CLOEXEC);
	if (m_fd_demux < 0)
		eWarning("[eDVBText] %s: %m", filename);
	if (eDVBTText::m_debug < 0)
		eDVBTText::m_debug = eSimpleConfig::getBool("config.crash.debugDVB", false) ? 1 : 0;
}

int eDVBTText::startPid(int pid)
{
	if (m_fd_demux < 0)
		return -1;
	dmx_pes_filter_params pes = {};
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
 	pes.flags    = 0;

	if(eDVBTText::m_debug)
		eDebugNoNewLineStart("[eDVBText%d] DMX_SET_PES_FILTER pid=0x%04x ", m_dev, pid);
	if (::ioctl(m_fd_demux, DMX_SET_PES_FILTER, &pes) < 0)
	{
		if(eDVBTText::m_debug)
			eDebugNoNewLine("failed: %m");
		return -errno;
	}
	if(eDVBTText::m_debug)
	{
		eDebugNoNewLine("ok");
		eDebugNoNewLineStart("[eDVBText%d] DEMUX_START ", m_dev);
	}
	if (::ioctl(m_fd_demux, DMX_START) < 0)
	{
		if(eDVBTText::m_debug)
			eDebugNoNewLine("failed: %m");
		return -errno;
	}
	if(eDVBTText::m_debug)
		eDebugNoNewLine("ok");
	return 0;
}

void eDVBTText::stop()
{
	if(eDVBTText::m_debug)
	{
		eDebugNoNewLineStart("[eDVBText%d] DEMUX_STOP ", m_dev);
		if (::ioctl(m_fd_demux, DMX_STOP) < 0)
			eDebugNoNewLine("failed: %m");
		else
			eDebugNoNewLine("ok");
	}
	else
		::ioctl(m_fd_demux, DMX_STOP);
}

eDVBTText::~eDVBTText()
{
	if (m_fd_demux >= 0)
		::close(m_fd_demux);
	if(eDVBTText::m_debug)
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
	if ((m_changed & changeText) || m_state == 1)
	{
		if (m_text)
		{
			m_text->stop();
			if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
				eTuxtxtApp::getInstance()->stopCaching(this);
		}
		m_text = 0;
	}

#ifdef DREAMNEXTGEN
	/* a mosaic window ran the system clock since the main sync was set up */
	static bool s_mosaic_clock = false;

	/* Kernel-tsync PCRMASTER bootstrap: STOP_TSYNC_PCR (clear previous
	 * pts_start) then SET_DEMUX_INFO, before eDVBVideo::startPid.
	 * The sync belongs to the main decoder; PiP has none. */
	if (m_decoder == 0 && (changed & (changeState|changeVideo|changePCR)))
	{
		eAVSyncCore *avsync = eAVSyncCore::getInstance();
		bool stopping = (m_state != statePlay && m_state != statePause);
		static int s_last_vpid    = -1;
		static int s_last_pcrpid  = -1;
		static int s_last_demux   = -1;

		int new_vpid = (m_vpid > 0 && m_vpid < 0x1FFF) ? m_vpid : 0x1FFF;
		int new_apid = (m_apid > 0 && m_apid < 0x1FFF) ? m_apid : 0x1FFF;
		int new_pcr  = (m_pcrpid > 0 && m_pcrpid < 0x1FFF) ? m_pcrpid : 0x1FFF;
		int new_demux = -1;
		if (m_demux) {
			uint8_t did = 0;
			m_demux->getCADemuxID(did);
			new_demux = did;
		}

		bool video_unchanged = !stopping && !s_mosaic_clock
			&& s_last_vpid   == new_vpid
			&& s_last_pcrpid == new_pcr
			&& s_last_demux  == new_demux
			&& new_vpid != 0x1FFF;

		if (video_unchanged) {
			/* Audio-only re-init on same video stream. Leave kernel-tsync
			 * running undisturbed. */
		} else if (stopping) {
			avsync->stopPCRSync();
			s_last_vpid = s_last_pcrpid = s_last_demux = -1;
		} else if ((m_vpid > 0 && m_vpid < 0x1FFF) ||
		           (m_apid > 0 && m_apid < 0x1FFF) ||
		           (m_pcrpid > 0 && m_pcrpid < 0x1FFF))
		{
			avsync->stopPCRSync();
			avsync->enableKernelSync();
			/* the video lags the PCR by 75ms */
			avsync->setPCROffset(0x1a5e);
			avsync->setAutoPCROffset(0);
			if (new_demux >= 0)
				avsync->setDemuxInfo(new_demux, 0, new_vpid, new_apid, new_pcr);
			s_last_vpid   = new_vpid;
			s_last_pcrpid = new_pcr;
			s_last_demux  = new_demux;
			s_mosaic_clock = false;
		}
	}
#endif

	if (m_changed & changePCR)
	{
#ifdef DREAMNEXTGEN
		/* no PCR decoder for PiP, the PiP layer paces itself */
		if ((m_pcrpid >= 0) && (m_pcrpid < 0x1FFF) && m_decoder == 0)
#else
		if ((m_pcrpid >= 0) && (m_pcrpid < 0x1FFF))
#endif
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
#ifdef DREAMNEXTGEN
		/* the mosaic window playing the audio runs the system clock */
		if (m_mosaic_audio)
		{
			CFile::writeInt(("/proc/stb/vmpeg/" + std::to_string(m_decoder) + "/clock").c_str(), m_audio ? 1 : 0);
			/* the main decoder sets its sync up again afterwards */
			if (m_audio)
				s_mosaic_clock = true;
		}
#endif
		m_changed &= ~changeAudio;
	}
	if (m_changed & changeVideo)
	{
		if ((m_vpid >= 0) && (m_vpid < 0x1FFF))
		{
			m_video = new eDVBVideo(m_demux, m_decoder, m_fcc_enable);
			m_video->connectEvent(sigc::mem_fun(*this, &eTSMPEGDecoder::video_event), m_video_event_conn);
#ifdef DREAMNEXTGEN
			m_video->setPcrPid(m_pcrpid);
#endif
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
				eTuxtxtApp::getInstance()->initCache(eTSMPEGDecoder::m_debugTXT == 1);
				eTuxtxtApp::getInstance()->startCaching(m_textpid, demux, this);
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
#ifdef DREAMNEXTGEN
		/* trick/FF/slowmotion → play: FREEZE+PLAY pair to flush the AML
		 * video pacer's stuck-iframe state before resuming normal play. */
		static int s_dnxt_prev_state = stateStop;
		/* trick and pause state is tracked for the main decoder only */
		const bool dnxt_main = m_decoder == 0;
		bool dnxt_recovery = dnxt_main && m_video
			&& m_state == statePlay
			&& (s_dnxt_prev_state == stateDecoderFastForward
				|| s_dnxt_prev_state == stateTrickmode
				|| s_dnxt_prev_state == stateSlowMotion);
		if (dnxt_recovery) {
			eDebug("[eTSMPEGDecoder] DreamOS recovery dance: prev=%d → statePlay",
				   s_dnxt_prev_state);
			m_video->freeze();         // VIDEO_FREEZE
			m_video->playRecovery();   // VIDEO_PLAY (flushes trickmode iframe state)
			if (m_audio) m_audio->unfreeze();  // AUDIO_CONTINUE
		}
#endif
		if (changed & (changeState|changeVideo) && m_video)
		{
			m_video->setSlowMotion(s[1]);
			m_video->setFastForward(s[2]);
			if (s[0])
				m_video->unfreeze();
			else
				m_video->freeze();
#ifdef DREAMNEXTGEN
			/* DMX_STOP+VIDEO_CLEAR_BUFFER+DMX_START so the kernel commits
			 * the VIDEO_FAST_FORWARD trickmode change to the screen. */
			if ((m_state == stateDecoderFastForward || m_state == stateTrickmode) && s[2] > 0)
				m_video->dnxtPostFastForward();
			/* Same pipeline reset on FF/Trick → play to clear leftover
			 * I-frame queue state in the AML decoder. */
			if (m_state == statePlay
				&& (s_dnxt_prev_state == stateDecoderFastForward
				    || s_dnxt_prev_state == stateTrickmode)) {
				eDebug("[eTSMPEGDecoder] FF/Trick→play: post-FF(0) DMX+CLEAR+START");
				m_video->dnxtPostFastForward();
			}
#endif
		}
#ifdef DREAMNEXTGEN
		/* PVR/Timeshift pause: AMSTREAM_IOC_VPAUSE freezes STC via vsync
		 * ISR gate; DMX_STOP halts the PCR feed. DVB VIDEO_FREEZE alone
		 * doesn't reach timestamp_pcrscr_enable() on our kernel build. */
		if (dnxt_main && m_user_pause_active) {
			auto aml_vpause = [](int arg) {
				int fd = ::open("/dev/amvideo", O_RDWR | O_CLOEXEC);
				if (fd < 0) return;
				::ioctl(fd, 0x40045317, arg); /* AMSTREAM_IOC_VPAUSE */
				::close(fd);
			};
			if ((s_dnxt_prev_state != statePause) && (m_state == statePause)) {
				aml_vpause(1);
				if (m_pcr) m_pcr->stop();
				eDebug("[eTSMPEGDecoder] pause: VPAUSE(1) + DMX_STOP PCR demux");
			} else if ((s_dnxt_prev_state == statePause) && (m_state == statePlay)) {
				if (m_pcr) m_pcr->start();
				aml_vpause(0);
				eDebug("[eTSMPEGDecoder] unpause: DMX_START PCR demux + VPAUSE(0)");
			}
		}
		if (dnxt_main)
			s_dnxt_prev_state = m_state;
#endif
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
	eTSMPEGDecoder::m_ac3_delay=-1,
	eTSMPEGDecoder::m_debugTXT=-1;

RESULT eTSMPEGDecoder::setHwPCMDelay(int delay)
{
	if (delay != m_pcm_delay )
	{
		CFile::writeIntHex("/proc/stb/audio/audio_delay_pcm", delay*90);
		m_pcm_delay = delay;
		return 0;
	}
	return -1;
}

RESULT eTSMPEGDecoder::setHwAC3Delay(int delay)
{
	if ( delay != m_ac3_delay )
	{
		CFile::writeIntHex("/proc/stb/audio/audio_delay_bitstream", delay*90);
		m_ac3_delay = delay;
		return 0;
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
		m_changed(0), m_decoder(decoder), m_video_clip_fd(-1), m_showSinglePicTimer(eTimer::create(eApp)),
		m_fcc_fd(-1), m_fcc_enable(false), m_fcc_state(fcc_state_stop), m_fcc_feid(-1), m_fcc_vpid(-1), m_fcc_vtype(-1), m_fcc_pcrpid(-1)
{
	if (m_demux)
	{
		m_demux->connectEvent(sigc::mem_fun(*this, &eTSMPEGDecoder::demux_event), m_demux_event_conn);
	}
	CONNECT(m_showSinglePicTimer->timeout, eTSMPEGDecoder::finishShowSinglePic);
	m_state = stateStop;

	char filename[128] = {};
	sprintf(filename, "/dev/dvb/adapter%d/audio%d", m_demux ? m_demux->adapter : 0, m_decoder);
	m_has_audio = !access(filename, W_OK);
	m_mosaic_audio = false;
#ifdef DREAMNEXTGEN
	if (m_decoder >= 2)
	{
		sprintf(filename, "/dev/dvb/adapter%d/dreamaudio%d", m_demux ? m_demux->adapter : 0, m_decoder);
		m_mosaic_audio = !access(filename, W_OK);
	}
#endif

	if (eTSMPEGDecoder::m_debugTXT < 0)
		eTSMPEGDecoder::m_debugTXT = eSimpleConfig::getBool("config.crash.debugTeletext", false) ? 1 : 0;
}

void eTSMPEGDecoder::freeDecoder()
{
	// Release demux filter objects by closing their fds (via destructors).
	// Unlike stop() which uses ioctl(DMX_STOP), close() lets the kernel
	// clean up filters without going through the Broadcom playpump path.
	// This prevents deadlocks/crashes on mipsel PVR-sourced demuxes.
	m_video = nullptr;
	m_audio = nullptr;
	m_pcr = nullptr;
	m_text = nullptr;
	m_video_event_conn = nullptr;
	m_demux_event_conn = nullptr;
	m_changed = 0;
}

eTSMPEGDecoder::~eTSMPEGDecoder()
{
	finishShowSinglePic();
	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();
	fccStop();
	fccFreeFD();

	if (m_demux && m_decoder == 0)	// Tuxtxt caching actions only on primary decoder
		eTuxtxtApp::getInstance()->freeCache(this);
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
	if (!m_has_audio && !m_mosaic_audio) apid = -1;

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
	return showSinglePic(filename, false);
}

RESULT eTSMPEGDecoder::showSinglePic(const char *filename, bool keepVisible)
{
	if (m_decoder == 0)
	{
		eDebug("[eTSMPEGDecoder] showSinglePic %s", filename);
		int f = open(filename, O_RDONLY);
		if (f >= 0)
		{
			struct stat s = {};
			fstat(f, &s);
#if HAVE_HISILICON
			if (m_video_clip_fd >= 0)
				finishShowSinglePic();
#endif
			if (m_video_clip_fd == -1)
				m_video_clip_fd = open("/dev/dvb/adapter0/video0", O_WRONLY);
			if (m_video_clip_fd >= 0)
			{
				bool seq_end_avail = false;
				off_t pos=0;
				unsigned char pes_header[] = { 0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x80, 0x80, 0x05, 0x21, 0x00, 0x01, 0x00, 0x01 };
				unsigned char seq_end[] = { 0x00, 0x00, 0x01, 0xB7 };
				unsigned char iframe[s.st_size];
				unsigned char stuffing[8192];
				int streamtype;
				memset(stuffing, 0, sizeof(stuffing));
				ssize_t ret = read(f, iframe, s.st_size);
				if (ret < 0) eDebug("[eTSMPEGDecoder] read failed: %m");
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
				if (ioctl(m_video_clip_fd, VIDEO_SET_STREAMTYPE, streamtype) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_SET_STREAMTYPE failed: %m");
				if (ioctl(m_video_clip_fd, VIDEO_PLAY) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_PLAY failed: %m");
				if (ioctl(m_video_clip_fd, VIDEO_CONTINUE) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_CONTINUE: %m");
				if (ioctl(m_video_clip_fd, VIDEO_CLEAR_BUFFER) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_CLEAR_BUFFER: %m");
				while(pos <= (s.st_size-4) && !(seq_end_avail = (!iframe[pos] && !iframe[pos+1] && iframe[pos+2] == 1 && iframe[pos+3] == 0xB7)))
					++pos;
#ifdef DREAMNEXTGEN
				dream_video_frame frame = {};
				int segment = 0;
				frame.pts = 0;
				frame.bytes[segment] = s.st_size;
				frame.data[segment++] = iframe;
				if (!seq_end_avail)
				{
					frame.bytes[segment] = sizeof(seq_end);
					frame.data[segment++] = seq_end;
				}
				frame.bytes[segment] = sizeof(stuffing);
				frame.data[segment] = stuffing;
				if (ioctl(m_video_clip_fd, DREAM_VIDEO_SET_FRAME, &frame) < 0)
					eDebug("[eTSMPEGDecoder] VIDEO_SET_FRAME failed: %m");
#else
				if ((iframe[3] >> 4) != 0xE) // no pes header
					writeAll(m_video_clip_fd, pes_header, sizeof(pes_header));
				else
					iframe[4] = iframe[5] = 0x00; // NOSONAR
				writeAll(m_video_clip_fd, iframe, s.st_size);
				if (!seq_end_avail)
				{
					ret = write(m_video_clip_fd, seq_end, sizeof(seq_end));
					if (ret < 0) eDebug("[eTSMPEGDecoder] write failed: %m");
				}
				writeAll(m_video_clip_fd, stuffing, 8192);
#endif
#if HAVE_HISILICON
				;
#else
				if (!keepVisible)
					m_showSinglePicTimer->start(150, true);
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

RESULT eTSMPEGDecoder::connectVideoEvent(const sigc::slot<void(struct videoEvent)> &event, ePtr<eConnection> &conn)
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
#ifdef DREAMNEXTGEN
	int m_width = -1;
	CFile::parseInt(&m_width, "/sys/class/video/frame_width");
	//eDebug("[eTSMPEGDecoder] m_width - %d", m_width);
	if (!m_width)
		return -1;
	return m_width;
#else
	if (m_video)
		return m_video->getWidth();
	return -1;
#endif
}

int eTSMPEGDecoder::getVideoHeight()
{
#ifdef DREAMNEXTGEN
	int m_height = -1;
	CFile::parseInt(&m_height, "/sys/class/video/frame_height");
	//eDebug("[eTSMPEGDecoder] m_height - %d", m_height);
	if (!m_height)
		return -1;
	return m_height;
#else
	if (m_video)
		return m_video->getHeight();
	return -1;
#endif
}

int eTSMPEGDecoder::getVideoProgressive()
{
#ifdef DREAMNEXTGEN
	int m_progressive = -1;
	CFile::parseInt(&m_progressive, "/proc/stb/vmpeg/0/progressive");
	if (m_progressive == 2)
		return -1;
	return m_progressive;
#else
	if (m_video)
		return m_video->getProgressive();
	return -1;
#endif
}

int eTSMPEGDecoder::getVideoFrameRate()
{
#ifdef DREAMNEXTGEN
	int m_framerate = -1;
	CFile::parseInt(&m_framerate, "/proc/stb/vmpeg/0/frame_rate");
	return m_framerate;
#else
	if (m_video)
		return m_video->getFrameRate();
	return -1;
#endif
}

int eTSMPEGDecoder::getVideoAspect()
{
#ifdef DREAMNEXTGEN
	int m_aspect = -1;
	CFile::parseIntHex(&m_aspect, "/sys/class/video/frame_aspect_ratio"); //0x90 (16:9) 
	//eDebug("[eTSMPEGDecoder] m_aspect - %d", m_aspect);
	if (!m_aspect)
		return -1;
	return m_aspect == 1 ? 2 : 3;
#else
	if (m_video)
		return m_video->getAspect();
	return -1;
#endif
}

int eTSMPEGDecoder::getVideoGamma()
{
	if (m_video)
		return m_video->getGamma();
	return -1;
}


#define FCC_SET_VPID 100 // NOSONAR
#define FCC_SET_APID 101 // NOSONAR
#define FCC_SET_PCRPID 102 // NOSONAR
#define FCC_SET_VCODEC 103 // NOSONAR
#define FCC_SET_ACODEC 104 // NOSONAR
#define FCC_SET_FRONTEND_ID 105 // NOSONAR
#define FCC_START 106 // NOSONAR
#define FCC_STOP 107 // NOSONAR
#define FCC_DECODER_START 108 // NOSONAR
#define FCC_DECODER_STOP 109 // NOSONAR

RESULT eTSMPEGDecoder::prepareFCC(int fe_id, int vpid, int vtype, int pcrpid)
{
	eTrace("[eTSMPEGDecoder] prepareFCC vp : %d, vt : %d, pp : %d, fe : %d", vpid, vtype, pcrpid, fe_id); 

	if ((fccGetFD() == -1) || (fccSetPids(fe_id, vpid, vtype, pcrpid) < 0) || (fccStart() < 0))
	{
		fccFreeFD();
		return -1;
	}

	m_fcc_enable = true;

	return 0;
}

RESULT eTSMPEGDecoder::fccDecoderStart()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_ready)
	{
		eDebug("[eTSMPEGDecoder] FCC decoder is already in decoding state.");
		return 0;
	}

	if (ioctl(m_fcc_fd, FCC_DECODER_START) < 0)
	{
		eDebug("[eTSMPEGDecoder] ioctl FCC_DECODER_START failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_decoding;

	eDebug("[eTSMPEGDecoder] FCC_DECODER_START OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccDecoderStop()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_decoding)
	{
		eDebug("[eTSMPEGDecoder] FCC decoder is not in decoding state.");
	}
	else if (ioctl(m_fcc_fd, FCC_DECODER_STOP) < 0)
	{
		eDebug("[eTSMPEGDecoder] ioctl FCC_DECODER_STOP failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_ready;

	/* stop pcr, video, audio, text */
	finishShowSinglePic();

	m_vpid = m_apid = m_pcrpid = m_textpid = pidNone;
	m_changed = -1;
	setState();

	eDebug("[eTSMPEGDecoder] FCC_DECODER_STOP OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccUpdatePids(int fe_id, int vpid, int vtype, int pcrpid)
{
	eTrace("[eTSMPEGDecoder] vp : %d, vt : %d, pp : %d, fe : %d", vpid, vtype, pcrpid, fe_id);

	if ((fe_id != m_fcc_feid) || (vpid != m_fcc_vpid) || (vtype != m_fcc_vtype) || (pcrpid != m_fcc_pcrpid))
	{
		fccStop();
		if (prepareFCC(fe_id, vpid, vtype, pcrpid))
		{
			eDebug("[eTSMPEGDecoder] prepare FCC failed!");
			return -1;
		}
	}
	return 0;
}

RESULT eTSMPEGDecoder::fccStart()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state != fcc_state_stop)
	{
		eDebug("[eTSMPEGDecoder] FCC is already started!");
		return 0;
	}
	else if (ioctl(m_fcc_fd, FCC_START) < 0)
	{
		eDebug("[eTSMPEGDecoder] ioctl FCC_START failed! (%m)");
		return -1;
	}

	eDebug("[eTSMPEGDecoder] FCC_START OK!");

	m_fcc_state = fcc_state_ready;
	return 0;
}

RESULT eTSMPEGDecoder::fccStop()
{
	if (m_fcc_fd == -1)
		return -1;

	if (m_fcc_state == fcc_state_stop)
	{
		eDebug("[eTSMPEGDecoder] FCC is already stopped!");
		return 0;
	}

	else if (m_fcc_state == fcc_state_decoding)
	{
		fccDecoderStop();
	}

	if (ioctl(m_fcc_fd, FCC_STOP) < 0)
	{
		eDebug("[eTSMPEGDecoder] ioctl FCC_STOP failed! (%m)");
		return -1;
	}

	m_fcc_state = fcc_state_stop;

	eDebug("[eTSMPEGDecoder] FCC_STOP OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccSetPids(int fe_id, int vpid, int vtype, int pcrpid)
{
	int streamtype = VIDEO_STREAMTYPE_MPEG2;

	if (m_fcc_fd == -1)
		return -1;

	if (ioctl(m_fcc_fd, FCC_SET_FRONTEND_ID, fe_id) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_FRONTEND_ID failed! (%m)");
		return -1;
	}

	else if(ioctl(m_fcc_fd, FCC_SET_PCRPID, pcrpid) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_PCRPID failed! (%m)");
		return -1;
	}

	else if (ioctl(m_fcc_fd, FCC_SET_VPID, vpid) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_VPID failed! (%m)");
		return -1;
	}

	switch(vtype)
	{
		default:
		case eDVBVideo::MPEG2:
			break;
		case eDVBVideo::MPEG4_H264:
			streamtype = VIDEO_STREAMTYPE_MPEG4_H264;
			break;
		case eDVBVideo::MPEG1:
			streamtype = VIDEO_STREAMTYPE_MPEG1;
			break;
		case eDVBVideo::MPEG4_Part2:
			streamtype = VIDEO_STREAMTYPE_MPEG4_Part2;
			break;
		case eDVBVideo::VC1:
			streamtype = VIDEO_STREAMTYPE_VC1;
			break;
		case eDVBVideo::VC1_SM:
			streamtype = VIDEO_STREAMTYPE_VC1_SM;
			break;
		case eDVBVideo::H265_HEVC:
			streamtype = VIDEO_STREAMTYPE_H265_HEVC;
			break;
	}

	if(ioctl(m_fcc_fd, FCC_SET_VCODEC, streamtype) < 0)
	{
		eDebug("[eTSMPEGDecoder] FCC_SET_VCODEC failed! (%m)");
		return -1;
	}

	m_fcc_feid = fe_id;
	m_fcc_vpid = vpid;
	m_fcc_vtype = vtype;
	m_fcc_pcrpid = pcrpid;

	//eDebug("[eTSMPEGDecoder] SET PIDS OK!");
	return 0;
}

RESULT eTSMPEGDecoder::fccGetFD()
{
	if (m_fcc_fd == -1)
	{
		eFCCDecoder* fcc = eFCCDecoder::getInstance();
		if (fcc != NULL)
		{
			m_fcc_fd = fcc->allocateFcc();
		}
	}

	return m_fcc_fd;
}

RESULT eTSMPEGDecoder::fccFreeFD()
{
	if (m_fcc_fd != -1)
	{
		eFCCDecoder* fcc = eFCCDecoder::getInstance();
		if (fcc != NULL)
		{
			fcc->freeFcc(m_fcc_fd);
			m_fcc_fd = -1;
		}
	}

	return 0;
}
