#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#include <lib/base/ebase.h>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;

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
	
	int getSlotID();
	int reset();
	int startMMI();
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
	int startMMI(int slot);
};

#endif
