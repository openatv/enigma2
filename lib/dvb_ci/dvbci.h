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
};

class eDVBCIInterfaces
{
DECLARE_REF(eDVBCIInterfaces);
private:
	eSmartPtrList<eDVBCISlot>	m_slots;
public:
	eDVBCIInterfaces();
	~eDVBCIInterfaces();
};

#endif
