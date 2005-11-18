#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#include <lib/base/ebase.h>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCIMMISession;

class eDVBCISlot: public iObject, public Object
{
DECLARE_REF(eDVBCISlot);
private:
	int slotid;
	int fd;
	void data(int);
	eSocketNotifier *notifier;

	int state;
	enum {stateRemoved, stateInserted};	
public:
	eDVBCISlot(eMainloop *context, int nr);
	~eDVBCISlot();
	
	int send(const unsigned char *data, size_t len);
	
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCIMMISession *mmi_session;
	
	int getSlotID();
	int reset();
	int initialize();
	int startMMI();
	int stopMMI();
	int answerMMI(int answer, char *value);
};

class eDVBCIInterfaces
{
DECLARE_REF(eDVBCIInterfaces);
	static eDVBCIInterfaces *instance;
private:
	eSmartPtrList<eDVBCISlot>	m_slots;
	eDVBCISlot *getSlot(int slotid);
public:
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	static eDVBCIInterfaces *getInstance();
	
	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerMMI(int slot, int answer, char *value);
};

#endif
