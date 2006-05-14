#include <lib/dvb/idvb.h>
#include <dvbsi++/service_description_section.h>
#include <dvbsi++/network_information_section.h>
#include <dvbsi++/bouquet_association_section.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/ca_identifier_descriptor.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/scan.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <errno.h>
#include <set>

#define SCAN_eDebug(x...) eDebug(x)
#define SCAN_eDebugNoNewLine(x...) eDebugNoNewLine(x)

DEFINE_REF(eDVBScan);

eDVBScan::eDVBScan(iDVBChannel *channel)
	:m_channel(channel), m_ready(0), m_flags(0), m_ready_all(readySDT)
	,m_channel_state(iDVBChannel::state_idle)
{
	if (m_channel->getDemux(m_demux))
		SCAN_eDebug("scan: failed to allocate demux!");
	m_channel->connectStateChange(slot(*this, &eDVBScan::stateChange), m_stateChanged_connection);
}

eDVBScan::~eDVBScan()
{
}

int eDVBScan::isValidONIDTSID(int orbital_position, eOriginalNetworkID onid, eTransportStreamID tsid)
{
	switch (onid.get())
	{
	case 0:
	case 0x1111:
		return 0;
	case 1:
		return orbital_position == 192;
	case 0x00B1:
		return tsid != 0x00B0;
	case 0x0002:
		return abs(orbital_position-282) < 6;
	default:
		return onid.get() < 0xFF00;
	}
}

eDVBNamespace eDVBScan::buildNamespace(eOriginalNetworkID onid, eTransportStreamID tsid, unsigned long hash)
{
		// on valid ONIDs, ignore frequency ("sub network") part
	if (isValidONIDTSID((hash >> 16) & 0xFFFF, onid, tsid))
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
	} else if (state == iDVBChannel::state_failed)
	{
		m_ch_unavailable.push_back(m_ch_current);
		nextChannel();
	}
			/* unavailable will timeout, anyway. */
}

RESULT eDVBScan::nextChannel()
{
	ePtr<iDVBFrontend> fe;

	m_SDT = 0; m_BAT = 0; m_NIT = 0;

	m_ready = 0;
	
		/* check what we need */
	m_ready_all = readySDT;
	
	if (m_flags & scanNetworkSearch)
		m_ready_all |= readyNIT;
	
	if (m_flags & scanSearchBAT)
		m_ready_all |= readyBAT;
	
	if (m_ch_toScan.empty())
	{
//		SCAN_eDebug("no channels left to scan.");
//		SCAN_eDebug("%d channels scanned, %d were unavailable.", 
//				m_ch_scanned.size(), m_ch_unavailable.size());
//		SCAN_eDebug("%d channels in database.", m_new_channels.size());
		m_event(evtFinish);
		return -ENOENT;
	}
	
	m_ch_current = m_ch_toScan.front();
	
	m_ch_toScan.pop_front();
	
	if (m_channel->getFrontend(fe))
	{
		m_event(evtFail);
		return -ENOTSUP;
	}

	int fetype;
	fe->getFrontendType(fetype);
	if ( fetype == iDVBFrontend::feSatellite)
	{
		eDVBFrontendParametersSatellite p;
		m_ch_current->getDVBS(p);
		m_chid_current = eDVBChannelID(p.orbital_position << 16, -1, -1);
	}
	else
		m_chid_current = eDVBChannelID();

	m_channel_state = iDVBChannel::state_idle;
	if (fe->tune(*m_ch_current))
	{
		return nextChannel();
		m_event(evtFail);
		return -EINVAL;
	}
		
	m_event(evtUpdate);
	return 0;
}

RESULT eDVBScan::startFilter()
{
	assert(m_demux);
	
			/* only start required filters filter */
	
	m_SDT = 0;

	if (m_ready_all & readySDT)
	{
		m_SDT = new eTable<ServiceDescriptionSection>();
		if (m_SDT->start(m_demux, eDVBSDTSpec()))
			return -1;
		CONNECT(m_SDT->tableReady, eDVBScan::SDTready);
	}

	m_NIT = 0;
	if (m_ready_all & readyNIT)
	{
		m_NIT = new eTable<NetworkInformationSection>();
		if (m_NIT->start(m_demux, eDVBNITSpec()))
			return -1;
		CONNECT(m_NIT->tableReady, eDVBScan::NITready);
	}

	m_BAT = 0;
	if (m_ready_all & readyBAT)
	{
		m_BAT = new eTable<BouquetAssociationSection>();
		if (m_BAT->start(m_demux, eDVBBATSpec()))
			return -1;
		CONNECT(m_BAT->tableReady, eDVBScan::BATready);
	}
	
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

void eDVBScan::addKnownGoodChannel(const eDVBChannelID &chid, iDVBFrontendParameters *feparm)
{
		/* add it to the list of known channels. */
	if (chid)
		m_new_channels.insert(std::pair<eDVBChannelID,ePtr<iDVBFrontendParameters> >(chid, feparm));
}

void eDVBScan::addChannelToScan(const eDVBChannelID &chid, iDVBFrontendParameters *feparm)
{
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
	m_ch_toScan.push_front(feparm); // better.. then the rotor not turning wild from east to west :)
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

		// m_ch_current is not set, when eDVBScan is just used for a SDT update
		if (!m_ch_current)
			m_channel->getCurrentFrontendParameters(m_ch_current);

		m_ch_current->getHash(hash);
		
		eDVBNamespace dvbnamespace = buildNamespace(
			(**m_SDT->getSections().begin()).getOriginalNetworkId(),
			(**m_SDT->getSections().begin()).getTransportStreamId(),
			hash);
		
		SCAN_eDebug("SDT: ");
		std::vector<ServiceDescriptionSection*>::const_iterator i;
		for (i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
			processSDT(dvbnamespace, **i);
		m_ready &= ~validSDT;
	}
	
	if (m_ready & validNIT)
	{
		SCAN_eDebug("dumping NIT");
		std::vector<NetworkInformationSection*>::const_iterator i;
		for (i = m_NIT->getSections().begin(); i != m_NIT->getSections().end(); ++i)
		{
			const TransportStreamInfoList &tsinfovec = *(*i)->getTsInfo();
			
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
					case CABLE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						CableDeliverySystemDescriptor &d = (CableDeliverySystemDescriptor&)**desc;
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersCable cable;
						cable.set(d);
						feparm->setDVBC(cable);

						unsigned long hash=0;
						feparm->getHash(hash);
						eDVBNamespace ns = buildNamespace(onid, tsid, hash);

						addChannelToScan(
							eDVBChannelID(ns, tsid, onid),
							feparm);
						break;
					}
					case TERRESTRIAL_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						TerrestrialDeliverySystemDescriptor &d = (TerrestrialDeliverySystemDescriptor&)**desc;
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersTerrestrial terr;
						terr.set(d);
						feparm->setDVBT(terr);

						unsigned long hash=0;
						feparm->getHash(hash);
						eDVBNamespace ns = buildNamespace(onid, tsid, hash);

						addChannelToScan(
							eDVBChannelID(ns, tsid, onid),
							feparm);
						break;
					}
					case SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						SatelliteDeliverySystemDescriptor &d = (SatelliteDeliverySystemDescriptor&)**desc;
						if (d.getFrequency() < 10000)
							break;
						
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersSatellite sat;
						sat.set(d);
						feparm->setDVBS(sat);
						unsigned long hash=0;
						feparm->getHash(hash);
						
						eDVBNamespace ns = buildNamespace(onid, tsid, hash);
						
						if ( m_chid_current.dvbnamespace.get() != -1 &&
							((ns.get() ^ m_chid_current.dvbnamespace.get()) & 0xFFFF0000))
							SCAN_eDebug("dropping this transponder, it's on another satellite.");
						else
						{
							addChannelToScan(
									eDVBChannelID(ns, tsid, onid),
									feparm);
						}
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
	
	if ((m_ready  & m_ready_all) != m_ready_all)
		return;
	SCAN_eDebug("channel done!");
	
		/* if we had services on this channel, we declare
		   this channels as "known good". add it.
		   
		   (TODO: not yet implemented)
		   a NIT entry could have possible overridden
		   our frontend data with more exact data.
		   
		   (TODO: not yet implemented)
		   the tuning process could have lead to more
		   exact data than the user entered.
		   
		   The channel id was probably corrected
		   by the data written in the SDT. this is
		   important, as "initial transponder lists"
		   usually don't have valid CHIDs (and that's
		   good).
		   
		   These are the reasons for adding the transponder
		   here, and not before.
		*/

	if (!m_chid_current)
		eWarning("SCAN: the current channel's ID was not corrected - not adding channel.");
	else
		addKnownGoodChannel(m_chid_current, m_ch_current);
	
	m_ch_scanned.push_back(m_ch_current);
	nextChannel();
}

void eDVBScan::start(const eSmartPtrList<iDVBFrontendParameters> &known_transponders, int flags)
{
	m_flags = flags;
	m_ch_toScan.clear();
	m_ch_scanned.clear();
	m_ch_unavailable.clear();
	m_new_channels.clear();
	m_new_services.clear();
	m_last_service = m_new_services.end();

	for (eSmartPtrList<iDVBFrontendParameters>::const_iterator i(known_transponders.begin()); i != known_transponders.end(); ++i)
	{
		bool exist=false;
		for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator ii(m_ch_toScan.begin()); ii != m_ch_toScan.end(); ++ii)
		{
			if (sameChannel(*i, *ii))
			{
				exist=true;
				break;
			}
		}
		if (!exist)
			m_ch_toScan.push_back(*i);
	}

	nextChannel();
}

void eDVBScan::insertInto(iDVBChannelList *db, bool dontRemoveOldFlags)
{
	if (m_flags & scanRemoveServices)
	{
		bool clearTerrestrial=false;
		bool clearCable=false;
		std::set<unsigned int> scanned_sat_positions;
		
		std::list<ePtr<iDVBFrontendParameters> >::iterator it(m_ch_scanned.begin());
		for (;it != m_ch_scanned.end(); ++it)
		{
			int system;
			(*it)->getSystem(system);
			switch(system)
			{
				case iDVBFrontend::feSatellite:
				{
					eDVBFrontendParametersSatellite sat_parm;
					(*it)->getDVBS(sat_parm);
					scanned_sat_positions.insert(sat_parm.orbital_position);
					break;
				}
				case iDVBFrontend::feTerrestrial:
				{
					clearTerrestrial=true;
					break;
				}
				case iDVBFrontend::feCable:
				{
					clearCable=true;
					break;
				}
			}
		}

		for (it=m_ch_unavailable.begin();it != m_ch_unavailable.end(); ++it)
		{
			int system;
			(*it)->getSystem(system);
			switch(system)
			{
				case iDVBFrontend::feSatellite:
				{
					eDVBFrontendParametersSatellite sat_parm;
					(*it)->getDVBS(sat_parm);
					scanned_sat_positions.insert(sat_parm.orbital_position);
					break;
				}
				case iDVBFrontend::feTerrestrial:
				{
					clearTerrestrial=true;
					break;
				}
				case iDVBFrontend::feCable:
				{
					clearCable=true;
					break;
				}
			}
		}

		if (clearTerrestrial)
		{
			eDVBChannelID chid;
			chid.dvbnamespace=0xEEEE0000;
			db->removeServices(chid);
		}
		if (clearCable)
		{
			eDVBChannelID chid;
			chid.dvbnamespace=0xFFFF0000;
			db->removeServices(chid);
		}
		for (std::set<unsigned int>::iterator x(scanned_sat_positions.begin()); x != scanned_sat_positions.end(); ++x)
		{
			eDVBChannelID chid;
			if (m_flags & scanDontRemoveFeeds)
				chid.dvbnamespace = eDVBNamespace((*x)<<16);
//			eDebug("remove %d %08x", *x, chid.dvbnamespace.get());
			db->removeServices(chid, *x);
		}
	}

	for (std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> >::const_iterator 
			ch(m_new_channels.begin()); ch != m_new_channels.end(); ++ch)
		db->addChannelToList(ch->first, ch->second);
	for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::const_iterator
		service(m_new_services.begin()); service != m_new_services.end(); ++service)
	{
		ePtr<eDVBService> dvb_service;
		if (!db->getService(service->first, dvb_service))
		{
			if (dvb_service->m_flags & eDVBService::dxNoSDT)
				continue;
			if (!(dvb_service->m_flags & eDVBService::dxHoldName))
			{
				dvb_service->m_service_name = service->second->m_service_name;
				dvb_service->m_service_name_sort = service->second->m_service_name_sort;
			}
			dvb_service->m_provider_name = service->second->m_provider_name;

			if (!dontRemoveOldFlags) // do not remove new found flags when not wished
				dvb_service->m_flags &= ~eDVBService::dxNewFound;
		}
		else
		{
			db->addService(service->first, service->second);
			service->second->m_flags |= eDVBService::dxNewFound;
		}
	}
}

RESULT eDVBScan::processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionSection &sdt)
{
	const ServiceDescriptionList &services = *sdt.getDescriptions();
	SCAN_eDebug("ONID: %04x", sdt.getOriginalNetworkId());
	eDVBChannelID chid(dvbnamespace, sdt.getTransportStreamId(), sdt.getOriginalNetworkId());
	
		/* save correct CHID for this channel if this is an ACTUAL_SDT */
	if (sdt.getTableId() == TID_SDT_ACTUAL)
		m_chid_current = chid;
	
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
				service->m_service_name = convertDVBUTF8(d.getServiceName());
				service->genSortName();

				service->m_provider_name = convertDVBUTF8(d.getServiceProviderName());
				SCAN_eDebug("name '%s', provider_name '%s'", service->m_service_name.c_str(), service->m_provider_name.c_str());
				break;
			}
/*
			case CA_IDENTIFIER_DESCRIPTOR:
			{
				CaIdentifierDescriptor &d = (CaIdentifierDescriptor&)**desc;
				const CaSystemIdList &caids = *d.getCaSystemIds();
				SCAN_eDebugNoNewLine("CA ");
				for (CaSystemIdList::const_iterator i(caids.begin()); i != caids.end(); ++i)
				{
					SCAN_eDebugNoNewLine("%04x ", *i);
					service->m_ca.insert(*i);
				}
				SCAN_eDebug("");
				break;
			}
*/
			default:
				SCAN_eDebug("descr<%x>", (*desc)->getTag());
				break;
			}
		}
		
		std::pair<std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator, bool> i = m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));
		
		if (i.second)
		{
			m_last_service = i.first;
			m_event(evtNewService);
		}
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

void eDVBScan::getLastServiceName(std::string &last_service_name)
{
	if (m_last_service == m_new_services.end())
		last_service_name = "";
	else
		last_service_name = m_last_service->second->m_service_name;
}
