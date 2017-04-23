#ifndef __nav_core_h
#define __nav_core_h

#include <lib/base/object.h>
#include <lib/service/iservice.h>
#include <lib/python/connections.h>
#include <connection.h>
#include <map>
#include <set>

class eNavigation;

/* a subset of eNavigation */
class pNavigation: public iObject, public sigc::trackable
{
    DECLARE_REF(pNavigation);
public:
	enum RecordType {
	    isRealRecording          =     1,
	    isStreaming              =     2,
	    isPseudoRecording        =     4,
	    isUnknownRecording       =     8,
	    isFromTimer              =  0x10,
	    isFromInstantRecording   =  0x20,
	    isFromEPGrefresh         =  0x40,
	    isFromSpecialJumpFastZap =  0x80,
	    isAnyRecording           =  0xFF
	};

    PSignal1<void, int> m_event;
    PSignal2<void, ePtr<iRecordableService>&, int> m_record_event;

    pNavigation(int decoder = 0);

    RESULT playService(const eServiceReference &service);
    RESULT stopService();
    RESULT pause(int p);
    SWIG_VOID(RESULT) getCurrentService(ePtr<iPlayableService> &SWIG_OUTPUT);

    SWIG_VOID(RESULT) recordService(const eServiceReference &ref, ePtr<iRecordableService> &SWIG_OUTPUT, bool simulate=false, RecordType type=isUnknownRecording);
    RESULT stopRecordService(ePtr<iRecordableService> &service);
    void getRecordings(std::vector<ePtr<iRecordableService> > &recordings, bool simulate=false, RecordType type=isAnyRecording);
    void getRecordingsServicesOnly(std::vector<eServiceReference> &services, pNavigation::RecordType type=isAnyRecording);
    void getRecordingsTypesOnly(std::vector<pNavigation::RecordType> &services, pNavigation::RecordType type=isAnyRecording);
    void getRecordingsSlotIDsOnly(std::vector<int> &slotids, pNavigation::RecordType type=isAnyRecording);
    std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > getRecordingsServices(RecordType type=isAnyRecording);
    void navEvent(int event);

private:
    ePtr<eNavigation> m_core;
    ePtr<eConnection> m_nav_event_connection, m_nav_record_event_connection;
    void navRecordEvent(ePtr<iRecordableService>, int event);
};


class eNavigation: public iObject, public sigc::trackable
{
    static eNavigation *instance;
    DECLARE_REF(eNavigation);
    int m_decoder;
    ePtr<iServiceHandler> m_servicehandler;

    ePtr<iPlayableService> m_runningService;
    sigc::signal1<void,int> m_event;
    ePtr<eConnection> m_service_event_conn;
    void serviceEvent(iPlayableService* service, int event);

    std::map<ePtr<iRecordableService>, ePtr<eConnection>, std::less<iRecordableService*> > m_recordings;
    std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > m_recordings_services;
    std::map<ePtr<iRecordableService>, pNavigation::RecordType, std::less<iRecordableService*> > m_recordings_types;
    std::set<ePtr<iRecordableService>, std::less<iRecordableService*> > m_simulate_recordings;

    sigc::signal2<void,ePtr<iRecordableService>,int> m_record_event;
    void recordEvent(iRecordableService* service, int event);
public:

    RESULT playService(const eServiceReference &service);
    RESULT connectEvent(const sigc::slot1<void,int> &event, ePtr<eConnection> &connection);
    RESULT connectRecordEvent(const sigc::slot2<void,ePtr<iRecordableService>,int> &event, ePtr<eConnection> &connection);
/*  int connectServiceEvent(const sigc::slot1<void,iPlayableService*,int> &event, ePtr<eConnection> &connection); */
    RESULT getCurrentService(ePtr<iPlayableService> &service);
    RESULT stopService(void);

    RESULT recordService(const eServiceReference &ref, ePtr<iRecordableService> &service, bool simulate, pNavigation::RecordType type);
    RESULT stopRecordService(ePtr<iRecordableService> &service);
    void getRecordings(std::vector<ePtr<iRecordableService> > &recordings, bool simulate, pNavigation::RecordType type);
    void getRecordingsServicesOnly(std::vector<eServiceReference> &services, pNavigation::RecordType type);
    void getRecordingsTypesOnly(std::vector<pNavigation::RecordType> &services, pNavigation::RecordType type);
    void getRecordingsSlotIDsOnly(std::vector<int> &slotids, pNavigation::RecordType type);
    std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > getRecordingsServices(pNavigation::RecordType type);

    RESULT pause(int p);
    eNavigation(iServiceHandler *serviceHandler, int decoder = 0);
    static eNavigation *getInstance() { return instance; }
    virtual ~eNavigation();
};
#endif
