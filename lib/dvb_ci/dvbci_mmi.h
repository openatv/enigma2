#ifndef __dvbci_dvbci_mmi_h
#define __dvbci_dvbci_mmi_h

#include <lib/dvb_ci/dvbci_session.h>

class eDVBCIMMISession: public eDVBCISession
{
	enum {
		stateDisplayReply=statePrivate, stateFakeOK, stateIdle
	};

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();
	eDVBCISlot *slot;
	bool is_mmi_active;
public:
	eDVBCIMMISession(eDVBCISlot *tslot);
	~eDVBCIMMISession();
	int stopMMI();
	int answerText(int answer);
	int answerEnq(char *answer);
	int cancelEnq();
};

#endif
