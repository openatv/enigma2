#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <errno.h>

eFilePushThread::eFilePushThread()
{
	m_stop = 0;
	m_buf_start = m_buf_end = 0;
}

static void signal_handler(int x)
{
}

void eFilePushThread::thread()
{
	eDebug("FILEPUSH THREAD START");
		// this is a race. FIXME.
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	
		/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
			/* first try flushing the bufptr */
		if (m_buf_start != m_buf_end)
		{
				// TODO: take care of boundaries.
			int w = write(m_fd_dest, m_buffer + m_buf_start, m_buf_end - m_buf_start);
			if (w <= 0)
			{
				if (errno == -EINTR)
					continue;
				eDebug("eFilePushThread *write error* - not yet handled");
				// ... we would stop the thread
			}
//			printf("FILEPUSH: wrote %d bytes\n", w);
			m_buf_start += w;
			continue;
		}
			
			/* now fill our buffer. */
		m_buf_start = 0;
		m_buf_end = read(m_fd_source, m_buffer, sizeof(m_buffer));
		if (m_buf_end < 0)
		{
			m_buf_end = 0;
			if (errno == EINTR)
				continue;
			eDebug("eFilePushThread *read error* - not yet handled");
		}
		if (m_buf_end == 0)
		{
			eDebug("FILEPUSH: end-of-file! (currently unhandled)");
			if (!lseek(m_fd_source, 0, SEEK_SET))
			{
				eDebug("(looping)");
				continue;
			}
			break;
		}
//		printf("FILEPUSH: read %d bytes\n", m_buf_end);
	}
	
	eDebug("FILEPUSH THREAD STOP");
}

void eFilePushThread::start(int fd_source, int fd_dest)
{
	m_fd_source = fd_source;
	m_fd_dest = fd_dest;
	m_stop = 0;
	run();
}

void eFilePushThread::stop()
{
	m_stop = 1;
	sendSignal(SIGUSR1);
	kill();
}
