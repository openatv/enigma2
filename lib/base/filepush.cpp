#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#if defined(__sh__) // this allows filesystem tasks to be prioritised
#include <sys/vfs.h>
#define USBDEVICE_SUPER_MAGIC 0x9fa2
#define EXT2_SUPER_MAGIC      0xEF53
#define EXT3_SUPER_MAGIC      0xEF53
#define SMB_SUPER_MAGIC       0x517B
#define NFS_SUPER_MAGIC       0x6969
#define MSDOS_SUPER_MAGIC     0x4d44 /* MD */
#endif
//#define SHOW_WRITE_TIME

eFilePushThread::eFilePushThread(int io_prio_class, int io_prio_level, int blocksize, size_t buffersize)
	:prio_class(io_prio_class),
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
		eFatal("Failed to allocate %d bytes", buffersize);
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
	eDebug("FILEPUSH THREAD START");

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
#if defined (__sh__) // tells the player to play in reverse
#define VIDEO_DISCONTINUITY                   _IO('o', 84)
#define DVB_DISCONTINUITY_SKIP                0x01
#define DVB_DISCONTINUITY_CONTINUOUS_REVERSE  0x02
			if ((m_sg->getSkipMode() != 0))
			{
				// inform the player about the jump in the stream data
				// this only works if the video device allows the discontinuity ioctl in read-only mode (patched)
				int param = DVB_DISCONTINUITY_SKIP; // | DVB_DISCONTINUITY_CONTINUOUS_REVERSE;
				int rc = ioctl(fd_video, VIDEO_DISCONTINUITY, (void*)param);
			}
#endif
			m_sg->getNextSourceSpan(m_current_position, bytes_read, current_span_offset, current_span_remaining);
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
			if (m_stop) {
				break;
			}
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
				continue;
			if (errno == EOVERFLOW)
			{
				eWarning("OVERFLOW while playback?");
				continue;
			}
			eDebug("eFilePushThread *read error* (%m) - not yet handled");
		}

			/* a read might be mis-aligned in case of a short read. */
		int d = buf_end % m_blocksize;
		if (d)
			buf_end -= d;

		if (buf_end == 0)
		{
				/* on EOF, try COMMITting once. */
			if (m_send_pvr_commit)
			{
				struct pollfd pfd;
				pfd.fd = m_fd_dest;
				pfd.events = POLLIN;
				switch (poll(&pfd, 1, 250)) // wait for 250ms
				{
					case 0:
						eDebug("wait for driver eof timeout");
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
						eDebug("wait for driver eof ok");
						break;
					default:
						eDebug("wait for driver eof aborted by signal");
						/* Check m_stop after interrupted syscall. */
						if (m_stop)
							break;
						continue;
				}
			}

			if (m_stop)
				break;

				/* in stream_mode, we are sending EOF events
				   over and over until somebody responds.

				   in stream_mode, think of evtEOF as "buffer underrun occurred". */
			sendEvent(evtEOF);

			if (m_stream_mode)
			{
				eDebug("reached EOF, but we are in stream mode. delaying 1 second.");
				sleep(1);
				continue;
			}
			else if (++eofcount < 10)
			{
				eDebug("reached EOF, but the file may grow. delaying 1 second.");
				sleep(1);
				continue;
			}
			break;
		} else
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
					if (m_stop) {
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
						continue;
					}
					eDebug("eFilePushThread WRITE ERROR");
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
	}
#if defined(__sh__) // closes video device for the reverse playback workaround
	close(fd_video);
#endif
	sendEvent(evtStopped);

	{ /* mutex lock scope */
		eSingleLocker lock(m_run_mutex);
		m_run_state = 0;
		m_run_cond.signal(); /* Tell them we're here */
		while (m_stop == 2) {
			eDebug("FILEPUSH THREAD PAUSED");
			m_run_cond.wait(m_run_mutex);
		}
		if (m_stop == 0)
			m_run_state = 1;
	}

	} while (m_stop == 0);
	eDebug("FILEPUSH THREAD STOP");
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
	eDebug("eFilePushThread stopping thread");
	m_run_cond.signal(); /* Break out of pause if needed */
	sendSignal(SIGUSR1);
	kill(); /* Kill means join actually */
}

void eFilePushThread::pause()
{
	if (m_stop == 1)
	{
		eWarning("eFilePushThread::pause called while not running");
		return;
	}
	/* Set thread into a paused state by setting m_stop to 2 and wait
	 * for the thread to acknowledge that */
	eSingleLocker lock(m_run_mutex);
	m_stop = 2;
	sendSignal(SIGUSR1);
	m_run_cond.signal(); /* Trigger if in weird state */
	while (m_run_state) {
		eDebug("FILEPUSH waiting for pause");
		m_run_cond.wait(m_run_mutex);
	}
}

void eFilePushThread::resume()
{
	if (m_stop != 2)
	{
		eWarning("eFilePushThread::resume called while not paused");
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
	m_messagepump.send(evt);
}

void eFilePushThread::recvEvent(const int &evt)
{
	m_event(evt);
}

void eFilePushThread::filterRecordData(const unsigned char *data, int len)
{
}




eFilePushThreadRecorder::eFilePushThreadRecorder(unsigned char* buffer, size_t buffersize):
	m_fd_source(-1),
	m_buffersize(buffersize),
	m_buffer(buffer),
	m_overflow_count(0),
	m_stop(1),
	m_messagepump(eApp, 0)
{
	CONNECT(m_messagepump.recv_msg, eFilePushThreadRecorder::recvEvent);
}

void eFilePushThreadRecorder::thread()
{
	setIoPrio(IOPRIO_CLASS_RT, 7);

	eDebug("[eFilePushThreadRecorder] THREAD START");

	/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);

	hasStarted();

	/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
		ssize_t bytes = ::read(m_fd_source, m_buffer, m_buffersize);
		if (bytes < 0)
		{
			bytes = 0;
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
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
			eDebug("[eFilePushThreadRecorder] WRITE ERROR, aborting thread");
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
