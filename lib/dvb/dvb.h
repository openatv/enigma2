#ifndef __dvb_dvb_h
#define __dvb_dvb_h

#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/frontend.h>
#include <connection.h>

class eDVBChannel;

class eDVBResourceManager: public iDVBResourceManager
{
	DECLARE_REF(eDVBResourceManager);
	int avail, busy;
	struct adapter
	{
		eSmartPtrList<eDVBFrontend> fe;
		eSmartPtrList<eDVBDemux> demux;
	};
	std::multimap<eDVBChannelID,eDVBChannel*> m_active_channels;
	ePtr<iDVBChannelList> m_list;
	ePtr<iDVBSatelliteEquipmentControl> m_sec;
	static eDVBResourceManager *instance;
public:
	eDVBResourceManager();
	virtual ~eDVBResourceManager();
	
	static RESULT getInstance(ePtr<eDVBResourceManager> &ptr) { if (instance) { ptr = instance; return 0; } return -1; }
	
	RESULT setChannelList(iDVBChannelList *list);
	RESULT getChannelList(ePtr<iDVBChannelList> &list);
	
	RESULT allocateChannel(const eDVBChannelID &channelid, ePtr<iDVBChannel> &channel);
	RESULT allocateRawChannel(ePtr<iDVBChannel> &channel);
	RESULT allocatePVRChannel(int caps);
	
	RESULT addChannel(const eDVBChannelID &chid, eDVBChannel *ch);
	RESULT removeChannel(const eDVBChannelID &chid, eDVBChannel *ch);
};

class eDVBChannel: public iDVBChannel, public eDVBDemux, public Object
{
	DECLARE_REF(eDVBChannel);
private:
	ePtr<eDVBFrontend> m_frontend;
	ePtr<iDVBFrontendParameters> m_current_frontend_parameters;
	eDVBChannelID m_channel_id;
	Signal1<void,iDVBChannel*> m_stateChanged;
	int m_state;
	ePtr<eDVBResourceManager> m_mgr;
	
	void frontendStateChanged(iDVBFrontend*fe);
	ePtr<eConnection> m_conn_frontendStateChanged;
public:
	eDVBChannel(eDVBResourceManager *mgr, int adapter, int frontend, int demux);
	virtual ~eDVBChannel();

		/* only for managed channels */
	RESULT setChannel(const eDVBChannelID &id);
	
	RESULT connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection);
	RESULT getState(int &state);

	RESULT setCIRouting(const eDVBCIRouting &routing);
	RESULT getDemux(ePtr<iDVBDemux> &demux);
	RESULT getFrontend(ePtr<iDVBFrontend> &frontend);
};

#endif
