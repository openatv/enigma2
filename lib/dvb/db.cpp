#include <errno.h>
#include <unistd.h>
#include <lib/dvb/db.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/epgcache.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <xmlccwrap/xmlccwrap.h>
#include <dvbsi++/service_description_section.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/satellite_delivery_system_descriptor.h>

DEFINE_REF(eDVBService);

RESULT eBouquet::addService(const eServiceReference &ref, eServiceReference before)
{
	list::iterator it =
		std::find(m_services.begin(), m_services.end(), ref);
	if ( it != m_services.end() )
		return -1;
	if (before.valid())
	{
		it = std::find(m_services.begin(), m_services.end(), before);
		m_services.insert(it, ref);
	}
	else
		m_services.push_back(ref);
	return 0;
}

RESULT eBouquet::removeService(const eServiceReference &ref)
{
	list::iterator it =
		std::find(m_services.begin(), m_services.end(), ref);
	if ( it == m_services.end() )
		return -1;
	m_services.erase(it);
	return 0;
}

RESULT eBouquet::moveService(const eServiceReference &ref, unsigned int pos)
{
	if ( pos < 0 || pos >= m_services.size() )
		return -1;
	++pos;
	list::iterator source=m_services.end();
	list::iterator dest=m_services.end();
	bool forward = false;
	for (list::iterator it(m_services.begin()); it != m_services.end(); ++it)
	{
		if (dest == m_services.end() && !--pos)
			dest = it;
		if (*it == ref)
		{
			source = it;
			forward = pos>0;
		}
		if (dest != m_services.end() && source != m_services.end())
			break;
	}
	if (dest == m_services.end() || source == m_services.end() || source == dest)
		return -1;
	while (source != dest)
	{
		if (forward)
			std::iter_swap(source++, source);
		else
			std::iter_swap(source--, source);
	}
	return 0;
}

RESULT eBouquet::flushChanges()
{
	std::string filename = eEnv::resolve("${sysconfdir}/enigma2/" + m_filename);
	FILE *f = fopen((filename + ".writing").c_str(), "w");
	if (!f)
		return -1;
	if ( fprintf(f, "#NAME %s\r\n", m_bouquet_name.c_str()) < 0 )
		goto err;
	for (list::iterator i(m_services.begin()); i != m_services.end(); ++i)
	{
		eServiceReference tmp = *i;
		std::string str = tmp.path;
		if ( fprintf(f, "#SERVICE %s\r\n", tmp.toString().c_str()) < 0 )
			goto err;
		if ( i->name.length() )
			if ( fprintf(f, "#DESCRIPTION %s\r\n", i->name.c_str()) < 0 )
				goto err;
	}
	fsync(fileno(f));
	fclose(f);
	rename((filename + ".writing").c_str(), filename.c_str());
	return 0;
err:
	fclose(f);
	eDebug("couldn't write file %s", m_filename.c_str());
	return -1;
}

RESULT eBouquet::setListName(const std::string &name)
{
	m_bouquet_name = name;
	return 0;
}

eDVBService::eDVBService()
	:m_cache(0), m_flags(0)
{
}

eDVBService::~eDVBService()
{
	delete [] m_cache;
}

eDVBService &eDVBService::operator=(const eDVBService &s)
{
	m_service_name = s.m_service_name;
	m_service_name_sort = s.m_service_name_sort;
	m_provider_name = s.m_provider_name;
	m_flags = s.m_flags;
	m_ca = s.m_ca;
	copyCache(s.m_cache);
	return *this;
}

void eDVBService::genSortName()
{
	size_t start = m_service_name.find_first_not_of(' ');
	if (start != std::string::npos)
	{
		/* strip leading spaces */
		m_service_name_sort = m_service_name.substr(start);
		/* remove UTF-8 */
		m_service_name_sort = removeDVBChars(m_service_name_sort);
		/* convert to uppercase */
		makeUpper(m_service_name_sort);
	}

	if (m_service_name_sort.empty())
	{
		/* put unnamed services at the end, not at the beginning. */
		m_service_name_sort = "\xFF";
	}
}

RESULT eDVBService::getName(const eServiceReference &ref, std::string &name)
{
	if (!ref.name.empty())
		name = ref.name; // use renamed service name..
	else if (!m_service_name.empty())
		name = m_service_name;
	else
		name = "(...)";
	return 0;
}

RESULT eDVBService::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &ptr, time_t start_time)
{
	return eEPGCache::getInstance()->lookupEventTime(ref, start_time, ptr);
}

int eDVBService::isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate)
{
	ePtr<eDVBResourceManager> res_mgr;
	if ( eDVBResourceManager::getInstance( res_mgr ) )
		eDebug("isPlayble... no res manager!!");
	else
	{
		eDVBChannelID chid, chid_ignore;
		((const eServiceReferenceDVB&)ref).getChannelID(chid);
		((const eServiceReferenceDVB&)ignore).getChannelID(chid_ignore);
		return res_mgr->canAllocateChannel(chid, chid_ignore, simulate);
	}
	return 0;
}

int eDVBService::checkFilter(const eServiceReferenceDVB &ref, const eDVBChannelQuery &query)
{
	int res = 0;
	switch (query.m_type)
	{
	case eDVBChannelQuery::tName:
		res = m_service_name_sort == query.m_string;
		break;
	case eDVBChannelQuery::tProvider:
		if (query.m_string == "Unknown" && m_provider_name.empty())
			res = 1;
		else
			res = m_provider_name == query.m_string;
		break;
	case eDVBChannelQuery::tType:
	{
		int service_type = ref.getServiceType();
		if (query.m_int == 1) // TV Service
		{
			// Hack for dish network
			int onid = ref.getOriginalNetworkID().get();
			if (onid >= 0x1001 && onid <= 0x100b)
			{
				static int dish_tv_types[] = { 128, 133, 137, 140, 144, 145, 150, 154, 163, 164, 165, 166, 167, 168, 173, 174 };
				static size_t dish_tv_num_types = sizeof(dish_tv_types) / sizeof(int);
				if (std::binary_search(dish_tv_types, dish_tv_types + dish_tv_num_types, service_type))
					return true;
			}
		}
		res = service_type == query.m_int;
		break;
	}
	case eDVBChannelQuery::tBouquet:
		res = 0;
		break;
	case eDVBChannelQuery::tSatellitePosition:
		res = ((unsigned int)ref.getDVBNamespace().get())>>16 == (unsigned int)query.m_int;
		break;
	case eDVBChannelQuery::tFlags:
		res = (m_flags & query.m_int) == query.m_int;
		break;
	case eDVBChannelQuery::tChannelID:
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = chid == query.m_channelid;
		break;
	}
	case eDVBChannelQuery::tAND:
		res = checkFilter(ref, *query.m_p1) && checkFilter(ref, *query.m_p2);
		break;
	case eDVBChannelQuery::tOR:
		res = checkFilter(ref, *query.m_p1) || checkFilter(ref, *query.m_p2);
		break;
	case eDVBChannelQuery::tAny:
		res = 1;
		break;
	}

	if (query.m_inverse)
		return !res;
	else
		return res;
}

bool eDVBService::cacheEmpty()
{
	if (m_cache)
		for (int i=0; i < cacheMax; ++i)
			if (m_cache[i] != -1)
				return false;
	return true;
}

void eDVBService::initCache()
{
	m_cache = new int[cacheMax];
	memset(m_cache, -1, sizeof(int) * cacheMax);
}

void eDVBService::copyCache(int *source)
{
	if (source)
	{
		if (!m_cache)
			m_cache = new int[cacheMax];
		memcpy(m_cache, source, cacheMax * sizeof(int));
	}
	else
	{
		delete [] m_cache;
		m_cache = 0;
	}
}

int eDVBService::getCacheEntry(cacheID id)
{
	if (id >= cacheMax || !m_cache)
		return -1;
	return m_cache[id];
}

void eDVBService::setCacheEntry(cacheID id, int pid)
{
	if (!m_cache)
		initCache();
	if (id < cacheMax)
		m_cache[id] = pid;
}

DEFINE_REF(eDVBDB);

void eDVBDB::reloadServicelist()
{
	loadServicelist(eEnv::resolve("${sysconfdir}/enigma2/lamedb").c_str());
}

void eDVBDB::parseServiceData(ePtr<eDVBService> s, std::string str)
{
	while ((!str.empty()) && str[1]==':') // new: p:, f:, c:%02d...
	{
		size_t c=str.find(',');
		char p=str[0];
		std::string v;
		if (c == std::string::npos)
		{
			v=str.substr(2);
			str="";
		} else
		{
			v=str.substr(2, c-2);
			str=str.substr(c+1);
		}
//		eDebug("%c ... %s", p, v.c_str());
		if (p == 'p')
			s->m_provider_name=v;
		else if (p == 'f')
		{
			sscanf(v.c_str(), "%x", &s->m_flags);
		} else if (p == 'c')
		{
			int cid, val;
			sscanf(v.c_str(), "%02d%x", &cid, &val);
			s->setCacheEntry((eDVBService::cacheID)cid,val);
		} else if (p == 'C')
		{
			int val;
			sscanf(v.c_str(), "%04x", &val);
			s->m_ca.push_back((uint16_t)val);
		}
	}
}

	/* THIS CODE IS BAD. it should be replaced by somethine better. */
void eDVBDB::loadServicelist(const char *file)
{
	eDebug("---- opening lame channel db");
	FILE *f=fopen(file, "rt");
	if (!f) {
		eDebug("can't open %s: %m", file);
		return;
	}

	char line[256];
	int version=3;
	if ((!fgets(line, 256, f)) || sscanf(line, "eDVB services /%d/", &version) != 1)
	{
		eDebug("not a valid servicefile");
		fclose(f);
		return;
	}
	eDebug("reading services (version %d)", version);
	if ((!fgets(line, 256, f)) || strcmp(line, "transponders\n"))
	{
		eDebug("services invalid, no transponders");
		fclose(f);
		return;
	}

	// clear all transponders

	while (!feof(f))
	{
		if (!fgets(line, 256, f))
			break;
		if (!strcmp(line, "end\n"))
			break;
		int dvb_namespace=-1, transport_stream_id=-1, original_network_id=-1;
		sscanf(line, "%x:%x:%x", &dvb_namespace, &transport_stream_id, &original_network_id);
		if (original_network_id == -1)
			continue;
		eDVBChannelID channelid = eDVBChannelID(
			eDVBNamespace(dvb_namespace),
			eTransportStreamID(transport_stream_id),
			eOriginalNetworkID(original_network_id));

		ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
		while (!feof(f))
		{
			fgets(line, 256, f);
			if (!strcmp(line, "/\n"))
				break;
			if (line[1]=='s')
			{
				eDVBFrontendParametersSatellite sat;
				int frequency, symbol_rate, polarisation, fec, orbital_position, inversion,
					flags=0,
					system=eDVBFrontendParametersSatellite::System_DVB_S,
					modulation=eDVBFrontendParametersSatellite::Modulation_QPSK,
					rolloff=eDVBFrontendParametersSatellite::RollOff_alpha_0_35,
					pilot=eDVBFrontendParametersSatellite::Pilot_Unknown;
				if (version == 3)
					sscanf(line+3, "%d:%d:%d:%d:%d:%d:%d:%d:%d:%d", &frequency, &symbol_rate, &polarisation, &fec, &orbital_position, &inversion, &system, &modulation, &rolloff, &pilot);
				else
					sscanf(line+3, "%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d", &frequency, &symbol_rate, &polarisation, &fec, &orbital_position, &inversion, &flags, &system, &modulation, &rolloff, &pilot);
				sat.frequency = frequency;
				sat.symbol_rate = symbol_rate;
				sat.polarisation = polarisation;
				sat.fec = fec;
				sat.orbital_position =
					orbital_position < 0 ? orbital_position + 3600 : orbital_position;
				sat.inversion = inversion;
				sat.system = system;
				sat.modulation = modulation;
				sat.rolloff = rolloff;
				sat.pilot = pilot;
				feparm->setDVBS(sat);
				feparm->setFlags(flags);
			} else if (line[1]=='t')
			{
				eDVBFrontendParametersTerrestrial ter;
				int frequency, bandwidth, code_rate_HP, code_rate_LP, modulation, transmission_mode, guard_interval, hierarchy, inversion, flags=0;
				int system = eDVBFrontendParametersTerrestrial::System_DVB_T;
				sscanf(line+3, "%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d", &frequency, &bandwidth, &code_rate_HP, &code_rate_LP, &modulation, &transmission_mode, &guard_interval, &hierarchy, &inversion, &flags, &system);
				ter.frequency = frequency;
				switch (bandwidth)
				{
				case eDVBFrontendParametersTerrestrial::Bandwidth_8MHz: ter.bandwidth = 8000000; break;
				case eDVBFrontendParametersTerrestrial::Bandwidth_7MHz: ter.bandwidth = 7000000; break;
				case eDVBFrontendParametersTerrestrial::Bandwidth_6MHz: ter.bandwidth = 6000000; break;
				default:
				case eDVBFrontendParametersTerrestrial::Bandwidth_Auto: ter.bandwidth = 0; break;
				case eDVBFrontendParametersTerrestrial::Bandwidth_5MHz: ter.bandwidth = 5000000; break;
				case eDVBFrontendParametersTerrestrial::Bandwidth_1_712MHz: ter.bandwidth = 1712000; break;
				case eDVBFrontendParametersTerrestrial::Bandwidth_10MHz: ter.bandwidth = 10000000; break;
				}
				ter.code_rate_HP = code_rate_HP;
				ter.code_rate_LP = code_rate_LP;
				ter.modulation = modulation;
				ter.transmission_mode = transmission_mode;
				ter.guard_interval = guard_interval;
				ter.hierarchy = hierarchy;
				ter.inversion = inversion;
				ter.system = system;
				feparm->setDVBT(ter);
				feparm->setFlags(flags);
			} else if (line[1]=='c')
			{
				eDVBFrontendParametersCable cab;
				int frequency, symbol_rate,
					inversion=eDVBFrontendParametersCable::Inversion_Unknown,
					modulation=eDVBFrontendParametersCable::Modulation_Auto,
					fec_inner=eDVBFrontendParametersCable::FEC_Auto,
					system = eDVBFrontendParametersCable::System_DVB_C_ANNEX_A,
					flags=0;
				sscanf(line+3, "%d:%d:%d:%d:%d:%d", &frequency, &symbol_rate, &inversion, &modulation, &fec_inner, &flags, &system);
				cab.frequency = frequency;
				cab.fec_inner = fec_inner;
				cab.inversion = inversion;
				cab.symbol_rate = symbol_rate;
				cab.modulation = modulation;
				cab.system = system;
				feparm->setDVBC(cab);
				feparm->setFlags(flags);
			}
		}
		addChannelToList(channelid, feparm);
	}

	if ((!fgets(line, 256, f)) || strcmp(line, "services\n"))
	{
		eDebug("services invalid, no services");
		return;
	}

	// clear all services

	int count=0;

	size_t linebufsize = 256;
	char *linebuf = (char*)malloc(linebufsize);
	while (!feof(f))
	{
		int len;
		if (getline(&linebuf, &linebufsize, f) <= 0)
			break;
		if (!strcmp(linebuf, "end\n"))
			break;

		int service_id=-1, dvb_namespace, transport_stream_id=-1, original_network_id=-1, service_type=-1, service_number=-1;
		sscanf(linebuf, "%x:%x:%x:%x:%d:%d", &service_id, &dvb_namespace, &transport_stream_id, &original_network_id, &service_type, &service_number);
		if (service_number == -1)
			continue;
		ePtr<eDVBService> s = new eDVBService;
		eServiceReferenceDVB ref =
						eServiceReferenceDVB(
						eDVBNamespace(dvb_namespace),
						eTransportStreamID(transport_stream_id),
						eOriginalNetworkID(original_network_id),
						eServiceID(service_id),
						service_type);
		count++;
		if ((len = getline(&linebuf, &linebufsize, f)) > 0)
		{
			/* strip newline */
			linebuf[--len] = 0;
			s->m_service_name = linebuf;
		}
		s->genSortName();

		if ((len = getline(&linebuf, &linebufsize, f)) > 0)
		{
			/* strip newline */
			linebuf[--len] = 0;
			if (linebuf[1]!=':')	// old ... (only service_provider)
				s->m_provider_name=linebuf;
			else
				parseServiceData(s, linebuf);
		}
		addService(ref, s);
	}
	free(linebuf);

	eDebug("loaded %d services", count);

	fclose(f);
}

void eDVBDB::saveServicelist(const char *file)
{
	eDebug("---- saving lame channel db");
	std::string filename = file;
	FILE *f = fopen((filename + ".writing").c_str(), "w");
	int channels=0, services=0;
	if (!f)
		eFatal("couldn't save lame channel db!");
	fprintf(f, "eDVB services /4/\n");
	fprintf(f, "transponders\n");
	for (std::map<eDVBChannelID, channel>::const_iterator i(m_channels.begin());
			i != m_channels.end(); ++i)
	{
		const eDVBChannelID &chid = i->first;
		const channel &ch = i->second;

		fprintf(f, "%08x:%04x:%04x\n", chid.dvbnamespace.get(),
				chid.transport_stream_id.get(), chid.original_network_id.get());
		eDVBFrontendParametersSatellite sat;
		eDVBFrontendParametersTerrestrial ter;
		eDVBFrontendParametersCable cab;
		unsigned int flags;  // flagOnlyFree yet..
		ch.m_frontendParameters->getFlags(flags);
		if (!ch.m_frontendParameters->getDVBS(sat))
		{
			if (sat.system == eDVBFrontendParametersSatellite::System_DVB_S2)
			{
				fprintf(f, "\ts %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d\n",
					sat.frequency, sat.symbol_rate,
					sat.polarisation, sat.fec,
					sat.orbital_position > 1800 ? sat.orbital_position - 3600 : sat.orbital_position,
					sat.inversion,
					flags,
					sat.system,
					sat.modulation,
					sat.rolloff,
					sat.pilot);
			}
			else
			{
				fprintf(f, "\ts %d:%d:%d:%d:%d:%d:%d\n",
					sat.frequency, sat.symbol_rate,
					sat.polarisation, sat.fec,
					sat.orbital_position > 1800 ? sat.orbital_position - 3600 : sat.orbital_position,
					sat.inversion, flags);
			}
		}
		else if (!ch.m_frontendParameters->getDVBT(ter))
		{
			int bandwidth;
			switch (ter.bandwidth)
			{
			case 8000000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_8MHz; break;
			case 7000000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_7MHz; break;
			case 6000000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_6MHz; break;
			default:
			case 0: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_Auto; break;
			case 5000000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_5MHz; break;
			case 1712000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_1_712MHz; break;
			case 10000000: bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_10MHz; break;
			}
			fprintf(f, "\tt %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d\n",
				ter.frequency, bandwidth, ter.code_rate_HP,
				ter.code_rate_LP, ter.modulation, ter.transmission_mode,
				ter.guard_interval, ter.hierarchy, ter.inversion, flags, ter.system);
		}
		else if (!ch.m_frontendParameters->getDVBC(cab))
		{
			fprintf(f, "\tc %d:%d:%d:%d:%d:%d\n",
				cab.frequency, cab.symbol_rate, cab.inversion, cab.modulation, cab.fec_inner, flags);
		}
		fprintf(f, "/\n");
		channels++;
	}
	fprintf(f, "end\nservices\n");

	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator i(m_services.begin());
		i != m_services.end(); ++i)
	{
		const eServiceReferenceDVB &s = i->first;
		fprintf(f, "%04x:%08x:%04x:%04x:%d:%d\n",
				s.getServiceID().get(), s.getDVBNamespace().get(),
				s.getTransportStreamID().get(),s.getOriginalNetworkID().get(),
				s.getServiceType(),
				0);

		fprintf(f, "%s\n", i->second->m_service_name.c_str());

		fprintf(f, "p:%s", i->second->m_provider_name.c_str());

		// write cached pids
		for (int x=0; x < eDVBService::cacheMax; ++x)
		{
			int entry = i->second->getCacheEntry((eDVBService::cacheID)x);
			if (entry != -1)
				fprintf(f, ",c:%02d%04x", x, entry);
		}

		// write cached ca pids
		for (CAID_LIST::const_iterator ca(i->second->m_ca.begin());
			ca != i->second->m_ca.end(); ++ca)
			fprintf(f, ",C:%04x", *ca);

		if (i->second->m_flags)
			fprintf(f, ",f:%x", i->second->m_flags);

		fprintf(f, "\n");
		services++;
	}
	fprintf(f, "end\nHave a lot of bugs!\n");
	eDebug("saved %d channels and %d services!", channels, services);
	fsync(fileno(f));
	fclose(f);
	rename((filename + ".writing").c_str(), filename.c_str());
}

void eDVBDB::saveServicelist()
{
	saveServicelist(eEnv::resolve("${sysconfdir}/enigma2/lamedb").c_str());
}

void eDVBDB::loadBouquet(const char *path)
{
	std::string bouquet_name = path;
	if (!bouquet_name.length())
	{
		eDebug("Bouquet load failed.. no path given..");
		return;
	}
	size_t pos = bouquet_name.rfind('/');
	if ( pos != std::string::npos )
		bouquet_name.erase(0, pos+1);
	if (bouquet_name.empty())
	{
		eDebug("Bouquet load failed.. no filename given..");
		return;
	}
	eBouquet &bouquet = m_bouquets[bouquet_name];
	bouquet.m_filename = bouquet_name;
	std::list<eServiceReference> &list = bouquet.m_services;
	list.clear();

	std::string p = eEnv::resolve("${sysconfdir}/enigma2/");
	p+=path;
	eDebug("loading bouquet... %s", p.c_str());
	FILE *fp=fopen(p.c_str(), "rt");
	if (!fp)
	{
		eDebug("can't open %s: %m", p.c_str());
		if (!strcmp(path, "bouquets.tv"))
		{
			eDebug("recreate bouquets.tv");
			bouquet.m_bouquet_name="Bouquets (TV)";
			bouquet.flushChanges();
		}
		else if (!strcmp(path, "bouquets.radio"))
		{
			eDebug("recreate bouquets.radio");
			bouquet.m_bouquet_name="Bouquets (Radio)";
			bouquet.flushChanges();
		}
		return;
	}
	int entries=0;
	size_t linesize = 256;
	char *line = (char*)malloc(linesize);
	bool read_descr=false;
	eServiceReference *e = NULL;
	while (1)
	{
		int len;
		if ((len = getline(&line, &linesize, fp)) < 2) break;
		/* strip newline */
		line[--len] = 0;
		/* strip carriage return (when found) */
		if (line[len - 1] == '\r') line[--len] = 0;
		if (!strncmp(line, "#SERVICE", 8))
		{
			int offs = line[8] == ':' ? 10 : 9;
			eServiceReference tmp(line+offs);
			if ( tmp.flags&eServiceReference::canDescent )
			{
				size_t pos = tmp.path.rfind('/');
				char buf[256];
				std::string path = tmp.path;
				if ( pos != std::string::npos )
					path.erase(0, pos+1);
				if (path.empty())
				{
					eDebug("Bouquet load failed.. no filename given..");
					continue;
				}
				pos = path.find("FROM BOUQUET ");
				if (pos != std::string::npos)
				{
					char endchr = path[pos+13];
					if (endchr != '"')
					{
						eDebug("ignore invalid bouquet '%s' (only \" are allowed)",
							tmp.toString().c_str());
						continue;
					}
					char *beg = &path[pos+14];
					char *end = strchr(beg, endchr);
					path.assign(beg, end - beg);
				}
				else
				{
					snprintf(buf, 256, "FROM BOUQUET \"%s\" ORDER BY bouquet", path.c_str());
					tmp.path = buf;
				}
				loadBouquet(path.c_str());
			}
			list.push_back(tmp);
			e = &list.back();
			read_descr=true;
			++entries;
		}
		else if (read_descr && !strncmp(line, "#DESCRIPTION", 12))
		{
			int offs = line[12] == ':' ? 14 : 13;
			e->name = line+offs;
			read_descr=false;
		}
		else if (!strncmp(line, "#NAME ", 6))
			bouquet.m_bouquet_name=line+6;
	}
	free(line);
	fclose(fp);
	eDebug("%d entries in Bouquet %s", entries, bouquet_name.c_str());
}

void eDVBDB::reloadBouquets()
{
	m_bouquets.clear();
	loadBouquet("bouquets.tv");
	loadBouquet("bouquets.radio");
// create default bouquets when missing
	if ( m_bouquets.find("userbouquet.favourites.tv") == m_bouquets.end() )
	{
		eBouquet &b = m_bouquets["userbouquet.favourites.tv"];
		b.m_filename = "userbouquet.favourites.tv";
		b.m_bouquet_name = "Favourites (TV)";
		b.flushChanges();
		eServiceReference ref;
		ref.type=1;
		ref.flags=7;
		ref.data[0]=1;
		ref.path="FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet";
		eBouquet &parent = m_bouquets["bouquets.tv"];
		parent.m_services.push_back(ref);
		parent.flushChanges();
	}
	if ( m_bouquets.find("userbouquet.favourites.radio") == m_bouquets.end() )
	{
		eBouquet &b = m_bouquets["userbouquet.favourites.radio"];
		b.m_filename = "userbouquet.favourites.radio";
		b.m_bouquet_name = "Favourites (Radio)";
		b.flushChanges();
		eServiceReference ref;
		ref.type=1;
		ref.flags=7;
		ref.data[0]=2;
		ref.path="FROM BOUQUET \"userbouquet.favourites.radio\" ORDER BY bouquet";
		eBouquet &parent = m_bouquets["bouquets.radio"];
		parent.m_services.push_back(ref);
		parent.flushChanges();
	}
}

eDVBDB *eDVBDB::instance;

using namespace xmlcc;

eDVBDB::eDVBDB()
{
	instance = this;
	reloadServicelist();
}

PyObject *eDVBDB::readSatellites(ePyObject sat_list, ePyObject sat_dict, ePyObject tp_dict)
{
	if (!PyDict_Check(tp_dict)) {
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 2 is not a python dict");
		return NULL;
	}
	else if (!PyDict_Check(sat_dict))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 1 is not a python dict");
		return NULL;
	}
	else if (!PyList_Check(sat_list))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 0 is not a python list");
		return NULL;
	}
	XMLTree tree;
	const char* satellitesFilename = "/etc/enigma2/satellites.xml";
	struct stat stat_dummy;
	if (stat(satellitesFilename, &stat_dummy) != 0)
	{
		satellitesFilename = "/etc/tuxbox/satellites.xml";
	}
	tree.setFilename(satellitesFilename);
	tree.read();
	Element *root = tree.getRoot();
	if (!root)
	{
		eDebug("couldn't open /etc/tuxbox/satellites.xml!!");
		Py_INCREF(Py_False);
		return Py_False;
	}
	int tmp, *dest = NULL,
		modulation, system, freq, sr, pol, fec, inv, pilot, rolloff, tsid, onid;
	char *end_ptr;
	const Attribute *at;
	std::string name;
	const ElementList &root_elements = root->getElementList();
	for (ElementConstIterator it(root_elements.begin()); it != root_elements.end(); ++it)
	{
//		eDebug("element: %s", (*it)->name().c_str());
		const Element *el = *it;
		const ElementList &sat_elements = el->getElementList();
		const AttributeList &sat_attributes = el->getAttributeList();
		ePyObject sat_name;
		ePyObject sat_pos;
		ePyObject sat_flags;
		for (AttributeConstIterator it(sat_attributes.begin()); it != sat_attributes.end(); ++it)
		{
//			eDebug("\tattr: %s", at->name().c_str());
			at = *it;
			name = at->name();
			if (name == "name")
				sat_name = PyString_FromString(at->value().c_str());
			else if (name == "flags")
			{
				tmp = strtol(at->value().c_str(), &end_ptr, 10);
				if (!*end_ptr)
					sat_flags = PyInt_FromLong(tmp);
			}
			else if (name == "position")
			{
				tmp = strtol(at->value().c_str(), &end_ptr, 10);
				if (!*end_ptr)
				{
					if (tmp < 0)
						tmp = 3600 + tmp;
					sat_pos = PyInt_FromLong(tmp);
				}
			}
		}
		if (sat_pos && sat_name)
		{
			ePyObject tplist = PyList_New(0);
			ePyObject tuple = PyTuple_New(3);
			if (!sat_flags)
				sat_flags = PyInt_FromLong(0);
			PyTuple_SET_ITEM(tuple, 0, sat_pos);
			PyTuple_SET_ITEM(tuple, 1, sat_name);
			PyTuple_SET_ITEM(tuple, 2, sat_flags);
			PyList_Append(sat_list, tuple);
			Py_DECREF(tuple);
			PyDict_SetItem(sat_dict, sat_pos, sat_name);
			PyDict_SetItem(tp_dict, sat_pos, tplist);
			for (ElementConstIterator it(sat_elements.begin()); it != sat_elements.end(); ++it)
			{
				//eDebug("\telement: %s", (*it)->name().c_str());
				const AttributeList &tp_attributes = (*it)->getAttributeList();
				AttributeConstIterator end = tp_attributes.end();
				modulation = eDVBFrontendParametersSatellite::Modulation_QPSK;
				system = eDVBFrontendParametersSatellite::System_DVB_S;
				freq = 0;
				sr = 0;
				pol = -1;
				fec = eDVBFrontendParametersSatellite::FEC_Auto;
				inv = eDVBFrontendParametersSatellite::Inversion_Unknown;
				pilot = eDVBFrontendParametersSatellite::Pilot_Unknown;
				rolloff = eDVBFrontendParametersSatellite::RollOff_alpha_0_35;
				tsid = -1;
				onid = -1;

				for (AttributeConstIterator it(tp_attributes.begin()); it != end; ++it)
				{
					at = *it;
					//eDebug("\t\tattr: %s", at->name().c_str());
					name = at->name();
					if (name == "modulation") dest = &modulation;
					else if (name == "system") dest = &system;
					else if (name == "frequency") dest = &freq;
					else if (name == "symbol_rate") dest = &sr;
					else if (name == "polarization") dest = &pol;
					else if (name == "fec_inner") dest = &fec;
					else if (name == "inversion") dest = &inv;
					else if (name == "rolloff") dest = &rolloff;
					else if (name == "pilot") dest = &pilot;
					else if (name == "tsid") dest = &tsid;
					else if (name == "onid") dest = &onid;
					else continue;
					if (dest)
					{
						//eDebug("\t\t\tvalue: %s", at->value().c_str());
						tmp = strtol(at->value().c_str(), &end_ptr, 10);
						if (!*end_ptr)
							*dest = tmp;
					}
				}
				if (freq && sr && pol != -1)
				{
					tuple = PyTuple_New(12);
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(0));
					PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(freq));
					PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(sr));
					PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(pol));
					PyTuple_SET_ITEM(tuple, 4, PyInt_FromLong(fec));
					PyTuple_SET_ITEM(tuple, 5, PyInt_FromLong(system));
					PyTuple_SET_ITEM(tuple, 6, PyInt_FromLong(modulation));
					PyTuple_SET_ITEM(tuple, 7, PyInt_FromLong(inv));
					PyTuple_SET_ITEM(tuple, 8, PyInt_FromLong(rolloff));
					PyTuple_SET_ITEM(tuple, 9, PyInt_FromLong(pilot));
					PyTuple_SET_ITEM(tuple, 10, PyInt_FromLong(tsid));
					PyTuple_SET_ITEM(tuple, 11, PyInt_FromLong(onid));
					PyList_Append(tplist, tuple);
					Py_DECREF(tuple);
				}
			}
			Py_DECREF(tplist);
		}
		else
		{
			if (sat_pos)
				Py_DECREF(sat_pos);
			if (sat_name)
				Py_DECREF(sat_name);
			if (sat_flags)
				Py_DECREF(sat_flags);
		}
	}
	Py_INCREF(Py_True);
	return Py_True;
}

PyObject *eDVBDB::readCables(ePyObject cab_list, ePyObject tp_dict)
{
	if (!PyDict_Check(tp_dict)) {
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 1 is not a python dict");
		return NULL;
	}
	else if (!PyList_Check(cab_list))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 0 is not a python list");
		return NULL;
	}
	XMLTree tree;
	tree.setFilename("/etc/tuxbox/cables.xml");
	tree.read();
	Element *root = tree.getRoot();
	if (!root)
	{
		eDebug("couldn't open /etc/tuxbox/cables.xml!!");
		Py_INCREF(Py_False);
		return Py_False;
	}
	const Attribute *at;
	int tmp, *dest,
		modulation, fec, freq, sr, inversion, system;
	std::string name;
	char *end_ptr;
	const ElementList &root_elements = root->getElementList();
	for (ElementConstIterator it(root_elements.begin()); it != root_elements.end(); ++it)
	{
//		eDebug("element: %s", el->name().c_str());
		const Element *el = *it;
		const ElementList &cab_elements = el->getElementList();
		const AttributeList &cab_attributes = el->getAttributeList();
		ePyObject cab_name;
		ePyObject cab_flags;
		for (AttributeConstIterator it(cab_attributes.begin()); it != cab_attributes.end(); ++it)
		{
//			eDebug("\tattr: %s", at->name().c_str());
			at = *it;
			name = at->name();
			if (name == "name")
				cab_name = PyString_FromString(at->value().c_str());
			else if (name == "flags")
			{
				tmp = strtol(at->value().c_str(), &end_ptr, 10);
				if (!*end_ptr)
					cab_flags = PyInt_FromLong(tmp);
			}
		}
		if (cab_name)
		{
			ePyObject tplist = PyList_New(0);
			ePyObject tuple = PyTuple_New(2);
			if (!cab_flags)
				cab_flags = PyInt_FromLong(0);
			PyTuple_SET_ITEM(tuple, 0, cab_name);
			PyTuple_SET_ITEM(tuple, 1, cab_flags);
			PyList_Append(cab_list, tuple);
			Py_DECREF(tuple);
			PyDict_SetItem(tp_dict, cab_name, tplist);
			for (ElementConstIterator it(cab_elements.begin()); it != cab_elements.end(); ++it)
			{
//				eDebug("\telement: %s", (*it)->name().c_str());
				const AttributeList &tp_attributes = (*it)->getAttributeList();
				AttributeConstIterator end = tp_attributes.end();
				modulation = eDVBFrontendParametersCable::Modulation_QAM64;
				fec = eDVBFrontendParametersCable::FEC_Auto;
				system = eDVBFrontendParametersCable::System_DVB_C_ANNEX_A;
				inversion = eDVBFrontendParametersCable::Inversion_Unknown;
				freq = 0;
				sr = 0;
				for (AttributeConstIterator it(tp_attributes.begin()); it != end; ++it)
				{
//					eDebug("\t\tattr: %s", at->name().c_str());
					at = *it;
					dest = 0;
					name = at->name();
					if (name == "modulation") dest = &modulation;
					else if (name == "frequency") dest = &freq;
					else if (name == "symbol_rate") dest = &sr;
					else if (name == "fec_inner") dest = &fec;
					else if (name == "inversion") dest = &inversion;
					else if (name == "system") dest = &system;
					else continue;
					if (dest)
					{
						tmp = strtol(at->value().c_str(), &end_ptr, 10);
						if (!*end_ptr)
							*dest = tmp;
					}
				}
				if (freq && sr)
				{
					while (freq > 999999)
						freq /= 10;
					tuple = PyTuple_New(7);
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(1));
					PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(freq));
					PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(sr));
					PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(modulation));
					PyTuple_SET_ITEM(tuple, 4, PyInt_FromLong(fec));
					PyTuple_SET_ITEM(tuple, 5, PyInt_FromLong(inversion));
					PyTuple_SET_ITEM(tuple, 6, PyInt_FromLong(system));
					PyList_Append(tplist, tuple);
					Py_DECREF(tuple);
				}
			}
			Py_DECREF(tplist);
		}
		else if (cab_flags)
			Py_DECREF(cab_flags);
	}
	Py_INCREF(Py_True);
	return Py_True;
}

PyObject *eDVBDB::readTerrestrials(ePyObject ter_list, ePyObject tp_dict)
{
	if (!PyDict_Check(tp_dict)) {
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 1 is not a python dict");
		return NULL;
	}
	else if (!PyList_Check(ter_list))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
			eDebug("arg 0 is not a python list");
		return NULL;
	}
	XMLTree tree;
	tree.setFilename("/etc/tuxbox/terrestrial.xml");
	tree.read();
	Element *root = tree.getRoot();
	if (!root)
	{
		eDebug("couldn't open /etc/tuxbox/terrestrial.xml!!");
		Py_INCREF(Py_False);
		return Py_False;
	}
	const Attribute *at;
	std::string name;
	int tmp, *dest,
		freq, bw, constellation, crh, crl, guard, transm, hierarchy, inv, system;
	char *end_ptr;
	const ElementList &root_elements = root->getElementList();
	for (ElementConstIterator it(root_elements.begin()); it != root_elements.end(); ++it)
	{
//		eDebug("element: %s", el->name().c_str());
		const Element *el = *it;
		const ElementList &ter_elements = el->getElementList();
		const AttributeList &ter_attributes = el->getAttributeList();
		ePyObject ter_name;
		ePyObject ter_flags;
		for (AttributeConstIterator it(ter_attributes.begin()); it != ter_attributes.end(); ++it)
		{
//			eDebug("\tattr: %s", at->name().c_str());
			at = *it;
			name = at->name();
			if (name == "name")
				ter_name = PyString_FromString(at->value().c_str());
			else if (name == "flags")
			{
				tmp = strtol(at->value().c_str(), &end_ptr, 10);
				if (!*end_ptr)
					ter_flags = PyInt_FromLong(tmp);
			}
		}
		if (ter_name)
		{
			ePyObject tplist = PyList_New(0);
			ePyObject tuple = PyTuple_New(2);
			if (!ter_flags)
				ter_flags = PyInt_FromLong(0);
			PyTuple_SET_ITEM(tuple, 0, ter_name);
			PyTuple_SET_ITEM(tuple, 1, ter_flags);
			PyList_Append(ter_list, tuple);
			Py_DECREF(tuple);
			PyDict_SetItem(tp_dict, ter_name, tplist);
			for (ElementConstIterator it(ter_elements.begin()); it != ter_elements.end(); ++it)
			{
//				eDebug("\telement: %s", (*it)->name().c_str());
				const AttributeList &tp_attributes = (*it)->getAttributeList();
				AttributeConstIterator end = tp_attributes.end();
				freq = 0;
				bw = eDVBFrontendParametersTerrestrial::Bandwidth_Auto;
				constellation = eDVBFrontendParametersTerrestrial::Modulation_Auto;
				crh = eDVBFrontendParametersTerrestrial::FEC_Auto;
				crl = eDVBFrontendParametersTerrestrial::FEC_Auto;
				guard = eDVBFrontendParametersTerrestrial::GuardInterval_Auto;
				transm = eDVBFrontendParametersTerrestrial::TransmissionMode_Auto;
				hierarchy = eDVBFrontendParametersTerrestrial::Hierarchy_Auto;
				inv = eDVBFrontendParametersTerrestrial::Inversion_Unknown;
				system = eDVBFrontendParametersTerrestrial::System_DVB_T;
				for (AttributeConstIterator it(tp_attributes.begin()); it != end; ++it)
				{
//					eDebug("\t\tattr: %s", at->name().c_str());
					at = *it;
					dest = 0;
					name = at->name();
					if (name == "centre_frequency") dest = &freq;
					else if (name == "bandwidth") dest = &bw;
					else if (name == "constellation") dest = &constellation;
					else if (name == "code_rate_hp") dest = &crh;
					else if (name == "code_rate_lp") dest = &crl;
					else if (name == "guard_interval") dest = &guard;
					else if (name == "transmission_mode") dest = &transm;
					else if (name == "hierarchy_information") dest = &hierarchy;
					else if (name == "inversion") dest = &inv;
					else if (name == "system") dest = &system;
					else continue;
					if (dest)
					{
						tmp = strtol(at->value().c_str(), &end_ptr, 10);
						if (!*end_ptr)
							*dest = tmp;
					}
				}
				if (freq)
				{
					switch (bw)
					{
					case eDVBFrontendParametersTerrestrial::Bandwidth_8MHz: bw = 8000000; break;
					case eDVBFrontendParametersTerrestrial::Bandwidth_7MHz: bw = 7000000; break;
					case eDVBFrontendParametersTerrestrial::Bandwidth_6MHz: bw = 6000000; break;
					default:
					case eDVBFrontendParametersTerrestrial::Bandwidth_Auto: bw = 0; break;
					case eDVBFrontendParametersTerrestrial::Bandwidth_5MHz: bw = 5000000; break;
					case eDVBFrontendParametersTerrestrial::Bandwidth_1_712MHz: bw = 1712000; break;
					case eDVBFrontendParametersTerrestrial::Bandwidth_10MHz: bw = 10000000; break;
					}
					if (crh > eDVBFrontendParametersTerrestrial::FEC_8_9)
						crh = eDVBFrontendParametersTerrestrial::FEC_Auto;
					if (crl > eDVBFrontendParametersTerrestrial::FEC_8_9)
						crl = eDVBFrontendParametersTerrestrial::FEC_Auto;
					tuple = PyTuple_New(11);
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(2));
					PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(freq));
					PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(bw));
					PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(constellation));
					PyTuple_SET_ITEM(tuple, 4, PyInt_FromLong(crh));
					PyTuple_SET_ITEM(tuple, 5, PyInt_FromLong(crl));
					PyTuple_SET_ITEM(tuple, 6, PyInt_FromLong(guard));
					PyTuple_SET_ITEM(tuple, 7, PyInt_FromLong(transm));
					PyTuple_SET_ITEM(tuple, 8, PyInt_FromLong(hierarchy));
					PyTuple_SET_ITEM(tuple, 9, PyInt_FromLong(inv));
					PyTuple_SET_ITEM(tuple, 10, PyInt_FromLong(system));
					PyList_Append(tplist, tuple);
					Py_DECREF(tuple);
				}
			}
			Py_DECREF(tplist);
		}
		else if (ter_flags)
			Py_DECREF(ter_flags);
	}
	Py_INCREF(Py_True);
	return Py_True;
}

eDVBDB::~eDVBDB()
{
	instance=NULL;
}

RESULT eDVBDB::removeService(const eServiceReference &ref)
{
	if (ref.type == eServiceReference::idDVB)
	{
		eServiceReferenceDVB &service = (eServiceReferenceDVB&)ref;
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_services.find(service));
		if (it != m_services.end())
		{
			m_services.erase(it);
			return 0;
		}
	}
	return -1;
}

RESULT eDVBDB::removeServices(int dvb_namespace, int tsid, int onid, unsigned int orb_pos)
{
	return removeServices(eDVBChannelID(eDVBNamespace(dvb_namespace), eTransportStreamID(tsid), eOriginalNetworkID(onid)), orb_pos);
}

RESULT eDVBDB::removeServices(eDVBChannelID chid, unsigned int orbpos)
{
	RESULT ret=-1;
	eDVBNamespace eNs;
	eTransportStreamID eTsid;
	eOriginalNetworkID eOnid;
	std::map<eDVBChannelID, channel>::iterator it(m_channels.begin());
	std::set<eDVBChannelID> removed_chids;
	while (it != m_channels.end())
	{
		const eDVBChannelID &ch = it->first;
		bool remove=true;
		int system;
		it->second.m_frontendParameters->getSystem(system);
		if ( system == iDVBFrontend::feSatellite )
		{
			eDVBFrontendParametersSatellite sat;
			it->second.m_frontendParameters->getDVBS(sat);
			if ((unsigned int)sat.orbital_position != orbpos)
				remove=false;
		}
		if ( remove && chid.dvbnamespace != eNs ) // namespace given?
		{
			if ( system == iDVBFrontend::feCable && chid.dvbnamespace.get() == (int)0xFFFF0000 )
				;
			else if ( system == iDVBFrontend::feTerrestrial && chid.dvbnamespace.get() == (int)0xEEEE0000 )
				;
			else if ( chid.dvbnamespace != ch.dvbnamespace )
				remove=false;
		}
		else if ( system == iDVBFrontend::feCable || system == iDVBFrontend::feTerrestrial )
			remove=false;
		if ( remove && chid.original_network_id != eOnid && chid.original_network_id != ch.original_network_id )
			remove=false;
		if ( remove && chid.transport_stream_id != eTsid && chid.transport_stream_id != ch.transport_stream_id )
			remove=false;
		if ( remove )
		{
			eDebug("remove %08x %04x %04x",
				ch.dvbnamespace.get(),
				ch.original_network_id.get(),
				ch.transport_stream_id.get());
			removed_chids.insert(it->first);
			m_channels.erase(it++);
		}
		else
			++it;
	}
	if (!removed_chids.empty())
	{
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator service(m_services.begin());
		while(service != m_services.end())
		{
			eDVBChannelID chid;
			service->first.getChannelID(chid);
			std::set<eDVBChannelID>::iterator it(removed_chids.find(chid));
			if (it != removed_chids.end())
				m_services.erase(service++);
			else
				++service;
			ret=0;
		}
	}
	return ret;
}

RESULT eDVBDB::removeServices(iDVBFrontendParameters *feparm)
{
	int ret = -1;
	std::set<eDVBChannelID> removed_chids;
	std::map<eDVBChannelID, channel>::iterator it(m_channels.begin());
	while (it != m_channels.end())
	{
		int diff;
		if (!feparm->calculateDifference(&(*it->second.m_frontendParameters), diff, false))
		{
			if (diff < 4000)
			{
				removed_chids.insert(it->first);
				m_channels.erase(it++);
			}
			else
				++it;
		}
		else
			++it;
	}
	if (!removed_chids.empty())
	{
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator service(m_services.begin());
		while(service != m_services.end())
		{
			eDVBChannelID chid;
			service->first.getChannelID(chid);
			std::set<eDVBChannelID>::iterator it(removed_chids.find(chid));
			if (it != removed_chids.end())
				m_services.erase(service++);
			else
				++service;
		}
		ret = 0;
	}
	return ret;
}

RESULT eDVBDB::addFlag(const eServiceReference &ref, unsigned int flagmask)
{
	if (ref.type == eServiceReference::idDVB)
	{
		eServiceReferenceDVB &service = (eServiceReferenceDVB&)ref;
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_services.find(service));
		if (it != m_services.end())
			it->second->m_flags |= ~flagmask;
		return 0;
	}
	return -1;
}

RESULT eDVBDB::removeFlag(const eServiceReference &ref, unsigned int flagmask)
{
	if (ref.type == eServiceReference::idDVB)
	{
		eServiceReferenceDVB &service = (eServiceReferenceDVB&)ref;
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_services.find(service));
		if (it != m_services.end())
			it->second->m_flags &= ~flagmask;
		return 0;
	}
	return -1;
}

RESULT eDVBDB::removeFlags(unsigned int flagmask, int dvb_namespace, int tsid, int onid, unsigned int orb_pos)
{
	return removeFlags(flagmask, eDVBChannelID(eDVBNamespace(dvb_namespace), eTransportStreamID(tsid), eOriginalNetworkID(onid)), orb_pos);
}

RESULT eDVBDB::removeFlags(unsigned int flagmask, eDVBChannelID chid, unsigned int orbpos)
{
	eDVBNamespace eNs;
	eTransportStreamID eTsid;
	eOriginalNetworkID eOnid;
	std::map<eDVBChannelID, channel>::iterator it(m_channels.begin());
	std::set<eDVBChannelID> removed_chids;
	while (it != m_channels.end())
	{
		const eDVBChannelID &ch = it->first;
		bool remove=true;
		int system;
		it->second.m_frontendParameters->getSystem(system);
		if ( orbpos != 0xFFFFFFFF && system == iDVBFrontend::feSatellite )
		{
			eDVBFrontendParametersSatellite sat;
			it->second.m_frontendParameters->getDVBS(sat);
			if ((unsigned int)sat.orbital_position != orbpos)
				remove=false;
		}
		if ( remove && chid.dvbnamespace != eNs )
		{
			if (system == iDVBFrontend::feCable && chid.dvbnamespace.get() == (int)0xFFFF0000)
				;
			else if (system == iDVBFrontend::feTerrestrial && chid.dvbnamespace.get() == (int)0xEEEE0000)
				;
			else if ( chid.dvbnamespace != ch.dvbnamespace )
				remove=false;
		}
		if ( remove && chid.original_network_id != eOnid && chid.original_network_id != ch.original_network_id )
			remove=false;
		if ( remove && chid.transport_stream_id != eTsid && chid.transport_stream_id != ch.transport_stream_id )
			remove=false;
		if ( remove )
			removed_chids.insert(it->first);
		++it;
	}
	if (!removed_chids.empty())
	{
		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator service(m_services.begin());
		while(service != m_services.end())
		{
			eDVBChannelID chid;
			service->first.getChannelID(chid);
			std::set<eDVBChannelID>::iterator it(removed_chids.find(chid));
			if (it != removed_chids.end())
				service->second->m_flags &= ~flagmask;
			++service;
		}
	}
	return 0;
}

RESULT eDVBDB::addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm)
{
	channel ch;
	std::map<eDVBChannelID, channel>::iterator it = m_channels.find(id);
	ASSERT(feparm);
	ch.m_frontendParameters = feparm;
	if (it != m_channels.end())
		it->second = ch;
	else
		m_channels.insert(std::pair<eDVBChannelID, channel>(id, ch));
	return 0;
}

RESULT eDVBDB::removeChannel(const eDVBChannelID &id)
{
	m_channels.erase(id);
	return 0;
}

RESULT eDVBDB::getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm)
{
	std::map<eDVBChannelID, channel>::iterator i = m_channels.find(id);
	if (i == m_channels.end())
	{
		parm = 0;
		return -ENOENT;
	}
	parm = i->second.m_frontendParameters;
	return 0;
}

RESULT eDVBDB::addService(const eServiceReferenceDVB &serviceref, eDVBService *service)
{
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_services.find(serviceref));
	if (it == m_services.end())
		m_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(serviceref, service));
	return 0;
}

RESULT eDVBDB::getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service)
{
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator i;
	i = m_services.find(reference);
	if (i == m_services.end())
	{
		service = 0;
		return -ENOENT;
	}
	service = i->second;
	return 0;
}

RESULT eDVBDB::flush()
{
	saveServicelist();
	return 0;
}

RESULT eDVBDB::getBouquet(const eServiceReference &ref, eBouquet* &bouquet)
{
	std::string str = ref.path;
	if (str.empty())
	{
		eDebug("getBouquet failed.. no path given!");
		return -1;
	}
	size_t pos = str.find("FROM BOUQUET \"");
	if ( pos != std::string::npos )
	{
		str.erase(0, pos+14);
		pos = str.find('"');
		if ( pos != std::string::npos )
			str.erase(pos);
		else
			str.clear();
	}
	if (str.empty())
	{
		eDebug("getBouquet failed.. couldn't parse bouquet name");
		return -1;
	}
	std::map<std::string, eBouquet>::iterator i =
		m_bouquets.find(str);
	if (i == m_bouquets.end())
	{
		bouquet = 0;
		return -ENOENT;
	}
	bouquet = &i->second;
	return 0;
}

RESULT eDVBDB::startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *q, const eServiceReference &source)
{
	if ( source.path.find("FROM") != std::string::npos )
	{
		if ( source.path.find("BOUQUET") != std::string::npos )
			query = new eDVBDBBouquetQuery(this, source, q);
		else if ( source.path.find("SATELLITES") != std::string::npos )
			query = new eDVBDBSatellitesQuery(this, source, q);
		else if ( source.path.find("PROVIDERS") != std::string::npos )
			query = new eDVBDBProvidersQuery(this, source, q);
		else
			eFatal("invalid query %s", source.toString().c_str());
	}
	else
		query = new eDVBDBQuery(this, source, q);
	return 0;
}

eServiceReference eDVBDB::searchReference(int tsid, int onid, int sid)
{
	eServiceID Sid(sid);
	eTransportStreamID Tsid(tsid);
	eOriginalNetworkID Onid(onid);
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator sit(m_services.begin());
		sit != m_services.end(); ++sit)
	{
		if (sit->first.getTransportStreamID() == Tsid &&
			sit->first.getOriginalNetworkID() == Onid &&
			sit->first.getServiceID() == Sid)
			return sit->first;
	}
	return eServiceReference();
}

void eDVBDB::searchAllReferences(std::vector<eServiceReference> &result, int tsid, int onid, int sid)
{
	eServiceID Sid(sid);
	eTransportStreamID Tsid(tsid);
	eOriginalNetworkID Onid(onid);
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator sit(m_services.begin());
		sit != m_services.end(); ++sit)
	{
		if (sit->first.getTransportStreamID() == Tsid &&
			sit->first.getOriginalNetworkID() == Onid &&
			sit->first.getServiceID() == Sid)
			result.push_back(sit->first);
	}
}

DEFINE_REF(eDVBDBQueryBase);

eDVBDBQueryBase::eDVBDBQueryBase(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:m_db(db), m_query(query), m_source(source)
{
}

int eDVBDBQueryBase::compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b)
{
	ePtr<eDVBService> a_service, b_service;
	int sortmode = m_query ? m_query->m_sort : eDVBChannelQuery::tName;

	if ((sortmode == eDVBChannelQuery::tName) || (sortmode == eDVBChannelQuery::tProvider))
	{
		if (a.name.empty() && m_db->getService(a, a_service))
			return 1;
		if (b.name.empty() && m_db->getService(b, b_service))
			return 1;
	}

	switch (sortmode)
	{
	case eDVBChannelQuery::tName:
		if (a_service)
		{
			if (b_service)
				return a_service->m_service_name_sort < b_service->m_service_name_sort;
			else
			{
				std::string str = b.name;
				makeUpper(str);
				return a_service->m_service_name_sort < str;
			}
		}
		else if (b_service)
		{
			std::string str = a.name;
			makeUpper(str);
			return str < b_service->m_service_name_sort;
		}
		else
		{
			std::string aa = a.name, bb = b.name;
			makeUpper(aa);
			makeUpper(bb);
			return aa < bb;
		}
	case eDVBChannelQuery::tProvider:
		return a_service->m_provider_name < b_service->m_provider_name;
	case eDVBChannelQuery::tType:
		return a.getServiceType() < b.getServiceType();
	case eDVBChannelQuery::tBouquet:
		return 0;
	case eDVBChannelQuery::tSatellitePosition:
		return (a.getDVBNamespace().get() >> 16) < (b.getDVBNamespace().get() >> 16);
	default:
		return 1;
	}
	return 0;
}

eDVBDBQuery::eDVBDBQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:eDVBDBQueryBase(db, source, query)
{
	m_cursor = m_db->m_services.begin();
}

RESULT eDVBDBQuery::getNextResult(eServiceReferenceDVB &ref)
{
	while (m_cursor != m_db->m_services.end())
	{
		ePtr<eDVBService> service = m_cursor->second;
		if (service->isHidden())
			++m_cursor;
		else
		{
			ref = m_cursor->first;

			int res = (!m_query) || service->checkFilter(ref, *m_query);

			++m_cursor;

			if (res)
				return 0;
		}
	}

	ref.type = eServiceReference::idInvalid;

	return 1;
}

eDVBDBBouquetQuery::eDVBDBBouquetQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:eDVBDBQueryBase(db, source, query), m_cursor(db->m_bouquets[query->m_bouquet_name].m_services.begin())
{
}

RESULT eDVBDBBouquetQuery::getNextResult(eServiceReferenceDVB &ref)
{
	eBouquet &bouquet = m_db->m_bouquets[m_query->m_bouquet_name];
	std::list<eServiceReference> &list = bouquet.m_services;
	while (m_cursor != list.end())
	{
		ref = *((eServiceReferenceDVB*)&(*m_cursor));

		std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it =
			m_db->m_services.find(ref);

		int res = (!m_query) || it == m_db->m_services.end() || !(it->second->isHidden() && it->second->checkFilter(ref, *m_query));

		++m_cursor;

		if (res)
			return 0;
	}

	ref.type = eServiceReference::idInvalid;

	return 1;
}

eDVBDBListQuery::eDVBDBListQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:eDVBDBQueryBase(db, source, query), m_cursor(m_list.end())
{
}

RESULT eDVBDBListQuery::getNextResult(eServiceReferenceDVB &ref)
{
	if (m_cursor != m_list.end())
	{
		ref = *m_cursor++;
		return 0;
	}
	ref.type = eServiceReference::idInvalid;
	return 1;
}

int eDVBDBListQuery::compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b)
{
	if ( m_query->m_sort == eDVBChannelQuery::tSatellitePosition )
	{
		int x = (a.getDVBNamespace().get() >> 16);
		int y = (b.getDVBNamespace().get() >> 16);
		if ( x > 1800 )
			x -= 3600;
		if ( y > 1800 )
			y -= 3600;
		return x < y;
	}
	std::string aa = a.name, bb = b.name;
	makeUpper(aa);
	makeUpper(bb);
	return aa < bb;
}

eDVBDBSatellitesQuery::eDVBDBSatellitesQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:eDVBDBListQuery(db, source, query)
{
	std::set<unsigned int> found;
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_db->m_services.begin());
		it != m_db->m_services.end(); ++it)
	{
		int res = !it->second->isHidden() && it->second->checkFilter(it->first, *query);
		if (res)
		{
			unsigned int dvbnamespace = it->first.getDVBNamespace().get()&0xFFFF0000;
			if (found.find(dvbnamespace) == found.end())
			{
				found.insert(dvbnamespace);
				eServiceReferenceDVB ref;
				ref.setDVBNamespace(dvbnamespace);
				ref.flags=eServiceReference::flagDirectory;
				char buf[128];
				snprintf(buf, 128, "(satellitePosition == %d) && ", dvbnamespace>>16);

				ref.path=buf+source.path;
				unsigned int pos=ref.path.find("FROM");
				ref.path.erase(pos);
				ref.path+="ORDER BY name";
//				eDebug("ref.path now %s", ref.path.c_str());
				m_list.push_back(ref);

				ref.path=buf+source.path;
				pos=ref.path.find("FROM");
				ref.path.erase(pos+5);
				ref.path+="PROVIDERS ORDER BY name";
//				eDebug("ref.path now %s", ref.path.c_str());
				m_list.push_back(ref);

				snprintf(buf, 128, "(satellitePosition == %d) && (flags == %d) && ", dvbnamespace>>16, eDVBService::dxNewFound);
				ref.path=buf+source.path;
				pos=ref.path.find("FROM");
				ref.path.erase(pos);
				ref.path+="ORDER BY name";
//				eDebug("ref.path now %s", ref.path.c_str());
				m_list.push_back(ref);
			}
		}
	}
	m_cursor=m_list.begin();
}

eDVBDBProvidersQuery::eDVBDBProvidersQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query)
	:eDVBDBListQuery(db, source, query)
{
	std::set<std::string> found;
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_db->m_services.begin());
		it != m_db->m_services.end(); ++it)
	{
		int res = !it->second->isHidden() && it->second->checkFilter(it->first, *query);
		if (res)
		{
			const char *provider_name = it->second->m_provider_name.length() ?
				it->second->m_provider_name.c_str() :
				"Unknown";
			if (found.find(std::string(provider_name)) == found.end())
			{
				found.insert(std::string(provider_name));
				eServiceReferenceDVB ref;
				char buf[64];
				ref.name=provider_name;
				snprintf(buf, 64, "(provider == \"%s\") && ", provider_name);
				ref.path=buf+source.path;
				unsigned int pos = ref.path.find("FROM");
				ref.flags=eServiceReference::flagDirectory;
				ref.path.erase(pos);
				ref.path+="ORDER BY name";
//				eDebug("ref.path now %s", ref.path.c_str());
				m_list.push_back(ref);
			}
		}
	}
	m_cursor=m_list.begin();
}

/* (<name|provider|type|bouquet|satpos|chid> <==|...> <"string"|int>)[||,&& (..)] */

static int decodeType(const std::string &type)
{
	if (type == "name")
		return eDVBChannelQuery::tName;
	else if (type == "provider")
		return eDVBChannelQuery::tProvider;
	else if (type == "type")
		return eDVBChannelQuery::tType;
	else if (type == "bouquet")
		return eDVBChannelQuery::tBouquet;
	else if (type == "satellitePosition")
		return eDVBChannelQuery::tSatellitePosition;
	else if (type == "channelID")
		return eDVBChannelQuery::tChannelID;
	else if (type == "flags")
		return eDVBChannelQuery::tFlags;
	else
		return -1;
}

	/* never, NEVER write a parser in C++! */
RESULT parseExpression(ePtr<eDVBChannelQuery> &res, std::list<std::string>::const_iterator begin, std::list<std::string>::const_iterator end)
{
	std::list<std::string>::const_iterator end_of_exp;

	if (begin == end)
		return 0;

	if (*begin == "(")
	{
		end_of_exp = begin;
		while (end_of_exp != end)
			if (*end_of_exp == ")")
				break;
			else
				++end_of_exp;

		if (end_of_exp == end)
		{
			eDebug("expression parse: end of expression while searching for closing brace");
			return -1;
		}

		++begin;
		// begin..end_of_exp
		int r = parseExpression(res, begin, end_of_exp);
		if (r)
			return r;
		++end_of_exp;

			/* we had only one sub expression */
		if (end_of_exp == end)
		{
//			eDebug("only one sub expression");
			return 0;
		}

			/* otherwise we have an operator here.. */

		ePtr<eDVBChannelQuery> r2 = res;
		res = new eDVBChannelQuery();
		res->m_sort = 0;
		res->m_p1 = r2;
		res->m_inverse = 0;
		r2 = 0;

		if (*end_of_exp == "||")
			res->m_type = eDVBChannelQuery::tOR;
		else if (*end_of_exp == "&&")
			res->m_type = eDVBChannelQuery::tAND;
		else
		{
			eDebug("found operator %s, but only && and || are allowed!", end_of_exp->c_str());
			res = 0;
			return 1;
		}

		++end_of_exp;

		return parseExpression(res->m_p2, end_of_exp, end);
	}

	// "begin" <op> "end"
	std::string type, op, val;

	res = new eDVBChannelQuery();
	res->m_sort = 0;

	int cnt = 0;
	while (begin != end)
	{
		switch (cnt)
		{
		case 0:
			type = *begin;
			break;
		case 1:
			op = *begin;
			break;
		case 2:
			val = *begin;
			break;
		case 3:
			eDebug("malformed query: got '%s', but expected only <type> <op> <val>", begin->c_str());
			return 1;
		}
		++begin;
		++cnt;
	}

	if (cnt != 3)
	{
		eDebug("malformed query: missing stuff");
		res = 0;
		return 1;
	}

	res->m_type = decodeType(type);

	if (res->m_type == -1)
	{
		eDebug("malformed query: invalid type %s", type.c_str());
		res = 0;
		return 1;
	}

	if (op == "==")
		res->m_inverse = 0;
	else if (op == "!=")
		res->m_inverse = 1;
	else
	{
		eDebug("invalid operator %s", op.c_str());
		res = 0;
		return 1;
	}

	res->m_string = val;

	if (res->m_type == eDVBChannelQuery::tChannelID)
	{
		int ns, tsid, onid;
		if (sscanf(val.c_str(), "%08x%04x%04x", &ns, &tsid, &onid) == 3)
			res->m_channelid = eDVBChannelID(eDVBNamespace(ns), eTransportStreamID(tsid), eOriginalNetworkID(onid));
		else
			eDebug("couldn't parse channelid !! format should be hex NNNNNNNNTTTTOOOO (namespace, tsid, onid)");
	}
	else
		res->m_int = atoi(val.c_str());

	return 0;
}

RESULT eDVBChannelQuery::compile(ePtr<eDVBChannelQuery> &res, std::string query)
{
	std::list<std::string> tokens;

	std::string current_token;
	std::string bouquet_name;

//	eDebug("splitting %s....", query.c_str());
	unsigned int i = 0;
	const char *splitchars="()";
	int quotemode = 0, lastsplit = 0, lastalnum = 0;
	while (i <= query.size())
	{
		int c = (i < query.size()) ? query[i] : ' ';
		++i;

		int issplit = !!strchr(splitchars, c);
		int isaln = isalnum(c);
		int iswhite = c == ' ';
		int isquot = c == '\"';

		if (quotemode)
		{
			iswhite = issplit = 0;
			isaln = lastalnum;
		}

		if (issplit || iswhite || isquot || lastsplit || (lastalnum != isaln))
		{
			if (current_token.size())
				tokens.push_back(current_token);
			current_token.clear();
		}

		if (!(iswhite || isquot))
			current_token += c;

		if (isquot)
			quotemode = !quotemode;
		lastsplit = issplit;
		lastalnum = isaln;
	}

//	for (std::list<std::string>::const_iterator a(tokens.begin()); a != tokens.end(); ++a)
//	{
//		printf("%s\n", a->c_str());
//	}

	int sort = eDVBChannelQuery::tName;
		/* check for "ORDER BY ..." */

	std::list<std::string>::iterator it = tokens.begin();
	while (it != tokens.end())
	{
		if (*it == "ORDER")
		{
			tokens.erase(it++);
			if (it != tokens.end() && *it == "BY")
			{
				tokens.erase(it++);
				sort = decodeType(*it);
				tokens.erase(it++);
			} else
				sort = -1;
		}
		else if (*it == "FROM")
		{
			tokens.erase(it++);
			if (it != tokens.end() && *it == "BOUQUET")
			{
				tokens.erase(it++);
				bouquet_name = *it;
				tokens.erase(it++);
			}
			else if (it != tokens.end() && *it == "SATELLITES")
				tokens.erase(it++);
			else if (it != tokens.end() && *it == "PROVIDERS")
				tokens.erase(it++);
			else
			{
				eDebug("FROM unknown %s", (*it).c_str());
				tokens.erase(it++);
			}
		}
		else
			++it;
	}

	if (sort == -1)
	{
		eWarning("ORDER BY .. string invalid.");
		res = 0;
		return -1;
	}

//	eDebug("sort by %d", sort);

		/* now we recursivly parse that. */
	int r = parseExpression(res, tokens.begin(), tokens.end());

		/* we have an empty (but valid!) expression */
	if (!r && !res)
	{
		res = new eDVBChannelQuery();
		res->m_inverse = 0;
		res->m_type = eDVBChannelQuery::tAny;
	}

	if (res)
	{
		res->m_sort = sort;
		res->m_bouquet_name = bouquet_name;
	}

//	eDebug("return: %d", r);
	return r;
}

DEFINE_REF(eDVBChannelQuery);
