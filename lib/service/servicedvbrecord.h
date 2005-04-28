#ifndef __servicedvbrecord_h
#define __servicedvbrecord_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>

#include <lib/service/servicedvb.h>

class eDVBServiceRecord: public iRecordableService, public Object
{
DECLARE_REF(eDVBServiceRecord);
public:
	RESULT start();
	RESULT stop();
private:
	friend class eServiceFactoryDVB;
	eDVBServiceRecord(const eServiceReferenceDVB &ref);
	
	eDVBServicePMTHandler m_service_handler;
	eServiceReferenceDVB m_ref;
	void serviceEvent(int event);
};

#endif
