#ifndef __dvbci_dvbci_datetimemgr_h
#define __dvbci_dvbci_datetimemgr_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIDateTimeSession: public eDVBCISession, public sigc::trackable
{
	enum {
		stateFinal=statePrivate, stateSendDateTime
	};

	ePtr<eTimer> m_timer;
	int m_interval;

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
public:
	eDVBCIDateTimeSession();
	void sendDateTime();
};

#endif
