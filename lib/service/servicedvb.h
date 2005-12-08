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

class eBouquet;

class eDVBServiceList: public iListableService, public iMutableServiceList
{
DECLARE_REF(eDVBServiceList);
public:
	virtual ~eDVBServiceList();
	RESULT getContent(std::list<eServiceReference> &list);
	RESULT getNext(eServiceReference &ptr);
	int compareLessEqual(const eServiceReference &a, const eServiceReference &b);
	
	RESULT startEdit(ePtr<iMutableServiceList> &);
	RESULT flushChanges();
	RESULT addService(eServiceReference &ref);
	RESULT removeService(eServiceReference &ref);
	RESULT moveService(eServiceReference &ref, int pos);
private:
	RESULT startQuery();
	eServiceReference m_parent;
	friend class eServiceFactoryDVB;
	eDVBServiceList(const eServiceReference &parent);
	ePtr<iDVBChannelListQuery> m_query;
	
		/* for editing purposes. WARNING: lifetime issue! */
	eBouquet *m_bouquet;
};

class eDVBServicePlay: public iPlayableService, public iPauseableService, 
		public iSeekableService, public Object, public iServiceInformation, 
		public iAudioTrackSelection, public iFrontendStatusInformation,
		public iSubserviceList
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
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr);
	RESULT frontendStatusInfo(ePtr<iFrontendStatusInformation> &ptr);
	RESULT subServices(ePtr<iSubserviceList> &ptr);

		// iPauseableService
	RESULT pause();
	RESULT unpause();
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);
    	
		// iSeekableService
	RESULT getLength(pts_t &len);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &pos);

		// iServiceInformation
	RESULT getName(std::string &name);
	RESULT getEvent(ePtr<eServiceEvent> &evt, int nownext);
	int getInfo(int w);
	std::string getInfoString(int w);

		// iAudioTrackSelection	
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo &, unsigned int n);

		// iFrontendStatusInformation
	int getFrontendInfo(int w);

		// iSubserviceList
	int getNumberOfSubservices();
	RESULT getSubservice(eServiceReference &subservice, unsigned int n);

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
	
	int m_current_audio_stream;
	int selectAudioStream(int n);
};

#endif
