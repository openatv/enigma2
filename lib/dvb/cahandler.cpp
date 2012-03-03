#include <unistd.h>
#include <string.h>
#include <stdint.h>

#include <dvbsi++/ca_descriptor.h>
#include <dvbsi++/ca_program_map_section.h>
#include <lib/dvb/cahandler.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

ePMTClient::ePMTClient(eDVBCAHandler *handler, int socket) : eUnixDomainSocket(socket, 1, eApp), parent(handler)
{
	receivedTag[0] = 0;
	receivedLength = 0;
	receivedValue = NULL;
	displayText = NULL;
	CONNECT(connectionClosed_, ePMTClient::connectionLost);
	CONNECT(readyRead_, ePMTClient::dataAvailable);
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
		if (!receivedTag[0])
		{
			if (bytesAvailable() < 4) return;
			/* read the tag (3 bytes) + the first byte of the length */
			if(readBlock((char*)receivedTag, 4) < 4) return;
			receivedLength = 0;
		}
		if (receivedTag[0] && !receivedLength)
		{
			if (receivedTag[3] & 0x80)
			{
				/* multibyte length field */
				unsigned char lengthdata[128];
				int lengthdatasize;
				int i;
				lengthdatasize = receivedTag[3] & 0x7f;
				if (bytesAvailable() < lengthdatasize) return;
				if (readBlock((char*)lengthdata, lengthdatasize) < lengthdatasize) return;
				for (i = 0; i < lengthdatasize; i++)
				{
					receivedLength = (receivedLength << 8) | lengthdata[i];
				}
			}
			else
			{
				/* singlebyte length field */
				receivedLength = receivedTag[3] & 0x7f;
			}
		}

		if (receivedLength)
		{
			if (bytesAvailable() < receivedLength) return;
			if (receivedValue) delete [] receivedValue;
			receivedValue = new unsigned char[receivedLength];
			if (readBlock((char*)receivedValue, receivedLength) < receivedLength) return;
		}

		if (receivedValue)
		{
			/* the client message is complete, handle it */
			clientTLVReceived(receivedTag, receivedLength, receivedValue);
			/* prepare for a new message */
			delete [] receivedValue;
			receivedValue = NULL;
			receivedTag[0] = 0;
		}
	}
}

void ePMTClient::parseTLVObjects(unsigned char *data, int size)
{
	/* parse all tlv objects in the buffer */
	while (1)
	{
		int length = 0;
		int lengthdatasize = 0;
		size -= 4;
		if (size <= 0) break;
		if (data[3] & 0x80)
		{
			/* multibyte length field */
			int i;
			lengthdatasize = data[3] & 0x7f;
			size -= lengthdatasize;
			if (size <= 0) break;
			for (i = 1; i < lengthdatasize; i++)
			{
				length = (length << 8) | data[i + 3];
			}
		}
		else
		{
			/* singlebyte length field */
			length = data[3] & 0x7f;
		}
		if (size < length) break;

		/* we have a complete TLV object, handle it */
		clientTLVReceived(data, length, &data[3 + lengthdatasize]);
	}
}

void ePMTClient::clientTLVReceived(unsigned char *tag, int length, unsigned char *value)
{
	if (tag[0] != 0x9F) return; /* unknown command class */

	switch (tag[1])
	{
	case 0x80: /* application / CA / resource */
		switch (tag[2])
		{
		case 0x31: /* ca_info */
			
			break;
		case 0x33: /* ca_pmt_reply */
			/* currently not used */
			break;
		}
		break;
	case 0x84: /* host control / datetime */
		/* currently not used */
		break;
	case 0x88: /* MMI */
		switch (tag[2])
		{
		case 0x10: /* display message */
			/* display message contains several TLV objects (we're interested in the text objects) */
			if (displayText) delete [] displayText;
			displayText = new char[length];
			parseTLVObjects(value, length);
			/* TODO: display the message */
			if (displayText)
			{
				delete [] displayText;
				displayText = NULL;
			}
			break;
		case 0x04: /* text more */
			if (displayText)
			{
				strncat(displayText, (const char*)value, length);
				strncat(displayText, "\n", 1);
			}
			break;
		case 0x05: /* text last */
			if (displayText)
			{
				strncat(displayText, (const char*)value, length);
			}
			break;
		default:
			break;
		}
		break;
	case 0x8C: /* comms */
		/* currently not used */
		break;
	case 0x70: /* custom */
		switch (tag[2])
		{
		case 0x10: /* clientname */
			parent->clientname((const char*)value);
			break;
		case 0x20: /* client info */
			parent->clientinfo((const char*)value);
			break;
		case 0x21: /* used caid */
			if (length == sizeof(int32_t))
			{
				parent->usedcaid(ntohl(*(int32_t*)value));
			}
			break;
		case 0x22: /* verboseinfo */
			parent->verboseinfo((const char*)value);
			break;
		case 0x23: /* decode time (ms) */
			if (length == sizeof(int32_t))
			{
				parent->decodetime(ntohl(*(int32_t*)value));
			}
			break;
		case 0x24: /* used cardid */
			parent->usedcardid((const char*)value);
			break;
		default: /* unknown */
			break;
		}
		break;
	default: /* unknown command group */
		break;
	}
}

eDVBCAHandler *eDVBCAHandler::instance = NULL;

DEFINE_REF(eDVBCAHandler);

eDVBCAHandler::eDVBCAHandler()
 : eServerSocket(PMT_SERVER_SOCKET, eApp), serviceLeft(eTimer::create(eApp))
{
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

int eDVBCAHandler::registerService(const eServiceReferenceDVB &ref, int adapter, int demux_nums[2], int servicetype, eDVBCAService *&caservice)
{
	CAServiceMap::iterator it = services.find(ref);
	if (it != services.end())
	{
		caservice = it->second;
	}
	else
	{
		caservice = (services[ref] = new eDVBCAService(ref));
		caservice->setAdapter(adapter);
		eDebug("[eDVBCAService] new service %s", ref.toString().c_str() );
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
	 */
	return 0;
}

int eDVBCAHandler::unregisterService(const eServiceReferenceDVB &ref, int adapter, int demux_nums[2], eTable<ProgramMapSection> *ptr)
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
						eDebug("[eDVBCAService] free slot %d demux %d for service %s", iter, demux_nums[i], caservice->toString());
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
				}
				else
				{
					if (ptr)
					{
						if (it->second->buildCAPMT(ptr) >= 0)
						{
							it->second->sendCAPMT();
						}
					}
					else
					{
						eDebug("[eDVBCAService] can not send updated demux info");
					}
				}
			}
		}
	}

	serviceLeft->startLongTimer(2);

	usedcaid(0);
	/* our servicelist has changed, distribute the list of CAPMT objects to all our clients */
	distributeCAPMT();
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

void eDVBCAHandler::handlePMT(const eServiceReferenceDVB &ref, eTable<ProgramMapSection> *ptr)
{
	bool isUpdate;
	CAServiceMap::iterator it = services.find(ref);
	if (it == services.end())
	{
		/* not one of our services */
		return;
	}

	isUpdate = (it->second->getCAPMTVersion() >= 0);

	/* prepare the data */
	if (it->second->buildCAPMT(ptr) < 0) return; /* probably equal version, ignore */

	/* send the data to the listening client */
	it->second->sendCAPMT();

	if (isUpdate)
	{
		/* this is a PMT update, we should distribute the new CAPMT object to all our connected clients */
		for (ePtrList<ePMTClient>::iterator client_it = clients.begin(); client_it != clients.end(); ++client_it)
		{
			if (client_it->state() == eSocket::Connection)
			{
				it->second->writeCAPMTObject(*client_it, LIST_UPDATE);
			}
		}
	}
	else
	{
		/*
		 * this is PMT information for a new service, so we can now distribute
		 * the CAPMT objects to all our connected clients
		 */
		distributeCAPMT();
	}
}

eDVBCAService::eDVBCAService(const eServiceReferenceDVB &service)
	: eUnixDomainSocket(eApp), m_service(service), m_adapter(0), m_service_type_mask(0), m_prev_build_hash(0), m_version(-1), m_retryTimer(eTimer::create(eApp))
{
	memset(m_used_demux, 0xFF, sizeof(m_used_demux));
	CONNECT(connectionClosed_, eDVBCAService::connectionLost);
	CONNECT(m_retryTimer->timeout, eDVBCAService::sendCAPMT);
}

eDVBCAService::~eDVBCAService()
{
	eDebug("[eDVBCAService] free service %s", m_service.toString().c_str());
}

const char *eDVBCAService::toString()
{
	return m_service.toString().c_str();
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

	uint8_t demux_mask = 0;
	int data_demux = -1;

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

	eDebug("demux %d mask %02x prevhash %llx", data_demux, demux_mask, m_prev_build_hash);

	uint64_t build_hash = m_adapter;
	build_hash <<= 8;
	build_hash |= data_demux;
	build_hash <<= 16;
	build_hash |= pmtpid;
	build_hash <<= 8;
	build_hash |= demux_mask;
	build_hash <<= 8;
	build_hash |= (pmt_version & 0xff);
	build_hash <<= 16;
	build_hash |= (m_service_type_mask & 0xffff);

	if ( build_hash == m_prev_build_hash )
	{
		eDebug("[eDVBCAService] don't build/send the same CA PMT twice");
		return -1;
	}

	std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
	if ( i != ptr->getSections().end() )
	{
		CaProgramMapSection capmt(*i++, m_prev_build_hash ? LIST_UPDATE : LIST_ONLY, CMD_OK_DESCRAMBLING);

		while( i != ptr->getSections().end() )
		{
//			eDebug("append");
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
		tmp[2] = demux_mask;	// descramble bitmask
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

		capmt.writeToBuffer(m_capmt);
	}

	m_prev_build_hash = build_hash;
	m_version = pmt_version;
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
	if (m_capmt[3] & 0x80)
	{
		int i=0;
		int lenbytes = m_capmt[3] & ~0x80;
		while(i < lenbytes)
			wp = (wp << 8) | m_capmt[4 + i++];
		wp += 4;
		wp += lenbytes;
		if (list_management >= 0) m_capmt[4 + lenbytes] = (unsigned char)list_management;
	}
	else
	{
		wp = m_capmt[3];
		wp += 4;
		if (list_management >= 0) m_capmt[4] = (unsigned char)list_management;
	}

	return socket->writeBlock((const char*)m_capmt, wp);
}

eAutoInitPtr<eDVBCAHandler> init_eDVBCAHandler(eAutoInitNumbers::dvb, "CA handler");
