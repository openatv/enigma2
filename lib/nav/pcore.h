#ifndef __lib_nav_pcore_h
#define __lib_nav_pcore_h

#include <lib/nav/core.h>
#include <lib/python/connections.h>

/* a subset of eNavigation */

class pNavigation: public iObject
{
DECLARE_REF;
private:
	ePtr<eNavigation> m_core;
public:
	PSignal1<void, int> event;
	
	pNavigation();
	
	RESULT playService(const eServiceReference &service);
	RESULT enqueueService(const eServiceReference &service);
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	RESULT getPlaylist(ePtr<ePlaylist> &playlist);
	
	RESULT pause(int p);
};

#endif
