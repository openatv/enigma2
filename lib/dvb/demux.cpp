#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <unistd.h>

#include <linux/dvb/dmx.h>
#include "crc32.h"

#include <lib/base/eerror.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/decoder.h>

eDVBDemux::eDVBDemux(int adapter, int demux): adapter(adapter), demux(demux), ref(0)
{
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

eDVBSectionReader::eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res): ref(0), demux(demux)
{
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d/demux%d", demux->adapter, demux->demux);
	fd = ::open(filename, O_RDWR);
	
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

	dmx_sct_filter_params sct;
	
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
	
	res = ::ioctl(fd, DMX_SET_FILTER, &sct);
	if (!res)
		active = 1;
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
