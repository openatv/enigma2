#ifndef __dvb_demux_h
#define __dvb_demux_h

#include <aio.h>
#include <atomic>
#include <sys/types.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/pvrparse.h>
#include <lib/service/iservicescrambled.h>
#include "filepush.h"

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
	int getDvrId() { return m_dvr_id; }

	RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader);
	RESULT createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader);
	RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder, unsigned int packetsize = 188, bool streaming=false, bool sync_mode=false, bool is_streaming_output=false);
	RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader, int index);
	RESULT getSTC(pts_t &pts, int num);
	RESULT getCADemuxID(uint8_t &id) { id = demux; return 0; }
	RESULT getCAAdapterID(uint8_t &id) { id = adapter; return 0; }
	RESULT flush();
	RESULT connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &conn);
	int openDVR(int flags);

	int getRefCount() { return ref; }
private:
	int adapter, demux, source;

	int m_dvr_busy;
	int m_dvr_id;
	int m_dvr_source_offset;
	friend class eDVBSectionReader;
	friend class eDVBPESReader;
	friend class eDVBAudio;
	friend class eDVBVideo;
	friend class eDVBVideoSwDemux;
	friend class eDVBPCR;
	friend class eDVBTText;
	friend class eDVBTSRecorder;
	friend class eDVBCAService;
	friend class eTSMPEGDecoder;
	friend class eHEVCHDRDetector;
	sigc::signal<void(int)> m_event;
	int openDemux(void);
};

class eDVBSectionReader: public iDVBSectionReader, public sigc::trackable
{
	DECLARE_REF(eDVBSectionReader);
	int fd;
	sigc::signal<void(const uint8_t*)> read;
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
	RESULT connectRead(const sigc::slot<void(const uint8_t*)> &read, ePtr<eConnection> &conn);
};

class eDVBPESReader: public iDVBPESReader, public sigc::trackable
{
	DECLARE_REF(eDVBPESReader);
	int m_fd;
	sigc::signal<void(const uint8_t*, int)> m_read;
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
	RESULT connectRead(const sigc::slot<void(const uint8_t*,int)> &read, ePtr<eConnection> &conn);
};

class eDVBRecordFileThread: public eFilePushThreadRecorder
{
public:
	eDVBRecordFileThread(int packetsize, int bufferCount, int buffersize = -1, bool sync_mode = false);
	virtual ~eDVBRecordFileThread();
	void setTimingPID(int pid, iDVBTSRecorder::timing_pid_type pidtype, int streamtype);
	int startSaveMetaInformation(const std::string &filename);
	void stopSaveMetaInformation();
	void setSyncOnStop(bool enabled) { m_syncOnStop = enabled; m_ts_parser.setSyncOnStop(enabled); }
	int getLastPTS(pts_t &pts);
	virtual int getFirstPTS(pts_t &pts);
	void setTargetFD(int fd) { m_fd_dest = fd; _targetCached = false; updateWriteChunk(); }
	void setTargetFilename(const std::string &filename) { _targetFilename = filename; _fileOutput = !filename.empty(); _targetCached = false; }
	RESULT setSplitSize(off_t bytes);
	long long getWrittenBytes() const { return _writtenBytes.load(); }
	void enableAccessPoints(bool enable) { m_ts_parser.enableAccessPoints(enable); }
	void setDescrambler(ePtr<iServiceScrambled> serviceDescrambler) { m_serviceDescrambler = serviceDescrambler; updateWriteChunk(); };
	void setDiscardOnTimeout(bool discard) { m_discard_on_timeout = discard; }

	// Virtual: wait for first data (only ScrambledThread actually waits)
	virtual bool waitForFirstData(int /*timeout_ms*/) { return true; }

protected:
	int asyncWrite(int len);
	/* override */ int writeData(int len);
	/* override */ void flush();
	int _drainWrites(bool allowCancelled = false);
	int _syncWrite(int len, bool parse = true);
	int _nextPart();
	int _cacheFileTarget();
	int _checkTargetBase();
	void _publishWrittenBytes();

	// One buffer, written as one or more AIO requests (parts). glibc runs
	// requests for the same fd in submission order, so parts stay in order.
	struct AsyncIO
	{
		std::vector<struct aiocb> parts;
		unsigned char* buffer = nullptr;
		bool short_written = false; // a part had a short write (counted once per buffer)
		int wait(int* short_write_count = nullptr, bool allowCancelled = false);
		int start(int fd, off_t offset, size_t nbytes, unsigned char* data, size_t chunk = 0);
		int poll(int* short_write_count = nullptr, bool allowCancelled = false); // returns 1 if busy, 0 if ready, <0 on error return
		int cancel(int fd); // returns <0 on error, 0 cancelled, >0 bytes written?
	private:
		int pollPart(struct aiocb& aio, int* short_write_count, bool allowCancelled);
		void countShortWrite(int* short_write_count);
	};
	// Descrambled data written to the DVR is split into parts of at most this
	// size: the DVR driver copies each write into one contiguous kernel buffer,
	// which fails with ENOMEM for 188 kB blocks on fragmented memory.
	static const size_t MAX_DVR_WRITE = 32768;
	void updateWriteChunk();
	std::atomic<size_t> m_write_chunk{0}; // 0 = write whole buffers
	eMPEGStreamParserTS m_ts_parser;
	off_t m_current_offset;
	int m_fd_dest;
	bool m_sync_mode;
	bool m_discard_on_timeout;
	typedef std::vector<AsyncIO> AsyncIOvector;
	unsigned char* m_allocated_buffer;
	AsyncIOvector m_aio;
	AsyncIOvector::iterator m_current_buffer;
	std::vector<int> m_buffer_use_histogram;
	ePtr<iServiceScrambled> m_serviceDescrambler;
	int m_aio_short_write_count = 0;
	unsigned int m_busy_discard_count = 0;
	std::string _targetFilename;
	bool _fileOutput = false;
	bool m_syncOnStop = true;
	bool _ownsTarget = false;
	off_t _splitSize = 0;
	off_t _partStart = 0;
	unsigned int _partNumber = 0;
	int _packetSize;
	bool _targetCached = false;
	int _targetDirectoryFd = -1;
	std::string _targetBasename;
	dev_t _targetDevice = 0;
	ino_t _targetInode = 0;
	mode_t _targetMode = 0;
	std::atomic<long long> _writtenBytes{0};
};

class eDVBRecordStreamThread: public eDVBRecordFileThread
{
public:
	eDVBRecordStreamThread(int packetsize, int buffersize = -1, bool sync_mode = false);

protected:
	int writeData(int len);
	void flush();
};

class eDVBRecordScrambledThread: public eDVBRecordStreamThread
{
public:
	eDVBRecordScrambledThread(int packetsize, int buffersize = -1, bool sync_mode = false, bool is_streaming = false);
	~eDVBRecordScrambledThread();

	// Wait for first data to be written (for decoder sync)
	// Returns true if data arrived, false on timeout
	/* override */ bool waitForFirstData(int timeout_ms);

	// Reset the first-data flag (call before start() if reusing)
	void resetFirstDataFlag();

protected:
	int writeData(int len);
	void flush() override;

private:
	unsigned char key[8];
	uint32_t* ks;

	// Synchronization for first data notification
	pthread_mutex_t m_data_ready_mutex;
	pthread_cond_t m_data_ready_cond;
	bool m_first_data_written;
	bool m_is_streaming;
};

class eDVBTSRecorder: public iDVBTSRecorder, public sigc::trackable
{
	DECLARE_REF(eDVBTSRecorder);
public:
	eDVBTSRecorder(eDVBDemux *demux, int packetsize, bool streaming, bool sync_mode = false, bool is_streaming_output = false);
	~eDVBTSRecorder();

	RESULT setBufferSize(int size);
	RESULT start();
	RESULT addPID(int pid);
	RESULT removePID(int pid);

	RESULT setTimingPID(int pid, timing_pid_type pidtype, int streamtype);

	RESULT setTargetFD(int fd);
	RESULT setTargetFilename(const std::string& filename);
	RESULT setBoundary(off_t max);
	RESULT setSplitSize(off_t bytes) override;
	void setSyncOnStop(bool enabled) override { m_thread->setSyncOnStop(enabled); }
	long long getWrittenBytes() override { return m_thread->getWrittenBytes(); }
	RESULT enableAccessPoints(bool enable);

	RESULT stop();

	RESULT getCurrentPCR(pts_t &pcr);
	RESULT getFirstPTS(pts_t &pts);

	RESULT connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &conn);

	RESULT setDescrambler(ePtr<iServiceScrambled>);
	void setDiscardOnTimeout(bool discard);

	// Wait for first data to be written (for SoftDecoder sync)
	bool waitForFirstData(int timeout_ms);
	void setMinWrite(size_t size) override;
	void setServiceFilter(int serviceId, int pmtPid, bool shared) override;
	void replaceThread(eDVBRecordFileThread *newThread);
private:
	RESULT startPID(int pid);
	void stopPID(int pid);

	void filepushEvent(int event);

	std::map<int,int> m_pids;
	sigc::signal<void(int)> m_event;

	ePtr<eDVBDemux> m_demux;

	int m_running;
	int m_target_fd;
	int m_source_fd;
	eDVBRecordFileThread *m_thread;
	std::string m_target_filename;
	int m_packetsize;
	bool m_ram_mode;
	friend class eRTSPStreamClient;
};

#endif
