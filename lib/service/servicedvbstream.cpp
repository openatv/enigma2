#include <lib/service/servicedvbstream.h>
#include <lib/base/eerror.h>
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
	m_tuned = 0;
	m_target_fd = -1;
}

void eDVBServiceStream::serviceEvent(int event)
{
	eDebug("STREAM service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("tuned..");
		m_tuned = 1;

			/* start feeding EIT updates */
		ePtr<iDVBDemux> m_demux;
		if (!m_service_handler.getDataDemux(m_demux))
		{
			eServiceReferenceDVB &ref = (eServiceReferenceDVB&) m_ref;
			int sid = ref.getParentServiceID().get();
			if (!sid)
				sid = ref.getServiceID().get();
			if ( ref.getParentTransportStreamID().get() &&
				ref.getParentTransportStreamID() != ref.getTransportStreamID() )
				m_event_handler.startOther(m_demux, sid);
			else
				m_event_handler.start(m_demux, sid);
		}

		if (m_state == stateRecording && m_want_record)
			doRecord();
		break;
	}
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("stream failed to tune");
		tuneFailed();
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		if (m_state == stateIdle)
			doPrepare();
		else if (m_want_record) /* doRecord can be called from Prepared and Recording state */
			doRecord();
		break;
	}
	case eDVBServicePMTHandler::eventMisconfiguration:
		tuneFailed();
		break;
	case eDVBServicePMTHandler::eventNoResources:
		tuneFailed();
		break;
	}
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
	eDebug("stop streaming");

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
		m_pids_active.clear();
		m_state = statePrepared;
		eDVBServicePMTHandler::serviceType servicetype = m_stream_ecm ? eDVBServicePMTHandler::scrambled_streamserver : eDVBServicePMTHandler::streamserver;
		bool descramble = eConfigManager::getConfigBoolValue("config.streaming.descramble", true);
		return m_service_handler.tune(m_ref, 0, 0, 0, NULL, servicetype, descramble);
	}
	return 0;
}

int eDVBServiceStream::doRecord()
{
	int err = doPrepare();
	if (err)
	{
		return err;
	}

	if (!m_tuned)
		return 0; /* try it again when we are tuned in */

	if (!m_record && m_tuned)
	{
		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux))
		{
			eDebug("eDVBServiceStream - NO DEMUX available");
			return -1;
		}
		demux->createTSRecorder(m_record, /*packetsize*/ 188, /*streaming*/ true);
		if (!m_record)
		{
			eDebug("eDVBServiceStream - no ts recorder available.");
			return -1;
		}
		m_record->setTargetFD(m_target_fd);
		m_record->connectEvent(slot(*this, &eDVBServiceStream::recordEvent), m_con_record_event);
	}

	eDebug("start streaming...");

	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
	{
		eDebug("getting program info failed.");
	}
	else
	{
		std::set<int> pids_to_record;

		pids_to_record.insert(0); // PAT

		if (program.pmtPid != -1)
			pids_to_record.insert(program.pmtPid); // PMT

		int timing_pid = -1, timing_stream_type = -1;
		iDVBTSRecorder::timing_pid_type timing_pid_type = iDVBTSRecorder::none;

		eDebugNoNewLine("STREAM: have %zd video stream(s)", program.videoStreams.size());
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
		eDebug(", and the text pid is %04x", program.textPid);
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

		/* include TDT pid, really low bandwidth, should not hurt anyone */
		pids_to_record.insert(0x14);

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
			eDebug("ADD PID: %04x", *i);
			m_record->addPID(*i);
		}

		for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
		{
			eDebug("REMOVED PID: %04x", *i);
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

	return 0;
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
		eDebug("unhandled record event %d", event);
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
