#ifndef __dvb_idvb_h
#define __dvb_idvb_h

#include <config.h>
#if HAVE_DVB_API_VERSION < 3
#include <ost/frontend.h>
#define FRONTENDPARAMETERS FrontendParameters
#else
#include <linux/dvb/frontend.h>
#define FRONTENDPARAMETERS struct dvb_frontend_parameters
#endif
#include <lib/dvb/frontendparms.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/service/service.h>
#include <libsig_comp.h>
#include <connection.h>

struct eBouquet
{
	std::string m_bouquet_name;
	std::string m_path;
	typedef std::list<eServiceReference> list;
	list m_services;
// the following four methods are implemented in db.cpp
	RESULT flushChanges();
	RESULT addService(const eServiceReference &);
	RESULT removeService(const eServiceReference &);
	RESULT moveService(const eServiceReference &, unsigned int);
};

		/* these structures have by intention no operator int() defined.
		   the reason of these structures is to avoid mixing for example
		   a onid and a tsid (as there's no general order for them).
		   
		   defining an operator int() would implicitely convert values
		   between them over the constructor with the int argument.
		   
		   'explicit' doesn't here - eTransportStreamID(eOriginalNetworkID(n)) 
		   would still work. */

struct eTransportStreamID
{
private:
	int v;
public:
	int get() const { return v; }
	eTransportStreamID(int i): v(i) { }
	eTransportStreamID(): v(-1) { }
	bool operator == (const eTransportStreamID &c) const { return v == c.v; }
	bool operator != (const eTransportStreamID &c) const { return v != c.v; }
	bool operator < (const eTransportStreamID &c) const { return v < c.v; }
	bool operator > (const eTransportStreamID &c) const { return v > c.v; }
};

struct eServiceID
{
private:
	int v;
public:
	int get() const { return v; }
	eServiceID(int i): v(i) { }
	eServiceID(): v(-1) { }
	bool operator == (const eServiceID &c) const { return v == c.v; }
	bool operator != (const eServiceID &c) const { return v != c.v; }
	bool operator < (const eServiceID &c) const { return v < c.v; }
	bool operator > (const eServiceID &c) const { return v > c.v; }
};

struct eOriginalNetworkID
{
private:
	int v;
public:
	int get() const { return v; }
	eOriginalNetworkID(int i): v(i) { }
	eOriginalNetworkID(): v(-1) { }
	bool operator == (const eOriginalNetworkID &c) const { return v == c.v; }
	bool operator != (const eOriginalNetworkID &c) const { return v != c.v; }
	bool operator < (const eOriginalNetworkID &c) const { return v < c.v; }
	bool operator > (const eOriginalNetworkID &c) const { return v > c.v; }
};

struct eDVBNamespace
{
private:
	int v;
public:
	int get() const { return v; }
	eDVBNamespace(int i): v(i) { }
	eDVBNamespace(): v(-1) { }
	bool operator == (const eDVBNamespace &c) const { return v == c.v; }
	bool operator != (const eDVBNamespace &c) const { return v != c.v; }
	bool operator < (const eDVBNamespace &c) const { return v < c.v; }
	bool operator > (const eDVBNamespace &c) const { return v > c.v; }
};

struct eDVBChannelID
{
	eDVBNamespace dvbnamespace;
	eTransportStreamID transport_stream_id;
	eOriginalNetworkID original_network_id;
	
	bool operator==(const eDVBChannelID &c) const
	{
		return dvbnamespace == c.dvbnamespace &&
			transport_stream_id == c.transport_stream_id &&
			original_network_id == c.original_network_id;
	}
	
	bool operator<(const eDVBChannelID &c) const
	{
		if (dvbnamespace < c.dvbnamespace)
			return 1;
		else if (dvbnamespace == c.dvbnamespace)
		{
			if (original_network_id < c.original_network_id)
				return 1;
			else if (original_network_id == c.original_network_id)
				if (transport_stream_id < c.transport_stream_id)
					return 1;
		}
		return 0;
	}
	eDVBChannelID(eDVBNamespace dvbnamespace, eTransportStreamID tsid, eOriginalNetworkID onid): 
			dvbnamespace(dvbnamespace), transport_stream_id(tsid), original_network_id(onid)
	{
	}
	eDVBChannelID():
			dvbnamespace(-1), transport_stream_id(-1), original_network_id(-1)
	{
	}
	operator bool() const
	{
		return (dvbnamespace != -1) && (transport_stream_id != -1) && (original_network_id != -1);
	}
};

struct eServiceReferenceDVB: public eServiceReference
{
	int getServiceType() const { return data[0]; }
	void setServiceType(int service_type) { data[0]=service_type; }

	eServiceID getServiceID() const { return eServiceID(data[1]); }
	void setServiceID(eServiceID service_id) { data[1]=service_id.get(); }

	eTransportStreamID getTransportStreamID() const { return eTransportStreamID(data[2]); }
	void setTransportStreamID(eTransportStreamID transport_stream_id) { data[2]=transport_stream_id.get(); }

	eOriginalNetworkID getOriginalNetworkID() const { return eOriginalNetworkID(data[3]); }
	void setOriginalNetworkID(eOriginalNetworkID original_network_id) { data[3]=original_network_id.get(); }

	eDVBNamespace getDVBNamespace() const { return eDVBNamespace(data[4]); }
	void setDVBNamespace(eDVBNamespace dvbnamespace) { data[4]=dvbnamespace.get(); }

	eServiceReferenceDVB(eDVBNamespace dvbnamespace, eTransportStreamID transport_stream_id, eOriginalNetworkID original_network_id, eServiceID service_id, int service_type)
		:eServiceReference(eServiceReference::idDVB, 0)
	{
		setTransportStreamID(transport_stream_id);
		setOriginalNetworkID(original_network_id);
		setDVBNamespace(dvbnamespace);
		setServiceID(service_id);
		setServiceType(service_type);
	}
	
	void set(const eDVBChannelID &chid)
	{
		setDVBNamespace(chid.dvbnamespace);
		setOriginalNetworkID(chid.original_network_id);
		setTransportStreamID(chid.transport_stream_id);
	}
	
	void getChannelID(eDVBChannelID &chid) const
	{
		chid = eDVBChannelID(getDVBNamespace(), getTransportStreamID(), getOriginalNetworkID());
	}

	eServiceReferenceDVB()
		:eServiceReference(eServiceReference::idDVB, 0)
	{
	}
};


////////////////// TODO: we need an interface here, but what exactly?

#include <set>
// btw, still implemented in db.cpp. FIX THIS, TOO.

class eDVBChannelQuery;

class eDVBService: public iStaticServiceInformation
{
	DECLARE_REF(eDVBService);
public:
	enum cacheID
	{
		cVPID, cAPID, cTPID, cPCRPID, cAC3PID, cacheMax
	};

	int getCachePID(cacheID);
	void setCachePID(cacheID, int);
	bool cacheEmpty() { return m_cache.empty(); }

	eDVBService();
		/* m_service_name_sort is uppercase, with special chars removed, to increase sort performance. */
	std::string m_service_name, m_service_name_sort;
	std::string m_provider_name;
	
	void genSortName();
	
	int m_flags;
	std::set<int> m_ca;
	std::map<int,int> m_cache;
	virtual ~eDVBService();
	
	eDVBService &operator=(const eDVBService &);
	
	// iStaticServiceInformation
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	
		/* for filtering: */
	int checkFilter(const eServiceReferenceDVB &ref, const eDVBChannelQuery &query);
};

//////////////////

class iDVBChannel;
class iDVBDemux;
class iDVBFrontendParameters;

class iDVBChannelListQuery: public iObject
{
public:
	virtual RESULT getNextResult(eServiceReferenceDVB &ref)=0;
	virtual int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b)=0;
};

class eDVBChannelQuery: public iObject
{
	DECLARE_REF(eDVBChannelQuery);
public:
	enum
	{
		tName,
		tProvider,
		tType,
		tBouquet,
		tSatellitePosition,
		tChannelID,
		tAND,
		tOR
	};
	
	int m_type;
	int m_inverse;
	
	std::string m_string;
	int m_int;
	eDVBChannelID m_channelid;
	
		/* sort is only valid in root, and must be from the enum above. */
	int m_sort;
	std::string m_bouquet_name;
	
	static RESULT compile(ePtr<eDVBChannelQuery> &res, std::string query);
	
	ePtr<eDVBChannelQuery> m_p1, m_p2;
};

class iDVBChannelList: public iObject
{
public:
	virtual RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm)=0;
	virtual RESULT removeChannel(const eDVBChannelID &id)=0;
	
	virtual RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm)=0;
	
	virtual RESULT addService(const eServiceReferenceDVB &service, eDVBService *service)=0;
	virtual RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service)=0;

	virtual RESULT getBouquet(const eServiceReference &ref,  eBouquet* &bouquet)=0;

	virtual RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *query, const eServiceReference &source)=0;
};

class iDVBFrontendParameters: public iObject
{
public:
	virtual RESULT getSystem(int &type) const = 0;
	virtual RESULT getDVBS(eDVBFrontendParametersSatellite &p) const = 0;
	virtual RESULT getDVBC(eDVBFrontendParametersCable &p) const = 0;
	virtual RESULT getDVBT(eDVBFrontendParametersTerrestrial &p) const = 0;
	
	virtual RESULT calculateDifference(const iDVBFrontendParameters *parm, int &diff) const = 0;
	virtual RESULT getHash(unsigned long &hash) const = 0;
};

#define MAX_DISEQC_LENGTH  16

class eDVBDiseqcCommand
{
public:
	int len;
	__u8 data[MAX_DISEQC_LENGTH];
#if HAVE_DVB_API_VERSION < 3
	int tone;
	int voltage;
#endif
};

class iDVBSatelliteEquipmentControl;
class eSecCommandList;

class iDVBFrontend: public iObject
{
public:
	enum {
		feSatellite, feCable, feTerrestrial
	};
	virtual RESULT getFrontendType(int &type)=0;
	virtual RESULT tune(const iDVBFrontendParameters &where)=0;
	virtual RESULT connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)=0;
	enum {
		stateIdle = 0,
		stateTuning = 1,
		stateFailed = 2,
		stateLock = 3,
		stateLostLock = 4,
	};
	virtual RESULT getState(int &state)=0;
	enum {
		toneOff, toneOn
	};
	virtual RESULT setTone(int tone)=0;
	enum {
		voltageOff, voltage13, voltage18
	};
	virtual RESULT setVoltage(int voltage)=0;
	virtual RESULT sendDiseqc(const eDVBDiseqcCommand &diseqc)=0;
	virtual RESULT sendToneburst(int burst)=0;
	virtual RESULT setSEC(iDVBSatelliteEquipmentControl *sec)=0;
	virtual RESULT setSecSequence(const eSecCommandList &list)=0;
	virtual RESULT getData(int num, int &data)=0;
	virtual RESULT setData(int num, int val)=0;
	
		/* 0 means: not compatible. other values are a priority. */
	virtual int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm)=0;
};

class iDVBSatelliteEquipmentControl: public iObject
{
public:
	virtual RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat)=0;
	virtual int canTune(const eDVBFrontendParametersSatellite &feparm, iDVBFrontend *fe, int frontend_id)=0;
};

struct eDVBCIRouting
{
	int enabled;
};

class iDVBChannel: public iObject
{
public:
	enum
	{
		state_idle,        /* not yet tuned */
		state_tuning,      /* currently tuning (first time) */
		state_failed,      /* tuning failed. */
		state_unavailable, /* currently unavailable, will be back without further interaction */
		state_ok,          /* ok */
		state_release      /* channel is being shut down. */
	};
	virtual RESULT connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)=0;
	virtual RESULT getState(int &state)=0;
	
		/* demux capabilities */
	enum
	{
		capDecode = 1,
		/* capCI = 2 */
	};
	virtual RESULT setCIRouting(const eDVBCIRouting &routing)=0;
	virtual RESULT getDemux(ePtr<iDVBDemux> &demux, int cap=0)=0;
	
		/* direct frontend access for raw channels and/or status inquiries. */
	virtual RESULT getFrontend(ePtr<iDVBFrontend> &frontend)=0;
	
		/* use count handling */
	virtual void AddUse() = 0;
	virtual void ReleaseUse() = 0;
};

	/* signed, so we can express deltas. */
typedef long long pts_t;

class iDVBPVRChannel: public iDVBChannel
{
public:
	enum
	{
		state_eof = state_release + 1  /* end-of-file reached. */
	};
	
		/* FIXME: there are some very ugly buffer-end and ... related problems */
		/* so this is VERY UGLY. */
	virtual RESULT playFile(const char *file) = 0;
	
	virtual RESULT getLength(pts_t &pts) = 0;
	virtual RESULT getCurrentPosition(pts_t &pos) = 0;
	virtual RESULT seekTo(int relative, pts_t &pts) = 0;
	virtual RESULT seekToPosition(const off_t &pts) = 0;
};

class iDVBSectionReader;
class iDVBTSRecorder;
class iTSMPEGDecoder;

class iDVBDemux: public iObject
{
public:
	virtual RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)=0;
	virtual RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder)=0;
	virtual RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader)=0;
	virtual RESULT getSTC(pts_t &pts)=0;
	virtual RESULT getCADemuxID(uint8_t &id)=0;
	virtual RESULT flush()=0;
};

class iTSMPEGDecoder: public iObject
{
public:
	enum { pidDisabled = -1 };
		/** Set Displayed Video PID */
	virtual RESULT setVideoPID(int vpid)=0;

	enum { af_MPEG, af_AC3, af_DTS };
		/** Set Displayed Audio PID and type */
	virtual RESULT setAudioPID(int apid, int type)=0;

		/** Set Sync mode to PCR */
	virtual RESULT setSyncPCR(int pcrpid)=0;
	enum { sm_Audio, sm_Video };
		/** Set Sync mode to either audio or video master */
	virtual RESULT setSyncMaster(int who)=0;
	
		/** Apply settings */
	virtual RESULT start()=0;
	
		/** Freeze frame. Either continue decoding (without display) or halt. */
	virtual RESULT freeze(int cont)=0;
		/** Continue after freeze. */
	virtual RESULT unfreeze()=0;
	
		// stop on .. Picture
	enum { spm_I, spm_Ref, spm_Any };
		/** Stop on specific decoded picture. For I-Frame display. */
	virtual RESULT setSinglePictureMode(int when)=0;
	
	enum { pkm_B, pkm_PB };
		/** Fast forward by skipping either B or P/B pictures */
	virtual RESULT setPictureSkipMode(int what)=0;
	
		/** Slow Motion by repeating pictures */
	virtual RESULT setSlowMotion(int repeat)=0;
	
	enum { zoom_Normal, zoom_PanScan, zoom_Letterbox, zoom_Fullscreen };
		/** Set Zoom. mode *must* be fitting. */
	virtual RESULT setZoom(int what)=0;
};

#endif
