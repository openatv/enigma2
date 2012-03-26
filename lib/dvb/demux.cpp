#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <aio.h>
#include <lib/base/systemsettings.h>
#include <sys/sysinfo.h>
#include <sys/mman.h>
// For SYS_ stuff
#include <syscall.h>

//#define SHOW_WRITE_TIME
static int determineBufferCount()
{
	struct sysinfo si;
	if (sysinfo(&si) != 0)
	{
		return 6; // Default to small
	}
	unsigned int megabytes = si.totalram >> 20;
	int result;
	if (megabytes > 200)
		result = 20; // 512MB systems: Use 4MB IO buffers (et9x00, vuultimo, ...)
	else if (megabytes > 100)
		result = 16; // 256MB systems: Use 3MB demux buffers (dm8000, et5x00, vuduo)
	else
		result = 8; // Smaller boxes: Use 1.5MB buffer (dm7025)
	return result;
}
static const int demuxSize = 4*188*1024; // With the large userspace IO buffers, a 752k demux buffer is enough
static int recordingBufferCount = determineBufferCount();

static size_t flushSize = 0;

// Defined and exported to SWIG in systemsettings.h
int getFlushSize(void)
{
	return (int)flushSize;
}

void setFlushSize(int size)
{
	if (size >= 0)
	{
		flushSize = (size_t)size;
	}
}

#if HAVE_DVB_API_VERSION < 3
#include <ost/dmx.h>

#ifndef DMX_SET_NEGFILTER_MASK
	#define DMX_SET_NEGFILTER_MASK   _IOW('o',48,uint8_t *)
#endif

#ifndef DMX_GET_STC
	struct dmx_stc
	{
		unsigned int num;	/* input : which STC? O..N */
		unsigned int base;	/* output: divisor for stc to get 90 kHz clock */
		unsigned long long stc; /* output: src in 'base'*90 kHz units */
	};
	#define DMX_GET_STC		_IOR('o', 50, struct dmx_stc)
#endif

#else
#include <linux/dvb/dmx.h>

#define HAVE_ADD_PID

#ifdef HAVE_ADD_PID

#if HAVE_DVB_API_VERSION > 3
#ifndef DMX_ADD_PID
#define DMX_ADD_PID		_IOW('o', 51, __u16)
#define DMX_REMOVE_PID		_IOW('o', 52, __u16)
#endif
#else
#define DMX_ADD_PID              _IO('o', 51)
#define DMX_REMOVE_PID           _IO('o', 52)

typedef enum {
	DMX_TAP_TS = 0,
	DMX_TAP_PES = DMX_PES_OTHER, /* for backward binary compat. */
} dmx_tap_type_t;
#endif

#endif

#endif

#include "crc32.h"

#include <lib/base/eerror.h>
#include <lib/base/filepush.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/pvrparse.h>

eDVBDemux::eDVBDemux(int adapter, int demux):
	adapter(adapter),
	demux(demux),
	source(-1),
	m_dvr_busy(0)
{
}

eDVBDemux::~eDVBDemux()
{
}

int eDVBDemux::openDemux(void)
{
	char filename[32];
#if HAVE_DVB_API_VERSION < 3
	snprintf(filename, sizeof(filename), "/dev/dvb/card%d/demux%d", adapter, demux);
#else
	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/demux%d", adapter, demux);
#endif
	return ::open(filename, O_RDWR);
}

int eDVBDemux::openDVR(int flags)
{
#if HAVE_DVB_API_VERSION < 3
	return ::open("/dev/pvr", flags);
#else
#ifdef HAVE_OLDPVR
	return ::open("/dev/misc/pvr", flags);
#else
	char filename[32];
	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/dvr%d", adapter, demux);
	return ::open(filename, flags);
#endif
#endif
}

DEFINE_REF(eDVBDemux)

RESULT eDVBDemux::setSourceFrontend(int fenum)
{
#if HAVE_DVB_API_VERSION >= 3
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = DMX_SOURCE_FRONT0 + fenum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	if (res)
		eDebug("DMX_SET_SOURCE failed! - %m");
	else
		source = fenum;
	::close(fd);
	return res;
#endif
	return 0;
}

RESULT eDVBDemux::setSourcePVR(int pvrnum)
{
#if HAVE_DVB_API_VERSION >= 3
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = DMX_SOURCE_DVR0 + pvrnum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	source = -1;
	::close(fd);
	return res;
#endif
	return 0;
}

RESULT eDVBDemux::createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)
{
	RESULT res;
	reader = new eDVBSectionReader(this, context, res);
	if (res)
		reader = 0;
	return res;
}

RESULT eDVBDemux::createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader)
{
	RESULT res;
	reader = new eDVBPESReader(this, context, res);
	if (res)
		reader = 0;
	return res;
}

RESULT eDVBDemux::createTSRecorder(ePtr<iDVBTSRecorder> &recorder, int packetsize, bool streaming)
{
	if (m_dvr_busy)
		return -EBUSY;
	recorder = new eDVBTSRecorder(this, packetsize, streaming);
	return 0;
}

RESULT eDVBDemux::getMPEGDecoder(ePtr<iTSMPEGDecoder> &decoder, int primary)
{
	decoder = new eTSMPEGDecoder(this, primary ? 0 : 1);
	return 0;
}

RESULT eDVBDemux::getSTC(pts_t &pts, int num)
{
	int fd = openDemux();
	
	if (fd < 0)
		return -ENODEV;

	struct dmx_stc stc;
	stc.num = num;
	stc.base = 1;
	
	if (ioctl(fd, DMX_GET_STC, &stc) < 0)
	{
		eDebug("DMX_GET_STC failed!");
		::close(fd);
		return -1;
	}
	
	pts = stc.stc;
	
	eDebug("DMX_GET_STC - %lld", pts);
	
	::close(fd);
	return 0;
}

RESULT eDVBDemux::flush()
{
	// FIXME: implement flushing the PVR queue here.
	
	m_event(evtFlush);
	return 0;
}

RESULT eDVBDemux::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

void eDVBSectionReader::data(int)
{
	__u8 data[4096]; // max. section size
	int r;
	r = ::read(fd, data, 4096);
	if(r < 0)
	{
		eWarning("ERROR reading section - %m\n");
		return;
	}
	if (checkcrc)
	{
		// this check should never happen unless the driver is crappy!
		unsigned int c;
		if ((c = crc32((unsigned)-1, data, r)))
		{
			eDebug("crc32 failed! is %x\n", c);
			return;
		}
	}
	if (active)
		read(data);
	else
		eDebug("data.. but not active");
}

eDVBSectionReader::eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res): demux(demux)
{
	fd = demux->openDemux();
	
	if (fd >= 0)
	{
		notifier=eSocketNotifier::create(context, fd, eSocketNotifier::Read, false);
		CONNECT(notifier->activated, eDVBSectionReader::data);
		res = 0;
	} else
	{
		perror("demux->openDemux failed");
		res = errno;
	}
}

DEFINE_REF(eDVBSectionReader)

eDVBSectionReader::~eDVBSectionReader()
{
	if (fd >= 0)
		::close(fd);
}

RESULT eDVBSectionReader::setBufferSize(int size)
{
	int res=::ioctl(fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBSectionReader DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

RESULT eDVBSectionReader::start(const eDVBSectionFilterMask &mask)
{
	RESULT res;
	if (fd < 0)
		return -ENODEV;

	notifier->start();
#if HAVE_DVB_API_VERSION < 3
	dmxSctFilterParams sct;
#else
	dmx_sct_filter_params sct;
#endif
	sct.pid     = mask.pid;
	sct.timeout = 0;
#if HAVE_DVB_API_VERSION < 3
	sct.flags   = 0;
#else
	sct.flags   = DMX_IMMEDIATE_START;
#endif
	if (mask.flags & eDVBSectionFilterMask::rfCRC)
	{
		sct.flags |= DMX_CHECK_CRC;
		checkcrc = 1;
	} else
		checkcrc = 0;
	
	memcpy(sct.filter.filter, mask.data, DMX_FILTER_SIZE);
	memcpy(sct.filter.mask, mask.mask, DMX_FILTER_SIZE);
#if HAVE_DVB_API_VERSION >= 3
	memcpy(sct.filter.mode, mask.mode, DMX_FILTER_SIZE);
	setBufferSize(8192*8);
#endif
	
	res = ::ioctl(fd, DMX_SET_FILTER, &sct);
	if (!res)
	{
#if HAVE_DVB_API_VERSION < 3
		res = ::ioctl(fd, DMX_SET_NEGFILTER_MASK, mask.mode);
		if (!res)
		{
			res = ::ioctl(fd, DMX_START, 0);
			if (!res)
				active = 1;
		}
#else
		active = 1;
#endif
	}
	return res;
}

RESULT eDVBSectionReader::stop()
{
	if (!active)
		return -1;

	active=0;
	::ioctl(fd, DMX_STOP);
	notifier->stop();

	return 0;
}

RESULT eDVBSectionReader::connectRead(const Slot1<void,const __u8*> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, read.connect(r));
	return 0;
}

void eDVBPESReader::data(int)
{
	while (1)
	{
		__u8 buffer[16384];
		int r;
		r = ::read(m_fd, buffer, 16384);
		if (!r)
			return;
		if(r < 0)
		{
			if (errno == EAGAIN || errno == EINTR) /* ok */
				return;
			eWarning("ERROR reading PES (fd=%d) - %m", m_fd);
			return;
		}

		if (m_active)
			m_read(buffer, r);
		else
			eWarning("PES reader not active");
		if (r != 16384)
			break;
	}
}

eDVBPESReader::eDVBPESReader(eDVBDemux *demux, eMainloop *context, RESULT &res): m_demux(demux)
{
	m_fd = m_demux->openDemux();
	if (m_fd >= 0)
	{
		setBufferSize(64*1024);
		::fcntl(m_fd, F_SETFL, O_NONBLOCK);
		m_notifier = eSocketNotifier::create(context, m_fd, eSocketNotifier::Read, false);
		CONNECT(m_notifier->activated, eDVBPESReader::data);
		res = 0;
	} else
	{
		perror("openDemux");
		res = errno;
	}
}

RESULT eDVBPESReader::setBufferSize(int size)
{
	int res = ::ioctl(m_fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBPESReader DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

DEFINE_REF(eDVBPESReader)

eDVBPESReader::~eDVBPESReader()
{
	if (m_fd >= 0)
		::close(m_fd);
}

RESULT eDVBPESReader::start(int pid)
{
	RESULT res;
	if (m_fd < 0)
		return -ENODEV;

	m_notifier->start();

#if HAVE_DVB_API_VERSION < 3
	dmxPesFilterParams flt;
	
	flt.pesType = DMX_PES_OTHER;
#else
	dmx_pes_filter_params flt;
	
	flt.pes_type = DMX_PES_OTHER;
#endif

	flt.pid     = pid;
	flt.input   = DMX_IN_FRONTEND;
	flt.output  = DMX_OUT_TAP;
	
	flt.flags   = DMX_IMMEDIATE_START;

	res = ::ioctl(m_fd, DMX_SET_PES_FILTER, &flt);
	
	if (res)
		eWarning("PES filter: DMX_SET_PES_FILTER - %m");
	if (!res)
		m_active = 1;
	return res;
}

RESULT eDVBPESReader::stop()
{
	if (!m_active)
		return -1;

	m_active=0;
	::ioctl(m_fd, DMX_STOP);
	m_notifier->stop();

	return 0;
}

RESULT eDVBPESReader::connectRead(const Slot2<void,const __u8*,int> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_read.connect(r));
	return 0;
}

class eDVBRecordFileThread: public eFilePushThreadRecorder
{
public:
	eDVBRecordFileThread(int packetsize, int bufferCount);
	~eDVBRecordFileThread();
	void setTimingPID(int pid, int type);
	void startSaveMetaInformation(const std::string &filename);
	void stopSaveMetaInformation();
	int getLastPTS(pts_t &pts);
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
	off_t offset_last_sync;
	size_t written_since_last_sync;
	typedef std::vector<AsyncIO> AsyncIOvector;
	unsigned char* m_allocated_buffer;
	AsyncIOvector m_aio;
	AsyncIOvector::iterator m_current_buffer;
	std::vector<int> m_buffer_use_histogram;
};

eDVBRecordFileThread::eDVBRecordFileThread(int packetsize, int bufferCount):
	eFilePushThreadRecorder(
		/* buffer */ (unsigned char*) ::mmap(NULL, bufferCount * packetsize * 1024, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, /*ignored*/-1, 0),
		/*buffersize*/ packetsize * 1024),
	 m_ts_parser(packetsize),
	 m_current_offset(0),
	 m_fd_dest(-1),
	 offset_last_sync(0),
	 written_since_last_sync(0),
	 m_aio(bufferCount),
	 m_current_buffer(m_aio.begin()),
	 m_buffer_use_histogram(bufferCount+1, 0)
{
	if (m_buffer == MAP_FAILED)
		eFatal("Failed to allocate filepush buffer, contact MiLo\n");
	// m_buffer actually points to a data block large enough to hold ALL buffers. m_buffer will
	// move around during writes, so we must remember where the "head" is.
	m_allocated_buffer = m_buffer;
	// m_buffersize is thus the size of a single buffer in the queue
	// Initialize the buffer pointers
	int index = 0;
	for (AsyncIOvector::iterator it = m_aio.begin(); it != m_aio.end(); ++it)
	{
		it->buffer = m_allocated_buffer + (index * m_buffersize);
		++index;
	}
}

eDVBRecordFileThread::~eDVBRecordFileThread()
{
	::munmap(m_allocated_buffer, m_aio.size() * m_buffersize);
}

void eDVBRecordFileThread::setTimingPID(int pid, int type)
{
	m_ts_parser.setPid(pid, type);
}

void eDVBRecordFileThread::startSaveMetaInformation(const std::string &filename)
{
	m_ts_parser.startSave(filename);
}

void eDVBRecordFileThread::stopSaveMetaInformation()
{
	m_ts_parser.stopSave();
}

int eDVBRecordFileThread::getLastPTS(pts_t &pts)
{
	return m_ts_parser.getLastPTS(pts);
}

int eDVBRecordFileThread::AsyncIO::wait()
{
	if (aio.aio_buf != NULL) // Only if we had a request outstanding
	{
		while (aio_error(&aio) == EINPROGRESS)
		{
			eDebug("[eDVBRecordFileThread] Waiting for I/O to complete");
			struct aiocb* paio = &aio;
			int r = aio_suspend(&paio, 1, NULL);
			if (r < 0)
			{
				eDebug("[eDVBRecordFileThread] aio_suspend failed: %m");
				return -1;
			}
		}
		int r = aio_return(&aio);
		aio.aio_buf = NULL;
		if (r < 0)
		{
			eDebug("[eDVBRecordFileThread] wait: aio_return returned failure: %m");
			return -1;
		}
	}
	return 0;
}

int eDVBRecordFileThread::AsyncIO::cancel(int fd)
{
	int r = poll();
	if (r <= 0)
		return r; // Either no need to cancel, or error return
	eDebug("[eDVBRecordFileThread] cancelling");
	return aio_cancel(fd, &aio);
}

int eDVBRecordFileThread::AsyncIO::poll()
{
	if (aio.aio_buf == NULL)
		return 0;
	if (aio_error(&aio) == EINPROGRESS)
	{
		return 1;
	}
	int r = aio_return(&aio);
	aio.aio_buf = NULL;
	if (r < 0)
	{
		eDebug("[eDVBRecordFileThread] poll: aio_return returned failure: %m");
		return -1;
	}
	return 0;
}

int eDVBRecordFileThread::AsyncIO::start(int fd, off_t offset, size_t nbytes, void* buffer)
{
	memset(&aio, 0, sizeof(struct aiocb)); // Documentation says "zero it before call".
	aio.aio_fildes = fd;
	aio.aio_nbytes = nbytes;
	aio.aio_offset = offset;   // Offset can be omitted with O_APPEND
	aio.aio_buf = buffer;
	return aio_write(&aio);
}

int eDVBRecordFileThread::asyncWrite(int len)
{
#ifdef SHOW_WRITE_TIME
	struct timeval starttime;
	struct timeval now;
	suseconds_t diff;
	gettimeofday(&starttime, NULL);
#endif

	m_ts_parser.parseData(m_current_offset, m_buffer, len);

#ifdef SHOW_WRITE_TIME
	gettimeofday(&now, NULL);
	diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
	eDebug("[eFilePushThreadRecorder] m_ts_parser.parseData: %9u us", (unsigned int)diff);
	gettimeofday(&starttime, NULL);
#endif
	
	int r = m_current_buffer->start(m_fd_dest, m_current_offset, len, m_buffer);
	if (r < 0)
	{
		eDebug("[eDVBRecordFileThread] aio_write failed: %m");
		return r;
	}
	m_current_offset += len;

#ifdef SHOW_WRITE_TIME
	gettimeofday(&now, NULL);
	diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
	eDebug("[eFilePushThreadRecorder] aio_write: %9u us", (unsigned int)diff);
#endif
	
	// do the flush thing if the user wanted it
	if (flushSize != 0)
	{
		written_since_last_sync += len;
		if (written_since_last_sync > flushSize)
		{
			int pr;
			pr = syscall(SYS_fadvise64, m_fd_dest, offset_last_sync, 0, 0, 0, POSIX_FADV_DONTNEED);
			if (pr != 0)
			{
				eDebug("[eDVBRecordFileThread] POSIX_FADV_DONTNEED returned %d", pr);
			}
			offset_last_sync += written_since_last_sync;
			written_since_last_sync = 0;
		}
	}

	// Count how many buffers are still "busy". Move backwards from current,
	// because they can reasonably be expected to finish in that order.
	AsyncIOvector::iterator i = m_current_buffer;
	r = i->poll();
	int busy_count = 0;
	while (r > 0)
	{
		++busy_count;
		if (i == m_aio.begin())
			i = m_aio.end();
		--i;
		if (i == m_current_buffer)
		{
			eDebug("[eFilePushThreadRecorder] Warning: All write buffers busy");
			break;
		}
		r = i->poll();
		if (r < 0)
			return r;
	}
	++m_buffer_use_histogram[busy_count];

#ifdef SHOW_WRITE_TIME
	gettimeofday(&starttime, NULL);
#endif
	
	++m_current_buffer;
	if (m_current_buffer == m_aio.end())
		m_current_buffer = m_aio.begin();
	m_buffer = m_current_buffer->buffer;
	return len;
}

int eDVBRecordFileThread::writeData(int len)
{
	len = asyncWrite(len);
	if (len < 0)
		return len;
	// Wait for previous aio to complete on this buffer before returning
	int r = m_current_buffer->wait();
	if (r < 0)
		return -1;
	return len;
}

void eDVBRecordFileThread::flush()
{
	eDebug("[eDVBRecordFileThread] waiting for aio to complete");
	for (AsyncIOvector::iterator it = m_aio.begin(); it != m_aio.end(); ++it)
	{
		it->wait();
	}
	int bufferCount = m_aio.size();
	eDebug("[eDVBRecordFileThread] buffer usage histogram (%d buffers of %d kB)", bufferCount, m_buffersize>>10);
	for (int i=0; i <= bufferCount; ++i)
	{
		if (m_buffer_use_histogram[i] != 0) eDebug("     %2d: %6d", i, m_buffer_use_histogram[i]);
	}
	if (m_overflow_count)
	{
		eDebug("[eDVBRecordFileThread] Demux buffer overflows: %d", m_overflow_count);
	}
}

class eDVBRecordStreamThread: public eDVBRecordFileThread
{
public:
	eDVBRecordStreamThread(int packetsize):
		eDVBRecordFileThread(packetsize, /*bufferCount*/ 4)
	{
	}
protected:
	int writeData(int len)
	{
		len = asyncWrite(len);
		if (len < 0)
			return len;
		// Cancel aio on this buffer before returning, streams should not be held up. So we CANCEL
		// any request that hasn't finished on the second round.
		int r = m_current_buffer->cancel(m_fd_dest);
		switch (r)
		{
			//case 0: // that's one of these two:
			case AIO_CANCELED:
			case AIO_ALLDONE:
				break;
			case AIO_NOTCANCELED:
				eDebug("[eDVBRecordStreamThread] failed to cancel, killing all waiting IO");
				aio_cancel(m_fd_dest, NULL);
				// Poll all open requests, because they are all in error state now.
				for (AsyncIOvector::iterator it = m_aio.begin(); it != m_aio.end(); ++it)
				{
					it->poll();
				}
				break;
			case -1:
				eDebug("[eDVBRecordStreamThread] failed: %m");
				return r;
		}
		// we want to have a consistent state, so wait for completion, just to be sure
		r = m_current_buffer->wait();
		if (r < 0)
		{
			eDebug("[eDVBRecordStreamThread] wait failed: %m");
			return -1;
		}
		return len;
	}
	void flush()
	{
		eDebug("[eDVBRecordStreamThread] cancelling aio");
		switch (aio_cancel(m_fd_dest, NULL))
		{
			case AIO_CANCELED:
				eDebug("[eDVBRecordStreamThread] ok");
				break;
			case AIO_NOTCANCELED:
				eDebug("[eDVBRecordStreamThread] not all cancelled");
				break;
			case AIO_ALLDONE:
				eDebug("[eDVBRecordStreamThread] all done");
				break;
			case -1:
				eDebug("[eDVBRecordStreamThread] failed: %m");
				break;
			default:
				eDebug("[eDVBRecordStreamThread] unexpected return code");
				break;
		}
		// Call inherited flush to clean up the rest.
		eDVBRecordFileThread::flush();
	}
};


DEFINE_REF(eDVBTSRecorder);

eDVBTSRecorder::eDVBTSRecorder(eDVBDemux *demux, int packetsize, bool streaming):
	m_demux(demux),
	m_running(0),
	m_target_fd(-1),
	m_thread(streaming ? new eDVBRecordStreamThread(packetsize) : new eDVBRecordFileThread(packetsize, recordingBufferCount)),
	m_packetsize(packetsize)
{
	CONNECT(m_thread->m_event, eDVBTSRecorder::filepushEvent);
#ifndef HAVE_ADD_PID
	m_demux->m_dvr_busy = 1;
#endif
}

eDVBTSRecorder::~eDVBTSRecorder()
{
	stop();
	delete m_thread;
#ifndef HAVE_ADD_PID
	m_demux->m_dvr_busy = 0;
#endif
}

RESULT eDVBTSRecorder::start()
{
	std::map<int,int>::iterator i(m_pids.begin());

	if (m_running)
		return -1;
	
	if (m_target_fd == -1)
		return -2;

	if (i == m_pids.end())
		return -3;

	char filename[128];
#ifndef HAVE_ADD_PID
#if HAVE_DVB_API_VERSION < 3
	snprintf(filename, 128, "/dev/dvb/card%d/dvr%d", m_demux->adapter, m_demux->demux);
#else
	snprintf(filename, 128, "/dev/dvb/adapter%d/dvr%d", m_demux->adapter, m_demux->demux);
#endif
	m_source_fd = ::open(filename, O_RDONLY);
	
	if (m_source_fd < 0)
	{
		eDebug("FAILED to open dvr (%s) in ts recoder (%m)", filename);
		return -3;
	}
#else
	snprintf(filename, 128, "/dev/dvb/adapter%d/demux%d", m_demux->adapter, m_demux->demux);

	m_source_fd = ::open(filename, O_RDONLY);
	
	if (m_source_fd < 0)
	{
		eDebug("FAILED to open demux (%s) in ts recoder (%m)", filename);
		return -3;
	}

	{
		int size = demuxSize;
		if (m_packetsize != 188)
		{
			size /= 188;
			size *= m_packetsize;
		}
		eDebug("Demux size: %d", size);
		setBufferSize(size);
	}

	dmx_pes_filter_params flt;
#if HAVE_DVB_API_VERSION > 3
	flt.pes_type = DMX_PES_OTHER;
	flt.output  = DMX_OUT_TSDEMUX_TAP;
#else
	flt.pes_type = (dmx_pes_type_t)DMX_TAP_TS;
	flt.output  = DMX_OUT_TAP;
#endif
	flt.pid     = i->first;
	++i;
	flt.input   = DMX_IN_FRONTEND;
	flt.flags   = 0;
	int res = ::ioctl(m_source_fd, DMX_SET_PES_FILTER, &flt);
	if (res)
	{
		eDebug("DMX_SET_PES_FILTER: %m");
		::close(m_source_fd);
		m_source_fd = -1;
		return -3;
	}
	
	::ioctl(m_source_fd, DMX_START);
	
#endif

	if (!m_target_filename.empty())
		m_thread->startSaveMetaInformation(m_target_filename);
	
	m_thread->start(m_source_fd);
	m_running = 1;

	while (i != m_pids.end()) {
		startPID(i->first);
		++i;
	}

	return 0;
}

RESULT eDVBTSRecorder::setBufferSize(int size)
{
	int res = ::ioctl(m_source_fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("eDVBTSRecorder DMX_SET_BUFFER_SIZE failed(%m)");
	return res;
}

RESULT eDVBTSRecorder::addPID(int pid)
{
	if (m_pids.find(pid) != m_pids.end())
		return -1;
	
	m_pids.insert(std::pair<int,int>(pid, -1));
	if (m_running)
		startPID(pid);
	return 0;
}

RESULT eDVBTSRecorder::removePID(int pid)
{
	if (m_pids.find(pid) == m_pids.end())
		return -1;
		
	if (m_running)
		stopPID(pid);
	
	m_pids.erase(pid);
	return 0;
}

RESULT eDVBTSRecorder::setTimingPID(int pid, int type)
{
	m_thread->setTimingPID(pid, type);
	return 0;
}

RESULT eDVBTSRecorder::setTargetFD(int fd)
{
	m_target_fd = fd;
	m_thread->setTargetFD(fd);
	return 0;
}

RESULT eDVBTSRecorder::setTargetFilename(const std::string& filename)
{
	m_target_filename = filename;
	return 0;
}

RESULT eDVBTSRecorder::enableAccessPoints(bool enable)
{
	m_thread->enableAccessPoints(enable);
	return 0;
}

RESULT eDVBTSRecorder::setBoundary(off_t max)
{
	return -1; // not yet implemented
}

RESULT eDVBTSRecorder::stop()
{
	int state=3;

	for (std::map<int,int>::iterator i(m_pids.begin()); i != m_pids.end(); ++i)
		stopPID(i->first);

	if (!m_running)
		return -1;

#if HAVE_DVB_API_VERSION >= 5
	/* workaround for record thread stop */
	if (m_source_fd >= 0)
	{
		if (::ioctl(m_source_fd, DMX_STOP) < 0)
			perror("DMX_STOP");
		else
			state &= ~1;

		if (::close(m_source_fd) < 0)
			perror("close");
		else
			state &= ~2;
		m_source_fd = -1;
	}
#endif

	m_thread->stop();

	if (state & 3)
	{
		if (m_source_fd >= 0)
		{
			::close(m_source_fd);
			m_source_fd = -1;
		}
	}

	m_running = 0;

	m_thread->stopSaveMetaInformation();
	return 0;
}

RESULT eDVBTSRecorder::getCurrentPCR(pts_t &pcr)
{
	if (!m_running)
		return 0;
	if (!m_thread)
		return 0;
		/* XXX: we need a lock here */

			/* we don't filter PCR data, so just use the last received PTS, which is not accurate, but better than nothing */
	return m_thread->getLastPTS(pcr);
}

RESULT eDVBTSRecorder::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eDVBTSRecorder::startPID(int pid)
{
#ifndef HAVE_ADD_PID
	int fd = m_demux->openDemux();
	if (fd < 0)
	{
		eDebug("FAILED to open demux in ts recoder (%m)");
		return -1;
	}

#if HAVE_DVB_API_VERSION < 3
	dmxPesFilterParams flt;
	
	flt.pesType = DMX_PES_OTHER;
#else
	dmx_pes_filter_params flt;
	
	flt.pes_type = DMX_PES_OTHER;
#endif

	flt.pid     = pid;
	flt.input   = DMX_IN_FRONTEND;
	flt.output  = DMX_OUT_TS_TAP;
	
	flt.flags   = DMX_IMMEDIATE_START;

	int res = ::ioctl(fd, DMX_SET_PES_FILTER, &flt);
	if (res < 0)
	{
		eDebug("set pes filter failed!");
		::close(fd);
		return -1;
	}
	m_pids[pid] = fd;
#else
	while(true) {
#if HAVE_DVB_API_VERSION > 3
		__u16 p = pid;
		if (::ioctl(m_source_fd, DMX_ADD_PID, &p) < 0) {
#else
		if (::ioctl(m_source_fd, DMX_ADD_PID, pid) < 0) {
#endif
			perror("DMX_ADD_PID");
			if (errno == EAGAIN || errno == EINTR) {
				eDebug("retry!");
				continue;
			}
		} else
			m_pids[pid] = 1;
		break;
	}
#endif
	return 0;
}

void eDVBTSRecorder::stopPID(int pid)
{
#ifndef HAVE_ADD_PID
	if (m_pids[pid] != -1)
		::close(m_pids[pid]);
#else
	if (m_pids[pid] != -1)
	{
		while(true) {
#if HAVE_DVB_API_VERSION > 3
			__u16 p = pid;
			if (::ioctl(m_source_fd, DMX_REMOVE_PID, &p) < 0) {
#else
			if (::ioctl(m_source_fd, DMX_REMOVE_PID, pid) < 0) {
#endif
				perror("DMX_REMOVE_PID");
				if (errno == EAGAIN || errno == EINTR) {
					eDebug("retry!");
					continue;
				}
			}
			break;
		}
	}
#endif
	m_pids[pid] = -1;
}

void eDVBTSRecorder::filepushEvent(int event)
{
	switch (event)
	{
	case eFilePushThread::evtWriteError:
		m_event(eventWriteError);
		break;
	}
}
