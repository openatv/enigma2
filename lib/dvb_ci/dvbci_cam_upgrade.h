#ifndef __dvbci_dvbci_cam_upgrade_h
#define __dvbci_dvbci_cam_upgrade_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCICAMUpgradeSession: public eDVBCISession
{
	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
};

#endif
