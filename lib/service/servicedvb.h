#ifndef __servicemp3_h
#define __servicemp3_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>

class eServiceFactoryDVB: public virtual iServiceHandler, public virtual iObject
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
};

class eDVBServicePlay: public virtual iPlayableService, public virtual iObject, public Object
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
	RESULT start();
	RESULT getIPausableService(ePtr<iPauseableService> &ptr);
};

#endif
