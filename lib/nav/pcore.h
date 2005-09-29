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
	
	enum
	{
		evStopService,  /** the "current" service was just stopped and likes to be deallocated (clear refs!) */
		evNewService,   /** a new "current" service was just started */
		evPlayFailed,   /** the next service (in playlist) or the one given in playService failed to play */
		evPlaylistDone, /** the last service in the playlist was just played */
		evUpdatedEventInfo /** the "currently running" event info was updated */
	};
	
	pNavigation();
	
	RESULT playService(const eServiceReference &service);
	RESULT recordService(const eServiceReference &ref, ePtr<iRecordableService> &service);
	
	RESULT enqueueService(const eServiceReference &service);
	SWIG_VOID(RESULT) getCurrentService(ePtr<iPlayableService> &SWIG_OUTPUT);
	SWIG_VOID(RESULT) getPlaylist(ePtr<ePlaylist> &SWIG_OUTPUT);
	
	RESULT pause(int p);
private:
	ePtr<eNavigation> m_core;
	ePtr<eConnection> m_nav_event_connection;
	void navEvent(eNavigation *nav, int event);
};

#endif
