#ifndef __dvbci_dvbci_app_mmi_h
#define __dvbci_dvbci_app_mmi_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIApplicationMMISession: public eDVBCISession
{
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
};

#endif
