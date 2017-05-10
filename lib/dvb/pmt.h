#ifndef __lib_dvb_dvbmid_h
#define __lib_dvb_dvbmid_h

#ifndef SWIG
#include <map>
#include <lib/base/buffer.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/cahandler.h>
#include <lib/dvb/pmtparse.h>
#include <lib/python/python.h>

#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>

class eDVBScan;

#endif

class OCSection : public LongCrcSection
{
	protected:
		void *data;

	public:
		OCSection(const uint8_t * const buffer)
		: LongCrcSection(buffer)
		{
			data = malloc(getSectionLength());
			memcpy(data, buffer, getSectionLength());
		}
		~OCSection()
		{
			free(data);
		}
		void *getData() { return data; }
};

class eDVBServicePMTHandler: public eDVBPMTParser
{
#ifndef SWIG
	friend class eDVBCAService;
	eServiceReferenceDVB m_reference;
	ePtr<eDVBService> m_service;

	int m_last_channel_state;
	eDVBCAService *m_ca_servicePtr;
	ePtr<eDVBScan> m_dvb_scan; // for sdt scan

	eAUTable<eTable<ProgramAssociationSection> > m_PAT;
	eAUTable<eTable<ApplicationInformationSection> > m_AIT;
	eAUTable<eTable<OCSection> > m_OC;

	eUsePtr<iDVBChannel> m_channel;
	eUsePtr<iDVBPVRChannel> m_pvr_channel;
	ePtr<eDVBResourceManager> m_resourceManager;
	ePtr<iDVBDemux> m_demux, m_pvr_demux_tmp;

	void channelStateChanged(iDVBChannel *);
	ePtr<eConnection> m_channelStateChanged_connection;
	void channelEvent(iDVBChannel *, int event);
	ePtr<eConnection> m_channelEvent_connection;
	void SDTScanEvent(int);
	ePtr<eConnection> m_scan_event_connection;

	void registerCAService();

	void PMTready(int error);
	void PATready(int error);
	void AITready(int error);
	void OCready(int error);

	int m_pmt_pid;
	int m_dsmcc_pid;
	std::string m_HBBTVUrl;

	int m_use_decode_demux;
	uint8_t m_decode_demux_num;
	ePtr<eTimer> m_no_pat_entry_delay;
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

		eventHBBTVInfo, /* HBBTV information was detected in the AIT */

		eventStopped,
	};
#ifndef SWIG
	sigc::signal1<void,int> serviceEvent;

	int getProgramInfo(program &program);
	int getDataDemux(ePtr<iDVBDemux> &demux);
	int getDecodeDemux(ePtr<iDVBDemux> &demux);
	void getAITApplications(std::map<int, std::string> &aitlist);
	void getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids);

	int getPVRChannel(ePtr<iDVBPVRChannel> &pvr_channel);
	int getServiceReference(eServiceReferenceDVB &service) { service = m_reference; return 0; }
	int getService(ePtr<eDVBService> &service) { service = m_service; return 0; }
	int getPMT(ePtr<eTable<ProgramMapSection> > &ptr) { return m_PMT.getCurrent(ptr); }
	int getChannel(eUsePtr<iDVBChannel> &channel);
	int getDemuxID() const { return m_decode_demux_num; }
	void resetCachedProgram() { m_have_cached_program = false; }
	void sendEventNoPatEntry();
	void getHBBTVUrl(std::string &ret) const { ret = m_HBBTVUrl; }

	enum serviceType
	{
		livetv = 0,
		recording = 1,
		scrambled_recording = 2,
		playback = 3,
		timeshift_recording = 4,
		scrambled_timeshift_recording = 5,
		timeshift_playback = 6,
		streamserver = 7,
		scrambled_streamserver = 8,
		streamclient = 9,
		offline = 10
	};

	/* deprecated interface */
	int tune(eServiceReferenceDVB &ref, int use_decode_demux, eCueSheet *sg=0, bool simulate=false, eDVBService *service = 0, serviceType type = livetv, bool descramble = true);

	/* new interface */
	int tuneExt(eServiceReferenceDVB &ref, ePtr<iTsSource> &, const char *streaminfo_file, eCueSheet *sg=0, bool simulate=false, eDVBService *service = 0, serviceType type = livetv, bool descramble = true);

	void free();
private:
	bool m_have_cached_program;
	program m_cached_program;
	serviceType m_service_type;

	struct aitInfo
	{
		int id;
		std::string url;
		std::string name;
	};
	std::vector<struct aitInfo> m_aitInfoList;
#endif
};

#endif
