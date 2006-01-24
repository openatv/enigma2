#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicedvb.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/decoder.h>

#include <lib/service/servicedvbrecord.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb/tstools.h>
#include <lib/python/python.h>

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
	eServiceReferenceDVB &service = (eServiceReferenceDVB&)ref;
	if ( !ref.name.empty() )
	{
		if (service.getParentTransportStreamID().get()) // linkage subservice
		{
			ePtr<iServiceHandler> service_center;
			if (!eServiceCenter::getInstance(service_center))
			{
				eServiceReferenceDVB parent = service;
				parent.setTransportStreamID( service.getParentTransportStreamID() );
				parent.setServiceID( service.getParentServiceID() );
				parent.setParentTransportStreamID(eTransportStreamID(0));
				parent.setParentServiceID(eServiceID(0));
				parent.name="";
				ePtr<iStaticServiceInformation> service_info;
				if (!service_center->info(parent, service_info))
				{
					if (!service_info->getName(parent, name))
					{
						// just show short name
						unsigned int pos = name.find("\xc2\x86");
						if ( pos != std::string::npos )
							name.erase(0, pos+2);
						pos = name.find("\xc2\x87");
						if ( pos != std::string::npos )
							name.erase(pos);
						name+=" - ";
					}
				}
			}
		}
		else
			name="";
		name += ref.name;
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

	eBouquet *bouquet=0;
	if ((err = db->getBouquet(ref, bouquet)) != 0)
	{
		eDebug("eStaticServiceDVBBouquetInformation::getName failed.. getBouquet failed!");
		return -1;
	}

	if ( bouquet && bouquet->m_bouquet_name.length() )
	{
		name = bouquet->m_bouquet_name;
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
	
	int getInfo(const eServiceReference &ref, int w);
	std::string getInfoString(const eServiceReference &ref,int w);
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

int eStaticServiceDVBPVRInformation::getInfo(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sDescription:
		return iServiceInformation::resIsString;
	case iServiceInformation::sTimeCreate:
		if (m_parser.m_time_create)
			return m_parser.m_time_create;
		else
			return iServiceInformation::resNA;
	default:
		return iServiceInformation::resNA;
	}
}

std::string eStaticServiceDVBPVRInformation::getInfoString(const eServiceReference &ref,int w)
{
	switch (w)
	{
	case iServiceInformation::sDescription:
		return m_parser.m_description;
	default:
		return "";
	}
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
	res.push_back(m_ref.path + ".meta");
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
	
	if (!m_parent.path.empty())
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

RESULT eDVBServiceList::getContent(PyObject *list, bool sorted)
{
	eServiceReferenceDVB ref;

	if (!m_query || !list || !PyList_Check(list))
		return -1;

	std::list<eServiceReferenceDVB> tmplist;

	while (!m_query->getNextResult(ref))
		tmplist.push_back(ref);

	if (sorted)
		tmplist.sort(iListableServiceCompare(this));

	for (std::list<eServiceReferenceDVB>::iterator it(tmplist.begin());
		it != tmplist.end(); ++it)
	{
		PyObject *refobj = New_eServiceReference(*it);
		PyList_Append(list, refobj);
		Py_DECREF(refobj);
	}
	return 0;
}

RESULT eDVBServiceList::getContent(std::list<eServiceReference> &list, bool sorted)
{
	eServiceReferenceDVB ref;
	
	if (!m_query)
		return -1;
	
	while (!m_query->getNextResult(ref))
		list.push_back(ref);

	if (sorted)
		list.sort(iListableServiceCompare(this));

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

RESULT eDVBServiceList::startEdit(ePtr<iMutableServiceList> &res)
{
	if (m_parent.flags & eServiceReference::flagDirectory) // bouquet
	{
		ePtr<iDVBChannelList> db;
		ePtr<eDVBResourceManager> resm;

		if (eDVBResourceManager::getInstance(resm) || resm->getChannelList(db))
			return -1;

		if (db->getBouquet(m_parent, m_bouquet) != 0)
			return -1;

		res = this;
		
		return 0;
	}
	res = 0;
	return -1;
}

RESULT eDVBServiceList::addService(eServiceReference &ref)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->addService(ref);
}

RESULT eDVBServiceList::removeService(eServiceReference &ref)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->removeService(ref);
}

RESULT eDVBServiceList::moveService(eServiceReference &ref, int pos)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->moveService(ref, pos);
}

RESULT eDVBServiceList::flushChanges()
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->flushChanges();
}

RESULT eDVBServiceList::setListName(const std::string &name)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->setListName(name);
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
	if (ref.path.empty())
	{
		ptr = new eDVBServiceRecord((eServiceReferenceDVB&)ref);
		return 0;
	} else
	{
		ptr = 0;
		return -1;
	}
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
	/* is a listable service? */
	if ((ref.flags & eServiceReference::flagDirectory) == eServiceReference::flagDirectory) // bouquet
	{
		if ( !ref.name.empty() )  // satellites or providers list
			ptr = new eStaticServiceDVBInformation;
		else // a dvb bouquet
			ptr = new eStaticServiceDVBBouquetInformation;
	}
	else if (!ref.path.empty()) /* do we have a PVR service? */
		ptr = new eStaticServiceDVBPVRInformation(ref);
	else // normal dvb service
	{
		ePtr<eDVBService> service;
		if (lookupService(service, ref)) // no eDVBService avail for this reference ( Linkage Services... )
			ptr = new eStaticServiceDVBInformation;
		else
			/* eDVBService has the iStaticServiceInformation interface, so we pass it here. */
			ptr = service;
	}
	return 0;
}

RESULT eServiceFactoryDVB::offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr)
{
	if (ref.path.empty())
	{
		ptr = 0;
		return -1;
	} else
	{
		ptr = new eDVBPVRServiceOfflineOperations(ref);
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
	m_reference(ref), m_dvb_service(service), m_is_paused(0)
{
	m_is_pvr = !ref.path.empty();
	m_timeshift_enabled = m_timeshift_active = 0;
	
	CONNECT(m_service_handler.serviceEvent, eDVBServicePlay::serviceEvent);
	CONNECT(m_service_handler_timeshift.serviceEvent, eDVBServicePlay::serviceEventTimeshift);
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
		if (!m_service_handler.getDataDemux(m_demux))
		{
			eServiceReferenceDVB &ref = (eServiceReferenceDVB&) m_reference;
			int sid = ref.getParentServiceID().get();
			if (!sid)
				sid = ref.getServiceID().get();
			if ( ref.getParentTransportStreamID().get() &&
				ref.getParentTransportStreamID() != ref.getTransportStreamID() )
				m_event_handler.startOther(m_demux, sid);
			else
				m_event_handler.start(m_demux, sid);
		}
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
		eDebug("eventNewProgramInfo %d %d", m_timeshift_enabled, m_timeshift_active);
		if (m_timeshift_enabled)
			updateTimeshiftPids();
		if (!m_timeshift_active)
			updateDecoder();
		m_event((iPlayableService*)this, evUpdatedInfo);
		break;
	}
	case eDVBServicePMTHandler::eventEOF:
	{
		m_event((iPlayableService*)this, evEnd);
		break;
	}
	}
}

void eDVBServicePlay::serviceEventTimeshift(int event)
{
	switch (event)
	{
	case eDVBServicePMTHandler::eventNewProgramInfo:
		if (m_timeshift_active)
			updateDecoder();
		break;
	case eDVBServicePMTHandler::eventEOF:
		switchToLive();
		break;
	}
}

RESULT eDVBServicePlay::start()
{
	int r;
		/* in pvr mode, we only want to use one demux. in tv mode, we're using 
		   two (one for decoding, one for data source), as we must be prepared
		   to start recording from the data demux. */
	r = m_service_handler.tune((eServiceReferenceDVB&)m_reference, m_is_pvr);
	m_event(this, evStart);
	m_event((iPlayableService*)this, evSeekableStatusChanged);
	return 0;
}

RESULT eDVBServicePlay::stop()
{
	return 0;
}

RESULT eDVBServicePlay::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eDVBServicePlay::pause(ePtr<iPauseableService> &ptr)
{
		/* note: we check for timeshift to be enabled,
		   not neccessary active. if you pause when timeshift
		   is not active, you should activate it when unpausing */
	if ((!m_is_pvr) && (!m_timeshift_enabled))
	{
		ptr = 0;
		return -1;
	}

	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::setSlowMotion(int ratio)
{
	if (m_decoder)
		return m_decoder->setSlowMotion(ratio);
	else
		return -1;
}

RESULT eDVBServicePlay::setFastForward(int ratio)
{
	if (m_decoder)
		return m_decoder->setFastForward(ratio);
	else
		return -1;
}
    
RESULT eDVBServicePlay::seek(ePtr<iSeekableService> &ptr)
{
	if (m_is_pvr || m_timeshift_active)
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

RESULT eDVBServicePlay::pause()
{
	if (!m_is_paused && m_decoder)
	{
		m_is_paused = 1;
		return m_decoder->freeze(0);
	} else
		return -1;
}

RESULT eDVBServicePlay::unpause()
{
	if (m_is_paused && m_decoder)
	{
		m_is_paused = 0;
		return m_decoder->unfreeze();
	} else
		return -1;
}

RESULT eDVBServicePlay::seekTo(pts_t to)
{
	eDebug("eDVBServicePlay::seekTo: jump %lld", to);
	
	if (!m_decode_demux)
		return -1;

	ePtr<iDVBPVRChannel> pvr_channel;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
	return pvr_channel->seekTo(m_decode_demux, 0, to);
}

RESULT eDVBServicePlay::seekRelative(int direction, pts_t to)
{
	eDebug("eDVBServicePlay::seekRelative: jump %d, %lld", direction, to);
	
	if (!m_decode_demux)
		return -1;

	ePtr<iDVBPVRChannel> pvr_channel;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
	to *= direction;
	
	return pvr_channel->seekTo(m_decode_demux, 1, to);
}

RESULT eDVBServicePlay::getPlayPosition(pts_t &pos)
{
	ePtr<iDVBPVRChannel> pvr_channel;
	
	if (!m_decode_demux)
		return -1;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
	return pvr_channel->getCurrentPosition(m_decode_demux, pos, 1);
}

RESULT eDVBServicePlay::setTrickmode(int trick)
{
	if (m_decoder)
		m_decoder->setTrickmode(trick);
	return 0;
}

RESULT eDVBServicePlay::frontendStatusInfo(ePtr<iFrontendStatusInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::info(ePtr<iServiceInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::audioTracks(ePtr<iAudioTrackSelection> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::subServices(ePtr<iSubserviceList> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::timeshift(ePtr<iTimeshiftService> &ptr)
{
	if (m_timeshift_enabled || !m_is_pvr)
	{
		ptr = this;
		return 0;
	}
	ptr = 0;
	return -1;
}

RESULT eDVBServicePlay::getName(std::string &name)
{
	if (m_is_pvr)
	{
		ePtr<iStaticServiceInformation> i = new eStaticServiceDVBPVRInformation(m_reference);
		return i->getName(m_reference, name);
	}
	if (m_dvb_service)
	{
		m_dvb_service->getName(m_reference, name);
		if (name.empty())
			name = "(...)";
	}
	else if (!m_reference.name.empty())
		eStaticServiceDVBInformation().getName(m_reference, name);
	else
		name = "DVB service";
	return 0;
}

RESULT eDVBServicePlay::getEvent(ePtr<eServiceEvent> &evt, int nownext)
{
	return m_event_handler.getEvent(evt, nownext);
}

int eDVBServicePlay::getInfo(int w)
{
	eDVBServicePMTHandler::program program;

	if (m_service_handler.getProgramInfo(program))
		return -1;
	
	switch (w)
	{
	case sAspect:
		if (!program.videoStreams.empty() && program.videoStreams[0].component_tag != -1)
		{
			ePtr<eServiceEvent> evt;
			if (!m_event_handler.getEvent(evt, 0))
			{
				ePtr<eComponentData> data;
				if (!evt->getComponentData(data, program.videoStreams[0].component_tag))
				{
					if ( data->getStreamContent() == 1 )
					{
						switch(data->getComponentType())
						{
							// SD
							case 1: // 4:3 SD PAL
							case 2:
							case 3: // 16:9 SD PAL
							case 4: // > 16:9 PAL
							case 5: // 4:3 SD NTSC
							case 6: 
							case 7: // 16:9 SD NTSC
							case 8: // > 16:9 NTSC

							// HD
							case 9: // 4:3 HD PAL
							case 0xA:
							case 0xB: // 16:9 HD PAL
							case 0xC: // > 16:9 HD PAL
							case 0xD: // 4:3 HD NTSC
							case 0xE:
							case 0xF: // 16:9 HD NTSC
							case 0x10: // > 16:9 HD PAL
								return data->getComponentType();
						}
					}
				}
			}
		}
		return -1;
	case sIsCrypted: return program.isCrypted;
	case sVideoPID: if (program.videoStreams.empty()) return -1; return program.videoStreams[0].pid;
	case sAudioPID: if (program.audioStreams.empty()) return -1; return program.audioStreams[m_current_audio_stream].pid;
	case sPCRPID: return program.pcrPid;
	case sPMTPID: return program.pmtPid;
	case sTXTPID: return program.textPid;
	case sSID: return ((const eServiceReferenceDVB&)m_reference).getServiceID().get();
	case sONID: return ((const eServiceReferenceDVB&)m_reference).getOriginalNetworkID().get();
	case sTSID: return ((const eServiceReferenceDVB&)m_reference).getTransportStreamID().get();
	case sNamespace: return ((const eServiceReferenceDVB&)m_reference).getDVBNamespace().get();
	case sProvider: if (!m_dvb_service) return -1; return -2;
	default:
		return -1;
	}
}

std::string eDVBServicePlay::getInfoString(int w)
{	
	switch (w)
	{
	case sProvider:
		if (!m_dvb_service) return "";
		return m_dvb_service->m_provider_name;
	default:
		return "";
	}
}

int eDVBServicePlay::getNumberOfTracks()
{
	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
		return 0;
	return program.audioStreams.size();
}

RESULT eDVBServicePlay::selectTrack(unsigned int i)
{
	int ret = selectAudioStream(i);

	if (m_decoder->start())
		return -5;

	return ret;
}

RESULT eDVBServicePlay::getTrackInfo(struct iAudioTrackInfo &info, unsigned int i)
{
	eDVBServicePMTHandler::program program;

	if (m_service_handler.getProgramInfo(program))
		return -1;
	
	if (i >= program.audioStreams.size())
		return -2;
	
	if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atMPEG)
		info.m_description = "MPEG";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAC3)
		info.m_description = "AC3";
	else  if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atDTS)
		info.m_description = "DTS";
	else
		info.m_description = "???";

	if (program.audioStreams[i].component_tag != -1)
	{
		ePtr<eServiceEvent> evt;
		if (!m_event_handler.getEvent(evt, 0))
		{
			ePtr<eComponentData> data;
			if (!evt->getComponentData(data, program.audioStreams[i].component_tag))
				info.m_language = data->getText();
		}
	}

	if (info.m_language.empty())
		info.m_language = program.audioStreams[i].language_code;
	
	return 0;
}

int eDVBServicePlay::selectAudioStream(int i)
{
	eDVBServicePMTHandler::program program;

	if (m_service_handler.getProgramInfo(program))
		return -1;
	
	if ((unsigned int)i >= program.audioStreams.size())
		return -2;
	
	if (!m_decoder)
		return -3;
	
	if (m_decoder->setAudioPID(program.audioStreams[i].pid, program.audioStreams[i].type))
		return -4;

	if (m_dvb_service && !m_is_pvr)
	{
		if (program.audioStreams[i].type == eDVBAudio::aMPEG)
		{
			m_dvb_service->setCachePID(eDVBService::cAPID, program.audioStreams[i].pid);
			m_dvb_service->setCachePID(eDVBService::cAC3PID, -1);
		}	else
		{
			m_dvb_service->setCachePID(eDVBService::cAPID, -1);
			m_dvb_service->setCachePID(eDVBService::cAC3PID, program.audioStreams[i].pid);
		}
	}

	m_current_audio_stream = i;

	return 0;
}

int eDVBServicePlay::getFrontendInfo(int w)
{
	if (m_is_pvr)
		return 0;
	eUsePtr<iDVBChannel> channel;
	if(m_service_handler.getChannel(channel))
		return 0;
	ePtr<iDVBFrontend> fe;
	if(channel->getFrontend(fe))
		return 0;
	return fe->readFrontendData(w);
}

int eDVBServicePlay::getNumberOfSubservices()
{
	ePtr<eServiceEvent> evt;
	if (!m_event_handler.getEvent(evt, 0))
		return evt->getNumOfLinkageServices();
	return 0;
}

RESULT eDVBServicePlay::getSubservice(eServiceReference &sub, unsigned int n)
{
	ePtr<eServiceEvent> evt;
	if (!m_event_handler.getEvent(evt, 0))
	{
		if (!evt->getLinkageService(sub, m_reference, n))
			return 0;
	}
	sub.type=eServiceReference::idInvalid;
	return -1;
}

RESULT eDVBServicePlay::startTimeshift()
{
	ePtr<iDVBDemux> demux;
	
	eDebug("Start timeshift!");
	
	if (m_timeshift_enabled)
		return -1;
	
		/* start recording with the data demux. */
	if (m_service_handler.getDataDemux(demux))
		return -2;

	demux->createTSRecorder(m_record);
	if (!m_record)
		return -3;

	char templ[]="/media/hdd/timeshift.XXXXXX";
	m_timeshift_fd = mkstemp(templ);
	m_timeshift_file = templ;
	
	eDebug("recording to %s", templ);
	
	if (m_timeshift_fd < 0)
	{
		m_record = 0;
		return -4;
	}
		
	m_record->setTargetFD(m_timeshift_fd);

	m_timeshift_enabled = 1;
	
	updateTimeshiftPids();
	m_record->start();

	return 0;
}

RESULT eDVBServicePlay::stopTimeshift()
{
	if (!m_timeshift_enabled)
		return -1;
	
	switchToLive();
	
	m_timeshift_enabled = 0;
	
	m_record->stop();
	m_record = 0;
	
	close(m_timeshift_fd);
	remove(m_timeshift_file.c_str());
	
	return 0;
}

int eDVBServicePlay::isTimeshiftActive()
{
	return m_timeshift_enabled && m_timeshift_active;
}

RESULT eDVBServicePlay::activateTimeshift()
{
	if (!m_timeshift_enabled)
		return -1;
	
	if (!m_timeshift_active)
	{
		switchToTimeshift();
		return 0;
	}
	
	return -2;
}

void eDVBServicePlay::updateTimeshiftPids()
{
	if (!m_record)
		return;
	
	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
		return;
	else
	{
		std::set<int> pids_to_record;
		pids_to_record.insert(0); // PAT
		if (program.pmtPid != -1)
			pids_to_record.insert(program.pmtPid); // PMT

		if (program.textPid != -1)
			pids_to_record.insert(program.textPid); // Videotext

		for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
			i(program.videoStreams.begin()); 
			i != program.videoStreams.end(); ++i)
			pids_to_record.insert(i->pid);

		for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
			i(program.audioStreams.begin()); 
			i != program.audioStreams.end(); ++i)
				pids_to_record.insert(i->pid);

		std::set<int> new_pids, obsolete_pids;
		
		std::set_difference(pids_to_record.begin(), pids_to_record.end(), 
				m_pids_active.begin(), m_pids_active.end(),
				std::inserter(new_pids, new_pids.begin()));
		
		std::set_difference(
				m_pids_active.begin(), m_pids_active.end(),
				pids_to_record.begin(), pids_to_record.end(), 
				std::inserter(new_pids, new_pids.begin())
				);

		for (std::set<int>::iterator i(new_pids.begin()); i != new_pids.end(); ++i)
			m_record->addPID(*i);

		for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
			m_record->removePID(*i);
	}
}

void eDVBServicePlay::switchToLive()
{
	if (!m_timeshift_active)
		return;
	
	m_decoder = 0;
	m_decode_demux = 0;
		/* free the timeshift service handler, we need the resources */
	m_service_handler_timeshift.free();
	m_timeshift_active = 0;
	
	m_event((iPlayableService*)this, evSeekableStatusChanged);
	
	updateDecoder();
}

void eDVBServicePlay::switchToTimeshift()
{
	if (m_timeshift_active)
		return;
	
	m_decode_demux = 0;
	m_decoder = 0;
	
	m_timeshift_active = 1;

	m_event((iPlayableService*)this, evSeekableStatusChanged);
	
	eServiceReferenceDVB r = (eServiceReferenceDVB&)m_reference;
	r.path = m_timeshift_file;
	
	m_service_handler_timeshift.tune(r, 1); /* use the decoder demux for everything */
}

void eDVBServicePlay::updateDecoder()
{
	int vpid = -1, apid = -1, apidtype = -1, pcrpid = -1, tpid = -1;
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	eDVBServicePMTHandler::program program;
	if (h.getProgramInfo(program))
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
				{
					apid = i->pid;
					apidtype = i->type;
				}
				if (i != program.audioStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebugNoNewLine(", and the pcr pid is %04x", program.pcrPid);
		pcrpid = program.pcrPid;
		eDebug(", and the text pid is %04x", program.textPid);
		tpid = program.textPid;
	}

	if (!m_decoder)
	{
		h.getDecodeDemux(m_decode_demux);
		if (m_decode_demux)
			m_decode_demux->getMPEGDecoder(m_decoder);
	}

	if (m_decoder)
	{
		m_decoder->setVideoPID(vpid);
		m_current_audio_stream = 0;
		m_decoder->setAudioPID(apid, apidtype);
		if (!(m_is_pvr || m_timeshift_active))
			m_decoder->setSyncPCR(pcrpid);
		else
			m_decoder->setSyncPCR(-1);
		m_decoder->setTextPID(tpid);
		m_decoder->start();
// how we can do this better?
// update cache pid when the user changed the audio track or video track
// TODO handling of difference audio types.. default audio types..
				
		/* don't worry about non-existing services, nor pvr services */
		if (m_dvb_service && !m_is_pvr)
		{
			if (apidtype == eDVBAudio::aMPEG)
			{
				m_dvb_service->setCachePID(eDVBService::cAPID, apid);
				m_dvb_service->setCachePID(eDVBService::cAC3PID, -1);
			}
			else
			{
				m_dvb_service->setCachePID(eDVBService::cAPID, -1);
				m_dvb_service->setCachePID(eDVBService::cAC3PID, apid);
			}
			m_dvb_service->setCachePID(eDVBService::cVPID, vpid);
			m_dvb_service->setCachePID(eDVBService::cPCRPID, pcrpid);
			m_dvb_service->setCachePID(eDVBService::cTPID, tpid);
		}
	}
}

DEFINE_REF(eDVBServicePlay)

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
