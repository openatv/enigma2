#ifndef __lib_nav_pcore_h
#define __lib_nav_pcore_h

#include <lib/nav/core.h>
#include <lib/python/connections.h>

/* a subset of eNavigation */

class pNavigation: public iObject, public Object
{
DECLARE_REF(pNavigation);
public:
	PSignal1<void, int> m_event;
	
	pNavigation();
	
	RESULT playService(const eServiceReference &service);
	SWIG_VOID(RESULT) recordService(const eServiceReference &ref, ePtr<iRecordableService> &SWIG_OUTPUT);
	
	SWIG_VOID(RESULT) getCurrentService(ePtr<iPlayableService> &SWIG_OUTPUT);
	RESULT stopService();
	
	RESULT pause(int p);
private:
	ePtr<eNavigation> m_core;
	ePtr<eConnection> m_nav_event_connection;
	void navEvent(eNavigation *nav, int event);
};

#endif
