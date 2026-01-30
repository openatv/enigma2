#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <sys/sysinfo.h>
#include <sys/mman.h>

#include <linux/dvb/dmx.h>

#include <lib/base/eerror.h>
#include <lib/base/cfile.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/decoder.h>

#include "crc32.h"

#ifndef DMX_SET_SOURCE
/**
 * DMX_SET_SOURCE and dmx_source enum removed on 4.14 kernel
 * Check commit 13adefbe9e566c6db91579e4ce17f1e5193d6f2c
**/
enum dmx_source {
	DMX_SOURCE_FRONT0 = 0,
	DMX_SOURCE_FRONT1,
	DMX_SOURCE_FRONT2,
	DMX_SOURCE_FRONT3,
	DMX_SOURCE_DVR0   = 16,
	DMX_SOURCE_DVR1,
	DMX_SOURCE_DVR2,
	DMX_SOURCE_DVR3
};
#define DMX_SET_SOURCE _IOW('o', 49, enum dmx_source)
#endif

//#define SHOW_WRITE_TIME
static int determineBufferCount()
{
	struct sysinfo si = {};
	if (sysinfo(&si) != 0)
	{
		return 6; // Default to small
	}
	unsigned int megabytes = si.totalram >> 20;
	int result;
	if (megabytes > 400)
		result = 40; // 1024MB systems: Use 8MB IO buffers (vusolo2, vuduo2, ...)
	else if (megabytes > 200)
		result = 20; // 512MB systems: Use 4MB IO buffers (et9x00, vuultimo, ...)
	else if (megabytes > 100)
		result = 16; // 256MB systems: Use 3MB demux buffers (dm8000, et5x00, vuduo)
	else
		result = 8; // Smaller boxes: Use 1.5MB buffer
	return result;
}

static int recordingBufferCount = determineBufferCount();

eDVBDemux::eDVBDemux(int adapter, int demux):
	adapter(adapter),
	demux(demux),
	source(-1),
	m_dvr_busy(0),
	m_dvr_id(-1),
	m_dvr_source_offset(DMX_SOURCE_DVR0)
{
	if (CFile::parseInt(&m_dvr_source_offset, "/proc/stb/frontend/dvr_source_offset") == 0)
		eDebug("[eDVBDemux] using %d for PVR DMX_SET_SOURCE", m_dvr_source_offset);

}

eDVBDemux::~eDVBDemux()
{
}

int eDVBDemux::openDemux(void)
{
	char filename[32] = {};
	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/demux%d", adapter, demux);
	eTrace("[eDVBDemux] Open demux '%s'.", filename);
	int fd = ::open(filename, O_RDWR | O_CLOEXEC);
	if (fd < 0)
		eDebug("[eDVBDemux] Error: Unable to open demux '%s'!", filename);
	return fd;
}

int eDVBDemux::openDVR(int flags)
{
	char filename[32];
	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/dvr%d", adapter, demux);
	eDebug("[eDVBDemux] open dvr %s", filename);
	return ::open(filename, flags);
}

DEFINE_REF(eDVBDemux)

RESULT eDVBDemux::setSourceFrontend(int fenum)
{
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = DMX_SOURCE_FRONT0 + fenum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	if (res)
		eDebug("[eDVBDemux] DMX_SET_SOURCE Frontend%d failed: %m", fenum);
	else
		source = fenum;
	::close(fd);
	return res;
}

RESULT eDVBDemux::setSourcePVR(int pvrnum)
{
	int fd = openDemux();
	if (fd < 0) return -1;
	int n = m_dvr_source_offset + pvrnum;
	int res = ::ioctl(fd, DMX_SET_SOURCE, &n);
	if (res)
		eDebug("[eDVBDemux] DMX_SET_SOURCE dvr%d failed: %m", pvrnum);
	source = -1;
	m_dvr_id = pvrnum;
	::close(fd);
	return res;
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

RESULT eDVBDemux::createTSRecorder(ePtr<iDVBTSRecorder> &recorder, unsigned int packetsize, bool streaming, bool sync_mode, bool is_streaming_output)
{
	if (m_dvr_busy)
		return -EBUSY;
	// Note: scrambled thread selection is now done via setDescrambler()
	// If streaming=true, use eDVBRecordStreamThread, else use eDVBRecordScrambledThread
	// (which supports descrambling when a descrambler is attached)
	// sync_mode=true for Live-TV (DVR device), false for recording (file)
	// is_streaming_output=true when target is a socket (encrypted streaming)
	recorder = new eDVBTSRecorder(this, packetsize, streaming, sync_mode, is_streaming_output);
	return 0;
}

RESULT eDVBDemux::getMPEGDecoder(ePtr<iTSMPEGDecoder> &decoder, int index)
{
	decoder = new eTSMPEGDecoder(this, index);
	return 0;
}

RESULT eDVBDemux::getSTC(pts_t &pts, int num)
{
	int fd = openDemux();

	if (fd < 0)
		return -ENODEV;

	struct dmx_stc stc = {};
	stc.num = num;
	stc.base = 1;

	if (ioctl(fd, DMX_GET_STC, &stc) < 0)
	{
		eDebug("[eDVBDemux] DMX_GET_STC failed: %m");
		::close(fd);
		return -1;
	}

	pts = stc.stc;

	eDebug("[eDVBDemux] DMX_GET_STC - %lld", pts);

	::close(fd);
	return 0;
}

RESULT eDVBDemux::flush()
{
	// FIXME: implement flushing the PVR queue here.

	m_event(evtFlush);
	return 0;
}

RESULT eDVBDemux::connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

void eDVBSectionReader::data(int)
{
	uint8_t data[4096] = {}; // max. section size
	int r;
	r = ::read(fd, data, 4096);
	if(r < 0)
	{
		eWarning("[eDVBSectionReader] ERROR reading section - %m\n");
		return;
	}
	if (checkcrc)
	{
		// this check should never happen unless the driver is crappy!
		unsigned int c;
		if ((c = crc32((unsigned)-1, data, r)))
		{
			//eDebug("[eDVBSectionReader] section crc32 failed! is %x\n", c);
			return;
		}
	}
	if (active)
		read(data);
	else
		eDebug("[eDVBSectionReader] data.. but not active");
}

eDVBSectionReader::eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res): demux(demux), active(0)
{
	fd = demux->openDemux();

	if (fd >= 0)
	{
		notifier=eSocketNotifier::create(context, fd, eSocketNotifier::Read, false);
		CONNECT(notifier->activated, eDVBSectionReader::data);
		res = 0;
	} else
	{
		eWarning("[eDVBSectionReader] demux->openDemux failed: %m");
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
		eDebug("[eDVBSectionReader] DMX_SET_BUFFER_SIZE %d failed: %m", size);
	return res;
}

RESULT eDVBSectionReader::start(const eDVBSectionFilterMask &mask)
{
	RESULT res;
	if (fd < 0)
		return -ENODEV;

	eTrace("[eDVBSectionReader] DMX_SET_FILTER pid=%d", mask.pid);
	notifier->start();

	dmx_sct_filter_params sct = {};
	memset(&sct, 0, sizeof(sct));
	sct.pid     = mask.pid;
	sct.timeout = 0;
	sct.flags   = DMX_IMMEDIATE_START;

	if (mask.flags & eDVBSectionFilterMask::rfCRC)
	{
		sct.flags |= DMX_CHECK_CRC;
		checkcrc = 1;
	} else
		checkcrc = 0;

	memcpy(sct.filter.filter, mask.data, DMX_FILTER_SIZE);
	memcpy(sct.filter.mask, mask.mask, DMX_FILTER_SIZE);
	memcpy(sct.filter.mode, mask.mode, DMX_FILTER_SIZE);
	setBufferSize(8192*8);

	res = ::ioctl(fd, DMX_SET_FILTER, &sct);
	if (!res)
	{
		active = 1;
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

RESULT eDVBSectionReader::connectRead(const sigc::slot<void(const uint8_t*)> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, read.connect(r));
	return 0;
}

void eDVBPESReader::data(int)
{
	while (1)
	{
		uint8_t buffer[16384] = {};
		int r;
		r = ::read(m_fd, buffer, 16384);
		if (!r)
			return;
		if(r < 0)
		{
			if (errno == EAGAIN || errno == EINTR) /* ok */
				return;
			eWarning("[eDVBPESReader] ERROR reading PES (fd=%d): %m", m_fd);
			return;
		}

		if (m_active)
			m_read(buffer, r);
		else
			eWarning("[eDVBPESReader] PES reader not active");
		if (r != 16384)
			break;
	}
}

eDVBPESReader::eDVBPESReader(eDVBDemux *demux, eMainloop *context, RESULT &res): m_demux(demux), m_active(0)
{
	eWarning("[eDVBPESReader] Created. Opening demux");
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
		eWarning("[eDVBPESReader] openDemux failed: %m");
		res = errno;
	}
}

RESULT eDVBPESReader::setBufferSize(int size)
{
	int res = ::ioctl(m_fd, DMX_SET_BUFFER_SIZE, size);
	if (res < 0)
		eDebug("[eDVBPESReader] DMX_SET_BUFFER_SIZE %d failed: %m", size);
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

	eDebug("[eDVBPESReader] DMX_SET_PES_FILTER pid=%04x", pid);
	m_notifier->start();

	dmx_pes_filter_params flt = {};
	memset(&flt, 0, sizeof(flt));

	flt.pes_type = DMX_PES_OTHER;
	flt.pid     = pid;
	flt.input   = DMX_IN_FRONTEND;
	flt.output  = DMX_OUT_TAP;

	flt.flags   = DMX_IMMEDIATE_START;

	res = ::ioctl(m_fd, DMX_SET_PES_FILTER, &flt);

	if (res)
		eWarning("[eDVBPESReader] DMX_SET_PES_FILTER pid=%04x:  %m", pid);
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

RESULT eDVBPESReader::connectRead(const sigc::slot<void(const uint8_t*,int)> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_read.connect(r));
	return 0;
}

eDVBRecordFileThread::eDVBRecordFileThread(int packetsize, int bufferCount, int buffersize, bool sync_mode) :
	/*
	 * Note on buffer size: Usually this is calculated from packet size and an evaluated number of buffers.
	 * for the Broadcom encoder we need to have a fixed buffer size though, so we must be able to override
	 * the calculation. This could be faked by using a packet size of 47, but apparently other code
	 * can't handle that and segfaults. If you want the "normal" behaviour, just use -1 (or leave it out
	 * completely, the default declaration).
	 */
	eFilePushThreadRecorder(
		/*buffer*/ (unsigned char*) ::mmap(NULL, (buffersize > 0) ? (buffersize * bufferCount) : (bufferCount * packetsize * 1024), PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, /*ignored*/-1, 0),
		/*buffersize*/ (buffersize > 0) ? buffersize : (packetsize * 1024)),
	 m_ts_parser(packetsize),
	 m_current_offset(0),
	 m_fd_dest(-1),
	 m_sync_mode(sync_mode),
	 m_aio(bufferCount),
	 m_current_buffer(m_aio.begin()),
	 m_buffer_use_histogram(bufferCount+1, 0)
{
	if (m_buffer == MAP_FAILED)
		eFatal("[eDVBRecordFileThread] Failed to allocate filepush buffer, contact MiLo\n");
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

void eDVBRecordFileThread::setTimingPID(int pid, iDVBTSRecorder::timing_pid_type pidtype, int streamtype)
{
	m_ts_parser.setPid(pid, pidtype, streamtype);
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

int eDVBRecordFileThread::getFirstPTS(pts_t &pts)
{
	return m_ts_parser.getFirstPTS(pts);
}

int eDVBRecordFileThread::AsyncIO::wait(volatile int* stop_flag)
{
	if (aio.aio_buf == NULL) // Only if we had a request outstanding
		return 0;

	// Limit consecutive timeouts to prevent infinite blocking
	const int MAX_TIMEOUTS = 5;
	int timeout_count = 0;

	while (true)
	{
		// Wait for current operation to complete with timeout
		while (aio_error(&aio) == EINPROGRESS)
		{
			eDebug("[eDVBRecordFileThread] Waiting for I/O to complete");
			struct aiocb* paio = &aio;
			struct timespec timeout = {1, 0}; // 1 second timeout
			int r = aio_suspend(&paio, 1, &timeout);
			if (r < 0)
			{
				if (errno == EAGAIN) // Timeout
				{
					timeout_count++;
					eDebug("[eDVBRecordFileThread] aio_suspend timeout (%d/%d)",
						timeout_count, MAX_TIMEOUTS);

					// Check if we should stop
					if (stop_flag && *stop_flag)
					{
						eDebug("[eDVBRecordFileThread] stop requested, cancelling AIO");
						aio_cancel(aio.aio_fildes, &aio);
						aio.aio_buf = NULL;
						return -1;
					}

					// After MAX_TIMEOUTS, cancel AIO and continue (don't block forever)
					if (timeout_count >= MAX_TIMEOUTS)
					{
						eWarning("[eDVBRecordFileThread] AIO timeout limit reached, cancelling and continuing");
						aio_cancel(aio.aio_fildes, &aio);
						aio.aio_buf = NULL;
						return 0; // Return 0 so thread continues!
					}
					continue;
				}
				if (errno == EINTR)
				{
					// Check if we should stop after signal
					if (stop_flag && *stop_flag)
					{
						eDebug("[eDVBRecordFileThread] stop requested after EINTR");
						aio_cancel(aio.aio_fildes, &aio);
						aio.aio_buf = NULL;
						return -1;
					}
					continue;
				}
				eDebug("[eDVBRecordFileThread] aio_suspend failed: %m");
				return -1;
			}
		}

		int r = aio_return(&aio);
		aio.aio_buf = NULL;
		if (r < 0)
		{
			eDebug("[eDVBRecordFileThread] wait: aio_return failed: %m");
			aio.aio_buf = NULL;
			return -1;
		}

		// Handle short write - retry remaining bytes
		if ((size_t)r != aio.aio_nbytes)
		{
			eDebug("[eDVBRecordFileThread] wait: short write %d of %zu bytes -> retry", r, aio.aio_nbytes);
			aio.aio_nbytes -= r;
			aio.aio_offset += r;
			aio.aio_buf = (volatile void*)((const char*)aio.aio_buf + r);
			if (aio_write(&aio) < 0)
			{
				eDebug("[eDVBRecordFileThread] wait: aio_write retry failed: %m");
				aio.aio_buf = NULL;
				return -1;
			}
			continue; // Wait for retry to complete
		}

		aio.aio_buf = NULL;
		return 0;
	}
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

	if (r >= 0 && (size_t)r != aio.aio_nbytes)
	{ // short write
		eDebug("[eDVBRecordFileThread] short write: %d of bytes %d written -> retry", r, aio.aio_nbytes);
		aio.aio_nbytes -= r;
		aio.aio_offset += r;
		aio.aio_buf = (volatile void*)((const char*)aio.aio_buf + r);
		if (aio_write(&aio) < 0)
			return -1;
		return 1;
	}

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
	struct timeval starttime = {};
	struct timeval now = {};
	suseconds_t diff;
	gettimeofday(&starttime, NULL);
#endif
	// Only call parseData here if no descrambler is set.
	// When a descrambler is active, eDVBRecordScrambledThread::writeData()
	// calls parseData AFTER descrambling to ensure we parse clear data.
	if (!getProtocol() && !m_serviceDescrambler)
	{
		int parse_result = m_ts_parser.parseData(m_current_offset, m_buffer, len);
		if (parse_result == -2)
		{
			m_event(eFilePushThreadRecorder::evtStreamCorrupt);
			return len;
		}
	}

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
			eWarning("[eFilePushThreadRecorder] Warning: All write buffers busy");
			break;
		}
		r = i->poll();
		if (r < 0)
		{
			eWarning("[eDVBRecordFileThread] poll failed: %d", r);
			return r;
		}
	}
	++m_buffer_use_histogram[busy_count];

	++m_current_buffer;
	if (m_current_buffer == m_aio.end())
		m_current_buffer = m_aio.begin();
	m_buffer = m_current_buffer->buffer;
	return len;
}

// Static flag: Once AIO is detected as unsupported (ENOSYS), all future threads use sync mode
// This persists until Enigma2 restart - no point retrying AIO on every channel change
static bool s_aio_not_supported = false;

int eDVBRecordFileThread::writeData(int len)
{
	if (!len || !m_buffer)
		return 0;

	// Use sync mode if: explicitly configured OR AIO was detected as unsupported
	if (m_sync_mode || s_aio_not_supported)
	{
		// Synchronous write mode with timeout to prevent blocking forever
		struct pollfd pfd = {};
		pfd.fd = m_fd_dest;
		pfd.events = POLLOUT;
		int poll_ret = poll(&pfd, 1, 1000); // 1 second timeout

		if (poll_ret == 0)
		{
			eDebug("[eDVBRecordFileThread] sync write poll timeout");
			return 0; // Timeout - return 0 to retry
		}
		if (poll_ret < 0)
		{
			if (errno == EINTR)
				return 0; // Interrupted - return 0 to retry
			eWarning("[eDVBRecordFileThread] sync write poll error: %m");
			return -1;
		}
		// Only call parseData here if no descrambler is set.
		// When a descrambler is active, eDVBRecordScrambledThread::writeData()
		// calls parseData AFTER descrambling to ensure we parse clear data.
		if (!getProtocol() && !m_serviceDescrambler)
		{
			m_ts_parser.parseData(m_current_offset, m_buffer, len);
		}

		int written = 0;
		while (written < len)
		{
			ssize_t w = ::write(m_fd_dest, m_buffer + written, len - written);
			if (w > 0)
			{
				written += w;
				continue;
			}
			if (w < 0 && errno == EINTR)
				continue;
			if (w < 0 && (errno == EAGAIN || errno == EWOULDBLOCK))
			{
				usleep(1000);
				continue;
			}
			eWarning("[eDVBRecordFileThread] sync write error: %m");
			return -1;
		}
		m_current_offset += len;
		return len;
	}
	else
	{
		// Asynchronous write mode - better performance with buffer rotation
		len = asyncWrite(len);
		if (len < 0)
		{
			// Check for ENOSYS (AIO not supported by kernel) - automatic fallback to sync
			if (errno == ENOSYS)
			{
				eWarning("[eDVBRecordFileThread] AIO not supported (ENOSYS), falling back to sync mode");
				s_aio_not_supported = true;  // Remember globally for all future threads
				m_sync_mode = true;
				// Retry this write in sync mode (recursive call, now using sync path)
				return writeData(m_buffersize);
			}
			eWarning("[eDVBRecordFileThread] asyncWrite failed: %d", len);
			return len;
		}
		// Wait for previous aio to complete on this buffer before returning
		int r = m_current_buffer->wait(&m_stop);
		if (r < 0)
		{
			// Check for ENOSYS in wait (aio_return) - automatic fallback to sync
			if (errno == ENOSYS)
			{
				eWarning("[eDVBRecordFileThread] AIO not supported (ENOSYS in wait), falling back to sync mode");
				s_aio_not_supported = true;  // Remember globally for all future threads
				m_sync_mode = true;
				// Data was already submitted to asyncWrite, but we can't get the result
				// Future writes will use sync mode
				return len;
			}
			eWarning("[eDVBRecordFileThread] wait failed: %d", r);
			return -1;
		}
		return len;
	}
}

void eDVBRecordFileThread::flush()
{
	eDebug("[eDVBRecordFileThread] waiting for aio to complete");
	for (AsyncIOvector::iterator it = m_aio.begin(); it != m_aio.end(); ++it)
	{
		if (m_stop)
		{
			eDebug("[eDVBRecordFileThread] flush: stop requested, cancelling remaining AIOs");
			// Cancel all remaining AIOs without waiting
			for (; it != m_aio.end(); ++it)
			{
				it->cancel(m_fd_dest);
			}
			break;
		}
		if (it->wait(&m_stop) < 0 && m_stop)
		{
			eDebug("[eDVBRecordFileThread] flush: wait failed and stop requested, aborting");
			break;
		}
	}
	int bufferCount = m_aio.size();
	eDebug("[eDVBRecordFileThread] buffer usage histogram (%d buffers of %lu kB)", bufferCount, m_buffersize>>10);
	for (int i=0; i <= bufferCount; ++i)
	{
		if (m_buffer_use_histogram[i] != 0)
			eDebug("[eDVBRecordFileThread]  %2d: %6d", i, m_buffer_use_histogram[i]);
	}
	if (m_overflow_count)
	{
		eDebug("[eDVBRecordFileThread] Demux buffer overflows: %d", m_overflow_count);
	}
	if (m_fd_dest >= 0)
	{
		posix_fadvise(m_fd_dest, 0, 0, POSIX_FADV_DONTNEED);
	}
}

eDVBRecordStreamThread::eDVBRecordStreamThread(int packetsize, int buffersize, bool sync_mode) :
	eDVBRecordFileThread(packetsize, recordingBufferCount, buffersize, sync_mode)
{
	eDebug("[eDVBRecordStreamThread] allocated %zu buffers of %zu kB", m_aio.size(), m_buffersize>>10);
}


int eDVBRecordStreamThread::writeData(int len)
{
	if(m_sync_mode)
	{
		struct pollfd pfd = {};
		int pos = 0;
		int w = 0;
		int count = 0;

		do
		{
			pfd.fd = m_fd_dest;
			pfd.events = POLLOUT;
			poll(&pfd, 1, -1);

			w = write(m_fd_dest, m_buffer + pos, len - pos);

			if(w < 0)
			{
				eWarning("[eDVBRecordStreamThread] writedata write error len: %d return: %d %m", len, w);
				return(len);
			}

			if(w == 0)
			{
				eWarning("[eDVBRecordStreamThread] writedata write eof: %d %m", len);
				return(len);
			}

			pos += w;
			count++;
		} while (pos < len && count < 3); // Streams should not be held up. So stop after 3 tries.
		len = pos;
	}
	else
	{
		len = asyncWrite(len);
		if (len < 0)
		{
			eWarning("[eDVBRecordStreamThread] asyncWrite returns %d\n", len);
			return len;
		}
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
		r = m_current_buffer->wait(&m_stop);
		if (r < 0)
		{
			eDebug("[eDVBRecordStreamThread] wait failed: %m");
			return -1;
		}
	}

	return len;
}

void eDVBRecordStreamThread::flush()
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

eDVBRecordScrambledThread::eDVBRecordScrambledThread(int packetsize, int buffersize, bool sync_mode, bool is_streaming) :
	eDVBRecordStreamThread(packetsize, buffersize, sync_mode),
	m_first_data_written(false),
	m_is_streaming(is_streaming)
{
	pthread_mutex_init(&m_data_ready_mutex, NULL);
	pthread_cond_init(&m_data_ready_cond, NULL);
	// Note: s_aio_not_supported may override sync_mode at runtime in writeData()
	const char* mode = sync_mode ? "sync" : (s_aio_not_supported ? "sync (AIO unavailable)" : "async");
	eDebug("[eDVBRecordScrambledThread] %s allocated %zu buffers of %zu kB (streaming=%d)",
		mode, m_aio.size(), m_buffersize>>10, is_streaming);
}

eDVBRecordScrambledThread::~eDVBRecordScrambledThread()
{
	pthread_cond_destroy(&m_data_ready_cond);
	pthread_mutex_destroy(&m_data_ready_mutex);
}

void eDVBRecordScrambledThread::resetFirstDataFlag()
{
	pthread_mutex_lock(&m_data_ready_mutex);
	m_first_data_written = false;
	pthread_mutex_unlock(&m_data_ready_mutex);
}

bool eDVBRecordScrambledThread::waitForFirstData(int timeout_ms)
{
	struct timespec ts;
	clock_gettime(CLOCK_REALTIME, &ts);
	ts.tv_sec += timeout_ms / 1000;
	ts.tv_nsec += (timeout_ms % 1000) * 1000000;
	if (ts.tv_nsec >= 1000000000) {
		ts.tv_sec++;
		ts.tv_nsec -= 1000000000;
	}

	// Wait for DVR data (thread-safe)
	pthread_mutex_lock(&m_data_ready_mutex);
	while (!m_first_data_written)
	{
		int ret = pthread_cond_timedwait(&m_data_ready_cond, &m_data_ready_mutex, &ts);
		if (ret == ETIMEDOUT)
		{
			eDebug("[eDVBRecordScrambledThread] waitForFirstData: DVR timeout after %dms", timeout_ms);
			pthread_mutex_unlock(&m_data_ready_mutex);
			return false;
		}
	}
	pthread_mutex_unlock(&m_data_ready_mutex);
	eDebug("[eDVBRecordScrambledThread] waitForFirstData: DVR data ready");

	return true;
}

int eDVBRecordScrambledThread::writeData(int len)
{
	// Descramble if we have a descrambler - ignore return value
	// This allows CI+, StreamRelay and FTA to pass through unchanged
	// (data is already clear or hardware-descrambled)
	// For SoftCSA: descrambles in-place when CW available,
	// passes through encrypted when no CW (may cause artifacts at channel start)
	if (m_serviceDescrambler)
		m_serviceDescrambler->descramble(m_buffer, len);

	// Parse AFTER descrambling for correct Access Points (.ap files)
	// This is needed because asyncWrite/writeData skip parseData when m_serviceDescrambler is set
	if (!getProtocol())
	{
		m_ts_parser.parseData(m_current_offset, m_buffer, len);
	}

	// Call the appropriate parent writeData based on target type:
	// - Streaming (socket): use eDVBRecordStreamThread::writeData() for proper socket handling
	// - Recording (file): use eDVBRecordFileThread::writeData() for file I/O
	int ret;
	if (m_is_streaming)
		ret = eDVBRecordStreamThread::writeData(len);
	else
		ret = eDVBRecordFileThread::writeData(len);

	// Signal first data written (for decoder sync)
	if (ret > 0 && !m_first_data_written)
	{
		pthread_mutex_lock(&m_data_ready_mutex);
		if (!m_first_data_written)
		{
			m_first_data_written = true;
			eDebug("[eDVBRecordScrambledThread] First data written (%d bytes), signaling", ret);
			pthread_cond_signal(&m_data_ready_cond);
		}
		pthread_mutex_unlock(&m_data_ready_mutex);
	}

	return ret;
}


DEFINE_REF(eDVBTSRecorder);

eDVBTSRecorder::eDVBTSRecorder(eDVBDemux *demux, int packetsize, bool streaming, bool sync_mode, bool is_streaming_output):
	m_demux(demux),
	m_running(0),
	m_target_fd(-1),
	m_packetsize(packetsize)
{
	if (streaming)
		// For streaming: use StreamThread for FTA (no descrambling needed)
		// Encrypted streams use streaming=false and get ScrambledThread
		m_thread = new eDVBRecordStreamThread(packetsize);
	else
		// Use ScrambledThread for file recording - supports optional descrambling
		// Buffer size 256*188 = 47kB - larger buffers cause latency issues
		// sync_mode=true for Live-TV (DVR device has small buffers, frequent short writes)
		// sync_mode=false for recording/timeshift (file has large buffers, async is faster)
		// is_streaming_output=true when target is a socket (streaming encrypted channels)
		m_thread = new eDVBRecordScrambledThread(packetsize, 256*188, sync_mode, is_streaming_output);
	CONNECT(m_thread->m_event, eDVBTSRecorder::filepushEvent);
}

eDVBTSRecorder::~eDVBTSRecorder()
{
	stop();
	delete m_thread;
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
	snprintf(filename, 128, "/dev/dvb/adapter%d/demux%d", m_demux->adapter, m_demux->demux);

#if HAVE_HISILICON
	m_source_fd = ::open(filename, O_RDONLY | O_CLOEXEC | O_NONBLOCK);
#else
	m_source_fd = ::open(filename, O_RDONLY | O_CLOEXEC);
#endif

	if (m_source_fd < 0)
	{
		eDebug("[eDVBTSRecorder] FAILED to open demux %s: %m", filename);
		return -3;
	}

	setBufferSize(1024*1024);

	dmx_pes_filter_params flt = {};
	memset(&flt, 0, sizeof(flt));

	flt.pes_type = DMX_PES_OTHER;
	flt.output  = DMX_OUT_TSDEMUX_TAP;
	flt.pid     = i->first;
	++i;
	flt.input   = DMX_IN_FRONTEND;
	flt.flags   = (m_packetsize == 192) ? 0x80000000 : 0;
	int res = ::ioctl(m_source_fd, DMX_SET_PES_FILTER, &flt);
	if (res)
	{
		eDebug("[eDVBTSRecorder] DMX_SET_PES_FILTER pid=%04x: %m", flt.pid);
		::close(m_source_fd);
		m_source_fd = -1;
		return -3;
	}

	::ioctl(m_source_fd, DMX_START);

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
		eDebug("[eDVBTSRecorder] DMX_SET_BUFFER_SIZE %d failed: %m", size);
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

RESULT eDVBTSRecorder::setTimingPID(int pid, timing_pid_type pidtype, int streamtype)
{
	m_thread->setTimingPID(pid, pidtype, streamtype);
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

	/* workaround for record thread stop */
	if (m_source_fd >= 0)
	{
		if (::ioctl(m_source_fd, DMX_STOP) < 0)
			eWarning("[eDVBTSRecorder] DMX_STOP: %m");
		else
			state &= ~1;

		if (::close(m_source_fd) < 0)
			eWarning("[eDVBTSRecorder] close: %m");
		else
			state &= ~2;
		m_source_fd = -1;
	}

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

RESULT eDVBTSRecorder::getFirstPTS(pts_t &pts)
{
	if (!m_running || !m_thread)
		return 0;

	return m_thread->getFirstPTS(pts);
}

RESULT eDVBTSRecorder::connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eDVBTSRecorder::startPID(int pid)
{
	while(true) {
		uint16_t p = pid;
		if (::ioctl(m_source_fd, DMX_ADD_PID, &p) < 0) {
			eWarning("[eDVBTSRecorder] DMX_ADD_PID pid=%04x: %m", pid);
			if (errno == EAGAIN || errno == EINTR) {
				eDebug("[eDVBTSRecorder] retry!");
				continue;
			}
		} else
			m_pids[pid] = 1;
		break;
	}
	return 0;
}

void eDVBTSRecorder::stopPID(int pid)
{
	if (m_pids[pid] != -1)
	{
		while(true) {
			uint16_t p = pid;
			if (::ioctl(m_source_fd, DMX_REMOVE_PID, &p) < 0) {
				eWarning("[eDVBTSRecorder] DMX_REMOVE_PID pid=%04x: %m", pid);
				if (errno == EAGAIN || errno == EINTR) {
					eDebug("[eDVBTSRecorder] retry!");
					continue;
				}
			}
			break;
		}
	}
	m_pids[pid] = -1;
}

void eDVBTSRecorder::filepushEvent(int event)
{
	switch (event)
	{
	case eFilePushThread::evtWriteError:
		m_event(eventWriteError);
		break;
	case eFilePushThreadRecorder::evtStreamCorrupt:
		eDebug("[eDVBTSRecorder] Stream corruption detected, emitting signal!");
		m_event(eventStreamCorrupt);
		break;
	}
}

RESULT eDVBTSRecorder::setDescrambler(ePtr<iServiceScrambled> serviceDescrambler)
{
	m_thread->setDescrambler(serviceDescrambler);
	return 0;
}

bool eDVBTSRecorder::waitForFirstData(int timeout_ms)
{
	// Delegate to thread - only ScrambledThread actually implements waiting
	// Other thread types return immediately via base class default
	return m_thread->waitForFirstData(timeout_ms);
}
