#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#define PVR_COMMIT 1

eFilePushThread::eFilePushThread(int io_prio_class, int io_prio_level)
	:prio_class(io_prio_class), prio(io_prio_level), m_messagepump(eApp, 0)
{
	m_stop = 0;
	m_sg = 0;
	flush();
	enablePVRCommit(0);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
}

static void signal_handler(int x)
{
}

void eFilePushThread::thread()
{
	setIoPrio(prio_class, prio);

	off_t dest_pos = 0, source_pos = 0;
	size_t bytes_read = 0;
	
	off_t current_span_offset = 0;
	size_t current_span_remaining = 0;
	
	size_t written_since_last_sync = 0;

	int already_empty = 0;
	eDebug("FILEPUSH THREAD START");
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	
	hasStarted();
	
	source_pos = m_raw_source.lseek(0, SEEK_CUR);
	
		/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
			/* first try flushing the bufptr */
		if (m_buf_start != m_buf_end)
		{
				// TODO: take care of boundaries.
			filterRecordData(m_buffer + m_buf_start, m_buf_end - m_buf_start);
			int w = write(m_fd_dest, m_buffer + m_buf_start, m_buf_end - m_buf_start);
//			eDebug("wrote %d bytes", w);
			if (w <= 0)
			{
				if (errno == EINTR)
					continue;
				break;
				// ... we would stop the thread
			}

			written_since_last_sync += w;

			if (written_since_last_sync >= 512*1024)
			{
				int toflush = written_since_last_sync > 2*1024*1024 ?
					2*1024*1024 : written_since_last_sync &~ 4095; // write max 2MB at once
				dest_pos = lseek(m_fd_dest, 0, SEEK_CUR);
				dest_pos -= toflush;
				posix_fadvise(m_fd_dest, dest_pos, toflush, POSIX_FADV_DONTNEED);
				written_since_last_sync -= toflush;
			}

//			printf("FILEPUSH: wrote %d bytes\n", w);
			m_buf_start += w;
			continue;
		}

			/* now fill our buffer. */
			
		if (m_sg && !current_span_remaining)
		{
			m_sg->getNextSourceSpan(source_pos, bytes_read, current_span_offset, current_span_remaining);

			if (source_pos != current_span_offset)
				source_pos = m_raw_source.lseek(current_span_offset, SEEK_SET);
			bytes_read = 0;
		}
		
		size_t maxread = sizeof(m_buffer);
		
			/* if we have a source span, don't read past the end */
		if (m_sg && maxread > current_span_remaining)
			maxread = current_span_remaining;

		m_buf_start = 0;
		m_buf_end = 0;
		
		if (maxread)
			m_buf_end = m_raw_source.read(m_buffer, maxread);

		if (m_buf_end < 0)
		{
			m_buf_end = 0;
			if (errno == EINTR)
				continue;
			if (errno == EOVERFLOW)
			{
				eWarning("OVERFLOW while recording");
				continue;
			}
			eDebug("eFilePushThread *read error* (%m) - not yet handled");
		}
		if (m_buf_end == 0)
		{
				/* on EOF, try COMMITting once. */
			if (m_send_pvr_commit && !already_empty)
			{
				eDebug("sending PVR commit");
				already_empty = 1;
				if (::ioctl(m_fd_dest, PVR_COMMIT) < 0 && errno == EINTR)
					continue;
				eDebug("commit done");
						/* well check again */
				continue;
			}
			sendEvent(evtEOF);
#if 0
			eDebug("FILEPUSH: end-of-file! (currently unhandled)");
			if (!m_raw_source.lseek(0, SEEK_SET))
			{
				eDebug("(looping)");
				continue;
			}
#endif
			break;
		} else
		{
			source_pos += m_buf_end;
			bytes_read += m_buf_end;
			if (m_sg)
				current_span_remaining -= m_buf_end;
			already_empty = 0;
		}
//		printf("FILEPUSH: read %d bytes\n", m_buf_end);
	}
	fdatasync(m_fd_dest);

	eDebug("FILEPUSH THREAD STOP");
}

void eFilePushThread::start(int fd_source, int fd_dest)
{
	m_raw_source.setfd(fd_source);
	m_fd_dest = fd_dest;
	resume();
}

int eFilePushThread::start(const char *filename, int fd_dest)
{
	if (m_raw_source.open(filename) < 0)
		return -1;
	m_fd_dest = fd_dest;
	resume();
	return 0;
}

void eFilePushThread::stop()
{
		/* if we aren't running, don't bother stopping. */
	if (!sync())
		return;

	m_stop = 1;

	// fixmee.. here we need a better solution to ensure
	// that the thread context take notice of the signal
	// even when no syscall is in progress
	while(!sendSignal(SIGUSR1))
	{
		eDebug("send SIGUSR1 to thread context");
		usleep(5000); // wait msek
	}
	kill();
}

void eFilePushThread::pause()
{
	stop();
}

void eFilePushThread::seek(int whence, off_t where)
{
	m_raw_source.lseek(where, whence);
}

void eFilePushThread::resume()
{
	m_stop = 0;
	run();
}

void eFilePushThread::flush()
{
	m_buf_start = m_buf_end = 0;
}

void eFilePushThread::enablePVRCommit(int s)
{
	m_send_pvr_commit = s;
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
	/* do nothing */
}

