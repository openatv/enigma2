#ifndef __lib_dvb_scan_h
#define __lib_dvb_scan_h

#include <lib/dvb_si/nit.h>
#include <lib/dvb_si/sdt.h>
#include <lib/dvb_si/bat.h>
#include <lib/dvb/db.h>

class eDVBScan: public Object, public iObject
{
DECLARE_REF;
private:
		/* chid helper functions: */
		
		/* heuristically determine if onid/tsid is valid */
	int isValidONIDTSID(eOriginalNetworkID onid, eTransportStreamID tsid);
		/* build dvb namespace */
	eDVBNamespace buildNamespace(eOriginalNetworkID onid, eTransportStreamID tsid, unsigned long hash);
	
		/* scan resources */	
	ePtr<iDVBChannel> m_channel;
	ePtr<iDVBDemux> m_demux;
	
		/* infrastructure */
	void stateChange(iDVBChannel *);
	ePtr<eConnection> m_stateChanged_connection;

		/* state handling */	
	RESULT nextChannel();
	
	RESULT startFilter();	
	enum { readySDT=1, readyNIT=2, readyBAT=4, readyAll=7,
	       validSDT=8, validNIT=16, validBAT=32};

		/* scan state variables */
	int m_channel_state;
	int m_ready;
	
	std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> > m_new_channels;
	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_new_services;
	
	std::list<ePtr<iDVBFrontendParameters> > m_ch_toScan, m_ch_scanned, m_ch_unavailable;
	ePtr<iDVBFrontendParameters> m_ch_current;
	
	ePtr<eTable<ServiceDescriptionTable> > m_SDT;
	ePtr<eTable<NetworkInformationTable> > m_NIT;
	ePtr<eTable<BouquetAssociationTable> > m_BAT;
	
	void SDTready(int err);
	void NITready(int err);
	void BATready(int err);
	
	void addChannel(const eDVBChannelID &chid, iDVBFrontendParameters *feparm);
	int  sameChannel(iDVBFrontendParameters *ch1, iDVBFrontendParameters *ch2) const;
	
	void channelDone();
	
	Signal1<void,int> m_event;
	RESULT processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionTable &sdt);
public:
	eDVBScan(iDVBChannel *channel);
	~eDVBScan();
	
	void start(const std::list<ePtr<iDVBFrontendParameters> > &known_transponders);

	enum { evtUpdate, evtFinish };
  RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection);
	void insertInto(eDVBDB *db);
};

#endif
