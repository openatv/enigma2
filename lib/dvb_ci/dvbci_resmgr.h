#ifndef __dvbci_dvbci_resmgr_h
#define __dvbci_dvbci_resmgr_h

//#include <lib/base/ebase.h>
#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIResourceManagerSession: public eDVBCISession
{
	enum {
		stateFirstProfileEnquiry=statePrivate,
		stateProfileChange,
		stateProfileEnquiry,
		stateFinal };
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
	int m_version;
public:
	eDVBCIResourceManagerSession(int version) : m_version(version) {};
};

#endif
