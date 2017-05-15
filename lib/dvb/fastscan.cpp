#include <byteswap.h>
#include <dvbsi++/byte_stream.h>
#include <dvbsi++/descriptor_tag.h>

#include <lib/dvb/db.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/fastscan.h>
#include <lib/base/cfile.h>
#include <lib/base/estring.h>
#include <lib/base/nconfig.h>

FastScanLogicalChannel::FastScanLogicalChannel(const uint8_t *const buffer)
{
	serviceId = UINT16(&buffer[0]);
	hiddenFlag = (buffer[2] >> 6) & 0x01;
	logicalChannelNumber = UINT16(&buffer[2]) & 0x3fff;
}

FastScanLogicalChannel::~FastScanLogicalChannel(void)
{
}

uint16_t FastScanLogicalChannel::getServiceId(void) const
{
	return serviceId;
}

uint8_t FastScanLogicalChannel::getHiddenFlag(void) const
{
	return hiddenFlag;
}

uint16_t FastScanLogicalChannel::getLogicalChannelNumber(void) const
{
	return logicalChannelNumber;
}

FastScanLogicalChannelDescriptor::FastScanLogicalChannelDescriptor(const uint8_t *const buffer)
: Descriptor(buffer)
{
	uint16_t pos = 2;
	uint16_t bytesLeft = descriptorLength;
	uint16_t loopLength = 4;

	while (bytesLeft >= loopLength) {
		channelList.push_back(new FastScanLogicalChannel(&buffer[pos]));
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

FastScanLogicalChannelDescriptor::~FastScanLogicalChannelDescriptor(void)
{
	for (FastScanLogicalChannelListIterator i = channelList.begin(); i != channelList.end(); ++i)
		delete *i;
}

const FastScanLogicalChannelList *FastScanLogicalChannelDescriptor::getChannelList(void) const
{
	return &channelList;
}

FastScanService::FastScanService(const uint8_t * const buffer)
: ServiceDescriptor(&buffer[18])
{
	originalNetworkId = UINT16(&buffer[0]);
	transportStreamId = UINT16(&buffer[2]);
	serviceId = UINT16(&buffer[4]);
	defaultVideoPid = DVB_PID(&buffer[6]);
	defaultAudioPid = DVB_PID(&buffer[8]);
	defaultVideoEcmPid = DVB_PID(&buffer[10]);
	defaultAudioEcmPid = DVB_PID(&buffer[12]);
	defaultPcrPid = DVB_PID(&buffer[14]);
	descriptorLoopLength = DVB_LENGTH(&buffer[16]);
}

FastScanService::~FastScanService(void)
{
}

uint16_t FastScanService::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t FastScanService::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t FastScanService::getServiceId(void) const
{
	return serviceId;
}

uint16_t FastScanService::getDefaultVideoPid(void) const
{
	return defaultVideoPid;
}

uint16_t FastScanService::getDefaultAudioPid(void) const
{
	return defaultAudioPid;
}

uint16_t FastScanService::getDefaultVideoEcmPid(void) const
{
	return defaultVideoEcmPid;
}

uint16_t FastScanService::getDefaultAudioEcmPid(void) const
{
	return defaultAudioEcmPid;
}

uint16_t FastScanService::getDefaultPcrPid(void) const
{
	return defaultPcrPid;
}

FastScanServicesSection::FastScanServicesSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	uint16_t pos = 8;
	uint16_t bytesLeft = sectionLength > 8 ? sectionLength - 8 : 0;
	uint16_t loopLength = 0;

	versionNumber = (buffer[5] >> 1) & 0x1f;

	while (bytesLeft > 17 && bytesLeft >= (loopLength = 18 + DVB_LENGTH(&buffer[pos+16])))
	{
		services.push_back(new FastScanService(&buffer[pos]));
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

FastScanServicesSection::~FastScanServicesSection(void)
{
	for (FastScanServiceListIterator i = services.begin(); i != services.end(); ++i)
		delete *i;
}

uint8_t FastScanServicesSection::getVersion(void) const
{
	return versionNumber;
}

const FastScanServiceList *FastScanServicesSection::getServices(void) const
{
	return &services;
}

FastScanTransportStream::FastScanTransportStream(const uint8_t *const buffer)
: deliverySystem(NULL), serviceList(NULL), logicalChannels(NULL)
{
	transportStreamId = UINT16(&buffer[0]);
	originalNetworkId = UINT16(&buffer[2]);
	descriptorLoopLength = DVB_LENGTH(&buffer[4]);

	uint16_t pos = 6;
	uint16_t bytesLeft = descriptorLoopLength;
	uint16_t loopLength = 0;

	while (bytesLeft > 1 && bytesLeft >= (loopLength = 2 + buffer[pos + 1]))
	{
		switch (buffer[pos])
		{
		case LOGICAL_CHANNEL_DESCRIPTOR:
			logicalChannels = new FastScanLogicalChannelDescriptor(&buffer[pos]);
			break;
		case SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
			deliverySystem = new SatelliteDeliverySystemDescriptor(&buffer[pos]);
			break;
		case SERVICE_LIST_DESCRIPTOR:
			serviceList = new ServiceListDescriptor(&buffer[pos]);
			break;
		}
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

FastScanTransportStream::~FastScanTransportStream(void)
{
	delete deliverySystem;
	delete serviceList;
	delete logicalChannels;
}

uint16_t FastScanTransportStream::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t FastScanTransportStream::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t FastScanTransportStream::getOrbitalPosition(void) const
{
	if (deliverySystem) return deliverySystem->getOrbitalPosition();
	return 0;
}

uint32_t FastScanTransportStream::getFrequency(void) const
{
	if (deliverySystem) return deliverySystem->getFrequency();
	return 0;
}

uint8_t FastScanTransportStream::getPolarization(void) const
{
	if (deliverySystem) return deliverySystem->getPolarization();
	return 0;
}

uint8_t FastScanTransportStream::getRollOff(void) const
{
	if (deliverySystem) return deliverySystem->getRollOff();
	return 0;
}

uint8_t FastScanTransportStream::getModulationSystem(void) const
{
	if (deliverySystem) return deliverySystem->getModulationSystem();
	return 0;
}

uint8_t FastScanTransportStream::getModulation(void) const
{
	if (deliverySystem) return deliverySystem->getModulation();
	return 0;
}

uint32_t FastScanTransportStream::getSymbolRate(void) const
{
	if (deliverySystem) return deliverySystem->getSymbolRate();
	return 0;
}

uint8_t FastScanTransportStream::getFecInner(void) const
{
	if (deliverySystem) return deliverySystem->getFecInner();
	return 0;
}

const ServiceListItemList *FastScanTransportStream::getServiceList(void) const
{
	if (serviceList) return serviceList->getServiceList();
	return NULL;
}

const FastScanLogicalChannelList *FastScanTransportStream::getLogicalChannelList(void) const
{
	if (logicalChannels) return logicalChannels->getChannelList();
	return NULL;
}

FastScanNetworkSection::FastScanNetworkSection(const uint8_t * const buffer)
: LongCrcSection(buffer), NetworkNameDescriptor(&buffer[10])
{
	uint16_t networkdescriptorLength = DVB_LENGTH(&buffer[8]);
	uint16_t pos = 10 + networkdescriptorLength;
	uint16_t bytesLeft = DVB_LENGTH(&buffer[pos]);
	pos += 2;
	uint16_t loopLength = 0;

	versionNumber = (buffer[5] >> 1) & 0x1f;

	while (bytesLeft >= 6 && bytesLeft >= (loopLength = 6 + DVB_LENGTH(&buffer[pos + 4])))
	{
		transportStreams.push_back(new FastScanTransportStream(&buffer[pos]));
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

FastScanNetworkSection::~FastScanNetworkSection(void)
{
	for (FastScanTransportStreamListIterator i = transportStreams.begin(); i != transportStreams.end(); ++i)
		delete *i;
}

uint8_t FastScanNetworkSection::getVersion(void) const
{
	return versionNumber;
}

const FastScanTransportStreamList *FastScanNetworkSection::getTransportStreams(void) const
{
	return &transportStreams;
}

DEFINE_REF(eFastScan);

eFastScan::eFastScan(int pid, const char *providername, eDVBFrontendParametersSatellite transponderparameters, bool originalnumbering, bool fixedserviceinfo, bool createradiobouquet)
{
	m_pid = pid;
	providerName = providername;
	bouquetFilename = replace_all(providerName, " ", "");
	transponderParameters = transponderparameters;
	originalNumbering = originalnumbering;
	useFixedServiceInfo = fixedserviceinfo;
	createRadioBouquet = createradiobouquet;
	versionNumber = -1;
}

eFastScan::~eFastScan()
{
}

void eFastScan::startFile(const char *fnt, const char *fst)
{
	versionNumber = -1;
	{
		CFile file(fst, "rb");
		if (file)
		{
			eFastScanFileTable<FastScanServicesSection> *table = new eFastScanFileTable<FastScanServicesSection>;
			m_ServicesTable = table;
			table->readFile(file);
		}
	}
	{
		CFile file(fnt, "rb");
		if (file)
		{
			eFastScanFileTable<FastScanNetworkSection> *table = new eFastScanFileTable<FastScanNetworkSection>;
			m_NetworkTable = table;
			table->readFile(file);
		}
	}

	if (m_ServicesTable && m_NetworkTable)
	{
		parseResult();
	}
	else
	{
		scanCompleted(-1);
	}

	m_ServicesTable = NULL;
	m_NetworkTable = NULL;
}

void eFastScan::start(int frontendid)
{
	/* scan on fastscan channel */
	ePtr<eDVBResourceManager> res;
	eDVBResourceManager::getInstance(res);
	ePtr<iDVBFrontend> fe;

	versionNumber = -1;

	if (res->allocateRawChannel(m_channel, frontendid))
	{
		eDebug("[eFastScan] failed to allocate fastscan channel!");
		scanCompleted(-1);
		return;
	}

	m_channel->getFrontend(fe);
	m_channel->getDemux(m_demux);

	eDVBFrontendParameters parm;
	parm.setDVBS(transponderParameters);

	fe->tune(parm);

	m_ServicesTable = new eFastScanTable<FastScanServicesSection>;
	m_NetworkTable = new eFastScanTable<FastScanNetworkSection>;
	CONNECT(m_ServicesTable->tableProgress, eFastScan::servicesTableProgress);
	CONNECT(m_NetworkTable->tableProgress, eFastScan::networkTableProgress);
	CONNECT(m_ServicesTable->tableReady, eFastScan::servicesTableReady);
	CONNECT(m_NetworkTable->tableReady, eFastScan::networkTableReady);

	m_ServicesTable->start(m_demux, eDVBFastScanServicesSpec(m_pid));
}

int eFastScan::getVersion()
{
	return versionNumber;
}

void eFastScan::servicesTableProgress(int size, int max)
{
	scanProgress(size * 45 / max);
}

void eFastScan::networkTableProgress(int size, int max)
{
	scanProgress(45 + size * 45 / max);
}

void eFastScan::servicesTableReady(int error)
{
	eDebug("[eFastScan] servicesTableReady %d", error);
	if (error)
	{
		m_channel = NULL;
		m_demux = NULL;
		m_ServicesTable = NULL;
		m_NetworkTable = NULL;
		scanCompleted(-1);
	}
	else
	{
		m_NetworkTable->start(m_demux, eDVBFastScanNetworkSpec(m_pid));
	}
}

void eFastScan::networkTableReady(int error)
{
	eDebug("[eFastScan] networkTableReady %d", error);

	if (!error)
	{
		parseResult();
	}
	else
	{
		scanCompleted(-1);
	}

	m_channel = NULL;
	m_demux = NULL;
	m_ServicesTable = NULL;
	m_NetworkTable = NULL;
}

void eFastScan::fillBouquet(eBouquet *bouquet, std::map<int, eServiceReferenceDVB> &numbered_channels)
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

void eFastScan::parseResult()
{
	ePtr<iDVBChannelList> db;
	ePtr<eDVBResourceManager> res;
	eDVBResourceManager::getInstance(res);
	res->getChannelList(db);
	eDVBDB *dvbdb = eDVBDB::getInstance();

	std::vector<FastScanNetworkSection*> networksections = m_NetworkTable->getSections();
	std::vector<FastScanServicesSection*> servicessections = m_ServicesTable->getSections();

	std::map<uint16_t, std::map<uint16_t, std::map<uint16_t, int> > > service_orbital_position;
	std::map<int, eServiceReferenceDVB> numbered_channels;
	std::map<int, eServiceReferenceDVB> radio_channels;

	if (!networksections.empty()) versionNumber = networksections[0]->getVersion();

	for (unsigned int i = 0; i < networksections.size(); i++)
	{
		const FastScanTransportStreamList *transportstreams = networksections[i]->getTransportStreams();
		for (FastScanTransportStreamListConstIterator it = transportstreams->begin(); it != transportstreams->end(); it++)
		{
			eDVBChannelID chid;
			int orbitalposbcd = (*it)->getOrbitalPosition();
			int orbitalpos = (orbitalposbcd & 0x0f) + ((orbitalposbcd >> 4) & 0x0f) * 10 + ((orbitalposbcd >> 8) & 0x0f) * 100;
			chid.dvbnamespace = eDVBNamespace(orbitalpos<<16);
			chid.transport_stream_id = eTransportStreamID((*it)->getTransportStreamId());
			chid.original_network_id = eOriginalNetworkID((*it)->getOriginalNetworkId());
			ePtr<eDVBFrontendParameters> parm = new eDVBFrontendParameters();

			eDVBFrontendParametersSatellite fesat;
			fesat.frequency = (*it)->getFrequency() * 10;
			fesat.symbol_rate = (*it)->getSymbolRate() * 100;
			fesat.polarisation = (*it)->getPolarization();
			fesat.fec = (*it)->getFecInner();
			fesat.inversion = eDVBFrontendParametersSatellite::Inversion_Unknown;
			fesat.orbital_position = orbitalpos;
			fesat.system = (*it)->getModulationSystem();
			fesat.modulation = (*it)->getModulation();
			fesat.rolloff = (*it)->getRollOff();
			fesat.pilot = eDVBFrontendParametersSatellite::Pilot_Unknown;
			fesat.is_id = NO_STREAM_ID_FILTER;
			fesat.pls_mode = eDVBFrontendParametersSatellite::PLS_Root;
			fesat.pls_code = 1;

			parm->setDVBS(fesat);
			db->addChannelToList(chid, parm);

			std::map<int, int> servicetypemap;

			const ServiceListItemList *services = (*it)->getServiceList();
			if (services)
				for (ServiceListItemConstIterator service = services->begin(); service != services->end(); service++)
					servicetypemap[(*service)->getServiceId()] = (*service)->getServiceType();
			const FastScanLogicalChannelList *channels = (*it)->getLogicalChannelList();
			if (channels)
			{
				for (FastScanLogicalChannelListConstIterator channel = channels->begin(); channel != channels->end(); channel++)
				{
					int type = servicetypemap[(*channel)->getServiceId()];
					eServiceReferenceDVB ref(orbitalpos << 16, (*it)->getTransportStreamId(), (*it)->getOriginalNetworkId(), (*channel)->getServiceId(), type);
					service_orbital_position[(*it)->getTransportStreamId()][(*it)->getOriginalNetworkId()][(*channel)->getServiceId()] = orbitalpos;
					if (createRadioBouquet)
					{
						switch (type)
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
							numbered_channels[(*channel)->getLogicalChannelNumber()] = ref;
							break;
						case 2: /* digital radio sound service */
						case 10: /* advanced codec digital radio sound service */
							radio_channels[(*channel)->getLogicalChannelNumber()] = ref;
							break;
						}
					}
					else
						numbered_channels[(*channel)->getLogicalChannelNumber()] = ref;
				}
			}
		}
	}

	std::map<eServiceReferenceDVB, ePtr<eDVBService> > new_services;

	for (unsigned int i = 0; i < servicessections.size(); i++)
	{
		const FastScanServiceList *services = servicessections[i]->getServices();
		for (FastScanServiceListConstIterator it = services->begin(); it != services->end(); it++)
		{
			eServiceReferenceDVB ref(service_orbital_position[(*it)->getTransportStreamId()][(*it)->getOriginalNetworkId()][(*it)->getServiceId()] << 16, (*it)->getTransportStreamId(), (*it)->getOriginalNetworkId(), (*it)->getServiceId(), (*it)->getServiceType());
			eDVBService *service = new eDVBService;
			service->m_service_name = convertDVBUTF8((*it)->getServiceName());
			service->genSortName();
			service->m_provider_name = convertDVBUTF8((*it)->getServiceProviderName());
			/*
			 * NOTE: it makes no sense to store the default video pid, without knowing the video stream type.
			 * However, assuming there is only one video stream, the cache information will be fixed
			 * (and the missing video stream type added) as soon as the channel is selected for the first time.
			 */
			service->setCacheEntry(eDVBService::cVPID, (*it)->getDefaultVideoPid());
			/*
			 * NOTE: it makes no sense to store the default audio pid, we do not have any information about
			 * the stream type (so we risk storing the wrong information in the cache).
			 * When we have only one audio stream, the information will be fixed as soon as the channel
			 * is selected for the first time.
			 * However, when the channel has more than one audio stream, the information will not be fixed
			 * untill the user selects a different audio track.
			 * So we will not store the default audio pid in the cache.
			 */
#if 0
			service->setCacheEntry(eDVBService::cMPEGAPID, (*it)->getDefaultAudioPid());
#endif
			service->setCacheEntry(eDVBService::cPCRPID, (*it)->getDefaultPcrPid());
			if (useFixedServiceInfo)
			{
				/* we want to use the fixed settings from our fastscan table, don't allow them to be overruled by sdt and nit */
				service->m_flags = eDVBService::dxHoldName | eDVBService::dxNoSDT;
			}
			new_services[ref] = service;
		}
	}

	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::const_iterator
		service(new_services.begin()); service != new_services.end(); ++service)
	{
		ePtr<eDVBService> dvb_service;
		if (!db->getService(service->first, dvb_service))
		{
			if (useFixedServiceInfo)
			{
				/*
				 * replace current settings by fastscan settings,
				 * note that we don't obey the dxHoldName flag here,
				 * as the user explicitly gave us permission to use
				 * the fastscan names.
				 */
				dvb_service->m_service_name = service->second->m_service_name;
				dvb_service->m_service_name_sort = service->second->m_service_name_sort;
				dvb_service->m_provider_name = service->second->m_provider_name;
			}
			dvb_service->m_flags |= service->second->m_flags;
			if (service->second->m_ca.size())
				dvb_service->m_ca = service->second->m_ca;
		}
		else
		{
			db->addService(service->first, service->second);
			service->second->m_flags |= eDVBService::dxNewFound;
		}
	}

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
			/* fill our fastscan bouquet */
			fillBouquet(bouquet, numbered_channels);
		}
		else
		{
			eDebug("[eFastScan] failed to create bouquet!");
		}
	}
	else
	{
		/* single bouquet mode, fill the favourites bouquet */
		eBouquet *bouquet = NULL;
		eServiceReference favref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet");
		if (!db->getBouquet(favref, bouquet))
		{
			fillBouquet(bouquet, numbered_channels);
		}
	}

	if (!radio_channels.empty())
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
				/* fill our fastscan bouquet */
				fillBouquet(bouquet, radio_channels);
			}
			else
			{
				eDebug("[eFastScan] failed to create bouquet!");
			}
		}
		else
		{
			/* single bouquet, fill the favourites bouquet */
			eBouquet *bouquet = NULL;
			eServiceReference favref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"userbouquet.favourites.radio\" ORDER BY bouquet");
			if (!db->getBouquet(favref, bouquet))
			{
				fillBouquet(bouquet, radio_channels);
			}
		}
	}

	/* force services to be saved */
	if (dvbdb)
	{
		dvbdb->saveServicelist();
	}

	scanProgress(100);
	scanCompleted(numbered_channels.empty() ? -1 : numbered_channels.size() + radio_channels.size());
}
