#include <lib/base/nconfig.h> // access to python config
#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/scan.h>
#include <lib/dvb_ci/dvbci_session.h>
#include <dvbsi++/ca_descriptor.h>
#include <dvbsi++/ca_program_map_section.h>
#include <dvbsi++/teletext_descriptor.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/iso639_language_descriptor.h>
#include <dvbsi++/stream_identifier_descriptor.h>
#include <dvbsi++/subtitling_descriptor.h>
#include <dvbsi++/teletext_descriptor.h>
#include <dvbsi++/video_stream_descriptor.h>
#include <dvbsi++/registration_descriptor.h>

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

			if (!m_service || m_service->usePMT())
			{
				if (m_pmt_pid == -1)
					m_PAT.begin(eApp, eDVBPATSpec(), m_demux);
				else
					m_PMT.begin(eApp, eDVBPMTSpec(m_pmt_pid, m_reference.getServiceID().get()), m_demux);
			}

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
		m_have_cached_program = false;
		serviceEvent(eventNewProgramInfo);
		if (!m_pvr_channel) // don't send campmt to camd.socket for playbacked services
		{
			eEPGCache::getInstance()->PMTready(this);
			if(!m_ca_servicePtr)
			{
				int demuxes[2] = {0,0};
				uint8_t demuxid;
				uint8_t adapterid;
				m_demux->getCADemuxID(demuxid);
				m_demux->getCAAdapterID(adapterid);
				demuxes[0]=demuxid;
				if (m_decode_demux_num != 0xFF)
					demuxes[1]=m_decode_demux_num;
				else
					demuxes[1]=demuxes[0];
				eDVBCAHandler::getInstance()->registerService(m_reference, adapterid, demuxes, m_ca_servicePtr);
				eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
			}
			eDVBCIInterfaces::getInstance()->gotPMT(this);
		}
		if (m_ca_servicePtr)
		{
			ePtr<eTable<ProgramMapSection> > ptr;
			if (!m_PMT.getCurrent(ptr))
				eDVBCAHandler::getInstance()->handlePMT(m_reference, ptr);
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
	ePyObject ret;

	program prog;

	if ( !getProgramInfo(prog) )
	{
		int cnt=prog.caids.size();
		if (cnt)
		{
			ret=PyList_New(cnt);
			std::set<uint16_t>::iterator it(prog.caids.begin());
			while(cnt--)
				PyList_SET_ITEM(ret, cnt, PyInt_FromLong(*it++));
		}
	}

	return ret ? (PyObject*)ret : (PyObject*)PyList_New(0);
}

int eDVBServicePMTHandler::getProgramInfo(struct program &program)
{
	ePtr<eTable<ProgramMapSection> > ptr;
	int cached_apid_ac3 = -1;
	int cached_apid_mpeg = -1;
	int cached_vpid = -1;
	int cached_tpid = -1;
	int ret = -1;

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.pcrPid = -1;
	program.pmtPid = -1;
	program.textPid = -1;

	int first_ac3 = -1;
	program.defaultAudioStream = 0;
	int rdsPid = -1;
	audioStream *prev_audio = 0;

	if ( m_service && !m_service->cacheEmpty() )
	{
		cached_vpid = m_service->getCacheEntry(eDVBService::cVPID);
		cached_apid_mpeg = m_service->getCacheEntry(eDVBService::cAPID);
		cached_apid_ac3 = m_service->getCacheEntry(eDVBService::cAC3PID);
		cached_tpid = m_service->getCacheEntry(eDVBService::cTPID);
	}

	if ( ((m_service && m_service->usePMT()) || !m_service) && !m_PMT.getCurrent(ptr))
	{
		if (m_have_cached_program)
		{
			program = m_cached_program;
			ret = 0;
		}
		else
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
					int isaudio = 0, isvideo = 0, issubtitle = 0, forced_video = 0, forced_audio = 0, isteletext = 0;
					int streamtype = (*es)->getType();
					videoStream video;
					audioStream audio;
					audio.component_tag=video.component_tag=-1;
					video.type = videoStream::vtMPEG2;
					audio.type = audioStream::atMPEG;
					audio.rdsPid = -1;

					switch (streamtype)
					{
					case 0x1b: // AVC Video Stream (MPEG4 H264)
						video.type = videoStream::vtMPEG4_H264;
						isvideo = 1;
						//break; fall through !!!
					case 0x10: // MPEG 4 Part 2
						if (!isvideo)
						{
							video.type = videoStream::vtMPEG4_Part2;
							isvideo = 1;
						}
						//break; fall through !!!
					case 0x01: // MPEG 1 video
						if (!isvideo)
							video.type = videoStream::vtMPEG1;
						//break; fall through !!!
					case 0x02: // MPEG 2 video
						isvideo = 1;
						forced_video = 1;
						//break; fall through !!!
					case 0x03: // MPEG 1 audio
					case 0x04: // MPEG 2 audio:
						if (!isvideo) {
							isaudio = 1;
							forced_audio = 1;
						}
						//break; fall through !!!
					case 0x0f: // MPEG 2 AAC
						if (!isvideo && !isaudio)
						{
							isaudio = 1;
							audio.type = audioStream::atAAC;
							forced_audio = 1;
						}
						//break; fall through !!!
					case 0x11: // MPEG 4 AAC
						if (!isvideo && !isaudio)
						{
							isaudio = 1;
							audio.type = audioStream::atAACHE;
							forced_audio = 1;
						}
					case 0x80: // user private ... but blueray LPCM
						if (!isvideo && !isaudio)
						{
							isaudio = 1;
							audio.type = audioStream::atLPCM;
						}
					case 0x81: // user private ... but blueray AC3
						if (!isvideo && !isaudio)
						{
							isaudio = 1;
							audio.type = audioStream::atAC3;
						}
					case 0x82: // Blueray DTS (dvb user private...)
					case 0xA2: // Blueray secondary DTS
						if (!isvideo && !isaudio)
						{
							isaudio = 1;
							audio.type = audioStream::atDTS;
						}
					case 0x06: // PES Private
					case 0xEA: // TS_PSI_ST_SMPTE_VC1
					{
						int num_descriptors = 0;
						for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
							desc != (*es)->getDescriptors()->end(); ++desc)
						{
							uint8_t tag = (*desc)->getTag();
							/* check descriptors to get the exakt stream type. */
							++num_descriptors;
							if (!forced_video && !forced_audio)
							{
								switch (tag)
								{
								case AUDIO_STREAM_DESCRIPTOR:
									isaudio = 1;
									break;
								case VIDEO_STREAM_DESCRIPTOR:
								{
									isvideo = 1;
									VideoStreamDescriptor *d = (VideoStreamDescriptor*)(*desc);
									if (d->getMpeg1OnlyFlag())
										video.type = videoStream::vtMPEG1;
									break;
								}
								case SUBTITLING_DESCRIPTOR:
								{
									SubtitlingDescriptor *d = (SubtitlingDescriptor*)(*desc);
									const SubtitlingList *list = d->getSubtitlings();
									subtitleStream s;
									s.pid = (*es)->getPid();
									for (SubtitlingConstIterator it(list->begin()); it != list->end(); ++it)
									{
										s.subtitling_type = (*it)->getSubtitlingType();
										switch(s.subtitling_type)
										{
										case 0x10 ... 0x13:
										case 0x20 ... 0x23: // dvb subtitles
											break;
										default:
											eDebug("dvb subtitle %s PID %04x with wrong subtitling type (%02x)... force 0x10!!",
												s.language_code.c_str(), s.pid, s.subtitling_type);
											s.subtitling_type = 0x10;
											break;
										}
										s.composition_page_id = (*it)->getCompositionPageId();
										s.ancillary_page_id = (*it)->getAncillaryPageId();
										s.language_code = (*it)->getIso639LanguageCode();
//										eDebug("add dvb subtitle %s PID %04x, type %d, composition page %d, ancillary_page %d",
//											s.language_code.c_str(), s.pid, s.subtitling_type, s.composition_page_id, s.ancillary_page_id);
										issubtitle=1;
										program.subtitleStreams.push_back(s);
									}
									break;
								}
								case TELETEXT_DESCRIPTOR:
									if ( program.textPid == -1 || (*es)->getPid() == cached_tpid )
									{
										subtitleStream s;
										s.subtitling_type = 0x01; // EBU TELETEXT SUBTITLES
										s.pid = program.textPid = (*es)->getPid();
										TeletextDescriptor *d = (TeletextDescriptor*)(*desc);
										isteletext = 1;
										const VbiTeletextList *list = d->getVbiTeletexts();
										for (VbiTeletextConstIterator it(list->begin()); it != list->end(); ++it)
										{
											switch((*it)->getTeletextType())
											{
											case 0x02: // Teletext subtitle page
											case 0x05: // Teletext subtitle page for hearing impaired pepople
												s.language_code = (*it)->getIso639LanguageCode();
												s.teletext_page_number = (*it)->getTeletextPageNumber();
												s.teletext_magazine_number = (*it)->getTeletextMagazineNumber();
//												eDebug("add teletext subtitle %s PID %04x, page number %d, magazine number %d",
//													s.language_code.c_str(), s.pid, s.teletext_page_number, s.teletext_magazine_number);
												program.subtitleStreams.push_back(s);
												issubtitle=1;
											default:
												break;
											}
										}
									}
									break;
								case DTS_DESCRIPTOR:
									isaudio = 1;
									audio.type = audioStream::atDTS;
									break;
								case 0x2B: // TS_PSI_DT_MPEG2_AAC
									isaudio = 1;
									audio.type = audioStream::atAAC; // MPEG2-AAC
									break;
								case 0x1C: // TS_PSI_DT_MPEG4_Audio
								case AAC_DESCRIPTOR:
									isaudio = 1;
									audio.type = audioStream::atAACHE; // MPEG4-AAC
									break;
								case AC3_DESCRIPTOR:
									isaudio = 1;
									audio.type = audioStream::atAC3;
									break;
								case REGISTRATION_DESCRIPTOR: /* some services don't have a separate AC3 descriptor */
								{
									RegistrationDescriptor *d = (RegistrationDescriptor*)(*desc);
									switch (d->getFormatIdentifier())
									{
									case 0x44545331 ... 0x44545333: // DTS1/DTS2/DTS3
										isaudio = 1;
										audio.type = audioStream::atDTS;
										break;
									case 0x41432d33: // == 'AC-3'
										isaudio = 1;
										audio.type = audioStream::atAC3;
										break;
									case 0x42535344: // == 'BSSD' (LPCM)
										isaudio = 1;
										audio.type = audioStream::atLPCM;
										break;
									case 0x56432d31: // == 'VC-1'
									{
										const AdditionalIdentificationInfoVector *vec = d->getAdditionalIdentificationInfo();
										if (vec->size() > 1 && (*vec)[0] == 0x01) // subdescriptor tag
										{
											if ((*vec)[1] >= 0x90) // profile_level
												video.type = videoStream::vtVC1; // advanced profile
											else
												video.type = videoStream::vtVC1_SM; // simple main
											isvideo = 1;
										}
									}
									default:
										break;
									}
									break;
								}
								case 0x28: // TS_PSI_DT_AVC
									isvideo = 1;
									video.type = videoStream::vtMPEG4_H264;
									break;
								case 0x1B: // TS_PSI_DT_MPEG4_Video
									isvideo = 1;
									video.type = videoStream::vtMPEG4_Part2;
									break;
								default:
									break;
								}
							}
							switch (tag)
							{
							case ISO_639_LANGUAGE_DESCRIPTOR:
								if (!isvideo)
								{
									int cnt=0;
									const Iso639LanguageList *languages = ((Iso639LanguageDescriptor*)*desc)->getIso639Languages();
										/* use last language code */
									for (Iso639LanguageConstIterator i(languages->begin()); i != languages->end(); ++i, ++cnt)
									{
										if (cnt == 0)
											audio.language_code = (*i)->getIso639LanguageCode();
										else
											audio.language_code += "/" + (*i)->getIso639LanguageCode();
									}
								}
								break;
							case STREAM_IDENTIFIER_DESCRIPTOR:
								audio.component_tag =
									video.component_tag =
										((StreamIdentifierDescriptor*)*desc)->getComponentTag();
								break;
							case CA_DESCRIPTOR:
							{
								CaDescriptor *descr = (CaDescriptor*)(*desc);
								program.caids.insert(descr->getCaSystemId());
								break;
							}
							default:
								break;
							}
						}
						if (!num_descriptors && streamtype == 0x06 && prev_audio)
						{
							prev_audio->rdsPid = (*es)->getPid();
							eDebug("Rds PID %04x detected ? ! ?", prev_audio->rdsPid);
						}
						prev_audio = 0;
					}
					default:
						break;
					}
					if (isteletext && (isaudio || isvideo)) 
					{
						eDebug("ambiguous streamtype for PID %04x detected.. forced as teletext!", (*es)->getPid());					
						continue; // continue with next PID
					}
					else if (issubtitle && (isaudio || isvideo))
						eDebug("ambiguous streamtype for PID %04x detected.. forced as subtitle!", (*es)->getPid());
					else if (isaudio && isvideo)
						eDebug("ambiguous streamtype for PID %04x detected.. forced as video!", (*es)->getPid());
					if (issubtitle) // continue with next PID
						continue;
					else if (isvideo)
					{
						video.pid = (*es)->getPid();
						if ( !program.videoStreams.empty() && video.pid == cached_vpid )
						{
							program.videoStreams.push_back(program.videoStreams[0]);
							program.videoStreams[0] = video;
						}
						else
							program.videoStreams.push_back(video);
					}
					else if (isaudio)
					{
						audio.pid = (*es)->getPid();

							/* if we find the cached pids, this will be our default stream */
						if (audio.pid == cached_apid_ac3 || audio.pid == cached_apid_mpeg)
							program.defaultAudioStream = program.audioStreams.size();

							/* also, we need to know the first non-mpeg (i.e. "ac3"/dts/...) stream */
						if ((audio.type != audioStream::atMPEG) && ((first_ac3 == -1) || (audio.pid == cached_apid_ac3)))
							first_ac3 = program.audioStreams.size();

						program.audioStreams.push_back(audio);
						prev_audio = &program.audioStreams.back();
					}
					else
						continue;
				}
				for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
					desc != pmt.getDescriptors()->end(); ++desc)
				{
					if ((*desc)->getTag() == CA_DESCRIPTOR)
					{
						CaDescriptor *descr = (CaDescriptor*)(*desc);
						program.caids.insert(descr->getCaSystemId());
					}
				}
			}
			ret = 0;


			/* PG: use the defaultac3 setting only when the user didn't specifically select a non-AC3 track before */
			if (cached_apid_mpeg == -1)
			{
				/* finally some fixup: if our default audio stream is an MPEG audio stream, 
					and we have 'defaultac3' set, use the first available ac3 stream instead.
					(note: if an ac3 audio stream was selected before, this will be also stored
					in 'fisrt_ac3', so we don't need to worry. */
				bool defaultac3 = false;
				std::string default_ac3;

				if (!ePythonConfigQuery::getConfigValue("config.av.defaultac3", default_ac3))
					defaultac3 = default_ac3 == "True";

				if (defaultac3 && (first_ac3 != -1))
					program.defaultAudioStream = first_ac3;
			}

			m_cached_program = program;
			m_have_cached_program = true;
		}
	} else if ( m_service && !m_service->cacheEmpty() )
	{
		int cached_pcrpid = m_service->getCacheEntry(eDVBService::cPCRPID),
			vpidtype = m_service->getCacheEntry(eDVBService::cVTYPE),
			cnt=0;
		if ( vpidtype == -1 )
			vpidtype = videoStream::vtMPEG2;
		if ( cached_vpid != -1 )
		{
			videoStream s;
			s.pid = cached_vpid;
			s.type = vpidtype;
			program.videoStreams.push_back(s);
			++cnt;
		}
		if ( cached_apid_ac3 != -1 )
		{
			audioStream s;
			s.type = audioStream::atAC3;
			s.pid = cached_apid_ac3;
			s.rdsPid = -1;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( cached_apid_mpeg != -1 )
		{
			audioStream s;
			s.type = audioStream::atMPEG;
			s.pid = cached_apid_mpeg;
			s.rdsPid = -1;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( cached_pcrpid != -1 )
		{
			++cnt;
			program.pcrPid = cached_pcrpid;
		}
		if ( cached_tpid != -1 )
		{
			++cnt;
			program.textPid = cached_tpid;
		}
		CAID_LIST &caids = m_service->m_ca;
		for (CAID_LIST::iterator it(caids.begin()); it != caids.end(); ++it)
			program.caids.insert(*it);
		if ( cnt )
			ret = 0;
	}
	return ret;
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
				eDVBChannelID chid;
				m_reference.getChannelID(chid);
				if (chid == m_dvb_scan->getCurrentChannelID())
				{
					m_dvb_scan->insertInto(db, true);
					eDebug("sdt update done!");
				}
				else
					eDebug("ignore sdt update data.... incorrect transponder tuned!!!");
			}
			break;
		}

		default:
			break;
	}
}

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *cue, bool simulate, eDVBService *service)
{
	RESULT res=0;
	m_reference = ref;
	
	m_use_decode_demux = use_decode_demux;

		/* use given service as backup. This is used for timeshift where we want to clone the live stream using the cache, but in fact have a PVR channel */
	m_service = service;
	
		/* is this a normal (non PVR) channel? */
	if (ref.path.empty())
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = m_resourceManager->allocateChannel(chid, m_channel, simulate);
		if (!simulate)
			eDebug("allocate Channel: res %d", res);

		ePtr<iDVBChannelList> db;
		if (!m_resourceManager->getChannelList(db))
			db->getService((eServiceReferenceDVB&)m_reference, m_service);

		if (!res && !simulate)
			eDVBCIInterfaces::getInstance()->addPMTHandler(this);
	} else if (!simulate) // no simulation of playback services
	{
		eDVBMetaParser parser;

		int ret=parser.parseFile(ref.path);
		if (ret || !parser.m_ref.getServiceID().get() /* incorrect sid in meta file or recordings.epl*/ )
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

	if (!simulate)
	{
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
				std::string disable_background_scan;
				if (ePythonConfigQuery::getConfigValue("config.misc.disable_background_scan", disable_background_scan) < 0
					|| disable_background_scan != "True")
				{
					m_dvb_scan = 0;
					m_dvb_scan = new eDVBScan(m_channel, true, false);
					m_dvb_scan->connectEvent(slot(*this, &eDVBServicePMTHandler::SDTScanEvent), m_scan_event_connection);
				}
			}
		} else
		{
			if (res == eDVBResourceManager::errAllSourcesBusy)
				serviceEvent(eventNoResources);
			else /* errChidNotFound, errNoChannelList, errChannelNotInList, errNoSourceFound */
				serviceEvent(eventMisconfiguration);
			return res;
		}

		if (m_pvr_channel)
		{
			m_pvr_channel->setCueSheet(cue);
			m_pvr_channel->playFile(ref.path.c_str());
		}
	}

	return res;
}

void eDVBServicePMTHandler::free()
{
	m_dvb_scan = 0;

	if (m_ca_servicePtr)
	{
		int demuxes[2] = {0,0};
		uint8_t demuxid;
		uint8_t adapterid;
		m_demux->getCADemuxID(demuxid);
		m_demux->getCAAdapterID(adapterid);
		demuxes[0]=demuxid;
		if (m_decode_demux_num != 0xFF)
			demuxes[1]=m_decode_demux_num;
		else
			demuxes[1]=demuxes[0];
		ePtr<eTable<ProgramMapSection> > ptr;
		m_PMT.getCurrent(ptr);
		eDVBCAHandler::getInstance()->unregisterService(m_reference, adapterid, demuxes, ptr);
		m_ca_servicePtr = 0;
	}

	if (m_channel)
		eDVBCIInterfaces::getInstance()->removePMTHandler(this);

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

static PyObject *createTuple(int pid, const char *type)
{
	PyObject *r = PyTuple_New(2);
	PyTuple_SET_ITEM(r, 0, PyInt_FromLong(pid));
	PyTuple_SET_ITEM(r, 1, PyString_FromString(type));
	return r;
}

static inline void PyList_AppendSteal(PyObject *list, PyObject *item)
{
	PyList_Append(list, item);
	Py_DECREF(item);
}

extern void PutToDict(ePyObject &dict, const char*key, ePyObject item); // defined in dvb/frontend.cpp

PyObject *eDVBServicePMTHandler::program::createPythonObject()
{
	ePyObject r = PyDict_New();
	ePyObject l = PyList_New(0);

	PyList_AppendSteal(l, createTuple(0, "pat"));

	if (pmtPid != -1)
		PyList_AppendSteal(l, createTuple(pmtPid, "pmt"));

	for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
			i(videoStreams.begin()); 
			i != videoStreams.end(); ++i)
		PyList_AppendSteal(l, createTuple(i->pid, "video"));

	for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
			i(audioStreams.begin()); 
			i != audioStreams.end(); ++i)
		PyList_AppendSteal(l, createTuple(i->pid, "audio"));

	for (std::vector<eDVBServicePMTHandler::subtitleStream>::const_iterator
			i(subtitleStreams.begin());
			i != subtitleStreams.end(); ++i)
		PyList_AppendSteal(l, createTuple(i->pid, "subtitle"));

	PyList_AppendSteal(l, createTuple(pcrPid, "pcr"));

	if (textPid != -1)
		PyList_AppendSteal(l, createTuple(textPid, "text"));

	PutToDict(r, "pids", l);

	return r;
}
