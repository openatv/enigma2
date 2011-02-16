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
	:m_ca_servicePtr(0), m_dvb_scan(0), m_decode_demux_num(0xFF), m_no_pat_entry_delay(eTimer::create())
{
	m_use_decode_demux = 0;
	m_pmt_pid = -1;
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
	CONNECT(m_no_pat_entry_delay->timeout, eDVBServicePMTHandler::sendEventNoPatEntry);
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
		{
			if (m_pvr_demux_tmp)
			{
				m_demux = m_pvr_demux_tmp;
				m_pvr_demux_tmp = NULL;
			}
			else if (m_channel->getDemux(m_demux, (!m_use_decode_demux) ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating %s-decoding a demux for now tuned-in channel failed.", m_use_decode_demux ? "" : "non-");
		}
		
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
	case iDVBChannel::evtPreStart:
		serviceEvent(eventPreStart);
		break;
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
				uint8_t tmp;
				m_demux->getCADemuxID(tmp);
				demuxes[0]=tmp;
				if (m_decode_demux_num != 0xFF)
					demuxes[1]=m_decode_demux_num;
				else
					demuxes[1]=demuxes[0];
				eDVBCAService::register_service(m_reference, demuxes, m_ca_servicePtr);
				eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
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

void eDVBServicePMTHandler::sendEventNoPatEntry()
{
	serviceEvent(eventNoPATEntry);
}

void eDVBServicePMTHandler::PATready(int)
{
	eDebug("PATready");
	ePtr<eTable<ProgramAssociationSection> > ptr;
	if (!m_PAT.getCurrent(ptr))
	{
		int service_id_single = -1;
		int pmtpid_single = -1;
		int pmtpid = -1;
		int cnt=0;
		std::vector<ProgramAssociationSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); pmtpid == -1 && i != ptr->getSections().end(); ++i)
		{
			const ProgramAssociationSection &pat = **i;
			ProgramAssociationConstIterator program;
			for (program = pat.getPrograms()->begin(); pmtpid == -1 && program != pat.getPrograms()->end(); ++program)
			{
				++cnt;
				if (eServiceID((*program)->getProgramNumber()) == m_reference.getServiceID())
					pmtpid = (*program)->getProgramMapPid();
				if (++cnt == 1 && pmtpid_single == -1 && pmtpid == -1)
				{
					pmtpid_single = (*program)->getProgramMapPid();
					service_id_single = (*program)->getProgramNumber();
				}
				else
					pmtpid_single = service_id_single = -1;
			}
		}
		if (pmtpid_single != -1) // only one PAT entry .. and not valid pmtpid found
		{
			eDebug("use single pat entry!");
			m_reference.setServiceID(eServiceID(service_id_single));
			pmtpid = pmtpid_single;
		}
		if (pmtpid == -1) {
			eDebug("no PAT entry found.. start delay");
			m_no_pat_entry_delay->start(1000, true);
		}
		else {
			eDebug("use pmtpid %04x for service_id %04x", pmtpid, m_reference.getServiceID().get());
			m_no_pat_entry_delay->stop();
			m_PMT.begin(eApp, eDVBPMTSpec(pmtpid, m_reference.getServiceID().get()), m_demux);
		}
	} else
		serviceEvent(eventNoPAT);
}

PyObject *eDVBServicePMTHandler::getCaIds(bool pair)
{
	ePyObject ret;

	program prog;

	if ( !getProgramInfo(prog) )
	{
		if (pair)
		{
			int cnt=prog.caids.size();
			if (cnt)
			{
				ret=PyList_New(cnt);
				std::list<program::capid_pair>::iterator it(prog.caids.begin());
				while(cnt--)
				{
					ePyObject tuple = PyTuple_New(2);
					PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(it->caid));
					PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong((it++)->capid));
					PyList_SET_ITEM(ret, cnt, tuple);
				}
			}
		}
		else
		{
			std::set<program::capid_pair> set(prog.caids.begin(), prog.caids.end());
			std::set<program::capid_pair>::iterator it(set.begin());
			int cnt=set.size();
			ret=PyList_New(cnt);
			while(cnt--)
				PyList_SET_ITEM(ret, cnt, PyInt_FromLong((it++)->caid));
		}
	}

	return ret ? (PyObject*)ret : (PyObject*)PyList_New(0);
}

int eDVBServicePMTHandler::getProgramInfo(program &program)
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
				int is_hdmv = 0;

				program.pcrPid = pmt.getPcrPid();

				for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
					desc != pmt.getDescriptors()->end(); ++desc)
				{
					if ((*desc)->getTag() == CA_DESCRIPTOR)
					{
						CaDescriptor *descr = (CaDescriptor*)(*desc);
						program::capid_pair pair;
						pair.caid = descr->getCaSystemId();
						pair.capid = descr->getCaPid();
						program.caids.push_back(pair);
					}
					else if ((*desc)->getTag() == REGISTRATION_DESCRIPTOR)
					{
						RegistrationDescriptor *d = (RegistrationDescriptor*)(*desc);
						if (d->getFormatIdentifier() == 0x48444d56) // HDMV
							is_hdmv = 1;
					}
				}

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
					case 0x80: // user private ... but bluray LPCM
					case 0xA0: // bluray secondary LPCM
						if (!isvideo && !isaudio && is_hdmv)
						{
							isaudio = 1;
							audio.type = audioStream::atLPCM;
						}
					case 0x81: // user private ... but bluray AC3
					case 0xA1: // bluray secondary AC3
						if (!isvideo && !isaudio && is_hdmv)
						{
							isaudio = 1;
							audio.type = audioStream::atAC3;
						}
					case 0x82: // bluray DTS (dvb user private...)
					case 0xA2: // bluray secondary DTS
						if (!isvideo && !isaudio && is_hdmv)
						{
							isaudio = 1;
							audio.type = audioStream::atDTS;
						}
					case 0x86: // bluray DTS-HD (dvb user private...)
					case 0xA6: // bluray secondary DTS-HD
						if (!isvideo && !isaudio && is_hdmv)
						{
							isaudio = 1;
							audio.type = audioStream::atDTSHD;
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
								program::capid_pair pair;
								pair.caid = descr->getCaSystemId();
								pair.capid = descr->getCaPid();
								program.caids.push_back(pair);
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
			}
			ret = 0;

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
		for (CAID_LIST::iterator it(caids.begin()); it != caids.end(); ++it) {
			program::capid_pair pair;
			pair.caid = *it;
			pair.capid = -1; // not known yet
			program.caids.push_back(pair);
		}
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
	ePtr<iTsSource> s;
	return tuneExt(ref, use_decode_demux, s, NULL, cue, simulate, service);
}

int eDVBServicePMTHandler::tuneExt(eServiceReferenceDVB &ref, int use_decode_demux, ePtr<iTsSource> &source, const char *streaminfo_file, eCueSheet *cue, bool simulate, eDVBService *service)
{
	RESULT res=0;
	m_reference = ref;
	m_use_decode_demux = use_decode_demux;
	m_no_pat_entry_delay->stop();

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
		if (!ref.getServiceID().get() /* incorrect sid in meta file or recordings.epl*/ )
		{
			eDVBTSTools tstools;
			bool b = source || !tstools.openFile(ref.path.c_str(), 1);
			eWarning("no .meta file found, trying to find PMT pid");
			if (source)
				tstools.setSource(source, NULL);
			if (b)
			{
				int service_id, pmt_pid;
				if (!tstools.findPMT(pmt_pid, service_id))
				{
					eDebug("PMT pid found on pid %04x, service id %d", pmt_pid, service_id);
					m_reference.setServiceID(service_id);
					m_pmt_pid = pmt_pid;
				}
			}
			else
				eWarning("no valid source to find PMT pid!");
		}
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
				m_dvb_scan = 0;
				m_dvb_scan = new eDVBScan(m_channel, true, false);
				m_dvb_scan->connectEvent(slot(*this, &eDVBServicePMTHandler::SDTScanEvent), m_scan_event_connection);
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

			if (m_pvr_channel->getDemux(m_pvr_demux_tmp, (!m_use_decode_demux) ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating %s-decoding a demux for PVR channel failed.", m_use_decode_demux ? "" : "non-");
			else if (source)
				m_pvr_channel->playSource(source, streaminfo_file);
			else
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

CAServiceMap eDVBCAService::exist;
ChannelMap eDVBCAService::exist_channels;
ePtr<eConnection> eDVBCAService::m_chanAddedConn;

eDVBCAService::eDVBCAService()
	:m_buffer(512), m_prev_build_hash(0), m_sendstate(0), m_retryTimer(eTimer::create(eApp))
{
	memset(m_used_demux, 0xFF, sizeof(m_used_demux));
	CONNECT(m_retryTimer->timeout, eDVBCAService::sendCAPMT);
	Connect();
}

eDVBCAService::~eDVBCAService()
{
	eDebug("[eDVBCAService] free service %s", m_service.toString().c_str());
	::close(m_sock);
}

// begin static methods
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

void eDVBCAService::registerChannelCallback(eDVBResourceManager *res_mgr)
{
	res_mgr->connectChannelAdded(slot(&DVBChannelAdded), m_chanAddedConn);
}

void eDVBCAService::DVBChannelAdded(eDVBChannel *chan)
{
	if ( chan )
	{
		eDebug("[eDVBCAService] new channel %p!", chan);
		channel_data *data = new channel_data();
		data->m_channel = chan;
		data->m_prevChannelState = -1;
		data->m_dataDemux = -1;
		exist_channels[chan] = data;
		chan->connectStateChange(slot(&DVBChannelStateChanged), data->m_stateChangedConn);
	}
}

void eDVBCAService::DVBChannelStateChanged(iDVBChannel *chan)
{
	ChannelMap::iterator it =
		exist_channels.find(chan);
	if ( it != exist_channels.end() )
	{
		int state=0;
		chan->getState(state);
		if ( it->second->m_prevChannelState != state )
		{
			switch (state)
			{
				case iDVBChannel::state_ok:
				{
					eDebug("[eDVBCAService] channel %p running", chan);
					break;
				}
				case iDVBChannel::state_release:
				{
					eDebug("[eDVBCAService] remove channel %p", chan);
					unsigned char msg[8] = { 0x9f,0x80,0x3f,0x04,0x83,0x02,0x00,0x00 };
					msg[7] = it->second->m_dataDemux & 0xFF;
					int sock, clilen;
					struct sockaddr_un servaddr;
					memset(&servaddr, 0, sizeof(struct sockaddr_un));
					servaddr.sun_family = AF_UNIX;
					strcpy(servaddr.sun_path, "/tmp/camd.socket");
					clilen = sizeof(servaddr.sun_family) + strlen(servaddr.sun_path);
					sock = socket(PF_UNIX, SOCK_STREAM, 0);
					if (sock > -1)
					{
						connect(sock, (struct sockaddr *) &servaddr, clilen);
						fcntl(sock, F_SETFL, O_NONBLOCK);
						int val=1;
						setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &val, 4);
						if (write(sock, msg, 8) != 8)
							eDebug("[eDVBCAService] write leave transponder failed!!");
						close(sock);
					}
					exist_channels.erase(it);
					delete it->second;
					it->second=0;
					break;
				}
				default: // ignore all other events
					return;
			}
			if (it->second)
				it->second->m_prevChannelState = state;
		}
	}
}

channel_data *eDVBCAService::getChannelData(eDVBChannelID &chid)
{
	for (ChannelMap::iterator it(exist_channels.begin()); it != exist_channels.end(); ++it)
	{
		if (chid == it->second->m_channel->getChannelID())
			return it->second;
	}
	return 0;
}
// end static methods

#define CA_REPLY_DEBUG
#define MAX_LENGTH_BYTES 4
#define MIN_LENGTH_BYTES 1

void eDVBCAService::socketCB(int what)
{
	if (what & (eSocketNotifier::Read | eSocketNotifier::Priority))
	{
		char msgbuffer[4096];
		ssize_t length = read(m_sock, msgbuffer, sizeof(msgbuffer));
		if (length == -1)
		{
			if (errno != EAGAIN && errno != EINTR && errno != EBUSY)
			{
				eDebug("[eSocketMMIHandler] read (%m)");
				what |= eSocketNotifier::Error;
			}
		} else if (length == 0)
		{
			what |= eSocketNotifier::Hungup;
		} else
		{
			int len = length;
			unsigned char *data = (unsigned char*)msgbuffer;
			int clear = 1;
	// If a new message starts, then the previous message
	// should already have been processed. Otherwise the
	// previous message was incomplete and should therefore
	// be deleted.
			if ((len >= 1) && ((data[0] & 0xFF) != 0x9f))
				clear = 0;
			if ((len >= 2) && ((data[1] & 0x80) != 0x80))
				clear = 0;
			if ((len >= 3) && ((data[2] & 0x80) != 0x00))
				clear = 0;
			if (clear)
			{
				m_buffer.clear();
#ifdef CA_REPLY_DEBUG
				eDebug("clear buffer");
#endif
			}
#ifdef CA_REPLY_DEBUG
			eDebug("Put to buffer:");
			for (int i=0; i < len; ++i)
				eDebugNoNewLine("%02x ", data[i]);
			eDebug("\n--------");
#endif
			m_buffer.write( data, len );

			while ( m_buffer.size() >= (3 + MIN_LENGTH_BYTES) )
			{
				unsigned char tmp[3+MAX_LENGTH_BYTES];
				m_buffer.peek(tmp, 3+MIN_LENGTH_BYTES);
				if (((tmp[0] & 0xFF) != 0x9f) || ((tmp[1] & 0x80) != 0x80) || ((tmp[2] & 0x80) != 0x00))
				{
					m_buffer.skip(1);
#ifdef CA_REPLY_DEBUG
					eDebug("skip %02x", tmp[0]);
#endif
					continue;
				}
				if (tmp[3] & 0x80)
				{
					int peekLength = (tmp[3] & 0x7f) + 4;
					if (m_buffer.size() < peekLength)
						continue;
					m_buffer.peek(tmp, peekLength);
				}
				int size=0;
				int LengthBytes=eDVBCISession::parseLengthField(tmp+3, size);
				int messageLength = 3+LengthBytes+size;
				if ( m_buffer.size() >= messageLength )
				{
					unsigned char dest[messageLength];
					m_buffer.read(dest, messageLength);
#ifdef CA_REPLY_DEBUG
					eDebug("dump ca reply:");
					for (int i=0; i < messageLength; ++i)
						eDebugNoNewLine("%02x ", dest[i]);
					eDebug("\n--------");
#endif
//					/*emit*/ mmi_progress(0, dest, (const void*)(dest+3+LengthBytes), messageLength-3-LengthBytes);
				}
			}
		}
	}
	if (what & eSocketNotifier::Hungup) {
		/*eDebug("[eDVBCAService] connection closed")*/;
		m_sendstate=1;
		sendCAPMT();
	}
	if (what & eSocketNotifier::Error)
		eDebug("[eDVBCAService] connection error");
}

void eDVBCAService::Connect()
{
	m_sn=0;
	memset(&m_servaddr, 0, sizeof(struct sockaddr_un));
	m_servaddr.sun_family = AF_UNIX;
	strcpy(m_servaddr.sun_path, "/tmp/camd.socket");
	m_clilen = sizeof(m_servaddr.sun_family) + strlen(m_servaddr.sun_path);
	m_sock = socket(PF_UNIX, SOCK_STREAM, 0);
	if (m_sock != -1)
	{
		if (!connect(m_sock, (struct sockaddr *) &m_servaddr, m_clilen))
		{
			int val=1;
			fcntl(m_sock, F_SETFL, O_NONBLOCK);
			setsockopt(m_sock, SOL_SOCKET, SO_REUSEADDR, &val, 4);
			m_sn = eSocketNotifier::create(eApp, m_sock,
				eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Error|eSocketNotifier::Hungup);
			CONNECT(m_sn->activated, eDVBCAService::socketCB);
			
		}
//		else
//			eDebug("[eDVBCAService] connect failed %m");
	}
	else
		eDebug("[eDVBCAService] create socket failed %m");
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

	unsigned int build_hash = ( pmtpid << 16);
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
		eDVBChannelID chid;
		m_service.getChannelID(chid);
		channel_data *data = getChannelData(chid);
		if (data)
		{
			int lenbytes = m_capmt[3] & 0x80 ? m_capmt[3] & ~0x80 : 0;
			data->m_dataDemux = m_capmt[24+lenbytes];
		}
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
				m_retryTimer->start(0,true);
//				eDebug("[eDVBCAService] send failed .. immediate retry");
				break;
			default:
				m_retryTimer->start(5000,true);
//				eDebug("[eDVBCAService] send failed .. retry in 5 sec");
				break;
		}
		++m_sendstate;
	}
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
