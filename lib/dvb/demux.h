#ifndef __dvb_demux_h
#define __dvb_demux_h

#include <aio.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/base/filepush.h>
#include <lib/dvb/pvrparse.h>

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
	int getSource() { return source; }
	RESULT setSourcePVR(int pvrnum);

	RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader);
	RESULT createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader);
	RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder, int packetsize = 188, bool streaming=false);
	RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader, int index);
	RESULT getSTC(pts_t &pts, int num);
	RESULT getCADemuxID(uint8_t &id) { id = demux; return 0; }
	RESULT getCAAdapterID(uint8_t &id) { id = adapter; return 0; }
	RESULT flush();
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn);
	int openDVR(int flags);

	int getRefCount() { return ref; }
private:
	int adapter, demux, source;

	int m_dvr_busy;
	friend class eDVBSectionReader;
	friend class eDVBPESReader;
	friend class eDVBAudio;
	friend class eDVBVideo;
	friend class eDVBPCR;
	friend class eDVBTText;
	friend class eDVBTSRecorder;
	friend class eDVBCAService;
	friend class eTSMPEGDecoder;
	Signal1<void, int> m_event;

	int openDemux(void);
};

class eDVBSectionReader: public iDVBSectionReader, public Object
{
	DECLARE_REF(eDVBSectionReader);
	int fd;
	Signal1<void, const uint8_t*> read;
	ePtr<eDVBDemux> demux;
	int active;
	int checkcrc;
	void data(int);
	ePtr<eSocketNotifier> notifier;
public:
	eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res);
	virtual ~eDVBSectionReader();
	RESULT setBufferSize(int size);
	RESULT start(const eDVBSectionFilterMask &mask);
	RESULT stop();
	RESULT connectRead(const Slot1<void,const uint8_t*> &read, ePtr<eConnection> &conn);
};

class eDVBPESReader: public iDVBPESReader, public Object
{
	DECLARE_REF(eDVBPESReader);
	int m_fd;
	Signal2<void, const uint8_t*, int> m_read;
	ePtr<eDVBDemux> m_demux;
	int m_active;
	void data(int);
	ePtr<eSocketNotifier> m_notifier;
public:
	eDVBPESReader(eDVBDemux *demux, eMainloop *context, RESULT &res);
	virtual ~eDVBPESReader();
	RESULT setBufferSize(int size);
	RESULT start(int pid);
	RESULT stop();
	RESULT connectRead(const Slot2<void,const uint8_t*, int> &read, ePtr<eConnection> &conn);
};

class eDVBRecordFileThread: public eFilePushThreadRecorder
{
public:
	eDVBRecordFileThread(int packetsize, int bufferCount);
	~eDVBRecordFileThread();
	void setTimingPID(int pid, iDVBTSRecorder::timing_pid_type pidtype, int streamtype);
	void startSaveMetaInformation(const std::string &filename);
	void stopSaveMetaInformation();
	int getLastPTS(pts_t &pts);
	int getFirstPTS(pts_t &pts);
	void setTargetFD(int fd) { m_fd_dest = fd; }
	void enableAccessPoints(bool enable) { m_ts_parser.enableAccessPoints(enable); }
protected:
	int asyncWrite(int len);
	/* override */ int writeData(int len);
	/* override */ void flush();

	struct AsyncIO
	{
		struct aiocb aio;
		unsigned char* buffer;
		AsyncIO()
		{
			memset(&aio, 0, sizeof(struct aiocb));
			buffer = NULL;
		}
		int wait();
		int start(int fd, off_t offset, size_t nbytes, void* buffer);
		int poll(); // returns 1 if busy, 0 if ready, <0 on error return
		int cancel(int fd); // returns <0 on error, 0 cancelled, >0 bytes written?
	};
	eMPEGStreamParserTS m_ts_parser;
	off_t m_current_offset;
	int m_fd_dest;
	typedef std::vector<AsyncIO> AsyncIOvector;
	unsigned char* m_allocated_buffer;
	AsyncIOvector m_aio;
	AsyncIOvector::iterator m_current_buffer;
	std::vector<int> m_buffer_use_histogram;
};

class eDVBRecordStreamThread: public eDVBRecordFileThread
{
public:
	eDVBRecordStreamThread(int packetsize):
		eDVBRecordFileThread(packetsize, /*bufferCount*/ 4)
	{
	}
protected:
	int writeData(int len);
	void flush();
};

class eDVBTSRecorder: public iDVBTSRecorder, public Object
{
	DECLARE_REF(eDVBTSRecorder);
public:
	eDVBTSRecorder(eDVBDemux *demux, int packetsize, bool streaming);
	~eDVBTSRecorder();

	RESULT setBufferSize(int size);
	RESULT start();
	RESULT addPID(int pid);
	RESULT removePID(int pid);

	RESULT setTimingPID(int pid, timing_pid_type pidtype, int streamtype);

	RESULT setTargetFD(int fd);
	RESULT setTargetFilename(const std::string& filename);
	RESULT setBoundary(off_t max);
	RESULT enableAccessPoints(bool enable);

	RESULT stop();

	RESULT getCurrentPCR(pts_t &pcr);
	RESULT getFirstPTS(pts_t &pts);

	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn);
private:
	RESULT startPID(int pid);
	void stopPID(int pid);

	void filepushEvent(int event);

	std::map<int,int> m_pids;
	Signal1<void,int> m_event;

	ePtr<eDVBDemux> m_demux;

	int m_running;
	int m_target_fd;
	int m_source_fd;
	eDVBRecordFileThread *m_thread;
	std::string m_target_filename;
	int m_packetsize;
};

#endif
