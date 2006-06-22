#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#include <map>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/python/python.h>
#include <dvbsi++/program_map_section.h>
#include <dvbsi++/program_association_section.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>

class eDVBCAService;
class eDVBScan;

typedef std::map<eServiceReferenceDVB, eDVBCAService*> CAServiceMap;

class eDVBCAService: public Object
{
	eServiceReferenceDVB m_service;
	uint8_t m_used_demux[32];
	unsigned int m_prev_build_hash;

	int m_sock, m_clilen; 
	struct sockaddr_un m_servaddr;
	unsigned int m_sendstate;
	unsigned char m_capmt[2048];
	eTimer m_retryTimer;
	void sendCAPMT();
	void Connect();

	static CAServiceMap exist;
	eDVBCAService();
	~eDVBCAService();
public:
	static RESULT register_service( const eServiceReferenceDVB &ref, int demux_nums[2], eDVBCAService *&caservice );
	static RESULT unregister_service( const eServiceReferenceDVB &ref, int demux_nums[2], eTable<ProgramMapSection> *ptr );
	void buildCAPMT(eTable<ProgramMapSection> *ptr);
};

class eDVBServicePMTHandler: public Object
{
	friend class eDVBCAService;
	eServiceReferenceDVB m_reference;
	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	eDVBCAService *m_ca_servicePtr;
	eDVBScan *m_dvb_scan; // for sdt scan

	eAUTable<eTable<ProgramMapSection> > m_PMT;
	eAUTable<eTable<ProgramAssociationSection> > m_PAT;

	eUsePtr<iDVBChannel> m_channel;
	eUsePtr<iDVBPVRChannel> m_pvr_channel;
	ePtr<eDVBResourceManager> m_resourceManager;
	ePtr<iDVBDemux> m_demux;
	
	void channelStateChanged(iDVBChannel *);
	ePtr<eConnection> m_channelStateChanged_connection;
	void channelEvent(iDVBChannel *, int event);
	ePtr<eConnection> m_channelEvent_connection;
	void SDTScanEvent(int);
	ePtr<eConnection> m_scan_event_connection;

	void PMTready(int error);
	void PATready(int error);
	
	int m_use_decode_demux;
	uint8_t m_decode_demux_num;

public:
	eDVBServicePMTHandler();
	~eDVBServicePMTHandler();
	
	enum
	{
		eventNoResources,  // a requested resource couldn't be allocated
		eventTuneFailed,   // tune failed
		eventNoPAT,        // no pat could be received (timeout)
		eventNoPATEntry,   // no pat entry for the corresponding SID could be found
		eventNoPMT,        // no pmt could be received (timeout)
		eventNewProgramInfo, // we just received a PMT
		eventTuned,        // a channel was sucessfully (re-)tuned in, you may start additional filters now
		
		eventSOF,          // seek pre start
		eventEOF,          // a file playback did end
	};

	Signal1<void,int> serviceEvent;

	struct videoStream
	{
		int pid;
		int component_tag;
		enum { vtMPEG2, vtMPEG4_H264 };
		int type;
	};
	
	struct audioStream
	{
		int pid;
		enum { atMPEG, atAC3, atDTS, atAAC };
		int type; // mpeg2, ac3, dts, ...
		
		int component_tag;
		std::string language_code; /* iso-639, if available. */
	};
	
	struct program
	{
		std::vector<videoStream> videoStreams;
		std::vector<audioStream> audioStreams;
		std::set<uint16_t> caids;
		int pcrPid;
		int pmtPid;
		int textPid;
		bool isCrypted() { return !caids.empty(); }
	};

	int getProgramInfo(struct program &program);
	int getDataDemux(ePtr<iDVBDemux> &demux);
	int getDecodeDemux(ePtr<iDVBDemux> &demux);
	PyObject *getCaIds();
	
	int getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel);
	int getServiceReference(eServiceReferenceDVB &service) { service = m_reference; return 0; }
	int getService(ePtr<eDVBService> &service) { service = m_service; return 0; }
	int getPMT(ePtr<eTable<ProgramMapSection> > &ptr) { return m_PMT.getCurrent(ptr); }
	int getChannel(eUsePtr<iDVBChannel> &channel);

	int tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *sg=0);
	void free();

	int m_pmt_pid;
};

#endif
