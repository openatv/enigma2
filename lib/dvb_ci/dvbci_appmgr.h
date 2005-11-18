#ifndef __dvbci_dvbci_appmgr_h
#define __dvbci_dvbci_appmgr_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIApplicationManagerSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate,
	};
	int wantmenu;
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
	int enterMenu();
	int startMMI();
};

#endif
