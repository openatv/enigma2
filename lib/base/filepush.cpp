#include <lib/base/filepush.h>
#include <lib/base/eerror.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <netdb.h>

#define PVR_COMMIT 1

//FILE *f = fopen("/log.ts", "wb");

eFilePushThread::eFilePushThread(int io_prio_class, int io_prio_level, int blocksize)
	:prio_class(io_prio_class), prio(io_prio_level), m_messagepump(eApp, 0)
{
	m_stop = 0;
	m_sg = 0;
	m_send_pvr_commit = 0;
	m_stream_mode = 0;
	m_blocksize = blocksize;
	streamFd = -1;
	flush();
	enablePVRCommit(0);
	CONNECT(m_messagepump.recv_msg, eFilePushThread::recvEvent);
}

eFilePushThread::~eFilePushThread()
{
	if (streamFd >= 0) ::close(streamFd);
}

static void signal_handler(int x)
{
}

int eFilePushThread::connectStream(std::string &url)
{
	std::string host;
	int port = 80;
	std::string uri;

	int slash = url.find("/", 7);
	if (slash > 0)
	{
		host = url.substr(7, slash - 7);
		uri = url.substr(slash, url.length() - slash);
	}
	else
	{
		host = url.substr(7, url.length() - 7);
		uri = "";
	}
	int dp = host.find(":");
	if (dp == 0)
	{
		port = atoi(host.substr(1, host.length() - 1).c_str());
		host = "localhost";
	}
	else if (dp > 0)
	{
		port = atoi(host.substr(dp + 1, host.length() - dp - 1).c_str());
		host = host.substr(0, dp);
	}

	struct hostent* h = gethostbyname(host.c_str());
	if (h == NULL || h->h_addr_list == NULL) return -1;
	int fd = socket(PF_INET, SOCK_STREAM, 0);
	if (fd == -1) return -1;

	struct sockaddr_in addr;
	addr.sin_family = AF_INET;
	addr.sin_addr.s_addr = *((in_addr_t*)h->h_addr_list[0]);
	addr.sin_port = htons(port);

	eDebug("connecting to %s", url.c_str());

	if (::connect(fd, (sockaddr*)&addr, sizeof(addr)) == -1)
	{
		::close(fd);
		std::string msg = "connect failed for: " + url;
		eDebug(msg.c_str());
		return -1;
	}

	std::string request = "GET ";
	request.append(uri).append(" HTTP/1.1\n");
	request.append("Host: ").append(host).append("\n");
	request.append("Accept: */*\n");
	request.append("Connection: close\n");
	request.append("\n");
	socketWrite(fd, request.c_str(), request.length());

	char linebuf[1024] = {0};
	if (timedSocketRead(fd, linebuf, sizeof(linebuf) - 1, 5000) <= 0)
	{
		::close(fd);
		eDebug("read timeout");
		return -1;
	}

	char proto[100];
	int statuscode = 0;
	char statusmsg[100];
	int rc = sscanf(linebuf, "%99s %d %99s", proto, &statuscode, statusmsg);
	if (rc != 3 || statuscode != 200)
	{
		eDebug("wrong response: \"200 OK\" expected.\n %d --- %d", rc, statuscode);
		::close(fd);
		return -1;
	}

	return fd;
}

ssize_t eFilePushThread::socketRead(int fd, void *buf, size_t count)
{
	int retval;
	while (1)
	{
		retval = ::read(fd, buf, count);
		if (retval < 0)
		{
			if (errno == EINTR)
			{
				if (m_stop) return -1;
				continue;
			}
			eDebug("eFilePushThread::socketRead %m");
		}
		return retval;
	}
}

ssize_t eFilePushThread::timedSocketRead(int fd, void *data, size_t size, int msinitial, int msinterbyte)
{
	fd_set rset;
	struct timeval timeout;
	int result;
	size_t totalread = 0;

	while (totalread < size)
	{
		int maxfd = 0;
		FD_ZERO(&rset);
		FD_SET(fd, &rset);
		maxfd = fd + 1;
		if (totalread == 0)
		{
			timeout.tv_sec = msinitial/1000;
			timeout.tv_usec = (msinitial%1000) * 1000;
		}
		else
		{
			timeout.tv_sec = msinterbyte/1000;
			timeout.tv_usec = (msinterbyte%1000) * 1000;
		}
		result = ::select(maxfd, &rset, NULL, NULL, &timeout);
		if (result < 0)
		{
			if (errno == EINTR)
			{
				if (m_stop) return -1;
				continue;
			}
			return -1;
		}
		if (result == 0) break;
		if ((result = socketRead(fd, ((char*)data) + totalread, size - totalread)) < 0)
		{
			return -1;
		}
		if (result == 0) break;
		totalread += result;
	}
	return totalread;
}

ssize_t eFilePushThread::socketWrite(int fd, const void *buf, size_t count)
{
	int retval;
	char *ptr = (char*)buf;
	size_t handledcount = 0;
	while (handledcount < count)
	{
		retval = ::write(fd, &ptr[handledcount], count - handledcount);

		if (retval == 0) return -1;
		if (retval < 0)
		{
			if (errno == EINTR)
			{
				if (m_stop) return -1;
				continue;
			}
			eDebug("eFilePushThread::socketWrite %m");
			return retval;
		}
		handledcount += retval;
	}
	return handledcount;
}

void eFilePushThread::thread()
{
	if (m_raw_source.valid()) setIoPrio(prio_class, prio);

	off_t source_pos = 0;
	size_t bytes_read = 0;
	
	off_t current_span_offset = 0;
	size_t current_span_remaining = 0;
	
	size_t written_since_last_sync = 0;

	eDebug("FILEPUSH THREAD START");
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it. we want to receive the -EINTR
	act.sa_flags = 0;
	sigaction(SIGUSR1, &act, 0);
	
	hasStarted();

	if (m_raw_source.valid()) source_pos = m_raw_source.lseek(0, SEEK_CUR);

	if (streamFd >= 0)
	{
		::close(streamFd);
		streamFd = -1;
	}
	if (!streamUrl.empty())
	{
		streamFd = connectStream(streamUrl);
		if (streamFd < 0) return;
	}
	
		/* m_stop must be evaluated after each syscall. */
	while (!m_stop)
	{
			/* first try flushing the bufptr */
		if (m_buf_start != m_buf_end)
		{
				/* filterRecordData wants to work on multiples of blocksize.
				   if it returns a negative result, it means that this many bytes should be skipped
				   *in front* of the buffer. Then, it will be called again. with the newer, shorter buffer.
				   if filterRecordData wants to skip more data then currently available, it must do that internally.
				   Skipped bytes will also not be output.

				   if it returns a positive result, that means that only these many bytes should be used
				   in the buffer. 
				   
				   In either case, current_span_remaining is given as a reference and can be modified. (Of course it 
				   doesn't make sense to decrement it to a non-zero value unless you return 0 because that would just
				   skip some data). This is probably a very special application for fast-forward, where the current
				   span is to be cancelled after a complete iframe has been output.

				   we always call filterRecordData with our full buffer (otherwise we couldn't easily strip from the end)
				   
				   we filter data only once, of course, but it might not get immediately written.
				   that's what m_filter_end is for - it points to the start of the unfiltered data.
				*/
			
			int filter_res;
			
			do
			{
				filter_res = filterRecordData(m_buffer + m_filter_end, m_buf_end - m_filter_end, current_span_remaining);

				if (filter_res < 0)
				{
					eDebug("[eFilePushThread] filterRecordData re-syncs and skips %d bytes", -filter_res);
					m_buf_start = m_filter_end + -filter_res;  /* this will also drop unwritten data */
					ASSERT(m_buf_start <= m_buf_end); /* otherwise filterRecordData skipped more data than available. */
					continue; /* try again */
				}
				
					/* adjust end of buffer to strip dropped tail bytes */
				m_buf_end = m_filter_end + filter_res;
					/* mark data as filtered. */
				m_filter_end = m_buf_end;
			} while (0);
			
			ASSERT(m_filter_end == m_buf_end);
			
			if (m_buf_start == m_buf_end)
				continue;

				/* now write out data. it will be 'aligned' (according to filterRecordData). 
				   absolutely forbidden is to return EINTR and consume a non-aligned number of bytes. 
				*/
			int w = write(m_fd_dest, m_buffer + m_buf_start, m_buf_end - m_buf_start);
//			fwrite(m_buffer + m_buf_start, 1, m_buf_end - m_buf_start, f);
//			eDebug("wrote %d bytes", w);
			if (w <= 0)
			{
				if (errno == EINTR || errno == EAGAIN || errno == EBUSY)
					continue;
				eDebug("eFilePushThread WRITE ERROR");
				sendEvent(evtWriteError);
				break;
				// ... we would stop the thread
			}

			if (!m_send_pvr_commit)
			{
				/* only do posix_fadvise for real files, not for the pvr device */
				written_since_last_sync += w;

				if (written_since_last_sync >= 512*1024)
				{
					int toflush = written_since_last_sync > 2*1024*1024 ?
						2*1024*1024 : written_since_last_sync &~ 4095; // write max 2MB at once
					off_t dest_pos = lseek(m_fd_dest, 0, SEEK_CUR);
					dest_pos -= toflush;
					posix_fadvise(m_fd_dest, dest_pos, toflush, POSIX_FADV_DONTNEED);
					written_since_last_sync -= toflush;
				}
			}

//			printf("FILEPUSH: wrote %d bytes\n", w);
			m_buf_start += w;
			continue;
		}

			/* now fill our buffer. */

		if (m_raw_source.valid() && m_sg && !current_span_remaining)
		{
			m_sg->getNextSourceSpan(source_pos, bytes_read, current_span_offset, current_span_remaining);
			ASSERT(!(current_span_remaining % m_blocksize));

			if (source_pos != current_span_offset)
				source_pos = m_raw_source.lseek(current_span_offset, SEEK_SET);
			bytes_read = 0;
		}
		
		size_t maxread = sizeof(m_buffer);
		
			/* if we have a source span, don't read past the end */
		if (m_raw_source.valid() && m_sg && maxread > current_span_remaining)
			maxread = current_span_remaining;

			/* align to blocksize */
		if (m_raw_source.valid()) maxread -= maxread % m_blocksize;

		m_buf_start = 0;
		m_filter_end = 0;
		m_buf_end = 0;
		
		if (maxread)
		{
			if (m_raw_source.valid())
			{
				m_buf_end = m_raw_source.read(m_buffer, maxread);
			}
			else if (streamFd)
			{
				m_buf_end = timedSocketRead(streamFd, m_buffer, maxread, 15000);
			}
		}

		if (m_buf_end < 0)
		{
			m_buf_end = 0;
			if (errno == EINTR || errno == EBUSY || errno == EAGAIN)
				continue;
			if (errno == EOVERFLOW)
			{
				eWarning("OVERFLOW while recording");
				continue;
			}
			eDebug("eFilePushThread *read error* (%m) - not yet handled");
		}

		if (m_raw_source.valid())
		{
			/* a read might be mis-aligned in case of a short read. */
			int d = m_buf_end % m_blocksize;
			if (d)
			{
				m_raw_source.lseek(-d, SEEK_CUR);
				m_buf_end -= d;
			}
		}

		if (m_buf_end == 0)
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
						continue;
					case 1:
						eDebug("wait for driver eof ok");
						break;
					default:
						eDebug("wait for driver eof aborted by signal");
						continue;
				}
			}
			
				/* in stream_mode, we are sending EOF events 
				   over and over until somebody responds.
				   
				   in stream_mode, think of evtEOF as "buffer underrun occured". */
			sendEvent(evtEOF);

			if (m_stream_mode)
			{
				eDebug("reached EOF, but we are in stream mode. delaying 1 second.");
				sleep(1);
				continue;
			}
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
	if (!strncmp(filename, "http://", 7))
	{
		streamUrl = filename;
	}
	else
	{
		if (m_raw_source.open(filename) < 0)
			return -1;
	}
	m_fd_dest = fd_dest;
	resume();
	return 0;
}

int eFilePushThread::startUrl(const char *url, int fd_dest)
{
	streamUrl = url;
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

	eDebug("stopping thread."); /* just do it ONCE. it won't help to do this more than once. */
	sendSignal(SIGUSR1);
	kill(0);
}

void eFilePushThread::pause()
{
	stop();
}

void eFilePushThread::seek(int whence, off_t where)
{
	if (!m_raw_source.valid()) return;
	m_raw_source.lseek(where, whence);
}

void eFilePushThread::resume()
{
	m_stop = 0;
	run();
}

void eFilePushThread::flush()
{
	m_buf_start = m_buf_end = m_filter_end = 0;
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

int eFilePushThread::filterRecordData(const unsigned char *data, int len, size_t &current_span_remaining)
{
	return len;
}
