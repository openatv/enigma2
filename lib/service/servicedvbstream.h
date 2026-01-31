#ifndef __servicedvbstream_h
#define __servicedvbstream_h

#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <set>

#include <lib/service/servicedvb.h>

// Forward declaration
class eDVBCSASession;

class eDVBServiceStream: public eDVBServiceBase, public sigc::trackable
{
	DECLARE_REF(eDVBServiceStream);
public:
	eDVBServiceStream();
	~eDVBServiceStream();
	int start(const char *serviceref, int fd);
	int stop();
	RESULT frontendInfo(ePtr<iFrontendInformation>& ptr);

protected:
	enum { stateIdle, statePrepared, stateRecording };
	int m_state, m_want_record;
	bool m_stream_ecm, m_stream_eit, m_stream_ait, m_stream_sdtbat;

	eDVBServiceEITHandler m_event_handler;

	eServiceReferenceDVB m_ref;

	ePtr<iDVBTSRecorder> m_record;
	ePtr<eConnection> m_con_record_event;

	int m_recording, m_tuned;
	std::set<int> m_pids_active;

	int m_target_fd;

	int doPrepare();
	int doRecord();

	/* events */
	void serviceEvent(int event);

	/* recorder events */
	void recordEvent(int event);

	/* eit updates */
	void gotNewEvent(int error);

	virtual void streamStopped() {}
	virtual void tuneFailed() {}
	virtual void eventUpdate(int event){}
	int m_record_no_pids = 0;
	void recordPids(std::set<int> pids_to_record, int timing_pid, int timing_stream_type, iDVBTSRecorder::timing_pid_type timing_pid_type);
	bool recordCachedPids();

	// Speculative software descrambler - always attached for encrypted channels
	// Does nothing unless algo=3 is received
	ePtr<eDVBCSASession> m_csa_session;
	void setupSpeculativeDescrambler();
	void cleanupCSASession();
};

#endif
