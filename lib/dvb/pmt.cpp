 #include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/metaparser.h>

eDVBServicePMTHandler::eDVBServicePMTHandler()
{
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
}

void eDVBServicePMTHandler::channelStateChanged(iDVBChannel *channel)
{
	int state;
	channel->getState(state);
	
	if ((m_last_channel_state != iDVBChannel::state_ok)
		&& (state == iDVBChannel::state_ok) && (!m_demux))
	{
		if (m_channel)
			if (m_channel->getDemux(m_demux))
				eDebug("shit it failed.. again.");
		
		serviceEvent(eventTuned);
		
		if (m_demux)
		{
			eDebug("ok ... now we start!!");

			/* emit */ m_resourceManager->m_channelRunning(channel);

			m_PAT.begin(eApp, eDVBPATSpec(), m_demux);

			if ( m_service && !m_service->cacheEmpty() )
				serviceEvent(eventNewProgramInfo);
		}
	}
}

void eDVBServicePMTHandler::PMTready(int error)
{
	if (error)
		serviceEvent(eventNoPMT);
	else
		serviceEvent(eventNewProgramInfo);
}

void eDVBServicePMTHandler::PATready(int)
{
	eDebug("got PAT");
	ePtr<eTable<ProgramAssociationTable> > ptr;
	if (!m_PAT.getCurrent(ptr))
	{
		int pmtpid = -1;
		ProgramAssociationTableConstIterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramAssociationTable &pat = **i;
			ProgramAssociationConstIterator program;
			for (program = pat.getPrograms()->begin(); program != pat.getPrograms()->end(); ++program)
				if (eServiceID((*program)->getProgramNumber()) == m_reference.getServiceID())
					pmtpid = (*program)->getProgramMapPid();
		}
		if (pmtpid == -1)
			serviceEvent(eventNoPATEntry);
		else
			m_PMT.begin(eApp, eDVBPMTSpec(pmtpid, m_reference.getServiceID().get()), m_demux);
	} else
		serviceEvent(eventNoPAT);
}

int eDVBServicePMTHandler::getProgramInfo(struct program &program)
{
	eDebug("got PMT");
	ePtr<eTable<ProgramMapTable> > ptr;

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.pcrPid = -1;

	if (!m_PMT.getCurrent(ptr))
	{
		ProgramMapTableConstIterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramMapTable &pmt = **i;
			program.pcrPid = pmt.getPcrPid();
			
			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int isaudio = 0, isvideo = 0;
				videoStream video;
				audioStream audio;
				
				video.pid = (*es)->getPid();
				audio.pid = (*es)->getPid();
				
				switch ((*es)->getType())
				{
				case 0x01: // MPEG 1 video
				case 0x02: // MPEG 2 video
					isvideo = 1;
					break;
				case 0x03: // MPEG 1 audio
				case 0x04: // MPEG 2 audio:
					isaudio = 1;
					audio.type = audioStream::atMPEG;
					break;
				}
				if (isaudio)
					program.audioStreams.push_back(audio);
				if (isvideo)
					program.videoStreams.push_back(video);
			}
		}
		return 0;
	}
	else if ( m_service && !m_service->cacheEmpty() )
	{
		int vpid = m_service->getCachePID(eDVBService::cVPID),
			apid_ac3 = m_service->getCachePID(eDVBService::cAPID),
			apid_mpeg = m_service->getCachePID(eDVBService::cAC3PID),
			pcrpid = m_service->getCachePID(eDVBService::cPCRPID),
			cnt=0;
		if ( vpid != -1 )
		{
			videoStream s;
			s.pid = vpid;
			program.videoStreams.push_back(s);
			++cnt;
		}
		if ( apid_ac3 != -1 )
		{
			audioStream s;
			s.type = audioStream::atAC3;
			s.pid = apid_ac3;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( apid_mpeg != -1 )
		{
			audioStream s;
			s.type = audioStream::atMPEG;
			s.pid = apid_mpeg;
			program.audioStreams.push_back(s);
			++cnt;
		}
		if ( pcrpid != -1 )
		{
			++cnt;
			program.pcrPid = pcrpid;
		}
		if ( cnt )
			return 0;
	}
	return -1;
}

int eDVBServicePMTHandler::getDemux(ePtr<iDVBDemux> &demux)
{
	demux = m_demux;
	if (demux)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref)
{
	RESULT res;
	m_reference = ref;
	
//	ref.path = "/viva.ts"; // hrhr.
	
		/* is this a normal (non PVR) channel? */
	if (ref.path.empty())
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = m_resourceManager->allocateChannel(chid, m_channel);
	} else
	{
		eDVBMetaParser parser;
		
		if (parser.parseFile(ref.path))
			eWarning("no .meta file found, trying original service ref.");
		else
			m_reference = parser.m_ref;
		
		eDebug("alloc PVR");
			/* allocate PVR */
		res = m_resourceManager->allocatePVRChannel(m_pvr_channel);
		if (res)
			eDebug("allocatePVRChannel failed!\n");
		m_channel = m_pvr_channel;
	}
	
	if (m_channel)
	{
		m_channel->connectStateChange(
			slot(*this, &eDVBServicePMTHandler::channelStateChanged), 
			m_channelStateChanged_connection);
		m_last_channel_state = -1;
		channelStateChanged(m_channel);
	}

	if (m_pvr_channel)
		m_pvr_channel->playFile(ref.path.c_str());

	ePtr<iDVBChannelList> db;
	if (!m_resourceManager->getChannelList(db))
		db->getService((eServiceReferenceDVB&)m_reference, m_service);

	return res;
}
