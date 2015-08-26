/* DVB CI DateTime Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_datetimemgr.h>

int eDVBCIDateTimeSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eDebugNoNewLineStart("SESSION(%d)/DATETIME %02x %02x %02x: ", session_nb, tag[0],tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eDebugNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eDebugNoNewLineEnd("");

	if ((tag[0]==0x9f) && (tag[1]==0x84))
	{
		switch (tag[2])
		{
		case 0x40:
			state=stateSendDateTime;
			return 1;
			break;
		default:
			eDebug("unknown APDU tag 9F 84 %02x", tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCIDateTimeSession::doAction()
{
	switch (state)
	{
	case stateStarted:
		return 0;
	case stateSendDateTime:
	{
		unsigned char tag[3]={0x9f, 0x84, 0x41}; // date_time_response
		unsigned char msg[7]={0, 0, 0, 0, 0, 0, 0};
		sendAPDU(tag, msg, 7);
		return 0;
	}
	case stateFinal:
		eDebug("stateFinal und action! kann doch garnicht sein ;)");
	default:
		return 0;
	}
}
