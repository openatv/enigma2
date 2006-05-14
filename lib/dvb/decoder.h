#ifndef __decoder_h
#define __decoder_h

#include <lib/base/object.h>
#include <lib/dvb/demux.h>

class eDVBAudio: public iObject
{
DECLARE_REF(eDVBAudio);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev;
public:
	enum { aMPEG, aAC3, aDTS, aAAC };
	eDVBAudio(eDVBDemux *demux, int dev);
	int startPid(int pid, int type);
	void stop();
#if HAVE_DVB_API_VERSION < 3
	void start();
	void stopPid();
#endif
	void flush();
	void freeze();
	void unfreeze();
	int getPTS(pts_t &now);
	virtual ~eDVBAudio();
};

class eDVBVideo: public iObject
{
DECLARE_REF(eDVBVideo);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev;
	
	int m_is_slow_motion, m_is_fast_forward;
public:
	enum { MPEG2, MPEG4_H264 };
	eDVBVideo(eDVBDemux *demux, int dev);
	int startPid(int pid, int type);
	void stop();
#if HAVE_DVB_API_VERSION < 3
	void start();
	void stopPid();
#endif
	void flush();
	void freeze();
	int setSlowMotion(int repeat);
	int setFastForward(int skip);
	void unfreeze();
	int getPTS(pts_t &now);
	virtual ~eDVBVideo();
};

class eDVBPCR: public iObject
{
DECLARE_REF(eDVBPCR);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd_demux;
public:
	eDVBPCR(eDVBDemux *demux);
	int startPid(int pid);
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
DECLARE_REF(eTSMPEGDecoder);
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
	ePtr<eConnection> m_demux_event;
	
	void demux_event(int event);
public:
	enum { pidNone = -1 };
	eTSMPEGDecoder(eDVBDemux *demux, int decoder);
	virtual ~eTSMPEGDecoder();
	RESULT setVideoPID(int vpid, int type);
	RESULT setAudioPID(int apid, int type);
	RESULT setSyncPCR(int pcrpid);
	RESULT setTextPID(int textpid);
	RESULT setSyncMaster(int who);
	RESULT start();
	RESULT freeze(int cont);
	RESULT unfreeze();
	RESULT setSinglePictureMode(int when);
	RESULT setPictureSkipMode(int what);
	RESULT setFastForward(int frames_to_skip);
	RESULT setSlowMotion(int repeat);
	RESULT setZoom(int what);
	RESULT flush();
	RESULT setTrickmode(int what);
	
		/* what 0=auto, 1=video, 2=audio. */
	RESULT getPTS(int what, pts_t &pts);
};

#endif
