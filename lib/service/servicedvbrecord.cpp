#include <lib/service/servicedvbrecord.h>
#include <lib/base/eerror.h>


DEFINE_REF(eDVBServiceRecord);

eDVBServiceRecord::eDVBServiceRecord(const eServiceReferenceDVB &ref): m_ref(ref)
{
	CONNECT(m_service_handler.serviceEvent, eDVBServiceRecord::serviceEvent);
}

void eDVBServiceRecord::serviceEvent(int event)
{
	eDebug("service event %d", event);
	switch (event)
	{
	case eDVBServicePMTHandler::eventTuned:
	{
		eDebug("tuned..");
		break;
	}
	case eDVBServicePMTHandler::eventNewProgramInfo:
	{
		int vpid = -1, apid = -1, pcrpid = -1;
		eDVBServicePMTHandler::program program;
		if (m_service_handler.getProgramInfo(program))
			eDebug("getting program info failed.");
		else
		{
			eDebugNoNewLine("RECORD: have %d video stream(s)", program.videoStreams.size());
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
		
				// notify record thread...		
		break;
	}
	}
}

RESULT eDVBServiceRecord::start()
{
	eDebug("starting recording..");
	return m_service_handler.tune(m_ref);
}

RESULT eDVBServiceRecord::stop()
{
	eDebug("stop recording!!");
	return 0;
}

