#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <connection.h>
#include <map>
#include <set>

class eNavigation: public iObject, public Object
{
	DECLARE_REF(eNavigation);
	ePtr<iServiceHandler> m_servicehandler;

	ePtr<iPlayableService> m_runningService;
	Signal1<void,int> m_event;
	ePtr<eConnection> m_service_event_conn;
	void serviceEvent(iPlayableService* service, int event);

	std::map<ePtr<iRecordableService>, ePtr<eConnection>, std::less<iRecordableService*> > m_recordings;
	std::set<ePtr<iRecordableService>, std::less<iRecordableService*> > m_simulate_recordings;

	Signal2<void,ePtr<iRecordableService>,int> m_record_event;
	void recordEvent(iRecordableService* service, int event);
public:
	
	RESULT playService(const eServiceReference &service);
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection);
	RESULT connectRecordEvent(const Slot2<void,ePtr<iRecordableService>,int> &event, ePtr<eConnection> &connection);
/*	int connectServiceEvent(const Slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
	RESULT getCurrentService(ePtr<iPlayableService> &service);
	RESULT stopService(void);
	
	RESULT recordService(const eServiceReference &ref, ePtr<iRecordableService> &service, bool simulate=false);
	RESULT stopRecordService(ePtr<iRecordableService> &service);
	PyObject *getRecordings(bool simulate=false);
	
	RESULT pause(int p);
	eNavigation(iServiceHandler *serviceHandler);
	virtual ~eNavigation();
};

#endif
