#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicedvb.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>

#include <lib/service/servicedvbrecord.h>
#include <lib/dvb/metaparser.h>

class eStaticServiceDVBPVRInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBPVRInformation);
	eServiceReference m_ref;
	eDVBMetaParser m_parser;
public:
	eStaticServiceDVBPVRInformation(const eServiceReference &ref);
	RESULT getName(const eServiceReference &ref, std::string &name);
};

DEFINE_REF(eStaticServiceDVBPVRInformation);

eStaticServiceDVBPVRInformation::eStaticServiceDVBPVRInformation(const eServiceReference &ref)
{
	m_ref = ref;
	m_parser.parseFile(ref.path);
}

RESULT eStaticServiceDVBPVRInformation::getName(const eServiceReference &ref, std::string &name)
{
	ASSERT(ref == m_ref);
	name = m_parser.m_name.size() ? m_parser.m_name : ref.path;
}

DEFINE_REF(eServiceFactoryDVB)

eServiceFactoryDVB::eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryDVB::id, this);
}

eServiceFactoryDVB::~eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryDVB::id);
}

DEFINE_REF(eDVBServiceList);

eDVBServiceList::eDVBServiceList(const eServiceReference &parent): m_parent(parent)
{
}

eDVBServiceList::~eDVBServiceList()
{
}

RESULT eDVBServiceList::getContent(std::list<eServiceReference> &list)
{
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;
	
	int err;
	if ((err = eDVBResourceManager::getInstance(res)) != 0)
	{
		eDebug("no resource manager");
		return err;
	}
	if ((err = res->getChannelList(db)) != 0)
	{
		eDebug("no channel list");
		return err;
	}
	
	ePtr<iDVBChannelListQuery> query;
	
	ePtr<eDVBChannelQuery> q;
	
	if (m_parent.path.size())
		eDVBChannelQuery::compile(q, m_parent.path);
	
	if ((err = db->startQuery(query, q)) != 0)
	{
		eDebug("startQuery failed");
		return err;
	}
	
	eServiceReferenceDVB ref;
	
	while (!query->getNextResult(ref))
		list.push_back(ref);
	return 0;
}

RESULT eDVBServiceList::getNext(eServiceReference &)
{
		/* implement me */
	return -1;
}

RESULT eServiceFactoryDVB::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ePtr<eDVBService> service;
	int r = lookupService(service, ref);
	if (r)
		service = 0;
		// check resources...
	ptr = new eDVBServicePlay(ref, service);
	return 0;
}

RESULT eServiceFactoryDVB::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr = new eDVBServiceRecord((eServiceReferenceDVB&)ref);
	return 0;
}

RESULT eServiceFactoryDVB::list(const eServiceReference &ref, ePtr<iListableService> &ptr)
{
	ptr = new eDVBServiceList(ref);
	return 0;
}

RESULT eServiceFactoryDVB::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
		/* do we have a PVR service? */
	if (ref.path.size())
	{
		ptr = new eStaticServiceDVBPVRInformation(ref);
		return 0;
	} else
	{
		ePtr<eDVBService> service;
		int r = lookupService(service, ref);
		if (r)
			return r;
			/* eDVBService has the iStaticServiceInformation interface, so we pass it here. */
		ptr = service;
		return 0;
	}
}

RESULT eServiceFactoryDVB::lookupService(ePtr<eDVBService> &service, const eServiceReference &ref)
{
			// TODO: handle the listing itself
	// if (ref.... == -1) .. return "... bouquets ...";
	// could be also done in another serviceFactory (with seperate ID) to seperate actual services and lists
			// TODO: cache
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;
	
	int err;
	if ((err = eDVBResourceManager::getInstance(res)) != 0)
	{
		eDebug("no resource manager");
		return err;
	}
	if ((err = res->getChannelList(db)) != 0)
	{
		eDebug("no channel list");
		return err;
	}
	
		/* we are sure to have a ..DVB reference as the info() call was forwarded here according to it's ID. */
	if ((err = db->getService((eServiceReferenceDVB&)ref, service)) != 0)
	{
		eDebug("getService failed!");
		return err;
	}

	return 0;
}

eDVBServicePlay::eDVBServicePlay(const eServiceReference &ref, eDVBService *service): 
	m_reference(ref), m_dvb_service(service)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServicePlay::serviceEvent);
	CONNECT(m_event_handler.m_eit_changed, eDVBServicePlay::gotNewEvent);
	eDebug("DVB start (play)");
}

eDVBServicePlay::~eDVBServicePlay()
{
	eDebug("DVB stop (play)");
}

void eDVBServicePlay::gotNewEvent()
{
#if 0
		// debug only
	ePtr<eServiceEvent> m_event_now, m_event_next;
	getEvent(m_event_now, 0);
	getEvent(m_event_next, 1);

	if (m_event_now)
		eDebug("now running: %s (%d seconds :)", m_event_now->m_event_name.c_str(), m_event_now->m_duration);
	if (m_event_next)
		eDebug("next running: %s (%d seconds :)", m_event_next->m_event_name.c_str(), m_event_next->m_duration);
#endif
	m_event((iPlayableService*)this, evUpdatedEventInfo);
}

void eDVBServicePlay::serviceEvent(int event)
{
	eDebug("service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		ePtr<iDVBDemux> m_demux;
		if (!m_service_handler.getDemux(m_demux))
		{
//			eventStartedEventAcquisition
			m_event_handler.start(m_demux, ((eServiceReferenceDVB&)m_reference).getServiceID().get());
		} else
			eDebug("no event data available :( ");
//			eventNoEvent
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		int vpid = -1, apid = -1, pcrpid = -1;
		eDVBServicePMTHandler::program program;
		if (m_service_handler.getProgramInfo(program))
			eDebug("getting program info failed.");
		else
		{
			eDebugNoNewLine("have %d video stream(s)", program.videoStreams.size());
			if (!program.videoStreams.empty())
			{
				eDebugNoNewLine(" (");
				for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
					i(program.videoStreams.begin()); 
					i != program.videoStreams.end(); ++i)
				{
					if (vpid == -1)
						vpid = i->pid;
					if (i != program.videoStreams.begin())
						eDebugNoNewLine(", ");
					eDebugNoNewLine("%04x", i->pid);
				}
				eDebugNoNewLine(")");
			}
			eDebugNoNewLine(", and %d audio stream(s)", program.audioStreams.size());
			if (!program.audioStreams.empty())
			{
				eDebugNoNewLine(" (");
				for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
					i(program.audioStreams.begin()); 
					i != program.audioStreams.end(); ++i)
				{
					if (apid == -1)
						apid = i->pid;
					if (i != program.audioStreams.begin())
						eDebugNoNewLine(", ");
					eDebugNoNewLine("%04x", i->pid);
				}
				eDebugNoNewLine(")");
			}
			eDebug(", and the pcr pid is %04x", program.pcrPid);
			if (program.pcrPid != 0x1fff)
				pcrpid = program.pcrPid;
		}
		
		if (!m_decoder)
		{
			ePtr<iDVBDemux> demux;
			m_service_handler.getDemux(demux);
			if (demux)
				demux->getMPEGDecoder(m_decoder);
		}

		if (m_decoder)
		{
			m_decoder->setVideoPID(vpid);
			m_decoder->setAudioPID(apid, 0);
			m_decoder->setSyncPCR(pcrpid);
			m_decoder->start();
// how we can do this better?
// update cache pid when the user changed the audio track or video track
// TODO handling of difference audio types.. default audio types..
			m_dvb_service->setCachePID(eDVBService::cVPID, vpid);
			m_dvb_service->setCachePID(eDVBService::cAPID, apid);
			m_dvb_service->setCachePID(eDVBService::cPCRPID, pcrpid);
		}
		
		break;
	}
	}
}

RESULT eDVBServicePlay::start()
{
	eDebug("starting DVB service");
	m_event(this, evStart);
	return m_service_handler.tune((eServiceReferenceDVB&)m_reference);
}

RESULT eDVBServicePlay::stop()
{
	eDebug("stopping..");
	return 0;
}

RESULT eDVBServicePlay::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eDVBServicePlay::pause(ePtr<iPauseableService> &ptr)
{
		// not yet possible, maybe later...
	ptr = 0;
	return -1;
}

RESULT eDVBServicePlay::info(ePtr<iServiceInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::getName(std::string &name)
{
	if (m_dvb_service)
		m_dvb_service->getName(m_reference, name);
	else
		name = "DVB service";
	return 0;
}

RESULT eDVBServicePlay::getEvent(ePtr<eServiceEvent> &evt, int nownext)
{
	return m_event_handler.getEvent(evt, nownext);
}

DEFINE_REF(eDVBServicePlay)

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
