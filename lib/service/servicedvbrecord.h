#ifndef __servicedvbrecord_h
#define __servicedvbrecord_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <set>

#include <lib/service/servicedvb.h>

class eDVBServiceRecord: public eDVBServiceBase,
	public iRecordableService, 
	public iStreamableService,
	public Object
{
	DECLARE_REF(eDVBServiceRecord);
public:
	RESULT connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection);
	RESULT prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id);
	RESULT prepareStreaming();
	RESULT start();
	RESULT stop();
	RESULT stream(ePtr<iStreamableService> &ptr);
	RESULT getError(int &error) { error = m_error; return 0; }
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr);

		/* streamable service */
	PyObject *getStreamingData();

private:
	enum { stateIdle, statePrepared, stateRecording };
	int m_state, m_want_record;
	friend class eServiceFactoryDVB;
	eDVBServiceRecord(const eServiceReferenceDVB &ref);
	
	eServiceReferenceDVB m_ref;
	
	ePtr<iDVBTSRecorder> m_record;
	ePtr<eConnection>	m_con_record_event;
	
	int m_recording, m_tuned, m_error;
	std::set<int> m_pids_active;
	std::string m_filename;
	int m_target_fd;
	int m_streaming;
	
	int doPrepare();
	int doRecord();

			/* events */
	void serviceEvent(int event);
	Signal2<void,iRecordableService*,int> m_event;
	
			/* recorder events */
	void recordEvent(int event);
};

#endif
