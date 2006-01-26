#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#define PVR_COMMIT 1

eFilePushThread::eFilePushThread(): m_messagepump(eApp, 0)
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
	off_t dest_pos = 0, source_pos = 0;
	size_t bytes_read = 0;
	
	off_t current_span_offset = 0;
	size_t current_span_remaining = 0;
	
	int already_empty = 0;
	eDebug("FILEPUSH THREAD START");
		// this is a race. FIXME.
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	
	dest_pos = lseek(m_fd_dest, 0, SEEK_CUR);
	source_pos = lseek(m_fd_source, 0, SEEK_CUR);
	
		/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
			/* first try flushing the bufptr */
		if (m_buf_start != m_buf_end)
		{
				// TODO: take care of boundaries.
			int w = write(m_fd_dest, m_buffer + m_buf_start, m_buf_end - m_buf_start);
//			eDebug("wrote %d bytes", w);
			if (w <= 0)
			{
				if (errno == -EINTR)
					continue;
				break;
				// ... we would stop the thread
			}

				/* this should flush all written pages to disk. */
			posix_fadvise(m_fd_dest, dest_pos, w, POSIX_FADV_DONTNEED);

			dest_pos += w;
//			printf("FILEPUSH: wrote %d bytes\n", w);
			m_buf_start += w;
			continue;
		}

			/* now fill our buffer. */
			
		if (m_sg && !current_span_remaining)
		{
			m_sg->getNextSourceSpan(source_pos, bytes_read, current_span_offset, current_span_remaining);

			if (source_pos != current_span_offset)
				source_pos = lseek(m_fd_source, current_span_offset, SEEK_SET);
			bytes_read = 0;
		}
		
		size_t maxread = sizeof(m_buffer);
		
			/* if we have a source span, don't read past the end */
		if (m_sg && maxread > current_span_remaining)
			maxread = current_span_remaining;

		m_buf_start = 0;
		m_buf_end = 0;
		
		if (maxread)
			m_buf_end = read(m_fd_source, m_buffer, maxread);

		if (m_buf_end < 0)
		{
			m_buf_end = 0;
			if (errno == EINTR)
				continue;
			eDebug("eFilePushThread *read error* - not yet handled");
		}
		if (m_buf_end == 0)
		{
				/* on EOF, try COMMITting once. */
			if (m_send_pvr_commit && !already_empty)
			{
				eDebug("sending PVR commit");
				already_empty = 1;
				if (::ioctl(m_fd_dest, PVR_COMMIT) == EINTR)
					continue;
				eDebug("commit done");
						/* well check again */
				continue;
			}
			sendEvent(evtEOF);
#if 0
			eDebug("FILEPUSH: end-of-file! (currently unhandled)");
			if (!lseek(m_fd_source, 0, SEEK_SET))
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
	
	eDebug("FILEPUSH THREAD STOP");
}

void eFilePushThread::start(int fd_source, int fd_dest)
{
	m_fd_source = fd_source;
	m_fd_dest = fd_dest;
	resume();
}

void eFilePushThread::stop()
{
	if (!thread_running()) /* FIXME: races */
		return;
	m_stop = 1;
	sendSignal(SIGUSR1);
	kill();
}

void eFilePushThread::pause()
{
	stop();
}

void eFilePushThread::seek(int whence, off_t where)
{
	::lseek(m_fd_source, where, whence);
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
