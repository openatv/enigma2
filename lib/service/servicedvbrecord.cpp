#include <lib/service/servicedvbrecord.h>
#include <lib/base/eerror.h>
#include <lib/dvb/epgcache.h>

#include <fcntl.h>

DEFINE_REF(eDVBServiceRecord);

eDVBServiceRecord::eDVBServiceRecord(const eServiceReferenceDVB &ref): m_ref(ref)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceRecord::serviceEvent);
	m_state = stateIdle;
	m_want_record = 0;
	m_tuned = 0;
	m_target_fd = -1;
}

void eDVBServiceRecord::serviceEvent(int event)
{
	eDebug("RECORD service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("tuned..");
		m_tuned = 1;
		if (m_state == stateRecording && m_want_record)
			doRecord();
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
	}
}

RESULT eDVBServiceRecord::prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id)
{
	m_filename = filename;
	if (m_state == stateIdle)
	{
		int ret = doPrepare();
		if (!ret)
		{
			eEPGCache::getInstance()->Lock();
			const eit_event_struct *event = 0;
			eServiceReferenceDVB ref = m_ref.getParentServiceReference();
			if (!ref.valid())
				ref = m_ref;
			if ( eit_event_id != -1 )
			{
				eDebug("query epg event id %d", eit_event_id);
				eEPGCache::getInstance()->lookupEventId(ref, eit_event_id, event);
			}
			if ( !event && (begTime != -1 && endTime != -1) )
			{
				time_t queryTime = begTime + ((endTime-begTime)/2);
				tm beg, end, query;
				localtime_r(&begTime, &beg);
				localtime_r(&endTime, &end);
				localtime_r(&queryTime, &query);
				eDebug("query stime %d:%d:%d, etime %d:%d:%d, qtime %d:%d:%d",
					beg.tm_hour, beg.tm_min, beg.tm_sec,
					end.tm_hour, end.tm_min, end.tm_sec,
					query.tm_hour, query.tm_min, query.tm_sec);
				eEPGCache::getInstance()->lookupEventTime(ref, queryTime, event);
			}
			if ( event )
			{
				eDebug("found event.. store to disc");
				std::string fname = filename;
				fname.erase(fname.length()-2, 2);
				fname+="eit";
				int fd = open(fname.c_str(), O_CREAT|O_WRONLY, 0777);
				if (fd>-1)
				{
					int evLen=HILO(event->descriptors_loop_length)+12/*EIT_LOOP_SIZE*/;
					int wr = ::write( fd, (unsigned char*)event, evLen );
					if ( wr != evLen )
						eDebug("eit write error (%m)");
					::close(fd);
				}
			}
			eEPGCache::getInstance()->Unlock();
		}
		return ret;
	}
	else
		return -1;
}

RESULT eDVBServiceRecord::start()
{
	m_want_record = 1;
		/* when tune wasn't yet successfully, doRecord stays in "prepared"-state which is fine. */
	return doRecord();
}


RESULT eDVBServiceRecord::stop()
{
	eDebug("stop recording!!");
	if (m_state == stateRecording)
	{
		if (m_record)
			m_record->stop();
		if (m_target_fd >= 0)
		{
			::close(m_target_fd);
			m_target_fd = -1;
		}
		m_state = statePrepared;
	}
	
	if (m_state == statePrepared)
	{
		m_record = 0;
		m_state = stateIdle;
	}
	return 0;
}


int eDVBServiceRecord::doPrepare()
{
		/* allocate a ts recorder if we don't already have one. */
	if (m_state == stateIdle)
	{
		m_pids_active.clear();
		m_state = statePrepared;
		return m_service_handler.tune(m_ref, 0);
	}
	return 0;
}

int eDVBServiceRecord::doRecord()
{
	int err = doPrepare();
	if (err)
		return err;
	
	if (!m_tuned)
		return 0; /* try it again when we are tuned in */
	
	if (!m_record && m_tuned)
	{

		eDebug("Recording to %s...", m_filename.c_str());
		::remove(m_filename.c_str());
		int fd = ::open(m_filename.c_str(), O_WRONLY|O_CREAT|O_LARGEFILE, 0644);
		if (fd == -1)
		{
			eDebug("eDVBServiceRecord - can't open recording file!");
			return -1;
		}
		
			/* turn off kernel caching strategies */
		posix_fadvise(fd, 0, 0, POSIX_FADV_RANDOM);
		
		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux))
		{
			eDebug("eDVBServiceRecord - NO DEMUX available!");
			return -2;
		}
		demux->createTSRecorder(m_record);
		if (!m_record)
		{
			eDebug("eDVBServiceRecord - no ts recorder available.");
			return -3;
		}
		m_record->setTargetFD(fd);
		m_record->setTargetFilename(m_filename.c_str());
		m_target_fd = fd;
	}
	eDebug("starting recording..");
	
	eDVBServicePMTHandler::program program;
	if (m_service_handler.getProgramInfo(program))
		eDebug("getting program info failed.");
	else
	{
		std::set<int> pids_to_record;
		
		pids_to_record.insert(0); // PAT
		
		if (program.pmtPid != -1)
			pids_to_record.insert(program.pmtPid); // PMT
		
		int timing_pid = -1;
		
		eDebugNoNewLine("RECORD: have %d video stream(s)", program.videoStreams.size());
		if (!program.videoStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
				i(program.videoStreams.begin()); 
				i != program.videoStreams.end(); ++i)
			{
				pids_to_record.insert(i->pid);
				
				if (timing_pid == -1)
					timing_pid = i->pid;
				
				if (i != program.videoStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebugNoNewLine(", and %d audio stream(s)", program.audioStreams.size());
		if (!program.audioStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::audioStream>::const_iterator
				i(program.audioStreams.begin()); 
				i != program.audioStreams.end(); ++i)
			{
				pids_to_record.insert(i->pid);

				if (timing_pid == -1)
					timing_pid = i->pid;
				
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
		if (program.pcrPid != 0x1fff)
			pids_to_record.insert(program.pcrPid);
		eDebug(", and the text pid is %04x", program.textPid);
		if (program.textPid != -1)
			pids_to_record.insert(program.textPid); // Videotext

			/* find out which pids are NEW and which pids are obsolete.. */
		std::set<int> new_pids, obsolete_pids;
		
		std::set_difference(pids_to_record.begin(), pids_to_record.end(), 
				m_pids_active.begin(), m_pids_active.end(),
				std::inserter(new_pids, new_pids.begin()));
		
		std::set_difference(
				m_pids_active.begin(), m_pids_active.end(),
				pids_to_record.begin(), pids_to_record.end(), 
				std::inserter(new_pids, new_pids.begin())
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
			m_record->setTimingPID(timing_pid);
		
		m_pids_active = pids_to_record;
		
		if (m_state != stateRecording)
		{
			m_record->start();
			m_state = stateRecording;
		}
	}
	return 0;
}

RESULT eDVBServiceRecord::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}
