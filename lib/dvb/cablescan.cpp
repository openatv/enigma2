#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/ca_identifier_descriptor.h>
#include <dvbsi++/logical_channel_descriptor.h>

#include <lib/dvb/db.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/cablescan.h>
#include <lib/base/estring.h>
#include <lib/base/nconfig.h>

DEFINE_REF(eCableScan);

eCableScan::eCableScan(int networkid, unsigned int frequency, unsigned int symbolrate, int modulation, bool originalnumbering, bool hdlist)
{
	networkId = networkid;
	initialFrequency = frequency;
	initialSymbolRate = symbolrate;
	initialModulation = modulation;
	originalNumbering = originalnumbering;
	hdList = hdlist;
}

eCableScan::~eCableScan()
{
}

void eCableScan::start(int frontendid)
{
	/* scan on specified channel */
	ePtr<eDVBResourceManager> res;
	eDVBResourceManager::getInstance(res);
	ePtr<iDVBFrontend> fe;

	if (res->allocateRawChannel(m_channel, frontendid))
	{
		eDebug("[eCableScan] failed to allocate channel!");
		scanCompleted(-1);
		return;
	}

	m_channel->getFrontend(fe);
	m_channel->getDemux(m_demux);

	eDVBFrontendParametersCable cable;
	cable.frequency = initialFrequency;
	cable.fec_inner = eDVBFrontendParametersCable::FEC_Auto;
	cable.inversion = eDVBFrontendParametersCable::Inversion_Unknown;
	cable.symbol_rate = initialSymbolRate;
	cable.modulation = initialModulation;

	eDVBFrontendParameters parm;
	parm.setDVBC(cable);

	fe->tune(parm);

	m_NIT = new eTable<NetworkInformationSection>;
	CONNECT(m_NIT->tableReady, eCableScan::NITReady);
	m_NIT->start(m_demux, eDVBNITSpec(networkId));
}

void eCableScan::NITReady(int error)
{
	eDebug("[eCableScan] NITReady %d", error);

	if (!error)
	{
		parseNIT();
		nextChannel();
	}
	else
	{
		scanCompleted(-1);
	}

	m_NIT = NULL;
}

void eCableScan::SDTReady(int error)
{
	eDebug("[eCableScan] SDTReady %d", error);

	if (!error)
	{
		parseSDT();
	}

	nextChannel();
}

int eCableScan::nextChannel()
{
	ePtr<iDVBFrontend> fe;

	m_SDT = NULL;

	if (scanChannels.empty())
	{
		m_channel = NULL;
		createBouquets();
		return 1;
	}

	scanProgress(100 - (scanChannels.size() * 90) / totalChannels);

	currentScanChannel = scanChannels.front();
	scanChannels.pop_front();

	if (m_channel->getFrontend(fe))
	{
		m_channel = NULL;
		scanCompleted(-1);
		return -1;
	}

	if (fe->tune(*currentScanChannel))
		return nextChannel();

	m_SDT = new eTable<ServiceDescriptionSection>;
	CONNECT(m_SDT->tableReady, eCableScan::SDTReady);
	eDVBTableSpec spec = eDVBSDTSpec();
	/*
	 * limit the SDT timeout to 5s (e2 defaults to 60s),
	 * so we do not have to wait for too long when channels
	 * from the NIT are not available.
	 * We should actually implement a channel statechange handler
	 * (to receive tune failed status) but limiting the SDT reader
	 * timeout has the same effect, and is a lot simpler
	 */
	spec.timeout = 5000;
	m_SDT->start(m_demux, spec);
	return 0;
}

void eCableScan::parseNIT()
{
	std::vector<NetworkInformationSection*>::const_iterator i;
	for (i = m_NIT->getSections().begin(); i != m_NIT->getSections().end(); ++i)
	{
		const TransportStreamInfoList &tsinfovec = *(*i)->getTsInfo();

		for (TransportStreamInfoConstIterator tsinfo(tsinfovec.begin());
			tsinfo != tsinfovec.end(); ++tsinfo)
		{
			for (DescriptorConstIterator desc = (*tsinfo)->getDescriptors()->begin();
					desc != (*tsinfo)->getDescriptors()->end(); ++desc)
			{
				switch ((*desc)->getTag())
				{
				case CABLE_DELIVERY_SYSTEM_DESCRIPTOR:
				{
					CableDeliverySystemDescriptor &d = (CableDeliverySystemDescriptor&)**desc;
					ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
					eDVBFrontendParametersCable cable;
					cable.set(d);
					feparm->setDVBC(cable);
					scanChannels.push_back(feparm);
					break;
				}
				case LOGICAL_CHANNEL_DESCRIPTOR:
				{
					unsigned char buf[(*desc)->getLength() + 2];
					(*desc)->writeToBuffer(buf);
					LogicalChannelDescriptor d(buf);
					const LogicalChannelList &channels = *d.getChannelList();
					for (LogicalChannelListConstIterator c(channels.begin()); c != channels.end(); ++c)
					{
						serviceIdToChannelId[(*c)->getServiceId()] = (*c)->getLogicalChannelNumber();
					}
					break;
				}
				case HD_SIMULCAST_LOGICAL_CHANNEL_DESCRIPTOR:
				{
					unsigned char buf[(*desc)->getLength() + 2];
					(*desc)->writeToBuffer(buf);
					LogicalChannelDescriptor d(buf);
					const LogicalChannelList &channels = *d.getChannelList();
					for (LogicalChannelListConstIterator c(channels.begin()); c != channels.end(); ++c)
					{
						serviceIdToHDChannelId[(*c)->getServiceId()] = (*c)->getLogicalChannelNumber();
					}
					break;
				}
				default:
					break;
				}
			}
		}
	}
	totalChannels = scanChannels.size();
}

void eCableScan::parseSDT()
{
	unsigned long hash = 0;
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;

	if (m_SDT->getSections().empty()) return;

	eDVBResourceManager::getInstance(res);
	res->getChannelList(db);

	currentScanChannel->getHash(hash);
	eDVBNamespace dvbnamespace(hash & ~0xFFFF);

	eDVBChannelID chid(dvbnamespace, (**m_SDT->getSections().begin()).getTransportStreamId(), (**m_SDT->getSections().begin()).getOriginalNetworkId());

	db->addChannelToList(chid, currentScanChannel);

	std::vector<ServiceDescriptionSection*>::const_iterator i;
	for (i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
	{
		const ServiceDescriptionSection &sdt = **i;
		const ServiceDescriptionList &services = *sdt.getDescriptions();
		for (ServiceDescriptionConstIterator s(services.begin()); s != services.end(); ++s)
		{
			unsigned short service_id = (*s)->getServiceId();
			eServiceReferenceDVB ref;
			ePtr<eDVBService> service = new eDVBService;

			ref.set(chid);
			ref.setServiceID(service_id);

			for (DescriptorConstIterator desc = (*s)->getDescriptors()->begin();
					desc != (*s)->getDescriptors()->end(); ++desc)
			{
				switch ((*desc)->getTag())
				{
				case SERVICE_DESCRIPTOR:
				{
					ServiceDescriptor &d = (ServiceDescriptor&)**desc;
					int servicetype = d.getServiceType();
					ref.setServiceType(servicetype);
					service->m_service_name = convertDVBUTF8(d.getServiceName());
					service->genSortName();
					service->m_provider_name = convertDVBUTF8(d.getServiceProviderName());
					providerNames[service->m_provider_name]++;
					break;
				}
				case CA_IDENTIFIER_DESCRIPTOR:
				{
					CaIdentifierDescriptor &d = (CaIdentifierDescriptor&)**desc;
					const CaSystemIdList &caids = *d.getCaSystemIds();
					for (CaSystemIdList::const_iterator i(caids.begin()); i != caids.end(); ++i)
					{
						service->m_ca.push_front(*i);
					}
					break;
				}
				default:
					break;
				}
			}
			ePtr<eDVBService> dvb_service;
			if (!db->getService(ref, dvb_service))
			{
				dvb_service->m_flags |= service->m_flags;
				if (service->m_ca.size())
					dvb_service->m_ca = service->m_ca;
			}
			else
			{
				db->addService(ref, service);
				service->m_flags |= eDVBService::dxNewFound;
			}
			int logicalchannelid = 0;
			if (hdList)
			{
				std::map<int, int>::const_iterator it = serviceIdToHDChannelId.find(service_id);
				if (it != serviceIdToHDChannelId.end())
				{
					logicalchannelid = it->second;
				}
			}
			if (!logicalchannelid)
			{
				std::map<int, int>::const_iterator it = serviceIdToChannelId.find(service_id);
				if (it != serviceIdToChannelId.end())
				{
					logicalchannelid = it->second;

					/* check if logical logicalchannalid was already used in the TV numberedServiceRefs list to give priority when the serviceid was already used in the HD
					logicalchannelid list */
					std::map<int, eServiceReferenceDVB>::const_iterator it = numberedServiceRefs.find(logicalchannelid);
					if (it != numberedServiceRefs.end())
					{
						logicalchannelid = 0;
					}
				}
			}
			if (logicalchannelid)
			{
				switch (ref.getServiceType())
				{
				case 1: /* digital television service */
				case 4: /* nvod reference service (NYI) */
				case 17: /* MPEG-2 HD digital television service */
				case 22: /* advanced codec SD digital television */
				case 24: /* advanced codec SD NVOD reference service (NYI) */
				case 25: /* advanced codec HD digital television */
				case 27: /* advanced codec HD NVOD reference service (NYI) */
				default:
					/* just assume that anything *not* radio is tv */
					numberedServiceRefs[logicalchannelid] = ref;
					break;
				case 2: /* digital radio sound service */
				case 10: /* advanced codec digital radio sound service */
					numberedRadioServiceRefs[logicalchannelid] = ref;
					break;
				}
			}
		}
	}
}

void eCableScan::fillBouquet(eBouquet *bouquet, std::map<int, eServiceReferenceDVB> &numbered_channels)
{
	if (bouquet)
	{
		bouquet->m_bouquet_name = providerName;
		int number = 1;
		for (std::map<int, eServiceReferenceDVB>::const_iterator
			service(numbered_channels.begin()); service != numbered_channels.end(); ++service)
		{
			if (originalNumbering)
			{
				while (number < service->first)
				{
					eServiceReference ref(eServiceReference::idDVB, eServiceReference::isMarker | eServiceReference::isNumberedMarker);
					ref.setName("-");
					bouquet->m_services.push_back(ref);
					number++;
				}
			}
			bouquet->m_services.push_back(service->second);
			number++;
		}
		bouquet->flushChanges();
		eDVBDB::getInstance()->renumberBouquet();
	}
}

void eCableScan::createBouquets()
{
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;
	eDVBResourceManager::getInstance(res);
	res->getChannelList(db);
	eDVBDB *dvbdb = eDVBDB::getInstance();

	int most = 0;
	for (std::map<std::string, int>::iterator it = providerNames.begin(); it != providerNames.end(); ++it)
	{
		if (it->second > most)
		{
			most = it->second;
			providerName = it->first;
		}
	}
	bouquetFilename = replace_all(providerName, " ", "");

	bool multibouquet = eConfigManager::getConfigBoolValue("config.usage.multibouquet");

	if (multibouquet)
	{
		std::string bouquetname = "userbouquet." + bouquetFilename + ".tv";
		std::string bouquetquery = "FROM BOUQUET \"" + bouquetname + "\" ORDER BY bouquet";
		eServiceReference bouquetref(eServiceReference::idDVB, eServiceReference::flagDirectory, bouquetquery);
		bouquetref.setData(0, 1); /* bouquet 'servicetype' tv */
		eBouquet *bouquet = NULL;
		eServiceReference rootref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet");

		if (!db->getBouquet(bouquetref, bouquet) && bouquet)
		{
			/* bouquet already exists, empty it before we continue */
			bouquet->m_services.clear();
		}
		else
		{
			/* bouquet doesn't yet exist, create a new one */
			if (!db->getBouquet(rootref, bouquet) && bouquet)
			{
				bouquet->m_services.push_front(bouquetref);
				bouquet->flushChanges();
			}
			/* loading the bouquet seems to be the only way to add it to the bouquet list */
			dvbdb->loadBouquet(bouquetname.c_str());
			/* and now that it has been added to the list, we can find it */
			db->getBouquet(bouquetref, bouquet);
		}

		if (bouquet)
		{
			/* fill our cable bouquet */
			fillBouquet(bouquet, numberedServiceRefs);

		}
		else
		{
			eDebug("[eCableScan] failed to create bouquet!");
		}
	}
	else
	{
		/* single bouquet mode, fill the favourites bouquet */
		eBouquet *bouquet = NULL;
		eServiceReference favref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet");
		if (!db->getBouquet(favref, bouquet))
		{
			fillBouquet(bouquet, numberedServiceRefs);
		}
	}

	if (!numberedRadioServiceRefs.empty())
	{
		if (multibouquet)
		{
			std::string bouquetname = "userbouquet." + bouquetFilename + ".radio";
			std::string bouquetquery = "FROM BOUQUET \"" + bouquetname + "\" ORDER BY bouquet";
			eServiceReference bouquetref(eServiceReference::idDVB, eServiceReference::flagDirectory, bouquetquery);
			bouquetref.setData(0, 2); /* bouquet 'servicetype' radio */
			eBouquet *bouquet = NULL;
			eServiceReference rootref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet");

			if (!db->getBouquet(bouquetref, bouquet) && bouquet)
			{
				/* bouquet already exists, empty it before we continue */
				bouquet->m_services.clear();
			}
			else
			{
				/* bouquet doesn't yet exist, create a new one */
				if (!db->getBouquet(rootref, bouquet) && bouquet)
				{
					bouquet->m_services.push_front(bouquetref);
					bouquet->flushChanges();
				}
				/* loading the bouquet seems to be the only way to add it to the bouquet list */
				dvbdb->loadBouquet(bouquetname.c_str());
				/* and now that it has been added to the list, we can find it */
				db->getBouquet(bouquetref, bouquet);
			}

			if (bouquet)
			{
				/* fill our cable bouquet */
				fillBouquet(bouquet, numberedRadioServiceRefs);
			}
			else
			{
				eDebug("[eCableScan] failed to create bouquet!");
			}
		}
		else
		{
			/* single bouquet, fill the favourites bouquet */
			eBouquet *bouquet = NULL;
			eServiceReference favref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"userbouquet.favourites.radio\" ORDER BY bouquet");
			if (!db->getBouquet(favref, bouquet))
			{
				fillBouquet(bouquet, numberedRadioServiceRefs);
			}
		}
	}

	/* force services to be saved */
	if (dvbdb)
	{
		dvbdb->saveServicelist();
	}

	scanProgress(100);
	scanCompleted(numberedServiceRefs.empty() ? -1 : numberedServiceRefs.size() + numberedRadioServiceRefs.size());
}
