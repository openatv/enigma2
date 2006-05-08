#ifndef __lib_dvb_scan_h
#define __lib_dvb_scan_h

#include <dvbsi++/network_information_section.h>
#include <dvbsi++/service_description_section.h>
#include <dvbsi++/bouquet_association_section.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/db.h>

class eDVBScan: public Object, public iObject
{
DECLARE_REF(eDVBScan);
private:
		/* chid helper functions: */
		
		/* heuristically determine if onid/tsid is valid */
	int isValidONIDTSID(int orbital_position, eOriginalNetworkID onid, eTransportStreamID tsid);
		/* build dvb namespace */
	eDVBNamespace buildNamespace(eOriginalNetworkID onid, eTransportStreamID tsid, unsigned long hash);
	
		/* scan resources */	
	eUsePtr<iDVBChannel> m_channel;
	ePtr<iDVBDemux> m_demux;
	
		/* infrastructure */
	void stateChange(iDVBChannel *);
	ePtr<eConnection> m_stateChanged_connection;

		/* state handling */	
	RESULT nextChannel();
	
	RESULT startFilter();	
	enum { readySDT=1, readyNIT=2, readyBAT=4,
	       validSDT=8, validNIT=16, validBAT=32};

		/* scan state variables */
	int m_channel_state;
	int m_ready, m_ready_all;
	
	std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> > m_new_channels;
	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_new_services;
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator m_last_service;
	
	std::list<ePtr<iDVBFrontendParameters> > m_ch_toScan, m_ch_scanned, m_ch_unavailable;
	ePtr<iDVBFrontendParameters> m_ch_current;
	eDVBChannelID m_chid_current;
	
	ePtr<eTable<ServiceDescriptionSection> > m_SDT;
	ePtr<eTable<NetworkInformationSection> > m_NIT;
	ePtr<eTable<BouquetAssociationSection> > m_BAT;
	
	void SDTready(int err);
	void NITready(int err);
	void BATready(int err);
	
	void addKnownGoodChannel(const eDVBChannelID &chid, iDVBFrontendParameters *feparm);
	void addChannelToScan(const eDVBChannelID &chid, iDVBFrontendParameters *feparm);
	int  sameChannel(iDVBFrontendParameters *ch1, iDVBFrontendParameters *ch2) const;
	
	void channelDone();
	
	Signal1<void,int> m_event;
	RESULT processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionSection &sdt);
	
	int m_flags;
public:
	eDVBScan(iDVBChannel *channel);
	~eDVBScan();
	
	enum { scanNetworkSearch = 1, scanSearchBAT = 2, scanRemoveServices = 4, scanDontRemoveFeeds=8 };
	void start(const eSmartPtrList<iDVBFrontendParameters> &known_transponders, int flags);

	enum { evtUpdate, evtNewService, evtFinish, evtFail };
	RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection);
	void insertInto(iDVBChannelList *db);
	
	void getStats(int &transponders_done, int &transponders_total, int &services);
	void getLastServiceName(std::string &name);
};

#endif
