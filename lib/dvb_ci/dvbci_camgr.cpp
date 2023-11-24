/* DVB CI CA Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_camgr.h>

eDVBCICAManagerSession::eDVBCICAManagerSession(eDVBCISlot *tslot)
{
	slot = tslot;
	slot->setCAManager(this);
}

eDVBCICAManagerSession::~eDVBCICAManagerSession()
{
	slot->setCAManager(NULL);
}

int eDVBCICAManagerSession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eTraceNoNewLine("[CI%d CA] SESSION(%d)/CA %02x %02x %02x: ", slot->getSlotID(), session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLine("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x80))
	{
		switch (tag[2])
		{
		case 0x31:
			eDebugNoNewLineStart("[CI%d CA]ca info:", slot->getSlotID());
			for (int i=0; i<len; i+=2)
			{
				eDebugNoNewLine("%04x ", (((const unsigned char*)data)[i]<<8)|(((const unsigned char*)data)[i+1]));
				caids.push_back((((const unsigned char*)data)[i]<<8)|(((const unsigned char*)data)[i+1]));
			}
			std::sort(caids.begin(), caids.end());
			eDebugNoNewLine("\n");
			eDVBCIInterfaces::getInstance()->executeRecheckPMTHandlersInMainloop();
			break;
		default:
			eWarning("[CI%d CA] unknown APDU tag 9F 80 %02x", slot->getSlotID(), tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCICAManagerSession::doAction()
{
	switch (state)
	{
	case stateStarted:
	{
		const unsigned char tag[3]={0x9F, 0x80, 0x30}; // ca info enq
		sendAPDU(tag);
		state=stateFinal;
		return 0;
	}
	case stateFinal:
		eWarning("[CI%d CA] stateFinal and action should not happen", slot->getSlotID());
		[[fallthrough]];
	default:
		return 0;
	}
}

int eDVBCICAManagerSession::sendCAPMT(unsigned char *data, int len)
{
	const unsigned char tag[3]={0x9F, 0x80, 0x32}; // ca_pmt

	sendAPDU(tag, data, len);

	return 0;
}

