#include <lib/service/servicedvbrecord.h>
#include <lib/dvb/csasession.h>
#include <lib/dvb/cahandler.h>
#include <lib/base/eerror.h>
#include <lib/dvb/db.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/metaparser.h>
#include <lib/base/nconfig.h>
#include <lib/base/httpstream.h>
#include <fcntl.h>

	/* for cutlist */
#include <byteswap.h>
#include <netinet/in.h>

DEFINE_REF(eDVBServiceRecord);

eDVBServiceRecord::eDVBServiceRecord(const eServiceReferenceDVB &ref, bool isstreamclient): m_ref(ref)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceRecord::serviceEvent);
	CONNECT(m_event_handler.m_eit_changed, eDVBServiceRecord::gotNewEvent);
	m_state = stateIdle;
	m_want_record = 0;
	m_record_ecm = false;
	m_packet_size = 188;
	m_descramble = true;
	m_pvr_descramble = false;
	m_is_stream_client = isstreamclient;
	m_is_pvr = !m_ref.path.empty() && !m_is_stream_client;
	m_tuned = 0;
	m_target_fd = -1;
	m_error = 0;
	m_streaming = 0;
	m_simulate = false;
	m_last_event_id = -1;
	m_serviceType = eDVBServicePMTHandler::recording;

	// Software descrambling initialization
	m_use_software_descramble = false;
}

eDVBServiceRecord::~eDVBServiceRecord()
{
	// Ensure clean shutdown
	stop();
}

void eDVBServiceRecord::serviceEvent(int event)
{
	eDebug("[eDVBServiceRecord] RECORD service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("[eDVBServiceRecord] tuned..");
		m_tuned = 1;

			/* start feeding EIT updates */
		ePtr<iDVBDemux> m_demux;
		if (!m_service_handler.getDataDemux(m_demux))
		{
			eServiceReferenceDVB &ref = (eServiceReferenceDVB&) m_ref;
			m_event_handler.start(m_demux, ref);
		}

		if (m_state == stateRecording && m_want_record)
			doRecord();
		m_event((iRecordableService*)this, evTunedIn);
		break;
	}
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("[eDVBServiceRecord] record failed to tune");
		m_event((iRecordableService*)this, evTuneFailed);
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		// eDebug("[eDVBServiceRecord] eventNewProgramInfo m_state=%d / m_want_record=%d / m_pvr_descramble=%d", m_state, m_want_record, m_pvr_descramble);
		if (m_state == stateIdle)
			doPrepare();
		else if (m_want_record) /* doRecord can be called from Prepared and Recording state */
		{
			if (m_pvr_descramble)
				updateDecoder();
			else
				doRecord();
		}
		m_event((iRecordableService*)this, evNewProgramInfo);
		break;
	}
	case eDVBServicePMTHandler::eventMisconfiguration:
		m_error = errMisconfiguration;
		m_event((iRecordableService*)this, evTuneFailed);
		break;
	case eDVBServicePMTHandler::eventNoResources:
		m_error = errNoResources;
		m_event((iRecordableService*)this, evTuneFailed);
		break;
	case eDVBServicePMTHandler::eventEOF:
		m_event((iRecordableService*)this, evPvrEof);
		break;
	case eDVBServicePMTHandler::eventStopped:
		/* recording data source has stopped, stop recording */
		stop();
		m_event((iRecordableService*)this, evRecordAborted);
		break;
	case eDVBServicePMTHandler::eventStartPvrDescramble:
		if (m_want_record)
		{
			doRecord();
		}
		break;
	}
}

RESULT eDVBServiceRecord::prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm, int packetsize)
{
	bool config_recording_always_ecm = eConfigManager::getConfigBoolValue("config.recording.always_ecm", false);
	bool config_recording_never_decrypt = eConfigManager::getConfigBoolValue("config.recording.never_decrypt", false);

	m_filename = filename;
	m_streaming = 0;
	m_descramble = config_recording_never_decrypt ? false : descramble;
	bool write_descramble = m_descramble; // remember descramble flag to fix icam recordings
	m_record_ecm = config_recording_always_ecm ? true : recordecm;

	// force descramble for _pvrdesc.ts
	if (strstr(filename, "_pvrdesc.ts"))
	{
		m_pvr_descramble = true;
		m_descramble = true;
		m_record_ecm = false;
		write_descramble = true;
	}
	m_packet_size = packetsize;

	eTrace("[eDVBServiceRecord] prepare filename %s / m_record_ecm = %d / m_descramble = %d / m_pvr_descramble = %d", filename, m_record_ecm, m_descramble, m_pvr_descramble);

	if (m_state == stateIdle)
	{
		int ret = doPrepare();
		if (!ret)
		{
			eServiceReferenceDVB ref = m_ref.getParentServiceReference();
			ePtr<eDVBService> service;
			eDVBMetaParser meta;
			std::string service_data;

			if (!ref.valid())
				ref = m_ref;

			if (!eDVBDB::getInstance()->getService(ref, service))
			{
				char tmp[255];
				sprintf(tmp, "f:%x", service->m_flags);
				service_data += tmp;
				// cached pids
				for (int x=0; x < eDVBService::cacheMax; ++x)
				{
					int entry = service->getCacheEntry((eDVBService::cacheID)x);
					if (entry != -1)
					{
						sprintf(tmp, ",c:%02d%04x", x, entry);
						service_data += tmp;
					}
				}
			}

			meta.m_time_create = begTime;
			meta.m_ref = m_ref;
			meta.m_data_ok = 1;
			meta.m_service_data = service_data;
			if (name)
				meta.m_name = name;
			if (descr)
				meta.m_description = descr;
			if (tags)
				meta.m_tags = tags;
			meta.m_scrambled = !write_descramble;
			meta.m_packet_size = m_packet_size;
			ret = meta.updateMeta(filename) ? -255 : 0;
			if (!ret)
			{
				std::string fname = filename;
				fname.erase(fname.length()-2, 2);
				fname += "eit";
				eEPGCache::getInstance()->saveEventToFile(fname.c_str(), ref, eit_event_id, begTime, endTime);
			}
		}
		return ret;
	}
	return -1;
}

RESULT eDVBServiceRecord::prepareStreaming(bool descramble, bool includeecm)
{
	m_filename = "";
	m_streaming = 1;
	m_descramble = descramble;
	m_record_ecm = includeecm;
	if (m_state == stateIdle)
		return doPrepare();
	return -1;
}

RESULT eDVBServiceRecord::start(bool simulate)
{
	m_simulate = simulate;
	m_want_record = 1;
		/* when tune wasn't yet successfully, doRecord stays in "prepared"-state which is fine. */
	m_event((iRecordableService*)this, evStart);
	return doRecord();
}

RESULT eDVBServiceRecord::stop()
{
	if (!m_simulate)
		eDebug("[eDVBServiceRecord] stop recording!");

	// Stop the recorder thread FIRST to prevent race condition:
	// The thread accesses m_serviceDescrambler without synchronization,
	// so we must ensure it's not running before we release the CSA session.
	if (m_state == stateRecording && m_record)
	{
		m_record->stop();
	}

	// Now safe to remove descrambler and release session
	if (m_csa_session && m_record)
	{
		eDebug("[eDVBServiceRecord] Removing CSA session from recorder");
		m_record->setDescrambler(nullptr);
	}

	// Free CSA session if used
	if (m_csa_session)
	{
		eDebug("[eDVBServiceRecord] Releasing CSA session");
		m_csa_session = nullptr;
		m_use_software_descramble = false;
	}

	// Recording already stopped above
	if (m_state == stateRecording)
	{
		if (m_target_fd >= 0)
		{
			::close(m_target_fd);
			m_target_fd = -1;
		}

		saveCutlist();

		m_state = statePrepared;
	} else if (!m_simulate)
		eDebug("[eDVBServiceRecord] (was not recording)");
	if (m_state == statePrepared)
	{
		m_record = 0;
		m_state = stateIdle;
	}
	m_event((iRecordableService*)this, evRecordStopped);
	return 0;
}

int eDVBServiceRecord::doPrepare()
{
	/* allocate a ts recorder if we don't already have one. */
	eTrace("[eDVBServiceRecord] doPrepare m_ref %s", m_ref.toString().c_str());

	if (m_state == stateIdle)
	{

		if(tryFallbackTuner(/*REF*/m_ref, /*REF*/m_is_stream_client, m_is_pvr, m_simulate))
			eDebug("[eDVBServiceRecord] fallback tuner selected");

		if (m_streaming)
		{
			m_serviceType = m_record_ecm ? eDVBServicePMTHandler::scrambled_streamserver : eDVBServicePMTHandler::streamserver;
		}
		else
		{
			m_serviceType = m_record_ecm ? eDVBServicePMTHandler::scrambled_recording : eDVBServicePMTHandler::recording;
		}
		m_pids_active.clear();
		m_state = statePrepared;
		ePtr<iTsSource> source;
		/*
		 * NOTE: we do not have to create a source for simulated recordings,
		 * we will not get to the point where the source is going to be used
		 */
		if (!m_simulate && !m_ref.path.empty())
		{
			if (m_is_stream_client)
			{
				/*
				* streams are considered to be descrambled by default;
				* user can indicate a stream is scrambled, by using servicetype id + 0x100
				* (or idDVB + idServiceIsScrambled == idDVBScrambled)
				*/
				bool config_descramble_client = eConfigManager::getConfigBoolValue("config.streaming.descramble_client", false);

				m_descramble = (m_ref.type == eServiceReference::idDVBScrambled);

				if(config_descramble_client)
					m_descramble = true;

				m_record_ecm = false;
				m_serviceType = eDVBServicePMTHandler::streamclient;
				eHttpStream *f = new eHttpStream();
				f->open(m_ref.path.c_str());
				source = ePtr<iTsSource>(f);
			}
			else
			{
				/* re-record a recording */
				int packetsize = 188;
				eDVBMetaParser meta;
				if (!meta.parseFile(m_ref.path))
				{
					std::string path = m_ref.path;
					m_ref = meta.m_ref;
					m_ref.path = path;
					packetsize = meta.m_packet_size;
					m_descramble = meta.m_scrambled;
				}
				if(m_pvr_descramble)
				{
					m_serviceType = eDVBServicePMTHandler::pvrDescramble;
				}
				else
				{
					m_serviceType = eDVBServicePMTHandler::offline;
				}
				eRawFile *f = new eRawFile(packetsize);
				f->open(m_ref.path.c_str());
				source = ePtr<iTsSource>(f);
			}
			m_event((iRecordableService*)this, evPvrTuneStart);
		}
		else
		{
			m_event((iRecordableService*)this, evTuneStart);
		}

		eTrace("[eDVBServiceRecord] doPrepare m_ref:%s / m_simulate:%d / m_serviceType:%d / m_is_stream_client:%d / m_descramble:%d / m_pvr_descramble:%d", m_ref.path.c_str(), m_simulate, m_serviceType, m_is_stream_client, m_descramble, m_pvr_descramble);

		return m_service_handler.tuneExt(m_ref, source, m_ref.path.c_str(), 0, m_simulate, NULL, m_serviceType, m_descramble);
	}
	return 0;
}

// Called to setup software descrambling for recording
int eDVBServiceRecord::setupSoftwareDescrambler(eDVBServicePMTHandler::program& program)
{
	eDebug("[eDVBServiceRecord] Setting up CSA session for recording");

	// Create session for recording (no decoder needed)
	eServiceReferenceDVB ref(m_ref);
	m_csa_session = new eDVBCSASession(ref);
	if (!m_csa_session)
	{
		eWarning("[eDVBServiceRecord] Failed to create CSA session");
		return -1;
	}

	// Initialize session - connects to CAHandler for CW reception
	if (!m_csa_session->init())
	{
		eWarning("[eDVBServiceRecord] Failed to initialize CSA session");
		m_csa_session = nullptr;
		return -2;
	}

	// Start ECM monitor for CSA-ALT detection and ecm_mode extraction
	// This is needed for timer recordings where no Live-TV is running
	if (!program.caids.empty())
	{
		uint16_t ecm_pid = program.caids.front().capid;
		uint16_t caid = program.caids.front().caid;
		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux) == 0 && demux)
		{
			eDebug("[eDVBServiceRecord] Starting ECM monitor on PID %d, CAID 0x%04X", ecm_pid, caid);
			m_csa_session->startECMMonitor(demux, ecm_pid, caid);
		}
	}

	// Activate session immediately - recording can't wait for ECM analysis
	// If cache has CSA-ALT info, ecm_mode will be used from cache
	// Otherwise default ecm_mode is used until first ECM arrives
	m_csa_session->forceActivate();

	eDebug("[eDVBServiceRecord] CSA session activated for recording");

	// No startup buffering for recording (data goes directly to file)

	m_use_software_descramble = true;
	return 0;
}

int eDVBServiceRecord::doRecord()
{
	int err = doPrepare();
	if (err)
	{
		m_error = errTuneFailed;
		m_event((iRecordableService*)this, evRecordFailed);
		return err;
	}

	if (!m_tuned)
		return 0; /* try it again when we are tuned in */

	if (!m_record && m_tuned && !m_streaming && !m_simulate)
	{
		if (m_pvr_descramble)
		{
			if (m_service_handler.isPmtReady())
			{
				if (!m_service_handler.isCiConnected())
				{
					m_event((iRecordableService*)this, evRecordFailed);
					return errNoCiConnected;
				}
			}
			else
			{
				return 0;
			}
		}
		eDebug("[eDVBServiceRecord] Recording to %s...", m_filename.c_str());
		::remove(m_filename.c_str());
		int fd = ::open(m_filename.c_str(), O_WRONLY | O_CREAT | O_LARGEFILE | O_CLOEXEC, 0666);
		if (fd == -1)
		{
			eDebug("[eDVBServiceRecord] can't open recording file: %m");
			m_error = errOpenRecordFile;
			m_event((iRecordableService*)this, evRecordFailed);
			return errOpenRecordFile;
		}

		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux))
		{
			eDebug("[eDVBServiceRecord] NO DEMUX available!");
			m_error = errNoDemuxAvailable;
			m_event((iRecordableService*)this, evRecordFailed);
			::close(fd);
			return errNoDemuxAvailable;
		}
		demux->createTSRecorder(m_record, m_packet_size, false);
		if (!m_record)
		{
			eDebug("[eDVBServiceRecord] no ts recorder available.");
			m_error = errNoTsRecorderAvailable;
			m_event((iRecordableService*)this, evRecordFailed);
			::close(fd);
			return errNoTsRecorderAvailable;
		}
		m_record->setTargetFD(fd);
		m_record->setTargetFilename(m_filename);
		m_record->connectEvent(sigc::mem_fun(*this, &eDVBServiceRecord::recordEvent), m_con_record_event);

		m_target_fd = fd;
	}

	if (m_streaming)
	{
		m_state = stateRecording;
		eDebug("[eDVBServiceRecord] start streaming...");
	} else
	{
		eDebug("[eDVBServiceRecord] start recording...");

		eDVBServicePMTHandler::program program;
		if (m_service_handler.getProgramInfo(program))
			eDebug("[eDVBServiceRecord] getting program info failed.");
		else
		{
			// Check if channel needs software descrambling
			bool is_encrypted = program.isCrypted();
			if (is_encrypted && !m_use_software_descramble)
			{
				eDebug("[eDVBServiceRecord] Channel is encrypted, setting up software descrambler");
				setupSoftwareDescrambler(program);

				// Always attach descrambler immediately
				// - For algo=3 channels: will descramble when keys arrive
				// - For CI channels: PASSTHROUGH mode, but TSC bits get cleared
				if (m_csa_session)
				{
					eDebug("[eDVBServiceRecord] Attaching CSA session to recorder");
					m_record->setDescrambler(static_cast<iServiceScrambled*>(m_csa_session.operator->()));
				}
			}

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

			eDebugNoNewLineStart("[eDVBServiceRecord] RECORD: have %zd video stream(s)", program.videoStreams.size());
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

					if (i->rdsPid != -1)
					{
						pids_to_record.insert(i->rdsPid);
						eDebugNoNewLine(", (RDS %04x)", i->rdsPid);
					}
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
			eDebugNoNewLine(", and the text pid is %04x\n", program.textPid);
			if (program.textPid != -1)
				pids_to_record.insert(program.textPid); // Videotext

			if (m_record_ecm)
			{
				for (std::list<eDVBServicePMTHandler::program::capid_pair>::const_iterator i(program.caids.begin());
							i != program.caids.end(); ++i)
				{
					if (i->capid >= 0) pids_to_record.insert(i->capid);
				}
				pids_to_record.insert(EventInformationSection::PID);
				pids_to_record.insert(TimeAndDateSection::PID);
			}

			bool include_ait = eConfigManager::getConfigBoolValue("config.recording.include_ait");
			if (include_ait)
			{
				/* add AIT pid (if any) */
				if (program.aitPid >= 0) pids_to_record.insert(program.aitPid);
			}

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
				eDebug("[eDVBServiceRecord] ADD PID: %04x", *i);
				m_record->addPID(*i);
			}

			for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
			{
				eDebug("[eDVBServiceRecord] REMOVED PID: %04x", *i);
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
	}
	m_error = 0;
	m_event((iRecordableService*)this, evRecordRunning);
	return 0;
}

void eDVBServiceRecord::updateDecoder()
{
	int vpid = -1, vpidtype = -1, apid = -1, apidtype = -1;

	eDVBServicePMTHandler &h = m_service_handler;

	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
		eDebug("getting program info failed.");
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

		apid = program.audioStreams[program.defaultAudioStream].pid;
		apidtype = program.audioStreams[program.defaultAudioStream].type;

		eDebugNoNewLine(", and the pcr pid is %04x\n", program.pcrPid);
	}

	if (!m_decoder)
	{
		h.getDecodeDemux(m_decode_demux);
		if (m_decode_demux)
		{
			m_decode_demux->getMPEGDecoder(m_decoder, 0);
		}
	}

	if (m_decoder)
	{
		m_decoder->setVideoPID(vpid, vpidtype);
		m_decoder->setAudioPID(apid, apidtype);
		m_decoder->setSyncPCR(-1);
		m_decoder->play();
	}
}

RESULT eDVBServiceRecord::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServiceRecord::connectEvent(const sigc::slot<void(iRecordableService*,int)> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iRecordableService*)this, m_event.connect(event));
	return 0;
}

RESULT eDVBServiceRecord::stream(ePtr<iStreamableService> &ptr)
{
	ptr = this;
	return 0;
}

ePtr<iStreamData> eDVBServiceRecord::getStreamingData()
{
	ePtr<iStreamData> retval;
	eDVBServicePMTHandler::program program;
	if (m_tuned && !m_service_handler.getProgramInfo(program))
	{
		retval = new eDVBServicePMTHandler::eStreamData(program);
	}

	return retval;
}

void eDVBServiceRecord::recordEvent(int event)
{
	switch (event)
	{
	case iDVBTSRecorder::eventWriteError:
		eWarning("[eDVBServiceRecord] record write error");
		stop();
		m_event((iRecordableService*)this, evRecordWriteError);
		return;
	default:
		eDebug("[eDVBServiceRecord] unhandled record event %d", event);
	}
}

void eDVBServiceRecord::gotNewEvent(int /*error*/)
{
	ePtr<eServiceEvent> event_now;
	m_event_handler.getEvent(event_now, 0);

	if (!event_now)
		return;

	int event_id = event_now->getEventId();

	pts_t p;

	if (m_record)
	{
		if (m_record->getCurrentPCR(p))
			eDebug("[eDVBServiceRecord] getting PCR failed!");
		else
		{
			m_event_timestamps[event_id] = p;
			eDebug("[eDVBServiceRecord] pcr of eit change: %llx", p);
		}
	}

	if (event_id != m_last_event_id)
		eDebug("[eDVBServiceRecord] now running: %s (%d seconds)", event_now->getEventName().c_str(), event_now->getDuration());

	m_last_event_id = event_id;

	m_event((iRecordableService*)this, evNewEventInfo);
}

void eDVBServiceRecord::saveCutlist()
{
	/* XXX: dupe of eDVBServicePlay::saveCuesheet, refactor plz */

	/* save cuesheet only when main file is accessible. */
	if (::access(m_filename.c_str(), R_OK) < 0)
		return;

	std::string filename = m_filename + ".cuts";

	eDVBTSTools tstools;

	if (tstools.openFile(m_filename.c_str()))
	{
		eDebug("[eDVBServiceRecord] saving cutlist failed because tstools failed");
		return;
	}

	// If a cuts file exists, append to it (who cares about sorting it)
	FILE *f = fopen(filename.c_str(), "a+b");
	if (f)
	{
		unsigned long long where;
		int what;

		for (std::map<int,pts_t>::iterator i(m_event_timestamps.begin()); i != m_event_timestamps.end(); ++i)
		{
			pts_t p = i->second;
			off_t offset = 0; // fixme, we need to note down both
			if (tstools.fixupPTS(offset, p))
			{
				eDebug("[eDVBServiceRecord] fixing up PTS failed, not saving");
				continue;
			}
			eDebug("[eDVBServiceRecord] fixed up %llx to %llx (offset %jx)", i->second, p, (intmax_t)offset);
			where = htobe64(p);
			what = htonl(2); /* mark */
			fwrite(&where, sizeof(where), 1, f);
			fwrite(&what, sizeof(what), 1, f);
		}
		fclose(f);
	}

}

RESULT eDVBServiceRecord::subServices(ePtr<iSubserviceList> &ptr)
{
	ptr = this;
	return 0;
}

int eDVBServiceRecord::getNumberOfSubservices()
{
	ePtr<eServiceEvent> evt;
	if (!m_event_handler.getEvent(evt, 0))
		return evt->getNumOfLinkageServices();
	return 0;
}

RESULT eDVBServiceRecord::getSubservice(eServiceReference &sub, unsigned int n)
{
	ePtr<eServiceEvent> evt;
	if (!m_event_handler.getEvent(evt, 0))
	{
		if (!evt->getLinkageService(sub, m_ref, n))
			return 0;
	}
	sub.type=eServiceReference::idInvalid;
	return -1;
}
