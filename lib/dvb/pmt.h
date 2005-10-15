#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <dvbsi++/program_map_section.h>
#include <dvbsi++/program_association_section.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>

class eDVBServicePMTHandler;

class eDVBCAService: public Object
{
	eDVBServicePMTHandler &m_parent;
	int m_sock, m_clilen;
	struct sockaddr_un m_servaddr;
	unsigned int m_sendstate;
	unsigned char *m_capmt;
	eTimer m_retryTimer;
	void sendCAPMT();
	void Connect();
public:
	eDVBCAService( eDVBServicePMTHandler &parent )
		:m_parent(parent), m_sendstate(0), m_capmt(NULL), m_retryTimer(eApp)
	{
		CONNECT(m_retryTimer.timeout, eDVBCAService::sendCAPMT);
		Connect();
//		eDebug("[eDVBCAHandler] new service %s", service.toString().c_str() );
	}
	~eDVBCAService()
	{
		delete [] m_capmt;
		::close(m_sock);
//		eDebug("[eDVBCAHandler] leave service %s", me.toString().c_str() );
	}
	void buildCAPMT();
};

class eDVBServicePMTHandler: public Object
{
	friend class eDVBCAService;
	eServiceReferenceDVB m_reference;
	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	uint16_t m_pmt_pid;
	eDVBCAService *m_ca_servicePtr;

	eAUTable<eTable<ProgramMapSection> > m_PMT;
	eAUTable<eTable<ProgramAssociationSection> > m_PAT;

	eUsePtr<iDVBChannel> m_channel;
	eUsePtr<iDVBPVRChannel> m_pvr_channel;
	ePtr<eDVBResourceManager> m_resourceManager;
	ePtr<iDVBDemux> m_demux;
	
	void channelStateChanged(iDVBChannel *);
	ePtr<eConnection> m_channelStateChanged_connection;

	void PMTready(int error);
	void PATready(int error);
	
	int m_record;
public:
	eDVBServicePMTHandler(int record);
	~eDVBServicePMTHandler();
	
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
	int getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel);
	
	int tune(eServiceReferenceDVB &ref);	
};

#endif
