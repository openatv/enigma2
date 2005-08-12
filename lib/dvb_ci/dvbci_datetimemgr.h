#ifndef __dvbci_dvbci_datetimemgr_h
#define __dvbci_dvbci_datetimemgr_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIDateTimeSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate, stateSendDateTime
	};
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
};

#endif
