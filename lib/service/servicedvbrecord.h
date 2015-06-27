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
	public iSubserviceList,
	public Object
{
	DECLARE_REF(eDVBServiceRecord);
public:
	RESULT connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection);
	RESULT prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm);
	RESULT prepareStreaming(bool descramble, bool includeecm);
	RESULT start(bool simulate=false);
	RESULT stop();
	RESULT stream(ePtr<iStreamableService> &ptr);
	RESULT getError(int &error) { error = m_error; return 0; }
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr);
	RESULT subServices(ePtr<iSubserviceList> &ptr);
	RESULT getFilenameExtension(std::string &ext) { ext = ".ts"; return 0; };

		// iStreamableService
	ePtr<iStreamData> getStreamingData();

		// iSubserviceList
	int getNumberOfSubservices();
	RESULT getSubservice(eServiceReference &subservice, unsigned int n);
private:
	enum { stateIdle, statePrepared, stateRecording };
	bool m_simulate;
	int m_state, m_want_record;
	bool m_record_ecm;
	bool m_descramble;
	bool m_is_stream_client;
	friend class eServiceFactoryDVB;
	eDVBServiceRecord(const eServiceReferenceDVB &ref, bool isstreamclient = false);

	eDVBServiceEITHandler m_event_handler;

	eServiceReferenceDVB m_ref;

	ePtr<iDVBTSRecorder> m_record;
	ePtr<eConnection> m_con_record_event;

	int m_recording, m_tuned, m_error;
	std::set<int> m_pids_active;
	std::string m_filename;

	std::map<int,pts_t> m_event_timestamps;
	int m_target_fd;
	int m_streaming;
	int m_last_event_id;

	int doPrepare();
	int doRecord();

			/* events */
	void serviceEvent(int event);
	Signal2<void,iRecordableService*,int> m_event;

			/* recorder events */
	void recordEvent(int event);

			/* eit updates */
	void gotNewEvent(int error);
	void saveCutlist();
};

#endif
