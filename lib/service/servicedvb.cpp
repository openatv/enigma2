#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicedvb.h>
#include <lib/service/service.h>
#include <lib/base/estring.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/decoder.h>

#include <lib/components/file_eraser.h>
#include <lib/service/servicedvbrecord.h>
#include <lib/service/event.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb/tstools.h>
#include <lib/python/python.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/base/httpstream.h>

		/* for subtitles */
#include <lib/gui/esubtitle.h>

#include <sys/vfs.h>
#include <sys/stat.h>

#include <byteswap.h>
#include <netinet/in.h>

#include <iostream>
#include <fstream>
using namespace std;

#ifndef BYTE_ORDER
#error no byte order defined!
#endif

#include <ios>
#include <sstream>
#include <iomanip>

class eStaticServiceDVBInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBInformation);
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate=false);
	ePtr<iDVBTransponderData> getTransponderData(const eServiceReference &ref);
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
						name=buildShortName(name) + " - ";
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

int eStaticServiceDVBInformation::isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate)
{
	ePtr<eDVBResourceManager> res_mgr;
	if ( eDVBResourceManager::getInstance( res_mgr ) )
		eDebug("isPlayable... no res manager!!");
	else
	{
		eDVBChannelID chid, chid_ignore;
		int system;
		((const eServiceReferenceDVB&)ref).getChannelID(chid);
		((const eServiceReferenceDVB&)ignore).getChannelID(chid_ignore);
		return res_mgr->canAllocateChannel(chid, chid_ignore, system);
	}
	return 0;
}

ePtr<iDVBTransponderData> eStaticServiceDVBInformation::getTransponderData(const eServiceReference &r)
{
	ePtr<iDVBTransponderData> retval;
	if (r.type == eServiceReference::idDVB)
	{
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)r;
		ePtr<eDVBResourceManager> res;
		if (!eDVBResourceManager::getInstance(res))
		{
			ePtr<iDVBChannelList> db;
			if (!res->getChannelList(db))
			{
				eDVBChannelID chid;
				ref.getChannelID(chid);
				ePtr<iDVBFrontendParameters> feparm;
				if (!db->getChannelFrontendData(chid, feparm))
				{
					int system;
					if (!feparm->getSystem(system))
					{
						switch (system)
						{
							case iDVBFrontend::feSatellite:
							{
								eDVBFrontendParametersSatellite s;
								feparm->getDVBS(s);
								retval = new eDVBSatelliteTransponderData(NULL, 0, s, 0, 0, true);
								break;
							}
							case iDVBFrontend::feTerrestrial:
							{
								eDVBFrontendParametersTerrestrial t;
								feparm->getDVBT(t);
								retval = new eDVBTerrestrialTransponderData(NULL, 0, t, true);
								break;
							}
							case iDVBFrontend::feCable:
							{
								eDVBFrontendParametersCable c;
								feparm->getDVBC(c);
								retval = new eDVBCableTransponderData(NULL, 0, c, true);
								break;
							}
							case iDVBFrontend::feATSC:
							{
								eDVBFrontendParametersATSC a;
								feparm->getATSC(a);
								retval = new eDVBATSCTransponderData(NULL, 0, a, true);
								break;
							}
							default:
								eDebug("unknown frontend type %d", system);
								break;
						}
					}
				}
			}
		}
	}
	return retval;
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

int eStaticServiceDVBBouquetInformation::isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate)
{
	if (ref.flags & eServiceReference::isGroup)
	{
		ePtr<iDVBChannelList> db;
		ePtr<eDVBResourceManager> res;
		eServiceReference streamable_service;

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

		int prio_order = eDVBFrontend::getTypePriorityOrder();
		int cur=0;
		eDVBChannelID chid, chid_ignore;
		((const eServiceReferenceDVB&)ignore).getChannelID(chid_ignore);
		for (std::list<eServiceReference>::iterator it(bouquet->m_services.begin()); it != bouquet->m_services.end(); ++it)
		{
			static unsigned char prio_map[6][3] = {
				{ 3, 2, 1 }, // -S -C -T
				{ 3, 1, 2 }, // -S -T -C
				{ 2, 3, 1 }, // -C -S -T
				{ 1, 3, 2 }, // -C -T -S
				{ 1, 2, 3 }, // -T -C -S
				{ 2, 1, 3 }  // -T -S -C
			};
			int system;
			((const eServiceReferenceDVB&)*it).getChannelID(chid);
			int tmp = res->canAllocateChannel(chid, chid_ignore, system, simulate);
			if (prio_order == 127) // ignore dvb-type priority, try all alternatives one-by-one
			{
				if (((tmp > 0) || (!it->path.empty())))
				{
					m_playable_service = *it;
					return 1;
				}
			}
			else
			{
				if (tmp > 0)
				{
					switch (system)
					{
						case iDVBFrontend::feTerrestrial:
							tmp = prio_map[prio_order][2];
							break;
						case iDVBFrontend::feCable:
							tmp = prio_map[prio_order][1];
							break;
						default:
						case iDVBFrontend::feSatellite:
							tmp = prio_map[prio_order][0];
							break;
					}
				}
				if (tmp > cur)
				{
					m_playable_service = *it;
					cur = tmp;
				}
				if (!it->path.empty())
				{
					streamable_service = *it;
				}
			}
		}
		if (cur)
		{
			return !!cur;
		}
		/* fallback to stream (or pvr) service alternative */
		if (streamable_service)
		{
			m_playable_service = streamable_service;
			return 1;
		}
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
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) { return 1; }
	int getInfo(const eServiceReference &ref, int w);
	std::string getInfoString(const eServiceReference &ref,int w);
	ePtr<iDVBTransponderData> getTransponderData(const eServiceReference &r);
	long long getFileSize(const eServiceReference &r);
};

DEFINE_REF(eStaticServiceDVBPVRInformation);

eStaticServiceDVBPVRInformation::eStaticServiceDVBPVRInformation(const eServiceReference &ref)
{
	m_ref = ref;
	m_parser.parseFile(ref.path);
}

static bool looksLikeRecording(const std::string& n)
{
	return
		(n.size() > 19) &&
		(n[8] == ' ') &&
		(n[13] == ' ') &&
		(n[14] == '-') &&
		(n[15] == ' ') &&
		(isdigit(n[0]));
}

RESULT eStaticServiceDVBPVRInformation::getName(const eServiceReference &ref, std::string &name)
{
	ASSERT(ref == m_ref);
	if (!ref.name.empty())
		name = ref.name;
	else if (!m_parser.m_name.empty())
		name = m_parser.m_name;
	else
	{
		name = ref.path;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
		if (looksLikeRecording(name))
		{
			// Parse recording names in 'YYYYMMDD HHMM - ... - name.ts' into name
			std::size_t dash2 = name.find(" - ", 16, 3);
			if (dash2 != std::string::npos)
			{
				struct tm stm = {0};
				if (strptime(name.c_str(), "%Y%m%d %H%M", &stm) != NULL)
				{
					m_parser.m_time_create = mktime(&stm);
				}
				name.erase(0,dash2+3);
			}
			if (name[name.size()-3] == '.')
			{
				name.erase(name.size()-3);
			}
		}
		m_parser.m_name = name;
	}
	return 0;
}

int eStaticServiceDVBPVRInformation::getLength(const eServiceReference &ref)
{
	ASSERT(ref == m_ref);

	eDVBTSTools tstools;

	if (tstools.openFile(ref.path.c_str(), 1))
		return 0;

	struct stat s;
	stat(ref.path.c_str(), &s);

			/* check if cached data is still valid */
	if (m_parser.m_data_ok && (s.st_size == m_parser.m_filesize) && (m_parser.m_length))
		return (int)(m_parser.m_length / 90000);

			/* open again, this time with stream info */
	if (tstools.openFile(ref.path.c_str()))
		return 0;

			/* otherwise, re-calc length and update meta file */
	pts_t len;
	if (tstools.calcLen(len))
		return 0;

	if (m_parser.m_name.empty())
	{
		std::string name;
		getName(ref, name); // This also updates m_parser.name
	}
	m_parser.m_data_ok = 1;
 	m_parser.m_length = len;
	m_parser.m_filesize = s.st_size;
	m_parser.updateMeta(ref.path);
	return (int)(m_parser.m_length / 90000);
}

int eStaticServiceDVBPVRInformation::getInfo(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sDescription:
		return iServiceInformation::resIsString;
	case iServiceInformation::sServiceref:
		return iServiceInformation::resIsString;
	case iServiceInformation::sFileSize:
		return m_parser.m_filesize;
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

ePtr<iDVBTransponderData> eStaticServiceDVBPVRInformation::getTransponderData(const eServiceReference &r)
{
	ePtr<iDVBTransponderData> retval;
	return retval;
}

long long eStaticServiceDVBPVRInformation::getFileSize(const eServiceReference &ref)
{
	return m_parser.m_filesize;
}

RESULT eStaticServiceDVBPVRInformation::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &evt, time_t start_time)
{
	if (!ref.path.empty())
	{
		if (ref.path.substr(0, 7) == "http://")
		{
			eServiceReference equivalentref(ref);
			/* this might be a scrambled stream (id + 0x100), force equivalent dvb type */
			equivalentref.type = eServiceFactoryDVB::id;
			equivalentref.path.clear();
			return eEPGCache::getInstance()->lookupEventTime(equivalentref, start_time, evt);
		}
		else
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
	RESULT reindex();
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
				eraser->erase(*i);
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
		if (::access(buf, R_OK) < 0) break;
		res.push_back(buf);
	}

	res.push_back(m_ref.path + ".meta");
	res.push_back(m_ref.path + ".ap");
	res.push_back(m_ref.path + ".sc");
	res.push_back(m_ref.path + ".cuts");
	std::string tmp = m_ref.path;
	tmp.erase(m_ref.path.length()-3);
	res.push_back(tmp + ".eit");
	return 0;
}

static int reindex_work(const std::string& filename)
{
	/* This does not work, need to call parser.setPid(pid, type) otherwise
	 * the parser will not actually output any data! */

	eRawFile f;

	int err = f.open(filename.c_str());
	if (err < 0)
		return err;

	eMPEGStreamParserTS parser; /* Missing packetsize, should be determined from stream? */

	{
		unsigned int i;
		bool timingpidset = false;
		eDVBTSTools tstools;
		tstools.openFile(filename.c_str(), 1);
		eDVBPMTParser::program program;
		err = tstools.findPMT(program);
		if (err)
		{
			eDebug("reindex - Failed to find PMT");
			return err;
		}
		for (i = 0; i < program.videoStreams.size(); i++)
		{
			if (timingpidset) break;
			eDebug("reindex: video pid=0x%x", program.videoStreams[i].pid);
			parser.setPid(program.videoStreams[i].pid, iDVBTSRecorder::video_pid, program.videoStreams[i].type);
			timingpidset = true;
		}
		for (i = 0; i < program.audioStreams.size(); i++)
		{
			if (timingpidset) break;
			eDebug("reindex: audio pid=0x%x", program.audioStreams[i].pid);
			parser.setPid(program.audioStreams[i].pid, iDVBTSRecorder::audio_pid, program.audioStreams[i].type);
			timingpidset = true;
		}
	}

	parser.startSave(filename);

	off_t offset = 0;
	std::vector<char> buffer(188*1024);
	while (1)
	{
		int r = f.read(offset, &buffer[0], buffer.size());
		if (!r)
			break;
		if (r < 0)
			return r;
		parser.parseData(offset, &buffer[0], r);
		offset += r;
	}

	parser.stopSave();
	return 0;
}

RESULT eDVBPVRServiceOfflineOperations::reindex()
{
	int result;
	/* Release global interpreter lock */
	Py_BEGIN_ALLOW_THREADS;
	result = reindex_work(m_ref.path.c_str());
	Py_END_ALLOW_THREADS;
	return result;
}

DEFINE_REF(eServiceFactoryDVB)

eServiceFactoryDVB::eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("ts");
		extensions.push_back("trp");
		sc->addServiceFactory(eServiceFactoryDVB::id, this, extensions);
		/*
		 * User can indicate that a ts stream is scrambled, by using servicetype id + 0x100
		 * This only works by specifying the servicetype, we won't allow file extension
		 * lookup, as we cannot map the same extensions to several service types.
		 */
		extensions.clear();
		sc->addServiceFactory(eServiceFactoryDVB::id + 0x100, this, extensions);
	}

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
//   n = Short Service Name (short name brakets used) (as python string object)
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

		if (strchr(format, 'N') || strchr(format, 'n'))
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

							// filter short name brakets
							size_t pos;
							while((pos = name.find("\xc2\x86")) != std::string::npos)
								name.erase(pos,2);
							while((pos = name.find("\xc2\x87")) != std::string::npos)
								name.erase(pos,2);

							if (name.length())
								tmp = PyString_FromString(name.c_str());
						}
					}
					if (!tmp)
						tmp = PyString_FromString("<n/a>");
					break;
				case 'n':  // short service name
					if (service_center)
					{
						service_center->info(ref, sptr);
						if (sptr)
						{
							std::string name;
							sptr->getName(ref, name);
							name = buildShortName(name);
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

RESULT eDVBServiceList::removeService(eServiceReference &ref, bool renameBouquet)
{
	if (!m_bouquet)
		return -1;
	return m_bouquet->removeService(ref, renameBouquet);
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
	bool isstream = ref.path.substr(0, 7) == "http://";
	ptr = new eDVBServiceRecord((eServiceReferenceDVB&)ref, isstream);
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
	if (!ref.path.empty()) // playback
	{
		eDVBMetaParser parser;
		int ret=parser.parseFile(ref.path);
		service = new eDVBService;
		if (!ret)
			eDVBDB::getInstance()->parseServiceData(service, parser.m_service_data);
	}
	else
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
//			eDebug("getService failed!");
			return err;
		}
	}

	return 0;
}

eDVBServicePlay::eDVBServicePlay(const eServiceReference &ref, eDVBService *service):
	m_reference(ref),
	m_dvb_service(service),
	m_decoder_index(0),
	m_have_video_pid(0),
	m_tune_state(-1),
	m_is_stream(ref.path.substr(0, 7) == "http://"),
	m_is_pvr(!ref.path.empty() && !m_is_stream),
	m_is_paused(0),
	m_timeshift_enabled(0),
	m_timeshift_active(0),
	m_timeshift_changed(0),
	m_save_timeshift(0),
	m_timeshift_fd(-1),
	m_skipmode(0),
	m_fastforward(0),
	m_slowmotion(0),
	m_cuesheet_changed(0),
	m_cutlist_enabled(1),
	m_subtitle_widget(0),
	m_subtitle_sync_timer(eTimer::create(eApp)),
	m_nownext_timer(eTimer::create(eApp))
{
	CONNECT(m_service_handler.serviceEvent, eDVBServicePlay::serviceEvent);
	CONNECT(m_service_handler_timeshift.serviceEvent, eDVBServicePlay::serviceEventTimeshift);
	CONNECT(m_event_handler.m_eit_changed, eDVBServicePlay::gotNewEvent);
	CONNECT(m_subtitle_sync_timer->timeout, eDVBServicePlay::checkSubtitleTiming);
	CONNECT(m_nownext_timer->timeout, eDVBServicePlay::updateEpgCacheNowNext);
}

eDVBServicePlay::~eDVBServicePlay()
{
	if (m_is_pvr)
	{
		eDVBMetaParser meta;
		int ret=meta.parseFile(m_reference.path);
		if (!ret)
		{
			char tmp[255];
			meta.m_service_data="";
			sprintf(tmp, "f:%x", m_dvb_service->m_flags);
			meta.m_service_data += tmp;
			// cached pids
			for (int x=0; x < eDVBService::cacheMax; ++x)
			{
				int entry = m_dvb_service->getCacheEntry((eDVBService::cacheID)x);
				if (entry != -1)
				{
					sprintf(tmp, ",c:%02d%04x", x, entry);
					meta.m_service_data += tmp;
				}
			}
			meta.updateMeta(m_reference.path);
		}
	}
	if (m_subtitle_widget) m_subtitle_widget->destroy();
}

void eDVBServicePlay::gotNewEvent(int error)
{
	ePtr<eServiceEvent> event_now;
	getEvent(event_now, 0);
#if 0
		// debug only
	ePtr<eServiceEvent> event_next;
	getEvent(event_next, 1);

	if (event_now)
		eDebug("now running: %s (%d seconds :)", event_now->m_event_name.c_str(), event_now->m_duration);
	if (event_next)
		eDebug("next running: %s (%d seconds :)", event_next->m_event_name.c_str(), event_next->m_duration);
#endif
	if (!error)
	{
		m_nownext_timer->stop();
		m_event((iPlayableService*)this, evUpdatedEventInfo);
	}
	else
	{
		/* our eit reader has stopped, we have to take care of our own event updates */
		updateEpgCacheNowNext();
	}

	if (m_timeshift_enabled)
	{
		if (!event_now)
			return;

		pts_t now_pts, first_pts, fixup_pts;
		if (m_record)
		{
			if (m_record->getCurrentPCR(now_pts))
				eDebug("getting current PTS failed!");
			else
			{
				if (m_record->getFirstPTS(first_pts))
					return;
				if (now_pts < first_pts)
					fixup_pts = now_pts + 0x200000000LL - first_pts;
				else
					fixup_pts = now_pts - first_pts;
				m_cue_entries.insert(cueEntry(fixup_pts, 2));
				m_cuesheet_changed = 1;
				eDebug("pts of eit change: %llx, fixup_pts: %llx, first_pts: %llx", now_pts, fixup_pts, first_pts);
				m_event((iPlayableService*)this, evCuesheetChanged);
			}
		}
	}
}

void eDVBServicePlay::updateEpgCacheNowNext()
{
	bool update = false;
	ePtr<eServiceEvent> next = 0;
	ePtr<eServiceEvent> ptr = 0;
	eServiceReferenceDVB &ref = (eServiceReferenceDVB&) m_reference;
	if (eEPGCache::getInstance() && eEPGCache::getInstance()->lookupEventTime(ref, -1, ptr) >= 0)
	{
		ePtr<eServiceEvent> current = 0;
		m_event_handler.getEvent(current, 0);
		if (!current || !ptr || current->getEventId() != ptr->getEventId())
		{
			update = true;
			m_event_handler.inject(ptr, 0);
			time_t next_time = ptr->getBeginTime() + ptr->getDuration();
			if (eEPGCache::getInstance()->lookupEventTime(ref, next_time, ptr) >= 0)
			{
				next = ptr;
				m_event_handler.inject(ptr, 1);
			}
		}
	}

	int refreshtime = 60;
	if (!next)
	{
		m_event_handler.getEvent(next, 1);
	}
	if (next)
	{
		time_t now = eDVBLocalTimeHandler::getInstance()->nowTime();
		refreshtime = (int)(next->getBeginTime() - now) + 3;
		if (refreshtime <= 0 || refreshtime > 60) refreshtime = 60;
	}
	m_nownext_timer->startLongTimer(refreshtime);
	if (update) m_event((iPlayableService*)this, evUpdatedEventInfo);
}

void eDVBServicePlay::serviceEvent(int event)
{
	m_tune_state = event;

	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		/* fill now/next with info from the epg cache, will be replaced by EIT when it arrives */
		updateEpgCacheNowNext();

		/* default behaviour is to start an eit reader, and wait for now/next info, unless this is disabled */
		if (eConfigManager::getConfigBoolValue("config.usage.show_eit_nownext", true))
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
		}
		m_event((iPlayableService*)this, evTunedIn);
		break;
	}
	case eDVBServicePMTHandler::eventNoResources:
	case eDVBServicePMTHandler::eventNoPAT:
	case eDVBServicePMTHandler::eventNoPATEntry:
	case eDVBServicePMTHandler::eventNoPMT:
	case eDVBServicePMTHandler::eventTuneFailed:
	case eDVBServicePMTHandler::eventMisconfiguration:
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
		if (m_first_program_info & 1 && m_is_pvr)
		{
			m_first_program_info &= ~1;
			seekTo(0);
		}
		if (!m_timeshift_active)
			m_event((iPlayableService*)this, evUpdatedInfo);

		m_event((iPlayableService*)this, evNewProgramInfo);
		break;
	}
	case eDVBServicePMTHandler::eventPreStart:
		loadCuesheet();
		break;
	case eDVBServicePMTHandler::eventEOF:
		m_event((iPlayableService*)this, evEOF);
		break;
	case eDVBServicePMTHandler::eventSOF:
		m_event((iPlayableService*)this, evSOF);
		break;
	case eDVBServicePMTHandler::eventHBBTVInfo:
		m_event((iPlayableService*)this, evHBBTVInfo);
		break;
	}
}

void eDVBServicePlay::serviceEventTimeshift(int event)
{
	switch (event)
	{
	case eDVBServicePMTHandler::eventNewProgramInfo:
		eDebug("eventNewProgramInfo TS");
		if (m_timeshift_active)
		{
			updateDecoder();
			if (m_first_program_info & 2)
			{
				if (m_slowmotion)
				{
					eDebug("re-apply slowmotion after timeshift file change");
					m_decoder->setSlowMotion(m_slowmotion);
				}
				if (m_fastforward)
				{
					eDebug("re-apply skip %d, ratio %d after timeshift file change", m_skipmode, m_fastforward);
					if (m_skipmode)
						m_cue->setSkipmode(m_skipmode * 90000); /* convert to 90000 per second */
					if (m_fastforward != 1)
						m_decoder->setFastForward(m_fastforward);
					else
						m_decoder->setTrickmode();
				}
				else
					seekTo(0);
				m_first_program_info &= ~2;
			}
			m_event((iPlayableService*)this, evUpdatedInfo);
		}
		break;
	case eDVBServicePMTHandler::eventSOF:
#if 0
		if (!m_timeshift_file_next.empty())
		{
			eDebug("timeshift SOF, switch to next file");
			m_decoder->pause();

			m_first_program_info |= 2;

			eServiceReferenceDVB r = (eServiceReferenceDVB&)m_reference;
			r.path = m_timeshift_file_next;

			/* free the timeshift service handler, we need the resources */
			m_service_handler_timeshift.free();
			resetTimeshift(1);

			if (m_skipmode < 0)
				m_cue->seekTo(0, -1000);
			ePtr<iTsSource> source = createTsSource(r);
			m_service_handler_timeshift.tuneExt(r, 1, source, r.path.c_str(), m_cue, 0, m_dvb_service, false); /* use the decoder demux for everything */

			m_event((iPlayableService*)this, evUser+1);
		}
		else
#endif
			m_event((iPlayableService*)this, evSOF);
		break;
	case eDVBServicePMTHandler::eventEOF:
		if ((!m_is_paused) && (m_skipmode >= 0))
		{
			if (m_timeshift_file_next.empty())
			{
				eDebug("timeshift EOF, so let's go live");
				switchToLive();
			}
			else
			{
				eDebug("timeshift EOF, switch to next file");

				m_first_program_info |= 2;

				eServiceReferenceDVB r = (eServiceReferenceDVB&)m_reference;
				r.path = m_timeshift_file_next;

				/* free the timeshift service handler, we need the resources */
				m_service_handler_timeshift.free();
				resetTimeshift(1);

				ePtr<iTsSource> source = createTsSource(r);
				m_service_handler_timeshift.tuneExt(r, 1, source, m_timeshift_file_next.c_str(), m_cue, 0, m_dvb_service, eDVBServicePMTHandler::timeshift_playback, false); /* use the decoder demux for everything */

				m_event((iPlayableService*)this, evUser+1);
			}
		}
		break;
	}
}

RESULT eDVBServicePlay::start()
{
	eServiceReferenceDVB service = (eServiceReferenceDVB&)m_reference;
	bool scrambled = true;
	int packetsize = 188;
	eDVBServicePMTHandler::serviceType type = eDVBServicePMTHandler::livetv;
	ePtr<eDVBResourceManager> res_mgr;

	bool remote_fallback_enabled = eConfigManager::getConfigBoolValue("config.usage.remote_fallback_enabled", false);
	std::string remote_fallback_url = eConfigManager::getConfigValue("config.usage.remote_fallback");

	if(!m_is_stream && !m_is_pvr &&
			remote_fallback_enabled &&
			(remote_fallback_url.length() > 0) &&
			!eDVBResourceManager::getInstance(res_mgr))
	{
		eDVBChannelID chid, chid_ignore;
		int system;

		service.getChannelID(chid);
		eServiceReferenceDVB().getChannelID(chid_ignore);

		if(!res_mgr->canAllocateChannel(chid, chid_ignore, system))
		{
			size_t index;

			while((index = remote_fallback_url.find(':')) != std::string::npos)
			{
				remote_fallback_url.erase(index, 1);
				remote_fallback_url.insert(index, "%3a");
			}

			std::ostringstream remote_service_ref;
			remote_service_ref << std::hex << service.type << ":" << service.flags << ":" << 
					service.getData(0) << ":" << service.getData(1) << ":" << service.getData(2) << ":0:0:0:0:0:" <<
					remote_fallback_url << "/" <<
					service.type << "%3a" << service.flags;
			for(index = 0; index < 8; index++)
					remote_service_ref << "%3a" << service.getData(index);

			service = eServiceReferenceDVB(remote_service_ref.str());

			m_is_stream = true;
			m_is_pvr = false;
		}
	}

		/* in pvr mode, we only want to use one demux. in tv mode, we're using
		   two (one for decoding, one for data source), as we must be prepared
		   to start recording from the data demux. */
	if (m_is_pvr)
	{
		eDVBMetaParser meta;
		if (!meta.parseFile(m_reference.path))
		{
			service = meta.m_ref;
			service.path = m_reference.path;
			packetsize = meta.m_packet_size;
			scrambled = meta.m_scrambled;
		}
		m_cue = new eCueSheet();
		type = eDVBServicePMTHandler::playback;
	}
	else
		m_event(this, evStart);

	if (m_is_stream)
	{
		/*
		 * streams are considered to be descrambled by default;
		 * user can indicate a stream is scrambled, by using servicetype id + 0x100
		 */
		scrambled = (m_reference.type == eServiceFactoryDVB::id + 0x100);
		type = eDVBServicePMTHandler::streamclient;
	}

	m_first_program_info = 1;
	ePtr<iTsSource> source = createTsSource(service, packetsize);
	m_service_handler.tuneExt(service, m_is_pvr, source, service.path.c_str(), m_cue, false, m_dvb_service, type, scrambled);

	if (m_is_pvr)
	{
		/* inject EIT if there is a stored one */
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
		m_event(this, evStart);
	}
	return 0;
}

RESULT eDVBServicePlay::stop()
{
		/* add bookmark for last play position */
		/* m_cutlist_enabled bit 2 is the "don't remember bit" */
	if (m_is_pvr && ((m_cutlist_enabled & 2) == 0))
	{
		pts_t play_position, length;
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

			if (getLength(length))
				length = 0;

			if (length)
			{
				m_cue_entries.insert(cueEntry(play_position, 3)); /* last play position */
			}
			m_cuesheet_changed = 1;
		}
	}

	if ((m_is_pvr || m_timeshift_enabled) && m_cuesheet_changed)
	{
		saveCuesheet();
	}

	stopTimeshift(); /* in case timeshift was enabled, remove buffer etc. */

	m_service_handler_timeshift.free();
	m_service_handler.free();

	m_nownext_timer->stop();
	m_event((iPlayableService*)this, evStopped);
	return 0;
}

RESULT eDVBServicePlay::setTarget(int target)
{
	m_decoder_index = target;
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
	int ret = 0;
	ASSERT(ratio); /* The API changed: instead of calling setSlowMotion(0), call play! */
	eDebug("eDVBServicePlay::setSlowMotion(%d)", ratio);
	setFastForward_internal(0);
	if (m_decoder)
	{
		ret = m_decoder->setSlowMotion(ratio);
		if (!ret)
			m_slowmotion = ratio;
		return ret;
	}
	else
		return -1;
}

RESULT eDVBServicePlay::setFastForward(int ratio)
{
	eDebug("eDVBServicePlay::setFastForward(%d)", ratio);
	ASSERT(ratio);
	return setFastForward_internal(ratio);
}

RESULT eDVBServicePlay::setFastForward_internal(int ratio, bool final_seek)
{
	int skipmode, ffratio, ret = 0;
	pts_t pos=0;

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
		{
			long long _skipmode = skipmode;
			if (!m_timeshift_active && (m_current_video_pid_type == eDVBServicePMTHandler::videoStream::vtH265_HEVC))
			{
				if (ratio < 0)
					_skipmode = skipmode * 3;
				else
					_skipmode = skipmode * 4;
			}
			m_cue->setSkipmode(_skipmode * 90000); /* convert to 90000 per second */
		}
	}

	m_skipmode = skipmode;

	if (final_seek)
		eDebug("trickplay stopped .. ret %d, pos %lld", getPlayPosition(pos), pos);

	m_fastforward = ffratio;

	if (!m_decoder)
		return -1;

	if (ffratio == 0)
		; /* return m_decoder->play(); is done in caller*/
	else if (ffratio != 1)
		ret = m_decoder->setFastForward(ffratio);
	else
		ret = m_decoder->setTrickmode();

	if (pos)
		eDebug("final seek after trickplay ret %d", seekTo(pos));

	return ret;
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
	eDebug("eDVBServicePlay::pause");
	setFastForward_internal(0, m_slowmotion || m_fastforward > 1);
	if (m_decoder)
	{
		m_slowmotion = 0;
		m_is_paused = 1;
		return m_decoder->pause();
	} else
		return -1;
}

RESULT eDVBServicePlay::unpause()
{
	eDebug("eDVBServicePlay::unpause");
	setFastForward_internal(0, m_slowmotion || m_fastforward > 1);
	if (m_decoder)
	{
		m_slowmotion = 0;
		m_is_paused = 0;
		return m_decoder->play();
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
	m_dvb_subtitle_pages.clear();
	m_subtitle_pages.clear();

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
	m_dvb_subtitle_pages.clear();
	m_subtitle_pages.clear();
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
	return pvr_channel->getCurrentPosition(m_decode_demux, pos, m_decoder);
}

RESULT eDVBServicePlay::setTrickmode(int trick)
{
		/* currently unimplemented */
	return -1;
}

RESULT eDVBServicePlay::isCurrentlySeekable()
{
	return (m_is_pvr || m_timeshift_active) ? 3 : 0; // fast forward/backward possible and seeking possible
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
	if (m_timeshift_enabled || !m_is_pvr)
	{
		if (!m_timeshift_enabled)
		{
			/* query config path */
			std::string tspath = eConfigManager::getConfigValue("config.usage.timeshift_path");
			if(tspath == "")
			{
				eDebug("could not query ts path from config");
				return -4;
			}
			tspath.append("/");
			/* we need enough diskspace */
			struct statfs fs;
			if (statfs(tspath.c_str(), &fs) < 0)
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
	if (m_is_pvr || m_timeshift_enabled)
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

RESULT eDVBServicePlay::rdsDecoder(ePtr<iRdsDecoder> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::streamed(ePtr<iStreamedService> &ptr)
{
	if (m_is_stream)
	{
		ptr = this;
		return 0;
	}
	ptr = 0;
	return -1;
}

ePtr<iStreamBufferInfo> eDVBServicePlay::getBufferCharge()
{
	/** FIXME **/
	return 0;
}

int eDVBServicePlay::setBufferSize(int size)
{
	/** FIXME **/
	return 0;
}

RESULT eDVBServicePlay::getName(std::string &name)
{
	if (m_is_pvr)
	{
		ePtr<iStaticServiceInformation> i = new eStaticServiceDVBPVRInformation(m_reference);
		return i->getName(m_reference, name);
	}
	else if (m_is_stream)
	{
		if (m_dvb_service)
			m_dvb_service->getName(m_reference, name);
		else
			name = "unknown service";
		if (name.empty())
			name = m_reference.name;
			if (name.empty())
				name = m_reference.path;
				if (name.empty())
					name = "(...)";
	}
	else if (m_dvb_service)
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

	if (w == sCAIDs || w == sCAIDPIDs)
		return resIsPyObject;

	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	int no_program_info = 0;

	if (h.getProgramInfo(program))
		no_program_info = 1;

	switch (w)
	{
	case sVideoHeight:
		if (m_decoder)
			return m_decoder->getVideoHeight();
		break;
	case sVideoWidth:
		if (m_decoder)
			return m_decoder->getVideoWidth();
		break;
	case sFrameRate:
		if (m_decoder)
			return m_decoder->getVideoFrameRate();
		break;
	case sProgressive:
		if (m_decoder)
			return m_decoder->getVideoProgressive();
		break;
	case sAspect:
	{
		int aspect = -1;
		if (m_decoder)
			aspect = m_decoder->getVideoAspect();
		if (aspect == -1 && no_program_info)
			break;
		else if (aspect == -1 && !program.videoStreams.empty() && program.videoStreams[0].component_tag != -1)
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
		else
			return aspect;
		break;
	}
	case sIsCrypted: if (no_program_info) return false; return program.isCrypted();
	case sVideoPID:
		if (m_dvb_service)
		{
			int vpid = m_dvb_service->getCacheEntry(eDVBService::cVPID);
			if (vpid != -1)
				return vpid;
		}
		if (no_program_info) return -1; if (program.videoStreams.empty()) return -1; return program.videoStreams[0].pid;
	case sVideoType: if (no_program_info) return -1; if (program.videoStreams.empty()) return -1; return program.videoStreams[0].type;
	case sAudioPID:
		if (m_dvb_service)
		{
			int apid = m_dvb_service->getCacheEntry(eDVBService::cMPEGAPID);
			if (apid != -1)
				return apid;
			apid = m_dvb_service->getCacheEntry(eDVBService::cAC3PID);
			if (apid != -1)
				return apid;
			apid = m_dvb_service->getCacheEntry(eDVBService::cDDPPID);
			if (apid != -1)
				return apid;
			apid = m_dvb_service->getCacheEntry(eDVBService::cAACHEAPID);
			if (apid != -1)
				return apid;
		}
		if (no_program_info) return -1; if (program.audioStreams.empty()) return -1; return program.audioStreams[0].pid;
	case sPCRPID:
		if (m_dvb_service)
		{
			int pcrpid = m_dvb_service->getCacheEntry(eDVBService::cPCRPID);
			if (pcrpid != -1)
				return pcrpid;
		}
		if (no_program_info) return -1; return program.pcrPid;
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
		break;
	}
	return -1;
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
	case sHBBTVUrl:
	{
		std::string url;
		eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
		h.getHBBTVUrl(url);
		return url;
	}
	case sLiveStreamDemuxId:
	{
		eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
		std::string demux;
		demux += h.getDemuxID() + '0';
		return demux;
	}
	default:
		break;
	}
	return iServiceInformation::getInfoString(w);
}

ePtr<iDVBTransponderData> eDVBServicePlay::getTransponderData()
{
	return eStaticServiceDVBInformation().getTransponderData(m_reference);
}

void eDVBServicePlay::getAITApplications(std::map<int, std::string> &aitlist)
{
	return m_service_handler.getAITApplications(aitlist);
}

void eDVBServicePlay::getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids)
{
	m_service_handler.getCaIds(caids, ecmpids);
}

int eDVBServicePlay::getNumberOfTracks()
{
	eDVBServicePMTHandler::program program;
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
	if (h.getProgramInfo(program))
		return 0;
	return program.audioStreams.size();
}

int eDVBServicePlay::getCurrentTrack()
{
	eDVBServicePMTHandler::program program;
	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
	if (h.getProgramInfo(program))
		return 0;

	int max = program.audioStreams.size();
	int i;

	for (i = 0; i < max; ++i)
		if (program.audioStreams[i].pid == m_current_audio_pid)
			return i;

	return 0;
}

RESULT eDVBServicePlay::selectTrack(unsigned int i)
{
	int ret = selectAudioStream(i);

	if (m_decoder->set())
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

	info.m_pid = program.audioStreams[i].pid;

	if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atMPEG)
		info.m_description = "MPEG";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAC3)
		info.m_description = "AC3";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atDDP)
		info.m_description = "AC3+";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAAC)
		info.m_description = "AAC";
	else if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atAACHE)
		info.m_description = "AAC-HE";
	else  if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atDTS)
		info.m_description = "DTS";
	else  if (program.audioStreams[i].type == eDVBServicePMTHandler::audioStream::atDTSHD)
		info.m_description = "DTS-HD";
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
	pts_t position = -1;

	if (h.getProgramInfo(program))
		return -1;

	if ((i != -1) && ((unsigned int)i >= program.audioStreams.size()))
		return -2;

	if (!m_decoder)
		return -3;

	int stream = i;
	if (stream == -1)
		stream = program.defaultAudioStream;

	int apid = -1, apidtype = -1;

	if (((unsigned int)stream) < program.audioStreams.size())
	{
		apid = program.audioStreams[stream].pid;
		apidtype = program.audioStreams[stream].type;
	}

	if (i != -1 && apid != m_current_audio_pid && (m_is_pvr || m_timeshift_active))
		eDebug("getPlayPosition ret %d, pos %lld in selectAudioStream", getPlayPosition(position), position);

	m_current_audio_pid = apid;

	pts_t a_pts, v_pts;
	a_pts = v_pts = 0;
	m_decoder->getPTS(2, a_pts);
	m_decoder->getPTS(1, v_pts);
	eDebug("a: %lld   v: %lld  %lld",a_pts, v_pts, a_pts-v_pts);
	bool radio_workaround = false;
	if(v_pts && a_pts && (abs(a_pts-v_pts) > 2* 90000))
		radio_workaround = true;

	if(radio_workaround)
		if (m_decoder->setAudioPID(-1, 0))
		{
			eDebug("set audio pid failed");
			return -4;
		}

	if (m_decoder->setAudioPID(apid, apidtype))
	{
		eDebug("set audio pid failed");
		return -4;
	}

	if (position != -1)
		eDebug("seekTo ret %d", seekTo(position));

	int rdsPid = apid;

		/* if we are not in PVR mode, timeshift is not active and we are not in pip mode, check if we need to enable the rds reader */
	if (!(m_is_pvr || m_timeshift_active || m_decoder_index || m_have_video_pid))
	{
		int different_pid = program.videoStreams.empty() && program.audioStreams.size() == 1 && program.audioStreams[stream].rdsPid != -1;
		if (different_pid)
			rdsPid = program.audioStreams[stream].rdsPid;
		if (!m_rds_decoder || m_rds_decoder->getPid() != rdsPid)
		{
			m_rds_decoder = 0;
			ePtr<iDVBDemux> data_demux;
			if (!h.getDataDemux(data_demux))
			{
				m_rds_decoder = new eDVBRdsDecoder(data_demux, different_pid);
				m_rds_decoder->connectEvent(slot(*this, &eDVBServicePlay::rdsDecoderEvent), m_rds_decoder_event_connection);
				m_rds_decoder->start(rdsPid);
			}
		}
	}

	if(radio_workaround)
		m_decoder->setSyncPCR(-1);

			/* store new pid as default only when:
				a.) we have an entry in the service db for the current service,
				b.) we are not playing back something,
				c.) we are not selecting the default entry. (we wouldn't change
				    anything in the best case, or destroy the default setting in
				    case the real default is not yet available.)
				d.) we have only one audiostream (overwrite the cache to make sure
				    the cache contains the correct audio pid and type)
			*/
	if (m_dvb_service && ((i != -1) || (program.audioStreams.size() == 1)
		|| ((m_dvb_service->getCacheEntry(eDVBService::cMPEGAPID) == -1)
		&& (m_dvb_service->getCacheEntry(eDVBService::cAC3PID)== -1)
		&& (m_dvb_service->getCacheEntry(eDVBService::cDDPPID)== -1)
		&& (m_dvb_service->getCacheEntry(eDVBService::cAACHEAPID) == -1))))
	{
		m_dvb_service->setCacheEntry(eDVBService::cMPEGAPID, apidtype == eDVBAudio::aMPEG ? apid : -1);
		m_dvb_service->setCacheEntry(eDVBService::cAC3PID, apidtype == eDVBAudio::aAC3 ? apid : -1);
		m_dvb_service->setCacheEntry(eDVBService::cDDPPID, apidtype == eDVBAudio::aDDP ? apid : -1);
		m_dvb_service->setCacheEntry(eDVBService::cAACHEAPID, apidtype == eDVBAudio::aAACHE ? apid : -1);
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

std::string eDVBServicePlay::getText(int x)
{
	if (m_rds_decoder)
		switch(x)
		{
			case RadioText:
				return convertLatin1UTF8(m_rds_decoder->getRadioText());
			case RtpText:
				return convertLatin1UTF8(m_rds_decoder->getRtpText());
		}
	return "";
}

void eDVBServicePlay::rdsDecoderEvent(int what)
{
	switch(what)
	{
		case eDVBRdsDecoder::RadioTextChanged:
			m_event((iPlayableService*)this, evUpdatedRadioText);
			break;
		case eDVBRdsDecoder::RtpTextChanged:
			m_event((iPlayableService*)this, evUpdatedRtpText);
			break;
		case eDVBRdsDecoder::RassInteractivePicMaskChanged:
			m_event((iPlayableService*)this, evUpdatedRassInteractivePicMask);
			break;
		case eDVBRdsDecoder::RecvRassSlidePic:
			m_event((iPlayableService*)this, evUpdatedRassSlidePic);
			break;
	}
}

void eDVBServicePlay::showRassSlidePicture()
{
	if (m_rds_decoder)
	{
		if (m_decoder)
		{
			std::string rass_slide_pic = m_rds_decoder->getRassSlideshowPicture();
			if (rass_slide_pic.length())
				m_decoder->showSinglePic(rass_slide_pic.c_str());
			else
				eDebug("empty filename for rass slide picture received!!");
		}
		else
			eDebug("no MPEG Decoder to show iframes avail");
	}
	else
		eDebug("showRassSlidePicture called.. but not decoder");
}

void eDVBServicePlay::showRassInteractivePic(int page, int subpage)
{
	if (m_rds_decoder)
	{
		if (m_decoder)
		{
			std::string rass_interactive_pic = m_rds_decoder->getRassPicture(page, subpage);
			if (rass_interactive_pic.length())
				m_decoder->showSinglePic(rass_interactive_pic.c_str());
			else
				eDebug("empty filename for rass interactive picture %d/%d received!!", page, subpage);
		}
		else
			eDebug("no MPEG Decoder to show iframes avail");
	}
	else
		eDebug("showRassInteractivePic called.. but not decoder");
}

ePyObject eDVBServicePlay::getRassInteractiveMask()
{
	if (m_rds_decoder)
		return m_rds_decoder->getRassPictureMask();
	Py_RETURN_NONE;
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

ePtr<iDVBFrontendData> eDVBServiceBase::getFrontendData()
{
	ePtr<iDVBFrontendData> ret;
	eUsePtr<iDVBChannel> channel;
	if(!m_service_handler.getChannel(channel))
	{
		ePtr<iDVBFrontend> fe;
		if(!channel->getFrontend(fe))
			fe->getFrontendData(ret);
	}
	return ret;
}

ePtr<iDVBFrontendStatus> eDVBServiceBase::getFrontendStatus()
{
	ePtr<iDVBFrontendStatus> ret;
	eUsePtr<iDVBChannel> channel;
	if(!m_service_handler.getChannel(channel))
	{
		ePtr<iDVBFrontend> fe;
		if(!channel->getFrontend(fe))
			fe->getFrontendStatus(ret);
	}
	return ret;
}

ePtr<iDVBTransponderData> eDVBServiceBase::getTransponderData(bool original)
{
	ePtr<iDVBTransponderData> ret;
	eUsePtr<iDVBChannel> channel;
	if(!m_service_handler.getChannel(channel))
	{
		ePtr<iDVBFrontend> fe;
		if(!channel->getFrontend(fe))
			fe->getTransponderData(ret, original);
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

	std::string tspath = eConfigManager::getConfigValue("config.usage.timeshift_path");
	if (tspath == "")
	{
		eDebug("could not query ts path");
		return -5;
	}
	if (tspath.empty())
	{
		eDebug("TS path is empty");
		return -5;
	}
	if (tspath[tspath.length()-1] != '/')
		tspath.append("/");
	tspath.append("timeshift.XXXXXX");
	char* templ = new char[tspath.length() + 1];
	strcpy(templ, tspath.c_str());
	m_timeshift_fd = mkstemp(templ);
	m_timeshift_file = std::string(templ);
	eDebug("recording to %s", templ);

	ofstream fileout;
	fileout.open("/proc/stb/lcd/symbol_timeshift");
	if(fileout.is_open())
	{
		fileout << "1";
	}

	delete [] templ;

	if (m_timeshift_fd < 0)
	{
		m_record = 0;
		return -4;
	}

	m_record->setTargetFD(m_timeshift_fd);
	m_record->setTargetFilename(m_timeshift_file);
	m_record->enableAccessPoints(false); // no need for AP information during shift
	m_timeshift_enabled = 1;

	updateTimeshiftPids();
	m_record->start();

	return 0;
}

RESULT eDVBServicePlay::stopTimeshift(bool swToLive)
{
	if (!m_timeshift_enabled)
		return -1;

	if (swToLive)
		switchToLive();

	m_timeshift_enabled = 0;

	m_record->stop();
	m_record = 0;

	if (m_timeshift_fd >= 0)
	{
		close(m_timeshift_fd);
		m_timeshift_fd = -1;
	}

	ofstream fileout;
	fileout.open("/proc/stb/lcd/symbol_timeshift");
	if(fileout.is_open())
	{
		fileout << "0";
	}

	if (!m_save_timeshift)
	{
		eDebug("remove timeshift files");
		eBackgroundFileEraser::getInstance()->erase(m_timeshift_file);
		eBackgroundFileEraser::getInstance()->erase(m_timeshift_file + ".sc");
		eBackgroundFileEraser::getInstance()->erase(m_timeshift_file + ".cuts");
	}
	else
	{
		eDebug("timeshift files not deleted");
		m_save_timeshift = 0;
	}
	return 0;
}

int eDVBServicePlay::isTimeshiftActive()
{
	return m_timeshift_enabled && m_timeshift_active;
}

int eDVBServicePlay::isTimeshiftEnabled()
{
        return m_timeshift_enabled;
}

RESULT eDVBServicePlay::saveTimeshiftFile()
{
	if (!m_timeshift_enabled)
                return -1;

	m_save_timeshift = 1;

	return 0;
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

std::string eDVBServicePlay::getTimeshiftFilename()
{
	if (m_timeshift_enabled)
		return m_timeshift_file;
	else
		return "";
}

PyObject *eDVBServicePlay::getCutList()
{
	ePyObject list = PyList_New(0);

	for (std::multiset<struct cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i)
	{
		ePyObject tuple = PyTuple_New(2);
		PyTuple_SET_ITEM(tuple, 0, PyLong_FromLongLong(i->where));
		PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(i->what));
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
		int timing_pid = -1;
		int timing_stream_type = -1;
		iDVBTSRecorder::timing_pid_type timing_pid_type = iDVBTSRecorder::none;
		std::set<int> pids_to_record;
		pids_to_record.insert(0); // PAT
		if (program.pmtPid != -1)
			pids_to_record.insert(program.pmtPid); // PMT

		if (program.textPid != -1)
			pids_to_record.insert(program.textPid); // Videotext

		for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
			i(program.videoStreams.begin());
			i != program.videoStreams.end(); ++i)
		{
			if (timing_pid == -1)
			{
				timing_pid = i->pid;
				timing_stream_type = i->type;
				timing_pid_type = iDVBTSRecorder::video_pid;
			}
			pids_to_record.insert(i->pid);
		}

		for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
			i(program.audioStreams.begin());
			i != program.audioStreams.end(); ++i)
		{
			if (timing_pid == -1)
			{
				timing_pid = i->pid;
				timing_stream_type = i->type;
				timing_pid_type = iDVBTSRecorder::audio_pid;
			}
			pids_to_record.insert(i->pid);
		}

		for (std::vector<eDVBServicePMTHandler::subtitleStream>::const_iterator
			i(program.subtitleStreams.begin());
			i != program.subtitleStreams.end(); ++i)
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

		if (timing_pid != -1)
			m_record->setTimingPID(timing_pid, timing_pid_type, timing_stream_type);
	}
}

RESULT eDVBServicePlay::setNextPlaybackFile(const char *f)
{
	m_timeshift_file_next = f;
	return 0;
}

void eDVBServicePlay::switchToLive()
{
	if (!m_timeshift_active)
		return;

	eDebug("SwitchToLive");

	resetTimeshift(0);

	m_is_paused = m_skipmode = m_fastforward = m_slowmotion = 0; /* not supported in live mode */

	/* free the timeshift service handler, we need the resources */
	m_service_handler_timeshift.free();

	updateDecoder(true);
}

void eDVBServicePlay::resetTimeshift(int start)
{
	m_cue = 0;
	m_decode_demux = 0;
	m_decoder = 0;
	m_teletext_parser = 0;
	m_rds_decoder = 0;
	m_subtitle_parser = 0;
	m_new_subtitle_stream_connection = 0;
	m_new_subtitle_page_connection = 0;
	m_new_dvb_subtitle_page_connection = 0;
	m_rds_decoder_event_connection = 0;
	m_video_event_connection = 0;
	m_timeshift_changed = 1;
	m_timeshift_file_next.clear();

	if (start)
	{
		m_cue = new eCueSheet();
		m_timeshift_active = 1;
	}
	else
		m_timeshift_active = 0;
}

ePtr<iTsSource> eDVBServicePlay::createTsSource(eServiceReferenceDVB &ref, int packetsize)
{
	/*
	 * NOTE: we cannot use our m_is_stream status, instead we check the reference again.
	 * It could be that createTsSource is called to start a timeshift on a stream,
	 * in which case the ref passed here no longer is a url, but a timeshift file instead.
	 * (but m_is_stream would still be set, because of the ref which was passed to our
	 * constructor)
	 */
	if (ref.path.substr(0, 7) == "http://")
	{
		eHttpStream *f = new eHttpStream();
		f->open(ref.path.c_str());
		return ePtr<iTsSource>(f);
	}
	else
	{
		eRawFile *f = new eRawFile(packetsize);
		f->open(ref.path.c_str());
		return ePtr<iTsSource>(f);
	}
}

void eDVBServicePlay::switchToTimeshift()
{
	if (m_timeshift_active)
		return;

	resetTimeshift(1);

	eServiceReferenceDVB r = (eServiceReferenceDVB&)m_reference;
	r.path = m_timeshift_file;

	m_cue->seekTo(0, -1000);

	ePtr<iTsSource> source = createTsSource(r);
	m_service_handler_timeshift.tuneExt(r, 1, source, m_timeshift_file.c_str(), m_cue, 0, m_dvb_service, eDVBServicePMTHandler::timeshift_playback, false); /* use the decoder demux for everything */

	eDebug("eDVBServicePlay::switchToTimeshift, in pause mode now.");
	pause();
	updateDecoder(true); /* mainly to switch off PCR, and to set pause */
}

void eDVBServicePlay::updateDecoder(bool sendSeekableStateChanged)
{
	int vpid = -1, vpidtype = -1, pcrpid = -1, tpid = -1, achannel = -1, ac3_delay=-1, pcm_delay=-1;
	bool mustPlay = false;

	eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;

	eDVBServicePMTHandler::program program;
	if (h.getProgramInfo(program))
		eDebug("getting program info failed.");
	else
	{
		eDebugNoNewLineStart("have %zd video stream(s)", program.videoStreams.size());
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
		eDebugNoNewLine(", and %zd audio stream(s)", program.audioStreams.size());
		if (!program.audioStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
				i(program.audioStreams.begin());
				i != program.audioStreams.end(); ++i)
			{
				if (i != program.audioStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		pcrpid = program.pcrPid;
		eDebugNoNewLine(", and the pcr pid is %04x", pcrpid);
		tpid = program.textPid;
		eDebugNoNewLineEnd(", and the text pid is %04x", tpid);
	}

	m_have_video_pid = 0;

	if (!m_decoder)
	{
		h.getDecodeDemux(m_decode_demux);
		if (m_decode_demux)
		{
			m_decode_demux->getMPEGDecoder(m_decoder, m_decoder_index);
			if (m_decoder)
				m_decoder->connectVideoEvent(slot(*this, &eDVBServicePlay::video_event), m_video_event_connection);
		}
		if (m_cue)
			m_cue->setDecodingDemux(m_decode_demux, m_decoder);
		mustPlay = true;
	}

	m_timeshift_changed = 0;

	if (m_decoder)
	{
		bool wasSeekable = m_decoder->getVideoProgressive() != -1;
		if (m_dvb_service)
		{
			achannel = m_dvb_service->getCacheEntry(eDVBService::cACHANNEL);
			ac3_delay = m_dvb_service->getCacheEntry(eDVBService::cAC3DELAY);
			pcm_delay = m_dvb_service->getCacheEntry(eDVBService::cPCMDELAY);
		}
		else // subservice
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

		setAC3Delay(ac3_delay == -1 ? 0 : ac3_delay);
		setPCMDelay(pcm_delay == -1 ? 0 : pcm_delay);

		m_decoder->setVideoPID(vpid, vpidtype);
		m_current_video_pid_type = vpidtype;
		m_have_video_pid = (vpid > 0 && vpid < 0x2000);

		if (!(m_is_pvr || m_is_stream || m_timeshift_active || (pcrpid == 0x1FFF)))
			m_decoder->setSyncPCR(pcrpid);
		else
			m_decoder->setSyncPCR(-1);

		selectAudioStream();

		if (m_decoder_index == 0)
		{
			m_decoder->setTextPID(tpid);
		}

		if (vpid > 0 && vpid < 0x2000)
			;
		else
		{
			std::string value;
			bool showRadioBackground = eConfigManager::getConfigBoolValue("config.misc.showradiopic", true);
			std::string radio_pic;
			if (showRadioBackground)
				radio_pic = eConfigManager::getConfigValue("config.misc.radiopic");
			else
				radio_pic = eConfigManager::getConfigValue("config.misc.blackradiopic");
			m_decoder->setRadioPic(radio_pic);
		}

		if (mustPlay)
			m_decoder->play();
		else
			m_decoder->set();

		m_decoder->setAudioChannel(achannel);

		if (mustPlay && m_decode_demux && m_decoder_index == 0)
		{
			m_teletext_parser = new eDVBTeletextParser(m_decode_demux);
			m_teletext_parser->connectNewStream(slot(*this, &eDVBServicePlay::newSubtitleStream), m_new_subtitle_stream_connection);
			m_teletext_parser->connectNewPage(slot(*this, &eDVBServicePlay::newSubtitlePage), m_new_subtitle_page_connection);
			m_subtitle_parser = new eDVBSubtitleParser(m_decode_demux);
			m_subtitle_parser->connectNewPage(slot(*this, &eDVBServicePlay::newDVBSubtitlePage), m_new_dvb_subtitle_page_connection);
			if (m_timeshift_changed)
			{
				struct SubtitleTrack track;
				if (getCachedSubtitle(track) >= 0)
				{
					if (track.type == 0) // dvb
						m_subtitle_parser->start(track.pid, track.page_number, track.magazine_number);
					else if (track.type == 1) // ttx
						m_teletext_parser->setPageAndMagazine(track.page_number, track.magazine_number, track.language_code.c_str());
				}
			}
			m_teletext_parser->start(program.textPid);
		}

		/* don't worry about non-existing services, nor pvr services */
		if (m_dvb_service)
		{
			/* (audio pid will be set in selectAudioTrack) */
			if (vpid >= 0)
			{
				m_dvb_service->setCacheEntry(eDVBService::cVPID, vpid);
				m_dvb_service->setCacheEntry(eDVBService::cVTYPE, vpidtype == eDVBVideo::MPEG2 ? -1 : vpidtype);
			}
			if (pcrpid >= 0) m_dvb_service->setCacheEntry(eDVBService::cPCRPID, pcrpid);
			if (tpid >= 0) m_dvb_service->setCacheEntry(eDVBService::cTPID, tpid);
		}
		if (!sendSeekableStateChanged && (m_decoder->getVideoProgressive() != -1) != wasSeekable)
			sendSeekableStateChanged = true;
	}

	if (sendSeekableStateChanged)
		m_event((iPlayableService*)this, evSeekableStatusChanged);
}

void eDVBServicePlay::loadCuesheet()
{
	std::string filename = m_reference.path + ".cuts";

	m_cue_entries.clear();

	FILE *f = fopen(filename.c_str(), "rb");

	if (f)
	{
		while (1)
		{
			unsigned long long where;
			unsigned int what;

			if (!fread(&where, sizeof(where), 1, f))
				break;
			if (!fread(&what, sizeof(what), 1, f))
				break;

			where = be64toh(where);
			what = ntohl(what);

			if (what > 3)
				break;

			m_cue_entries.insert(cueEntry(where, what));
		}
		fclose(f);
		eDebug("cuts file has %zd entries", m_cue_entries.size());
	} else
		eDebug("cutfile not found!");

	m_cuesheet_changed = 0;
	cutlistToCuesheet();
	m_event((iPlayableService*)this, evCuesheetChanged);
}

void eDVBServicePlay::saveCuesheet()
{
	std::string filename = m_timeshift_enabled ? m_timeshift_file : m_reference.path;

		/* save cuesheet only when main file is accessible. */
	if (::access(filename.c_str(), R_OK) < 0)
		return;

	filename.append(".cuts");

	FILE *f = fopen(filename.c_str(), "wb");

	if (f)
	{
		unsigned long long where;
		int what;

		for (std::multiset<cueEntry>::iterator i(m_cue_entries.begin()); i != m_cue_entries.end(); ++i)
		{
			where = htobe64(i->where);
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

	if ((m_cutlist_enabled & 1) == 0)
	{
		m_cue->commitSpans();
		eDebug("cutlists were disabled");
		return;
	}

	pts_t in = 0, out = 0, length = 0;

	getLength(length);

	std::multiset<cueEntry>::iterator i(m_cue_entries.begin());

	int have_any_span = 0;

	while (1)
	{
		if (i == m_cue_entries.end())
		{
			if (!have_any_span && !in)
				break;
			out = length;
		} else {
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

		if (in < 0)
			in = 0;
		if (out < 0)
			out = 0;
		if (in > length)
			in = length;
		if (out > length)
			out = length;

		if (in < out)
		{
			have_any_span = 1;
			m_cue->addSourceSpan(in, out);
			in = out = 0;
		}

		in = length;

		if (i == m_cue_entries.end())
			break;
	}
	m_cue->commitSpans();
}

RESULT eDVBServicePlay::enableSubtitles(iSubtitleUser *user, SubtitleTrack &track)
{
	if (m_subtitle_widget)
		disableSubtitles();

	if (track.type == 1)  // teletext subtitles
	{
		int page, magazine, pid;
		std::string lang;

		if (!m_teletext_parser)
		{
			eDebug("enable teletext subtitles.. no parser !!!");
			return -1;
		}

		pid = track.pid;
		page = track.page_number;
		magazine = track.magazine_number;
		lang = track.language_code;

		m_subtitle_widget = user;
		m_teletext_parser->setPageAndMagazine(page, magazine, lang.c_str());
		if (m_dvb_service)
		{
			int i, sub = 0;
			for (i=0; i < m_teletext_parser->max_id; i++)
			{
				if (!memcmp(m_teletext_parser->my_country_codes[i], lang.c_str(), 3))
				{
					sub = i;
					break;
				}
			}
			m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE,((pid&0xFFFF)<<16)|((page&0xFF)<<8)|((sub&0x1F)<<3)|(magazine&0x7));
		}
	}
	else if (track.type == 0)
	{
		int pid = 0, composition_page_id = 0, ancillary_page_id = 0;
		if (!m_subtitle_parser)
		{
			eDebug("enable dvb subtitles.. no parser !!!");
			return -1;
		}

		pid = track.pid;
		composition_page_id = track.page_number;
		ancillary_page_id = track.magazine_number;

		m_subtitle_widget = user;
		m_subtitle_parser->start(pid, composition_page_id, ancillary_page_id);
		if (m_dvb_service)
			m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE, ((pid&0xFFFF)<<16)|((composition_page_id&0xFF)<<8)|(ancillary_page_id&0xFF));
	}
	else
		goto error_out;
	return 0;
error_out:
	eDebug("enableSubtitles needs a valid type:\n"
		"for teletext subtitles (0, pid, teletext_page, teletext_magazine)\n"
		"for dvb subtitles (1, pid, composition_page_id, ancillary_page_id)");
	return -1;
}

RESULT eDVBServicePlay::disableSubtitles()
{
	if (m_subtitle_widget) m_subtitle_widget->destroy();
	m_subtitle_widget = 0;
	if (m_subtitle_parser)
	{
		m_subtitle_parser->stop();
		m_dvb_subtitle_pages.clear();
	}
	if (m_teletext_parser)
	{
		m_teletext_parser->setPageAndMagazine(-1, -1, "und");
		m_subtitle_pages.clear();
	}
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cSUBTITLE, 0);
	return 0;
}

RESULT eDVBServicePlay::getCachedSubtitle(struct SubtitleTrack &track)
{
	if (m_dvb_service)
	{
		eDVBServicePMTHandler::program program;
		eDVBServicePMTHandler &h = m_timeshift_active ? m_service_handler_timeshift : m_service_handler;
		if (!h.getProgramInfo(program))
		{
			bool usecache = eConfigManager::getConfigBoolValue("config.autolanguage.subtitle_usecache");
			int stream=program.defaultSubtitleStream;
			int tmp = m_dvb_service->getCacheEntry(eDVBService::cSUBTITLE);

			if (usecache || stream == -1)
			{
				if (tmp != -1 && tmp != 0)
				{
					unsigned int data = (unsigned int)tmp;
					int pid = (data&0xFFFF0000)>>16;
					if (program.textPid == pid) // teletext
						track.type = 1; // type teletext
					else
						track.type = 0; // type dvb
					track.pid = pid; // pid
					track.page_number = (data >> 8) & 0xff; // composition_page / page
					int k = (data >> 3) & 0x1f;
					track.magazine_number = data & 0x7; // ancillary_page / magazine
					track.language_code = m_teletext_parser->my_country_codes[k];
					return 0;
				}
			}
			if (stream != -1 && (tmp != 0 || !usecache))
			{
				if (program.subtitleStreams[stream].subtitling_type == 1)
				{
					track.type = 1; // type teletext
					track.pid = program.subtitleStreams[stream].pid;
					track.page_number = program.subtitleStreams[stream].teletext_page_number & 0xff;
					track.magazine_number = program.subtitleStreams[stream].teletext_magazine_number & 0x07;
					track.language_code = program.subtitleStreams[stream].language_code;
					return 0;
				}
				else
				{
					track.type = 0; // type dvb
					track.pid = program.subtitleStreams[stream].pid;
					track.page_number = program.subtitleStreams[stream].composition_page_id;
					track.magazine_number = program.subtitleStreams[stream].ancillary_page_id;
					track.language_code = program.subtitleStreams[stream].language_code;
					return 0;
				}
			}
		}
	}
	return -1;
}

RESULT eDVBServicePlay::getSubtitleList(std::vector<SubtitleTrack> &subtitlelist)
{
	if (!m_teletext_parser)
		return -1;

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
			struct SubtitleTrack track;
			switch(it->subtitling_type)
			{
				case 0x01: // ebu teletext subtitles
				{
					int page_number = it->teletext_page_number & 0xFF;
					int magazine_number = it->teletext_magazine_number & 7;
					int hash = magazine_number << 8 | page_number;
					if (added_ttx_pages.find(hash) == added_ttx_pages.end())
					{
						track.type = 1;
						track.pid = it->pid;
						track.page_number = page_number;
						track.magazine_number = magazine_number;
						track.language_code = it->language_code;
						subtitlelist.push_back(track);
						added_ttx_pages.insert(hash);
					}
					break;
				}
				case 0x10 ... 0x13:
				case 0x20 ... 0x23: // dvb subtitles
				{
					track.type = 0;
					track.pid = it->pid;
					track.page_number = it->composition_page_id;
					track.magazine_number = it->ancillary_page_id;
					track.language_code = it->language_code;
					subtitlelist.push_back(track);
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
			struct SubtitleTrack track;
			track.type = 1;
			track.pid = it->pid;
			track.page_number = page_number;
			track.magazine_number = magazine_number;
			track.language_code = "und";
			subtitlelist.push_back(track);
		}
	}

	return 0;
}

void eDVBServicePlay::newSubtitleStream()
{
	m_event((iPlayableService*)this, evUpdatedInfo);
}

void eDVBServicePlay::newSubtitlePage(const eDVBTeletextSubtitlePage &page)
{
	if (m_subtitle_widget)
	{
		int subtitledelay = 0;
		pts_t pts;
		m_decoder->getPTS(0, pts);
		if (m_is_pvr || m_timeshift_enabled)
		{
			eDebug("Subtitle in recording/timeshift");
			subtitledelay = eConfigManager::getConfigIntValue("config.subtitles.subtitle_noPTSrecordingdelay", 315000);
		}
		else
		{
			/* check the setting for subtitle delay in live playback, either with pts, or without pts */
			subtitledelay = eConfigManager::getConfigIntValue("config.subtitles.subtitle_bad_timing_delay", 0);
		}

		// eDebug("Subtitle get  TTX have_pts=%d pvr=%d timeshift=%d page.pts=%lld pts=%lld delay=%d", page.m_have_pts, m_is_pvr, m_timeshift_enabled, page.m_pts, pts, subtitledelay);
		eDVBTeletextSubtitlePage tmppage = page;
		tmppage.m_have_pts = true;

		if (abs(tmppage.m_pts - pts) > 20*90000)
			tmppage.m_pts = pts; // fix abnormal pts diffs

		tmppage.m_pts += subtitledelay;
		m_subtitle_pages.push_back(tmppage);

		checkSubtitleTiming();
	}
}

void eDVBServicePlay::checkSubtitleTiming()
{
	pts_t pos = 0;
//	eDebug("checkSubtitleTiming");
	if (!m_subtitle_widget)
		return;
	if (m_subtitle_pages.empty() && m_dvb_subtitle_pages.empty())
	{
		return;
	}
	if (m_decoder)
	{
		m_decoder->getPTS(0, pos);
	}

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

		int diff = show_time - pos;
//		eDebug("Subtitle show %d page.pts=%lld pts=%lld diff=%d", type, show_time, pos, diff);

		if (diff < 20*90 || diff > 1800000)
		{
			if (type == TELETEXT)
			{
				m_subtitle_widget->setPage(page);
				m_subtitle_pages.pop_front();
			}
			else
			{
				m_subtitle_widget->setPage(dvb_page);
				m_dvb_subtitle_pages.pop_front();
			}
		} else
		{
			m_subtitle_sync_timer->start(diff / 90, 1);
			break;
		}
	}
}

void eDVBServicePlay::newDVBSubtitlePage(const eDVBSubtitlePage &p)
{
	if (m_subtitle_widget)
	{
		pts_t pos = 0;
		if (m_decoder)
			m_decoder->getPTS(0, pos);
		if ( abs(pos-p.m_show_time)>1800000 && (m_is_pvr || m_timeshift_enabled))
		{
			eDebug("Subtitle without PTS and recording");
			int subtitledelay = eConfigManager::getConfigIntValue("config.subtitles.subtitle_noPTSrecordingdelay", 315000);

			eDVBSubtitlePage tmppage;
			tmppage = p;
			tmppage.m_show_time = pos + subtitledelay;
			m_dvb_subtitle_pages.push_back(tmppage);
		}
		else
		{
			int subtitledelay = eConfigManager::getConfigIntValue("config.subtitles.subtitle_bad_timing_delay", 0);
			if (subtitledelay != 0)
			{
				eDVBSubtitlePage tmppage;
				tmppage = p;
				tmppage.m_show_time += subtitledelay;
				m_dvb_subtitle_pages.push_back(tmppage);
			}
			else
				m_dvb_subtitle_pages.push_back(p);
		}
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
	{
		m_decoder->setAC3Delay(delay + eConfigManager::getConfigIntValue("config.av.generalAC3delay"));
	}
}

void eDVBServicePlay::setPCMDelay(int delay)
{
	if (m_dvb_service)
		m_dvb_service->setCacheEntry(eDVBService::cPCMDELAY, delay ? delay : -1);
	if (m_decoder)
	{
		m_decoder->setPCMDelay(delay + eConfigManager::getConfigIntValue("config.av.generalPCMdelay"));
	}
}

void eDVBServicePlay::video_event(struct iTSMPEGDecoder::videoEvent event)
{
	switch(event.type) {
		case iTSMPEGDecoder::videoEvent::eventSizeChanged:
			m_event((iPlayableService*)this, evVideoSizeChanged);
			break;
		case iTSMPEGDecoder::videoEvent::eventFrameRateChanged:
			m_event((iPlayableService*)this, evVideoFramerateChanged);
			break;
		case iTSMPEGDecoder::videoEvent::eventProgressiveChanged:
			m_event((iPlayableService*)this, evVideoProgressiveChanged);
			break;
		default:
			break;
	}
}

RESULT eDVBServicePlay::stream(ePtr<iStreamableService> &ptr)
{
	ptr = this;
	return 0;
}

ePtr<iStreamData> eDVBServicePlay::getStreamingData()
{
	ePtr<iStreamData> retval;
	eDVBServicePMTHandler::program program;
	if (!m_service_handler.getProgramInfo(program))
	{
		retval = new eDVBServicePMTHandler::eStreamData(program);
	}
	return retval;
}


DEFINE_REF(eDVBServicePlay)

ePtr<iDVBTransponderData> eDVBService::getTransponderData(const eServiceReference &ref)
{
	return eStaticServiceDVBInformation().getTransponderData(ref);
}

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
