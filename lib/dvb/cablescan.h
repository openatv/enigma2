#ifndef _lib_dvb_cablescan_h
#define _lib_dvb_cablescan_h

#include <dvbsi++/network_information_section.h>
#include <dvbsi++/service_description_section.h>

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/esection.h>

class eCableScan: public sigc::trackable, public iObject
{
	DECLARE_REF(eCableScan);

#ifndef SWIG
	eUsePtr<iDVBChannel> m_channel;
	ePtr<iDVBDemux> m_demux;
	bool originalNumbering;
	bool hdList;
	unsigned int initialFrequency;
	unsigned int initialSymbolRate;
	int initialModulation;
	std::string providerName, bouquetFilename;
	int networkId;
	std::map<std::string, int> providerNames;

	std::list<ePtr<eDVBFrontendParameters> > scanChannels;
	ePtr<iDVBFrontendParameters> currentScanChannel;
	int totalChannels;

	std::map<eServiceReferenceDVB, ePtr<eDVBService> > newServices;

	std::map<int, int> serviceIdToChannelId, serviceIdToHDChannelId;
	std::map<int, eServiceReferenceDVB> numberedServiceRefs, numberedRadioServiceRefs;

	ePtr<eTable<NetworkInformationSection> > m_NIT;
	ePtr<eTable<ServiceDescriptionSection> > m_SDT;

	void NITReady(int error);
	void SDTReady(int error);

	int nextChannel();
	void parseNIT();
	void parseSDT();

	void fillBouquet(eBouquet *bouquet, std::map<int, eServiceReferenceDVB> &numbered_channels);
	void createBouquets();
#endif /* no SWIG */

public:
	eCableScan(int networkid, unsigned int frequency, unsigned int symbolrate, int modulation, bool originalnumbering = false, bool hdlist = false);
	~eCableScan();

	void start(int frontendid = 0);

	PSignal1<void, int> scanProgress;
	PSignal1<void, int> scanCompleted;
};

#endif
