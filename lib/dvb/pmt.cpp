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
#include <dvbsi++/application_name_descriptor.h>

eDVBServicePMTHandler::eDVBServicePMTHandler()
	:m_ca_servicePtr(0), m_dvb_scan(0), m_decode_demux_num(0xFF), m_no_pat_entry_delay(eTimer::create())
{
	m_use_decode_demux = 0;
	m_pmt_pid = -1;
	m_dsmcc_pid = -1;
	m_service_type = livetv;
	eDVBResourceManager::getInstance(m_resourceManager);
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
		&& (state == iDVBChannel::state_ok))
	{
		if (!m_demux && m_channel)
		{
			if (m_pvr_demux_tmp)
			{
				m_demux = m_pvr_demux_tmp;
				m_pvr_demux_tmp = NULL;
			}
			else if (m_channel->getDemux(m_demux, (!m_use_decode_demux) ? 0 : iDVBChannel::capDecode))
				eDebug("[eDVBServicePMTHandler] Allocating %s-decoding a demux for now tuned-in channel failed.", m_use_decode_demux ? "" : "non-");
		}

		if (m_demux)
		{
			eDebug("[eDVBServicePMTHandler] ok ... now we start!!");
			m_have_cached_program = false;

			if (m_service && !m_service->cacheEmpty())
			{
				serviceEvent(eventNewProgramInfo);
				if (m_use_decode_demux)
				{
					if (!m_ca_servicePtr)
					{
						registerCAService();
					}
					if (m_ca_servicePtr && !m_service->usePMT())
					{
						eDebug("[eDVBServicePMTHandler] create cached caPMT");
						eDVBCAHandler::getInstance()->handlePMT(m_reference, m_service);
					}
					else if (m_ca_servicePtr && (m_service->m_flags & eDVBService::dxIsScrambledPMT))
					{
						eDebug("[eDVBServicePMTHandler] create caPMT to descramble PMT");
						eDVBCAHandler::getInstance()->handlePMT(m_reference, m_service);
					}
				}
			}

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
		eDebug("[eDVBServicePMTHandler] tune failed.");
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

void eDVBServicePMTHandler::registerCAService()
{
	int demuxes[2] = {0, 0};
	uint8_t demuxid;
	uint8_t adapterid;
	m_demux->getCADemuxID(demuxid);
	m_demux->getCAAdapterID(adapterid);
	demuxes[0] = demuxid;
	if (m_decode_demux_num != 0xFF)
		demuxes[1] = m_decode_demux_num;
	else
		demuxes[1] = demuxes[0];
	eDVBCAHandler::getInstance()->registerService(m_reference, adapterid, demuxes, (int)m_service_type, m_ca_servicePtr);
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
		if (m_use_decode_demux)
		{
			if (!m_ca_servicePtr)
			{
				registerCAService();
			}
			eDVBCIInterfaces::getInstance()->recheckPMTHandlers();
			eDVBCIInterfaces::getInstance()->gotPMT(this);
		}
		if (m_ca_servicePtr)
		{
			ePtr<eTable<ProgramMapSection> > ptr;
			if (!m_PMT.getCurrent(ptr))
				eDVBCAHandler::getInstance()->handlePMT(m_reference, ptr);
			else
				eDebug("[eDVBServicePMTHandler] cannot call buildCAPMT");
		}
	}
}

void eDVBServicePMTHandler::sendEventNoPatEntry()
{
	serviceEvent(eventNoPATEntry);
}

void eDVBServicePMTHandler::PATready(int)
{
	eDebug("[eDVBServicePMTHandler] PATready");
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
			eDebug("[eDVBServicePMTHandler] use single pat entry!");
			m_reference.setServiceID(eServiceID(service_id_single));
			pmtpid = pmtpid_single;
		}
		if (pmtpid == -1) {
			eDebug("[eDVBServicePMTHandler] no PAT entry found.. start delay");
			m_no_pat_entry_delay->start(1000, true);
		}
		else {
			eDebug("[eDVBServicePMTHandler] use pmtpid %04x for service_id %04x", pmtpid, m_reference.getServiceID().get());
			m_no_pat_entry_delay->stop();
			m_PMT.begin(eApp, eDVBPMTSpec(pmtpid, m_reference.getServiceID().get()), m_demux);
		}
	} else
		serviceEvent(eventNoPAT);
}

void eDVBServicePMTHandler::AITready(int error)
{
	eDebug("[eDVBServicePMTHandler] AITready");
	ePtr<eTable<ApplicationInformationSection> > ptr;
	m_aitInfoList.clear();
	if (!m_AIT.getCurrent(ptr))
	{
		m_HBBTVUrl = "";
		for (std::vector<ApplicationInformationSection*>::const_iterator it = ptr->getSections().begin(); it != ptr->getSections().end(); ++it)
		{
			for (std::list<ApplicationInformation *>::const_iterator i = (*it)->getApplicationInformation()->begin(); i != (*it)->getApplicationInformation()->end(); ++i)
			{
				struct aitInfo aitinfo;
				aitinfo.id = ((ApplicationIdentifier*)(*i)->getApplicationIdentifier())->getApplicationId();
				for (DescriptorConstIterator desc = (*i)->getDescriptors()->begin(); desc != (*i)->getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
					case APPLICATION_DESCRIPTOR:
						break;
					case APPLICATION_NAME_DESCRIPTOR:
					{
						ApplicationNameDescriptor *appname = (ApplicationNameDescriptor*)(*desc);
						for (ApplicationNameConstIterator appnamesit = appname->getApplicationNames()->begin(); appnamesit != appname->getApplicationNames()->end(); ++appnamesit)
						{
							aitinfo.name = (*appnamesit)->getApplicationName();
							eDebug("[eDVBServicePMTHandler] AIT: %s", aitinfo.name.c_str());
						}
						break;
					}
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
								if ((*i)->getApplicationControlCode() == 0x01) /* AUTOSTART */
								{
									m_HBBTVUrl = (*interactionit)->getUrlBase()->getUrl();
								}
								aitinfo.url = (*interactionit)->getUrlBase()->getUrl();
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
						if ((*i)->getApplicationControlCode() == 0x01) /* AUTOSTART */
						{
							m_HBBTVUrl += applicationlocation->getInitialPath();
						}
						aitinfo.url += applicationlocation->getInitialPath();
						m_aitInfoList.push_back(aitinfo);
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
	eDebug("[eDVBServicePMTHandler] OCready");
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

void eDVBServicePMTHandler::getAITApplications(std::map<int, std::string> &aitlist)
{
	for (std::vector<struct aitInfo>::iterator it = m_aitInfoList.begin(); it != m_aitInfoList.end(); ++it)
	{
		aitlist[it->id] = it->url;
	}
}

void eDVBServicePMTHandler::getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids, std::vector<std::string> &ecmdatabytes)
{
	program prog;

	if (!getProgramInfo(prog))
	{
		for (std::list<program::capid_pair>::iterator it = prog.caids.begin(); it != prog.caids.end(); ++it)
		{
			caids.push_back(it->caid);
			ecmpids.push_back(it->capid);
			ecmdatabytes.push_back(it->databytes);
		}
	}
}

int eDVBServicePMTHandler::getProgramInfo(program &program)
{
	ePtr<eTable<ProgramMapSection> > ptr;
	int cached_apid_ac3 = -1;
	int cached_apid_ddp = -1;
	int cached_apid_mpeg = -1;
	int cached_apid_aache = -1;
	int cached_apid_aac = -1;
	int cached_vpid = -1;
	int cached_tpid = -1;
	int ret = -1;
	uint8_t adapter, demux;

	if (m_have_cached_program)
	{
		program = m_cached_program;
		return 0;
	}

	eDVBPMTParser::clearProgramInfo(program);

	if ( m_service && !m_service->cacheEmpty() )
	{
		cached_vpid = m_service->getCacheEntry(eDVBService::cVPID);
		cached_apid_mpeg = m_service->getCacheEntry(eDVBService::cMPEGAPID);
		cached_apid_ac3 = m_service->getCacheEntry(eDVBService::cAC3PID);
		cached_apid_ddp = m_service->getCacheEntry(eDVBService::cDDPPID);
		cached_apid_aache = m_service->getCacheEntry(eDVBService::cAACHEAPID);
		cached_apid_aac = m_service->getCacheEntry(eDVBService::cAACAPID);
		cached_tpid = m_service->getCacheEntry(eDVBService::cTPID);
	}

	if ( ((m_service && m_service->usePMT()) || !m_service) && eDVBPMTParser::getProgramInfo(program) >= 0)
	{
		unsigned int i;
		int first_non_mpeg = -1;
		int audio_cached = -1;
		int autoaudio_mpeg = -1;
		int autoaudio_ac3 = -1;
		int autoaudio_ddp = -1;
		int autoaudio_aache = -1;
		int autoaudio_aac = -1;
		int autoaudio_level = 4;

		std::string configvalue;
		std::vector<std::string> autoaudio_languages;
		configvalue = eConfigManager::getConfigValue("config.autolanguage.audio_autoselect1");
		if (configvalue != "" && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.audio_autoselect2");
		if (configvalue != "" && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.audio_autoselect3");
		if (configvalue != "" && configvalue != "None")
			autoaudio_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.audio_autoselect4");
		if (configvalue != "" && configvalue != "None")
			autoaudio_languages.push_back(configvalue);

		int autosub_txt_normal = -1;
		int autosub_txt_hearing = -1;
		int autosub_dvb_normal = -1;
		int autosub_dvb_hearing = -1;
		int autosub_level =4;

		std::vector<std::string> autosub_languages;
		configvalue = eConfigManager::getConfigValue("config.autolanguage.subtitle_autoselect1");
		if (configvalue != "" && configvalue != "None")
			autosub_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.subtitle_autoselect2");
		if (configvalue != "" && configvalue != "None")
			autosub_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.subtitle_autoselect3");
		if (configvalue != "" && configvalue != "None")
			autosub_languages.push_back(configvalue);
		configvalue = eConfigManager::getConfigValue("config.autolanguage.subtitle_autoselect4");
		if (configvalue != "" && configvalue != "None")
			autosub_languages.push_back(configvalue);

		m_dsmcc_pid = program.dsmccPid;
		if (program.aitPid >= 0)
		{
			m_AIT.begin(eApp, eDVBAITSpec(program.aitPid), m_demux);
		}

		for (i = 0; i < program.videoStreams.size(); i++)
		{
			if (program.videoStreams[i].pid == cached_vpid)
			{
				/* put cached vpid at the front of the videoStreams vector */
				if (i > 0)
				{
					videoStream tmp = program.videoStreams[i];
					program.videoStreams[i] = program.videoStreams[0];
					program.videoStreams[0] = tmp;
				}
				break;
			}
		}
		for (i = 0; i < program.audioStreams.size(); i++)
		{
			if (program.audioStreams[i].pid == cached_apid_ac3
			 || program.audioStreams[i].pid == cached_apid_ddp
			 || program.audioStreams[i].pid == cached_apid_mpeg
			 || program.audioStreams[i].pid == cached_apid_aache
			 || program.audioStreams[i].pid == cached_apid_aac)
			{
				/* if we find the cached pids, this will be our default stream */
				audio_cached = i;
			}
			/* also, we need to know the first non-mpeg (i.e. "ac3"/dts/...) stream */
			if ((program.audioStreams[i].type != audioStream::atMPEG) && ((first_non_mpeg == -1)
				|| (program.audioStreams[i].pid == cached_apid_ac3)
				|| (program.audioStreams[i].pid == cached_apid_ddp)
				|| (program.audioStreams[i].pid == cached_apid_aache)
				|| (program.audioStreams[i].pid == cached_apid_aac)))
			{
				first_non_mpeg = i;
			}
			if (!program.audioStreams[i].language_code.empty())
			{
				int x = 1;
				for (std::vector<std::string>::iterator it = autoaudio_languages.begin();x <= autoaudio_level && it != autoaudio_languages.end();x++,it++)
				{
					if ((*it).find(program.audioStreams[i].language_code) != std::string::npos)
					{
						if (program.audioStreams[i].type == audioStream::atMPEG && (autoaudio_level > x || autoaudio_mpeg == -1))
							autoaudio_mpeg = i;
						else if (program.audioStreams[i].type == audioStream::atAC3 && (autoaudio_level > x || autoaudio_ac3 == -1))
							autoaudio_ac3 = i;
						else if (program.audioStreams[i].type == audioStream::atDDP && (autoaudio_level > x || autoaudio_ddp == -1))
							autoaudio_ddp = i;
						else if (program.audioStreams[i].type == audioStream::atAACHE && (autoaudio_level > x || autoaudio_aache == -1))
							autoaudio_aache = i;
						else if (program.audioStreams[i].type == audioStream::atAAC && (autoaudio_level > x || autoaudio_aac == -1))
							autoaudio_aac = i;
						autoaudio_level = x;
						break;
					}
				}
			}
		}
		for (i = 0; i < program.subtitleStreams.size(); i++)
		{
			if (!program.subtitleStreams[i].language_code.empty())
			{
				int x = 1;
				for (std::vector<std::string>::iterator it2 = autosub_languages.begin();x <= autosub_level && it2 != autosub_languages.end();x++,it2++)
				{
					if ((*it2).find(program.subtitleStreams[i].language_code) != std::string::npos)
					{
						autosub_level = x;
						if (program.subtitleStreams[i].subtitling_type >= 0x10)
						{
							/* DVB subs */
							if (program.subtitleStreams[i].subtitling_type >= 0x20)
								autosub_dvb_hearing = i;
							else
								autosub_dvb_normal = i;
						}
						else
						{
							/* TXT subs */
							if (program.subtitleStreams[i].subtitling_type == 0x05)
								autosub_txt_hearing = i;
							else
								autosub_txt_normal = i;
						}
						break;
					}
				}
			}
		}

		bool defaultac3 = eConfigManager::getConfigBoolValue("config.autolanguage.audio_defaultac3");
		bool defaultddp = eConfigManager::getConfigBoolValue("config.autolanguage.audio_defaultddp");
		bool useaudio_cache = eConfigManager::getConfigBoolValue("config.autolanguage.audio_usecache");

		if (useaudio_cache && audio_cached != -1)
			program.defaultAudioStream = audio_cached;
		else if (defaultac3 && autoaudio_ac3 != -1)
			program.defaultAudioStream = autoaudio_ac3;
		else if (defaultddp && autoaudio_ddp != -1)
			program.defaultAudioStream = autoaudio_ddp;
		else
		{
			if (autoaudio_mpeg != -1)
				program.defaultAudioStream = autoaudio_mpeg;
			else if (autoaudio_ac3 != -1)
				program.defaultAudioStream = autoaudio_ac3;
			else if (autoaudio_ddp != -1)
				program.defaultAudioStream = autoaudio_ddp;
			else if (autoaudio_aache != -1)
				program.defaultAudioStream = autoaudio_aache;
			else if (autoaudio_aac != -1)
				program.defaultAudioStream = autoaudio_aac;
			else if (first_non_mpeg != -1 && (defaultac3 || defaultddp))
				program.defaultAudioStream = first_non_mpeg;
		}

		bool allow_hearingimpaired = eConfigManager::getConfigBoolValue("config.autolanguage.subtitle_hearingimpaired");
		bool default_hearingimpaired = eConfigManager::getConfigBoolValue("config.autolanguage.subtitle_defaultimpaired");
		bool defaultdvb = eConfigManager::getConfigBoolValue("config.autolanguage.subtitle_defaultdvb");
		int equallanguagemask = eConfigManager::getConfigIntValue("config.autolanguage.equal_languages");

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
			else if (allow_hearingimpaired && autosub_txt_hearing != -1)
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

		ret = 0;
	}
	else if ( m_service && !m_service->cacheEmpty() )
	{
		int cached_pcrpid = m_service->getCacheEntry(eDVBService::cPCRPID),
			vpidtype = m_service->getCacheEntry(eDVBService::cVTYPE),
			pmtpid = m_service->getCacheEntry(eDVBService::cPMTPID),
			subpid = m_service->getCacheEntry(eDVBService::cSUBTITLE),
			cnt=0;
		if (pmtpid > 0)
		{
			program.pmtPid = pmtpid;
		}
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
		if ( cached_apid_ddp != -1 )
		{
			audioStream s;
			s.type = audioStream::atDDP;
			s.pid = cached_apid_ddp;
			s.rdsPid = -1;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( cached_apid_aache != -1 )
		{
			audioStream s;
			s.type = audioStream::atAACHE;
			s.pid = cached_apid_aache;
			s.rdsPid = -1;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( cached_apid_aac != -1 )
		{
			audioStream s;
			s.type = audioStream::atAAC;
			s.pid = cached_apid_aac;
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
		if (subpid > 0)
		{
			subtitleStream s;
			s.pid = (subpid & 0xffff0000) >> 16;
			if (s.pid != program.textPid)
			{
				s.subtitling_type = 0x10;
				s.composition_page_id = (subpid >> 8) & 0xff;
				s.ancillary_page_id = subpid & 0xff;
				program.subtitleStreams.push_back(s);
				++cnt;
			}
		}
		if (cnt)
		{
			ret = 0;
		}
	}

	if (m_service && program.caids.empty()) // Add CAID from cache
	{
		CAID_LIST &caids = m_service->m_ca;
		for (CAID_LIST::iterator it(caids.begin()); it != caids.end(); ++it)
		{
			program::capid_pair pair;
			pair.caid = *it;
			pair.capid = -1; // not known yet
			pair.databytes.clear();
			program.caids.push_back(pair);
		}
	}

	if (m_demux)
	{
		m_demux->getCAAdapterID(adapter);
		program.adapterId = adapter;
		m_demux->getCADemuxID(demux);
		program.demuxId = demux;
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
	if (m_pvr_channel)
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
				eDebug("[eDVBServicePMTHandler] no channel list");
			else
			{
				eDVBChannelID chid, curr_chid;
				m_reference.getChannelID(chid);
				curr_chid = m_dvb_scan->getCurrentChannelID();
				if (chid == curr_chid)
				{
					m_dvb_scan->insertInto(db, true);
					eDebug("[eDVBServicePMTHandler] sdt update done!");
				}
				else
				{
					eDebug("[eDVBServicePMTHandler] ignore sdt update data.... incorrect transponder tuned!!!");
					if (chid.dvbnamespace != curr_chid.dvbnamespace)
						eDebug("[eDVBServicePMTHandler] incorrect namespace. expected: %x current: %x",chid.dvbnamespace.get(), curr_chid.dvbnamespace.get());
					if (chid.transport_stream_id != curr_chid.transport_stream_id)
						eDebug("[eDVBServicePMTHandler] incorrect transport_stream_id. expected: %x current: %x",chid.transport_stream_id.get(), curr_chid.transport_stream_id.get());
					if (chid.original_network_id != curr_chid.original_network_id)
						eDebug("[eDVBServicePMTHandler] incorrect namespace. expected: %x current: %x",chid.original_network_id.get(), curr_chid.original_network_id.get());
				}
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
	return tuneExt(ref, s, NULL, cue, simulate, service, type, descramble);
}

int eDVBServicePMTHandler::tuneExt(eServiceReferenceDVB &ref, ePtr<iTsSource> &source, const char *streaminfo_file, eCueSheet *cue, bool simulate, eDVBService *service, serviceType type, bool descramble)
{
	RESULT res=0;
	m_reference = ref;

		/*
		 * We need to m_use decode demux only when we are descrambling (demuxers > ca demuxers)
		 * To avoid confusion with use_decode_demux now we look only descramble argument
		 */
	m_use_decode_demux = descramble;

	m_no_pat_entry_delay->stop();
	m_service_type = type;

		/* use given service as backup. This is used for timeshift where we want to clone the live stream using the cache, but in fact have a PVR channel */
	m_service = service;

		/* is this a normal (non PVR) channel? */
	if (ref.path.empty())
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = m_resourceManager->allocateChannel(chid, m_channel, simulate);
		if (!simulate)
			eDebug("[eDVBServicePMTHandler] allocate Channel: res %d", res);

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
			eWarning("[eDVBServicePMTHandler] no .meta file found, trying to find PMT pid");
			if (source)
				tstools.setSource(source, NULL);
			if (b)
			{
				eDVBPMTParser::program program;
				if (!tstools.findPMT(program))
				{
					m_pmt_pid = program.pmtPid;
					eDebug("[eDVBServicePMTHandler] PMT pid %04x, service id %d", m_pmt_pid, program.serviceId);
					m_reference.setServiceID(program.serviceId);
				}
			}
			else
				eWarning("[eDVBServicePMTHandler] no valid source to find PMT pid!");
		}
		eDebug("[eDVBServicePMTHandler] alloc PVR");
			/* allocate PVR */
		eDVBChannelID chid;
		if (m_service_type == streamclient) ref.getChannelID(chid);
		res = m_resourceManager->allocatePVRChannel(chid, m_pvr_channel);
		if (res)
			eDebug("[eDVBServicePMTHandler] allocatePVRChannel failed!\n");
		m_channel = m_pvr_channel;
	}

	if (!simulate)
	{
		if (m_channel)
		{
			m_channel->connectStateChange(
				sigc::mem_fun(*this, &eDVBServicePMTHandler::channelStateChanged),
				m_channelStateChanged_connection);
			m_last_channel_state = -1;
			channelStateChanged(m_channel);

			m_channel->connectEvent(
				sigc::mem_fun(*this, &eDVBServicePMTHandler::channelEvent),
				m_channelEvent_connection);

			if (ref.path.empty())
			{
				m_dvb_scan = new eDVBScan(m_channel, true, false);
				if (!eConfigManager::getConfigBoolValue("config.misc.disable_background_scan"))
				{
					/*
					 * not starting a dvb scan triggers what appears to be a
					 * refcount bug (channel?/demux?), so we always start a scan,
					 * but ignore the results when background scanning is disabled
					 */
					m_dvb_scan->connectEvent(sigc::mem_fun(*this, &eDVBServicePMTHandler::SDTScanEvent), m_scan_event_connection);
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
				eDebug("[eDVBServicePMTHandler] Allocating %s-decoding a demux for PVR channel failed.", m_use_decode_demux ? "" : "non-");
			else if (source)
				m_pvr_channel->playSource(source, streaminfo_file);
			else
				m_pvr_channel->playFile(ref.path.c_str());

			if (m_service_type == offline)
			{
				m_pvr_channel->setOfflineDecodeMode(eConfigManager::getConfigIntValue("config.recording.offline_decode_delay"));
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
		m_pvr_channel->stop();
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
