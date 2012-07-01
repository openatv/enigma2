#include <lib/service/servicedvbrecord.h>
#include <lib/base/eerror.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/metaparser.h>
#include <lib/base/httpstream.h>
#include <fcntl.h>

	/* for cutlist */
#include <byteswap.h>
#include <netinet/in.h>

// For SYS_ stuff
#include <syscall.h>

#ifndef BYTE_ORDER
#error no byte order defined!
#endif

DEFINE_REF(eDVBServiceRecord);

eDVBServiceRecord::eDVBServiceRecord(const eServiceReferenceDVB &ref, bool isstreamclient): m_ref(ref)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceRecord::serviceEvent);
	CONNECT(m_event_handler.m_eit_changed, eDVBServiceRecord::gotNewEvent);
	m_state = stateIdle;
	m_want_record = 0;
	m_record_ecm = false;
	m_descramble = true;
	m_is_stream_client = isstreamclient;
	m_tuned = 0;
	m_target_fd = -1;
	m_error = 0;
	m_streaming = 0;
	m_simulate = false;
	m_last_event_id = -1;
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
		m_event((iRecordableService*)this, evTunedIn);
		break;
	}
	case eDVBServicePMTHandler::eventTuneFailed:
	{
		eDebug("record failed to tune");
		m_event((iRecordableService*)this, evTuneFailed);
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		if (m_state == stateIdle)
			doPrepare();
		else if (m_want_record) /* doRecord can be called from Prepared and Recording state */
			doRecord();
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
	case eDVBServicePMTHandler::eventStopped:
		/* recording data source has stopped, stop recording */
		stop();
		m_event((iRecordableService*)this, evRecordAborted);
		break;
	}
}

RESULT eDVBServiceRecord::prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm)
{
	m_filename = filename;
	m_streaming = 0;
	m_descramble = descramble;
	m_record_ecm = recordecm;

	if (m_state == stateIdle)
	{
		int ret = doPrepare();
		if (!ret)
		{
			eServiceReferenceDVB ref = m_ref.getParentServiceReference();
			ePtr<eDVBResourceManager> res_mgr;
			eDVBMetaParser meta;
			std::string service_data;
			if (!ref.valid())
				ref = m_ref;
			if (!eDVBResourceManager::getInstance(res_mgr))
			{
				ePtr<iDVBChannelList> db;
				if (!res_mgr->getChannelList(db))
				{
					ePtr<eDVBService> service;
					if (!db->getService(ref, service))
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
			meta.m_scrambled = m_record_ecm; /* assume we will record scrambled data, when ecm will be included in the recording */
			ret = meta.updateMeta(filename) ? -255 : 0;
			if (!ret)
			{
				const eit_event_struct *event = 0;
				eEPGCache::getInstance()->Lock();
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
					int fd = open(fname.c_str(), O_CREAT|O_WRONLY, 0666);
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
		eDebug("stop recording!");
	if (m_state == stateRecording)
	{
		if (m_record)
			m_record->stop();
		if (m_target_fd >= 0)
		{
			::close(m_target_fd);
			m_target_fd = -1;
		}
		
		saveCutlist();
		
		m_state = statePrepared;
	} else if (!m_simulate)
		eDebug("(was not recording)");
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
	if (m_state == stateIdle)
	{
		eDVBServicePMTHandler::serviceType servicetype;
		if (m_streaming)
		{
			servicetype = m_record_ecm ? eDVBServicePMTHandler::scrambled_streamserver : eDVBServicePMTHandler::streamserver;
		}
		else
		{
			servicetype = m_record_ecm ? eDVBServicePMTHandler::scrambled_recording : eDVBServicePMTHandler::recording;
		}
		m_pids_active.clear();
		m_state = statePrepared;
		ePtr<iTsSource> source;
		if (!m_ref.path.empty())
		{
			if (m_is_stream_client)
			{
				/* 
				* streams are considered to be descrambled by default;
				* user can indicate a stream is scrambled, by using servicetype id + 0x100
				*/
				m_descramble = (m_ref.type == eServiceFactoryDVB::id + 0x100);
				m_record_ecm = false;
				servicetype = eDVBServicePMTHandler::streamclient;
				eHttpStream *f = new eHttpStream();
				f->open(m_ref.path.c_str());
				source = ePtr<iTsSource>(f);
			}
			else
			{
				/* re-record a recording */
				servicetype = eDVBServicePMTHandler::offline;
				eRawFile *f = new eRawFile();
				f->open(m_ref.path.c_str());
				source = ePtr<iTsSource>(f);
			}
		}
		return m_service_handler.tuneExt(m_ref, 0, source, m_ref.path.c_str(), 0, m_simulate, NULL, servicetype, m_descramble);
	}
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
		eDebug("Recording to %s...", m_filename.c_str());
		::remove(m_filename.c_str());
		int fd = ::open(m_filename.c_str(), O_WRONLY|O_CREAT|O_LARGEFILE, 0666);
		if (fd == -1)
		{
			eDebug("eDVBServiceRecord - can't open recording file!");
			m_error = errOpenRecordFile;
			m_event((iRecordableService*)this, evRecordFailed);
			return errOpenRecordFile;
		}

		/* Attempt to tune kernel caching strategies */
		int pr;
		pr = syscall(SYS_fadvise64, fd, 0, 0, 0, 0, 0, POSIX_FADV_RANDOM);
		eDebug("POSIX_FADV_RANDOM returned %d", pr);

		ePtr<iDVBDemux> demux;
		if (m_service_handler.getDataDemux(demux))
		{
			eDebug("eDVBServiceRecord - NO DEMUX available!");
			m_error = errNoDemuxAvailable;
			m_event((iRecordableService*)this, evRecordFailed);
			return errNoDemuxAvailable;
		}
		demux->createTSRecorder(m_record);
		if (!m_record)
		{
			eDebug("eDVBServiceRecord - no ts recorder available.");
			m_error = errNoTsRecorderAvailable;
			m_event((iRecordableService*)this, evRecordFailed);
			return errNoTsRecorderAvailable;
		}
		m_record->setTargetFD(fd);
		m_record->setTargetFilename(m_filename);
		m_record->connectEvent(slot(*this, &eDVBServiceRecord::recordEvent), m_con_record_event);

		m_target_fd = fd;
	}
	
	if (m_streaming)
	{
		m_state = stateRecording;
		eDebug("start streaming...");
	} else
	{
		eDebug("start recording...");

		eDVBServicePMTHandler::program program;
		if (m_service_handler.getProgramInfo(program))
			eDebug("getting program info failed.");
		else
		{
			std::set<int> pids_to_record;

			pids_to_record.insert(0); // PAT

			if (program.pmtPid != -1)
				pids_to_record.insert(program.pmtPid); // PMT

			int timing_pid = -1, timing_pid_type = -1;

			eDebugNoNewLine("RECORD: have %zd video stream(s)", program.videoStreams.size());
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
						timing_pid_type = i->type;
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
						timing_pid_type = -1;
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

			if (m_record_ecm)
			{
				for (std::list<eDVBServicePMTHandler::program::capid_pair>::const_iterator i(program.caids.begin()); 
							i != program.caids.end(); ++i)
				{
					if (i->capid >= 0) pids_to_record.insert(i->capid);
				}
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
				eDebug("ADD PID: %04x", *i);
				m_record->addPID(*i);
			}

			for (std::set<int>::iterator i(obsolete_pids.begin()); i != obsolete_pids.end(); ++i)
			{
				eDebug("REMOVED PID: %04x", *i);
				m_record->removePID(*i);
			}

			if (timing_pid != -1)
				m_record->setTimingPID(timing_pid, timing_pid_type);

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

RESULT eDVBServiceRecord::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServiceRecord::connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iRecordableService*)this, m_event.connect(event));
	return 0;
}

RESULT eDVBServiceRecord::stream(ePtr<iStreamableService> &ptr)
{
	ptr = this;
	return 0;
}

extern void PutToDict(ePyObject &dict, const char*key, long val);  // defined in dvb/frontend.cpp

PyObject *eDVBServiceRecord::getStreamingData()
{
	eDVBServicePMTHandler::program program;
	if (!m_tuned || m_service_handler.getProgramInfo(program))
	{
		Py_RETURN_NONE;
	}

	ePyObject r = program.createPythonObject();
	ePtr<iDVBDemux> demux;
	if (!m_service_handler.getDataDemux(demux))
	{
		uint8_t demux_id, adapter_id;
		if (!demux->getCADemuxID(demux_id))
			PutToDict(r, "demux", demux_id);
		if (!demux->getCAAdapterID(adapter_id))
			PutToDict(r, "adapter", adapter_id);
	}

	return r;
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
		eDebug("unhandled record event %d", event);
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
			eDebug("getting PCR failed!");
		else
		{
			m_event_timestamps[event_id] = p;
			eDebug("pcr of eit change: %llx", p);
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
			eDebug("fixed up %llx to %llx (offset %llx)", i->second, p, offset);
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
