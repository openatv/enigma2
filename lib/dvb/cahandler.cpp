#include <unistd.h>
#include <string.h>
#include <stdint.h>

#include <dvbsi++/ca_descriptor.h>
#include <dvbsi++/ca_program_map_section.h>
#include <dvbsi++/descriptor_tag.h>
#include <lib/dvb/db.h>
#include <lib/dvb/cahandler.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <linux/dvb/ca.h>
#include <map>

// Cache serviceId per DVB service reference to ensure OSCam always sees the same ID
// This prevents CW delivery issues when switching between StreamRelay and Live-TV
static std::map<eServiceReferenceDVB, uint32_t> s_serviceId_cache;

ePMTClient::ePMTClient(eDVBCAHandler *handler, int socket) : eUnixDomainSocket(socket, 1, eApp), parent(handler)
{
	receivedTag[0] = 0;
	receivedLength = 0;
	receivedData = NULL;
	m_protocolVersion = -1;
	m_serverInfoReceived = false;
	memset(m_capmt_buffer, 0, sizeof(m_capmt_buffer));
	m_capmt_buffer_len = 0;
	CONNECT(connectionClosed_, ePMTClient::connectionLost);
	CONNECT(readyRead_, ePMTClient::dataAvailable);

	sendClientInfo();
}

void ePMTClient::connectionLost()
{
	if (parent) parent->connectionLost(this);
}

void ePMTClient::dataAvailable()
{
	while (1)
	{
		/* this handler might be called multiple times (by the socket notifier), till we have the complete message */

		if (receivedLength < 1)
		{
			if (bytesAvailable() < 6) return;
			receivedLength = readBlock((char*)receivedHeader, 1);
			// check OSCam protocol version -> version 3 starts with 0xA5
			if ((m_protocolVersion == 3 || m_protocolVersion == -1) && receivedHeader[0] == 0xA5)
			{
				// OSCam protocol 3: read 4 byte msgid + first byte of tag
				readBlock((char*)receivedHeader, 5);
				receivedTag[0] = receivedHeader[4];
			}
			else if (m_protocolVersion == 3 && receivedHeader[0] != 0xA5)
			{
				eDebug("[ePMTClient] Error: Packet malformed! Byte %02X read instead of 0xA5 (message start) -> skip available bytes", receivedHeader[0]);
				int b = bytesAvailable();
				char* tmp = new char[b];
				readBlock(tmp, b);
				delete[] tmp;
				// Reset state machine after error to allow recovery
				receivedLength = 0;
				memset(receivedHeader, 0, 5);
				continue; // Try to parse next packet
			}
			else
				receivedTag[0] = receivedHeader[0];
		}

		if (receivedLength < 4)
		{
			if (bytesAvailable() < 3) return;
			receivedLength += readBlock((char*)receivedTag + receivedLength, 4 - receivedLength);
			if (receivedLength < 4) return;
		}

		if (receivedTag[0] == 0x40 && receivedTag[1] == 0x10 && receivedTag[2] == 0x6F && receivedTag[3] == 0x86) // DVBAPI_CA_SET_DESCR (0x40106F86)
		{
			if (!processCaSetDescrPacket()) return;
		}
		else if (receivedTag[0] == 0x40 && receivedTag[1] == 0x0C && receivedTag[2] == 0x6F && receivedTag[3] == 0x88) // DVBAPI_CA_SET_DESCR_MODE (0x400C6F88)
		{
			// CA_SET_DESCR_MODE packet structure (after 0xA5 + msgid + tag): total 13 bytes to skip
			int skipLength = 13;
			if (bytesAvailable() < skipLength)
				return;
			char skipBuf[16];
			readBlock(skipBuf, skipLength);
		}
		else if (receivedTag[0] == 0xFF && receivedTag[1] == 0xFF && receivedTag[2] == 0x00 && receivedTag[3] == 0x02) // DVBAPI_SERVER_INFO (0xFFFF0002)
		{
			if (!processServerInfoPacket()) return;
		}
		else if (receivedTag[0] == 0xFF && receivedTag[1] == 0xFF && receivedTag[2] == 0x00 && receivedTag[3] == 0x03) // DVBAPI_ECM_INFO (0xFFFF0003)
		{
			if (!processEcmInfoPacket()) return;
		}
		else
		{
			// Unknown packet type - log and skip
			eDebug("[ePMTClient] Unknown packet tag: %02X %02X %02X %02X (msgid: %02X%02X%02X%02X) - skipping",
				receivedTag[0], receivedTag[1], receivedTag[2], receivedTag[3],
				receivedHeader[0], receivedHeader[1], receivedHeader[2], receivedHeader[3]);
		}

		delete[] receivedData;
		receivedData = NULL;
		receivedLength = 0;
		memset(receivedHeader, 0, 5);
	}
}

void ePMTClient::sendClientInfo()
{
	char data[20];
	memset(data, 0, sizeof(data));
	data[0] = 0xFF; // DVBAPI_CLIENT_INFO 0xFFFF0001
	data[1] = 0xFF;
	data[2] = 0x00;
	data[3] = 0x01;
	data[4] = 0x00; // DVBAPI_PROTOCOL_VERSION 3
	data[5] = 0x03;
	sprintf(data + 7, "Enigma2");
	data[6] = 7;    // Text length

	eDebug("[ePMTClient] sendClientInfo");
	writeBlock((const char*)data, 14);
}

bool ePMTClient::processCaSetDescrPacket()
{
	int readDataLength = receivedLength - 4;
	int fixDataLength = 17;
	int read;
	uint32_t serviceId;

	if (receivedData == NULL)
		receivedData = new unsigned char[fixDataLength];
	if (bytesAvailable() < fixDataLength - readDataLength) return false;
	read = readBlock((char*)receivedData + readDataLength, fixDataLength - readDataLength);
	receivedLength += read;
	readDataLength += read;
	if (readDataLength == fixDataLength)
	{
		ca_descr_t descr;
		memcpy(&descr, receivedData + 1, sizeof(ca_descr_t));
		descr.index = ntohl(descr.index);
		descr.parity = ntohl(descr.parity);
		memcpy(&serviceId, receivedHeader, sizeof(uint32_t)); // msgid
		serviceId = ntohl(serviceId);

		eServiceReferenceDVB service;
		if (parent->getServiceReference(service, serviceId) == 0)
		{
			eDebug("[ePMTClient] CaSetDescr: Service %s", service.toString().c_str());
			eTraceNoNewLineStart("[ePMTClient] CaSetDescr: ServiceId %d, Parity %d, CW:", serviceId, descr.parity);
			for (int i = 0; i < 8; i++)
				eTraceNoNewLine(" %02X", descr.cw[i]);
			eTraceNoNewLine("\n");
			// Get CAID from ECM_INFO (if available)
			uint16_t caid = 0;
			auto it = parent->m_service_caid.find(serviceId);
			if (it != parent->m_service_caid.end())
				caid = it->second;
			parent->receivedCw(service, descr.parity, (const char*)descr.cw, caid);
		}
		return true;
	}
	return false;
}

bool ePMTClient::processServerInfoPacket()
{
	int readDataLength = receivedLength - 4;
	int fixDataLength = 3; // fix part: 2 byte protocol version + 1 byte info len
	int read;

	if (receivedData == NULL)
		receivedData = new unsigned char[260]; // max 256 byte info + 2 bytes protocol version + 1 byte info len + 1 NULL byte

	if (readDataLength < fixDataLength)
	{
		if (bytesAvailable() < fixDataLength - readDataLength) return false;
		read = readBlock((char*)receivedData + readDataLength, fixDataLength - readDataLength);
		receivedLength += read;
		readDataLength += read;
	}
	if (readDataLength >= fixDataLength)
	{
		readDataLength -= fixDataLength;
		int infoLength = receivedData[2];
		if (bytesAvailable() < infoLength - readDataLength) return false;
		read = readBlock((char*)receivedData + fixDataLength + readDataLength, infoLength - readDataLength);
		receivedLength += read;
		readDataLength += read;
		if (readDataLength == infoLength)
		{
			uint16_t serverProtocolVersion;
			memcpy(&serverProtocolVersion, receivedData, sizeof(uint16_t)); // msgid
			serverProtocolVersion = ntohs(serverProtocolVersion);
			if (serverProtocolVersion < 3)
				m_protocolVersion = serverProtocolVersion;
			else
				m_protocolVersion = 3;
			receivedData[fixDataLength + infoLength] = '\0';
			eDebug("[ePMTClient] ServerInfo: Protocol %u, Info: %s", serverProtocolVersion, receivedData + fixDataLength);

			m_serverInfoReceived = true;
			if (m_capmt_buffer_len > 0)
			{
				writeCAPMTObject(m_capmt_buffer, m_capmt_buffer_len);
				m_capmt_buffer_len = 0;
			}
			return true;
		}
	}
	return false;
}

bool ePMTClient::processEcmInfoPacket()
{
	int readDataLength = receivedLength - 4;
	int fixDataLength = 15; // fix part: 2 byte program number + 2 byte caid + 2 byte pid + 4 byte prov + 4 byte ecmtime + 1 hops
	int read, pos = 0, i = 0, old_pos;
	uint32_t serviceId, providerId, ecmTime;
	uint16_t program, caid, pid;
	int hops = -1;
	unsigned char cardsystem[257]; // max 256 byte + 1 NULL byte
	unsigned char reader[257];
	unsigned char from[257];
	unsigned char protocol[257];
	unsigned char* dest;

	if (receivedData == NULL)
	{
		receivedData = new unsigned char[1041]; // fix part 15 byte + 4 strings * a max 256 byte + 1 byte hop
		memset(receivedData, 0 , 1041);
	}
	if (readDataLength < fixDataLength)
	{
		if (bytesAvailable() < fixDataLength - readDataLength) return false;
		read = readBlock((char*)receivedData + readDataLength, fixDataLength - readDataLength);
		receivedLength += read;
		readDataLength += read;
	}
	if (readDataLength >= fixDataLength)
	{
		readDataLength -= fixDataLength;
		while (bytesAvailable())
		{
			// read cardsystem name, reader, from, protocol strings
			while (pos < readDataLength && i < 4)
			{
				old_pos = pos + 1;
				pos += receivedData[fixDataLength + pos] + 1; // 1 byte string len
				i++;
			}
			if (pos == readDataLength && i > 0) // string i fully read
			{
				if (i == 1)
					dest = cardsystem;
				else if (i == 2)
					dest = reader;
				else if (i == 3)
					dest = from;
				else if (i == 4)
					dest = protocol;

				unsigned char* str = receivedData + fixDataLength + old_pos;
				if (pos - old_pos > 0)
				{
					memcpy(dest, str, pos - old_pos);
					dest[pos - old_pos] = '\0';
				}
				else
					dest[0] = '\0';

				if (i == 4)
				{
					read = readBlock((char*)receivedData + fixDataLength + readDataLength, 1);
					hops = receivedData[fixDataLength + readDataLength];

					// Extract fixed fields
					memcpy(&serviceId, receivedHeader, sizeof(uint32_t)); // msgid
					serviceId = ntohl(serviceId);

					memcpy(&program, receivedData + 1, sizeof(uint16_t));
					program = ntohs(program);
					memcpy(&caid, receivedData + 3, sizeof(uint16_t));
					caid = ntohs(caid);
					memcpy(&pid, receivedData + 5, sizeof(uint16_t));
					pid = ntohs(pid);
					memcpy(&providerId, receivedData + 7, sizeof(uint32_t));
					providerId = ntohl(providerId);
					memcpy(&ecmTime, receivedData + 11, sizeof(uint32_t));
					ecmTime = ntohl(ecmTime);

					eServiceReferenceDVB service;
					if (parent->getServiceReference(service, serviceId) == 0)
					{
						eDebug("[ePMTClient] ECM Info %s", service.toString().c_str());
					}
					// Store CAID for this service (will be sent with next CW)
					parent->m_service_caid[serviceId] = caid;
					eTrace("[ePMTClient] ECM Info serviceId %u, caid %04X, ecmTime %u, cardsystem %s, reader %s, from %s, protocol %s, hops %d", serviceId, caid, ecmTime, cardsystem, reader, from, protocol, hops);

					return true;
				}
			}

			int bytesToRead = (pos == readDataLength) ? 1 : pos - readDataLength;
			if (bytesAvailable() < bytesToRead) return false;
			read = readBlock((char*)receivedData + fixDataLength + readDataLength, bytesToRead);
			receivedLength += read;
			readDataLength += read;
		}
	}
	return false;
}

int ePMTClient::writeCAPMTObject(const char* capmt, int len)
{
	if (m_serverInfoReceived)
	{
		if (m_protocolVersion < 3)
		{
			return writeBlock((capmt + 5), len); // skip extra header
		}
		else
		{
			len += 5;
			return writeBlock(capmt, len);
		}
	}
	// store packet until server info was received
	memcpy(m_capmt_buffer, capmt, len);
	m_capmt_buffer_len = len;
	return 0;
}


eDVBCAHandler *eDVBCAHandler::instance = NULL;

DEFINE_REF(eDVBCAHandler);

eDVBCAHandler::eDVBCAHandler()
 : eServerSocket(PMT_SERVER_SOCKET, eApp), serviceLeft(eTimer::create(eApp))
{
	serviceIdCounter = 1;
	if (instance == NULL)
	{
		instance = this;
	}
	CONNECT(serviceLeft->timeout, eDVBCAHandler::serviceGone);
}

eDVBCAHandler::~eDVBCAHandler()
{
	if (instance == this)
	{
		instance = NULL;
	}
	for (ePtrList<ePMTClient>::iterator it = clients.begin(); it != clients.end(); )
	{
		delete *it;
		it = clients.erase(it);
	}
}

void eDVBCAHandler::newConnection(int socket)
{
	ePMTClient *client = new ePMTClient(this, socket);
	clients.push_back(client);

	/* inform the new client about our current services, if we have any */
	distributeCAPMT();
}

void eDVBCAHandler::connectionLost(ePMTClient *client)
{
	ePtrList<ePMTClient>::iterator it = std::find(clients.begin(), clients.end(), client );
	if (it != clients.end())
	{
		delete *it;
		clients.erase(it);
	}
}

int eDVBCAHandler::getNumberOfCAServices()
{
	return services.size();
}

int eDVBCAHandler::registerService(const eServiceReferenceDVB &ref, int adapter, int demux_nums[2], int servicetype, eDVBCAService *&caservice)
{
	CAServiceMap::iterator it = services.find(ref);
	bool had_streamserver = false;
	if (it != services.end())
	{
		caservice = it->second;
		// Check if streamserver was already active before adding new type
		// servicetype 7 = streamserver, 8 = scrambled_streamserver
		uint32_t mask = caservice->getServiceTypeMask();
		had_streamserver = (mask & ((1 << 7) | (1 << 8))) != 0;
	}
	else
	{
		// Check if we have a cached serviceId for this DVB service
		uint32_t id;
		std::map<eServiceReferenceDVB, uint32_t>::iterator cache_it = s_serviceId_cache.find(ref);
		if (cache_it != s_serviceId_cache.end())
		{
			id = cache_it->second;
			eDebug("[eDVBCAService] reusing cached serviceId %u for %s", id, ref.toString().c_str());
		}
		else
		{
			id = serviceIdCounter++;
			s_serviceId_cache[ref] = id;
		}
		caservice = (services[ref] = new eDVBCAService(ref, id));
		caservice->setAdapter(adapter);
		eDebug("[eDVBCAService] new service %s, serviceId %u", ref.toString().c_str(), id);
	}
	caservice->addServiceType(servicetype);

	int loops = demux_nums[0] != demux_nums[1] ? 2 : 1;
	for (int i = 0; i < loops; ++i)
	{
		/* search free demux entry */
		int iter = 0, max_demux_slots = caservice->getNumberOfDemuxes();

		while (iter < max_demux_slots && caservice->getUsedDemux(iter) != 0xFF)
		{
			++iter;
		}

		if (iter < max_demux_slots)
		{
			caservice->setUsedDemux(iter, demux_nums[i] & 0xFF);
			eDebug("[eDVBCAService] add demux %d to slot %d service %s", demux_nums[i] & 0xFF, iter, ref.toString().c_str());
		}
		else
		{
			eDebug("[eDVBCAService] no more demux slots free for service %s!!", ref.toString().c_str());
			return -1;
		}
	}

	serviceLeft->stop();

	/*
	 * our servicelist has changed, but we have to wait till we receive PMT data
	 * for this service, before we distribute a new list of CAPMT objects to our clients.
	 *
	 * Unless we have a pmt section in our cache, for this service.
	 */

	std::map<eServiceReferenceDVB, ePtr<eTable<ProgramMapSection> > >::const_iterator cacheit = pmtCache.find(ref);
	if (cacheit != pmtCache.end() && cacheit->second)
	{
		// If streamserver was active and we're adding a different type (e.g. Live-TV),
		// send CA PMT update immediately so OSCam knows about the new demux config
		if (had_streamserver && servicetype != 7 && servicetype != 8)
		{
			caservice->resetBuildHash();
			if (caservice->buildCAPMT(cacheit->second) >= 0)
			{
				for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
				{
					if (client_it->state() == eSocket::Connection)
					{
						caservice->writeCAPMTObject(*client_it, LIST_UPDATE);
					}
				}
				eDebug("[eDVBCAService] sent early CA PMT update (streamserver active, new type %d registering)", servicetype);
			}
		}
		else
		{
			processPMTForService(caservice, cacheit->second);
		}
	}
	return 0;
}

int eDVBCAHandler::unregisterService(const eServiceReferenceDVB &ref, int adapter, int demux_nums[2], int servicetype, eTable<ProgramMapSection> *ptr)
{
	CAServiceMap::iterator it = services.find(ref);
	if (it == services.end())
	{
		eDebug("[eDVBCAService] try to unregister non registered %s", ref.toString().c_str());
		return -1;
	}
	else
	{
		eDVBCAService *caservice = it->second;
		caservice->removeServiceType(servicetype);

		int loops = demux_nums[0] != demux_nums[1] ? 2 : 1;
		for (int i = 0; i < loops; ++i)
		{
			bool freed = false;
			int iter = 0, used_demux_slots = 0, max_demux_slots = caservice->getNumberOfDemuxes();
			while (iter < max_demux_slots)
			{
				if (caservice->getUsedDemux(iter) != 0xFF)
				{
					if (!freed && caservice->getUsedDemux(iter) == demux_nums[i])
					{
						eDebug("[eDVBCAService] free slot %d demux %d for service %s", iter, demux_nums[i], caservice->toString().c_str());
						caservice->setUsedDemux(iter, 0xFF);
						freed = true;
					}
					else
					{
						++used_demux_slots;
					}
				}
				if (freed && used_demux_slots) break; /* we have all the information we need */
				++iter;
			}
			if (!freed)
			{
				eDebug("[eDVBCAService] couldn't free demux slot for demux %d", demux_nums[i]);
			}
			if (i || loops == 1)
			{
				if (!used_demux_slots)  // no more used.. so we remove it
				{
					delete it->second;
					services.erase(it);

					/*
					 * this service is completely removed, so we distribute
					 * a new list of CAPMT objects to all our clients
					 */
					distributeCAPMT();
				}
				else
				{
					// Only send CA PMT update when streamserver stops but other types remain
					// (e.g. StreamRelay stopped while Live-TV still active)
					// servicetype 7 = streamserver, 8 = scrambled_streamserver
					if (ptr && (servicetype == 7 || servicetype == 8))
					{
						caservice->resetBuildHash();
						if (caservice->buildCAPMT(ptr) >= 0)
						{
							// Send to all connected clients (PMT mode 6, Protocol 3)
							for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
							{
								if (client_it->state() == eSocket::Connection)
								{
									caservice->writeCAPMTObject(*client_it, LIST_UPDATE);
								}
							}
							eDebug("[eDVBCAService] sent CA PMT update after streamserver unregister");
						}
					}
				}
			}
		}
	}

	serviceLeft->startLongTimer(2);

	return 0;
}

void eDVBCAHandler::serviceGone()
{
	if (!services.size())
	{
		eDebug("[DVBCAHandler] no more services");
		for (ePtrList<ePMTClient>::iterator it = clients.begin(); it != clients.end(); )
		{
			delete *it;
			it = clients.erase(it);
		}
		if (pmtCache.size() > 500)
		{
			pmtCache.clear();
		}
	}
}

void eDVBCAHandler::distributeCAPMT()
{
	/*
	 * write the list of CAPMT objects to each connected client, if it's not empty
	 */
	if (services.empty()) return;

	for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
	{
		if (client_it->state() == eSocket::Connection)
		{
			unsigned char list_management = LIST_FIRST;
			for (CAServiceMap::iterator it = services.begin(); it != services.end(); )
			{
				eDVBCAService *current = it->second;
				++it;
				if (it == services.end()) list_management |= LIST_LAST;
				current->writeCAPMTObject(*client_it, list_management);
				list_management = LIST_MORE;
			}
		}
	}
}

void eDVBCAHandler::processPMTForService(eDVBCAService *service, eTable<ProgramMapSection> *ptr)
{
	bool isUpdate = (service->getCAPMTVersion() >= 0);

	/* prepare the data */
	if (service->buildCAPMT(ptr) < 0) return; /* probably equal version, ignore */

	/* send the data to the listening client */
	service->sendCAPMT();

	if (isUpdate)
	{
		/*
		 * this is a PMT update for an existing service, so we should
		 * send the updated CAPMT object to all our connected clients
		 */
		for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
		{
			if (client_it->state() == eSocket::Connection)
			{
				service->writeCAPMTObject(*client_it, LIST_UPDATE);
			}
		}
	}
	else
	{
		/*
		 * this is PMT information for a new service, so we should
		 * send the new CAPMT object to all our connected clients
		 */
		int list_management = (getNumberOfCAServices() == 1) ? LIST_ONLY : LIST_ADD;

		for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
		{
			if (client_it->state() == eSocket::Connection)
			{
				service->writeCAPMTObject(*client_it, list_management);
			}
		}
	}
}

void eDVBCAHandler::handlePMT(const eServiceReferenceDVB &ref, ePtr<eTable<ProgramMapSection> > &ptr)
{
	CAServiceMap::iterator it = services.find(ref);
	if (it == services.end())
	{
		/* not one of our services */
		return;
	}

	processPMTForService(it->second, ptr);

	pmtCache[ref] = ptr;
}

void eDVBCAHandler::handlePMT(const eServiceReferenceDVB &ref, ePtr<eDVBService> &dvbservice)
{
	CAServiceMap::iterator it = services.find(ref);
	if (it == services.end())
	{
		/* not one of our services */
		return;
	}

	eDVBCAService *service = it->second;

	/* prepare the data */
	if (service->buildCAPMT(dvbservice) < 0) return; /* probably equal version, ignore */

	service->sendCAPMT();

	distributeCAPMT();
}

int eDVBCAHandler::getServiceReference(eServiceReferenceDVB &service, uint32_t serviceId)
{
	CAServiceMap::iterator it;
	for (it = services.begin(); it != services.end(); it++)
	{
		if (it->second->getId() == serviceId)
		{
			service = it->first;
			return 0;
		}
	}
	return -1;
}

eDVBCAService::eDVBCAService(const eServiceReferenceDVB &service, uint32_t id)
	: eUnixDomainSocket(eApp), m_service(service), m_adapter(0), m_service_type_mask(0), m_prev_build_hash(0), m_crc32(0), m_id(id), m_version(-1), m_retryTimer(eTimer::create(eApp))
{
	memset(m_used_demux, 0xFF, sizeof(m_used_demux));
	CONNECT(connectionClosed_, eDVBCAService::connectionLost);
	CONNECT(m_retryTimer->timeout, eDVBCAService::sendCAPMT);
}

eDVBCAService::~eDVBCAService()
{
	eDebug("[eDVBCAService] free service %s", m_service.toString().c_str());
}

std::string eDVBCAService::toString()
{
	return m_service.toString();
}

int eDVBCAService::getCAPMTVersion()
{
	return m_version;
}

int eDVBCAService::getNumberOfDemuxes()
{
	return sizeof(m_used_demux);
}

uint8_t eDVBCAService::getUsedDemux(int index)
{
	if (index < 0 || index >= (int)sizeof(m_used_demux)) return 0xff;
	return m_used_demux[index];
}

void eDVBCAService::setUsedDemux(int index, uint8_t value)
{
	if (index < 0 || index >= (int)sizeof(m_used_demux)) return;
	m_used_demux[index] = value;
}

uint8_t eDVBCAService::getAdapter()
{
	return m_adapter;
}

void eDVBCAService::setAdapter(uint8_t value)
{
	m_adapter = value;
}

void eDVBCAService::addServiceType(int type)
{
	m_service_type_mask |= (1 << type);
}

void eDVBCAService::removeServiceType(int type)
{
	m_service_type_mask ^= (1 << type);
}

uint32_t eDVBCAService::getServiceTypeMask() const
{
	return m_service_type_mask;
}

void eDVBCAService::connectionLost()
{
	/* reconnect in 1s */
	m_retryTimer->startLongTimer(1);
}

int eDVBCAService::buildCAPMT(eTable<ProgramMapSection> *ptr)
{
	if (!ptr)
		return -1;

	eDVBTableSpec table_spec;
	ptr->getSpec(table_spec);

	int pmtpid = table_spec.pid,
		pmt_version = table_spec.version;

	uint32_t demux_mask = 0;
	int data_demux = -1;
	uint32_t crc = 0;

	int iter = 0, max_demux_slots = getNumberOfDemuxes();
	while ( iter < max_demux_slots )
	{
		if (m_used_demux[iter] != 0xFF)
		{
			if (m_used_demux[iter] > data_demux)
			{
				data_demux = m_used_demux[iter];
			}
			demux_mask |= (1 << m_used_demux[iter]);
		}
		++iter;
	}

	if (data_demux == -1)
	{
		eDebug("[eDVBCAService] no data demux found for service %s", m_service.toString().c_str());
		return -1;
	}

	uint64_t build_hash = m_adapter;
	build_hash <<= 8;
	build_hash |= data_demux;
	build_hash <<= 16;
	build_hash |= pmtpid;
	build_hash <<= 8;
	build_hash |= (demux_mask & 0xff);
	build_hash <<= 8;
	build_hash |= (pmt_version & 0xff);
	//build_hash <<= 16;
	//build_hash |= (m_service_type_mask & 0xffff); // don't include in build_hash

	bool scrambled = false;
	for (std::vector<ProgramMapSection*>::const_iterator pmt = ptr->getSections().begin();
		pmt != ptr->getSections().end() && !scrambled; ++pmt)
	{
		for (DescriptorConstIterator desc = (*pmt)->getDescriptors()->begin();
			desc != (*pmt)->getDescriptors()->end() && !scrambled; ++desc)
		{
			if ((*desc)->getTag() == CA_DESCRIPTOR)
				scrambled = true;
		}

		for (ElementaryStreamInfoConstIterator es = (*pmt)->getEsInfo()->begin();
			es != (*pmt)->getEsInfo()->end() && !scrambled; ++es)
		{
			for (DescriptorConstIterator edesc = (*es)->getDescriptors()->begin();
				edesc != (*es)->getDescriptors()->end() && !scrambled; ++edesc)
			{
				if ((*edesc)->getTag() == CA_DESCRIPTOR)
					scrambled = true;
			}
		}
	}

	std::vector<ProgramMapSection*>::const_iterator i = ptr->getSections().begin();
	if ( i != ptr->getSections().end() )
	{
		crc = (*i)->getCrc32();
		if (build_hash == m_prev_build_hash && crc == m_crc32)
		{
			eDebug("[eDVBCAService] don't build/send the same CA PMT twice");
			return -1;
		}
		CaProgramMapSection capmt(*i++, m_prev_build_hash ? LIST_UPDATE : LIST_ONLY, CMD_OK_DESCRAMBLING);

		while( i != ptr->getSections().end() )
		{
//			eDebug("[eDVBCAService] append");
			capmt.append(*i++);
		}

		// add our private descriptors to capmt
		uint8_t tmp[10];

		tmp[0]=0x84;  // pmt pid
		tmp[1]=0x02;
		tmp[2]=pmtpid>>8;
		tmp[3]=pmtpid&0xFF;
		capmt.injectDescriptor(tmp, false);

		if (m_adapter > 0)
		{
			tmp[0] = 0x83; /* adapter */
			tmp[1] = 0x01;
			tmp[2] = m_adapter;
			capmt.injectDescriptor(tmp, true);
		}

		tmp[0] = 0x82; // demux
		tmp[1] = 0x02;
		tmp[2] = demux_mask&0xFF; // descramble bitmask
		tmp[3] = data_demux&0xFF; // read section data from demux number
		capmt.injectDescriptor(tmp, false);

		tmp[0] = 0x81; // dvbnamespace
		tmp[1] = 0x08;
		tmp[2] = m_service.getDVBNamespace().get()>>24;
		tmp[3]=(m_service.getDVBNamespace().get()>>16)&0xFF;
		tmp[4]=(m_service.getDVBNamespace().get()>>8)&0xFF;
		tmp[5]=m_service.getDVBNamespace().get()&0xFF;
		tmp[6]=m_service.getTransportStreamID().get()>>8;
		tmp[7]=m_service.getTransportStreamID().get()&0xFF;
		tmp[8]=m_service.getOriginalNetworkID().get()>>8;
		tmp[9]=m_service.getOriginalNetworkID().get()&0xFF;
		capmt.injectDescriptor(tmp, false);

		tmp[0] = 0x85;  /* service type mask */
		tmp[1] = 0x04;
		tmp[2] = (m_service_type_mask >> 24) & 0xff;
		tmp[3] = (m_service_type_mask >> 16) & 0xff;
		tmp[4] = (m_service_type_mask >> 8) & 0xff;
		tmp[5] = m_service_type_mask & 0xff;
		capmt.injectDescriptor(tmp, true);

		tmp[0] = 0x86; // demux only
		tmp[1] = 0x01;
		tmp[2] = data_demux&0xFF; // read section data from demux number
		capmt.injectDescriptor(tmp, true);

		ePtr<eDVBService> dvbservice;
		if (!scrambled && !eDVBDB::getInstance()->getService(m_service, dvbservice))
		{
			CAID_LIST &caids = dvbservice->m_ca;
			for (CAID_LIST::iterator it(caids.begin()); it != caids.end(); ++it)
			{
				int caid = *it;
				tmp[0] = 0x09;
				tmp[1] = 0x04;
				tmp[2] = caid>>8;
				tmp[3] = caid&0xFF;
				tmp[4] = 0x1F;
				tmp[5] = 0xFF;
				capmt.injectDescriptor(tmp, true);
			}
		}

		// protocol version >= 3 add extra header (will be skipped if version < 3)
		m_capmt[0] = 0xA5; // message start
		m_capmt[1] = m_id >> 24;
		m_capmt[2] = m_id >> 16;
		m_capmt[3] = m_id >>  8;
		m_capmt[4] = m_id & 0xFF; // msgid
		size_t total = capmt.writeToBuffer(m_capmt + 5);

		if(!eDVBDB::getInstance()->getService(m_service, dvbservice))
		{
			pmtpid = dvbservice->getCacheEntry(eDVBService::cPMTPID);
			if (pmtpid > 0)
			{
				m_capmt[total++] = 0x0d; // Datastream (DSM CC)
				m_capmt[total++] = pmtpid>>8;
				m_capmt[total++] = pmtpid&0xFF;
				m_capmt[total++] = 0x00;
				m_capmt[total++] = 0x00;
				m_capmt[8] = (int)m_capmt[8] + 5;
			}
		}
	}

	m_prev_build_hash = build_hash;
	m_version = pmt_version;
	m_crc32 = crc;
	return 0;
}

int eDVBCAService::buildCAPMT(ePtr<eDVBService> &dvbservice)
{
	int pmt_version = 0;
	uint32_t demux_mask = 0;
	int data_demux = -1;
	uint32_t crc = 0;

	int iter = 0, max_demux_slots = getNumberOfDemuxes();
	while ( iter < max_demux_slots )
	{
		if (m_used_demux[iter] != 0xFF)
		{
			if (m_used_demux[iter] > data_demux)
			{
				data_demux = m_used_demux[iter];
			}
			demux_mask |= (1 << m_used_demux[iter]);
		}
		++iter;
	}

	if (data_demux == -1)
	{
		eDebug("[eDVBCAService] no data demux found for service %s", m_service.toString().c_str());
		return -1;
	}

	int pmtpid = dvbservice->getCacheEntry(eDVBService::cPMTPID);
	if (pmtpid == -1)
	{
		pmtpid = 0;
	}

	uint64_t build_hash = m_adapter;
	build_hash <<= 8;
	build_hash |= data_demux;
	build_hash <<= 16;
	build_hash |= pmtpid;
	build_hash <<= 8;
	build_hash |= (demux_mask & 0xff);
	build_hash <<= 8;
	build_hash |= (pmt_version & 0xff);
	//build_hash <<= 16;
	//build_hash |= (m_service_type_mask & 0xffff); // don't include in build_hash

	int pos = 0;
	int programInfoLength = 0;

	// protocol version >= 3 add extra header (will be skipped if version < 3)
	m_capmt[pos++] = 0xA5; // message start
	m_capmt[pos++] = m_id >> 24;
	m_capmt[pos++] = m_id >> 16;
	m_capmt[pos++] = m_id >>  8;
	m_capmt[pos++] = m_id & 0xFF; // msgid

	m_capmt[pos++] = 0x9f; // (caPmtTag >> 16) & 0xff;
	m_capmt[pos++] = 0x80; // (caPmtTag >> 8) & 0xff;
	m_capmt[pos++] = 0x32; // (caPmtTag >> 0) & 0xff;
	m_capmt[pos++] = 0x00; // Lenght fill later
	m_capmt[pos++] = 0x03; // LIST_ONLY

	// add our private descriptors to capmt

	m_capmt[pos++] = m_service.getServiceID().get()>>8;
	m_capmt[pos++] = m_service.getServiceID().get()&0xFF;

	m_capmt[pos++] = 0x01; // (versionNumber << 1) | currentNextIndicator
	m_capmt[pos++] = 0x00; // ProgramInfo Length fill later
	m_capmt[pos++] = 0x00; // ProgramInfo Length fill later
	m_capmt[pos++] = 0x01; // CMD_OK_DESCRAMBLING

	programInfoLength += 1;

	m_capmt[pos++] = 0x81; // dvbnamespace
	m_capmt[pos++] = 0x08;
	m_capmt[pos++] = m_service.getDVBNamespace().get()>>24;
	m_capmt[pos++] = (m_service.getDVBNamespace().get()>>16)&0xFF;
	m_capmt[pos++] = (m_service.getDVBNamespace().get()>>8)&0xFF;
	m_capmt[pos++] = m_service.getDVBNamespace().get()&0xFF;
	m_capmt[pos++] = m_service.getTransportStreamID().get()>>8;
	m_capmt[pos++] = m_service.getTransportStreamID().get()&0xFF;
	m_capmt[pos++] = m_service.getOriginalNetworkID().get()>>8;
	m_capmt[pos++] = m_service.getOriginalNetworkID().get()&0xFF;

	programInfoLength += 10;

	m_capmt[pos++] = 0x82; // demux
	m_capmt[pos++] = 0x02;
	m_capmt[pos++] = demux_mask&0xFF; // descramble bitmask
	m_capmt[pos++] = data_demux&0xFF; // read section data from demux number

	programInfoLength += 4;

	m_capmt[pos++] = 0x84;  // pmt pid
	m_capmt[pos++] = 0x02;
	m_capmt[pos++] = pmtpid>>8;
	m_capmt[pos++] = pmtpid&0xFF;

	programInfoLength += 4;

	if (m_adapter > 0)
	{
		m_capmt[pos++] = 0x83; /* adapter */
		m_capmt[pos++] = 0x01;
		m_capmt[pos++] = m_adapter;

		programInfoLength += 3;
	}

	CAID_LIST &caids = dvbservice->m_ca;
	for (CAID_LIST::iterator it(caids.begin()); it != caids.end(); ++it)
	{
		int caid = *it;
		m_capmt[pos++] = 0x09;
		m_capmt[pos++] = 0x04;
		m_capmt[pos++] = caid>>8;
		m_capmt[pos++] = caid&0xFF;
		m_capmt[pos++] = 0x1F;
		m_capmt[pos++] = 0xFF;

		programInfoLength += 6;
	}

	m_capmt[pos++] = 0x85;  /* service type mask */
	m_capmt[pos++] = 0x04;
	m_capmt[pos++] = (m_service_type_mask >> 24) & 0xff;
	m_capmt[pos++] = (m_service_type_mask >> 16) & 0xff;
	m_capmt[pos++] = (m_service_type_mask >> 8) & 0xff;
	m_capmt[pos++] = m_service_type_mask & 0xff;

	programInfoLength += 6;

	m_capmt[pos++] = 0x86; // demux
	m_capmt[pos++] = 0x01;
	m_capmt[pos++] = data_demux&0xFF; // read section data from demux number

	programInfoLength += 3;

	std::map<int,int> pidtype;

	pidtype[eDVBService::cVPID]      = 0x02; // Videostream (MPEG-2)
	pidtype[eDVBService::cMPEGAPID]  = 0x03; // Audiostream (MPEG-1)
	pidtype[eDVBService::cTPID]      = 0x06; // Data-/Audiostream (Subtitles/VBI and AC-3)
	pidtype[eDVBService::cPCRPID]    = 0x06;
	pidtype[eDVBService::cAC3PID]    = 0x06;
	pidtype[eDVBService::cAC4PID]    = 0x06;
	pidtype[eDVBService::cSUBTITLE]  = 0x06;
	pidtype[eDVBService::cAACHEAPID] = 0x06;
	pidtype[eDVBService::cDDPPID]    = 0x06;
	pidtype[eDVBService::cAACAPID]   = 0x06;
	pidtype[eDVBService::cDATAPID]   = 0x90; // Datastream (Blu-ray subtitling)
	pidtype[eDVBService::cPMTPID]    = 0x0d; // Datastream (DSM CC)

	// cached pids
	for (int x = 0; x < eDVBService::cacheMax; ++x)
	{
		if (x == 5)
		{
			x += 3; // ignore cVTYPE, cACHANNEL, cAC3DELAY, cPCMDELAY
			continue;
		}
		int entry = dvbservice->getCacheEntry((eDVBService::cacheID)x);

		if (entry != -1)
		{
			if (eDVBService::cSUBTITLE == (eDVBService::cacheID)x)
			{
				entry = (entry&0xFFFF0000)>>16;
			}
			m_capmt[pos++] = pidtype[x];
			m_capmt[pos++] = entry>>8;
			m_capmt[pos++] = entry&0xFF;
			m_capmt[pos++] = 0x00;
			m_capmt[pos++] = 0x00;
		}
	}

	// calculate capmt length
	m_capmt[3] = pos - 9;

	// calculate programinfo leght
	m_capmt[8] = programInfoLength>>8;
	m_capmt[9] = programInfoLength&0xFF;

	m_prev_build_hash = build_hash;
	m_version = pmt_version;
	m_crc32 = crc;
	return 0;
}

void eDVBCAService::sendCAPMT()
{
	if (state() == Idle || state() == Invalid)
	{
		/* we're not connected yet */
		connectToPath(PMT_CLIENT_SOCKET);
	}

	if (state() == Connection)
	{
		writeCAPMTObject(this, LIST_ONLY);
	}
	else
	{
		/* we're not connected, try again in 5s */
		m_retryTimer->startLongTimer(5);
	}
}

int eDVBCAService::writeCAPMTObject(eSocket *socket, int list_management)
{
	int wp = 0;
	if (m_capmt[8] & 0x80)
	{
		int i=0;
		int lenbytes = m_capmt[8] & ~0x80;
		while(i < lenbytes)
			wp = (wp << 8) | m_capmt[9 + i++];
		wp += 4;
		wp += lenbytes;
		if (list_management >= 0) m_capmt[9 + lenbytes] = (unsigned char)list_management;
	}
	else
	{
		wp = m_capmt[8];
		wp += 4;
		if (list_management >= 0) m_capmt[9] = (unsigned char)list_management;
	}

	return socket->writeBlock((const char*)(m_capmt + 5), wp); // skip extra header
}

int eDVBCAService::writeCAPMTObject(ePMTClient *client, int list_management)
{
	int wp = 0;
	if (m_capmt[8] & 0x80)
	{
		int i=0;
		int lenbytes = m_capmt[8] & ~0x80;
		while(i < lenbytes)
			wp = (wp << 8) | m_capmt[9 + i++];
		wp += 4;
		wp += lenbytes;
		if (list_management >= 0) m_capmt[9 + lenbytes] = (unsigned char)list_management;
	}
	else
	{
		wp = m_capmt[8];
		wp += 4;
		if (list_management >= 0) m_capmt[9] = (unsigned char)list_management;
	}

	return client->writeCAPMTObject((const char*)m_capmt, wp);
}

eAutoInitPtr<eDVBCAHandler> init_eDVBCAHandler(eAutoInitNumbers::dvb, "CA handler");
