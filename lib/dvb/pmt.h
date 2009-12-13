#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#ifndef SWIG
#include <map>
#include <lib/base/buffer.h>
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

struct channel_data: public Object
{
	ePtr<eDVBChannel> m_channel;
	ePtr<eConnection> m_stateChangedConn;
	int m_prevChannelState;
	int m_dataDemux;
};

// TODO .. put all static stuff into a 'eDVBCAServiceHandler class'

typedef std::map<eServiceReferenceDVB, eDVBCAService*> CAServiceMap;
typedef std::map<iDVBChannel*, channel_data*> ChannelMap;

class eDVBCAService: public Object
{
	eIOBuffer m_buffer;
	ePtr<eSocketNotifier> m_sn;
	eServiceReferenceDVB m_service;
	uint8_t m_used_demux[32];
	unsigned int m_prev_build_hash;

	int m_sock, m_clilen; 
	struct sockaddr_un m_servaddr;
	unsigned int m_sendstate;
	unsigned char m_capmt[2048];
	ePtr<eTimer> m_retryTimer;
	void sendCAPMT();
	void Connect();
	void socketCB(int what);

	static void DVBChannelAdded(eDVBChannel*);
	static void DVBChannelStateChanged(iDVBChannel*);
	static CAServiceMap exist;
	static ChannelMap exist_channels;
	static ePtr<eConnection> m_chanAddedConn;
	static channel_data *getChannelData(eDVBChannelID &chid);

	eDVBCAService();
	~eDVBCAService();
public:
	static void registerChannelCallback(eDVBResourceManager *res_mgr);
	static RESULT register_service( const eServiceReferenceDVB &ref, int demux_nums[2], eDVBCAService *&caservice );
	static RESULT unregister_service( const eServiceReferenceDVB &ref, int demux_nums[2], eTable<ProgramMapSection> *ptr );
	void buildCAPMT(eTable<ProgramMapSection> *ptr);
};

#endif

class eDVBServicePMTHandler: public Object
{
#ifndef SWIG
	friend class eDVBCAService;
	eServiceReferenceDVB m_reference;
	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	eDVBCAService *m_ca_servicePtr;
	ePtr<eDVBScan> m_dvb_scan; // for sdt scan

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
	
	int m_pmt_pid;
	
	int m_use_decode_demux;
	uint8_t m_decode_demux_num;
public:
	eDVBServicePMTHandler();
	~eDVBServicePMTHandler();
#endif

#ifdef SWIG
private:
	eDVBServicePMTHandler();
public:
#endif

	enum
	{
		eventNoResources,  // a requested resource couldn't be allocated
		eventTuneFailed,   // tune failed
		eventNoPAT,        // no pat could be received (timeout)
		eventNoPATEntry,   // no pat entry for the corresponding SID could be found
		eventNoPMT,        // no pmt could be received (timeout)
		eventNewProgramInfo, // we just received a PMT
		eventTuned,        // a channel was sucessfully (re-)tuned in, you may start additional filters now
		
		eventPreStart,     // before start filepush thread
		eventSOF,          // seek pre start
		eventEOF,          // a file playback did end
		
		eventMisconfiguration, // a channel was not found in any list, or no frontend was found which could provide this channel
	};
#ifndef SWIG
	Signal1<void,int> serviceEvent;

	struct videoStream
	{
		int pid;
		int component_tag;
		enum { vtMPEG2, vtMPEG4_H264, vtMPEG1, vtMPEG4_Part2, vtVC1, vtVC1_SM };
		int type;
	};
	
	struct audioStream
	{
		int pid,
		    rdsPid; // hack for some radio services which transmit radiotext on different pid (i.e. harmony fm, HIT RADIO FFH, ...)
		enum { atMPEG, atAC3, atDTS, atAAC, atAACHE, atLPCM };
		int type; // mpeg2, ac3, dts, ...
		
		int component_tag;
		std::string language_code; /* iso-639, if available. */
	};

	struct subtitleStream
	{
		int pid;
		int subtitling_type;  	/*  see ETSI EN 300 468 table 26 component_type
									when stream_content is 0x03
									0x10..0x13, 0x20..0x23 is used for dvb subtitles
									0x01 is used for teletext subtitles */
		union
		{
			int composition_page_id;  // used for dvb subtitles
			int teletext_page_number;  // used for teletext subtitles
		};
		union
		{
			int ancillary_page_id;  // used for dvb subtitles
			int teletext_magazine_number;  // used for teletext subtitles
		};
		std::string language_code;
		bool operator<(const subtitleStream &s) const
		{
			if (pid != s.pid)
				return pid < s.pid;
			if (teletext_page_number != s.teletext_page_number)
				return teletext_page_number < s.teletext_page_number;
			return teletext_magazine_number < s.teletext_magazine_number;
		}
	};

	struct program
	{
		std::vector<videoStream> videoStreams;
		std::vector<audioStream> audioStreams;
		int defaultAudioStream;
		std::vector<subtitleStream> subtitleStreams;
		std::set<uint16_t> caids;
		int pcrPid;
		int pmtPid;
		int textPid;
		bool isCrypted() { return !caids.empty(); }
		PyObject *createPythonObject();
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
	void resetCachedProgram() { m_have_cached_program = false; }

	int tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *sg=0, bool simulate=false, eDVBService *service = 0);
	void free();
private:
	bool m_have_cached_program;
	program m_cached_program;
#endif
};

#endif
