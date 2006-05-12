#ifndef __lib_dvb_teletext_h
#define __lib_dvb_teletext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>

class eDVBTeletextParser: public iObject, public ePESParser, public Object
{
	DECLARE_REF(eDVBTeletextParser);
public:
	eDVBTeletextParser(iDVBDemux *demux);
	int start(int pid);
	
private:
	void processPESPacket(__u8 *pkt, int len);
	
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
};

#endif
