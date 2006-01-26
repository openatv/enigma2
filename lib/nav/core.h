#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <connection.h>

class eNavigation: public iObject, public Object
{
	DECLARE_REF(eNavigation);
private:
	ePtr<iPlayableService> m_runningService;
	
	ePtr<iServiceHandler> m_servicehandler;
	Signal2<void,eNavigation*,int> m_event;
	ePtr<eConnection> m_service_event_conn;
	void serviceEvent(iPlayableService* service, int event);
public:
	
	RESULT playService(const eServiceReference &service);
	RESULT connectEvent(const Slot2<void,eNavigation*,int> &event, ePtr<eConnection> &connection);
/*	int connectServiceEvent(const Slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	RESULT stopService(void);
	
	RESULT recordService(const eServiceReference &ref, ePtr<iRecordableService> &service);
	
	RESULT pause(int p);
	eNavigation(iServiceHandler *serviceHandler);
	virtual ~eNavigation();
};

#endif
