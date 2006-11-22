#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <connection.h>
#include <map>

class eNavigation: public iObject, public Object
{
	DECLARE_REF(eNavigation);
private:
	ePtr<iServiceHandler> m_servicehandler;

	ePtr<iPlayableService> m_runningService;
	Signal1<void,int> m_event;
	ePtr<eConnection> m_service_event_conn;
	void serviceEvent(iPlayableService* service, int event);

	std::map<ePtr<iRecordableService>, ePtr<eConnection>, std::less<iRecordableService*> > m_recordings;
	Signal2<void,ePtr<iRecordableService>,int> m_record_event;
	void recordEvent(iRecordableService* service, int event);
public:
	
	RESULT playService(const eServiceReference &service);
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection);
	RESULT connectRecordEvent(const Slot2<void,ePtr<iRecordableService>,int> &event, ePtr<eConnection> &connection);
/*	int connectServiceEvent(const Slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	RESULT stopService(void);
	
	RESULT recordService(const eServiceReference &ref, ePtr<iRecordableService> &service);
	RESULT stopRecordService(ePtr<iRecordableService> &service);
	PyObject *getRecordings(void);
	
	RESULT pause(int p);
	eNavigation(iServiceHandler *serviceHandler);
	virtual ~eNavigation();
};

#endif
