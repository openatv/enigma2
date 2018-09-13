#include "filepush.h"
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#if defined(__sh__) // this allows filesystem tasks to be prioritised
#include <sys/vfs.h>
#define USBDEVICE_SUPER_MAGIC 0x9fa2
#define EXT2_SUPER_MAGIC 0xEF53
#define EXT3_SUPER_MAGIC 0xEF53
#define SMB_SUPER_MAGIC 0x517B
#define NFS_SUPER_MAGIC 0x6969
#define MSDOS_SUPER_MAGIC 0x4d44 /* MD */
#endif
//#define SHOW_WRITE_TIME

DEFINE_REF(eFilePushThread);
eFilePushThread::eFilePushThread(int io_prio_class, int io_prio_level, int blocksize, size_t buffersize)
	: prio_class(io_prio_class),
	  prio(io_prio_level),
	  m_sg(NULL),
	  m_stop(1),
	  m_send_pvr_commit(0),
	  m_stream_mode(0),
	  m_blocksize(blocksize),
	  m_buffersize(buffersize),
	  m_buffer((unsigned char *)malloc(buffersize)),
	  m_messagepump(eApp, 0),
	  m_run_state(0)
{
	if (m_buffer == NULL)
		eFatal("[eFilePushThread] Failed to allocate %zu bytes", buffersize);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
}

eFilePushThread::~eFilePushThread()
{
	stop(); /* eThread is borked, always call stop() from d'tor */
	free(m_buffer);
}

static void signal_handler(int x)
{
}

static void ignore_but_report_signals()
{
	/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
}

void eFilePushThread::thread()
{
	ignore_but_report_signals();
	hasStarted(); /* "start()" blocks until we get here */
	setIoPrio(prio_class, prio);
	eDebug("[eFilePushThread] START thread");

	do
	{
		int eofcount = 0;
		int buf_end = 0;
		size_t bytes_read = 0;
		off_t current_span_offset = 0;
		size_t current_span_remaining = 0;

#if defined(__sh__)
		// opens video device for the reverse playback workaround
		// Changes in this file are cause e2 doesnt tell the player to play reverse
		int fd_video = open("/dev/dvb/adapter0/video0", O_RDONLY);
		// Fix to ensure that event evtEOF is called at end of playbackl part 1/3
		bool already_empty = false;
#endif

		while (!m_stop)
		{
			if (m_sg && !current_span_remaining)
			{
#if defined(__sh__) // tells the player to play in reverse
#define VIDEO_DISCONTINUITY _IO('o', 84)
#define DVB_DISCONTINUITY_SKIP 0x01
#define DVB_DISCONTINUITY_CONTINUOUS_REVERSE 0x02
				if ((m_sg->getSkipMode() != 0))
				{
					// inform the player about the jump in the stream data
					// this only works if the video device allows the discontinuity ioctl in read-only mode (patched)
					int param = DVB_DISCONTINUITY_SKIP; // | DVB_DISCONTINUITY_CONTINUOUS_REVERSE;
					int rc = ioctl(fd_video, VIDEO_DISCONTINUITY, (void *)param);
				}
#endif
				m_sg->getNextSourceSpan(m_current_position, bytes_read, current_span_offset, current_span_remaining, m_blocksize);
				ASSERT(!(current_span_remaining % m_blocksize));
				m_current_position = current_span_offset;
				bytes_read = 0;
			}

			size_t maxread = m_buffersize;

			/* if we have a source span, don't read past the end */
			if (m_sg && maxread > current_span_remaining)
				maxread = current_span_remaining;

			/* align to blocksize */
			maxread -= maxread % m_blocksize;

			if (maxread)
			{
#ifdef SHOW_WRITE_TIME
				struct timeval starttime;
				struct timeval now;
				gettimeofday(&starttime, NULL);
#endif
				buf_end = m_source->read(m_current_position, m_buffer, maxread);
#ifdef SHOW_WRITE_TIME
				gettimeofday(&now, NULL);
				suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
				eDebug("[eFilePushThread] read %d bytes time: %9u us", buf_end, (unsigned int)diff);
#endif
			}
			else
				buf_end = 0;

			if (buf_end < 0)
			{
				buf_end = 0;
				/* Check m_stop after interrupted syscall. */
				if (m_stop)
				{
					break;
				}
				if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
					continue;
				if (errno == EOVERFLOW)
				{
					eWarning("[eFilePushThread] OVERFLOW while playback?");
					continue;
				}
				eDebug("[eFilePushThread] read error: %m");
			}

			/* a read might be mis-aligned in case of a short read. */
			int d = buf_end % m_blocksize;
			if (d)
				buf_end -= d;

			if (buf_end == 0)
			{
#ifndef HAVE_ALIEN5				/* on EOF, try COMMITting once. */
				if (m_send_pvr_commit)
				{
					struct pollfd pfd;
					pfd.fd = m_fd_dest;
					pfd.events = POLLIN;
					switch (poll(&pfd, 1, 250)) // wait for 250ms
					{
					case 0:
						eDebug("[eFilePushThread] wait for driver eof timeout");
#if defined(__sh__) // Fix to ensure that event evtEOF is called at end of playbackl part 2/3
						if (already_empty)
						{
							break;
						}
						else
						{
							already_empty = true;
							continue;
						}
#else
						continue;
#endif
					case 1:
						eDebug("[eFilePushThread] wait for driver eof ok");
						break;
					default:
						eDebug("[eFilePushThread] wait for driver eof aborted by signal");
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
							break;
						continue;
					}
				}
#endif
				if (m_stop)
					break;

				/* in stream_mode, we are sending EOF events
				   over and over until somebody responds.

				   in stream_mode, think of evtEOF as "buffer underrun occurred". */
				sendEvent(evtEOF);

				if (m_stream_mode)
				{
					eDebug("[eFilePushThread] reached EOF, but we are in stream mode. delaying 1 second.");
#if HAVE_ALIEN5
				usleep(50000);
#else
					sleep(1);
#endif
					continue;
				}
				else if (++eofcount < 10)
				{
					eDebug("[eFilePushThread] reached EOF, but the file may grow. delaying 1 second.");
#if HAVE_ALIEN5
								usleep(50000);
#else
					sleep(1);
#endif
					continue;
				}
				break;
			}
			else
			{
				/* Write data to mux */
				int buf_start = 0;
				filterRecordData(m_buffer, buf_end);
				while ((buf_start != buf_end) && !m_stop)
				{
					int w = write(m_fd_dest, m_buffer + buf_start, buf_end - buf_start);

					if (w <= 0)
					{
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
						{
							w = 0;
							buf_start = 0;
							buf_end = 0;
							break;
						}
						if (w < 0 && (errno == EINTR || errno == EAGAIN || errno == EBUSY))
						{
#if HAVE_CPULOADFIX
							sleep(2);
#endif
#if HAVE_HISILICON
							usleep(100000);
#endif
#if HAVE_ALIEN5
							usleep(100000);
#endif
							continue;
						}
#if HAVE_ALIEN5
						usleep(50000);
#endif
						eDebug("[eFilePushThread] write: %m");
						sendEvent(evtWriteError);
						break;
					}
					buf_start += w;
				}

				eofcount = 0;
#if defined(__sh__) // Fix to ensure that event evtEOF is called at end of playbackl part 3/3
				already_empty = false;
#endif
				m_current_position += buf_end;
				bytes_read += buf_end;
				if (m_sg)
					current_span_remaining -= buf_end;
			}
#if HAVE_ALIEN5
			usleep(10);
#endif
		}
#if defined(__sh__) // closes video device for the reverse playback workaround
		close(fd_video);
#endif
		sendEvent(evtStopped);

		{ /* mutex lock scope */
			eSingleLocker lock(m_run_mutex);
			m_run_state = 0;
			m_run_cond.signal(); /* Tell them we're here */
			while (m_stop == 2)
			{
				eDebug("[eFilePushThread] PAUSED");
				m_run_cond.wait(m_run_mutex);
			}
			if (m_stop == 0)
				m_run_state = 1;
		}

	} while (m_stop == 0);
	eDebug("[eFilePushThread] STOP");
}

void eFilePushThread::start(ePtr<iTsSource> &source, int fd_dest)
{
	m_source = source;
	m_fd_dest = fd_dest;
	m_current_position = 0;
	m_run_state = 1;
	m_stop = 0;
	run();
}

void eFilePushThread::stop()
{
	/* if we aren't running, don't bother stopping. */
	if (m_stop == 1)
		return;
	m_stop = 1;
	eDebug("[eFilePushThread] stopping thread");
	m_run_cond.signal(); /* Break out of pause if needed */
	sendSignal(SIGUSR1);
	kill(); /* Kill means join actually */
}

void eFilePushThread::pause()
{
	if (m_stop == 1)
	{
		eWarning("[eFilePushThread] pause called while not running");
		return;
	}
	/* Set thread into a paused state by setting m_stop to 2 and wait
	 * for the thread to acknowledge that */
	eSingleLocker lock(m_run_mutex);
	m_stop = 2;
	sendSignal(SIGUSR1);
	m_run_cond.signal(); /* Trigger if in weird state */
	while (m_run_state)
	{
		eDebug("[eFilePushThread] waiting for pause");
		m_run_cond.wait(m_run_mutex);
	}
}

void eFilePushThread::resume()
{
	if (m_stop != 2)
	{
		eWarning("[eFilePushThread] resume called while not paused");
		return;
	}
	/* Resume the paused thread by resetting the flag and
	 * signal the thread to release it */
	eSingleLocker lock(m_run_mutex);
	m_stop = 0;
	m_run_cond.signal(); /* Tell we're ready to resume */
}

void eFilePushThread::enablePVRCommit(int s)
{
	m_send_pvr_commit = s;
}

void eFilePushThread::setStreamMode(int s)
{
	m_stream_mode = s;
}

void eFilePushThread::setScatterGather(iFilePushScatterGather *sg)
{
	m_sg = sg;
}

void eFilePushThread::sendEvent(int evt)
{
	/* add a ref, to make sure the object is not destroyed while the messagepump contains unhandled messages */
	AddRef();
	m_messagepump.send(evt);
}

void eFilePushThread::recvEvent(const int &evt)
{
	m_event(evt);
	/* release the ref which we grabbed in sendEvent() */
	Release();
}

void eFilePushThread::filterRecordData(const unsigned char *data, int len)
{
}

eFilePushThreadRecorder::eFilePushThreadRecorder(unsigned char *buffer, size_t buffersize) : m_fd_source(-1),
																							 m_buffersize(buffersize),
																							 m_buffer(buffer),
																							 m_overflow_count(0),
																							 m_stop(1),
																							 m_messagepump(eApp, 0)
{
	m_protocol = m_stream_id = m_session_id = m_packet_no = 0;
	CONNECT(m_messagepump.recv_msg, eFilePushThreadRecorder::recvEvent);
}

#define copy16(a, i, v)           \
	{                             \
		a[i] = ((v) >> 8) & 0xFF; \
		a[i + 1] = (v)&0xFF;      \
	}
#define copy32(a, i, v)                \
	{                                  \
		a[i] = ((v) >> 24) & 0xFF;     \
		a[i + 1] = ((v) >> 16) & 0xFF; \
		a[i + 2] = ((v) >> 8) & 0xFF;  \
		a[i + 3] = (v)&0xFF;           \
	}
#define _PROTO_RTSP_UDP 1
#define _PROTO_RTSP_TCP 2

int eFilePushThreadRecorder::pushReply(void *buf, int len)
{
	m_reply.insert(m_reply.end(), (unsigned char *)buf, (unsigned char *)buf + len);
	eDebug("pushed reply of %d bytes", len);
	return 0;
}

static int errs;

int64_t eFilePushThreadRecorder::getTick()
{ //ms
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (ts.tv_nsec / 1000000) + (ts.tv_sec * 1000);
}

// wrapper around ::read, to read multiple of 188 or error (it does not block)
int eFilePushThreadRecorder::read_ts(int fd, unsigned char *buf, int size)
{
	int rb = 0, bytes = 0;
	int left = size;
	do
	{
		rb = ::read(fd, buf + bytes, left);
		if (rb > 0 && ((bytes % 188) != 0))
			eDebug("%s read %d out of %d bytes, total %d, size %d, fd %d", ((bytes + rb) % 188) ? "incomplete" : "completed", rb, left, bytes, size, fd);

		if (rb <= 0 && errno != EAGAIN && errno != EINTR)
			return rb;

		if (rb > 0)
		{
			bytes += rb;
			left -= rb;
		}
		if ((bytes % 188) != 0)
		{
			left = 188 - (bytes % 188);
		}

	} while ((bytes % 188) != 0);

	if (bytes == 0)
		return rb;

	return bytes;
}
int eFilePushThreadRecorder::read_dmx(int fd, void *m_buffer, int size)
{
	unsigned char *buf;
	int it = 0, pos = 0, bytes = 0;
	int max_pack = 42;
	int i, left;
	static int cnt;
	unsigned char *b;
	uint64_t start = getTick();
	while (size - pos > 188 + 16)
	{
		left = size - pos - 16;
		left = (left > 188 * max_pack) ? 188 * max_pack : (((int)(left / 188) - 1) * 188);
		if (left < 188)
			break;

		buf = (unsigned char *)m_buffer + pos;

		bytes = read_ts(fd, buf + 16, left);

		if (bytes <= 0 && errno != EAGAIN && errno != EINTR)
		{
			eDebug("error reading from DMX handle %d, errno %d: %m", fd, errno);
			break;
		}

		if (bytes > 0)
		{
			if ((bytes % 188) != 0)
				eDebug("incomplete packet read from %d with size %d", fd, bytes);

			m_packet_no++;
			it++;
			for (i = 0; i < bytes; i += 188)
			{
				b = buf + 16 + i;
				int pid = (b[1] & 0x1F) * 256 + b[2];

				if ((b[3] & 0x80)) // mark decryption failed if not decrypted by enigma
				{
					if ((errs++ % 100) == 0)
						eDebug("decrypt errs %d, pid %d, m_buffer %p, pos %d, buf %p, i %d: %02X %02X %02X %02X", errs, pid, m_buffer, pos, buf, i, b[0], b[1], b[2], b[3]);
					b[1] |= 0x1F;
					b[2] |= 0xFF;
				}
			}
			buf[0] = 0x24;
			buf[1] = 0;
			copy16(buf, 2, (uint16_t)(bytes + 12));
			copy16(buf, 4, 0x8021);
			copy16(buf, 6, m_stream_id);
			copy32(buf, 8, cnt);
			copy32(buf, 12, m_session_id);
			cnt++;
			pos += bytes + 16;
		}
		if (m_reply.size() > 0)
		{
			pos = m_reply.size();
			buf[0] = 0;
			memcpy(m_buffer, m_reply.data(), pos);
			eDebug("added reply of %d bytes", pos, m_buffer);
			m_reply.clear();
			break; // reply to the server ASAP
		}
		uint64_t ts = getTick() - start;

		if ((pos > 0) && (bytes == -1) && (ts > 50)) // do not block more than 50ms if there is available data
			break;

		if (bytes < 0)
			usleep(5000);
	}
	uint64_t ts = getTick() - start;
	if (ts > 1000)
		eDebug("returning %d bytes from %d, last read %d bytes in %jd ms (iteration %d)", pos, size, bytes, ts, m_packet_no);
	if (pos == 0)
		return bytes;
	return pos;
}

void eFilePushThreadRecorder::thread()
{
	setIoPrio(IOPRIO_CLASS_RT, 7);

	eDebug("[eFilePushThreadRecorder] THREAD START");

	/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	memset(&act, 0, sizeof(act));
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);

	hasStarted();
	if (m_protocol == _PROTO_RTSP_TCP)
	{
		int flags = fcntl(m_fd_source, F_GETFL, 0);
		flags |= O_NONBLOCK;
		if (fcntl(m_fd_source, F_SETFL, flags) == -1)
			eDebug("failed setting DMX handle %d in non-blocking mode, error %d: %s", m_fd_source, errno, strerror(errno));
	}
	/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
		ssize_t bytes;
		if (m_protocol == _PROTO_RTSP_TCP)
			bytes = read_dmx(m_fd_source, m_buffer, m_buffersize);
		else
			bytes = ::read(m_fd_source, m_buffer, m_buffersize);
		if (bytes < 0)
		{
			bytes = 0;
			/* Check m_stop after interrupted syscall. */
			if (m_stop)
			{
				break;
			}
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
#if HAVE_HISILICON
				usleep(100000);
#endif
			continue;
			if (errno == EOVERFLOW)
			{
				eWarning("[eFilePushThreadRecorder] OVERFLOW while recording");
				++m_overflow_count;
				continue;
			}
			eDebug("[eFilePushThreadRecorder] *read error* (%m) - aborting thread because i don't know what else to do.");
			sendEvent(evtReadError);
			break;
		}

#ifdef SHOW_WRITE_TIME
		struct timeval starttime;
		struct timeval now;
		gettimeofday(&starttime, NULL);
#endif
		int w = writeData(bytes);
#ifdef SHOW_WRITE_TIME
		gettimeofday(&now, NULL);
		suseconds_t diff = (1000000 * (now.tv_sec - starttime.tv_sec)) + now.tv_usec - starttime.tv_usec;
		eDebug("[eFilePushThreadRecorder] write %d bytes time: %9u us", bytes, (unsigned int)diff);
#endif
		if (w < 0)
		{
			eDebug("[eFilePushThreadRecorder] WRITE ERROR, aborting thread: %m");
			sendEvent(evtWriteError);
			break;
		}
	}
	flush();
	sendEvent(evtStopped);
	eDebug("[eFilePushThreadRecorder] THREAD STOP");
}

void eFilePushThreadRecorder::start(int fd)
{
	m_fd_source = fd;
	m_stop = 0;
	run();
}

void eFilePushThreadRecorder::stop()
{
	/* if we aren't running, don't bother stopping. */
	if (m_stop == 1)
		return;
	m_stop = 1;
	eDebug("[eFilePushThreadRecorder] stopping thread."); /* just do it ONCE. it won't help to do this more than once. */
	sendSignal(SIGUSR1);
	kill();
}

void eFilePushThreadRecorder::sendEvent(int evt)
{
	m_messagepump.send(evt);
}

void eFilePushThreadRecorder::recvEvent(const int &evt)
{
	m_event(evt);
}
