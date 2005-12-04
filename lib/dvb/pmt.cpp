#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb_ci/dvbci.h>
#include <dvbsi++/ca_program_map_section.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/iso639_language_descriptor.h>
#include <dvbsi++/component_descriptor.h>

eDVBServicePMTHandler::eDVBServicePMTHandler(int record)
	:m_ca_servicePtr(0)
{
	m_record = record;
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
	eDebug("new PMT handler record: %d", m_record);
}

eDVBServicePMTHandler::~eDVBServicePMTHandler()
{
	eDebug("delete PMT handler record: %d", m_record);
	if (m_ca_servicePtr)
	{
		eDebug("unregister caservice");
		uint8_t demux_num;
		m_demux->getCADemuxID(demux_num);
		ePtr<eTable<ProgramMapSection> > ptr;
		m_PMT.getCurrent(ptr);
		eDVBCAService::unregister_service(m_reference, demux_num, ptr);
		eDVBCIInterfaces::getInstance()->removePMTHandler(this);
	}
}

void eDVBServicePMTHandler::channelStateChanged(iDVBChannel *channel)
{
	int state;
	channel->getState(state);
	
	if ((m_last_channel_state != iDVBChannel::state_ok)
		&& (state == iDVBChannel::state_ok) && (!m_demux))
	{
		if (m_channel)
			if (m_channel->getDemux(m_demux, m_record ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating a demux for now tuned-in channel failed.");
		
		serviceEvent(eventTuned);
		
		if (m_demux)
		{
			eDebug("ok ... now we start!!");

			m_PAT.begin(eApp, eDVBPATSpec(), m_demux);

			if ( m_service && !m_service->cacheEmpty() )
				serviceEvent(eventNewProgramInfo);
		}
	} else if ((m_last_channel_state != iDVBChannel::state_failed) && 
			(state == iDVBChannel::state_failed))
	{
		eDebug("tune failed.");
		serviceEvent(eventTuneFailed);
	}
}

void eDVBServicePMTHandler::PMTready(int error)
{
	if (error)
		serviceEvent(eventNoPMT);
	else
	{
		serviceEvent(eventNewProgramInfo);
		if (!m_pvr_channel)
		{
			if(!m_ca_servicePtr)   // don't send campmt to camd.socket for playbacked services
			{
				uint8_t demux_num;
				m_demux->getCADemuxID(demux_num);
				eDVBCAService::register_service(m_reference, demux_num, m_ca_servicePtr);
				eDVBCIInterfaces::getInstance()->addPMTHandler(this);
			}
			eDVBCIInterfaces::getInstance()->gotPMT(this);
		}
		if (m_ca_servicePtr)
		{
			ePtr<eTable<ProgramMapSection> > ptr;
			if (!m_PMT.getCurrent(ptr))
				m_ca_servicePtr->buildCAPMT(ptr);
			else
				eDebug("eDVBServicePMTHandler cannot call buildCAPMT");
		}
	}
}

void eDVBServicePMTHandler::PATready(int)
{
	eDebug("got PAT");
	ePtr<eTable<ProgramAssociationSection> > ptr;
	if (!m_PAT.getCurrent(ptr))
	{
		int pmtpid = -1;
		std::vector<ProgramAssociationSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramAssociationSection &pat = **i;
			ProgramAssociationConstIterator program;
			for (program = pat.getPrograms()->begin(); program != pat.getPrograms()->end(); ++program)
				if (eServiceID((*program)->getProgramNumber()) == m_reference.getServiceID())
					pmtpid = (*program)->getProgramMapPid();
		}
		if (pmtpid == -1)
			serviceEvent(eventNoPATEntry);
		else
			m_PMT.begin(eApp, eDVBPMTSpec(pmtpid, m_reference.getServiceID().get()), m_demux);
	} else
		serviceEvent(eventNoPAT);
}

int eDVBServicePMTHandler::getProgramInfo(struct program &program)
{
	ePtr<eTable<ProgramMapSection> > ptr;

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.pcrPid = -1;

	if (!m_PMT.getCurrent(ptr))
	{
		eDVBTableSpec table_spec;
		ptr->getSpec(table_spec);
		program.pmtPid = table_spec.pid < 0x1fff ? table_spec.pid : -1;
		std::vector<ProgramMapSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;
			program.pcrPid = pmt.getPcrPid();
			
			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int isaudio = 0, isvideo = 0;
				videoStream video;
				audioStream audio;
				
				video.pid = (*es)->getPid();
				audio.pid = (*es)->getPid();
				
				switch ((*es)->getType())
				{
				case 0x01: // MPEG 1 video
				case 0x02: // MPEG 2 video
					isvideo = 1;
					break;
				case 0x03: // MPEG 1 audio
				case 0x04: // MPEG 2 audio:
					isaudio = 1;
					audio.type = audioStream::atMPEG;
					break;
				case 0x06: // PES Private
						/* PES private can contain AC-3, DTS or lots of other stuff.
						   check descriptors to get the exact type. */
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
							desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case AC3_DESCRIPTOR:
							isaudio = 1;
							audio.type = audioStream::atAC3;
							break;
						}
					}
					break;
				}
				if (isaudio)
				{
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
							desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case ISO_639_LANGUAGE_DESCRIPTOR:
						{
							const Iso639LanguageList *languages = ((Iso639LanguageDescriptor*)*desc)->getIso639Languages();
							
								/* use last language code */
							for (Iso639LanguageConstIterator i(languages->begin()); i != languages->end(); ++i)
								audio.language_code = (*i)->getIso639LanguageCode();

							break;
						}
						case COMPONENT_DESCRIPTOR:
							audio.component_tag = ((ComponentDescriptor*)*desc)->getComponentTag();
							break;
						}
					}

					program.audioStreams.push_back(audio);
				}
				if (isvideo)
					program.videoStreams.push_back(video);
			}
		}
		return 0;
	}
	else if ( m_service && !m_service->cacheEmpty() )
	{
		int vpid = m_service->getCachePID(eDVBService::cVPID),
			apid_ac3 = m_service->getCachePID(eDVBService::cAPID),
			apid_mpeg = m_service->getCachePID(eDVBService::cAC3PID),
			pcrpid = m_service->getCachePID(eDVBService::cPCRPID),
			cnt=0;
		if ( vpid != -1 )
		{
			videoStream s;
			s.pid = vpid;
			program.videoStreams.push_back(s);
			++cnt;
		}
		if ( apid_ac3 != -1 )
		{
			audioStream s;
			s.type = audioStream::atAC3;
			s.pid = apid_ac3;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( apid_mpeg != -1 )
		{
			audioStream s;
			s.type = audioStream::atMPEG;
			s.pid = apid_mpeg;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( pcrpid != -1 )
		{
			++cnt;
			program.pcrPid = pcrpid;
		}
		if ( cnt )
			return 0;
	}
	return -1;
}

int eDVBServicePMTHandler::getChannel(eUsePtr<iDVBChannel> &channel)
{
	channel = m_channel;
	if (channel)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::getDemux(ePtr<iDVBDemux> &demux)
{
	demux = m_demux;
	if (demux)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel)
{
	pvr_channel = m_pvr_channel;
	if (pvr_channel)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref)
{
	RESULT res;
	m_reference = ref;
	
		/* is this a normal (non PVR) channel? */
	if (ref.path.empty())
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = m_resourceManager->allocateChannel(chid, m_channel);
		eDebug("allocate Channel: res %d", res);
	} else
	{
		eDVBMetaParser parser;
		
		if (parser.parseFile(ref.path))
			eWarning("no .meta file found, trying original service ref.");
		else
			m_reference = parser.m_ref;
		
		eDebug("alloc PVR");
			/* allocate PVR */
		res = m_resourceManager->allocatePVRChannel(m_pvr_channel);
		if (res)
			eDebug("allocatePVRChannel failed!\n");
		m_channel = m_pvr_channel;
	}
	
	if (m_channel)
	{
		m_channel->connectStateChange(
			slot(*this, &eDVBServicePMTHandler::channelStateChanged), 
			m_channelStateChanged_connection);
		m_last_channel_state = -1;
		channelStateChanged(m_channel);
	} else
	{
		serviceEvent(eventTuneFailed);
		return res;
	}

	if (m_pvr_channel)
		m_pvr_channel->playFile(ref.path.c_str());

	ePtr<iDVBChannelList> db;
	if (!m_resourceManager->getChannelList(db))
		db->getService((eServiceReferenceDVB&)m_reference, m_service);

	return res;
}

std::map<eServiceReferenceDVB, eDVBCAService*> eDVBCAService::exist;

eDVBCAService::eDVBCAService()
	:m_prev_build_hash(0), m_sendstate(0), m_retryTimer(eApp)
{
	memset(m_used_demux, 0xFF, sizeof(m_used_demux));
	CONNECT(m_retryTimer.timeout, eDVBCAService::sendCAPMT);
	Connect();
}

eDVBCAService::~eDVBCAService()
{
	eDebug("[eDVBCAService] free service %s", m_service.toString().c_str());
	::close(m_sock);
}

RESULT eDVBCAService::register_service( const eServiceReferenceDVB &ref, int demux_num, eDVBCAService *&caservice )
{
	CAServiceMap::iterator it = exist.find(ref);
	if ( it != exist.end() )
		caservice = it->second;
	else
	{
		caservice = (exist[ref]=new eDVBCAService());
		caservice->m_service = ref;
		eDebug("[eDVBCAService] new service %s", ref.toString().c_str() );
	}
// search free demux entry
	int iter=0, max_demux_slots = sizeof(caservice->m_used_demux);

	while ( iter < max_demux_slots && caservice->m_used_demux[iter] != 0xFF )
		++iter;

	if ( iter < max_demux_slots )
	{
		caservice->m_used_demux[iter] = demux_num & 0xFF;
		eDebug("[eDVBCAService] add demux %d to slot %d service %s", demux_num, iter, ref.toString().c_str());
	}
	else
	{
		eDebug("[eDVBCAService] no more demux slots free for service %s!!", ref.toString().c_str());
		return -1;
	}
	return 0;
}

RESULT eDVBCAService::unregister_service( const eServiceReferenceDVB &ref, int demux_num, eTable<ProgramMapSection> *ptr )
{
	CAServiceMap::iterator it = exist.find(ref);
	if ( it == exist.end() )
	{
		eDebug("[eDVBCAService] try to unregister non registered %s", ref.toString().c_str());
		return -1;
	}
	else
	{
		eDVBCAService *caservice = it->second;
		bool freed = false;
		int iter = 0,
			used_demux_slots = 0,
			max_demux_slots = sizeof(caservice->m_used_demux)/sizeof(int);
		while ( iter < max_demux_slots )
		{
			if ( caservice->m_used_demux[iter] != 0xFF )
			{
				if ( !freed && caservice->m_used_demux[iter] == demux_num )
				{
					eDebug("[eDVBCAService] free slot %d demux %d for service %s", iter, caservice->m_used_demux[iter], caservice->m_service.toString().c_str() );
					caservice->m_used_demux[iter] = 0xFF;
					freed=true;
				}
				else
					++used_demux_slots;
			}
			++iter;
		}
		if (!freed)
		{
			eDebug("[eDVBCAService] couldn't free demux slot for demux %d", demux_num);
			return -1;
		}
		if (!used_demux_slots)  // no more used.. so we remove it
		{
			delete it->second;
			exist.erase(it);
		}
		else
		{
			if (ptr)
				it->second->buildCAPMT(ptr);
			else
				eDebug("[eDVBCAService] can not send updated demux info");
		}
	}
	return 0;
}

void eDVBCAService::Connect()
{
	memset(&m_servaddr, 0, sizeof(struct sockaddr_un));
	m_servaddr.sun_family = AF_UNIX;
	strcpy(m_servaddr.sun_path, "/tmp/camd.socket");
	m_clilen = sizeof(m_servaddr.sun_family) + strlen(m_servaddr.sun_path);
	m_sock = socket(PF_UNIX, SOCK_STREAM, 0);
	connect(m_sock, (struct sockaddr *) &m_servaddr, m_clilen);
	fcntl(m_sock, F_SETFL, O_NONBLOCK);
	int val=1;
	setsockopt(m_sock, SOL_SOCKET, SO_REUSEADDR, &val, 4);
}

void eDVBCAService::buildCAPMT(eTable<ProgramMapSection> *ptr)
{
	if (!ptr)
		return;

	eDVBTableSpec table_spec;
	ptr->getSpec(table_spec);

	int pmtpid = table_spec.pid,
		pmt_version = table_spec.version;

	uint8_t demux_mask = 0;
	uint8_t first_demux_num = 0xFF;

#if 1
	int iter=0, max_demux_slots = sizeof(m_used_demux);
	while ( iter < max_demux_slots )
	{
		if ( m_used_demux[iter] != 0xFF )
		{
			if ( first_demux_num == 0xFF )
				first_demux_num = m_used_demux[iter];
			demux_mask |= (1 << m_used_demux[iter]);
		}
		++iter;
	}
#else
	demux_mask = 3;
	first_demux_num = 0;
#endif

	if ( first_demux_num == 0xFF )
	{
		eDebug("[eDVBCAService] no demux found for service %s", m_service.toString().c_str() );
		return;
	}

	eDebug("demux %d mask %02x prevhash %08x", first_demux_num, demux_mask, m_prev_build_hash);

	unsigned int build_hash = (pmtpid << 16);
	build_hash |= (demux_mask << 8);
	build_hash |= (pmt_version&0xFF);

	if ( build_hash == m_prev_build_hash )
	{
		eDebug("[eDVBCAService] don't build/send the same CA PMT twice");
		return;
	}

	std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
	if ( i != ptr->getSections().end() )
	{
		CaProgramMapSection capmt(*i++, m_prev_build_hash ? 0x05 /*update*/ : 0x03 /*only*/, 0x01 );

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

		tmp[0] = 0x82; // demux
		tmp[1] = 0x02;
		tmp[2] = demux_mask;	// descramble bitmask
		tmp[3] = first_demux_num; // read section data from demux number
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

		capmt.writeToBuffer(m_capmt);
	}

	m_prev_build_hash = build_hash;

	if ( m_sendstate != 0xFFFFFFFF )
		m_sendstate=0;
	sendCAPMT();
}

void eDVBCAService::sendCAPMT()
{
	if ( m_sendstate && m_sendstate != 0xFFFFFFFF ) // broken pipe retry
	{
		::close(m_sock);
		Connect();
	}

	int wp=0;
	if ( m_capmt[3] & 0x80 )
	{
		int i=0;
		int lenbytes = m_capmt[3] & ~0x80;
		while(i < lenbytes)
			wp = (wp << 8) | m_capmt[4 + i++];
		wp+=4;
		wp+=lenbytes;
	}
	else
	{
		wp = m_capmt[3];
		wp+=4;
	}

	if ( write(m_sock, m_capmt, wp) == wp )
	{
		m_sendstate=0xFFFFFFFF;
		eDebug("[eDVBCAService] send %d bytes",wp);
#if 1
		for(int i=0;i<wp;i++)
			eDebugNoNewLine("%02x ", m_capmt[i]);
		eDebug("");
#endif
	}
	else
	{
		switch(m_sendstate)
		{
			case 0xFFFFFFFF:
				++m_sendstate;
				m_retryTimer.start(0,true);
//				eDebug("[eDVBCAService] send failed .. immediate retry");
				break;
			default:
				m_retryTimer.start(5000,true);
//				eDebug("[eDVBCAService] send failed .. retry in 5 sec");
				break;
		}
		++m_sendstate;
	}
}
