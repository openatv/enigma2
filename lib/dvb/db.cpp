#include <errno.h>
#include <lib/dvb/db.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eerror.h>
#include <lib/dvb_si/sdt.h>
#include <lib/dvb_si/descriptor_tag.h>
#include <lib/dvb_si/service_descriptor.h>
#include <lib/dvb_si/satellite_delivery_system_descriptor.h>

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

DEFINE_REF(eDVBDB);

eDVBDB::eDVBDB()
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
			}
			if (line[1]=='c')
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

eDVBDB::~eDVBDB()
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
		if (!ch.m_frontendParameters->getDVBS(sat))
		{
			fprintf(f, "\ts %d:%d:%d:%d:%d:%d\n", 
				sat.frequency, sat.symbol_rate,
				sat.polarisation, sat.fec, sat.inversion,
				sat.orbital_position);
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

