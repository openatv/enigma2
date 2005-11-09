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
#include <lib/dvb/tstools.h>

class eStaticServiceDVBInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBInformation);
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
};

DEFINE_REF(eStaticServiceDVBInformation);

RESULT eStaticServiceDVBInformation::getName(const eServiceReference &ref, std::string &name)
{
	if ( ref.name.length() )
	{
		name = ref.name;
		return 0;
	}
	else
		return -1;
}

int eStaticServiceDVBInformation::getLength(const eServiceReference &ref)
{
	return -1;
}

class eStaticServiceDVBBouquetInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBBouquetInformation);
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
};

DEFINE_REF(eStaticServiceDVBBouquetInformation);

RESULT eStaticServiceDVBBouquetInformation::getName(const eServiceReference &ref, std::string &name)
{
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;

	int err;
	if ((err = eDVBResourceManager::getInstance(res)) != 0)
	{
		eDebug("eStaticServiceDVBBouquetInformation::getName failed.. no resource manager!");
		return err;
	}
	if ((err = res->getChannelList(db)) != 0)
	{
		eDebug("eStaticServiceDVBBouquetInformation::getName failed.. no channel list!");
		return err;
	}

	const eBouquet *bouquet=0;
	if ((err = db->getBouquet(ref, bouquet)) != 0)
	{
		eDebug("eStaticServiceDVBBouquetInformation::getName failed.. getBouquet failed!");
		return -1;
	}

	if ( bouquet && bouquet->m_bouquet_name.length() )
	{
		name = "[Bouquet] " + bouquet->m_bouquet_name;
		return 0;
	}
	else
		return -1;
}

int eStaticServiceDVBBouquetInformation::getLength(const eServiceReference &ref)
{
	return -1;
}

class eStaticServiceDVBPVRInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBPVRInformation);
	eServiceReference m_ref;
	eDVBMetaParser m_parser;
public:
	eStaticServiceDVBPVRInformation(const eServiceReference &ref);
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
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
	return 0;
}

int eStaticServiceDVBPVRInformation::getLength(const eServiceReference &ref)
{
	ASSERT(ref == m_ref);
	
	eDVBTSTools tstools;
	
	if (tstools.openFile(ref.path.c_str()))
		return 0;

	pts_t len;
	if (tstools.calcLen(len))
		return 0;

	return len / 90000;
}



class eDVBPVRServiceOfflineOperations: public iServiceOfflineOperations
{
	DECLARE_REF(eDVBPVRServiceOfflineOperations);
	eServiceReferenceDVB m_ref;
public:
	eDVBPVRServiceOfflineOperations(const eServiceReference &ref);
	
	RESULT deleteFromDisk(int simulate);
	RESULT getListOfFilenames(std::list<std::string> &);
};

DEFINE_REF(eDVBPVRServiceOfflineOperations);

eDVBPVRServiceOfflineOperations::eDVBPVRServiceOfflineOperations(const eServiceReference &ref): m_ref((const eServiceReferenceDVB&)ref)
{
}

RESULT eDVBPVRServiceOfflineOperations::deleteFromDisk(int simulate)
{
	if (simulate)
		return 0;
	else
	{
		std::list<std::string> res;
		if (getListOfFilenames(res))
			return -1;
		
				/* TODO: deferred removing.. */
		for (std::list<std::string>::iterator i(res.begin()); i != res.end(); ++i)
		{
			eDebug("Removing %s...", i->c_str());
			::unlink(i->c_str());
		}
		
		return 0;
	}
}

RESULT eDVBPVRServiceOfflineOperations::getListOfFilenames(std::list<std::string> &res)
{
	res.clear();
	res.push_back(m_ref.path);
	return 0;
}



DEFINE_REF(eServiceFactoryDVB)

eServiceFactoryDVB::eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryDVB::id, this);
}

eServiceFactoryDVB::~eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
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

RESULT eDVBServiceList::startQuery()
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
	
	ePtr<eDVBChannelQuery> q;
	
	if (m_parent.path.size())
	{
		eDVBChannelQuery::compile(q, m_parent.path);
		if (!q)
		{
			eDebug("compile query failed");
			return err;
		}
	}
	
	if ((err = db->startQuery(m_query, q, m_parent)) != 0)
	{
		eDebug("startQuery failed");
		return err;
	}

	return 0;
}

RESULT eDVBServiceList::getContent(std::list<eServiceReference> &list)
{
	eServiceReferenceDVB ref;
	
	if (!m_query)
		return -1;
	
	while (!m_query->getNextResult(ref))
		list.push_back(ref);
	return 0;
}

RESULT eDVBServiceList::getNext(eServiceReference &ref)
{
	if (!m_query)
		return -1;
	
	return m_query->getNextResult((eServiceReferenceDVB&)ref);
}

int eDVBServiceList::compareLessEqual(const eServiceReference &a, const eServiceReference &b)
{
	return m_query->compareLessEqual((const eServiceReferenceDVB&)a, (const eServiceReferenceDVB&)b);
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
	ePtr<eDVBServiceList> list = new eDVBServiceList(ref);
	if (list->startQuery())
	{
		ptr = 0;
		return -1;
	}
	
	ptr = list;
	return 0;
}

RESULT eServiceFactoryDVB::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
		/* do we have a PVR service? */
	if (ref.flags & eServiceReference::flagDirectory) // bouquet
	{
		ptr = new eStaticServiceDVBBouquetInformation;
		return 0;
	}
	else if (ref.path.size())
	{
		ptr = new eStaticServiceDVBPVRInformation(ref);
		return 0;
	}
	else
	{
		ePtr<eDVBService> service;
		int r = lookupService(service, ref);
		if (r)
			ptr = new eStaticServiceDVBInformation;
		else
			/* eDVBService has the iStaticServiceInformation interface, so we pass it here. */
			ptr = service;
		return 0;
	}
}

RESULT eServiceFactoryDVB::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
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
	m_reference(ref), m_dvb_service(service), m_service_handler(0)
{
	m_is_pvr = !ref.path.empty();
	
	CONNECT(m_service_handler.serviceEvent, eDVBServicePlay::serviceEvent);
	CONNECT(m_event_handler.m_eit_changed, eDVBServicePlay::gotNewEvent);
}

eDVBServicePlay::~eDVBServicePlay()
{
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
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		ePtr<iDVBDemux> m_demux;
		if (!m_service_handler.getDemux(m_demux))
		{
//			eventStartedEventAcquisition
			m_event_handler.start(m_demux, ((eServiceReferenceDVB&)m_reference).getServiceID().get());
		}
//			eventNoEvent
		break;
	}
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("DVB service failed to tune");
		m_event((iPlayableService*)this, evTuneFailed);
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
			if (!m_is_pvr)
				m_decoder->setSyncPCR(pcrpid);
			else
				m_decoder->setSyncPCR(-1);
			m_decoder->start();
// how we can do this better?
// update cache pid when the user changed the audio track or video track
// TODO handling of difference audio types.. default audio types..
				
				/* don't worry about non-existing services, nor pvr services */
			if (m_dvb_service && !m_is_pvr)
			{
				m_dvb_service->setCachePID(eDVBService::cVPID, vpid);
				m_dvb_service->setCachePID(eDVBService::cAPID, apid);
				m_dvb_service->setCachePID(eDVBService::cPCRPID, pcrpid);
			}
		}
		
		break;
	}
	}
}

RESULT eDVBServicePlay::start()
{
	int r;
	eDebug("starting DVB service");
	r = m_service_handler.tune((eServiceReferenceDVB&)m_reference);
	eDebug("tune result: %d", r);
	m_event(this, evStart);
	return 0;
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

RESULT eDVBServicePlay::seek(ePtr<iSeekableService> &ptr)
{
	if (m_is_pvr)
	{
		ptr = this;
		return 0;
	}
	
	ptr = 0;
	return -1;
}

RESULT eDVBServicePlay::getLength(pts_t &len)
{
	ePtr<iDVBPVRChannel> pvr_channel;
	
	if (m_service_handler.getPVRChannel(pvr_channel))
	{
		eDebug("getPVRChannel failed!");
		return -1;
	}
	
	return pvr_channel->getLength(len);
}

RESULT eDVBServicePlay::seekTo(pts_t to)
{
	return -1;
}

RESULT eDVBServicePlay::getPlayPosition(pts_t &pos)
{
	ePtr<iDVBPVRChannel> pvr_channel;
	
	if (m_service_handler.getPVRChannel(pvr_channel))
		return -1;
	
	return pvr_channel->getCurrentPosition(pos);
}

RESULT eDVBServicePlay::info(ePtr<iServiceInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::getName(std::string &name)
{
	if (m_dvb_service)
	{
		m_dvb_service->getName(m_reference, name);
		if (name.empty())
			name = "(...)";
	} else
		name = "DVB service";
	return 0;
}

RESULT eDVBServicePlay::getEvent(ePtr<eServiceEvent> &evt, int nownext)
{
	return m_event_handler.getEvent(evt, nownext);
}

DEFINE_REF(eDVBServicePlay)

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
