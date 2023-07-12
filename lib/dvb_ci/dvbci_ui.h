#ifndef __dvbci_ui_h
#define __dvbci_ui_h

#include <string>
#include <lib/base/message.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/mmi/mmi_ui.h>
#include <lib/python/connections.h>

class eDVBCI_UI: public eMMI_UI
{
	static eDVBCI_UI *instance;
#ifndef SWIG
	void gotMessage(const eDVBCIInterfaces::Message &message);
#endif
#ifdef SWIG
	eDVBCI_UI();
#endif
	void stateChanged(int val) { ciStateChanged(val); }
public:
	enum { rateNormal, rateHigh };
	PSignal1<void,int> ciStateChanged;
#ifndef SWIG
	eFixedMessagePump<eDVBCIInterfaces::Message> m_messagepump;
	eDVBCI_UI();
#endif
	static eDVBCI_UI *getInstance();
	void setInit(int slot);
	void setReset(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int getMMIState(int slot);
	int answerMenu(int slot, int answer);
	int answerEnq(int slot, char *val);
	int cancelEnq(int slot);
	int setClockRate(int slot, int rate);
	int setEnabled(int slot, bool enabled);
};

#endif
