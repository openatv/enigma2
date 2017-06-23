#ifndef __lib_dvb_eit_h
#define __lib_dvb_eit_h

#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/atsc.h>
#include <dvbsi++/event_information_section.h>
#include <lib/service/event.h>

class eDVBServiceEITHandler: public sigc::trackable
{
	int sourceId;
	int ETTpid;
	ePtr<iDVBDemux> m_demux;
	eAUTable<eTable<EventInformationSection> > *m_EIT;
	eAUTable<eTable<MasterGuideTableSection> > *m_ATSC_MGT;
	eAUTable<eTable<ATSCEventInformationSection> > *m_ATSC_EIT;
	ePtr<iDVBSectionReader> m_now_ETT, m_next_ETT;
	ePtr<eConnection> m_now_conn, m_next_conn;
	void MGTready(int error);
	void EITready(int error);
	void nowETTsection(const uint8_t *d);
	void nextETTsection(const uint8_t *d);

	RESULT parseEvent(ePtr<eServiceEvent> &serviceevent, const Event &dvbevent);

	ePtr<eServiceEvent> m_event_now, m_event_next;
public:
	eDVBServiceEITHandler();
	~eDVBServiceEITHandler();

	void inject(ePtr<eServiceEvent> &event, int nownext);
	void start(iDVBDemux *demux, const eServiceReferenceDVB &ref);

	RESULT getEvent(ePtr<eServiceEvent> &event, int nownext);

	PSignal1<void, int> m_eit_changed;
};

#endif
