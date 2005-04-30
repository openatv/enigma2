#ifndef __servicedvbrecord_h
#define __servicedvbrecord_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <set>

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
	
	ePtr<iDVBTSRecorder> m_record;
	
	int m_recording;
	std::set<int> m_pids_active;
};

#endif
