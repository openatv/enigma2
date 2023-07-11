#ifndef __dvbci_dvbci_operatorprofile_h
#define __dvbci_dvbci_operatorprofile_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIOperatorProfileSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate
	};

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
	eDVBCIOperatorProfileSession();
};

#endif
