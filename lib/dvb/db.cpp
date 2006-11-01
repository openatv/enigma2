#include <errno.h>
#include <lib/dvb/db.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/epgcache.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
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
	FILE *f=fopen((CONFIGDIR"/enigma2/"+m_filename).c_str(), "w");
	if (!f)
		return -1;
	if ( fprintf(f, "#NAME %s\r\n", m_bouquet_name.c_str()) < 0 )
		goto err;
	for (list::iterator i(m_services.begin()); i != m_services.end(); ++i)
	{
		eServiceReference tmp = *i;
		std::string str = tmp.path;
		if ( (i->flags&eServiceReference::flagDirectory) == eServiceReference::flagDirectory )
		{
			unsigned int p1 = str.find("FROM BOUQUET \"");
			if (p1 == std::string::npos)
			{
				eDebug("doof... kaputt");
				continue;
			}
			str.erase(0, p1+14);
			p1 = str.find("\"");
			if (p1 == std::string::npos)
			{
				eDebug("doof2... kaputt");
				continue;
			}
			str.erase(p1);
			tmp.path=str;
		}
		if ( fprintf(f, "#SERVICE %s\r\n", tmp.toString().c_str()) < 0 )
			goto err;
		if ( i->name.length() )
			if ( fprintf(f, "#DESCRIPTION %s\r\n", i->name.c_str()) < 0 )
				goto err;
	}
	fclose(f);
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
	m_service_name_sort = removeDVBChars(m_service_name);
	makeUpper(m_service_name_sort);
	while ((!m_service_name_sort.empty()) && m_service_name_sort[0] == ' ')
		m_service_name_sort.erase(0, 1);

		/* put unnamed services at the end, not at the beginning. */
	if (m_service_name_sort.empty())
		m_service_name_sort = "\xFF";
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

bool eDVBService::isPlayable(const eServiceReference &ref, const eServiceReference &ignore)
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

int eDVBService::checkFilter(const eServiceReferenceDVB &ref, const eDVBChannelQuery &query)
{
	int res = 0;
	switch (query.m_type)
	{
	case eDVBChannelQuery::tName:
		res = m_service_name_sort.find(query.m_string) != std::string::npos;
		break;
	case eDVBChannelQuery::tProvider:
		res = m_provider_name.find(query.m_string) != std::string::npos;
		break;
	case eDVBChannelQuery::tType:
		res = ref.getServiceType() == query.m_int;
		break;
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

	/* THIS CODE IS BAD. it should be replaced by somethine better. */
void eDVBDB::reloadServicelist()
{
	eDebug("---- opening lame channel db");
	FILE *f=fopen(CONFIGDIR"/enigma2/lamedb", "rt");
	if (!f)
	{
		struct stat s;
		if ( !stat("lamedb", &s) )
		{
			if ( !stat(CONFIGDIR"/enigma2", &s) )
			{
				rename("lamedb", CONFIGDIR"/enigma2/lamedb" );
				reloadServicelist();
			}
		}
		return;
	}
	char line[256];
	if ((!fgets(line, 256, f)) || strncmp(line, "eDVB services", 13))
	{
		eDebug("not a servicefile");
		fclose(f);
		return;
	}
	eDebug("reading services");
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
					system=eDVBFrontendParametersSatellite::System::DVB_S,
					modulation=eDVBFrontendParametersSatellite::Modulation::QPSK,
					rolloff=eDVBFrontendParametersSatellite::RollOff::alpha_auto;
				sscanf(line+2, "%d:%d:%d:%d:%d:%d:%d:%d:%d", &frequency, &symbol_rate, &polarisation, &fec, &orbital_position, &inversion, &system, &modulation, &rolloff);
				sat.frequency = frequency;
				sat.symbol_rate = symbol_rate;
				sat.polarisation = polarisation;
				sat.fec = fec;
				sat.orbital_position =
					orbital_position < 0 ? orbital_position + 3600 : orbital_position;
				sat.inversion = inversion;
				sat.system = system;
				sat.modulation = modulation;
				sat.roll_off = rolloff;
				feparm->setDVBS(sat);
			} else if (line[1]=='t')
			{
				eDVBFrontendParametersTerrestrial ter;
				int frequency, bandwidth, code_rate_HP, code_rate_LP, modulation, transmission_mode, guard_interval, hierarchy, inversion;
				sscanf(line+2, "%d:%d:%d:%d:%d:%d:%d:%d:%d", &frequency, &bandwidth, &code_rate_HP, &code_rate_LP, &modulation, &transmission_mode, &guard_interval, &hierarchy, &inversion);
				ter.frequency = frequency;
				ter.bandwidth = bandwidth;
				ter.code_rate_HP = code_rate_HP;
				ter.code_rate_LP = code_rate_LP;
				ter.modulation = modulation;
				ter.transmission_mode = transmission_mode;
				ter.guard_interval = guard_interval;
				ter.hierarchy = hierarchy;
				ter.inversion = inversion;
				feparm->setDVBT(ter);
			} else if (line[1]=='c')
			{
				eDVBFrontendParametersCable cab;
				int frequency, symbol_rate,
					inversion=eDVBFrontendParametersCable::Inversion::Unknown,
					modulation=eDVBFrontendParametersCable::Modulation::Auto,
					fec_inner=eDVBFrontendParametersCable::FEC::fAuto;
				sscanf(line+2, "%d:%d:%d:%d:%d", &frequency, &symbol_rate, &inversion, &modulation, &fec_inner);
				cab.frequency = frequency;
				cab.fec_inner = fec_inner;
				cab.inversion = inversion;
				cab.symbol_rate = symbol_rate;
				cab.modulation = modulation;
				feparm->setDVBC(cab);
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

	while (!feof(f))
	{
		if (!fgets(line, 256, f))
			break;
		if (!strcmp(line, "end\n"))
			break;

		int service_id=-1, dvb_namespace, transport_stream_id=-1, original_network_id=-1, service_type=-1, service_number=-1;
		sscanf(line, "%x:%x:%x:%x:%d:%d", &service_id, &dvb_namespace, &transport_stream_id, &original_network_id, &service_type, &service_number);
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
		fgets(line, 256, f);
		if (strlen(line))
			line[strlen(line)-1]=0;

		s->m_service_name = line;
		s->genSortName();

		fgets(line, 256, f);
		if (strlen(line))
			line[strlen(line)-1]=0;
		std::string str=line;

		if (str[1]!=':')	// old ... (only service_provider)
		{
			s->m_provider_name=line;
		} else
			while ((!str.empty()) && str[1]==':') // new: p:, f:, c:%02d...
			{
				unsigned int c=str.find(',');
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
//				eDebug("%c ... %s", p, v.c_str());
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
					s->m_ca.push_front((uint16_t)val);
				}
			}
		addService(ref, s);
	}

	eDebug("loaded %d services", count);

	fclose(f);
}

void eDVBDB::saveServicelist()
{
	eDebug("---- saving lame channel db");
	FILE *f=fopen(CONFIGDIR"/enigma2/lamedb", "w");
	int channels=0, services=0;
	if (!f)
		eFatal("couldn't save lame channel db!");
	fprintf(f, "eDVB services /3/\n");
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
		if (!ch.m_frontendParameters->getDVBS(sat))
		{
			if (sat.system == eDVBFrontendParametersSatellite::System::DVB_S2)
			{
				fprintf(f, "\ts %d:%d:%d:%d:%d:%d:%d:%d:%d\n",
					sat.frequency, sat.symbol_rate,
					sat.polarisation, sat.fec,
					sat.orbital_position > 1800 ? sat.orbital_position - 3600 : sat.orbital_position,
					sat.inversion,
					sat.system,
					sat.modulation,
					sat.roll_off);
			}
			else
			{
				fprintf(f, "\ts %d:%d:%d:%d:%d:%d\n",
					sat.frequency, sat.symbol_rate,
					sat.polarisation, sat.fec,
					sat.orbital_position > 1800 ? sat.orbital_position - 3600 : sat.orbital_position,
					sat.inversion);
			}
		}
		if (!ch.m_frontendParameters->getDVBT(ter))
		{
			fprintf(f, "\tt %d:%d:%d:%d:%d:%d:%d:%d:%d\n",
				ter.frequency, ter.bandwidth, ter.code_rate_HP,
				ter.code_rate_LP, ter.modulation, ter.transmission_mode,
				ter.guard_interval, ter.hierarchy, ter.inversion);
		}
		if (!ch.m_frontendParameters->getDVBC(cab))
		{
			fprintf(f, "\tc %d:%d:%d:%d:%d\n",
				cab.frequency, cab.symbol_rate, cab.inversion, cab.modulation, cab.fec_inner);
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
	fclose(f);
}

void eDVBDB::loadBouquet(const char *path)
{
	std::string bouquet_name = path;
	if (!bouquet_name.length())
	{
		eDebug("Bouquet load failed.. no path given..");
		return;
	}
	unsigned int pos = bouquet_name.rfind('/');
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

	std::string p = CONFIGDIR"/enigma2/";
	p+=path;
	eDebug("loading bouquet... %s", p.c_str());
	FILE *fp=fopen(p.c_str(), "rt");
	int entries=0;
	if (!fp)
	{
		struct stat s;
		if ( !stat(path, &s) )
		{
			rename(path, p.c_str() );
			loadBouquet(path);
			return;
		}
		eDebug("failed to open.");
		if ( strstr(path, "bouquets.tv") )
		{
			eDebug("recreate bouquets.tv");
			bouquet.m_bouquet_name="Bouquets (TV)";
			bouquet.flushChanges();
		}
		else if ( strstr(path, "bouquets.radio") )
		{
			eDebug("recreate bouquets.radio");
			bouquet.m_bouquet_name="Bouquets (Radio)";
			bouquet.flushChanges();
		}
		return;
	}
	char line[256];
	bool read_descr=false;
	eServiceReference *e = NULL;
	while (1)
	{
		if (!fgets(line, 256, fp))
			break;
		line[strlen(line)-1]=0;
		if (strlen(line) && line[strlen(line)-1]=='\r')
			line[strlen(line)-1]=0;
		if (!line[0])
			break;
		if (line[0]=='#')
		{
			if (!strncmp(line, "#SERVICE ", 9) || !strncmp(line, "#SERVICE: ", 10))
			{
				int offs = line[8] == ':' ? 10 : 9;
				eServiceReference tmp(line+offs);
				if (tmp.type != eServiceReference::idDVB)
				{
					eDebug("only DVB Bouquets supported");
					continue;
				}
				if ( (tmp.flags&eServiceReference::flagDirectory) == eServiceReference::flagDirectory )
				{
					unsigned int pos = tmp.path.rfind('/');
					if ( pos != std::string::npos )
						tmp.path.erase(0, pos+1);
					if (tmp.path.empty())
					{
						eDebug("Bouquet load failed.. no filename given..");
						continue;
					}
					loadBouquet(tmp.path.c_str());
					char buf[256];
					snprintf(buf, 256, "(type == %d) FROM BOUQUET \"%s\" ORDER BY bouquet", tmp.data[0], tmp.path.c_str());
					tmp.path = buf;
				}
				list.push_back(tmp);
				e = &list.back();
				read_descr=true;
				++entries;
			}
			else if (read_descr && !strncmp(line, "#DESCRIPTION ", 13))
			{
				e->name = line+13;
				read_descr=false;
			}
			else if (!strncmp(line, "#NAME ", 6))
				bouquet.m_bouquet_name=line+6;
			continue;
		}
	}
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
		memset(ref.data, 0, sizeof(ref.data));
		ref.type=1;
		ref.flags=7;
		ref.data[0]=1;
		ref.path="(type == 1) FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet";
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
		memset(ref.data, 0, sizeof(ref.data));
		ref.type=1;
		ref.flags=7;
		ref.data[0]=2;
		ref.path="(type == 2) FROM BOUQUET \"userbouquet.favourites.radio\" ORDER BY bouquet";
		eBouquet &parent = m_bouquets["bouquets.radio"];
		parent.m_services.push_back(ref);
		parent.flushChanges();
	}
}

eDVBDB *eDVBDB::instance;

eDVBDB::eDVBDB()
{
	instance = this;
	reloadServicelist();
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
		if ( orbpos != 0xFFFFFFFF && system == iDVBFrontend::feSatellite )
		{
			eDVBFrontendParametersSatellite sat;
			it->second.m_frontendParameters->getDVBS(sat);
			if ((unsigned int)sat.orbital_position != orbpos)
				remove=false;
		}
		if ( remove && chid.dvbnamespace != eNs && chid.dvbnamespace != ch.dvbnamespace )
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
		if ( remove && chid.dvbnamespace != eNs && chid.dvbnamespace != ch.dvbnamespace )
			remove=false;
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
	assert(feparm);
	ch.m_frontendParameters = feparm;
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
	unsigned int pos = str.find("FROM BOUQUET \"");
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
		ref = m_cursor->first;

		int res = (!m_query) || m_cursor->second->checkFilter(ref, *m_query);

		++m_cursor;

		if (res)
			return 0;
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

		int res = (!m_query) || it == m_db->m_services.end() || it->second->checkFilter(ref, *m_query);

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
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_db->m_services.begin());
		it != m_db->m_services.end(); ++it)
	{
		int res = it->second->checkFilter(it->first, *query);
		if (res)
		{
			unsigned int dvbnamespace = it->first.getDVBNamespace().get()&0xFFFF0000;
			bool found=0;
			for (std::list<eServiceReferenceDVB>::iterator i(m_list.begin()); i != m_list.end(); ++i)
				if ( (i->getDVBNamespace().get()&0xFFFF0000) == dvbnamespace )
				{
					found=true;
					break;
				}
			if (!found)
			{
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
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator it(m_db->m_services.begin());
		it != m_db->m_services.end(); ++it)
	{
		int res = it->second->checkFilter(it->first, *query);
		if (res)
		{
			bool found=0;

			const char *provider_name = it->second->m_provider_name.length() ?
				it->second->m_provider_name.c_str() :
				"Unknown";

			for (std::list<eServiceReferenceDVB>::iterator i(m_list.begin()); i != m_list.end(); ++i)
				if (i->name == provider_name)
				{
					found=true;
					break;
				}
			if (!found)
			{
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
	{
		eDebug("empty expression!");
		return 0;
	}
	
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
	res->m_int = atoi(val.c_str());
//	res->m_channelid = eDVBChannelID(val);
	
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
