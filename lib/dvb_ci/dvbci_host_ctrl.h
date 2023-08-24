#ifndef __dvbci_dvbci_host_ctrl_h
#define __dvbci_dvbci_host_ctrl_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIHostControlSession: public eDVBCISession
{
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
};

#endif
