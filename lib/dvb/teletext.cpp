#include <lib/base/eerror.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/idemux.h>

DEFINE_REF(eDVBTeletextParser);

eDVBTeletextParser::eDVBTeletextParser(iDVBDemux *demux)
{
	setStreamID(0xBD); // as per en 300 472
	
	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create PES reader!");
	else
		m_pes_reader->connectRead(slot(*this, &eDVBTeletextParser::processData), m_read_connection);
		
}

void eDVBTeletextParser::processPESPacket(__u8 *pkt, int len)
{
	eDebug("GOT TELETEXT PACKET:");
	int i;
	for (i=0; i<16; ++i)
		eDebugNoNewLine("%02x ", pkt[i]);
	eDebug("<");
}

int eDVBTeletextParser::start(int pid)
{
	if (m_pes_reader)
		return m_pes_reader->start(pid);
	else
		return -1;
}
