#ifndef __dvb_demux_h
#define __dvb_demux_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/isection.h>

class eDVBDemux: public iDVBDemux
{
	int adapter, demux;
	friend class eDVBSectionReader;
	friend class eDVBAudio;
	friend class eDVBVideo;
public:
	DECLARE_REF(eDVBDemux);
	eDVBDemux(int adapter, int demux);
	virtual ~eDVBDemux();
	RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader);
	RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader);
};

class eDVBSectionReader: public iDVBSectionReader, public Object
{
	DECLARE_REF(eDVBSectionReader);
private:
	int fd;
	Signal1<void, const __u8*> read;
	ePtr<eDVBDemux> demux;
	int active;
	int checkcrc;
	void data(int);
	eSocketNotifier *notifier;
public:
	
	eDVBSectionReader(eDVBDemux *demux, eMainloop *context, RESULT &res);
	virtual ~eDVBSectionReader();
	RESULT start(const eDVBSectionFilterMask &mask);
	RESULT stop();
	RESULT connectRead(const Slot1<void,const __u8*> &read, ePtr<eConnection> &conn);
};

#endif
