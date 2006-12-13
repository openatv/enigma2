#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicedvb.h>
#include <lib/service/service.h>
#include <lib/base/estring.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/decoder.h>

#include <lib/components/file_eraser.h>
#include <lib/service/servicedvbrecord.h>
#include <lib/service/event.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb/tstools.h>
#include <lib/python/python.h>

		/* for subtitles */
#include <lib/gui/esubtitle.h>

#include <sys/vfs.h>
#include <sys/stat.h>

#include <byteswap.h>
#include <netinet/in.h>

#ifndef BYTE_ORDER
#error no byte order defined!
#endif

#define TSPATH "/media/hdd"

class eStaticServiceDVBInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBInformation);
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore);
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

int eStaticServiceDVBInformation::isPlayable(const eServiceReference &ref, const eServiceReference &ignore)
{
	ePtr<eDVBResourceManager> res_mgr;
	if ( eDVBResourceManager::getInstance( res_mgr ) )
		eDebug("isPlayble... no res manager!!");
	else
	{
		eDVBChannelID chid, chid_ignore;
		((const eServiceReferenceDVB&)ref).getChannelID(chid);
		((const eServiceReferenceDVB&)ignore).getChannelID(chid_ignore);
		return res_mgr->canAllocateChannel(chid, chid_ignore);
	}
	return false;
}

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

int eStaticServiceDVBBouquetInformation::isPlayable(const eServiceReference &ref, const eServiceReference &ignore)
{
	if (ref.flags & eServiceReference::isGroup)
	{
		ePtr<iDVBChannelList> db;
		ePtr<eDVBResourceManager> res;

		if (eDVBResourceManager::getInstance(res))
		{
			eDebug("eStaticServiceDVBBouquetInformation::isPlayable failed.. no resource manager!");
			return 0;
		}

		if (res->getChannelList(db))
		{
			eDebug("eStaticServiceDVBBouquetInformation::isPlayable failed.. no channel list!");
			return 0;
		}

		eBouquet *bouquet=0;
		if (db->getBouquet(ref, bouquet))
		{
			eDebug("eStaticServiceDVBBouquetInformation::isPlayable failed.. getBouquet failed!");
			return 0;
		}

		int cur=0;
		eDVBChannelID chid, chid_ignore;
		((const eServiceReferenceDVB&)ignore).getChannelID(chid_ignore);
		for (std::list<eServiceReference>::iterator it(bouquet->m_services.begin()); it != bouquet->m_services.end(); ++it)
		{
			((const eServiceReferenceDVB&)*it).getChannelID(chid);
			int tmp=res->canAllocateChannel(chid, chid_ignore);
			if (tmp > cur)
			{
				m_playable_service = *it;
				cur = tmp;
			}
		}
		if (cur)
			return cur;
	}
	m_playable_service = eServiceReference();
	return 0;
}

int eStaticServiceDVBBouquetInformation::getLength(const eServiceReference &ref)
{
	return -1;
}

#include <lib/dvb/epgcache.h>

RESULT eStaticServiceDVBBouquetInformation::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &ptr, time_t start_time)
{
	return eEPGCache::getInstance()->lookupEventTime(ref, start_time, ptr);
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
	RESULT getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &SWIG_OUTPUT, time_t start_time);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore) { return 1; }
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
	case iServiceInformation::sServiceref:
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
	case iServiceInformation::sServiceref:
		return m_parser.m_ref.toString();
	case iServiceInformation::sTags:
		return m_parser.m_tags;
	default:
		return "";
	}
}

RESULT eStaticServiceDVBPVRInformation::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &evt, time_t start_time)
{
	if (!ref.path.empty())
	{
		ePtr<eServiceEvent> event = new eServiceEvent;
		std::string filename = ref.path;
		filename.erase(filename.length()-2, 2);
		filename+="eit";
		if (!event->parseFrom(filename, (m_parser.m_ref.getTransportStreamID().get()<<16)|m_parser.m_ref.getOriginalNetworkID().get()))
		{
			evt = event;
			return 0;
		}
	}
	evt = 0;
	return -1;
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
		
		eBackgroundFileEraser *eraser = eBackgroundFileEraser::getInstance();
		if (!eraser)
			eDebug("FATAL !! can't get background file eraser");
		
		for (std::list<std::string>::iterator i(res.begin()); i != res.end(); ++i)
		{
			eDebug("Removing %s...", i->c_str());
			if (eraser)
				eraser->erase(i->c_str());
			else
				::unlink(i->c_str());
		}
		
		return 0;
	}
}

RESULT eDVBPVRServiceOfflineOperations::getListOfFilenames(std::list<std::string> &res)
{
	res.clear();
	res.push_back(m_ref.path);

// handling for old splitted recordings (enigma 1)
	char buf[255];
	int slice=1;
	while(true)
	{
		snprintf(buf, 255, "%s.%03d", m_ref.path.c_str(), slice++);
		struct stat s;
		if (stat(buf, &s) < 0)
			break;
		res.push_back(buf);
	}	

	res.push_back(m_ref.path + ".meta");
	res.push_back(m_ref.path + ".ap");
	res.push_back(m_ref.path + ".cuts");
	std::string tmp = m_ref.path;
	tmp.erase(m_ref.path.length()-3);
	res.push_back(tmp + ".eit");
	return 0;
}

DEFINE_REF(eServiceFactoryDVB)

eServiceFactoryDVB::eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryDVB::id, this);

	m_StaticServiceDVBInfo = new eStaticServiceDVBInformation;
	m_StaticServiceDVBBouquetInfo = new eStaticServiceDVBBouquetInformation;
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

//   The first argument of this function is a format string to specify the order and
//   the content of the returned list
//   useable format options are
//   R = Service Reference (as swig object .. this is very slow)
//   S = Service Reference (as python string object .. same as ref.toString())
//   C = Service Reference (as python string object .. same as ref.toCompareString())
//   N = Service Name (as python string object)
//   when exactly one return value per service is selected in the format string,
//   then each value is directly a list entry
//   when more than one value is returned per service, then the list is a list of
//   python tuples
//   unknown format string chars are returned as python None values !
PyObject *eDVBServiceList::getContent(const char* format, bool sorted)
{
	ePyObject ret;
	std::list<eServiceReference> tmplist;
	int retcount=1;

	if (!format || !(retcount=strlen(format)))
		format = "R"; // just return service reference swig object ...

	if (!getContent(tmplist, sorted))
	{
		int services=tmplist.size();
		ePtr<iStaticServiceInformation> sptr;
		eServiceCenterPtr service_center;

		if (strchr(format, 'N'))
			eServiceCenter::getPrivInstance(service_center);

		ret = PyList_New(services);
		std::list<eServiceReference>::iterator it(tmplist.begin());

		for (int cnt=0; cnt < services; ++cnt)
		{
			eServiceReference &ref=*it++;
			ePyObject tuple = retcount > 1 ? PyTuple_New(retcount) : ePyObject();
			for (int i=0; i < retcount; ++i)
			{
				ePyObject tmp;
				switch(format[i])
				{
				case 'R':  // service reference (swig)object
					tmp = NEW_eServiceReference(ref);
					break;
				case 'C':  // service reference compare string
					tmp = PyString_FromString(ref.toCompareString().c_str());
					break;
				case 'S':  // service reference string
					tmp = PyString_FromString(ref.toString().c_str());
					break;
				case 'N':  // service name
					if (service_center)
					{
						service_center->info(ref, sptr);
						if (sptr)
						{
							std::string name;
							sptr->getName(ref, name);
							if (name.length())
								tmp = PyString_FromString(name.c_str());
						}
					}
					if (!tmp)
						tmp = PyString_FromString("<n/a>");
					break;
				default:
					if (tuple)
					{
						tmp = Py_None;
						Py_INCREF(Py_None);
					}
					break;
				}
				if (tmp)
				{
					if (tuple)
						PyTuple_SET_ITEM(tuple, i, tmp);
					else
						PyList_SET_ITEM(ret, cnt, tmp);
				}
			}
			if (tuple)
				PyList_SET_ITEM(ret, cnt, tuple);
		}
	}
	return ret ? (PyObject*)ret : (PyObject*)PyList_New(0);
}

RESULT eDVBServiceList::getNext(eServiceReference &ref)
{
	if (!m_query)
		return -1;
	
	return m_query->getNextResult((eServiceReferenceDVB&)ref);
}

RESULT eDVBServiceList::startEdit(ePtr<iMutableServiceList> &res)
{
	if (m_parent.flags & eServiceReference::canDescent) // bouquet
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

RESULT eDVBServiceList::addService(eServiceReference &ref, eServiceReference before)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->addService(ref, before);
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
	if (ref.flags & eServiceReference::canDescent) // bouquet
	{
		if ( !ref.name.empty() )  // satellites or providers list
			ptr = m_StaticServiceDVBInfo;
		else // a dvb bouquet
			ptr = m_StaticServiceDVBBouquetInfo;
	}
	else if (!ref.path.empty()) /* do we have a PVR service? */
		ptr = new eStaticServiceDVBPVRInformation(ref);
	else // normal dvb service
	{
		ePtr<eDVBService> service;
		if (lookupService(service, ref)) // no eDVBService avail for this reference ( Linkage Services... )
			ptr = m_StaticServiceDVBInfo;
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
	m_reference(ref), m_dvb_service(service), m_have_video_pid(0), m_is_paused(0)
{
	memset(&m_videoEventData, 0, sizeof(struct iTSMPEGDecoder::videoEvent));
	m_is_primary = 1;
	m_is_pvr = !m_reference.path.empty();
	
	m_timeshift_enabled = m_timeshift_active = 0;
	m_skipmode = 0;
	
	CONNECT(m_service_handler.serviceEvent, eDVBServicePlay::serviceEvent);
	CONNECT(m_service_handler_timeshift.serviceEvent, eDVBServicePlay::serviceEventTimeshift);
	CONNECT(m_event_handler.m_eit_changed, eDVBServicePlay::gotNewEvent);

	m_cuesheet_changed = 0;
	m_cutlist_enabled = 1;
	
	m_subtitle_widget = 0;
	
	m_tune_state = -1;
	
	CONNECT(m_subtitle_sync_timer.timeout, eDVBServicePlay::checkSubtitleTiming);
}

eDVBServicePlay::~eDVBServicePlay()
{
	delete m_subtitle_widget;
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
	m_tune_state = event;

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
	case eDVBServicePMTHandler::eventNoPAT:
	case eDVBServicePMTHandler::eventNoPATEntry:
	case eDVBServicePMTHandler::eventNoPMT:
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("DVB service failed to tune - error %d", event);
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
		if (m_first_program_info && m_is_pvr)
		{
			m_first_program_info = 0;
			seekTo(0);
		}
		m_event((iPlayableService*)this, evUpdatedInfo);
		break;
	}
	case eDVBServicePMTHandler::eventEOF:
		m_event((iPlayableService*)this, evEOF);
		break;
	case eDVBServicePMTHandler::eventSOF:
		m_event((iPlayableService*)this, evSOF);
		break;
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
	case eDVBServicePMTHandler::eventSOF:
		m_event((iPlayableService*)this, evSOF);
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
	if (m_is_pvr)
		m_cue = new eCueSheet();

	m_first_program_info = 1;
	eServiceReferenceDVB &service = (eServiceReferenceDVB&)m_reference;
	r = m_service_handler.tune(service, m_is_pvr, m_cue);

		/* inject EIT if there is a stored one */
	if (m_is_pvr)
	{
		std::string filename = service.path;
		filename.erase(filename.length()-2, 2);
		filename+="eit";
		ePtr<eServiceEvent> event = new eServiceEvent;
		if (!event->parseFrom(filename, (service.getTransportStreamID().get()<<16)|service.getOriginalNetworkID().get()))
		{
			ePtr<eServiceEvent> empty;
			m_event_handler.inject(event, 0);
			m_event_handler.inject(empty, 1);
		}
	}

	if (m_is_pvr)
		loadCuesheet();

	m_event(this, evStart);
	m_event((iPlayableService*)this, evSeekableStatusChanged);
	return 0;
}

RESULT eDVBServicePlay::stop()
{
		/* add bookmark for last play position */
	if (m_is_pvr)
	{
		pts_t play_position;
		if (!getPlayPosition(play_position))
		{
				/* remove last position */
			for (std::multiset<struct cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end();)
			{
				if (i->what == 3) /* current play position */
				{
					m_cue_entries.erase(i);
					i = m_cue_entries.begin();
					continue;
				} else
					++i;
			}
			
			m_cue_entries.insert(cueEntry(play_position, 3)); /* last play position */
			m_cuesheet_changed = 1;
		}
	}

	stopTimeshift(); /* in case timeshift was enabled, remove buffer etc. */

	m_service_handler_timeshift.free();
	m_service_handler.free();
	
	if (m_is_pvr && m_cuesheet_changed)
	{
		struct stat s;
				/* save cuesheet only when main file is accessible. */
		if (!::stat(m_reference.path.c_str(), &s))
			saveCuesheet();
	}
	
	return 0;
}

RESULT eDVBServicePlay::setTarget(int target)
{
	m_is_primary = !target;
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
	int skipmode, ffratio;
	
	if (ratio > 8)
	{
		skipmode = ratio;
		ffratio = 1;
	} else if (ratio > 0)
	{
		skipmode = 0;
		ffratio = ratio;
	} else if (!ratio)
	{
		skipmode = 0;
		ffratio = 0;
	} else // if (ratio < 0)
	{
		skipmode = ratio;
		ffratio = 1;
	}

	if (m_skipmode != skipmode)
	{
		eDebug("setting cue skipmode to %d", skipmode);
		if (m_cue)
			m_cue->setSkipmode(skipmode * 90000); /* convert to 90000 per second */
	}
	
	m_skipmode = skipmode;
	
	if (!m_decoder)
		return -1;

	return m_decoder->setFastForward(ffratio);
}
    
RESULT eDVBServicePlay::seek(ePtr<iSeekableService> &ptr)
{
	if (m_is_pvr || m_timeshift_enabled)
	{
		ptr = this;
		return 0;
	}
	
	ptr = 0;
	return -1;
}

	/* TODO: when timeshift is enabled but not active, this doesn't work. */
RESULT eDVBServicePlay::getLength(pts_t &len)
{
	ePtr<iDVBPVRChannel> pvr_channel;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
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
	
	if (!m_cue)
		return -1;
	
	m_cue->seekTo(0, to);
	return 0;
}

RESULT eDVBServicePlay::seekRelative(int direction, pts_t to)
{
	eDebug("eDVBServicePlay::seekRelative: jump %d, %lld", direction, to);
	
	if (!m_decode_demux)
		return -1;

	ePtr<iDVBPVRChannel> pvr_channel;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
	int mode = 1;
	
			/* HACK until we have skip-AP api */
	if ((to > 0) && (to < 100))
		mode = 2;
	
	to *= direction;
	
	if (!m_cue)
		return 0;
	
	m_cue->seekTo(mode, to);
	return 0;
}

RESULT eDVBServicePlay::getPlayPosition(pts_t &pos)
{
	ePtr<iDVBPVRChannel> pvr_channel;
	
	if (!m_decode_demux)
		return -1;
	
	if ((m_timeshift_enabled ? m_service_handler_timeshift : m_service_handler).getPVRChannel(pvr_channel))
		return -1;
	
	int r = 0;

		/* if there is a decoder, use audio or video PTS */
	if (m_decoder)
	{
		r = m_decoder->getPTS(0, pos);
		if (r)
			return r;
	}
	
		/* fixup */
	return pvr_channel->getCurrentPosition(m_decode_demux, pos, m_decoder ? 1 : 0);
}

RESULT eDVBServicePlay::setTrickmode(int trick)
{
	if (m_decoder)
		m_decoder->setTrickmode(trick);
	return 0;
}

RESULT eDVBServicePlay::isCurrentlySeekable()
{
	return m_is_pvr || m_timeshift_active;
}

RESULT eDVBServicePlay::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::info(ePtr<iServiceInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::audioChannel(ePtr<iAudioChannelSelection> &ptr)
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
	ptr = 0;
	if (m_have_video_pid &&  // HACK !!! FIXMEE !! temporary no timeshift on radio services !!
		(m_timeshift_enabled || !m_is_pvr))
	{
		if (!m_timeshift_enabled)
		{
				/* we need enough diskspace */
			struct statfs fs;
			if (statfs(TSPATH "/.", &fs) < 0)
			{
				eDebug("statfs failed!");
				return -2;
			}
		
			if (((off_t)fs.f_bavail) * ((off_t)fs.f_bsize) < 1024*1024*1024LL)
			{
				eDebug("not enough diskspace for timeshift! (less than 1GB)");
				return -3;
			}
		}
		ptr = this;
		return 0;
	}
	return -1;
}

RESULT eDVBServicePlay::cueSheet(ePtr<iCueSheet> &ptr)
{
	if (m_is_pvr)
	{
		ptr = this;
		return 0;
	}
	ptr = 0;
	return -1;
}

RESULT eDVBServicePlay::subtitle(ePtr<iSubtitleOutput> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::audioDelay(ePtr<iAudioDelay> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::radioText(ePtr<iRadioText> &ptr)
{
	ptr = this;
	return 0;
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
	
	if (w == sCAIDs)
		return resIsPyObject;

	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
	
	int no_program_info = 0;
	
	if (h.getProgramInfo(program))
		no_program_info = 1;
	
	switch (w)
	{
#if HAVE_DVB_API_VERSION >= 3
	case sVideoHeight:
		if (m_videoEventData.type != iTSMPEGDecoder::videoEvent::eventUnknown)
			return m_videoEventData.height;
		return -1;
	case sVideoWidth:
		if (m_videoEventData.type != iTSMPEGDecoder::videoEvent::eventUnknown)
			return m_videoEventData.width;
		return -1;
#else
#warning "FIXMEE implement sVideoHeight, sVideoWidth for old DVB API"
#endif
	case sAspect:
#if HAVE_DVB_API_VERSION >= 3
		if (m_videoEventData.type != iTSMPEGDecoder::videoEvent::eventUnknown)
			return m_videoEventData.aspect == VIDEO_FORMAT_4_3 ? 1 : 3;
		else
#else
#warning "FIXMEE implement sAspect for old DVB API"
#endif
		if (no_program_info)
			return -1; 
		else if (!program.videoStreams.empty() && program.videoStreams[0].component_tag != -1)
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
	case sIsCrypted: if (no_program_info) return -1; return program.isCrypted();
	case sVideoPID: if (no_program_info) return -1; if (program.videoStreams.empty()) return -1; return program.videoStreams[0].pid;
	case sVideoType: if (no_program_info) return -1; if (program.videoStreams.empty()) return -1; return program.videoStreams[0].type;
	case sAudioPID: if (no_program_info) return -1; if (program.audioStreams.empty()) return -1; return program.audioStreams[0].pid;
	case sPCRPID: if (no_program_info) return -1; return program.pcrPid;
	case sPMTPID: if (no_program_info) return -1; return program.pmtPid;
	case sTXTPID: if (no_program_info) return -1; return program.textPid;
	case sSID: return ((const eServiceReferenceDVB&)m_reference).getServiceID().get();
	case sONID: return ((const eServiceReferenceDVB&)m_reference).getOriginalNetworkID().get();
	case sTSID: return ((const eServiceReferenceDVB&)m_reference).getTransportStreamID().get();
	case sNamespace: return ((const eServiceReferenceDVB&)m_reference).getDVBNamespace().get();
	case sProvider: if (!m_dvb_service) return -1; return -2;
	case sServiceref: return resIsString;
	case sDVBState: return m_tune_state;
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
	case sServiceref:
		return m_reference.toString();
	default:
		break;
	}
	return iServiceInformation::getInfoString(w);
}

PyObject *eDVBServicePlay::getInfoObject(int w)
{
	switch (w)
	{
	case sCAIDs:
		return m_service_handler.getCaIds();
	default:
		break;
	}
	return iServiceInformation::getInfoObject(w);
}

int eDVBServicePlay::getNumberOfTracks()
{
	eDVBServicePMTHandler::program program;
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
	if (h.getProgramInfo(program))
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
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	if (h.getProgramInfo(program))
		return -1;
	
	if (i >= program.audioStreams.size())
		return -2;
	
	if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atMPEG)
		info.m_description = "MPEG";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAC3)
		info.m_description = "AC3";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAAC)
		info.m_description = "AAC";
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
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	if (h.getProgramInfo(program))
		return -1;
	
	if ((unsigned int)i >= program.audioStreams.size())
		return -2;
	
	if (!m_decoder)
		return -3;
	
	if (m_decoder->setAudioPID(program.audioStreams[i].pid, program.audioStreams[i].type))
		return -4;

	if (m_radiotext_parser)
		m_radiotext_parser->start(program.audioStreams[i].pid);

	if (m_dvb_service && !m_is_pvr)
	{
		if (program.audioStreams[i].type == eDVBAudio::aMPEG)
		{
			m_dvb_service->setCacheEntry(eDVBService::cAPID, program.audioStreams[i].pid);
			m_dvb_service->setCacheEntry(eDVBService::cAC3PID, -1);
		}
		else
		{
			m_dvb_service->setCacheEntry(eDVBService::cAPID, -1);
			m_dvb_service->setCacheEntry(eDVBService::cAC3PID, program.audioStreams[i].pid);
		}
	}

	h.resetCachedProgram();

	return 0;
}

int eDVBServicePlay::getCurrentChannel()
{
	return m_decoder ? m_decoder->getAudioChannel() : STEREO;
}

RESULT eDVBServicePlay::selectChannel(int i)
{
	if (i < LEFT || i > RIGHT || i == STEREO)
		i = -1;  // Stereo
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cACHANNEL, i);
	if (m_decoder)
		m_decoder->setAudioChannel(i);
	return 0;
}

std::string eDVBServicePlay::getRadioText(int x)
{
	if (m_radiotext_parser)
		switch(x)
		{
			case 0:
				return convertLatin1UTF8(m_radiotext_parser->getCurrentText());
		}
	return "";
}

void eDVBServicePlay::radioTextUpdated()
{
	m_event((iPlayableService*)this, evUpdatedRadioText);
}

int eDVBServiceBase::getFrontendInfo(int w)
{
	eUsePtr<iDVBChannel> channel;
	if(m_service_handler.getChannel(channel))
		return 0;
	ePtr<iDVBFrontend> fe;
	if(channel->getFrontend(fe))
		return 0;
	return fe->readFrontendData(w);
}

PyObject *eDVBServiceBase::getFrontendData(bool original)
{
	ePyObject ret;

	eUsePtr<iDVBChannel> channel;
	if(!m_service_handler.getChannel(channel))
	{
		ePtr<iDVBFrontend> fe;
		if(!channel->getFrontend(fe))
		{
			ret = fe->readTransponderData(original);
			if (ret)
			{
				ePtr<iDVBFrontendParameters> feparm;
				channel->getCurrentFrontendParameters(feparm);
				if (feparm)
				{
					eDVBFrontendParametersSatellite osat;
					if (!feparm->getDVBS(osat))
					{
						void PutToDict(ePyObject &, const char*, long);
						void PutToDict(ePyObject &, const char*, const char*);
						PutToDict(ret, "orbital_position", osat.orbital_position);
						const char *tmp = "UNKNOWN";
						switch(osat.polarisation)
						{
							case eDVBFrontendParametersSatellite::Polarisation::Horizontal: tmp="HORIZONTAL"; break;
							case eDVBFrontendParametersSatellite::Polarisation::Vertical: tmp="VERTICAL"; break;
							case eDVBFrontendParametersSatellite::Polarisation::CircularLeft: tmp="CIRCULAR_LEFT"; break;
							case eDVBFrontendParametersSatellite::Polarisation::CircularRight: tmp="CIRCULAR_RIGHT"; break;
							default:break;
						}
						PutToDict(ret, "polarization", tmp);
					}
				}
			}
		}
	}
	if (!ret)
	{
		ret = Py_None;
		Py_INCREF(ret);
	}
	return ret;
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

	char templ[]=TSPATH "/timeshift.XXXXXX";
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
	eDebug("remove timeshift file");
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

PyObject *eDVBServicePlay::getCutList()
{
	ePyObject list = PyList_New(0);
	
	for (std::multiset<struct cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SetItem(tuple, 0, PyLong_FromLongLong(i->where));
		PyTuple_SetItem(tuple, 1, PyInt_FromLong(i->what));
		PyList_Append(list, tuple);
		Py_DECREF(tuple);
	}
	
	return list;
}

void eDVBServicePlay::setCutList(ePyObject list)
{
	if (!PyList_Check(list))
		return;
	int size = PyList_Size(list);
	int i;
	
	m_cue_entries.clear();
	
	for (i=0; i<size; ++i)
	{
		ePyObject tuple = PyList_GET_ITEM(list, i);
		if (!PyTuple_Check(tuple))
		{
			eDebug("non-tuple in cutlist");
			continue;
		}
		if (PyTuple_Size(tuple) != 2)
		{
			eDebug("cutlist entries need to be a 2-tuple");
			continue;
		}
		ePyObject ppts = PyTuple_GET_ITEM(tuple, 0), ptype = PyTuple_GET_ITEM(tuple, 1);
		if (!(PyLong_Check(ppts) && PyInt_Check(ptype)))
		{
			eDebug("cutlist entries need to be (pts, type)-tuples (%d %d)", PyLong_Check(ppts), PyInt_Check(ptype));
			continue;
		}
		pts_t pts = PyLong_AsLongLong(ppts);
		int type = PyInt_AsLong(ptype);
		m_cue_entries.insert(cueEntry(pts, type));
		eDebug("adding %08llx, %d", pts, type);
	}
	m_cuesheet_changed = 1;
	
	cutlistToCuesheet();
	m_event((iPlayableService*)this, evCuesheetChanged);
}

void eDVBServicePlay::setCutListEnable(int enable)
{
	m_cutlist_enabled = enable;
	cutlistToCuesheet();
}

void eDVBServicePlay::updateTimeshiftPids()
{
	if (!m_record)
		return;
	
	eDVBServicePMTHandler::program program;
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	if (h.getProgramInfo(program))
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
	
	m_cue = 0;
	m_decoder = 0;
	m_decode_demux = 0;
	m_teletext_parser = 0;
	m_radiotext_parser = 0;
	m_subtitle_parser = 0;
	m_new_dvb_subtitle_page_connection = 0;
	m_new_subtitle_page_connection = 0;
	m_radiotext_updated_connection = 0;

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
	m_teletext_parser = 0;
	m_radiotext_parser = 0;
	m_subtitle_parser = 0;
	m_new_subtitle_page_connection = 0;
	m_new_dvb_subtitle_page_connection = 0;
	m_radiotext_updated_connection = 0;

	m_timeshift_active = 1;

	m_event((iPlayableService*)this, evSeekableStatusChanged);

	eServiceReferenceDVB r = (eServiceReferenceDVB&)m_reference;
	r.path = m_timeshift_file;

	m_cue = new eCueSheet();
	m_service_handler_timeshift.tune(r, 1, m_cue); /* use the decoder demux for everything */
	updateDecoder(); /* mainly to switch off PCR */
}

void eDVBServicePlay::updateDecoder()
{
	int vpid = -1, vpidtype = -1, apid = -1, apidtype = -1, pcrpid = -1, tpid = -1, achannel = -1, ac3_delay=-1, pcm_delay=-1;

	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	bool defaultac3=false;
	std::string default_ac3;

	if (!ePythonConfigQuery::getConfigValue("config.av.defaultac3", default_ac3))
		defaultac3 = default_ac3 == "True";

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
				{
					vpid = i->pid;
					vpidtype = i->type;
				}
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
				if (apid == -1 || (apidtype == eDVBAudio::aMPEG && defaultac3))
				{
					if ( apid == -1 || (i->type != eDVBAudio::aMPEG) )
					{
						apid = i->pid;
						apidtype = i->type;
					}
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
		{
			m_decode_demux->getMPEGDecoder(m_decoder, m_is_primary);
			if (m_decoder)
				m_decoder->connectVideoEvent(slot(*this, &eDVBServicePlay::video_event), m_video_event_connection);
		}
		if (m_cue)
			m_cue->setDecodingDemux(m_decode_demux, m_decoder);
		m_teletext_parser = new eDVBTeletextParser(m_decode_demux);
		m_teletext_parser->connectNewPage(slot(*this, &eDVBServicePlay::newSubtitlePage), m_new_subtitle_page_connection);
		m_subtitle_parser = new eDVBSubtitleParser(m_decode_demux);
		m_subtitle_parser->connectNewPage(slot(*this, &eDVBServicePlay::newDVBSubtitlePage), m_new_dvb_subtitle_page_connection);
	}

	if (m_decoder)
	{
		if (m_dvb_service)
		{
			achannel = m_dvb_service->getCacheEntry(eDVBService::cACHANNEL);
			ac3_delay = m_dvb_service->getCacheEntry(eDVBService::cAC3DELAY);
			pcm_delay = m_dvb_service->getCacheEntry(eDVBService::cPCMDELAY);
		}
		else // subservice or recording
		{
			eServiceReferenceDVB ref;
			m_service_handler.getServiceReference(ref);
			eServiceReferenceDVB parent = ref.getParentServiceReference();
			if (!parent)
				parent = ref;
			if (parent)
			{
				ePtr<eDVBResourceManager> res_mgr;
				if (!eDVBResourceManager::getInstance(res_mgr))
				{
					ePtr<iDVBChannelList> db;
					if (!res_mgr->getChannelList(db))
					{
						ePtr<eDVBService> origService;
						if (!db->getService(parent, origService))
						{
		 					ac3_delay = origService->getCacheEntry(eDVBService::cAC3DELAY);
							pcm_delay = origService->getCacheEntry(eDVBService::cPCMDELAY);
						}
					}
				}
			}
		}
		m_decoder->setAC3Delay(ac3_delay == -1 ? 0 : ac3_delay);
		m_decoder->setPCMDelay(pcm_delay == -1 ? 0 : pcm_delay);

		m_decoder->setVideoPID(vpid, vpidtype);
		m_decoder->setAudioPID(apid, apidtype);
		if (!(m_is_pvr || m_timeshift_active || !m_is_primary))
		{
			m_decoder->setSyncPCR(pcrpid);
			if (apid != -1)
			{
				ePtr<iDVBDemux> data_demux;
				if (!h.getDataDemux(data_demux))
				{
					m_radiotext_parser = new eDVBRadioTextParser(data_demux);
					m_radiotext_parser->connectUpdatedRadiotext(slot(*this, &eDVBServicePlay::radioTextUpdated), m_radiotext_updated_connection);
					m_radiotext_parser->start(apid);
				}
			}
		}
		else
			m_decoder->setSyncPCR(-1);

		m_decoder->setTextPID(tpid);

		m_teletext_parser->start(program.textPid);

		if (!m_is_primary)
			m_decoder->setTrickmode(1);

		m_decoder->start();

		if (vpid > 0 && vpid < 0x2000)
			;
		else
		{
			std::string radio_pic;
			if (!ePythonConfigQuery::getConfigValue("config.misc.radiopic", radio_pic))
				m_decoder->setRadioPic(radio_pic);
		}

		m_decoder->setAudioChannel(achannel);

// how we can do this better?
// update cache pid when the user changed the audio track or video track
// TODO handling of difference audio types.. default audio types..
				
		/* don't worry about non-existing services, nor pvr services */
		if (m_dvb_service && !m_is_pvr)
		{
			if (apidtype == eDVBAudio::aMPEG)
			{
				m_dvb_service->setCacheEntry(eDVBService::cAPID, apid);
				m_dvb_service->setCacheEntry(eDVBService::cAC3PID, -1);
			}
			else
			{
				m_dvb_service->setCacheEntry(eDVBService::cAPID, -1);
				m_dvb_service->setCacheEntry(eDVBService::cAC3PID, apid);
			}
			m_dvb_service->setCacheEntry(eDVBService::cVPID, vpid);
			m_dvb_service->setCacheEntry(eDVBService::cVTYPE, vpidtype == eDVBVideo::MPEG2 ? -1 : vpidtype);
			m_dvb_service->setCacheEntry(eDVBService::cPCRPID, pcrpid);
			m_dvb_service->setCacheEntry(eDVBService::cTPID, tpid);
		}
	}
	m_have_video_pid = (vpid > 0 && vpid < 0x2000);
}

void eDVBServicePlay::loadCuesheet()
{
	std::string filename = m_reference.path + ".cuts";
	
	m_cue_entries.clear();

	FILE *f = fopen(filename.c_str(), "rb");

	if (f)
	{
		eDebug("loading cuts..");
		while (1)
		{
			unsigned long long where;
			unsigned int what;
			
			if (!fread(&where, sizeof(where), 1, f))
				break;
			if (!fread(&what, sizeof(what), 1, f))
				break;
			
#if BYTE_ORDER == LITTLE_ENDIAN
			where = bswap_64(where);
#endif
			what = ntohl(what);
			
			if (what > 3)
				break;
			
			m_cue_entries.insert(cueEntry(where, what));
		}
		fclose(f);
		eDebug("%d entries", m_cue_entries.size());
	} else
		eDebug("cutfile not found!");
	
	m_cuesheet_changed = 0;
	cutlistToCuesheet();
	m_event((iPlayableService*)this, evCuesheetChanged);
}

void eDVBServicePlay::saveCuesheet()
{
	std::string filename = m_reference.path + ".cuts";
	
	FILE *f = fopen(filename.c_str(), "wb");

	if (f)
	{
		unsigned long long where;
		int what;

		for (std::multiset<cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i)
		{
#if BYTE_ORDER == BIG_ENDIAN
			where = i->where;
#else
			where = bswap_64(i->where);
#endif
			what = htonl(i->what);
			fwrite(&where, sizeof(where), 1, f);
			fwrite(&what, sizeof(what), 1, f);
			
		}
		fclose(f);
	}
	
	m_cuesheet_changed = 0;
}

void eDVBServicePlay::cutlistToCuesheet()
{
	if (!m_cue)
	{
		eDebug("no cue sheet");
		return;
	}	
	m_cue->clear();
	
	if (!m_cutlist_enabled)
	{
		m_cue->commitSpans();
		eDebug("cutlists were disabled");
		return;
	}

	pts_t in = 0, out = 0, length = 0;
	
	getLength(length);
		
	std::multiset<cueEntry>::iterator i(m_cue_entries.begin());
	
	while (1)
	{
		if (i == m_cue_entries.end())
			out = length;
		else {
			if (i->what == 0) /* in */
			{
				in = i++->where;
				continue;
			} else if (i->what == 1) /* out */
				out = i++->where;
			else /* mark (2) or last play position (3) */
			{
				i++;
				continue;
			}
		}
		
		if (in != out)
			m_cue->addSourceSpan(in, out);
		
		in = length;
		
		if (i == m_cue_entries.end())
			break;
	}
	m_cue->commitSpans();
}

RESULT eDVBServicePlay::enableSubtitles(eWidget *parent, ePyObject tuple)
{
	if (m_subtitle_widget)
		disableSubtitles(parent);

	ePyObject entry;
	int tuplesize = PyTuple_Size(tuple);
	int type = 0;

	if (!PyTuple_Check(tuple))
		goto error_out;

	if (tuplesize < 1)
		goto error_out;

	entry = PyTuple_GET_ITEM(tuple, 0);

	if (!PyInt_Check(entry))
		goto error_out;

	type = PyInt_AsLong(entry);

	if (type == 1)  // teletext subtitles
	{
		int page, magazine, pid;
		if (tuplesize < 4)
			goto error_out;

		if (!m_teletext_parser)
		{
			eDebug("enable teletext subtitles.. no parser !!!");
			return -1;
		}

		entry = PyTuple_GET_ITEM(tuple, 1);
		if (!PyInt_Check(entry))
			goto error_out;
		pid = PyInt_AsLong(entry);

		entry = PyTuple_GET_ITEM(tuple, 2);
		if (!PyInt_Check(entry))
			goto error_out;
		page = PyInt_AsLong(entry);

		entry = PyTuple_GET_ITEM(tuple, 3);
		if (!PyInt_Check(entry))
			goto error_out;
		magazine = PyInt_AsLong(entry);

		m_subtitle_widget = new eSubtitleWidget(parent);
		m_subtitle_widget->resize(parent->size()); /* full size */
		m_teletext_parser->setPageAndMagazine(page, magazine);
		if (m_dvb_service)
			m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE,((pid&0xFFFF)<<16)|((page&0xFF)<<8)|(magazine&0xFF));
	}
	else if (type == 0)
	{
		int pid = 0, composition_page_id = 0, ancillary_page_id = 0;
		if (!m_subtitle_parser)
		{
			eDebug("enable dvb subtitles.. no parser !!!");
			return -1;
		}
		if (tuplesize < 4)
			goto error_out;

		entry = PyTuple_GET_ITEM(tuple, 1);
		if (!PyInt_Check(entry))
			goto error_out;
		pid = PyInt_AsLong(entry);

		entry = PyTuple_GET_ITEM(tuple, 2);
		if (!PyInt_Check(entry))
			goto error_out;
		composition_page_id = PyInt_AsLong(entry);

		entry = PyTuple_GET_ITEM(tuple, 3);
		if (!PyInt_Check(entry))
			goto error_out;
		ancillary_page_id = PyInt_AsLong(entry);

		m_subtitle_widget = new eSubtitleWidget(parent);
		m_subtitle_widget->resize(parent->size()); /* full size */
		m_subtitle_parser->start(pid, composition_page_id, ancillary_page_id);
		if (m_dvb_service)
			m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE, ((pid&0xFFFF)<<16)|((composition_page_id&0xFF)<<8)|(ancillary_page_id&0xFF));
	}
	else
		goto error_out;
	return 0;
error_out:
	eDebug("enableSubtitles needs a tuple as 2nd argument!\n"
		"for teletext subtitles (0, pid, teletext_page, teletext_magazine)\n"
		"for dvb subtitles (1, pid, composition_page_id, ancillary_page_id)");
	return -1;
}

RESULT eDVBServicePlay::disableSubtitles(eWidget *parent)
{
	delete m_subtitle_widget;
	m_subtitle_widget = 0;
	if (m_subtitle_parser)
	{
		m_subtitle_parser->stop();
		m_dvb_subtitle_pages.clear();
	}
	if (m_teletext_parser)
	{
		m_teletext_parser->setPageAndMagazine(-1, -1);
		m_subtitle_pages.clear();
	}
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE, -1);
	return 0;
}

PyObject *eDVBServicePlay::getCachedSubtitle()
{
	if (m_dvb_service)
	{
		int tmp = m_dvb_service->getCacheEntry(eDVBService::cSUBTITLE);
		if (tmp != -1)
		{
			unsigned int data = (unsigned int)tmp;
			int pid = (data&0xFFFF0000)>>16;
			ePyObject tuple = PyTuple_New(4);
			eDVBServicePMTHandler::program program;
			eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
			if (!h.getProgramInfo(program))
			{
				if (program.textPid==pid) // teletext
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(1)); // type teletext
				else
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(0)); // type dvb
				PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong((data&0xFFFF0000)>>16)); // pid
				PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong((data&0xFF00)>>8)); // composition_page / page
				PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(data&0xFF)); // ancillary_page / magazine
				return tuple;
			}
		}
	}
	Py_INCREF(Py_None);
	return Py_None;
}

PyObject *eDVBServicePlay::getSubtitleList()
{
	if (!m_teletext_parser)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	
	ePyObject l = PyList_New(0);
	std::set<int> added_ttx_pages;

	std::set<eDVBServicePMTHandler::subtitleStream> &subs =
		m_teletext_parser->m_found_subtitle_pages;

	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
	eDVBServicePMTHandler::program program;
	if (h.getProgramInfo(program))
		eDebug("getting program info failed.");
	else
	{
		for (std::vector<eDVBServicePMTHandler::subtitleStream>::iterator it(program.subtitleStreams.begin());
			it != program.subtitleStreams.end(); ++it)
		{
			switch(it->subtitling_type)
			{
				case 0x01: // ebu teletext subtitles
				{
					int page_number = it->teletext_page_number & 0xFF;
					int magazine_number = it->teletext_magazine_number & 7;
					int hash = magazine_number << 8 | page_number;
					if (added_ttx_pages.find(hash) == added_ttx_pages.end())
					{
						ePyObject tuple = PyTuple_New(5);
						PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(1));
						PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(it->pid));
						PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(page_number));
						PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(magazine_number));
						PyTuple_SET_ITEM(tuple, 4, PyString_FromString(it->language_code.c_str()));
						PyList_Append(l, tuple);
						Py_DECREF(tuple);
						added_ttx_pages.insert(hash);
					}
					break;
				}
				case 0x10 ... 0x13:
				case 0x20 ... 0x23: // dvb subtitles
				{
					ePyObject tuple = PyTuple_New(5);
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(0));
					PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(it->pid));
					PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(it->composition_page_id));
					PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(it->ancillary_page_id));
					PyTuple_SET_ITEM(tuple, 4, PyString_FromString(it->language_code.c_str()));
					PyList_Insert(l, 0, tuple);
					Py_DECREF(tuple);
					break;
				}
			}
		}
	}

	for (std::set<eDVBServicePMTHandler::subtitleStream>::iterator it(subs.begin());
		it != subs.end(); ++it)
	{
		int page_number = it->teletext_page_number & 0xFF;
		int magazine_number = it->teletext_magazine_number & 7;
		int hash = magazine_number << 8 | page_number;
		if (added_ttx_pages.find(hash) == added_ttx_pages.end())
		{
			ePyObject tuple = PyTuple_New(5);
			PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(1));
			PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(it->pid));
			PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(page_number));
			PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(magazine_number));
			PyTuple_SET_ITEM(tuple, 4, PyString_FromString("und"));  // undetermined
			PyList_Append(l, tuple);
			Py_DECREF(tuple);
		}
	}

	return l;
}

void eDVBServicePlay::newSubtitlePage(const eDVBTeletextSubtitlePage &page)
{
	if (m_subtitle_widget)
	{
		m_subtitle_pages.push_back(page);
		checkSubtitleTiming();
	}
}

void eDVBServicePlay::checkSubtitleTiming()
{
//	eDebug("checkSubtitleTiming");
	if (!m_subtitle_widget)
		return;
	while (1)
	{
		enum { TELETEXT, DVB } type;
		eDVBTeletextSubtitlePage page;
		eDVBSubtitlePage dvb_page;
		pts_t show_time;
		if (!m_subtitle_pages.empty())
		{
			page = m_subtitle_pages.front();
			type = TELETEXT;
			show_time = page.m_pts;
		}
		else if (!m_dvb_subtitle_pages.empty())
		{
			dvb_page = m_dvb_subtitle_pages.front();
			type = DVB;
			show_time = dvb_page.m_show_time;
		}
		else
			return;
	
		pts_t pos = 0;
	
		if (m_decoder)
			m_decoder->getPTS(0, pos);

//		eDebug("%lld %lld", pos, show_time);
		int diff =  show_time - pos;
		if (diff < 0)
		{
			eDebug("[late (%d ms)]", -diff / 90);
			diff = 0;
		}
		if (diff > 900000)
		{
			eDebug("[invalid]");
			diff = 0;
		}
	
		if (!diff)
		{
			if (type == TELETEXT)
			{
				eDebug("display teletext subtitle page");
				m_subtitle_widget->setPage(page);
				m_subtitle_pages.pop_front();
			}
			else
			{
				eDebug("display dvb subtitle Page");
				m_subtitle_widget->setPage(dvb_page);
				m_dvb_subtitle_pages.pop_front();
			}
		} else
		{
//			eDebug("start subtitle delay %d", diff / 90);
			m_subtitle_sync_timer.start(diff / 90, 1);
			break;
		}
	}
}

void eDVBServicePlay::newDVBSubtitlePage(const eDVBSubtitlePage &p)
{
	if (m_subtitle_widget)
	{
		m_dvb_subtitle_pages.push_back(p);
		checkSubtitleTiming();
	}
}

int eDVBServicePlay::getAC3Delay()
{
	if (m_dvb_service)
		return m_dvb_service->getCacheEntry(eDVBService::cAC3DELAY);
	else if (m_decoder)
		return m_decoder->getAC3Delay();
	else
		return 0;
}

int eDVBServicePlay::getPCMDelay()
{
	if (m_dvb_service)
		return m_dvb_service->getCacheEntry(eDVBService::cPCMDELAY);
	else if (m_decoder)
		return m_decoder->getPCMDelay();
	else
		return 0;
}

void eDVBServicePlay::setAC3Delay(int delay)
{
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cAC3DELAY, delay ? delay : -1);
	if (m_decoder)
		m_decoder->setAC3Delay(delay);
}

void eDVBServicePlay::setPCMDelay(int delay)
{
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cPCMDELAY, delay ? delay : -1);
	if (m_decoder)
		m_decoder->setPCMDelay(delay);
}

void eDVBServicePlay::video_event(struct iTSMPEGDecoder::videoEvent event)
{
	eDebug("!!!!!!!!!! Video Event type %d, aspect %d, %dx%d", event.type, event.aspect, event.width, event.height);
	memcpy(&m_videoEventData, &event, sizeof(iTSMPEGDecoder::videoEvent));
	m_event((iPlayableService*)this, evVideoSizeChanged);
}

DEFINE_REF(eDVBServicePlay)

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
