#ifndef __servicedvb_h
#define __servicedvb_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>

class eServiceFactoryDVB: public iServiceHandler
{
DECLARE_REF(eServiceFactoryDVB);
public:
	eServiceFactoryDVB();
	virtual ~eServiceFactoryDVB();
	enum { id = 0x1 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	RESULT lookupService(ePtr<eDVBService> &ptr, const eServiceReference &ref);
};

class eDVBServiceList: public iListableService
{
DECLARE_REF(eDVBServiceList);
public:
	virtual ~eDVBServiceList();
	RESULT getContent(std::list<eServiceReference> &list);
	RESULT getNext(eServiceReference &ptr);
	int compareLessEqual(const eServiceReference &a, const eServiceReference &b);
private:
	RESULT startQuery();
	eServiceReference m_parent;
	friend class eServiceFactoryDVB;
	eDVBServiceList(const eServiceReference &parent);
	ePtr<iDVBChannelListQuery> m_query;
};

class eDVBServicePlay: public iPlayableService, public iPauseableService, public iSeekableService, public Object, public iServiceInformation
{
DECLARE_REF(eDVBServicePlay);
public:
	virtual ~eDVBServicePlay();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT info(ePtr<iServiceInformation> &ptr);
	
		// iPauseableService
	RESULT pause();
	RESULT unpause();
	
		// iSeekableService
	RESULT getLength(pts_t &len);
	RESULT seekTo(pts_t to);
	RESULT getPlayPosition(pts_t &pos);

		// iServiceInformation
	RESULT getName(std::string &name);
	RESULT getEvent(ePtr<eServiceEvent> &evt, int nownext);

private:
	friend class eServiceFactoryDVB;
	eServiceReference m_reference;
	
	ePtr<eDVBService> m_dvb_service;
	
	ePtr<iTSMPEGDecoder> m_decoder;
	
	eDVBServicePMTHandler m_service_handler;
	eDVBServiceEITHandler m_event_handler;
	
	eDVBServicePlay(const eServiceReference &ref, eDVBService *service);
	
	void gotNewEvent();
	
	void serviceEvent(int event);
	Signal2<void,iPlayableService*,int> m_event;
	
	int m_is_pvr, m_is_paused;
};

#endif
