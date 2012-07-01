#ifndef __dvbci_dvbci_appmgr_h
#define __dvbci_dvbci_appmgr_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIApplicationManagerSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate,
	};
	
	eDVBCISlot *slot;
	
	int wantmenu;
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
	eDVBCIApplicationManagerSession(eDVBCISlot *tslot);
	~eDVBCIApplicationManagerSession();
	int enterMenu();
	int startMMI();
};

#endif
