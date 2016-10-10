#ifndef __servicedvbstream_h
#define __servicedvbstream_h

#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <set>

#include <lib/service/servicedvb.h>

class eDVBServiceStream: public eDVBServiceBase, public Object
{
	DECLARE_REF(eDVBServiceStream);
public:
	eDVBServiceStream();
	int start(const char *serviceref, int fd);
	int stop();

private:
	enum { stateIdle, statePrepared, stateRecording };
	int m_state, m_want_record;
	bool m_stream_ecm, m_stream_eit, m_stream_ait;

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

	void recordPids(std::set<int> pids_to_record, int timing_pid, int timing_stream_type, iDVBTSRecorder::timing_pid_type timing_pid_type);
	bool recordCachedPids();
};

#endif
