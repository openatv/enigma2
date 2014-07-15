#ifndef __lib_dvb_eit_h
#define __lib_dvb_eit_h

#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <dvbsi++/event_information_section.h>
#include <lib/service/event.h>

class eDVBServiceEITHandler: public Object
{
	ePtr<iDVBDemux> m_demux;
	eAUTable<eTable<EventInformationSection> > m_EIT;
	void EITready(int error);

	RESULT parseEvent(ePtr<eServiceEvent> &serviceevent, const Event &dvbevent);

	ePtr<eServiceEvent> m_event_now, m_event_next;
public:
	eDVBServiceEITHandler();

	void inject(ePtr<eServiceEvent> &event, int nownext);
	void start(iDVBDemux *demux, int sid);
	void startOther(iDVBDemux *demux, int sid);

	RESULT getEvent(ePtr<eServiceEvent> &event, int nownext);

	PSignal1<void, int> m_eit_changed;
};

#endif
