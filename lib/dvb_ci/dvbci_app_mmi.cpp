/* DVB CI Application MMI Manager */

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci_app_mmi.h>

int eDVBCIApplicationMMISession::receivedAPDU(const unsigned char *tag,const void *data, int len)
{
	eTraceNoNewLine("[CI AMMI] SESSION(%d)/AMMI %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLine("\n");
	if ((tag[0]==0x9f) && (tag[1]==0x80))
	{
		switch (tag[2])
		{
		default:
			eWarning("[CI AMMI] unknown APDU tag 9F 80 %02x", tag[2]);
			break;
		}
	}

	return 0;
}

int eDVBCIApplicationMMISession::doAction()
{
	switch (state)
	{
	default:
		eWarning("[CI AMMI] unknown state");
		break;
	}

	return 0;
}
