#ifndef __dvb_idvb_h
#define __dvb_idvb_h

#ifndef SWIG

#if HAVE_DVB_API_VERSION < 3
#include <ost/frontend.h>
#define FRONTENDPARAMETERS FrontendParameters
#else
#include <linux/dvb/frontend.h>
#include <linux/dvb/video.h>
#define FRONTENDPARAMETERS struct dvb_frontend_parameters
#endif
#include <lib/dvb/frontendparms.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/base/elock.h>
#include <lib/service/service.h>
#include <libsig_comp.h>
#include <connection.h>

#if defined(__GNUC__) && ((__GNUC__ == 3 && __GNUC_MINOR__ >= 1) || __GNUC__ == 4 )  // check if gcc version >= 3.1
#include <ext/slist>
#define CAID_LIST __gnu_cxx::slist<uint16_t>
#else
#include <slist>
#define CAID_LIST std::slist<uint16_t>
#endif

#ifndef DMX_FILTER_SIZE
#define DMX_FILTER_SIZE   16
#endif

struct eDVBSectionFilterMask
{
	int pid;
		/* mode is 0 for positive, 1 for negative filtering */
	__u8 data[DMX_FILTER_SIZE], mask[DMX_FILTER_SIZE], mode[DMX_FILTER_SIZE];
	enum {
		rfCRC=1,
		rfNoAbort=2
	};
	int flags;
};

struct eDVBTableSpec
{
	int pid, tid, tidext, tid_mask, tidext_mask;
	int version;
	int timeout;        /* timeout in ms */
	enum
	{
		tfInOrder=1,
		/*
			tfAnyVersion      filter ANY version
			0                 filter all EXCEPT given version (negative filtering)
			tfThisVersion     filter only THIS version
		*/
		tfAnyVersion=2,
		tfThisVersion=4,
		tfHaveTID=8,
		tfHaveTIDExt=16,
		tfCheckCRC=32,
		tfHaveTimeout=64,
		tfHaveTIDMask=128,
		tfHaveTIDExtMask=256
	};
	int flags;
};

struct eBouquet
{
	std::string m_bouquet_name;
	std::string m_filename;  // without path.. just name
	typedef std::list<eServiceReference> list;
	list m_services;
// the following five methods are implemented in db.cpp
	RESULT flushChanges();
	RESULT addService(const eServiceReference &, eServiceReference before=eServiceReference());
	RESULT removeService(const eServiceReference &);
	RESULT moveService(const eServiceReference &, unsigned int);
	RESULT setListName(const std::string &name);
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

	eServiceID getParentServiceID() const { return eServiceID(data[5]); }
	void setParentServiceID( eServiceID sid ) { data[5]=sid.get(); }

	eTransportStreamID getParentTransportStreamID() const { return eTransportStreamID(data[6]); }
	void setParentTransportStreamID( eTransportStreamID tsid ) { data[6]=tsid.get(); }

	eServiceReferenceDVB getParentServiceReference() const
	{
		eServiceReferenceDVB tmp(*this);
		if (data[5] && data[6])
		{
			tmp.data[1] = data[5];
			tmp.data[2] = data[6];
			tmp.data[5] = tmp.data[6] = 0;
		}
		else
			tmp.type = idInvalid;
		return tmp;
	}

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

	eServiceReferenceDVB(const std::string &string)
		:eServiceReference(string)
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
	int *m_cache;
	void initCache();
	void copyCache(int *source);
public:
	enum cacheID
	{
		cVPID, cAPID, cTPID, cPCRPID, cAC3PID,
		cVTYPE, cACHANNEL, cAC3DELAY, cPCMDELAY,
		cSUBTITLE, cacheMax
	};

	int getCacheEntry(cacheID);
	void setCacheEntry(cacheID, int);

	bool cacheEmpty();

	eDVBService();
		/* m_service_name_sort is uppercase, with special chars removed, to increase sort performance. */
	std::string m_service_name, m_service_name_sort;
	std::string m_provider_name;
	
	void genSortName();

	int m_flags;
	enum
	{
		dxNoSDT=1,    // don't get SDT
//nyi	dxDontshow=2,
		dxNoDVB=4,  // dont use PMT for this service ( use cached pids )
		dxHoldName=8,
		dxNewFound=64,
	};

	bool usePMT() const { return !(m_flags & dxNoDVB); }

	CAID_LIST m_ca;

	virtual ~eDVBService();
	
	eDVBService &operator=(const eDVBService &);
	
	// iStaticServiceInformation
	RESULT getName(const eServiceReference &ref, std::string &name);
	RESULT getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &ptr, time_t start_time);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore);
	PyObject *getInfoObject(const eServiceReference &ref, int);  // implemented in lib/service/servicedvb.h

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
		tOR,
		tAny,
		tFlags
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
	virtual RESULT removeService(const eServiceReference &service)=0;
	virtual RESULT removeServices(eDVBChannelID chid=eDVBChannelID(), unsigned int orb_pos=0xFFFFFFFF)=0;
	virtual RESULT removeServices(int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF)=0;
	virtual RESULT addFlag(const eServiceReference &service, unsigned int flagmask=0xFFFFFFFF)=0;
	virtual RESULT removeFlag(const eServiceReference &service, unsigned int flagmask=0xFFFFFFFF)=0;
	virtual RESULT removeFlags(unsigned int flagmask, eDVBChannelID chid=eDVBChannelID(), unsigned int orb_pos=0xFFFFFFFF)=0;
	virtual RESULT removeFlags(unsigned int flagmask, int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF)=0;
	virtual RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm)=0;
	virtual RESULT removeChannel(const eDVBChannelID &id)=0;
	
	virtual RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm)=0;
	
	virtual RESULT addService(const eServiceReferenceDVB &service, eDVBService *service)=0;
	virtual RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service)=0;
	virtual RESULT flush()=0;

	virtual RESULT getBouquet(const eServiceReference &ref,  eBouquet* &bouquet)=0;

	virtual RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *query, const eServiceReference &source)=0;
};

#endif  // SWIG

class iDVBFrontendParameters: public iObject
{
#ifdef SWIG
	iDVBFrontendParameters();
	~iDVBFrontendParameters();
#endif
public:
	virtual RESULT getSystem(int &SWIG_OUTPUT) const = 0;
	virtual RESULT getDVBS(eDVBFrontendParametersSatellite &SWIG_OUTPUT) const = 0;
	virtual RESULT getDVBC(eDVBFrontendParametersCable &SWIG_OUTPUT) const = 0;
	virtual RESULT getDVBT(eDVBFrontendParametersTerrestrial &SWIG_OUTPUT) const = 0;
	
	virtual RESULT calculateDifference(const iDVBFrontendParameters *parm, int &SWIG_OUTPUT, bool exact) const = 0;
	virtual RESULT getHash(unsigned long &SWIG_OUTPUT) const = 0;
};

#define MAX_DISEQC_LENGTH  16

class eDVBDiseqcCommand
{
#ifndef SWIG
public:
#endif
	int len;
	__u8 data[MAX_DISEQC_LENGTH];
#if HAVE_DVB_API_VERSION < 3
	int tone;
	int voltage;
#endif
#ifdef SWIG
public:
#endif
	void setCommandString(const char *str);
};

class iDVBSatelliteEquipmentControl;
class eSecCommandList;

class iDVBFrontend_ENUMS
{
#ifdef SWIG
	iDVBFrontend_ENUMS();
	~iDVBFrontend_ENUMS();
#endif
public:
	enum { feSatellite, feCable, feTerrestrial };
	enum { stateIdle, stateTuning, stateFailed, stateLock, stateLostLock };
	enum { toneOff, toneOn };
	enum { voltageOff, voltage13, voltage18, voltage13_5, voltage18_5 };
	enum { bitErrorRate, signalPower, signalQuality, locked, synced, frontendNumber, signalPowerdB };
};

SWIG_IGNORE(iDVBFrontend);
class iDVBFrontend: public iDVBFrontend_ENUMS, public iObject
{
public:
	virtual RESULT getFrontendType(int &SWIG_OUTPUT)=0;
	virtual RESULT tune(const iDVBFrontendParameters &where)=0;
#ifndef SWIG
	virtual RESULT connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)=0;
#endif
	virtual RESULT getState(int &SWIG_OUTPUT)=0;
	virtual RESULT setTone(int tone)=0;
	virtual RESULT setVoltage(int voltage)=0;
	virtual RESULT sendDiseqc(const eDVBDiseqcCommand &diseqc)=0;
	virtual RESULT sendToneburst(int burst)=0;
#ifndef SWIG
	virtual RESULT setSEC(iDVBSatelliteEquipmentControl *sec)=0;
	virtual RESULT setSecSequence(const eSecCommandList &list)=0;
#endif
	virtual int readFrontendData(int type)=0;
	virtual void getFrontendStatus(SWIG_PYOBJECT(ePyObject) dest)=0;
	virtual void getTransponderData(SWIG_PYOBJECT(ePyObject) dest, bool original)=0;
	virtual void getFrontendData(SWIG_PYOBJECT(ePyObject) dest)=0;
#ifndef SWIG
	virtual RESULT getData(int num, int &data)=0;
	virtual RESULT setData(int num, int val)=0;
		/* 0 means: not compatible. other values are a priority. */
	virtual int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm)=0;
#endif
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iDVBFrontend>, iDVBFrontendPtr);

#ifndef SWIG
class iDVBSatelliteEquipmentControl: public iObject
{
public:
	virtual RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, const eDVBFrontendParametersSatellite &sat, int frontend_id)=0;
	virtual int canTune(const eDVBFrontendParametersSatellite &feparm, iDVBFrontend *fe, int frontend_id)=0;
	virtual void setRotorMoving(bool)=0;
};

struct eDVBCIRouting
{
	int enabled;
};
#endif // SWIG

SWIG_IGNORE(iDVBChannel);
class iDVBChannel: public iObject
{
public:
		/* direct frontend access for raw channels and/or status inquiries. */
	virtual SWIG_VOID(RESULT) getFrontend(ePtr<iDVBFrontend> &SWIG_OUTPUT)=0;
#ifndef SWIG
	enum
	{
		state_idle,        /* not yet tuned */
		state_tuning,      /* currently tuning (first time) */
		state_failed,      /* tuning failed. */
		state_unavailable, /* currently unavailable, will be back without further interaction */
		state_ok,          /* ok */
		state_last_instance, /* just one reference to this channel is left */
		state_release      /* channel is being shut down. */
	};
	virtual RESULT getState(int &SWIG_OUTPUT)=0;

	virtual RESULT getCurrentFrontendParameters(ePtr<iDVBFrontendParameters> &)=0;
	enum 
	{
		evtEOF, evtSOF, evtFailed
	};
	virtual RESULT connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)=0;
	virtual RESULT connectEvent(const Slot2<void,iDVBChannel*,int> &eventChange, ePtr<eConnection> &connection)=0;

		/* demux capabilities */
	enum
	{
		capDecode = 1,
		/* capCI = 2 */
	};
	virtual RESULT setCIRouting(const eDVBCIRouting &routing)=0;
	virtual RESULT getDemux(ePtr<iDVBDemux> &demux, int cap=0)=0;
	
		/* use count handling */
	virtual void AddUse() = 0;
	virtual void ReleaseUse() = 0;
#endif
};
SWIG_TEMPLATE_TYPEDEF(eUsePtr<iDVBChannel>, iDVBChannelPtr);

#ifndef SWIG
	/* signed, so we can express deltas. */
	
typedef long long pts_t;

class iFilePushScatterGather;
class iTSMPEGDecoder;

	/* note that a cue sheet describes the logical positions. thus 
	   everything is specified in pts and not file positions */

	/* implemented in dvb.cpp */
class eCueSheet: public iObject, public Object
{
	DECLARE_REF(eCueSheet);
public:
	eCueSheet();
	
			/* frontend */
	void seekTo(int relative, const pts_t &pts);
	
	void clear();
	void addSourceSpan(const pts_t &begin, const pts_t &end);
	void commitSpans();
	
	void setSkipmode(const pts_t &ratio); /* 90000 is 1:1 */
	void setDecodingDemux(iDVBDemux *demux, iTSMPEGDecoder *decoder);
	
			/* frontend and backend */
	eRdWrLock m_lock;
	
			/* backend */
	enum { evtSeek, evtSkipmode, evtSpanChanged };
	RESULT connectEvent(const Slot1<void, int> &event, ePtr<eConnection> &connection);

	std::list<std::pair<pts_t,pts_t> > m_spans;	/* begin, end */
	std::list<std::pair<int, pts_t> > m_seek_requests; /* relative, delta */
	pts_t m_skipmode_ratio;
	Signal1<void,int> m_event;
	ePtr<iDVBDemux> m_decoding_demux;
	ePtr<iTSMPEGDecoder> m_decoder;
};

class iDVBPVRChannel: public iDVBChannel
{
public:
	enum
	{
		state_eof = state_release + 1  /* end-of-file reached. */
	};
	
		/* FIXME: there are some very ugly buffer-end and ... related problems */
		/* so this is VERY UGLY. 
		
		   ok, it's going to get better. but still...*/
	virtual RESULT playFile(const char *file) = 0;
	virtual void stopFile() = 0;
	
	virtual void setCueSheet(eCueSheet *cuesheet) = 0;
	
	virtual RESULT getLength(pts_t &pts) = 0;
	
		/* we explicitely ask for the decoding demux here because a channel
		   can be shared between multiple decoders.
		*/
	virtual RESULT getCurrentPosition(iDVBDemux *decoding_demux, pts_t &pos, int mode) = 0;
		/* skipping must be done with a cue sheet */
};

class iDVBSectionReader;
class iDVBPESReader;
class iDVBTSRecorder;
class iTSMPEGDecoder;

class iDVBDemux: public iObject
{
public:
	virtual RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)=0;
	virtual RESULT createPESReader(eMainloop *context, ePtr<iDVBPESReader> &reader)=0;
	virtual RESULT createTSRecorder(ePtr<iDVBTSRecorder> &recorder)=0;
	virtual RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader, int primary=1)=0;
	virtual RESULT getSTC(pts_t &pts, int num=0)=0;
	virtual RESULT getCADemuxID(uint8_t &id)=0;
	virtual RESULT flush()=0;
};

#if HAVE_DVB_API_VERSION < 3 && !defined(VIDEO_EVENT_SIZE_CHANGED)
#define VIDEO_EVENT_SIZE_CHANGED 1
#endif

class iTSMPEGDecoder: public iObject
{
public:
	enum { pidDisabled = -1 };
		/** Set Displayed Video PID and type */
	virtual RESULT setVideoPID(int vpid, int type)=0;

	enum { af_MPEG, af_AC3, af_DTS, af_AAC };
		/** Set Displayed Audio PID and type */
	virtual RESULT setAudioPID(int apid, int type)=0;

	enum { ac_left, ac_stereo, ac_right };
		/** Set Displayed Audio Channel */
	virtual RESULT setAudioChannel(int channel)=0;
	virtual int getAudioChannel()=0;

	virtual RESULT setPCMDelay(int delay)=0;
	virtual int getPCMDelay()=0;
	virtual RESULT setAC3Delay(int delay)=0;
	virtual int getAC3Delay()=0;

		/** Set Displayed Videotext PID */
	virtual RESULT setTextPID(int vpid)=0;

		/** Set Sync mode to PCR */
	virtual RESULT setSyncPCR(int pcrpid)=0;
	enum { sm_Audio, sm_Video };
		/** Set Sync mode to either audio or video master */
	virtual RESULT setSyncMaster(int who)=0;

		/** Apply settings with starting video */
	virtual RESULT start()=0;
		/** Apply settings but don't start yet */
	virtual RESULT preroll()=0;

		/** Freeze frame. Either continue decoding (without display) or halt. */
	virtual RESULT freeze(int cont)=0;
		/** Continue after freeze. */
	virtual RESULT unfreeze()=0;

		/** fast forward by skipping frames. 0 is disabled, 2 is twice-the-speed, ... */
	virtual RESULT setFastForward(int skip=0)=0;

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

	virtual RESULT setTrickmode(int what) = 0;

	virtual RESULT getPTS(int what, pts_t &pts) = 0;

	virtual RESULT showSinglePic(const char *filename) = 0;

	virtual RESULT setRadioPic(const std::string &filename) = 0;

	struct videoEvent
	{
		enum { eventUnknown = 0, eventSizeChanged = VIDEO_EVENT_SIZE_CHANGED } type;
		unsigned char aspect;
		unsigned short height;
		unsigned short width;
	};

	virtual RESULT connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &connection) = 0;
};

#endif //SWIG
#endif
