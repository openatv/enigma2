#ifndef __decoder_h
#define __decoder_h

#include <lib/base/object.h>
#include <lib/dvb/demux.h>

class eDVBAudio: public virtual iObject
{
DECLARE_REF;
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux;
public:
	eDVBAudio(eDVBDemux *demux, int dev);
	int startPid(int pid);
	void stop();
	virtual ~eDVBAudio();
};

class eDVBVideo: public virtual iObject
{
DECLARE_REF;
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux;
public:
	eDVBVideo(eDVBDemux *demux, int dev);
	int startPid(int pid);
	void stop();
	virtual ~eDVBVideo();
};

class eTSMPEGDecoder: public virtual iTSMPEGDecoder
{
DECLARE_REF;
private:
	ePtr<eDVBDemux> m_demux;
	ePtr<eDVBAudio> m_audio;
	ePtr<eDVBVideo> m_video;
	
	int m_vpid, m_apid, m_atype, m_pcrpid;
	enum
	{
		changeVideo = 1, 
		changeAudio = 2, 
		changePCR   = 4
	};
	int m_changed;
	int setState();
public:
	enum { pidNone = -1 };
	eTSMPEGDecoder(eDVBDemux *demux, int decoder);
	virtual ~eTSMPEGDecoder();
	RESULT setVideoPID(int vpid);
	RESULT setAudioPID(int apid, int type);
	RESULT setSyncPCR(int pcrpid);
	RESULT setSyncMaster(int who);
	RESULT start();
	RESULT freeze(int cont);
	RESULT unfreeze();
	RESULT setSinglePictureMode(int when);
	RESULT setPictureSkipMode(int what);
	RESULT setSlowMotion(int repeat);
	RESULT setZoom(int what);
};
#endif
