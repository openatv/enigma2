/* DVB CI Operator Profile Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_operatorprofile.h>

eDVBCIOperatorProfileSession::eDVBCIOperatorProfileSession()
{
}

int eDVBCIOperatorProfileSession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eTraceNoNewLine("[CI OP] SESSION(%d)/OPERATOR %02x %02x %02x: ", session_nb, tag[0],tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLine("\n");

	if ((tag[0]==0x9f) && (tag[1]==0x9c))
	{
		switch (tag[2])
		{
		case 0x01:
			eDebug("operator_status");
			state=stateStarted;
			break;
		case 0x03:
			eDebug("operator_nit");
			break;
		case 0x05:
			eDebug("operator_info");
			break;
		case 0x07:
			eDebug("operator_search_status");
			break;
		case 0x09:
			eDebug("operator_tune");
			break;
		default:
			eWarning("[CI OP] unknown APDU tag 9F 9C %02x", tag[2]);
			break;
		}
	}
	return 0;
}

int eDVBCIOperatorProfileSession::doAction()
{
	switch (state)
	{
	case stateStarted:
	{
		const unsigned char tag[3]={0x9F, 0x9C, 0x00};
		sendAPDU(tag);
		state = stateFinal;
		return 0;
	}
	case stateFinal:
	{
		eWarning("[CI OP] stateFinal and action should not happen");
		break;
	}
	default:
		break;
	}
	return 0;
}
