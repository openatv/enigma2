#ifndef __lib_dvb_eit_h
#define __lib_dvb_eit_h

#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/atsc.h>
#include <dvbsi++/event_information_section.h>
#include <lib/service/event.h>

class eDVBServiceEITHandler: public Object
{
	int sourceId;
	int ETTpid;
	ePtr<iDVBDemux> m_demux;
	eAUTable<eTable<EventInformationSection> > *m_EIT;
	eAUTable<eTable<MasterGuideTableSection> > *m_ATSC_MGT;
	eAUTable<eTable<ATSCEventInformationSection> > *m_ATSC_EIT;
	eAUTable<eTable<ExtendedTextTableSection> > *m_ATSC_ETT;
	void MGTready(int error);
	void EITready(int error);
	void ETTready(int error);

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
