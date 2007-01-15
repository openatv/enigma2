#ifndef __lib_dvb_radiotext_h
#define __lib_dvb_radiotext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

class eDVBRadioTextParser: public iObject, public ePESParser, public Object
{
	DECLARE_REF(eDVBRadioTextParser);
	int bytesread, ptr, p1, p2, msgPtr;
	unsigned char buf[128], message[66], leninfo, todo, state;
	unsigned short crc16, crc;
public:
	eDVBRadioTextParser(iDVBDemux *demux);
	int start(int pid);
	void connectUpdatedRadiotext(const Slot0<void> &slot, ePtr<eConnection> &connection);
	const char *getCurrentText() { return msgPtr ? (const char*)message : ""; }
private:
	void abortNonAvail();
	void processPESPacket(__u8 *pkt, int len);
	void gotAncillaryByte(__u8 data);
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	Signal0<void> m_updated_radiotext;
	eTimer m_abortTimer;
};

#endif
