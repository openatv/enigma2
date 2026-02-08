#include <lib/service/servicedvbsoftdecoder.h>
#include <lib/service/servicedvb.h>
#include <lib/dvb/csasession.h>
#include <lib/dvb/demux.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>
#include <fcntl.h>

DEFINE_REF(eDVBSoftDecoder);

eDVBSoftDecoder::eDVBSoftDecoder(eDVBServicePMTHandler& source_handler,
                                 ePtr<eDVBService> dvb_service,
                                 int decoder_index)
	: m_source_handler(source_handler)
	, m_dvb_service(dvb_service)
	, m_decoder_index(decoder_index)
	, m_dvr_fd(-1)
	, m_running(false)
	, m_stopping(false)
	, m_decoder_started(false)
	, m_last_pts(0)
	, m_stall_count(0)
	, m_stream_stalled(false)
	, m_paused(false)
	, m_last_health_check(0)
{
	eDebug("[eDVBSoftDecoder] Created for decoder %d", decoder_index);
}

eDVBSoftDecoder::~eDVBSoftDecoder()
{
	// Stop timers
	if (m_start_timer)
		m_start_timer->stop();
	if (m_health_timer)
		m_health_timer->stop();
	if (m_first_cw_conn.connected())
		m_first_cw_conn.disconnect();

	stop();
	eDebug("[eDVBSoftDecoder] Destroyed");
}

void eDVBSoftDecoder::setSession(ePtr<eDVBCSASession> session)
{
	m_session = session;

	if (m_session)
	{
		// Listen for activation
		m_session->activated.connect(
			sigc::mem_fun(*this, &eDVBSoftDecoder::onSessionActivated));

		// If session is already active
		if (m_session->isActive())
		{
			onSessionActivated(true);
		}
	}
}

void eDVBSoftDecoder::onSessionActivated(bool active)
{
	eDebug("[eDVBSoftDecoder] Session activated: %d", active);

	// Note: Don't start here automatically!
	// eDVBServicePlay::onSessionActivated will call start() after stopping
	// the old hardware decoder to ensure correct ordering.
	if (!active && m_running)
	{
		eDebug("[eDVBSoftDecoder] Session deactivated - stopping decoder");
		stop();
	}
}

void eDVBSoftDecoder::onFirstCwReceived()
{
	if (m_decoder_started)
		return;  // Already started

	eDebug("[eDVBSoftDecoder] First CW received - starting decoder with DVR wait");

	// Stop timer
	if (m_start_timer)
		m_start_timer->stop();

	// Disconnect signal
	if (m_first_cw_conn.connected())
		m_first_cw_conn.disconnect();

	startDecoderWithDvrWait();
}

void eDVBSoftDecoder::onWaitForFirstDataTimeout()
{
	if (m_decoder_started)
		return;  // Already started

	eWarning("[eDVBSoftDecoder] CW timeout - starting decoder with DVR wait anyway");

	// Disconnect signal
	if (m_first_cw_conn.connected())
		m_first_cw_conn.disconnect();

	startDecoderWithDvrWait();
}

void eDVBSoftDecoder::startDecoderWithDvrWait()
{
	if (m_decoder_started)
		return;

	// Safety check: m_record must exist
	if (!m_record)
	{
		eWarning("[eDVBSoftDecoder] startDecoderWithDvrWait: m_record is NULL!");
		return;
	}

	// Wait for DVR data (blocking)
	int wait_timeout = eSimpleConfig::getInt("config.softcsa.waitForDataTimeout", 800);
	eDebug("[eDVBSoftDecoder] Waiting for DVR data (timeout=%dms)", wait_timeout);

	if (!m_record->waitForFirstData(wait_timeout))
	{
		eWarning("[eDVBSoftDecoder] DVR timeout - starting decoder anyway");
	}

	// Start decoder
	eDebug("[eDVBSoftDecoder] Starting decoder");
	updatePids(true);
	m_decoder_started = true;

	if (!m_health_timer)
	{
		m_health_timer = eTimer::create(eApp);
		CONNECT(m_health_timer->timeout, eDVBSoftDecoder::streamHealthCheck);
	}
	m_last_pts = 0;
	m_stall_count = 0;
	m_stream_stalled = false;
	m_paused = false;
	m_last_health_check = 0;
	m_health_timer->start(500, false);
}

int eDVBSoftDecoder::start()
{
	if (m_running)
		return 0;

	eDebug("[eDVBSoftDecoder] Starting");

	// Connect to source PMT handler for program info updates (e.g. new audio tracks)
	m_source_event_conn = m_source_handler.serviceEvent.connect(
		sigc::mem_fun(*this, &eDVBSoftDecoder::serviceEventSource));

	int ret = setupRecorder();
	if (ret < 0)
	{
		eWarning("[eDVBSoftDecoder] setupRecorder failed");
		m_source_event_conn.disconnect();
		return ret;
	}

	m_running = true;
	m_stopping = false;
	return 0;
}

void eDVBSoftDecoder::stop()
{
	if (!m_running)
		return;

	eDebug("[eDVBSoftDecoder] Stopping");
	m_stopping = true;

	// Stop timers and disconnect signals
	if (m_start_timer)
	{
		m_start_timer->stop();
		m_start_timer = nullptr;
	}
	if (m_health_timer)
	{
		m_health_timer->stop();
		m_health_timer = nullptr;
	}
	if (m_first_cw_conn.connected())
		m_first_cw_conn.disconnect();

	// Disconnect from source PMT handler events
	m_source_event_conn.disconnect();

	// IMPORTANT: Close DVR fd FIRST to unblock any poll() waiting on it
	// Closing the fd causes poll() to return with POLLHUP/POLLERR,
	// allowing the thread to exit cleanly.
	if (m_dvr_fd >= 0)
	{
		eDebug("[eDVBSoftDecoder] Closing DVR fd %d (before stopping thread)", m_dvr_fd);
		::close(m_dvr_fd);
		m_dvr_fd = -1;
	}

	// Stop the recorder thread FIRST - poll() should have been unblocked by closing DVR fd
	// Must stop before setDescrambler(nullptr) to prevent race condition
	if (m_record)
	{
		eDebug("[eDVBSoftDecoder] Stopping recorder thread");
		m_record->stop();
		m_record->setDescrambler(nullptr);
		m_record = nullptr;
	}

	// Release decode demux
	if (m_decode_demux)
	{
		eDebug("[eDVBSoftDecoder] Releasing decode demux");
		m_decode_demux = nullptr;
	}

	// Stop decoder - release video/audio devices
	if (m_decoder)
	{
		eDebug("[eDVBSoftDecoder] Stopping decoder");
		m_decoder->pause();
		m_decoder->setVideoPID(-1, -1);
		m_decoder->setAudioPID(-1, -1);
		m_decoder->set();  // Apply the changes to release devices
		m_decoder = nullptr;
	}

	// Free PVR handler last
	eDebug("[eDVBSoftDecoder] Freeing PVR handler");
	m_pvr_handler.free();

	m_pids_active.clear();
	m_running = false;
	m_decoder_started = false;
	m_last_pts = 0;
	m_stall_count = 0;
	m_stream_stalled = false;
	m_paused = false;
	m_last_health_check = 0;
	eDebug("[eDVBSoftDecoder] Stop complete");
}

int eDVBSoftDecoder::setupRecorder()
{
	eDebug("[eDVBSoftDecoder] setupRecorder");

	if (!m_record)
	{
		ePtr<iDVBDemux> demux;
		if (m_source_handler.getDataDemux(demux))
		{
			eDebug("[eDVBSoftDecoder] NO DEMUX available");
			return -1;
		}

		// Debug: Show data demux ID
		uint8_t data_demux_id = 0;
		demux->getCADemuxID(data_demux_id);
		eDebug("[eDVBSoftDecoder] Data demux ID: %d (reads from tuner)", data_demux_id);

		// Use streaming=false to get ScrambledThread (supports descrambling)
		// sync_mode is configurable via GUI:
		// 0 - "Automatic" (default): async with automatic fallback to sync on ENOSYS
		// 1 - "Synchronous": force sync (poll + write)
		int sync_mode_cfg = eSimpleConfig::getInt("config.softcsa.syncMode", 0);
		bool sync_mode = (sync_mode_cfg == 1);  // 1 = Synchronous forced
		eDebug("[eDVBSoftDecoder] Using %s mode (config=%d)", sync_mode ? "synchronous" : "automatic", sync_mode_cfg);
		demux->createTSRecorder(m_record, 188, false, sync_mode);
		if (!m_record)
		{
			eDebug("[eDVBSoftDecoder] no ts recorder available.");
			return -1;
		}

		// Allocate separate PVR channel for decode demux (critical!)
		// This ensures we have a different demux for PVR playback
		m_pvr_handler.allocatePVRChannel();
		eDebug("[eDVBSoftDecoder] PVR channel allocated");

		// Get decode demux from PVR handler (NOT from source_handler!)
		m_pvr_handler.getDecodeDemux(m_decode_demux);
		if (!m_decode_demux)
		{
			eWarning("[eDVBSoftDecoder] No decode demux from PVR handler - aborting!");
			m_record = nullptr;
			return -2;
		}

		// Get demux ID
		uint8_t demux_id = 0;
		m_decode_demux->getCADemuxID(demux_id);
		eDebug("[eDVBSoftDecoder] Decode demux ID: %d (from PVR handler)", demux_id);

		// Set demux source to PVR (critical for decoder to read from DVR)
		eDVBDemux *demux_raw = (eDVBDemux*)m_decode_demux.operator->();
		if (demux_raw)
		{
			demux_raw->setSourcePVR(demux_id);
			eDebug("[eDVBSoftDecoder] Set demux %d source to PVR (DVR%d)", demux_id, demux_id);
		}

		int fd = m_decode_demux->openDVR(O_WRONLY);
		if (fd >= 0)
		{
			m_dvr_fd = fd;  // Save for closing before thread stop
			m_record->setTargetFD(fd);
			eDebug("[eDVBSoftDecoder] DVR opened for writing (fd=%d)", fd);
		}
		else
		{
			eWarning("[eDVBSoftDecoder] Failed to open DVR for writing - aborting!");
			m_decode_demux = nullptr;
			m_record = nullptr;
			return -3;
		}

		m_record->enableAccessPoints(false);
		m_record->connectEvent(sigc::mem_fun(*this, &eDVBSoftDecoder::recordEvent), m_record_event_conn);
	}

	// Attach session as descrambler
	if (m_session)
	{
		eDebug("[eDVBSoftDecoder] Attaching session as descrambler (active=%d)", m_session->isActive());
		m_record->setDescrambler(ePtr<iServiceScrambled>(m_session.operator->()));
	}
	else
		eWarning("[eDVBSoftDecoder] No session attached!");


	updatePids(false);     // Add PIDs only, no decoder yet

	// Reset state
	m_decoder_started = false;

	// Check if CW is already available (e.g. fast channel switch)
	if (m_session && m_session->hasKeys())
	{
		eDebug("[eDVBSoftDecoder] First CW already available - starting decoder with DVR wait");
		m_record->start();
		startDecoderWithDvrWait();
		return 0;
	}

	// Connect to firstCwReceived signal
	if (m_session)
	{
		m_first_cw_conn = m_session->firstCwReceived.connect(
			sigc::mem_fun(*this, &eDVBSoftDecoder::onFirstCwReceived));
	}

	// Start timeout timer for CW
	int wait_timeout = eSimpleConfig::getInt("config.softcsa.waitForDataTimeout", 800);
	eDebug("[eDVBSoftDecoder] Waiting for first CW (timeout=%dms)", wait_timeout);

	m_start_timer = eTimer::create(eApp);
	CONNECT(m_start_timer->timeout, eDVBSoftDecoder::onWaitForFirstDataTimeout);
	m_start_timer->start(wait_timeout, true);  // single-shot

	// Start record thread
	m_record->start();

	return 0;
}

void eDVBSoftDecoder::recordEvent(int event)
{
	if (m_stopping)
		return;

	switch (event)
	{
	case iDVBTSRecorder::eventWriteError:
		eDebug("[eDVBSoftDecoder] TS write error");
		break;
	default:
		eDebug("[eDVBSoftDecoder] Unhandled record event %d", event);
		break;
	}
}

void eDVBSoftDecoder::streamHealthCheck()
{
	if (!m_decoder || !m_running || m_stopping || !m_decoder_started)
		return;

	// Don't check for stalls while paused - PTS naturally stops
	if (m_paused)
		return;

	// Detect MainLoop hangs: if this timer callback comes much later than
	// expected (>2s instead of 500ms), the MainLoop was blocked.
	// In that case, skip the stall check - the stream kept running fine
	// via eDVBCWHandler thread, only our monitoring was paused.
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	int64_t now = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
	if (m_last_health_check > 0)
	{
		int64_t elapsed = now - m_last_health_check;
		if (elapsed > 2000)
		{
			eDebug("[eDVBSoftDecoder] MainLoop was blocked for %lldms, skipping stall check", elapsed);
			m_stall_count = 0;
			m_stream_stalled = false;
			m_last_pts = 0;
			m_last_health_check = now;
			// Restart timer to discard all queued callbacks from the freeze
			m_health_timer->start(500, false);
			return;
		}
	}
	m_last_health_check = now;

	pts_t current_pts = 0;
	if (m_decoder->getPTS(0, current_pts) != 0)
		return;

	// During startup, PTS=0 is normal (waiting for CW/data)
	// Only monitor for stalls once stream has actually started (PTS > 0)
	if (current_pts == 0 && m_last_pts == 0)
		return;

	if (current_pts == m_last_pts)
	{
		m_stall_count++;
		if (m_stall_count == 3)
		{
			eWarning("[eDVBSoftDecoder] Stream stalled (PTS=%lld)", current_pts);
			m_stream_stalled = true;
		}
		else if (m_stall_count == 6)
		{
			eWarning("[eDVBSoftDecoder] Stream stalled too long - attempting recovery");
			m_decoder->pause();
			m_decoder->play();
			m_stall_count = 0;
			m_stream_stalled = false;
		}
	}
	else
	{
		if (m_stream_stalled)
			eDebug("[eDVBSoftDecoder] Stream recovered (PTS: %lld -> %lld)", m_last_pts, current_pts);
		m_stall_count = 0;
		m_stream_stalled = false;
	}

	m_last_pts = current_pts;
}

void eDVBSoftDecoder::serviceEventSource(int event)
{
	// Called when source PMT handler sends events
	switch (event)
	{
	case eDVBServicePMTHandler::eventNewProgramInfo:
		eDebug("[eDVBSoftDecoder] Source: eventNewProgramInfo");
		if (m_running)
			updatePids(true);  // Decoder already running, update it
		break;
	default:
		break;
	}
}

void eDVBSoftDecoder::updatePids(bool withDecoder)
{
	int timing_pid = -1;
	int timing_stream_type = -1;
	int vpid = -1, vpidtype = -1, pcrpid = -1, tpid = -1;

	eDVBServicePMTHandler::program program;
	if (m_source_handler.getProgramInfo(program))
	{
		eDebug("[eDVBSoftDecoder] getting program info failed.");
		return;
	}

	iDVBTSRecorder::timing_pid_type timing_pid_type = iDVBTSRecorder::none;
	std::set<int> pids_to_record;
	pids_to_record.insert(0); // PAT
	if (program.pmtPid != -1)
		pids_to_record.insert(program.pmtPid); // PMT

	eDebugNoNewLineStart("[eDVBSoftDecoder] have %zd video stream(s)", program.videoStreams.size());
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
				vpid = timing_pid = i->pid;
				vpidtype = timing_stream_type = i->type;
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
	pcrpid = program.pcrPid;
	eDebugNoNewLine(", and the text pid is %04x\n", program.textPid);
	if (program.textPid != -1)
		pids_to_record.insert(program.textPid); // Videotext
	tpid = program.textPid;

	if (program.aitPid >= 0) pids_to_record.insert(program.aitPid);

	// EIT
	pids_to_record.insert(0x12);

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
		m_record->addPID(*i);

	for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
		m_record->removePID(*i);

	m_pids_active = pids_to_record;

	if (timing_pid != -1)
		m_record->setTimingPID(timing_pid, timing_pid_type, timing_stream_type);

	if (withDecoder)
		updateDecoder(vpid, vpidtype, pcrpid);
}

void eDVBSoftDecoder::updateDecoder(int vpid, int vpidtype, int pcrpid)
{
	bool mustPlay = false;

	if (!m_decoder)
	{
		// Use PVR handler's decode demux (not source_handler!)
		m_pvr_handler.getDecodeDemux(m_decode_demux);
		if (!m_decode_demux)
		{
			eWarning("[eDVBSoftDecoder] updateDecoder: No decode demux available!");
			return;
		}

		uint8_t demux_id = 0;
		m_decode_demux->getCADemuxID(demux_id);
		eDebug("[eDVBSoftDecoder] Getting decoder from demux %d", demux_id);

		m_decode_demux->getMPEGDecoder(m_decoder, m_decoder_index);
		if (!m_decoder)
		{
			eWarning("[eDVBSoftDecoder] updateDecoder: getMPEGDecoder failed!");
			return;
		}

		eDebug("[eDVBSoftDecoder] Decoder created on demux %d", demux_id);
		// Connect to video events to forward them to parent
		m_decoder->connectVideoEvent(sigc::mem_fun(*this, &eDVBSoftDecoder::videoEvent), m_video_event_conn);
		mustPlay = true;
	}

	if (m_decoder)
	{
		eDebug("[eDVBSoftDecoder] Setting decoder: vpid=%04x vpidtype=%d pcrpid=%04x", vpid, vpidtype, pcrpid);
		m_decoder->setVideoPID(vpid, vpidtype);

		// Select audio stream - first check service cache, then fall back to language preferences
		eDVBServicePMTHandler::program program;
		if (!m_source_handler.getProgramInfo(program) && !program.audioStreams.empty())
		{
			int apid = -1;
			int atype = -1;
			unsigned int audio_index = 0;

			// First, try to get cached audio PID from service database
			// This preserves user's previous audio selection for this channel
			if (m_dvb_service)
			{
				for(int m = 0; m < eDVBService::nAudioCacheTags; m++)
				{
					int cached_apid = m_dvb_service->getCacheEntry(eDVBService::audioCacheTags[m]);
					if (cached_apid != -1)
					{
						// Find matching stream index for this cached PID
						for(unsigned int s = 0; s < program.audioStreams.size(); s++)
						{
							if (program.audioStreams[s].pid == cached_apid)
							{
								apid = cached_apid;
								atype = program.audioStreams[s].type;
								audio_index = s;
								eDebug("[eDVBSoftDecoder] Using cached audio: apid=%04x atype=%d (stream %u)", apid, atype, audio_index);
								break;
							}
						}
						if (apid != -1)
							break;
					}
				}
			}

			// If no cached audio, use language preferences (defaultAudioStream)
			if (apid == -1)
			{
				audio_index = program.defaultAudioStream;
				if (audio_index >= program.audioStreams.size())
					audio_index = 0;  // Fallback to first stream

				apid = program.audioStreams[audio_index].pid;
				atype = program.audioStreams[audio_index].type;
				eDebug("[eDVBSoftDecoder] Using default audio: apid=%04x atype=%d (stream %u of %zu)",
				       apid, atype, audio_index, program.audioStreams.size());
			}

			m_decoder->setAudioPID(apid, atype);

			// Notify parent about selected audio PID
			m_audio_pid_selected(apid);
		}

		// Using explicit pcrpid breaks video on some HiSilicon devices (e.g. sf8008) in PVR loopback mode
		m_decoder->setSyncPCR(-1);

		if (mustPlay)
		{
			m_decoder->play();
			eDebug("[eDVBSoftDecoder] Decoder PLAY with vpid=%04x vpidtype=%d", vpid, vpidtype);
		}
		else
		{
			m_decoder->set();
		}
	}
}

void eDVBSoftDecoder::videoEvent(struct iTSMPEGDecoder::videoEvent event)
{
	// Forward video events to parent
	m_video_event(event);
}

// ============================================================================
// Playback Control - Delegate to decoder
// ============================================================================

int eDVBSoftDecoder::play()
{
	m_paused = false;
	if (m_decoder)
		return m_decoder->play();
	return -1;
}

int eDVBSoftDecoder::pause()
{
	m_paused = true;
	if (m_decoder)
		return m_decoder->pause();
	return -1;
}

int eDVBSoftDecoder::setSlowMotion(int ratio)
{
	if (m_decoder)
		return m_decoder->setSlowMotion(ratio);
	return -1;
}

int eDVBSoftDecoder::setFastForward(int ratio)
{
	if (m_decoder)
		return m_decoder->setFastForward(ratio);
	return -1;
}

int eDVBSoftDecoder::setTrickmode()
{
	if (m_decoder)
		return m_decoder->setTrickmode();
	return -1;
}

// ============================================================================
// Audio Control - Delegate to decoder
// ============================================================================

int eDVBSoftDecoder::setAudioPID(int pid, int type)
{
	if (m_decoder)
		return m_decoder->setAudioPID(pid, type);
	return -1;
}

int eDVBSoftDecoder::selectAudioTrack(unsigned int i)
{
	// Get program info from source handler
	eDVBServicePMTHandler::program program;
	if (m_source_handler.getProgramInfo(program))
	{
		eDebug("[eDVBSoftDecoder] selectAudioTrack: getProgramInfo failed");
		return -1;
	}

	if (i >= program.audioStreams.size())
	{
		eDebug("[eDVBSoftDecoder] selectAudioTrack: invalid track %u (have %zu)",
		       i, program.audioStreams.size());
		return -2;
	}

	int pid = program.audioStreams[i].pid;
	int type = program.audioStreams[i].type;

	eDebug("[eDVBSoftDecoder] selectAudioTrack(%u): pid=%04x type=%d", i, pid, type);

	// Set audio PID on our decoder
	int ret = setAudioPID(pid, type);

	// Apply changes
	if (m_decoder)
		m_decoder->set();

	return ret;
}

int eDVBSoftDecoder::getAudioChannel()
{
	if (m_decoder)
		return m_decoder->getAudioChannel();
	return -1;
}

void eDVBSoftDecoder::setAudioChannel(int channel)
{
	if (m_decoder)
		m_decoder->setAudioChannel(channel);
}

int eDVBSoftDecoder::getAC3Delay()
{
	if (m_decoder)
		return m_decoder->getAC3Delay();
	return 0;
}

int eDVBSoftDecoder::getPCMDelay()
{
	if (m_decoder)
		return m_decoder->getPCMDelay();
	return 0;
}

void eDVBSoftDecoder::setAC3Delay(int delay)
{
	if (m_decoder)
		m_decoder->setAC3Delay(delay);
}

void eDVBSoftDecoder::setPCMDelay(int delay)
{
	if (m_decoder)
		m_decoder->setPCMDelay(delay);
}

// ============================================================================
// Video Info - Delegate to decoder
// ============================================================================

int eDVBSoftDecoder::getVideoHeight()
{
	if (m_decoder)
		return m_decoder->getVideoHeight();
	return -1;
}

int eDVBSoftDecoder::getVideoWidth()
{
	if (m_decoder)
		return m_decoder->getVideoWidth();
	return -1;
}

int eDVBSoftDecoder::getVideoFrameRate()
{
	if (m_decoder)
		return m_decoder->getVideoFrameRate();
	return -1;
}

int eDVBSoftDecoder::getVideoProgressive()
{
	if (m_decoder)
		return m_decoder->getVideoProgressive();
	return -1;
}

int eDVBSoftDecoder::getVideoAspect()
{
	if (m_decoder)
		return m_decoder->getVideoAspect();
	return -1;
}

int eDVBSoftDecoder::getVideoGamma()
{
	if (m_decoder)
		return m_decoder->getVideoGamma();
	return -1;
}

int eDVBSoftDecoder::getPTS(int what, pts_t& pts)
{
	if (m_decoder)
		return m_decoder->getPTS(what, pts);
	return -1;
}

RESULT eDVBSoftDecoder::connectVideoEvent(
	const sigc::slot<void(struct iTSMPEGDecoder::videoEvent)>& slot,
	ePtr<eConnection>& conn)
{
	conn = new eConnection(this, m_video_event.connect(slot));
	return 0;
}
