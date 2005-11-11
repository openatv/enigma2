#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/metaparser.h>
#include <dvbsi++/ca_program_map_section.h>

eDVBServicePMTHandler::eDVBServicePMTHandler(int record)
	:m_pmt_pid(0xFFFF), m_ca_servicePtr(0)
{
	m_record = record;
	eDVBResourceManager::getInstance(m_resourceManager);
	CONNECT(m_PMT.tableReady, eDVBServicePMTHandler::PMTready);
	CONNECT(m_PAT.tableReady, eDVBServicePMTHandler::PATready);
}

eDVBServicePMTHandler::~eDVBServicePMTHandler()
{
	delete m_ca_servicePtr;
}

void eDVBServicePMTHandler::channelStateChanged(iDVBChannel *channel)
{
	int state;
	channel->getState(state);
	
	if ((m_last_channel_state != iDVBChannel::state_ok)
		&& (state == iDVBChannel::state_ok) && (!m_demux))
	{
		if (m_channel)
			if (m_channel->getDemux(m_demux, m_record ? 0 : iDVBChannel::capDecode))
				eDebug("Allocating a demux for now tuned-in channel failed.");
		
		serviceEvent(eventTuned);
		
		if (m_demux)
		{
			eDebug("ok ... now we start!!");

			/* emit */ m_resourceManager->m_channelRunning(channel);

			m_PAT.begin(eApp, eDVBPATSpec(), m_demux);

			if ( m_service && !m_service->cacheEmpty() )
				serviceEvent(eventNewProgramInfo);
		}
	} else if ((m_last_channel_state != iDVBChannel::state_failed) && 
			(state == iDVBChannel::state_failed))
	{
		eDebug("tune failed.");
		serviceEvent(eventTuneFailed);
	}
}

void eDVBServicePMTHandler::PMTready(int error)
{
	if (error)
		serviceEvent(eventNoPMT);
	else
	{
		serviceEvent(eventNewProgramInfo);
		if (!m_pvr_channel && !m_ca_servicePtr)   // don't send campmt to camd.socket for playbacked services
			m_ca_servicePtr = new eDVBCAService(*this);
		if (m_ca_servicePtr)
			m_ca_servicePtr->buildCAPMT();
	}
}

void eDVBServicePMTHandler::PATready(int)
{
	eDebug("got PAT");
	ePtr<eTable<ProgramAssociationSection> > ptr;
	if (!m_PAT.getCurrent(ptr))
	{
		int pmtpid = -1;
		std::vector<ProgramAssociationSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramAssociationSection &pat = **i;
			ProgramAssociationConstIterator program;
			for (program = pat.getPrograms()->begin(); program != pat.getPrograms()->end(); ++program)
				if (eServiceID((*program)->getProgramNumber()) == m_reference.getServiceID())
					pmtpid = (*program)->getProgramMapPid();
		}
		if (pmtpid == -1)
			serviceEvent(eventNoPATEntry);
		else
		{
			m_PMT.begin(eApp, eDVBPMTSpec(pmtpid, m_reference.getServiceID().get()), m_demux);
			m_pmt_pid = pmtpid;
		}
	} else
		serviceEvent(eventNoPAT);
}

int eDVBServicePMTHandler::getProgramInfo(struct program &program)
{
	eDebug("got PMT");
	ePtr<eTable<ProgramMapSection> > ptr;

	program.videoStreams.clear();
	program.audioStreams.clear();
	program.pcrPid = -1;
	program.pmtPid = m_pmt_pid < 0x1fff ? m_pmt_pid : -1;

	if (!m_PMT.getCurrent(ptr))
	{
		std::vector<ProgramMapSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;
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

int eDVBServicePMTHandler::getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel)
{
	pvr_channel = m_pvr_channel;
	if (pvr_channel)
		return 0;
	else
		return -1;
}

int eDVBServicePMTHandler::tune(eServiceReferenceDVB &ref)
{
	RESULT res;
	m_reference = ref;
	
		/* is this a normal (non PVR) channel? */
	if (ref.path.empty())
	{
		eDVBChannelID chid;
		ref.getChannelID(chid);
		res = m_resourceManager->allocateChannel(chid, m_channel);
		eDebug("allocate Channel: res %d", res);
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
	} else
	{
		serviceEvent(eventTuneFailed);
		return res;
	}

	if (m_pvr_channel)
		m_pvr_channel->playFile(ref.path.c_str());

	ePtr<iDVBChannelList> db;
	if (!m_resourceManager->getChannelList(db))
		db->getService((eServiceReferenceDVB&)m_reference, m_service);

	return res;
}

void eDVBCAService::Connect()
{
	memset(&m_servaddr, 0, sizeof(struct sockaddr_un));
	m_servaddr.sun_family = AF_UNIX;
	strcpy(m_servaddr.sun_path, "/tmp/camd.socket");
	m_clilen = sizeof(m_servaddr.sun_family) + strlen(m_servaddr.sun_path);
	m_sock = socket(PF_UNIX, SOCK_STREAM, 0);
	connect(m_sock, (struct sockaddr *) &m_servaddr, m_clilen);
	fcntl(m_sock, F_SETFL, O_NONBLOCK);
	int val=1;
	setsockopt(m_sock, SOL_SOCKET, SO_REUSEADDR, &val, 4);
}

void eDVBCAService::buildCAPMT()
{
	ePtr<eTable<ProgramMapSection> > ptr;

	if (m_parent.m_PMT.getCurrent(ptr))
		return;

	std::vector<ProgramMapSection*>::const_iterator i=ptr->getSections().begin();
	if ( i != ptr->getSections().end() )
	{
		CaProgramMapSection capmt(*i++, m_capmt == NULL ? 0x03 /*only*/: 0x05 /*update*/, 0x01 );

		while( i != ptr->getSections().end() )
		{
//			eDebug("append");
			capmt.append(*i++);
		}

		// add our private descriptors to capmt
		uint8_t tmp[10];

		tmp[0]=0x84;  // pmt pid
		tmp[1]=0x02;
		tmp[2]=m_parent.m_pmt_pid>>8;
		tmp[3]=m_parent.m_pmt_pid&0xFF;
		capmt.injectDescriptor(tmp, false);

		tmp[0] = 0x82; // demux
		tmp[1] = 0x02;
		m_parent.m_demux->getCADemuxID(tmp[3]); // read section data from demux number
		tmp[2] = 1 << tmp[3];			// descramble bitmask
		capmt.injectDescriptor(tmp, false);

		tmp[0] = 0x81; // dvbnamespace
		tmp[1] = 0x08;
		tmp[2] = m_parent.m_reference.getDVBNamespace().get()>>24;
		tmp[3]=(m_parent.m_reference.getDVBNamespace().get()>>16)&0xFF;
		tmp[4]=(m_parent.m_reference.getDVBNamespace().get()>>8)&0xFF;
		tmp[5]=m_parent.m_reference.getDVBNamespace().get()&0xFF;
		tmp[6]=m_parent.m_reference.getTransportStreamID().get()>>8;
		tmp[7]=m_parent.m_reference.getTransportStreamID().get()&0xFF;
		tmp[8]=m_parent.m_reference.getOriginalNetworkID().get()>>8;
		tmp[9]=m_parent.m_reference.getOriginalNetworkID().get()&0xFF;
		capmt.injectDescriptor(tmp, false);

		if ( !m_capmt )
			m_capmt = new uint8_t[2048];

		capmt.writeToBuffer(m_capmt);
	}

	if ( m_sendstate != 0xFFFFFFFF )
		m_sendstate=0;
	sendCAPMT();
}

void eDVBCAService::sendCAPMT()
{
	if ( m_sendstate && m_sendstate != 0xFFFFFFFF ) // broken pipe retry
	{
		::close(m_sock);
		Connect();
	}

	int wp=0;
	if ( m_capmt[3] & 0x80 )
	{
		int i=0;
		int lenbytes = m_capmt[3] & ~0x80;
		while(i < lenbytes)
			wp |= (m_capmt[4+i] << (8 * i++));
		wp+=4;
		wp+=lenbytes;
	}
	else
	{
		wp = m_capmt[3];
		wp+=4;
	}

	if ( write(m_sock, m_capmt, wp) == wp )
	{
		m_sendstate=0xFFFFFFFF;
		eDebug("[eDVBCAHandler] send %d bytes",wp);
#if 1
		for(int i=0;i<wp;i++)
			eDebugNoNewLine("%02x ", m_capmt[i]);
		eDebug("");
#endif
	}
	else
	{
		switch(m_sendstate)
		{
			case 0xFFFFFFFF:
				++m_sendstate;
				m_retryTimer.start(0,true);
//				eDebug("[eDVBCAHandler] send failed .. immediate retry");
				break;
			default:
				m_retryTimer.start(5000,true);
//				eDebug("[eDVBCAHandler] send failed .. retry in 5 sec");
				break;
		}
		++m_sendstate;
	}
}
