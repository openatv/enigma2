#include <lib/dvb/eit.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvbtime.h>
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
			ePtr<eTable<ATSCEventInformationSection> > ptr;
			if (!m_ATSC_EIT->getCurrent(ptr))
			{
				int a = 0;
				time_t now = eDVBLocalTimeHandler::getInstance()->nowTime() - (time_t)315964800; /* ATSC GPS system time epoch is 00:00 Jan 6th 1980 */;
				for (std::vector<ATSCEventInformationSection*>::const_iterator i = ptr->getSections().begin();
					i != ptr->getSections().end(); ++i)
				{
					const ATSCEventInformationSection *eit = *i;
					for (ATSCEventListConstIterator ev = eit->getEvents()->begin(); ev != eit->getEvents()->end(); ++ev)
					{
						if ((*ev)->getStartTime() + (*ev)->getLengthInSeconds() < now)
						{
							continue;
						}
						ePtr<eServiceEvent> evt = new eServiceEvent();
						evt->parseFrom(*ev);
						if (ETTpid != -1 && (*ev)->getETMLocation() == 1)
						{
							/* ETM on current transponder */
							uint32_t etm = ((sourceId & 0xffff) << 16) | ((evt->getEventId() & 0x3fff) << 2) | 0x2;
							eDVBSectionFilterMask mask;
							memset(&mask, 0, sizeof(mask));
							mask.pid   = ETTpid;
							mask.flags = eDVBSectionFilterMask::rfCRC;
							mask.data[0] = 0xcc;
							mask.mask[0] = 0xff;
							mask.data[7] = (etm >> 24) & 0xff;
							mask.data[8] = (etm >> 16) & 0xff;
							mask.data[9] = (etm >> 8) & 0xff;
							mask.data[10] = etm & 0xff;
							mask.mask[7] = mask.mask[8] = mask.mask[9] = mask.mask[10] = 0xff;
							if (!a)
							{
								m_demux->createSectionReader(eApp, m_now_ETT);
								m_now_ETT->connectRead(sigc::mem_fun(*this, &eDVBServiceEITHandler::nowETTsection), m_now_conn);
								m_now_ETT->start(mask);
							}
							else
							{
								m_demux->createSectionReader(eApp, m_next_ETT);
								m_next_ETT->connectRead(sigc::mem_fun(*this, &eDVBServiceEITHandler::nextETTsection), m_next_conn);
								m_next_ETT->start(mask);
							}
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
		}
	}

	m_eit_changed(error);
}

void eDVBServiceEITHandler::MGTready(int error)
{
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
		delete m_ATSC_EIT;
		m_ATSC_EIT = new eAUTable<eTable<ATSCEventInformationSection> >();
		CONNECT(m_ATSC_EIT->tableReady, eDVBServiceEITHandler::EITready);
		m_ATSC_EIT->begin(eApp, eATSCEITSpec(eitpid, sourceId), m_demux);
	}
	else
	{
		m_eit_changed(-1);
	}
}

void eDVBServiceEITHandler::nowETTsection(const uint8_t *d)
{
	ExtendedTextTableSection ett(d);
	if (m_event_now) m_event_now->parseFrom(&ett);
	m_now_ETT->stop();
	m_now_ETT = NULL;
	m_now_conn = NULL;
	m_eit_changed(0);
}

void eDVBServiceEITHandler::nextETTsection(const uint8_t *d)
{
	ExtendedTextTableSection ett(d);
	if (m_event_next) m_event_next->parseFrom(&ett);
	m_next_ETT->stop();
	m_next_ETT = NULL;
	m_next_conn = NULL;
	m_eit_changed(0);
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
	ETTpid = -1;
}

eDVBServiceEITHandler::~eDVBServiceEITHandler()
{
	delete m_EIT;
	delete m_ATSC_MGT;
	delete m_ATSC_EIT;
	m_now_ETT = NULL;
	m_now_conn = NULL;
	m_next_ETT = NULL;
	m_next_conn = NULL;
}

void eDVBServiceEITHandler::start(iDVBDemux *demux, const eServiceReferenceDVB &ref)
{
	sourceId = ref.getSourceID();
	m_demux = demux;
	if (sourceId)
	{
		delete m_ATSC_MGT;
		m_ATSC_MGT = new eAUTable<eTable<MasterGuideTableSection> >();
		CONNECT(m_ATSC_MGT->tableReady, eDVBServiceEITHandler::MGTready);
		m_ATSC_MGT->begin(eApp, eATSCMGTSpec(), m_demux);
	}
	else
	{
		int sid = ref.getParentServiceID().get();
		if (!sid)
		{
			sid = ref.getServiceID().get();
		}

		delete m_EIT;
		m_EIT = new eAUTable<eTable<EventInformationSection> >();
		CONNECT(m_EIT->tableReady, eDVBServiceEITHandler::EITready);
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
