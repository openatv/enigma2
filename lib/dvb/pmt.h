#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/isection.h>
#include <lib/dvb/esection.h>
#include <lib/dvb_si/pmt.h>
#include <lib/dvb_si/pat.h>

class eDVBServicePMTHandler: public Object
{
	eServiceReferenceDVB m_reference;
//	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	
	eAUTable<eTable<ProgramMapTable> > m_PMT;
	eAUTable<eTable<ProgramAssociationTable> > m_PAT;

	ePtr<iDVBChannel> m_channel;
	ePtr<iDVBResourceManager> m_resourceManager;
	ePtr<iDVBDemux> m_demux;
	
	void channelStateChanged(iDVBChannel *);
	ePtr<eConnection> m_channelStateChanged_connection;

	void PMTready(int error);
	void PATready(int error);
public:
	eDVBServicePMTHandler();
	
	enum
	{
		eventNoResources,  // a requested resource couldn't be allocated
		eventNoPAT,        // no pat could be received (timeout)
		eventNoPATEntry,   // no pat entry for the corresponding SID could be found
		eventNoPMT,        // no pmt could be received (timeout)
		eventNewProgramInfo, // we just received a PMT
		eventTuned         // a channel was sucessfully (re-)tuned in, you may start additional filters now
	};

	Signal1<void,int> serviceEvent;
	
	struct videoStream
	{
		int pid;
	};
	
	struct audioStream
	{
		int pid;
		enum { atMPEG, atAC3, atDTS };
		int type; // mpeg2, ac3, dts, ...
		// language code, ...
	};
	
	struct program
	{
		std::vector<videoStream> videoStreams;
		std::vector<audioStream> audioStreams;
		// ca info
		int pcrPid;
	};
	
	int getProgramInfo(struct program &program);
	int getDemux(ePtr<iDVBDemux> &demux);
	
	int tune(eServiceReferenceDVB &ref);	
};

#endif
