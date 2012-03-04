#include <lib/base/nconfig.h> // access to python config
#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/cahandler.h>
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
#include <dvbsi++/simple_application_location_descriptor.h>
#include <dvbsi++/simple_application_boundary_descriptor.h>
#include <dvbsi++/transport_protocol_descriptor.h>

eDVBServicePMTHandler::eDVBServicePMTHandler()
	:m_ca_servicePtr(0), m_dvb_scan(0), m_decode_demux_num(0xFF), m_no_pat_entry_delay(eTimer::create())
{
	m_use_decode_demux = 0;
	m_pmt_pid = -1;
	m_dsmcc_pid = -1;
	m_service_type = livetv;
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
	CONNECT(m_AIT.tableReady, eDVBServicePMTHandler::AITready);
	CONNECT(m_OC.tableReady, eDVBServicePMTHandler::OCready);
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

		if (m_demux)
		{
			eDebug("ok ... now we start!!");
			m_have_cached_program = false;

			if ( m_service && !m_service->cacheEmpty() )
				serviceEvent(eventNewProgramInfo);

			if (!m_service || m_service->usePMT())
			{
				if (m_pmt_pid == -1)
					m_PAT.begin(eApp, eDVBPATSpec(), m_demux);
				else
					m_PMT.begin(eApp, eDVBPMTSpec(m_pmt_pid, m_reference.getServiceID().get()), m_demux);
			}

			serviceEvent(eventTuned);
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
	case iDVBChannel::evtStopped:
		serviceEvent(eventStopped);
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
		switch (m_service_type)
		{
		case livetv:
		case recording:
		case scrambled_recording:
		case timeshift_recording:
		case scrambled_timeshift_recording:
		case streamserver:
		case scrambled_streamserver:
		case streamclient:
			eEPGCache::getInstance()->PMTready(this);
			break;
		default:
			/* do not start epg caching for other types of services */
			break;
		}
		if (doDescramble)
		{
			if (!m_ca_servicePtr)
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
				eDVBCAHandler::getInstance()->registerService(m_reference, adapterid, demuxes, (int)m_service_type, m_ca_servicePtr);
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

void eDVBServicePMTHandler::AITready(int error)
{
	eDebug("AITready");
	ePtr<eTable<ApplicationInformationSection> > ptr;
	if (!m_AIT.getCurrent(ptr))
	{
		m_HBBTVUrl = "";
		for (std::vector<ApplicationInformationSection*>::const_iterator it = ptr->getSections().begin(); it != ptr->getSections().end(); ++it)
		{
			for (std::list<ApplicationInformation *>::const_iterator i = (*it)->getApplicationInformation()->begin(); i != (*it)->getApplicationInformation()->end(); ++i)
			{
				if ((*i)->getApplicationControlCode() == 0x01) /* AUTOSTART */
				{
					for (DescriptorConstIterator desc = (*i)->getDescriptors()->begin();
						desc != (*i)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case APPLICATION_DESCRIPTOR:
							break;
						case APPLICATION_NAME_DESCRIPTOR:
							break;
						case TRANSPORT_PROTOCOL_DESCRIPTOR:
						{
							TransportProtocolDescriptor *transport = (TransportProtocolDescriptor*)(*desc);
							switch (transport->getProtocolId())
							{
							case 1: /* object carousel */
								if (m_dsmcc_pid >= 0)
								{
									m_OC.begin(eApp, eDVBDSMCCDLDataSpec(m_dsmcc_pid), m_demux);
								}
								break;
							case 2: /* ip */
								break;
							case 3: /* interaction */
								for (InterActionTransportConstIterator interactionit = transport->getInteractionTransports()->begin(); interactionit != transport->getInteractionTransports()->end(); ++interactionit)
								{
									m_HBBTVUrl = (*interactionit)->getUrlBase()->getUrl();
									break;
								}
								break;
							}
							break;
						}
						case GRAPHICS_CONSTRAINTS_DESCRIPTOR:
							break;
						case SIMPLE_APPLICATION_LOCATION_DESCRIPTOR:
						{
							SimpleApplicationLocationDescriptor *applicationlocation = (SimpleApplicationLocationDescriptor*)(*desc);
							m_HBBTVUrl += applicationlocation->getInitialPath();
							break;
						}
						case APPLICATION_USAGE_DESCRIPTOR:
							break;
						case SIMPLE_APPLICATION_BOUNDARY_DESCRIPTOR:
							break;
						}
					}
				}
			}
		}
		if (!m_HBBTVUrl.empty())
		{
			serviceEvent(eventHBBTVInfo);
		}
	}
	/* for now, do not keep listening for table updates */
	m_AIT.stop();
}

void eDVBServicePMTHandler::OCready(int error)
{
	eDebug("OCready");
	ePtr<eTable<OCSection> > ptr;
	if (!m_OC.getCurrent(ptr))
	{
		std::string data;
		for (std::vector<OCSection*>::const_iterator it = ptr->getSections().begin(); it != ptr->getSections().end(); ++it)
		{
		}
	}
	/* for now, do not keep listening for table updates */
	m_OC.stop();
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

	if (m_have_cached_program)
	{
		program = m_cached_program;
		return 0;
	}

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.subtitleStreams.clear();
	program.pcrPid = -1;
	program.pmtPid = -1;
	program.textPid = -1;
	program.aitPid = -1;

	program.defaultAudioStream = 0;
	program.defaultSubtitleStream = -1;

	if ( m_service && !m_service->cacheEmpty() )
	{
		cached_vpid = m_service->getCacheEntry(eDVBService::cVPID);
		cached_apid_mpeg = m_service->getCacheEntry(eDVBService::cAPID);
		cached_apid_ac3 = m_service->getCacheEntry(eDVBService::cAC3PID);
		cached_tpid = m_service->getCacheEntry(eDVBService::cTPID);
	}

	if ( ((m_service && m_service->usePMT()) || !m_service) && !m_PMT.getCurrent(ptr))
	{
		int first_ac3 = -1;
		int audio_cached = -1;
		int autoaudio_mpeg = -1;
		int autoaudio_ac3 = -1;
		int autoaudio_level = 4;

		std::string configvalue;
		std::vector<std::string> autoaudio_languages;
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_autoselect1", configvalue) && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_autoselect2", configvalue) && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_autoselect3", configvalue) && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_autoselect4", configvalue) && configvalue != "None")
			autoaudio_languages.push_back(configvalue);

		audioStream *prev_audio = 0;

		int autosub_txt_normal = -1;
		int autosub_txt_hearing = -1;
		int autosub_dvb_normal = -1;
		int autosub_dvb_hearing = -1;
		int autosub_level =4;

		std::vector<std::string> autosub_languages;
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_autoselect1", configvalue) && configvalue != "None")
			autosub_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_autoselect2", configvalue) && configvalue != "None")
			autosub_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_autoselect3", configvalue) && configvalue != "None")
			autosub_languages.push_back(configvalue);
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_autoselect4", configvalue) && configvalue != "None")
			autosub_languages.push_back(configvalue);

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
					if (!isvideo && !isaudio)
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
									case 0x10 ... 0x13: // dvb subtitles normal
									case 0x20 ... 0x23: // dvb subtitles hearing impaired
										break;
									default:
										eDebug("dvb subtitle %s PID %04x with wrong subtitling type (%02x)... force 0x10!!",
										s.language_code.c_str(), s.pid, s.subtitling_type);
										s.subtitling_type = 0x10;
										break;
									}
									s.composition_page_id = (*it)->getCompositionPageId();
									s.ancillary_page_id = (*it)->getAncillaryPageId();
									std::string language = (*it)->getIso639LanguageCode();
									s.language_code = language;
//								eDebug("add dvb subtitle %s PID %04x, type %d, composition page %d, ancillary_page %d", s.language_code.c_str(), s.pid, s.subtitling_type, s.composition_page_id, s.ancillary_page_id);

									if (!language.empty())
									{
										int x = 1;
										for (std::vector<std::string>::iterator it2 = autosub_languages.begin();x <= autosub_level && it2 != autosub_languages.end();x++,it2++)
										{
											if ((*it2).find(language) != std::string::npos)
											{
												autosub_level = x;
												if (s.subtitling_type >= 0x20)
													autosub_dvb_hearing = program.subtitleStreams.size();
												else
													autosub_dvb_normal = program.subtitleStreams.size();
												break;
											}
										}
									}
									issubtitle = 1;
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
									std::string language;
									for (VbiTeletextConstIterator it(list->begin()); it != list->end(); ++it)
									{
										switch((*it)->getTeletextType())
										{
										case 0x02: // Teletext subtitle page
										case 0x05: // Teletext subtitle page for hearing impaired pepople
											language = (*it)->getIso639LanguageCode();
											s.language_code = language;
											s.teletext_page_number = (*it)->getTeletextPageNumber();
											s.teletext_magazine_number = (*it)->getTeletextMagazineNumber();
//										eDebug("add teletext subtitle %s PID %04x, page number %d, magazine number %d", s.language_code.c_str(), s.pid, s.teletext_page_number, s.teletext_magazine_number);
											if (!language.empty())
											{
												int x = 1;
												for (std::vector<std::string>::iterator it2 = autosub_languages.begin();x <= autosub_level && it2 != autosub_languages.end();x++,it2++)
												{
													if ((*it2).find(language) != std::string::npos)
													{
														autosub_level = x;
														if (s.subtitling_type == 0x05)
															autosub_txt_hearing = program.subtitleStreams.size();
														else
															autosub_txt_normal = program.subtitleStreams.size();
														break;
													}
												}
											}
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
							case ENHANCED_AC3_DESCRIPTOR:
								isaudio = 1;
								audio.type = audioStream::atDDP;
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
								const Iso639LanguageList *languages = ((Iso639LanguageDescriptor*)*desc)->getIso639Languages();
								/* use last language code */
								int cnt=0;
								for (Iso639LanguageConstIterator i=languages->begin(); i != languages->end(); ++i)
								{
									std::string language=(*i)->getIso639LanguageCode();
									if ( cnt==0 )
										audio.language_code = language;
									else
										audio.language_code += "/" + language;
									cnt++;
										
									if (!language.empty())
									{
										int x = 1;
										for (std::vector<std::string>::iterator it = autoaudio_languages.begin();x <= autoaudio_level && it != autoaudio_languages.end();x++,it++)
										{
											if ((*it).find(language) != std::string::npos)
											{
												if (audio.type == audioStream::atMPEG && (autoaudio_level > x || autoaudio_mpeg == -1)) 
													autoaudio_mpeg = program.audioStreams.size();
												else if (audio.type != audioStream::atMPEG && (autoaudio_level > x || autoaudio_ac3 == -1))
													autoaudio_ac3 = program.audioStreams.size();
												autoaudio_level = x;
												break;
											}
										}
									}
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
					break;
				}
				case 0x05: /* ITU-T Rec. H.222.0 | ISO/IEC 13818-1 private sections */
				{
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case APPLICATION_SIGNALLING_DESCRIPTOR:
							program.aitPid = (*es)->getPid();
							m_AIT.begin(eApp, eDVBAITSpec(program.aitPid), m_demux);
							break;
						}
					}
					break;
				}
				case 0x0b: /* ISO/IEC 13818-6 DSM-CC U-N Messages */
				{
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
						case CAROUSEL_IDENTIFIER_DESCRIPTOR:
							m_dsmcc_pid = (*es)->getPid();
							break;
						case STREAM_IDENTIFIER_DESCRIPTOR:
							break;
						}
					}
					break;
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
						audio_cached = program.audioStreams.size();

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

		bool defaultac3 = false;
		bool useaudio_cache = false;

		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_defaultac3", configvalue))
			defaultac3 = configvalue == "True";
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.audio_usecache", configvalue))
			useaudio_cache = configvalue == "True";

		if (useaudio_cache && audio_cached != -1)
			program.defaultAudioStream = audio_cached;
		else if ( defaultac3 )
		{
			if ( autoaudio_ac3 != -1 )
				program.defaultAudioStream = autoaudio_ac3;
			else if ( autoaudio_mpeg != -1 )
				program.defaultAudioStream = autoaudio_mpeg;
			else if ( first_ac3 != -1 )
				program.defaultAudioStream = first_ac3;
		}
		else
		{
			if ( autoaudio_mpeg != -1 )
				program.defaultAudioStream = autoaudio_mpeg;
			else if ( autoaudio_ac3 != -1 )
				program.defaultAudioStream = autoaudio_ac3;
		}

		bool allow_hearingimpaired = false;
		bool default_hearingimpaired = false;
		bool defaultdvb = false;
		int equallanguagemask = false;

		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_hearingimpaired", configvalue))
			allow_hearingimpaired = configvalue == "True";
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_defaultimpaired", configvalue))
			default_hearingimpaired = configvalue == "True";
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.subtitle_defaultdvb", configvalue))
			defaultdvb = configvalue == "True";
		if (!ePythonConfigQuery::getConfigValue("config.autolanguage.equal_languages", configvalue))
			equallanguagemask = atoi(configvalue.c_str());

		if (defaultdvb)
		{
			if (allow_hearingimpaired && default_hearingimpaired && autosub_dvb_hearing != -1)
				program.defaultSubtitleStream = autosub_dvb_hearing;
			else if (autosub_dvb_normal != -1)
				program.defaultSubtitleStream = autosub_dvb_normal;
			else if (allow_hearingimpaired && autosub_dvb_hearing != -1)
				program.defaultSubtitleStream = autosub_dvb_hearing;
			else if (allow_hearingimpaired && default_hearingimpaired && autosub_txt_hearing != -1)
				program.defaultSubtitleStream = autosub_txt_hearing;
			else if (autosub_txt_normal != -1)
				program.defaultSubtitleStream = autosub_txt_normal;
			else if (allow_hearingimpaired && autosub_dvb_hearing != -1)
				program.defaultSubtitleStream = autosub_txt_hearing;
		}
		else
		{
			if (allow_hearingimpaired && default_hearingimpaired && autosub_txt_hearing != -1)
				program.defaultSubtitleStream = autosub_txt_hearing;
			else if (autosub_txt_normal != -1)
				program.defaultSubtitleStream = autosub_txt_normal;
			else if (allow_hearingimpaired && autosub_txt_hearing != -1)
				program.defaultSubtitleStream = autosub_txt_hearing;
			else if (allow_hearingimpaired && default_hearingimpaired && autosub_dvb_hearing != -1)
				program.defaultSubtitleStream = autosub_dvb_hearing;
			else if (autosub_dvb_normal != -1)
				program.defaultSubtitleStream = autosub_dvb_normal;
			else if (allow_hearingimpaired && autosub_dvb_hearing != -1)
				program.defaultSubtitleStream = autosub_dvb_hearing;
		}
		if (program.defaultSubtitleStream != -1 && (equallanguagemask & (1<<(autosub_level-1))) == 0 && program.subtitleStreams[program.defaultSubtitleStream].language_code.compare(program.audioStreams[program.defaultAudioStream].language_code) == 0 )
			program.defaultSubtitleStream = -1;
	}
	else if ( m_service && !m_service->cacheEmpty() )
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

	m_cached_program = program;
	m_have_cached_program = true;
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

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *cue, bool simulate, eDVBService *service, serviceType type, bool descramble)
{
	ePtr<iTsSource> s;
	return tuneExt(ref, use_decode_demux, s, NULL, cue, simulate, service, type, descramble);
}

int eDVBServicePMTHandler::tuneExt(eServiceReferenceDVB &ref, int use_decode_demux, ePtr<iTsSource> &source, const char *streaminfo_file, eCueSheet *cue, bool simulate, eDVBService *service, serviceType type, bool descramble)
{
	RESULT res=0;
	m_reference = ref;
	m_use_decode_demux = use_decode_demux;
	m_no_pat_entry_delay->stop();
	m_service_type = type;

	doDescramble = descramble;

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
		eDVBChannelID chid;
		if (m_service_type == streamclient) ref.getChannelID(chid);
		res = m_resourceManager->allocatePVRChannel(chid, m_pvr_channel);
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
				m_dvb_scan = new eDVBScan(m_channel, true, false);
				std::string disable_background_scan;
				if (ePythonConfigQuery::getConfigValue("config.misc.disable_background_scan", disable_background_scan) < 0
					|| disable_background_scan != "True")
				{
					/*
					 * not starting a dvb scan triggers what appears to be a
					 * refcount bug (channel?/demux?), so we always start a scan,
					 * but ignore the results when background scanning is disabled
					 */
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

			if (m_pvr_channel->getDemux(m_pvr_demux_tmp, (!m_use_decode_demux) ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating %s-decoding a demux for PVR channel failed.", m_use_decode_demux ? "" : "non-");
			else if (source)
				m_pvr_channel->playSource(source, streaminfo_file);
			else
				m_pvr_channel->playFile(ref.path.c_str());

			if (m_service_type == offline) 
			{
				std::string delay;
				ePythonConfigQuery::getConfigValue("config.recording.offline_decode_delay", delay);
				m_pvr_channel->setOfflineDecodeMode(atoi(delay.c_str()));
			}
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

	m_OC.stop();
	m_AIT.stop();
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
