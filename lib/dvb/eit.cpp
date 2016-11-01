#include <lib/dvb/eit.h>
#include <lib/dvb/specs.h>
#include <lib/base/eerror.h>
#include <lib/service/event.h>

void eDVBServiceEITHandler::EITready(int error)
{
	if (!error)
	{
		if (m_EIT)
		{
			ePtr<eTable<EventInformationSection> > ptr;
			if (!m_EIT->getCurrent(ptr))
			{
				int a = 0;
				for (std::vector<EventInformationSection*>::const_iterator i = ptr->getSections().begin();
					i != ptr->getSections().end(); ++i)
				{
					const EventInformationSection *eit = *i;
					for (EventConstIterator ev = eit->getEvents()->begin(); ev != eit->getEvents()->end(); ++ev)
					{
						ePtr<eServiceEvent> evt = new eServiceEvent();
						evt->parseFrom(*ev,(eit->getTransportStreamId()<<16)|eit->getOriginalNetworkId());
						if (!a)
							m_event_now = evt;
						else
							m_event_next = evt;
						++a;
					}
				}
			}
		}
		else if (m_ATSC_EIT)
		{
			bool hasETM = false;
			ePtr<eTable<ATSCEventInformationSection> > ptr;
			if (!m_ATSC_EIT->getCurrent(ptr))
			{
				int a = 0;
				for (std::vector<ATSCEventInformationSection*>::const_iterator i = ptr->getSections().begin();
					i != ptr->getSections().end(); ++i)
				{
					const ATSCEventInformationSection *eit = *i;
					for (ATSCEventListConstIterator ev = eit->getEvents()->begin(); ev != eit->getEvents()->end(); ++ev)
					{
						ePtr<eServiceEvent> evt = new eServiceEvent();
						evt->parseFrom(*ev);
						if ((*ev)->getETMLocation() == 1)
						{
							/* ETM on current transponder */
							hasETM = true;
						}
						if (!a)
							m_event_now = evt;
						else
							m_event_next = evt;
						++a;
						if (a > 1) break;
					}
					if (a > 1) break;
				}
			}
			if (hasETM && ETTpid != -1)
			{
				if (!m_ATSC_ETT)
				{
					m_ATSC_ETT = new eAUTable<eTable<ExtendedTextTableSection> >();
					CONNECT(m_ATSC_ETT->tableReady, eDVBServiceEITHandler::ETTready);
				}
				if (m_ATSC_ETT)
				{
					m_ATSC_ETT->begin(eApp, eATSCETTSpec(ETTpid), m_demux);
				}
			}
		}
	}

	m_eit_changed(error);
}

void eDVBServiceEITHandler::MGTready(int error)
{
	ETTpid = -1;
	int eitpid = -1;
	if (!error)
	{
		if (m_ATSC_MGT)
		{
			ePtr<eTable<MasterGuideTableSection> > ptr;
			if (!m_ATSC_MGT->getCurrent(ptr))
			{
				for (std::vector<MasterGuideTableSection*>::const_iterator i = ptr->getSections().begin();
					i != ptr->getSections().end(); ++i)
				{
					const MasterGuideTableSection *mgt = *i;
					for (MasterGuideTableListConstIterator table = mgt->getTables()->begin(); table != mgt->getTables()->end(); ++table)
					{
						if ((*table)->getTableType() == 0x0100)
						{
							/* EIT-0 */
							eitpid = (*table)->getPID();
						}
						else if ((*table)->getTableType() == 0x0200)
						{
							/* ETT-0 */
							ETTpid = (*table)->getPID();
						}
					}
				}
			}
		}
	}

	if (eitpid != -1)
	{
		if (!m_ATSC_EIT)
		{
			m_ATSC_EIT = new eAUTable<eTable<ATSCEventInformationSection> >();
			CONNECT(m_ATSC_EIT->tableReady, eDVBServiceEITHandler::EITready);
		}
		if (m_ATSC_EIT)
		{
			m_ATSC_EIT->begin(eApp, eATSCEITSpec(eitpid, sourceId), m_demux);
		}
	}
	else
	{
		m_eit_changed(-1);
	}
}

void eDVBServiceEITHandler::ETTready(int error)
{
	if (!error)
	{
		if (m_ATSC_ETT)
		{
			bool update = false;
			uint32_t nowetm = ((sourceId & 0xffff) << 16) | ((m_event_now->getEventId() & 0x3fff) << 2) | 0x2;
			uint32_t nextetm = ((sourceId & 0xffff) << 16) | ((m_event_next->getEventId() & 0x3fff) << 2) | 0x2;
			ePtr<eTable<ExtendedTextTableSection> > ptr;
			if (!m_ATSC_ETT->getCurrent(ptr))
			{
				for (std::vector<ExtendedTextTableSection*>::const_iterator i = ptr->getSections().begin();
					i != ptr->getSections().end(); ++i)
				{
					const ExtendedTextTableSection *ett = *i;
					if (ett->getETMId() == nowetm)
					{
						m_event_now->parseFrom(ett);
						update = true;
					}
					else if (ett->getETMId() == nextetm)
					{
						m_event_next->parseFrom(ett);
						update = true;
					}
				}
			}
			if (update) m_eit_changed(0);
		}
	}
}

void eDVBServiceEITHandler::inject(ePtr<eServiceEvent> &event, int nownext)
{
	if (nownext)
		m_event_next = event;
	else
		m_event_now = event;
	m_eit_changed(0);
}

eDVBServiceEITHandler::eDVBServiceEITHandler()
{
	m_EIT = NULL;
	m_ATSC_MGT = NULL;
	m_ATSC_EIT = NULL;
	m_ATSC_ETT = NULL;
}

eDVBServiceEITHandler::~eDVBServiceEITHandler()
{
	delete m_EIT;
	delete m_ATSC_MGT;
	delete m_ATSC_EIT;
	delete m_ATSC_ETT;
}

void eDVBServiceEITHandler::start(iDVBDemux *demux, const eServiceReferenceDVB &ref)
{
	sourceId = ref.getSourceID();
	m_demux = demux;
	if (sourceId)
	{
		if (!m_ATSC_MGT)
		{
			m_ATSC_MGT = new eAUTable<eTable<MasterGuideTableSection> >();
			CONNECT(m_ATSC_MGT->tableReady, eDVBServiceEITHandler::MGTready);
		}
		m_ATSC_MGT->begin(eApp, eATSCMGTSpec(), m_demux);
	}
	else
	{
		int sid = ref.getParentServiceID().get();
		if (!sid)
		{
			sid = ref.getServiceID().get();
		}

		if (!m_EIT)
		{
			m_EIT = new eAUTable<eTable<EventInformationSection> >();
			CONNECT(m_EIT->tableReady, eDVBServiceEITHandler::EITready);
		}
		if (ref.getParentTransportStreamID().get() && ref.getParentTransportStreamID() != ref.getTransportStreamID())
		{
			m_EIT->begin(eApp, eDVBEITSpecOther(sid), m_demux);
		}
		else
		{
			m_EIT->begin(eApp, eDVBEITSpec(sid), m_demux);
		}
	}
}

RESULT eDVBServiceEITHandler::getEvent(ePtr<eServiceEvent> &event, int nownext)
{
	event = nownext ? m_event_next : m_event_now;
	if (!event)
		return -1;
	return 0;
}
