#include <config.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>

#include <lib/base/thread.h>

#if HAVE_DVB_API_VERSION < 3
#include <ost/dmx.h>
#ifndef DMX_SET_NEGFILTER_MASK
	#define DMX_SET_NEGFILTER_MASK   _IOW('o',48,uint8_t *)
#endif
#else
#include <linux/dvb/dmx.h>
#endif

#include "crc32.h"

#include <lib/base/eerror.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/decoder.h>

eDVBDemux::eDVBDemux(int adapter, int demux): adapter(adapter), demux(demux)
{
	m_dvr_busy = 0;
}

eDVBDemux::~eDVBDemux()
{
}

DEFINE_REF(eDVBDemux)

RESULT eDVBDemux::createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)
{
	RESULT res;
	reader = new eDVBSectionReader(this, context, res);
	if (res)
		reader = 0;
	return res;
}

RESULT eDVBDemux::createTSRecorder(ePtr<iDVBTSRecorder> &recorder)
{
	if (m_dvr_busy)
		return -EBUSY;
	recorder = new eDVBTSRecorder(this);
	return 0;
}

RESULT eDVBDemux::getMPEGDecoder(ePtr<iTSMPEGDecoder> &decoder)
{
	decoder = new eTSMPEGDecoder(this, 0);
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
			eFatal("crc32 failed! is %x\n", c);
	}
	read(data);
}

eDVBSectionReader::eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res): demux(demux)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d/demux%d", demux->adapter, demux->demux);
#else
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
#endif
	fd = ::open(filename, O_RDWR);
	
	eDebug("eDVBSectionReader has fd %d", fd);
	
	if (fd >= 0)
	{
		notifier=new eSocketNotifier(context, fd, eSocketNotifier::Read);
		CONNECT(notifier->activated, eDVBSectionReader::data);
		res = 0;
	} else
	{
		perror(filename);
		res = errno;
	}
}

DEFINE_REF(eDVBSectionReader)

eDVBSectionReader::~eDVBSectionReader()
{
	if (notifier)
		delete notifier;
	if (fd >= 0)
		::close(fd);
}

RESULT eDVBSectionReader::start(const eDVBSectionFilterMask &mask)
{
	RESULT res;
	if (fd < 0)
		return -ENODEV;

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
	
	::ioctl(fd, DMX_STOP);
	
	return 0;
}

RESULT eDVBSectionReader::connectRead(const Slot1<void,const __u8*> &r, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, read.connect(r));
	return 0;
}

DEFINE_REF(eDVBTSRecorder);

class eDVBTSRecorderThread: public eThread
{
public:
	eDVBTSRecorderThread();
	void thread();
	void stop();
	void start(int sourcefd, int destfd);
private:
	int m_stop;
	unsigned char m_buffer[65536];
	int m_buf_start, m_buf_end;
	int m_fd_source, m_fd_dest;
};

eDVBTSRecorderThread::eDVBTSRecorderThread()
{
	m_stop = 0;
	m_buf_start = m_buf_end = 0;
}

static void signal_handler(int x)
{
}

void eDVBTSRecorderThread::thread()
{
	eDebug("RECORDING THREAD START");
		// this is race. FIXME.
	
		/* we set the signal to not restart syscalls, so we can detect our signal. */
	struct sigaction act;
	act.sa_handler = signal_handler; // no, SIG_IGN doesn't do it :/
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
				eDebug("eDVBTSRecorder *write error* - not yet handled");
				// ... we would stop the thread
			}
			printf("TSRECORD: wrote %d bytes\n", w);
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
			eDebug("eDVBTSRecorder *read error* - not yet handled");
		}
		printf("TSRECORD: read %d bytes\n", m_buf_end);
	}
	
	eDebug("RECORDING THREAD STOP");
}

void eDVBTSRecorderThread::start(int fd_source, int fd_dest)
{
	m_fd_source = fd_source;
	m_fd_dest = fd_dest;
	m_stop = 0;
	run();
}

void eDVBTSRecorderThread::stop()
{
	m_stop = 1;
	sendSignal(SIGUSR1);
	kill();
}

eDVBTSRecorder::eDVBTSRecorder(eDVBDemux *demux): m_demux(demux)
{
	m_running = 0;
	m_format = 0;
	m_target_fd = -1;
	m_thread = new eDVBTSRecorderThread();
	m_demux->m_dvr_busy = 1;
}

eDVBTSRecorder::~eDVBTSRecorder()
{
	stop();
	delete m_thread;
	m_demux->m_dvr_busy = 0;
}

RESULT eDVBTSRecorder::start()
{
	if (m_running)
		return -1;
	
	if (m_target_fd == -1)
		return -2;
		
	char filename[128];
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
	
	m_thread->start(m_source_fd, m_target_fd);
	m_running = 1;
	
	for (std::map<int,int>::iterator i(m_pids.begin()); i != m_pids.end(); ++i)
		startPID(i->first);
	
	return 0;
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

RESULT eDVBTSRecorder::setFormat(int format)
{
	if (m_running)
		return -1;
	m_format = format;
	return 0;
}

RESULT eDVBTSRecorder::setTargetFD(int fd)
{
	m_target_fd = fd;
	return 0;
}

RESULT eDVBTSRecorder::setBoundary(off_t max)
{
	return -1; // not yet implemented
}

RESULT eDVBTSRecorder::stop()
{
	for (std::map<int,int>::iterator i(m_pids.begin()); i != m_pids.end(); ++i)
		stopPID(i->first);

	if (!m_running)
		return -1;
	m_thread->stop();
	
	close(m_source_fd);
	
	return 0;
}

RESULT eDVBTSRecorder::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)
{
	conn = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eDVBTSRecorder::startPID(int pid)
{
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	snprintf(filename, 128, "/dev/dvb/card%d/demux%d", m_demux->adapter, m_demux->demux);
#else
	snprintf(filename, 128, "/dev/dvb/adapter%d/demux%d", m_demux->adapter, m_demux->demux);
#endif
	int fd = ::open(filename, O_RDWR);
	if (fd < 0)
	{
		eDebug("FAILED to open demux (%s) in ts recoder (%m)", filename);
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

	return 0;
}

void eDVBTSRecorder::stopPID(int pid)
{
	::close(m_pids[pid]);
	m_pids[pid] = -1;
}
