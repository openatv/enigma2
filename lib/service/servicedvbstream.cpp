#include <lib/service/servicedvbstream.h>
#include <lib/dvb/csasession.h>
#include <lib/base/eerror.h>
#include <lib/dvb/db.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/metaparser.h>
#include <lib/base/nconfig.h>
#include <fcntl.h>

DEFINE_REF(eDVBServiceStream);

eDVBServiceStream::eDVBServiceStream()
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceStream::serviceEvent);
	CONNECT(m_event_handler.m_eit_changed, eDVBServiceStream::gotNewEvent);
	m_state = stateIdle;
	m_want_record = 0;
	m_stream_ecm = false;
	m_stream_eit = false;
	m_stream_ait = false;
	m_stream_sdtbat = false;
	m_tuned = 0;
	m_target_fd = -1;
}

eDVBServiceStream::~eDVBServiceStream()
{
	eDebug("[eDVBServiceStream] Destructor called, state=%d", m_state);
	// Ensure clean shutdown of CSA session
	cleanupCSASession();
}

void eDVBServiceStream::cleanupCSASession()
{
	if (m_csa_session)
	{
		eDebug("[eDVBServiceStream] Cleaning up CSA session");
		m_csa_session->stopECMMonitor();
		// Detach descrambler and stop recorder BEFORE destroying session
		// This ensures the descrambling thread is not using the session anymore
		if (m_record)
		{
			m_record->setDescrambler(nullptr);
			m_record->stop();
		}
		// Now destroy session
		m_csa_session = nullptr;
		eDebug("[eDVBServiceStream] CSA session destroyed");
	}
}

void eDVBServiceStream::serviceEvent(int event)
{
	eDebug("[eDVBServiceStream] STREAM service event %d", event);
	if(event == eDVBServicePMTHandler::eventTuneFailed || event == eDVBServicePMTHandler::eventMisconfiguration || event == eDVBServicePMTHandler::eventNoResources)
		eventUpdate(event);

	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("[eDVBServiceStream] tuned.. m_state %d m_want_record %d", m_state, m_want_record);
		m_tuned = 1;

			/* start feeding EIT updates */
		ePtr<iDVBDemux> m_demux;
		if (!m_service_handler.getDataDemux(m_demux))
		{
			eServiceReferenceDVB &ref = (eServiceReferenceDVB&) m_ref;
			m_event_handler.start(m_demux, ref);
		}

		if (m_state > stateIdle && m_want_record)
			doRecord();
		break;
	}
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("[eDVBServiceStream] stream failed to tune");
		tuneFailed();
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		if (m_state == stateIdle)
			doPrepare();
		else if (m_want_record) /* doRecord can be called from Prepared and Recording state */
			doRecord();

		// Retry ECM monitor start if session exists but CSA-ALT not yet detected
		if (m_csa_session && !m_csa_session->isEcmAnalyzed())
		{
			eDVBServicePMTHandler::program program;
			if (m_service_handler.getProgramInfo(program) == 0)
			{
				for (const auto& ca : program.caids)
				{
					if (ca.capid > 0 && ca.capid < 0x1FFF)
					{
						ePtr<iDVBDemux> demux;
						if (m_service_handler.getDataDemux(demux) == 0 && demux)
						{
							m_csa_session->startECMMonitor(demux, ca.capid, ca.caid);
							eDebug("[eDVBServiceStream] ECM Monitor started on PID %d, CAID 0x%04X", ca.capid, ca.caid);
						}
						break;
					}
				}
			}
		}
		break;
	}
	case eDVBServicePMTHandler::eventMisconfiguration:
		tuneFailed();
		break;
	case eDVBServicePMTHandler::eventNoResources:
		tuneFailed();
		break;
	}
	if(event != eDVBServicePMTHandler::eventTuneFailed && event != eDVBServicePMTHandler::eventMisconfiguration && event != eDVBServicePMTHandler::eventNoResources)
		eventUpdate(event);
}

int eDVBServiceStream::start(const char *serviceref, int fd)
{
	if (m_state != stateIdle) return -1;

	m_ref = eServiceReferenceDVB(serviceref);
	if (doPrepare() < 0) return -1;
	m_target_fd = fd;
	m_want_record = 1;
	return doRecord();
}

RESULT eDVBServiceStream::stop()
{
	eDebug("[eDVBServiceStream] stop streaming m_state %d", m_state);

	// FIRST: Clean up CSA session BEFORE stopping recorder
	// This ensures descrambling thread stops using the session
	cleanupCSASession();

	if (m_state == stateRecording)
	{
		if (m_record)
			m_record->stop();

		m_state = statePrepared;
	}

	if (m_state == statePrepared)
	{
		m_record = 0;
		m_state = stateIdle;
	}

	eDebug("[eDVBServiceStream] stop complete");
	return 0;
}

int eDVBServiceStream::doPrepare()
{
	/* allocate a ts recorder if we don't already have one. */
	if (m_state == stateIdle)
	{
		m_stream_ecm = eConfigManager::getConfigBoolValue("config.streaming.stream_ecm");
		m_stream_eit = eConfigManager::getConfigBoolValue("config.streaming.stream_eit");
		m_stream_ait = eConfigManager::getConfigBoolValue("config.streaming.stream_ait");
		m_stream_sdtbat = eConfigManager::getConfigBoolValue("config.streaming.stream_sdtbat");
		m_pids_active.clear();
		m_state = statePrepared;
		bool descramble = eConfigManager::getConfigBoolValue("config.streaming.descramble", true);
		// Use scrambled_streamserver when descrambling is enabled (default)
		// This ensures CA descriptors are parsed for SoftCSA ECM analysis
		// When stream_ecm is true, ECM PIDs are also included in the stream
		eDVBServicePMTHandler::serviceType servicetype;
		if (descramble || m_stream_ecm)
			servicetype = eDVBServicePMTHandler::scrambled_streamserver;
		else
			servicetype = eDVBServicePMTHandler::streamserver;
		return m_service_handler.tune(m_ref, 0, 0, 0, NULL, servicetype, descramble);
	}
	return 0;
}

int eDVBServiceStream::doRecord()
{
	int err = doPrepare();
	if (err)
	{
		eDebug("[eDVBServiceStream] doPrerare err %d", err);
		return err;
	}

	if (!m_tuned)
	{
		eDebug("[eDVBServiceStream] try it again when we are tuned in");
		return 0; /* try it again when we are tuned in */
	}

	if (!m_record && m_tuned)
	{
		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux))
		{
			eDebug("[eDVBServiceStream] NO DEMUX available");
			return -1;
		}

		// Check if channel is encrypted - need scrambled recorder for software descrambling
		eDVBServicePMTHandler::program program;
		bool is_encrypted = false;
		if (!m_service_handler.getProgramInfo(program))
		{
			is_encrypted = program.isCrypted();
		}

		if (m_ref.path.empty())
		{
			// For encrypted channels, we need streaming=false to use eDVBRecordScrambledThread
			// which supports setDescrambler(). eDVBRecordStreamThread does NOT support descrambling!
			if (is_encrypted)
			{
				eDebug("[eDVBServiceStream] Encrypted channel - using ScrambledThread (async mode)");
				demux->createTSRecorder(m_record, /*packetsize*/ 188, /*streaming*/ false, /*sync_mode*/ false, /*is_streaming_output*/ true);
			}
			else
			{
				// FTA channel - can use streaming thread
				demux->createTSRecorder(m_record, /*packetsize*/ 188, /*streaming*/ true);
			}
		}
		else
			demux->createTSRecorder(m_record, /*packetsize*/ 188, /*streaming*/ false);
		if (!m_record)
		{
			eDebug("[eDVBServiceStream] no ts recorder available.");
			return -1;
		}
		m_record->setTargetFD(m_target_fd);
		m_record->connectEvent(sigc::mem_fun(*this, &eDVBServiceStream::recordEvent), m_con_record_event);

		// Attach speculative software descrambler for encrypted channels
		setupSpeculativeDescrambler();
	}

	// Try to attach descrambler if not yet done (PMT might not have been available earlier)
	if (m_record && !m_csa_session)
	{
		setupSpeculativeDescrambler();
	}

	eDebug("[eDVBServiceStream] start streaming...");

	if (recordCachedPids())
	{
		eDebug("[eDVBServiceStream] streaming pids from cache.");
		return 0;
	}

	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
	{
		eDebug("[eDVBServiceStream] getting program info failed.");
	}
	else if(m_record_no_pids == 0)
	{
		std::set<int> pids_to_record;

		eServiceReferenceDVB ref = m_ref.getParentServiceReference();
		ePtr<eDVBService> service;

		if (!ref.valid())
			ref = m_ref;

		if(!eDVBDB::getInstance()->getService(ref, service))
		{
			// cached pids
			for (int x = 0; x < eDVBService::cacheMax; ++x)
			{
				if (x == 5)
				{
					x += 3; // ignore cVTYPE, cACHANNEL, cAC3DELAY, cPCMDELAY
					continue;
				}
				int entry = service->getCacheEntry((eDVBService::cacheID)x);
				if (entry != -1)
				{
					if (eDVBService::cSUBTITLE == (eDVBService::cacheID)x)
					{
						entry = (entry&0xFFFF0000)>>16;
					}
					pids_to_record.insert(entry);
				}
			}
		}

		pids_to_record.insert(0); // PAT

		if (program.pmtPid != -1)
			pids_to_record.insert(program.pmtPid); // PMT

		int timing_pid = -1, timing_stream_type = -1;
		iDVBTSRecorder::timing_pid_type timing_pid_type = iDVBTSRecorder::none;

		eDebugNoNewLineStart("[eDVBServiceStream] have %zd video stream(s)", program.videoStreams.size());
		if (!program.videoStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
				i(program.videoStreams.begin());
				i != program.videoStreams.end(); ++i)
			{
				pids_to_record.insert(i->pid);

				if (timing_pid == -1)
				{
					timing_pid = i->pid;
					timing_stream_type = i->type;
					timing_pid_type = iDVBTSRecorder::video_pid;
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
				pids_to_record.insert(i->pid);

				if (timing_pid == -1)
				{
					timing_pid = i->pid;
					timing_stream_type = i->type;
					timing_pid_type = iDVBTSRecorder::audio_pid;
				}

				if (i != program.audioStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		if (!program.subtitleStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::subtitleStream>::const_iterator
				i(program.subtitleStreams.begin());
				i != program.subtitleStreams.end(); ++i)
			{
				pids_to_record.insert(i->pid);

				if (i != program.subtitleStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebugNoNewLine(", and the pcr pid is %04x", program.pcrPid);
		if (program.pcrPid >= 0 && program.pcrPid < 0x1fff)
			pids_to_record.insert(program.pcrPid);
		eDebugNoNewLine(", and the text pid is %04x", program.textPid);
		if (program.textPid != -1)
			pids_to_record.insert(program.textPid); // Videotext

		if (m_stream_ecm)
		{
			for (std::list<eDVBServicePMTHandler::program::capid_pair>::const_iterator i(program.caids.begin());
						i != program.caids.end(); ++i)
			{
				if (i->capid >= 0) pids_to_record.insert(i->capid);
			}
		}

		if (m_stream_ait)
		{
			if (program.aitPid >= 0) pids_to_record.insert(program.aitPid);
		}

		if (m_stream_eit)
		{
			pids_to_record.insert(0x12);
		}

		if (m_stream_sdtbat)
		{
			pids_to_record.insert(0x11);
		}

		/* include TDT pid, really low bandwidth, should not hurt anyone */
		pids_to_record.insert(0x14);

		recordPids(pids_to_record, timing_pid, timing_stream_type, timing_pid_type);
	}

	return 0;
}

bool eDVBServiceStream::recordCachedPids()
{
	eServiceReferenceDVB ref = m_ref.getParentServiceReference();
	ePtr<eDVBService> service;
	std::set<int> pids_to_record;

	if (!ref.valid())
		ref = m_ref;

	if (!eDVBDB::getInstance()->getService(ref, service) && !service->usePMT())
	{
		// cached pids
		for (int x = 0; x < eDVBService::cacheMax; ++x)
		{
			if (x == 5)
			{
				x += 3; // ignore cVTYPE, cACHANNEL, cAC3DELAY, cPCMDELAY
				continue;
			}
			int entry = service->getCacheEntry((eDVBService::cacheID)x);
			if (entry != -1)
			{
				if (eDVBService::cSUBTITLE == (eDVBService::cacheID)x)
				{
					entry = (entry&0xFFFF0000)>>16;
				}
				pids_to_record.insert(entry);
			}
		}
	}

	// check if cached pids found
	if (!pids_to_record.size())
	{
		eDebug("[eDVBServiceStream] no cached pids found");
		return false;
	}

	pids_to_record.insert(0); // PAT

	if (m_stream_eit)
	{
		pids_to_record.insert(0x12);
	}

	if (m_stream_sdtbat)
	{
		pids_to_record.insert(0x11);
	}

	/* include TDT pid, really low bandwidth, should not hurt anyone */
	pids_to_record.insert(0x14);

	recordPids(pids_to_record, -1, -1, iDVBTSRecorder::none);

	return true;
}

void eDVBServiceStream::recordPids(std::set<int> pids_to_record, int timing_pid,
	int timing_stream_type, iDVBTSRecorder::timing_pid_type timing_pid_type)
{
	/* find out which pids are NEW and which pids are obsolete.. */
	std::set<int> new_pids, obsolete_pids;

	std::set_difference(pids_to_record.begin(), pids_to_record.end(),
			m_pids_active.begin(), m_pids_active.end(),
			std::inserter(new_pids, new_pids.begin()));

	std::set_difference(
			m_pids_active.begin(), m_pids_active.end(),
			pids_to_record.begin(), pids_to_record.end(),
			std::inserter(obsolete_pids, obsolete_pids.begin())
			);

	for (std::set<int>::iterator i(new_pids.begin()); i != new_pids.end(); ++i)
	{
		eDebug("[eDVBServiceStream] ADD PID: %04x", *i);
		m_record->addPID(*i);
	}

	for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
	{
		eDebug("[eDVBServiceStream] REMOVED PID: %04x", *i);
		m_record->removePID(*i);
	}

	if (timing_pid != -1)
		m_record->setTimingPID(timing_pid, timing_pid_type, timing_stream_type);

	m_pids_active = pids_to_record;

	if (m_state != stateRecording)
	{
		m_record->start();
		m_state = stateRecording;
	}
}

void eDVBServiceStream::recordEvent(int event)
{
	switch (event)
	{
	case iDVBTSRecorder::eventWriteError:
		eWarning("[eDVBServiceStream] stream write error");
		streamStopped();
		break;
	default:
		eDebug("[eDVBServiceStream] unhandled record event %d", event);
		break;
	}
}

void eDVBServiceStream::gotNewEvent(int /*error*/)
{
	ePtr<eServiceEvent> event_now;
	m_event_handler.getEvent(event_now, 0);

	if (!event_now)
		return;

	/* TODO: inject EIT section into the stream */
}

RESULT eDVBServiceStream::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}

void eDVBServiceStream::setupSpeculativeDescrambler()
{
	// Check if channel is encrypted
	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
	{
		eDebug("[eDVBServiceStream] setupSpeculativeDescrambler: getProgramInfo failed");
		return;
	}

	if (!program.isCrypted())
	{
		eDebug("[eDVBServiceStream] FTA channel, no descrambler needed");
		return;
	}

	eDebug("[eDVBServiceStream] Encrypted channel, creating CSA session");

	// Create session (starts INACTIVE, activates when CSA-ALT detected from ECM)
	eServiceReferenceDVB ref(m_ref);
	m_csa_session = new eDVBCSASession(ref);
	if (!m_csa_session)
	{
		eDebug("[eDVBServiceStream] Failed to create eDVBCSASession");
		return;
	}

	// Initialize session (connects to eDVBCAHandler signals)
	if (!m_csa_session->init())
	{
		eDebug("[eDVBServiceStream] Failed to init CSA session");
		m_csa_session = nullptr;
		return;
	}

	// Attach session to our recorder
	if (m_record)
	{
		m_record->setDescrambler(static_cast<iServiceScrambled*>(m_csa_session.operator->()));
		eDebug("[eDVBServiceStream] CSA session attached to recorder");
	}

	// Start ECM Monitor for CSA-ALT detection
	// Find first valid ECM PID (capid > 0 and < 0x1FFF)
	for (const auto& ca : program.caids)
	{
		if (ca.capid > 0 && ca.capid < 0x1FFF)
		{
			ePtr<iDVBDemux> demux;
			if (m_service_handler.getDataDemux(demux) == 0 && demux)
			{
				m_csa_session->startECMMonitor(demux, ca.capid, ca.caid);
				eDebug("[eDVBServiceStream] ECM Monitor started on PID %d, CAID 0x%04X", ca.capid, ca.caid);
			}
			break;
		}
	}
}
