#ifndef __dvbci_dvbci_camgr_h
#define __dvbci_dvbci_camgr_h

#include <set>

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCICAManagerSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate,
	};
	std::set<int> caids;
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
};

#endif
