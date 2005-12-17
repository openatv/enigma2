#include <lib/service/servicedvbrecord.h>
#include <lib/base/eerror.h>

#include <fcntl.h>

DEFINE_REF(eDVBServiceRecord);

eDVBServiceRecord::eDVBServiceRecord(const eServiceReferenceDVB &ref): m_ref(ref), m_service_handler(1)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceRecord::serviceEvent);
	m_state = stateIdle;
	m_want_record = 0;
}

void eDVBServiceRecord::serviceEvent(int event)
{
	eDebug("RECORD service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("tuned..");
		if (!m_record)
		{
			eDebug("Recording to %s...", m_filename.c_str());
			::remove(m_filename.c_str());
			int fd = ::open(m_filename.c_str(), O_WRONLY|O_CREAT, 0644);
			if (fd == -1)
			{
				eDebug("eDVBServiceRecord - can't open hardcoded recording file!");
				return;
//				return -1;
			}
			ePtr<iDVBDemux> demux;
			if (m_service_handler.getDemux(demux))
			{
				eDebug("eDVBServiceRecord - NO DEMUX available!");
				return;
//				return -2;
			}
			demux->createTSRecorder(m_record);
			if (!m_record)
			{
				eDebug("eDVBServiceRecord - no ts recorder available.");
				return;
//				return -3;
			}
			m_record->setTargetFD(fd);
		}
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


RESULT eDVBServiceRecord::prepare(const char *filename)
{
	m_filename = filename;
	if (m_state == stateIdle)
		doPrepare();
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


int eDVBServiceRecord::doPrepare()
{
		/* allocate a ts recorder if we don't already have one. */
	if (m_state == stateIdle)
	{
		m_pids_active.clear();
		m_state = statePrepared;
		m_service_handler.tune(m_ref);
	}
	return 0;
}

int eDVBServiceRecord::doRecord()
{
	int err = doPrepare();
	if (err)
		return err;
	
	if (!m_record)
	{
		eDebug("demux not available (tune failed?). cannot record.");
		return -1;
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
		
		eDebugNoNewLine("RECORD: have %d video stream(s)", program.videoStreams.size());
		if (!program.videoStreams.empty())
		{
			eDebugNoNewLine(" (");
			for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
				i(program.videoStreams.begin()); 
				i != program.videoStreams.end(); ++i)
			{
				pids_to_record.insert(i->pid);
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
				if (i != program.audioStreams.begin())
					eDebugNoNewLine(", ");
				eDebugNoNewLine("%04x", i->pid);
			}
			eDebugNoNewLine(")");
		}
		eDebug(", and the pcr pid is %04x", program.pcrPid);
		if (program.pcrPid != 0x1fff)
			pids_to_record.insert(program.pcrPid);
		
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
		
		if (m_state != stateRecording)
		{
			m_record->start();
			m_state = stateRecording;
		}
	}
	return 0;
}
