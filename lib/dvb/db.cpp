#include <errno.h>
#include <lib/dvb/db.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <dvbsi++/service_description_section.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/satellite_delivery_system_descriptor.h>

DEFINE_REF(eDVBService);

eDVBService::eDVBService()
{
}

eDVBService::~eDVBService()
{
}

eDVBService &eDVBService::operator=(const eDVBService &s)
{
	m_service_name = s.m_service_name;
	m_provider_name = s.m_provider_name;
	m_flags = s.m_flags;
	m_ca = s.m_ca;
	m_cache = s.m_cache;
	return *this;
}

RESULT eDVBService::getName(const eServiceReference &ref, std::string &name)
{
	name = convertDVBUTF8(m_service_name);
	return 0;
}

int eDVBService::getLength(const eServiceReference &ref)
{
	return -1;
}

int eDVBService::checkFilter(const eServiceReferenceDVB &ref, const eDVBChannelQuery &query)
{
	int res = 0;
	switch (query.m_type)
	{
	case eDVBChannelQuery::tName:
		res = m_service_name.find(query.m_string) != std::string::npos;
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
		res = (ref.getDVBNamespace().get() >> 16) == query.m_int;
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
	}

	if (query.m_inverse)
		return !res;
	else
		return res;
}

int eDVBService::getCachePID(cacheID id)
{
	std::map<int, int>::iterator it = m_cache.find(id);
	if ( it != m_cache.end() )
		return it->second;
	return -1;
}

void eDVBService::setCachePID(cacheID id, int pid)
{
	m_cache[id] = pid;
}

DEFINE_REF(eDVBDB);

	/* THIS CODE IS BAD. it should be replaced by somethine better. */
void eDVBDB::load()
{
	eDebug("---- opening lame channel db");
	FILE *f=fopen("lamedb", "rt");
	if (!f)
		return;
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
				int frequency, symbol_rate, polarisation, fec, orbital_position, inversion;
				sscanf(line+2, "%d:%d:%d:%d:%d:%d", &frequency, &symbol_rate, &polarisation, &fec, &inversion, &orbital_position);
				sat.frequency = frequency;
				sat.symbol_rate = symbol_rate;
				sat.polarisation = polarisation;
				sat.fec = fec;
				sat.orbital_position = orbital_position;
				sat.inversion = inversion;
				// ...
//				t.setSatellite(frequency, symbol_rate, polarisation, fec, sat, inversion);
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
				int frequency, symbol_rate, inversion=0, modulation=3;
				sscanf(line+2, "%d:%d:%d:%d", &frequency, &symbol_rate, &inversion, &modulation);
//				t.setCable(frequency, symbol_rate, inversion, modulation);
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
		s->m_service_name=line;
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
					sscanf(v.c_str(), "%02d%04x", &cid, &val);
					s->m_cache[cid]=val;
				} else if (p == 'C')
				{
					int val;
					sscanf(v.c_str(), "%04x", &val);
					s->m_ca.insert(val);
				}
			}
		addService(ref, s);
	}

	eDebug("loaded %d services", count);

	fclose(f);
}

void eDVBDB::save()
{
	eDebug("---- saving lame channel db");
	FILE *f=fopen("lamedb", "wt");
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
		if (!ch.m_frontendParameters->getDVBS(sat))
		{
			fprintf(f, "\ts %d:%d:%d:%d:%d:%d\n",
				sat.frequency, sat.symbol_rate,
				sat.polarisation, sat.fec, sat.inversion,
				sat.orbital_position);
		}
		if (!ch.m_frontendParameters->getDVBT(ter))
		{
			fprintf(f, "\tt %d:%d:%d:%d:%d:%d:%d:%d:%d\n",
				ter.frequency, ter.bandwidth, ter.code_rate_HP,
				ter.code_rate_LP, ter.modulation, ter.transmission_mode,
				ter.guard_interval, ter.hierarchy, ter.inversion);
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
		for (std::map<int,int>::const_iterator ca(i->second->m_cache.begin());
			ca != i->second->m_cache.end(); ++ca)
			fprintf(f, ",c:%02d%04x", ca->first, ca->second);

		// write cached ca pids
		for (std::set<int>::const_iterator ca(i->second->m_ca.begin());
			ca != i->second->m_ca.end(); ++ca)
			fprintf(f, ",C:%04x", *ca);

		fprintf(f, "\n");
		services++;
	}
	fprintf(f, "end\nHave a lot of bugs!\n");
	eDebug("saved %d channels and %d services!", channels, services);
	fclose(f);
}

eDVBDB::eDVBDB()
{
	load();
}

eDVBDB::~eDVBDB()
{
//	save();
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

RESULT eDVBDB::startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *q)
{
	query = new eDVBDBQuery(this, eServiceReference(), q);
	return 0;
}

DEFINE_REF(eDVBDBQuery);

eDVBDBQuery::eDVBDBQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query): m_db(db), m_query(query)
{
		// TODO: use SOURCE ...
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
	return 1;
}

/* (<name|provider|type|bouquet|satpos|chid> <==|...> <"string"|int>)[AND (..)] */

	/* never, NEVER write a parser in C++! */
RESULT parseExpression(ePtr<eDVBChannelQuery> &res, std::list<std::string>::const_iterator begin, std::list<std::string>::const_iterator end)
{
	std::list<std::string>::const_iterator end_of_exp;
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
			return 1;
		
			/* otherwise we have an operator here.. */
		
		ePtr<eDVBChannelQuery> r2 = res;
		res = new eDVBChannelQuery();
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
	
	if (type == "name")
		res->m_type = eDVBChannelQuery::tName;
	else if (type == "provider")
		res->m_type = eDVBChannelQuery::tProvider;
	else if (type == "type")
		res->m_type = eDVBChannelQuery::tType;
	else if (type == "bouquet")
		res->m_type = eDVBChannelQuery::tBouquet;
	else if (type == "satellitePosition")
		res->m_type = eDVBChannelQuery::tSatellitePosition;
	else if (type == "channelID")
		res->m_type = eDVBChannelQuery::tChannelID;
	else
	{
		eDebug("malformed query: invalid type %s", type.c_str());
		res = 0;
		return 1;
	}
	
	eDebug("type is %d, nice!", res->m_type);
	
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
	
		/* now we recursivly parse that. */
	return  parseExpression(res, tokens.begin(), tokens.end());
/*	
	res = new eDVBChannelQuery();
	res->m_type = eDVBChannelQuery::tName;
	res->m_inverse = 0;
	res->m_string = query;
	return 0; */
}

DEFINE_REF(eDVBChannelQuery);
