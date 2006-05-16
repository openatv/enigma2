#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/scan.h>
#include <dvbsi++/ca_descriptor.h>
#include <dvbsi++/ca_program_map_section.h>
#include <dvbsi++/teletext_descriptor.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/iso639_language_descriptor.h>
#include <dvbsi++/stream_identifier_descriptor.h>

eDVBServicePMTHandler::eDVBServicePMTHandler()
	:m_ca_servicePtr(0), m_dvb_scan(0), m_decode_demux_num(0xFF)
{
	m_use_decode_demux = 0;
	m_pmt_pid = -1;
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
}

eDVBServicePMTHandler::~eDVBServicePMTHandler()
{
	free();
}

void eDVBServicePMTHandler::channelStateChanged(iDVBChannel *channel)
{
	int state;
	channel->getState(state);
	
	if ((m_last_channel_state != iDVBChannel::state_ok)
		&& (state == iDVBChannel::state_ok) && (!m_demux))
	{
		if (m_channel)
			if (m_channel->getDemux(m_demux, (!m_use_decode_demux) ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating %s-decoding a demux for now tuned-in channel failed.", m_use_decode_demux ? "" : "non-");
		
		serviceEvent(eventTuned);
		
		if (m_demux)
		{
			eDebug("ok ... now we start!!");

			if (m_pmt_pid == -1)
				m_PAT.begin(eApp, eDVBPATSpec(), m_demux);
			else
				m_PMT.begin(eApp, eDVBPMTSpec(m_pmt_pid, m_reference.getServiceID().get()), m_demux);

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

void eDVBServicePMTHandler::channelEvent(iDVBChannel *channel, int event)
{
	switch (event)
	{
	case iDVBChannel::evtEOF:
		serviceEvent(eventEOF);
		break;
	case iDVBChannel::evtSOF:
		serviceEvent(eventSOF);
		break;
	default:
		break;
	}
}

void eDVBServicePMTHandler::PMTready(int error)
{
	if (error)
		serviceEvent(eventNoPMT);
	else
	{
		serviceEvent(eventNewProgramInfo);
		eEPGCache::getInstance()->PMTready(this);
		if (!m_pvr_channel)
		{
			if(!m_ca_servicePtr)   // don't send campmt to camd.socket for playbacked services
			{
				int demuxes[2] = {0,0};
				uint8_t tmp;
				m_demux->getCADemuxID(tmp);
				demuxes[0]=tmp;
				if (m_decode_demux_num != 0xFF)
					demuxes[1]=m_decode_demux_num;
				else
					demuxes[1]=demuxes[0];
				eDVBCAService::register_service(m_reference, demuxes, m_ca_servicePtr);
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

PyObject *eDVBServicePMTHandler::getCaIds()
{
	PyObject *ret=0;

	ePtr<eTable<ProgramMapSection> > ptr;

	if ( ((m_service && m_service->usePMT()) || !m_service) && !m_PMT.getCurrent(ptr))
	{
		uint16_t caids[255];
		memset(caids, 0, sizeof(caids));
		std::vector<ProgramMapSection*>::const_iterator i = ptr->getSections().begin();
		for (; i != ptr->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;
			ElementaryStreamInfoConstIterator es = pmt.getEsInfo()->begin();
			for (; es != pmt.getEsInfo()->end(); ++es)
			{
				for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
						case CA_DESCRIPTOR:
						{
							const CaDescriptor *cadescr = (const CaDescriptor*)*desc;
							uint16_t caid = cadescr->getCaSystemId();
							int idx=0;
							while (caids[idx] && caids[idx] != caid)
								++idx;
							caids[idx]=caid;
							break;
						}
					}
				}
			}
			for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
				desc != pmt.getDescriptors()->end(); ++desc)
			{
				switch ((*desc)->getTag())
				{
					case CA_DESCRIPTOR:
					{
						const CaDescriptor *cadescr = (const CaDescriptor*)*desc;
						uint16_t caid = cadescr->getCaSystemId();
						int idx=0;
						while (caids[idx] && caids[idx] != caid)
							++idx;
						caids[idx]=caid;
						break;
					}
				}
			}
		}
		int cnt=0;
		while (caids[cnt])
			++cnt;
		if (cnt)
		{
			ret=PyList_New(cnt);
			while(cnt--)
				PyList_SET_ITEM(ret, cnt, PyInt_FromLong(caids[cnt]));
		}
	}

	if (!ret)
		ret=PyList_New(0);

	return ret;
}

int eDVBServicePMTHandler::getProgramInfo(struct program &program)
{
	ePtr<eTable<ProgramMapSection> > ptr;

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.pcrPid = -1;
	program.isCrypted = false;
	program.pmtPid = -1;
	program.textPid = -1;
	program.audioChannel = m_service ? m_service->getCacheEntry(eDVBService::cACHANNEL) : -1;

	if ( ((m_service && m_service->usePMT()) || !m_service) && !m_PMT.getCurrent(ptr))
	{
		int cached_apid_ac3 = -1;
		int cached_apid_mpeg = -1;
		int cached_vpid = -1;
		int cached_tpid = -1;
		if ( m_service && !m_service->cacheEmpty() )
		{
			cached_vpid = m_service->getCacheEntry(eDVBService::cVPID);
			cached_apid_mpeg = m_service->getCacheEntry(eDVBService::cAC3PID);
			cached_apid_ac3 = m_service->getCacheEntry(eDVBService::cAPID);
			cached_tpid = m_service->getCacheEntry(eDVBService::cTPID);
		}
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
				int isaudio = 0, isvideo = 0, cadescriptors = 0;
				videoStream video;
				audioStream audio;
				audio.component_tag=-1;
				video.component_tag=-1;

				video.pid = (*es)->getPid();
				audio.pid = (*es)->getPid();
				video.type = videoStream::vtMPEG2;

				switch ((*es)->getType())
				{
				case 0x1b: // AVC Video Stream (MPEG4 H264)
					video.type = videoStream::vtMPEG4_H264;
				case 0x01: // MPEG 1 video
				case 0x02: // MPEG 2 video
					isvideo = 1;
					//break; fall through !!!
				case 0x03: // MPEG 1 audio
				case 0x04: // MPEG 2 audio:
					if (!isvideo)
					{
						isaudio = 1;
						audio.type = audioStream::atMPEG;
					}
					//break; fall through !!!
				case 0x06: // PES Private
						/* PES private can contain AC-3, DTS or lots of other stuff.
						   check descriptors to get the exact type. */
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
							desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case TELETEXT_DESCRIPTOR:
							if ( program.textPid == -1 || (*es)->getPid() == cached_tpid )
								program.textPid = (*es)->getPid();
							break;
						case DTS_DESCRIPTOR:
							if (!isvideo)
							{
								isaudio = 1;
								audio.type = audioStream::atDTS;
							}
							break;
						case AC3_DESCRIPTOR:
							if (!isvideo)
							{
								isaudio = 1;
								audio.type = audioStream::atAC3;
							}
							break;
						case ISO_639_LANGUAGE_DESCRIPTOR:
							if (!isvideo)
							{
								const Iso639LanguageList *languages = ((Iso639LanguageDescriptor*)*desc)->getIso639Languages();
									/* use last language code */
								for (Iso639LanguageConstIterator i(languages->begin()); i != languages->end(); ++i)
									audio.language_code = (*i)->getIso639LanguageCode();
							}
							break;
						case STREAM_IDENTIFIER_DESCRIPTOR:
							audio.component_tag =
								video.component_tag =
									((StreamIdentifierDescriptor*)*desc)->getComponentTag();
							break;
						case CA_DESCRIPTOR:
							++cadescriptors;
							break;
						}
					}
					break;
				}
				if (isaudio)
				{
					if ( !program.audioStreams.empty() &&
						( audio.pid == cached_apid_ac3 || audio.pid == cached_apid_mpeg) )
					{
						program.audioStreams.push_back(program.audioStreams[0]);
						program.audioStreams[0] = audio;
					}
					else
						program.audioStreams.push_back(audio);
				}
				else if (isvideo)
				{
					if ( !program.videoStreams.empty() && video.pid == cached_vpid )
					{
						program.videoStreams.push_back(program.videoStreams[0]);
						program.videoStreams[0] = video;
					}
					else
						program.videoStreams.push_back(video);
				}
				else
					continue;
				if ( cadescriptors > 0 )
					program.isCrypted=true;
			}
			if ( !program.isCrypted )
			{
				for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
					desc != pmt.getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
					case CA_DESCRIPTOR:
						program.isCrypted=true;
						break;
					}
				}
				break;
			}
		}
		return 0;
	} else if ( m_service && !m_service->cacheEmpty() )
	{
		int vpid = m_service->getCacheEntry(eDVBService::cVPID),
			apid_ac3 = m_service->getCacheEntry(eDVBService::cAC3PID),
			apid_mpeg = m_service->getCacheEntry(eDVBService::cAPID),
			pcrpid = m_service->getCacheEntry(eDVBService::cPCRPID),
			tpid = m_service->getCacheEntry(eDVBService::cTPID),
			vpidtype = m_service->getCacheEntry(eDVBService::cVTYPE),
			cnt=0;
		if ( vpidtype == -1 )
			vpidtype = videoStream::vtMPEG2;
		if ( vpid != -1 )
		{
			videoStream s;
			s.pid = vpid;
			s.type = vpidtype;
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
		if ( tpid != -1 )
		{
			++cnt;
			program.textPid = tpid;
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

int eDVBServicePMTHandler::getDataDemux(ePtr<iDVBDemux> &demux)
{
	demux = m_demux;
	if (demux)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::getDecodeDemux(ePtr<iDVBDemux> &demux)
{
	int ret=0;
		/* if we're using the decoding demux as data source
		   (for example in pvr playbacks), return that one. */
	if (m_use_decode_demux)
	{
		demux = m_demux;
		return ret;
	}
	
	ASSERT(m_channel); /* calling without a previous ::tune is certainly bad. */

	ret = m_channel->getDemux(demux, iDVBChannel::capDecode);
	if (!ret)
		demux->getCADemuxID(m_decode_demux_num);

	return ret;
}

int eDVBServicePMTHandler::getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel)
{
	pvr_channel = m_pvr_channel;
	if (pvr_channel)
		return 0;
	else
		return -1;
}

void eDVBServicePMTHandler::SDTScanEvent(int event)
{
	switch (event)
	{
		case eDVBScan::evtFinish:
		{
			ePtr<iDVBChannelList> db;
			if (m_resourceManager->getChannelList(db) != 0)
				eDebug("no channel list");
			else
			{
				m_dvb_scan->insertInto(db);
				eDebug("sdt update done!");
			}
			break;
		}

		default:
			break;
	}
}

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *cue)
{
	RESULT res;
	m_reference = ref;
	
	m_use_decode_demux = use_decode_demux;
	
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
		{
			eWarning("no .meta file found, trying to find PMT pid");
			eDVBTSTools tstools;
			if (tstools.openFile(ref.path.c_str()))
				eWarning("failed to open file");
			else
			{
				int service_id, pmt_pid;
				if (!tstools.findPMT(pmt_pid, service_id))
				{
					eDebug("PMT pid found on pid %04x, service id %d", pmt_pid, service_id);
					m_reference.setServiceID(service_id);
					m_pmt_pid = pmt_pid;
				}
			}
		} else
			m_reference = parser.m_ref;
		
		eDebug("alloc PVR");
			/* allocate PVR */
		res = m_resourceManager->allocatePVRChannel(m_pvr_channel);
		if (res)
			eDebug("allocatePVRChannel failed!\n");
		m_channel = m_pvr_channel;
	}

	ePtr<iDVBChannelList> db;
	if (!m_resourceManager->getChannelList(db))
		db->getService((eServiceReferenceDVB&)m_reference, m_service);

	if (m_channel)
	{
		m_channel->connectStateChange(
			slot(*this, &eDVBServicePMTHandler::channelStateChanged), 
			m_channelStateChanged_connection);
		m_last_channel_state = -1;
		channelStateChanged(m_channel);

		m_channel->connectEvent(
			slot(*this, &eDVBServicePMTHandler::channelEvent), 
			m_channelEvent_connection);

		if (ref.path.empty())
		{
			delete m_dvb_scan;
			m_dvb_scan = new eDVBScan(m_channel);
			m_dvb_scan->connectEvent(slot(*this, &eDVBServicePMTHandler::SDTScanEvent), m_scan_event_connection);
		}
	} else
	{
		serviceEvent(eventTuneFailed);
		return res;
	}

	if (m_pvr_channel)
	{
		m_pvr_channel->setCueSheet(cue);
		m_pvr_channel->playFile(ref.path.c_str());
	}

	return res;
}

void eDVBServicePMTHandler::free()
{
	eDVBScan *tmp = m_dvb_scan;  // do a copy on stack (recursive call of free()) !!!
	m_dvb_scan = 0;
	delete m_dvb_scan;

	if (m_ca_servicePtr)
	{
		int demuxes[2] = {0,0};
		uint8_t tmp;
		m_demux->getCADemuxID(tmp);
		demuxes[0]=tmp;
		if (m_decode_demux_num != 0xFF)
			demuxes[1]=m_decode_demux_num;
		else
			demuxes[1]=demuxes[0];
		ePtr<eTable<ProgramMapSection> > ptr;
		m_PMT.getCurrent(ptr);
		eDVBCAService::unregister_service(m_reference, demuxes, ptr);
		eDVBCIInterfaces::getInstance()->removePMTHandler(this);
		m_ca_servicePtr = 0;
	}

	if (m_pvr_channel)
	{
		m_pvr_channel->stopFile();
		m_pvr_channel->setCueSheet(0);
	}
	m_PMT.stop();
	m_PAT.stop();
	m_service = 0;
	m_channel = 0;
	m_pvr_channel = 0;
	m_demux = 0;
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

RESULT eDVBCAService::register_service( const eServiceReferenceDVB &ref, int demux_nums[2], eDVBCAService *&caservice )
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

	int loops = demux_nums[0] != demux_nums[1] ? 2 : 1;
	for (int i=0; i < loops; ++i)
	{
// search free demux entry
		int iter=0, max_demux_slots = sizeof(caservice->m_used_demux);

		while ( iter < max_demux_slots && caservice->m_used_demux[iter] != 0xFF )
			++iter;

		if ( iter < max_demux_slots )
		{
			caservice->m_used_demux[iter] = demux_nums[i] & 0xFF;
			eDebug("[eDVBCAService] add demux %d to slot %d service %s", caservice->m_used_demux[iter], iter, ref.toString().c_str());
		}
		else
		{
			eDebug("[eDVBCAService] no more demux slots free for service %s!!", ref.toString().c_str());
			return -1;
		}
	}
	return 0;
}

RESULT eDVBCAService::unregister_service( const eServiceReferenceDVB &ref, int demux_nums[2], eTable<ProgramMapSection> *ptr )
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
		int loops = demux_nums[0] != demux_nums[1] ? 2 : 1;
		for (int i=0; i < loops; ++i)
		{
			bool freed = false;
			int iter = 0,
				used_demux_slots = 0,
				max_demux_slots = sizeof(caservice->m_used_demux)/sizeof(int);
			while ( iter < max_demux_slots )
			{
				if ( caservice->m_used_demux[iter] != 0xFF )
				{
					if ( !freed && caservice->m_used_demux[iter] == demux_nums[i] )
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
				eDebug("[eDVBCAService] couldn't free demux slot for demux %d", demux_nums[i]);
			if (i || loops == 1)
			{
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
	int data_demux = -1;

	int iter=0, max_demux_slots = sizeof(m_used_demux);
	while ( iter < max_demux_slots )
	{
		if ( m_used_demux[iter] != 0xFF )
		{
			if ( m_used_demux[iter] > data_demux )
				data_demux = m_used_demux[iter];
			demux_mask |= (1 << m_used_demux[iter]);
		}
		++iter;
	}

	if ( data_demux == -1 )
	{
		eDebug("[eDVBCAService] no data demux found for service %s", m_service.toString().c_str() );
		return;
	}

	eDebug("demux %d mask %02x prevhash %08x", data_demux, demux_mask, m_prev_build_hash);

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
