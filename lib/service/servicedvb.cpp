#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicedvb.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

DEFINE_REF(eServiceFactoryDVB)

eServiceFactoryDVB::eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryDVB::id, this);
}

eServiceFactoryDVB::~eServiceFactoryDVB()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryDVB::id);
}

RESULT eServiceFactoryDVB::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
		// check resources...
	ptr = new eDVBServicePlay(ref);
	return 0;
}

RESULT eServiceFactoryDVB::record(const eServiceReference &, ePtr<iRecordableService> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceFactoryDVB::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr = 0;
	return -1;
}

eDVBServicePlay::eDVBServicePlay(const eServiceReference &ref): 
	m_reference(ref)
{
	CONNECT(m_serviceHandler.serviceEvent, eDVBServicePlay::serviceEvent);
	eDebug("DVB start (play)");
}

eDVBServicePlay::~eDVBServicePlay()
{
	eDebug("DVB stop (play)");
}

void eDVBServicePlay::serviceEvent(int event)
{
	eDebug("service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		int vpid = -1, apid = -1, pcrpid = -1;
		eDVBServicePMTHandler::program program;
		if (m_serviceHandler.getProgramInfo(program))
			eDebug("getting program info failed.");
		else
		{
			eDebugNoNewLine("have %d video stream(s)", program.videoStreams.size());
			if (!program.videoStreams.empty())
			{
				eDebugNoNewLine(" (");
				for (std::vector<eDVBServicePMTHandler::videoStream>::const_iterator
					i(program.videoStreams.begin()); 
					i != program.videoStreams.end(); ++i)
				{
					if (vpid == -1)
						vpid = i->pid;
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
					if (apid == -1)
						apid = i->pid;
					if (i != program.audioStreams.begin())
						eDebugNoNewLine(", ");
					eDebugNoNewLine("%04x", i->pid);
				}
				eDebugNoNewLine(")");
			}
			eDebug(", and the pcr pid is %04x", program.pcrPid);
			if (program.pcrPid != 0x1fff)
				pcrpid = program.pcrPid;
		}
		
		if (!m_decoder)
		{
			ePtr<iDVBDemux> demux;
			m_serviceHandler.getDemux(demux);
			if (demux)
				demux->getMPEGDecoder(m_decoder);
		}

		if (m_decoder)
		{
			m_decoder->setVideoPID(vpid);
			m_decoder->setAudioPID(apid, 0);
			m_decoder->setSyncPCR(pcrpid);
			m_decoder->start();
		}
				
		break;
	}
	}
}

RESULT eDVBServicePlay::start()
{
	eDebug("starting DVB service");
	return m_serviceHandler.tune((eServiceReferenceDVB&)m_reference);
}

RESULT eDVBServicePlay::stop()
{
	eDebug("stopping..");
	return 0;
}

RESULT eDVBServicePlay::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	return -1;
}

RESULT eDVBServicePlay::getIPausableService(ePtr<iPauseableService> &ptr)
{
		// not yet possible, maybe later...
	ptr = 0;
	return -1;
}

RESULT eDVBServicePlay::getIServiceInformation(ePtr<iServiceInformation> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eDVBServicePlay::getName(std::string &name)
{
	name = "DVB service";
	return 0;
}

DEFINE_REF(eDVBServicePlay)

eAutoInitPtr<eServiceFactoryDVB> init_eServiceFactoryDVB(eAutoInitNumbers::service+1, "eServiceFactoryDVB");
