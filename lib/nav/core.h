#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <connection.h>

class eNavigation: public iObject, public Object
{
	DECLARE_REF;
private:
	ePtr<iPlayableService> m_runningService;
	ePtr<iServiceHandler> m_servicehandler;
	Signal2<void,eNavigation*,int> m_event;
	ePtr<eConnection> m_service_event_conn;
	void serviceEvent(iPlayableService* service, int event);
	
	std::list<eServiceReference> m_playlist;
public:
	enum
	{
		evStopService,  /** the "current" service was just stopped and likes to be deallocated (clear refs!) */
		evNewService, /** a new "current" service was just started */
		evPlayFailed,
		evPlaylistDone
	};
	RESULT playService(const eServiceReference &service);
	RESULT enqueueService(const eServiceReference &service);
	RESULT connectEvent(const Slot2<void,eNavigation*,int> &event, ePtr<eConnection> &connection);
/*	int connectServiceEvent(const Slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	
	RESULT pause(int p);
	eNavigation(iServiceHandler *serviceHandler);
	virtual ~eNavigation();
};

#endif
