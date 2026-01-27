#include <lib/service/servicedvbfcc.h>
#include <lib/components/file_eraser.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/csasession.h>
#include <lib/service/servicedvbsoftdecoder.h>
#include <lib/base/nconfig.h>
#include <lib/base/esimpleconfig.h>

eDVBServiceFCCPlay::eDVBServiceFCCPlay(const eServiceReference &ref, eDVBService *service)
	:eDVBServicePlay(ref, service, false), m_fcc_flag(0), m_fcc_mode(fcc_mode_preparing), m_fcc_mustplay(false),
		m_pmtVersion(-1), m_normal_decoding(false)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceFCCPlay::serviceEvent);
}

eDVBServiceFCCPlay::~eDVBServiceFCCPlay()
{
	// Base class destructor handles m_csa_session and m_soft_decoder cleanup
}

void eDVBServiceFCCPlay::serviceEvent(int event)
{
	if (!m_is_primary) // PiP mode
	{
		eDVBServicePlay::serviceEvent(event);
		return;
	}

	m_tune_state = event;

	switch (event)
	{
		case eDVBServicePMTHandler::eventTuned:
		{
			// Base class will call setupSpeculativeDescrambling() which is overridden
			// by FCC to use onFCCSessionActivated callback instead of onSessionActivated
			eDVBServicePlay::serviceEvent(event);
			pushbackFCCEvents(evTunedIn);
			break;
		}
		case eDVBServicePMTHandler::eventNoResources:
		case eDVBServicePMTHandler::eventNoPAT:
		case eDVBServicePMTHandler::eventNoPATEntry:
		case eDVBServicePMTHandler::eventNoPMT:
		case eDVBServicePMTHandler::eventTuneFailed:
		case eDVBServicePMTHandler::eventMisconfiguration:
		{
			eDVBServicePlay::serviceEvent(event);
			pushbackFCCEvents(evTuneFailed);
			break;
		}
		case eDVBServicePMTHandler::eventChannelAllocated:
		{
			bool is_usb_tuner = checkUsbTuner();
			bool fcc_state_decoding = getFCCStateDecoding();

			if (is_usb_tuner)
			{
				if (fcc_state_decoding)
				{
					m_normal_decoding = true;
					setNormalDecoding();
				}
				else
				{
					eDVBServicePlay::serviceEvent(eDVBServicePMTHandler::eventTuneFailed);
					pushbackFCCEvents(evTuneFailed);
				}
			}
			break;
		}
		case eDVBServicePMTHandler::eventNewProgramInfo:
		{
			if (m_fcc_flag & fcc_tune_failed)
				return;

			eDebug("[eDVBServiceFCCPlay] eventNewProgramInfo %d %d %d", m_timeshift_enabled, m_timeshift_active, m_normal_decoding);
			if (m_normal_decoding)
			{
				eDVBServicePlay::serviceEvent(event);
			}
			else
			{
				if (m_timeshift_enabled)
				updateTimeshiftPids();

				if (!m_timeshift_active)
					processNewProgramInfo();

				if (!m_timeshift_active)
				{
					m_event((iPlayableService*)this, evUpdatedInfo);
					pushbackFCCEvents(evUpdatedInfo);
				}

				// If session exists but ECM monitor not started yet, start it
				// (Session was created by setupSpeculativeDescrambling() in eventTuned)
				if (m_csa_session && !m_csa_session->isEcmAnalyzed())
				{
					eDVBServicePMTHandler::program program;
					if (m_service_handler.getProgramInfo(program) == 0 && !program.caids.empty())
					{
						uint16_t ecm_pid = program.caids.front().capid;
						uint16_t caid = program.caids.front().caid;
						ePtr<iDVBDemux> demux;
						if (m_service_handler.getDataDemux(demux) == 0 && demux)
						{
							eDebug("[eDVBServiceFCCPlay] Starting ECM monitor: PID=%d, CAID=0x%04X", ecm_pid, caid);
							m_csa_session->startECMMonitor(demux, ecm_pid, caid);
						}
					}
				}
			}
			break;
		}
		case eDVBServicePMTHandler::eventPreStart:
		case eDVBServicePMTHandler::eventEOF:
		case eDVBServicePMTHandler::eventSOF:
		{
			eDVBServicePlay::serviceEvent(event);
			break;
		}
		case eDVBServicePMTHandler::eventHBBTVInfo:
		{
			eDVBServicePlay::serviceEvent(event);
			pushbackFCCEvents(evHBBTVInfo);
			break;
		}
	}
}

RESULT eDVBServiceFCCPlay::start()
{
	RESULT ret = 0;

	if (!m_is_primary) // PiP mode
	{
		ret = eDVBServicePlay::start();
		return ret;
	}

	if (m_fcc_flag & fcc_start) // already started
	{
		changeFCCMode();
	}
	else
	{
		m_fcc_flag |= fcc_start;
		pushbackFCCEvents(evStart);

		/* disable CA Interfaces on fcc_mode_preparing */
		m_service_handler.setCaDisable(true);
		ret = eDVBServicePlay::start();
	}
	return ret;
}

void eDVBServiceFCCPlay::pushbackFCCEvents(int event)
{
	if (event == evTuneFailed)
		m_fcc_flag |= fcc_tune_failed;
	m_fcc_events.push_back(event);
}

void eDVBServiceFCCPlay::popFCCEvents()
{
	m_fcc_events.unique(); // remove duplicate evUpdatedInfo
	for (std::list<int>::iterator it = m_fcc_events.begin(); it != m_fcc_events.end(); ++it)
	{
		if (*it == evUpdatedInfo)
		{
			updateFCCDecoder();
			break;
		}
	}

	/* add CaHandler */
	m_service_handler.addCaHandler();

	// Activate SoftCSA session when switching to decoding mode
	// This enables software descrambling for CSA-ALT channels
	activateFCCCSASession();

	/* send events */
	for (std::list<int>::iterator it = m_fcc_events.begin(); it != m_fcc_events.end(); ++it)
	{
		int event = *it;
		m_event((iPlayableService*)this, event);
	}
}

void eDVBServiceFCCPlay::changeFCCMode()
{
	if (m_fcc_mode == fcc_mode_decoding)
	{
		eDebug("[eDVBServiceFCCPlay] changeFCCMode [%s] disable FCC decoding.", m_reference.toString().c_str());
		m_fcc_mode = fcc_mode_preparing;

		/* stop time shift */
		eDVBServicePlay::stopTimeshift();

		/* remove CaHandler */
		m_service_handler.removeCaHandler();

		// Deactivate SoftCSA when going back to prepare mode
		deactivateFCCCSASession();

		if (m_fcc_flag & fcc_tune_failed)
			m_event((iPlayableService*)this, evTuneFailed);

		else if (m_fcc_flag & fcc_failed)
			m_event((iPlayableService*)this, evFccFailed);

		FCCDecoderStop();
	}
	else
	{
		eDebug("[eDVBServiceFCCPlay] changeFCCMode [%s] enable FCC decoding.", m_reference.toString().c_str());
		m_fcc_mode = fcc_mode_decoding;
		popFCCEvents();
	}
}

void eDVBServiceFCCPlay::processNewProgramInfo(bool toLive)
{
	updateFCCDecoder(toLive);

	if (m_fcc_flag & fcc_failed)
	{
		m_event((iPlayableService*)this, evFccFailed);
	}
}

void eDVBServiceFCCPlay::updateFCCDecoder(bool sendSeekableStateChanged)
{
	eDebug("[eDVBServiceFCCPlay] updateFCCDecoder [%s]", m_reference.toString().c_str());
	int vpid = -1, vpidtype = -1, pcrpid = -1, tpid = -1, achannel = -1, ac3_delay=-1, pcm_delay=-1;
	bool isProgramInfoCached = false;
	bool pmtVersionChanged = false;

	eDVBServicePMTHandler &h = m_service_handler;

	eDVBServicePMTHandler::program program;
	if (h.getProgramInfo(program))
		eDebug("[eDVBServiceFCCPlay] Getting program info failed.");
	else
	{
		eDebugNoNewLine("have %zd video stream(s)", program.videoStreams.size());
		if (!program.videoStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
				i(program.videoStreams.begin());
				i != program.videoStreams.end(); ++i)
			{
				if (vpid == -1)
				{
					vpid = i->pid;
					vpidtype = i->type;
				}
				if (i != program.videoStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebugNoNewLine(", and %zd audio stream(s)", program.audioStreams.size());
		if (!program.audioStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
				i(program.audioStreams.begin());
				i != program.audioStreams.end(); ++i)
			{
				if (i != program.audioStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebugNoNewLine(", and the pcr pid is %04x", program.pcrPid);
		pcrpid = program.pcrPid;
		eDebugNoNewLine(", and the text pid is %04x", program.textPid);
		tpid = program.textPid;
		eDebug(" %s", program.isCached ? "(Cached)":"");
		isProgramInfoCached = program.isCached;
		if (m_pmtVersion != program.pmtVersion)
		{
			if (m_pmtVersion != -1)
				pmtVersionChanged = true;
			m_pmtVersion = program.pmtVersion;
			//eDebug("[eDVBServiceFCCPlay] updateFCCDecoder pmt version : %d", m_pmtVersion);
		}
	}

	if (!m_decoder)
	{
		h.getDecodeDemux(m_decode_demux);
		if (m_decode_demux)
		{
			m_decode_demux->getMPEGDecoder(m_decoder, m_decoder_index);
			if (m_decoder)
				m_decoder->connectVideoEvent(sigc::mem_fun(*this, &eDVBServiceFCCPlay::video_event), m_video_event_connection);
		}
		m_fcc_mustplay = true;
	}

	if (m_decoder)
	{
		if (!((m_fcc_flag & fcc_ready)||(m_fcc_flag & fcc_novideo)))
		{
			if (vpid == -1)
			{
				if (!isProgramInfoCached)
					m_fcc_flag |= fcc_novideo;
			}
			else if ((vpidtype == -1) || (pcrpid== -1))
			{
				if (!isProgramInfoCached)
					m_fcc_flag |= fcc_failed;
			}
			else if (!m_decoder->prepareFCC(m_decode_demux->getSource(), vpid, vpidtype, pcrpid))
				m_fcc_flag |= fcc_ready;
			else
				m_fcc_flag |= fcc_failed;
		}
		else if (pmtVersionChanged)
		{
			m_decoder->fccUpdatePids(m_decode_demux->getSource(), vpid, vpidtype, pcrpid);
			m_fcc_flag &=~fcc_decoding;
		}
	}

	if (m_fcc_mode != fcc_mode_decoding)
		return;

	/* fcc_mode_decoding */
	if (!(m_fcc_flag & fcc_ready) && !(m_fcc_flag & fcc_novideo))
	{
		eDebug("[eDVBServiceFCCPlay] updateFCCDecoder fcc is not ready.");
		return;
	}

	if (m_decode_demux)
	{
		if (m_is_primary)
		{
			m_teletext_parser = new eDVBTeletextParser(m_decode_demux);
			m_teletext_parser->connectNewPage(sigc::mem_fun(*this, &eDVBServiceFCCPlay::newSubtitlePage), m_new_subtitle_page_connection);
			m_subtitle_parser = new eDVBSubtitleParser(m_decode_demux);
			m_subtitle_parser->connectNewPage(sigc::mem_fun(*this, &eDVBServiceFCCPlay::newDVBSubtitlePage), m_new_dvb_subtitle_page_connection);
			if (m_timeshift_changed)
			{
				struct SubtitleTrack track = {};
				if (getCachedSubtitle(track) >= 0)
				{
					if (track.type == 0) // dvb
						m_subtitle_parser->start(track.pid, track.page_number, track.magazine_number);
					else if (track.type == 1) // ttx
						m_teletext_parser->setPageAndMagazine(track.page_number, track.magazine_number, track.language_code.c_str());
				}
			}
		}
	}

	m_timeshift_changed = 0;

	// Check if SoftCSA should take over (CSA-ALT detected and session is active)
	if (m_csa_session && m_csa_session->isActive() && m_soft_decoder)
	{
		eDebug("[eDVBServiceFCCPlay] CSA-ALT active, SoftDecoder takes over from HW decoder");

		// Stop HW decoder, SoftDecoder will handle decoding
		if (m_decoder)
		{
			m_decoder->setVideoPID(-1, -1);
			m_decoder->setAudioPID(-1, -1);
			m_decoder->setSyncPCR(-1);
			m_decoder->setTextPID(-1);
			m_decoder->set();
			// Don't release m_decoder - FCC needs it for fccDecoderStop
		}

		// Start SoftDecoder if not already running
		if (!m_soft_decoder->isRunning())
		{
			eDebug("[eDVBServiceFCCPlay] Starting SoftDecoder for CSA-ALT");
			m_soft_decoder->start();
		}

		m_have_video_pid = (vpid > 0 && vpid < 0x2000);

		if (sendSeekableStateChanged)
			m_event((iPlayableService*)this, evSeekableStatusChanged);

		return;  // Skip normal HW decoder setup
	}

	// Normal HW decoder path (non-CSA-ALT or CSA-ALT not yet detected)
	if (m_decoder)
	{
		bool wasSeekable = m_decoder->getVideoProgressive() != -1;

		if (m_dvb_service)
		{
			achannel = m_dvb_service->getCacheEntry(eDVBService::cACHANNEL);
			ac3_delay = m_dvb_service->getCacheEntry(eDVBService::cAC3DELAY);
			pcm_delay = m_dvb_service->getCacheEntry(eDVBService::cPCMDELAY);
		}
		else // subservice
		{
			eServiceReferenceDVB ref;
			m_service_handler.getServiceReference(ref);
			eServiceReferenceDVB parent = ref.getParentServiceReference();
			if (!parent)
				parent = ref;
			if (parent)
			{
				ePtr<eDVBResourceManager> res_mgr;
				if (!eDVBResourceManager::getInstance(res_mgr))
				{
					ePtr<iDVBChannelList> db;
					if (!res_mgr->getChannelList(db))
					{
						ePtr<eDVBService> origService;
						if (!db->getService(parent, origService))
						{
		 					ac3_delay = origService->getCacheEntry(eDVBService::cAC3DELAY);
							pcm_delay = origService->getCacheEntry(eDVBService::cPCMDELAY);
						}
					}
				}
			}
		}

		setAC3Delay(ac3_delay == -1 ? 0 : ac3_delay);
		setPCMDelay(pcm_delay == -1 ? 0 : pcm_delay);

		m_decoder->setVideoPID(vpid, vpidtype);
		selectAudioStream();

		if (!(m_is_pvr || m_is_stream || m_timeshift_active))
			m_decoder->setSyncPCR(pcrpid);
		else
			m_decoder->setSyncPCR(-1);

		if (m_is_primary)
		{
			m_decoder->setTextPID(tpid);
			m_teletext_parser->start(program.textPid);
		}

		if (vpid > 0 && vpid < 0x2000)
			;
		else
		{
			std::string value;
			bool showRadioBackground = eSimpleConfig::getBool("config.misc.showradiopic", true);
			std::string radio_pic = eConfigManager::getConfigValue( showRadioBackground ? "config.misc.radiopic" : "config.misc.blackradiopic" );
			m_decoder->setRadioPic(radio_pic);
		}

		/* fcc stop and decoder start */
		if (!(m_fcc_flag & fcc_novideo))
		{
			if (m_fcc_flag & fcc_decoding)
				;
			else if(!m_decoder->fccDecoderStart())
				m_fcc_flag |= fcc_decoding;
		}

		if (m_fcc_mustplay)
		{
			m_fcc_mustplay = false;
			m_decoder->play();
		}
		else
		{
			m_decoder->set();
		}

		m_decoder->setAudioChannel(achannel);

		/* don't worry about non-existing services, nor pvr services */
		if (m_dvb_service)
		{
				/* (audio pid will be set in selectAudioTrack */
			m_dvb_service->setCacheEntry(eDVBService::cVPID, vpid);
			m_dvb_service->setCacheEntry(eDVBService::cVTYPE, vpidtype == eDVBVideo::MPEG2 ? -1 : vpidtype);
			m_dvb_service->setCacheEntry(eDVBService::cPCRPID, pcrpid);
			m_dvb_service->setCacheEntry(eDVBService::cTPID, tpid);
		}
		if (!sendSeekableStateChanged && (m_decoder->getVideoProgressive() != -1) != wasSeekable)
			sendSeekableStateChanged = true;
	}
	m_have_video_pid = (vpid > 0 && vpid < 0x2000);

	if (sendSeekableStateChanged)
		m_event((iPlayableService*)this, evSeekableStatusChanged);
}

void eDVBServiceFCCPlay::FCCDecoderStop()
{
	eDebug("[eDVBServiceFCCPlay] FCCDecoderStop [%s]", m_reference.toString().c_str());

	if (m_decoder)
	{
		m_teletext_parser = 0;
		m_new_subtitle_page_connection = 0;
		m_subtitle_parser = 0;
		m_new_dvb_subtitle_page_connection = 0;

		if (m_fcc_flag & fcc_ready)
		{
			m_decoder->fccDecoderStop();
			m_fcc_flag &=~fcc_decoding;
		}
		else if (m_fcc_flag & fcc_novideo)
		{
			m_video_event_connection = 0;
			m_decoder = 0;
		}
	}
}

void eDVBServiceFCCPlay::switchToLive()
{
	if (!m_timeshift_active)
		return;

	eDebug("[eDVBServiceFCCPlay] SwitchToLive");

	resetTimeshift(0);

	m_is_paused = m_skipmode = m_fastforward = m_slowmotion = 0; /* not supported in live mode */

	/* free the time shift service handler, we need the resources */
	m_service_handler_timeshift.free();

	m_fcc_flag &=~fcc_ready;
	m_fcc_flag &=~fcc_decoding;
	processNewProgramInfo(true);
}

bool eDVBServiceFCCPlay::checkUsbTuner()
{
	return (bool)getFrontendInfo(iFrontendInformation_ENUMS::isUsbTuner);
}

bool eDVBServiceFCCPlay::getFCCStateDecoding()
{
	eFCCServiceManager *fcc_service_mgr = eFCCServiceManager::getInstance();
	return fcc_service_mgr->isStateDecoding((iPlayableService*)this);
}

void eDVBServiceFCCPlay::setNormalDecoding()
{
	eFCCServiceManager *fcc_service_mgr = eFCCServiceManager::getInstance();
	return fcc_service_mgr->setNormalDecoding((iPlayableService*)this);
}

// ==================== SoftCSA Support for FCC ====================

void eDVBServiceFCCPlay::setupSpeculativeDescrambling()
{
	// Override base class to use FCC-specific callback (onFCCSessionActivated)
	// instead of base class callback (onSessionActivated)

	// Only for Live-TV, not for PVR, streams
	if (m_is_pvr || m_is_stream)
		return;

	eDebug("[eDVBServiceFCCPlay] Encrypted channel, creating CSA session for FCC");

	// Use base class members (m_csa_session, m_soft_decoder) for proper integration
	// Create session (starts INACTIVE, will activate when CSA-ALT detected from ECM)
	eServiceReferenceDVB ref = eServiceReferenceDVB(m_reference.toString());
	m_csa_session = new eDVBCSASession(ref);
	if (!m_csa_session->init())
	{
		eWarning("[eDVBServiceFCCPlay] Failed to initialize CSA session");
		m_csa_session = nullptr;
		return;
	}

	// Create SoftDecoder using base class member
	m_soft_decoder = new eDVBSoftDecoder(m_service_handler, m_dvb_service, m_decoder_index);
	m_soft_decoder->setSession(m_csa_session);

	// Connect to SoftDecoder's audio PID selection signal
	// Note: Use a lambda to call the protected base class method
	m_soft_decoder->m_audio_pid_selected.connect(
		[this](int pid) { this->onSoftDecoderAudioPidSelected(pid); });

	// Connect to session's activated signal - use FCC-specific callback!
	// This is the key difference from base class: we use onFCCSessionActivated
	// which handles FCC decoder stop/start properly
	m_csa_session->activated.connect(
		sigc::mem_fun(*this, &eDVBServiceFCCPlay::onFCCSessionActivated));

	eDebug("[eDVBServiceFCCPlay] CSA session created for FCC, waiting for ECM analysis");
}

void eDVBServiceFCCPlay::activateFCCCSASession()
{
	if (!m_csa_session)
		return;

	// Check if CSA-ALT was detected during prepare phase
	// isCsaAlt() returns true only if CSA-ALT was actually detected (not just analyzed)
	if (m_csa_session->isCsaAlt())
	{
		eDebug("[eDVBServiceFCCPlay] CSA-ALT was detected, activating session for decoding");

		// Force activate the session now that we're in decoding mode
		// CWs should start arriving now that CA handler is active
		m_csa_session->forceActivate();

		// SoftDecoder will be started in updateFCCDecoder() when it sees the active session
	}
	else if (m_csa_session->isEcmAnalyzed())
	{
		eDebug("[eDVBServiceFCCPlay] ECM analyzed but no CSA-ALT, using HW descrambling");
	}
	else
	{
		eDebug("[eDVBServiceFCCPlay] No ECM analyzed yet, using HW descrambling");
	}
}

void eDVBServiceFCCPlay::deactivateFCCCSASession()
{
	// Stop SoftDecoder when going back to prepare mode
	if (m_soft_decoder && m_soft_decoder->isRunning())
	{
		eDebug("[eDVBServiceFCCPlay] Stopping SoftDecoder for FCC prepare mode");
		m_soft_decoder->stop();
	}

	// Deactivate session but keep it around for next switch
	if (m_csa_session && m_csa_session->isActive())
	{
		eDebug("[eDVBServiceFCCPlay] Deactivating CSA session for FCC prepare mode");
		m_csa_session->forceDeactivate();
	}
}

void eDVBServiceFCCPlay::onFCCSessionActivated(bool active)
{
	eDebug("[eDVBServiceFCCPlay] Session activated callback: active=%d, fcc_mode=%d", active, m_fcc_mode);

	if (active && m_soft_decoder)
	{
		// CSA-ALT activated - handle decoder handover
		eDebug("[eDVBServiceFCCPlay] CSA-ALT activated, handling decoder handover");

		// Disconnect old video event connection
		m_video_event_connection = nullptr;

		// Release HW decoder resources if we're in decoding mode
		if (m_fcc_mode == fcc_mode_decoding && m_decoder)
		{
			eDebug("[eDVBServiceFCCPlay] Releasing HW decoder for SoftDecoder");

			// Stop FCC decoder first
			if (m_fcc_flag & fcc_decoding)
			{
				m_decoder->fccDecoderStop();
				m_fcc_flag &= ~fcc_decoding;
			}

			m_decoder->setVideoPID(-1, -1);
			m_decoder->setAudioPID(-1, -1);
			m_decoder->setSyncPCR(-1);
			m_decoder->setTextPID(-1);
			m_decoder->set();

			// Start SoftDecoder now
			if (!m_soft_decoder->isRunning())
			{
				eDebug("[eDVBServiceFCCPlay] Starting SoftDecoder (late activation)");
				m_soft_decoder->start();
			}
		}
	}
	else if (!active && m_soft_decoder && m_soft_decoder->isRunning())
	{
		// Session deactivated - stop SoftDecoder
		eDebug("[eDVBServiceFCCPlay] Session deactivated, stopping SoftDecoder");
		m_soft_decoder->stop();
	}
}

DEFINE_REF(eDVBServiceFCCPlay)
