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
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/service/service.h>
#include <libsig_comp.h>
#include <connection.h>

		// bitte KEINE operator int() definieren, sonst bringt das ganze nix!
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
	
	void getChannelID(eDVBChannelID &chid)
	{
		chid = eDVBChannelID(getDVBNamespace(), getTransportStreamID(), getOriginalNetworkID());
	}

	eServiceReferenceDVB()
		:eServiceReference(eServiceReference::idDVB, 0)
	{
	}
};


class iDVBChannel;
class iDVBDemux;
class iDVBFrontendParameters;

class iDVBChannelList: public iObject
{
public:
	virtual RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm)=0;
};

class iDVBResourceManager: public iObject
{
public:
	/*
			solange rumloopen bis eine resource gefunden wurde, die eine frequenz
			tunen will
			
			wenn natuerlich sowas schon vorhanden ist, dann einfach ne ref darauf
			geben. (zwei services auf dem gleichen transponder teilen sich einen
			channel)
	*/
	virtual RESULT setChannelList(iDVBChannelList *list)=0;
	virtual RESULT getChannelList(ePtr<iDVBChannelList> &list)=0;
	virtual RESULT allocateChannel(const eDVBChannelID &channel, ePtr<iDVBChannel> &channel)=0;
	virtual RESULT allocateRawChannel(ePtr<iDVBChannel> &channel)=0;
	virtual RESULT allocatePVRChannel(int caps)=0;
};

class SatelliteDeliverySystemDescriptor;
class CableDeliverySystemDescriptor;
class TerrestrialDeliverySystemDescriptor;

struct eDVBFrontendParametersSatellite
{
	struct Polarisation
	{
		enum {
			Horizontal, Vertical, CircularLeft, CircularRight
		};
	};
	struct Inversion
	{
		enum {
			On, Off, Unknown
		};
	};
	struct FEC
	{
		enum {
			fNone, f1_2, f2_3, f3_4, f5_6, f7_8, fAuto
		};
	};
	unsigned int frequency, symbol_rate;
	int polarisation, fec, inversion, orbital_position;
	
	void set(const SatelliteDeliverySystemDescriptor  &);
};

struct eDVBFrontendParametersCable
{
	unsigned int frequency, symbol_rate;
	int modulation, inversion, fec_inner;
	void set(const CableDeliverySystemDescriptor  &);
};

struct eDVBFrontendParametersTerrestrial
{
	int unknown;
	void set(const TerrestrialDeliverySystemDescriptor  &);
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

struct eDVBDiseqcCommand
{
	int len;
	__u8 data[MAX_DISEQC_LENGTH];
};

class iDVBSatelliteEquipmentControl;

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
		stateLock = 3
	};
	virtual RESULT getState(int &state)=0;
	enum {
		toneOn, toneOff
	};
	virtual RESULT setTone(int tone)=0;
	enum {
		voltageOff, voltage13, voltage18
	};
	virtual RESULT setVoltage(int voltage)=0;
	virtual RESULT sendDiseqc(const eDVBDiseqcCommand &diseqc)=0;
	virtual RESULT setSEC(iDVBSatelliteEquipmentControl *sec)=0;
};

class iDVBSatelliteEquipmentControl: public iObject
{
public:
	virtual RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat)=0;
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
		state_unavailable, /* currently unavailable, will be back without further interaction */
		state_ok           /* ok */
	};
	virtual RESULT connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)=0;
	virtual RESULT getState(int &state)=0;
	enum
	{
		cap_decode,
		cap_ci
	};
	virtual RESULT setCIRouting(const eDVBCIRouting &routing)=0;
	virtual RESULT getDemux(ePtr<iDVBDemux> &demux)=0;
	
		/* direct frontend access for raw channels and/or status inquiries. */
	virtual RESULT getFrontend(ePtr<iDVBFrontend> &frontend)=0;
};

class iDVBSectionReader;
class iTSMPEGDecoder;

class iDVBDemux: public iObject
{
public:
	virtual RESULT createSectionReader(eMainloop *context, ePtr<iDVBSectionReader> &reader)=0;
	virtual RESULT getMPEGDecoder(ePtr<iTSMPEGDecoder> &reader)=0;
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
