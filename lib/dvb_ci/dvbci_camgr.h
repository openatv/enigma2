#ifndef __dvbci_dvbci_camgr_h
#define __dvbci_dvbci_camgr_h

#include <vector>

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCICAManagerSession: public eDVBCISession
{
	enum {
		stateFinal=statePrivate,
	};
	std::vector<uint16_t> caids;
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
	eDVBCICAManagerSession(eDVBCISlot *tslot);
	~eDVBCICAManagerSession();

	const std::vector<uint16_t> &getCAIDs() const { return caids; }
	int sendCAPMT(unsigned char *pmt, int len);
};

#endif
