#ifndef __servicemp3_h
#define __servicemp3_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>

class eServiceFactoryDVB: public iServiceHandler
{
DECLARE_REF;
public:
	eServiceFactoryDVB();
	virtual ~eServiceFactoryDVB();
	enum { id = 0x1 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
};

class eDVBServiceList: public iListableService
{
DECLARE_REF;
private:
	eServiceReference m_parent;
	friend class eServiceFactoryDVB;
	eDVBServiceList(const eServiceReference &parent);
public:
	virtual ~eDVBServiceList();
	RESULT getContent(std::list<eServiceReference> &list);
};

class eDVBServicePlay: public iPlayableService, public Object, public iServiceInformation
{
DECLARE_REF;
private:
	friend class eServiceFactoryDVB;
	eServiceReference m_reference;
	
	ePtr<iTSMPEGDecoder> m_decoder;
	
	eDVBServicePMTHandler m_serviceHandler;
	
	eDVBServicePlay(const eServiceReference &ref);
	
	void serviceEvent(int event);
public:
	virtual ~eDVBServicePlay();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT info(ePtr<iServiceInformation> &ptr);
	
		// iServiceInformation
	RESULT getName(const eServiceReference &ref, std::string &name);
};

#endif
