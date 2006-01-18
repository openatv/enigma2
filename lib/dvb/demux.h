#ifndef __dvb_demux_h
#define __dvb_demux_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>

class eDVBDemux: public iDVBDemux
{
	DECLARE_REF(eDVBDemux);
public:
	enum {
		evtFlush
	};
	eDVBDemux(int adapter, int demux);
	virtual ~eDVBDemux();
	
	RESULT setSourceFrontend(int fenum);
	RESULT setSourcePVR(int pvrnum);
	
	RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader);
	RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder);
	RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader);
	RESULT getSTC(pts_t &pts, int num);
	RESULT getCADemuxID(uint8_t &id) { id = demux; return 0; }
	RESULT flush();
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn);
private:
	int adapter, demux;
	
	int m_dvr_busy;
	friend class eDVBSectionReader;
	friend class eDVBAudio;
	friend class eDVBVideo;
	friend class eDVBPCR;
	friend class eDVBTText;
	friend class eDVBTSRecorder;
	friend class eDVBCAService;
	Signal1<void, int> m_event;
	
	int openDemux(void);
};

class eDVBSectionReader: public iDVBSectionReader, public Object
{
	DECLARE_REF(eDVBSectionReader);
private:
	int fd;
	Signal1<void, const __u8*> read;
	ePtr<eDVBDemux> demux;
	int active;
	int checkcrc;
	void data(int);
	eSocketNotifier *notifier;
public:
	
	eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res);
	virtual ~eDVBSectionReader();
	RESULT start(const eDVBSectionFilterMask &mask);
	RESULT stop();
	RESULT connectRead(const Slot1<void,const __u8*> &read, ePtr<eConnection> &conn);
};

class eFilePushThread;

class eDVBTSRecorder: public iDVBTSRecorder, public Object
{
	DECLARE_REF(eDVBTSRecorder);
public:
	eDVBTSRecorder(eDVBDemux *demux);
	~eDVBTSRecorder();

	RESULT start();
	RESULT addPID(int pid);
	RESULT removePID(int pid);
	
	RESULT setFormat(int pid);
	
	RESULT setTargetFD(int fd);
	RESULT setBoundary(off_t max);
	
	RESULT stop();
	
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn);
private:
	RESULT startPID(int pid);
	void stopPID(int pid);
	
	eFilePushThread *m_thread;
	
	std::map<int,int> m_pids;
	Signal1<void,int> m_event;
	
	ePtr<eDVBDemux> m_demux;
	
	int m_running, m_format, m_target_fd, m_source_fd;
};

#endif
