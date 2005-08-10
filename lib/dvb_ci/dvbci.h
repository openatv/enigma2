#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#include <lib/base/ebase.h>

class eDVBCISession;

class eDVBCISlot: public Object
{
DECLARE_REF(eDVBCISlot);
private:
	int fd;
	void data(int);
	eSocketNotifier *notifier_data;
	void event(int);
	eSocketNotifier *notifier_event;
	
	eDVBCISession *se;
public:
	eDVBCISlot(eMainloop *context, int nr);
	virtual ~eDVBCISlot();
	
	int eDVBCISlot::write(const unsigned char *data, size_t len);
};

class eDVBCIInterfaces
{
private:
	eSmartPtrList<eDVBCISlot>	m_slots;
public:
	eDVBCIInterfaces();
	virtual ~eDVBCIInterfaces();
};

#endif
