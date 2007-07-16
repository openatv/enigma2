#ifndef __decoder_h
#define __decoder_h

#include <lib/base/object.h>
#include <lib/dvb/demux.h>

class eSocketNotifier;

class eDVBAudio: public iObject
{
DECLARE_REF(eDVBAudio);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev, m_is_freezed;
public:
	enum { aMPEG, aAC3, aDTS, aAAC };
	eDVBAudio(eDVBDemux *demux, int dev);
	enum { aMonoLeft, aStereo, aMonoRight };
	void setChannel(int channel);
	void stop();
#if HAVE_DVB_API_VERSION < 3
	int setPid(int pid, int type);
	int startPid();
	int start();
	int stopPid();
	int setAVSync(int val);
#else
	int startPid(int pid, int type);
#endif
	void flush();
	void freeze();
	void unfreeze();
	int getPTS(pts_t &now);
	virtual ~eDVBAudio();
};

class eDVBVideo: public iObject, public Object
{
DECLARE_REF(eDVBVideo);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev;
#if HAVE_DVB_API_VERSION < 3
	m_fd_video;
#endif
	int m_is_slow_motion, m_is_fast_forward, m_is_freezed;
	eSocketNotifier *m_sn;
	void video_event(int what);
	Signal1<void, struct iTSMPEGDecoder::videoEvent> m_event;
public:
	enum { MPEG2, MPEG4_H264 };
	eDVBVideo(eDVBDemux *demux, int dev);
	void stop();
#if HAVE_DVB_API_VERSION < 3
	int setPid(int pid);
	int startPid();
	int start();
	int stopPid();
#else
	int startPid(int pid, int type=MPEG2);
#endif
	void flush();
	void freeze();
	int setSlowMotion(int repeat);
	int setFastForward(int skip);
	void unfreeze();
	int getPTS(pts_t &now);
	virtual ~eDVBVideo();
	RESULT connectEvent(const Slot1<void, struct iTSMPEGDecoder::videoEvent> &event, ePtr<eConnection> &conn);
};

class eDVBPCR: public iObject
{
DECLARE_REF(eDVBPCR);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd_demux;
public:
	eDVBPCR(eDVBDemux *demux);
#if HAVE_DVB_API_VERSION < 3
	int setPid(int pid);
	int startPid();
#else
	int startPid(int pid);
#endif
	void stop();
	virtual ~eDVBPCR();
};

class eDVBTText: public iObject
{
DECLARE_REF(eDVBTText);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd_demux;
public:
	eDVBTText(eDVBDemux *demux);
	int startPid(int pid);
	void stop();
	virtual ~eDVBTText();
};

class eTSMPEGDecoder: public Object, public iTSMPEGDecoder
{
	static int m_pcm_delay;
	static int m_ac3_delay;
	static int m_audio_channel;
DECLARE_REF(eTSMPEGDecoder);
	std::string m_radio_pic;
private:
	ePtr<eDVBDemux> m_demux;
	ePtr<eDVBAudio> m_audio;
	ePtr<eDVBVideo> m_video;
	ePtr<eDVBPCR> m_pcr;
	ePtr<eDVBTText> m_text;
	int m_vpid, m_vtype, m_apid, m_atype, m_pcrpid, m_textpid;
	enum
	{
		changeVideo = 1, 
		changeAudio = 2, 
		changePCR   = 4,
		changeText  = 8
	};
	int m_changed, m_decoder;
	int m_is_ff, m_is_sm, m_is_trickmode;
	int setState();
	ePtr<eConnection> m_demux_event_conn;
	ePtr<eConnection> m_video_event_conn;
	
	void demux_event(int event);
	void video_event(struct videoEvent);
	Signal1<void, struct videoEvent> m_video_event;
public:
	enum { pidNone = -1 };
	eTSMPEGDecoder(eDVBDemux *demux, int decoder);
	virtual ~eTSMPEGDecoder();
	RESULT setVideoPID(int vpid, int type);
	RESULT setAudioPID(int apid, int type);
	RESULT setAudioChannel(int channel);
	int getAudioChannel();
	RESULT setPCMDelay(int delay);
	int getPCMDelay() { return m_pcm_delay; }
	RESULT setAC3Delay(int delay);
	int getAC3Delay() { return m_ac3_delay; }
	RESULT setSyncPCR(int pcrpid);
	RESULT setTextPID(int textpid);
	RESULT setSyncMaster(int who);
	RESULT start();
	RESULT preroll();
	RESULT freeze(int cont);
	RESULT unfreeze();
	RESULT setSinglePictureMode(int when);
	RESULT setPictureSkipMode(int what);
	RESULT setFastForward(int frames_to_skip);
	RESULT setSlowMotion(int repeat);
	RESULT setZoom(int what);
	RESULT flush();
	RESULT setTrickmode(int what);
	RESULT showSinglePic(const char *filename);
	RESULT setRadioPic(const std::string &filename);
		/* what 0=auto, 1=video, 2=audio. */
	RESULT getPTS(int what, pts_t &pts);
	RESULT connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &connection);
};

#endif
