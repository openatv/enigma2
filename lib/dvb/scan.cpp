#include <lib/dvb/idvb.h>
#include <lib/dvb_si/sdt.h>
#include <lib/dvb_si/nit.h>
#include <lib/dvb_si/bat.h>
#include <lib/dvb_si/descriptor_tag.h>
#include <lib/dvb_si/service_descriptor.h>
#include <lib/dvb_si/satellite_delivery_system_descriptor.h>
#include <lib/dvb_si/ca_identifier_descriptor.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/scan.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eerror.h>
#include <errno.h>

#define SCAN_eDebug(x...)
#define SCAN_eDebugNoNewLine(x...)

DEFINE_REF(eDVBScan);

eDVBScan::eDVBScan(iDVBChannel *channel): m_channel(channel)
{
	if (m_channel->getDemux(m_demux))
		SCAN_eDebug("scan: failed to allocate demux!");
	m_channel->connectStateChange(slot(*this, &eDVBScan::stateChange), m_stateChanged_connection);
}

eDVBScan::~eDVBScan()
{
}

int eDVBScan::isValidONIDTSID(eOriginalNetworkID onid, eTransportStreamID tsid)
{
	switch (onid.get())
	{
	case 0:
	case 0xFFFF:
	case 0x1111:
		return 0;
	case 1:
		return tsid>1;
	case 0x00B1:
		return tsid != 0x00B0;
	case 0x0002:
		return tsid != 0x07E8;
	default:
		return 1;
	}
}

eDVBNamespace eDVBScan::buildNamespace(eOriginalNetworkID onid, eTransportStreamID tsid, unsigned long hash)
{
		// on valid ONIDs, ignore frequency ("sub network") part
	if (isValidONIDTSID(onid, tsid))
		hash &= ~0xFFFF;
	return eDVBNamespace(hash);
}

void eDVBScan::stateChange(iDVBChannel *ch)
{
	int state;
	if (ch->getState(state))
		return;
	if (m_channel_state == state)
		return;
	
	if (state == iDVBChannel::state_ok)
	{
		startFilter();
		m_channel_state = state;
	} else if (state == iDVBChannel::state_unavailable)
	{
		m_ch_unavailable.push_back(m_ch_current);
		nextChannel();
	}
}

RESULT eDVBScan::nextChannel()
{
	ePtr<iDVBFrontend> fe;

	m_SDT = 0; m_BAT = 0; m_NIT = 0;

	m_ready = readyBAT;
	if (m_ch_toScan.empty())
	{
		eDebug("no channels left to scan.");
		eDebug("%d channels scanned, %d were unavailable.", 
				m_ch_scanned.size(), m_ch_unavailable.size());
		eDebug("%d channels in database.", m_new_channels.size());
		m_event(evtFinish);
		return -ENOENT;
	}
	
	m_ch_current = m_ch_toScan.front();
	m_ch_toScan.pop_front();
	
	if (m_channel->getFrontend(fe))
		return -ENOTSUP;
	
	m_channel_state = iDVBChannel::state_idle;
	if (fe->tune(*m_ch_current))
		return -EINVAL;
		
	m_event(evtUpdate);
	return 0;
}

RESULT eDVBScan::startFilter()
{
	assert(m_demux);
	
	m_SDT = new eTable<ServiceDescriptionTable>();
	if (m_SDT->start(m_demux, eDVBSDTSpec()))
		return -1;
	CONNECT(m_SDT->tableReady, eDVBScan::SDTready);

	m_NIT = 0;
	m_NIT = new eTable<NetworkInformationTable>();
	if (m_NIT->start(m_demux, eDVBNITSpec()))
		return -1;
	CONNECT(m_NIT->tableReady, eDVBScan::NITready);
	
	m_BAT = new eTable<BouquetAssociationTable>();
	if (m_BAT->start(m_demux, eDVBBATSpec()))
		return -1;
	CONNECT(m_BAT->tableReady, eDVBScan::BATready);
	
	return 0;
}

void eDVBScan::SDTready(int err)
{
	SCAN_eDebug("got sdt");
	m_ready |= readySDT;
	if (!err)
		m_ready |= validSDT;
	channelDone();
}

void eDVBScan::NITready(int err)
{
	SCAN_eDebug("got nit, err %d", err);
	m_ready |= readyNIT;
	if (!err)
		m_ready |= validNIT;
	channelDone();
}

void eDVBScan::BATready(int err)
{
	SCAN_eDebug("got bat");
	m_ready |= readyBAT;
	if (!err)
		m_ready |= validBAT;
	channelDone();
}

void eDVBScan::addChannel(const eDVBChannelID &chid, iDVBFrontendParameters *feparm)
{
		/* add it to the list of known channels. */
	if (chid)
		m_new_channels.insert(std::pair<eDVBChannelID,ePtr<iDVBFrontendParameters> >(chid, feparm));
	
		/* check if we don't already have that channel ... */
		
		/* ... in the list of channels to scan */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_toScan.begin()); i != m_ch_toScan.end(); ++i)
		if (sameChannel(*i, feparm))
			return;

		/* ... in the list of successfully scanned channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_scanned.begin()); i != m_ch_scanned.end(); ++i)
		if (sameChannel(*i, feparm))
			return;
		
		/* ... in the list of unavailable channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_unavailable.begin()); i != m_ch_unavailable.end(); ++i)
		if (sameChannel(*i, feparm))
			return;

		/* ... on the current channel */
	if (sameChannel(m_ch_current, feparm))
		return;

		/* otherwise, add it to the todo list. */
	m_ch_toScan.push_back(feparm);
}

int eDVBScan::sameChannel(iDVBFrontendParameters *ch1, iDVBFrontendParameters *ch2) const
{
	int diff;
	if (ch1->calculateDifference(ch2, diff))
		return 0;
	if (diff < 4000) // more than 4mhz difference?
		return 1;
	return 0;
}

void eDVBScan::channelDone()
{
	if (m_ready & validSDT)
	{
		unsigned long hash = 0;
		m_ch_current->getHash(hash);
		
		eDVBNamespace dvbnamespace = buildNamespace(
			(**m_SDT->getSections().begin()).getOriginalNetworkId(),
			(**m_SDT->getSections().begin()).getTransportStreamId(),
			hash);
		
		SCAN_eDebug("SDT: ");
		ServiceDescriptionTableConstIterator i;
		for (i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
			processSDT(dvbnamespace, **i);
		m_ready &= ~validSDT;
	}
	
	if (m_ready & validNIT)
	{
		SCAN_eDebug("dumping NIT");
		NetworkInformationTableConstIterator i;
		for (i = m_NIT->getSections().begin(); i != m_NIT->getSections().end(); ++i)
		{
			const TransportStreamInfoVector &tsinfovec = *(*i)->getTsInfo();
			
			for (TransportStreamInfoConstIterator tsinfo(tsinfovec.begin()); 
				tsinfo != tsinfovec.end(); ++tsinfo)
			{
				SCAN_eDebug("TSID: %04x ONID: %04x", (*tsinfo)->getTransportStreamId(),
					(*tsinfo)->getOriginalNetworkId());
				
				eOriginalNetworkID onid = (*tsinfo)->getOriginalNetworkId();
				eTransportStreamID tsid = (*tsinfo)->getTransportStreamId();
				
				for (DescriptorConstIterator desc = (*tsinfo)->getDescriptors()->begin();
						desc != (*tsinfo)->getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
//					case SERVICE_LIST_DESCRIPTOR:
					case SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						SatelliteDeliverySystemDescriptor &d = (SatelliteDeliverySystemDescriptor&)**desc;
						SCAN_eDebug("%d kHz, %d%d%d.%d%c %s MOD:%d %d symb/s, fec %d", 
								d.getFrequency(), 
								(d.getOrbitalPosition()>>12)&0xF,
								(d.getOrbitalPosition()>>8)&0xF,
								(d.getOrbitalPosition()>>4)&0xF,
								d.getOrbitalPosition()&0xF, d.getWestEastFlag()?'E':'W',
								d.getPolarization() ? "hor" : "vert",
								d.getModulation(), d.getSymbolRate(), d.getFecInner());
						
							/* some sanity checking: below 100MHz is invalid */
						if (d.getFrequency() < 10000)
							break;
						
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersSatellite sat;
						sat.set(d);
						feparm->setDVBS(sat);
						unsigned long hash=0;
						feparm->getHash(hash);
						
						eDVBNamespace ns = buildNamespace(onid, tsid, hash);

						addChannel(
								eDVBChannelID(ns, tsid, onid),
								feparm);
						break;
					}
					default:
						SCAN_eDebug("descr<%x>", (*desc)->getTag());
						break;
					}
				}
				
			}
		}
		m_ready &= ~validNIT;
	}
	
	if ((m_ready  & readyAll) != readyAll)
		return;
	SCAN_eDebug("channel done!");
	m_ch_scanned.push_back(m_ch_current);
	nextChannel();
}

void eDVBScan::start(const std::list<ePtr<iDVBFrontendParameters> > &known_transponders)
{
	m_ch_toScan.clear();
	m_ch_scanned.clear();
	m_ch_unavailable.clear();
	m_new_channels.clear();
	m_new_services.clear();
	m_ch_toScan.insert(m_ch_toScan.end(), known_transponders.begin(), known_transponders.end());
	nextChannel();
}

void eDVBScan::insertInto(iDVBChannelList *db)
{
	for (std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> >::const_iterator 
			ch(m_new_channels.begin()); ch != m_new_channels.end(); ++ch)
		db->addChannelToList(ch->first, ch->second);
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::const_iterator
		service(m_new_services.begin()); service != m_new_services.end(); ++service)
	{
		ePtr<eDVBService> dvb_service;
		if (!db->getService(service->first, dvb_service))
			*dvb_service = *service->second;
		else
			db->addService(service->first, service->second);
	}
}

RESULT eDVBScan::processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionTable &sdt)
{
	const ServiceDescriptionVector &services = *sdt.getDescriptions();
	SCAN_eDebug("ONID: %04x", sdt.getOriginalNetworkId());
	eDVBChannelID chid(dvbnamespace, sdt.getTransportStreamId(), sdt.getOriginalNetworkId());
	
	for (ServiceDescriptionConstIterator s(services.begin()); s != services.end(); ++s)
	{
		SCAN_eDebugNoNewLine("SID %04x: ", (*s)->getServiceId());

		eServiceReferenceDVB ref;
		ePtr<eDVBService> service = new eDVBService;
		
		ref.set(chid);
		ref.setServiceID((*s)->getServiceId());

		for (DescriptorConstIterator desc = (*s)->getDescriptors()->begin();
				desc != (*s)->getDescriptors()->end(); ++desc)
			if ((*desc)->getTag() == SERVICE_DESCRIPTOR)
				ref.setServiceType(((ServiceDescriptor&)**desc).getServiceType());
		
		for (DescriptorConstIterator desc = (*s)->getDescriptors()->begin();
				desc != (*s)->getDescriptors()->end(); ++desc)
		{
			switch ((*desc)->getTag())
			{
			case SERVICE_DESCRIPTOR:
			{
				ServiceDescriptor &d = (ServiceDescriptor&)**desc;
				SCAN_eDebug("name '%s', provider_name '%s'", d.getServiceName().c_str(), d.getServiceProviderName().c_str());
				service->m_service_name = d.getServiceName();
				service->m_provider_name = d.getServiceProviderName();
				break;
			}
			case CA_IDENTIFIER_DESCRIPTOR:
			{
				CaIdentifierDescriptor &d = (CaIdentifierDescriptor&)**desc;
				const CaSystemIdVector &caids = *d.getCaSystemIds();
				SCAN_eDebugNoNewLine("CA ");
				for (CaSystemIdVector::const_iterator i(caids.begin()); i != caids.end(); ++i)
				{
					SCAN_eDebugNoNewLine("%04x ", *i);
					service->m_ca.insert(*i);
				}
				SCAN_eDebug("");
				break;
			}
			default:
				SCAN_eDebug("descr<%x>", (*desc)->getTag());
				break;
			}
		}
		
		m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));		
	}
	return 0;
}

RESULT eDVBScan::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}

void eDVBScan::getStats(int &transponders_done, int &transponders_total, int &services)
{
	transponders_done = m_ch_scanned.size() + m_ch_unavailable.size();
	transponders_total = m_ch_toScan.size() + transponders_done;
	services = m_new_services.size();
}
