#include <fcntl.h>
#include <lib/dvb/idvb.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/s2_satellite_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>
#include <dvbsi++/t2_delivery_system_descriptor.h>
#include <dvbsi++/logical_channel_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/ca_identifier_descriptor.h>
#include <dvbsi++/registration_descriptor.h>
#include <dvbsi++/extension_descriptor.h>
#include <dvbsi++/frequency_list_descriptor.h>
#include <lib/base/nconfig.h> // access to python config
#include <lib/dvb/specs.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/scan.h>
#include <lib/dvb/frontend.h>
#include <lib/dvb/db.h>
#include <lib/dvb/frontendparms.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/python/python.h>
#include <errno.h>
#include "absdiff.h"

#define SCAN_eDebug(x...) do { if (m_scan_debug) eDebug(x); } while(0)
#define SCAN_eDebugNoNewLineStart(x...) do { if (m_scan_debug) eDebugNoNewLineStart(x); } while(0)
#define SCAN_eDebugNoNewLine(x...) do { if (m_scan_debug) eDebugNoNewLine(x); } while(0)
#define SCAN_eDebugNoNewLineEnd(x...) do { if (m_scan_debug) eDebugNoNewLineEnd(x); } while(0)

DEFINE_REF(eDVBScan);

eDVBScan::eDVBScan(iDVBChannel *channel, bool usePAT, bool debug)
	:m_channel(channel)
	,m_channel_state(iDVBChannel::state_idle)
	,m_ready(0)
	,m_ready_all(usePAT ? (readySDT|readyPAT) : readySDT)
	,m_pmt_running(false)
	,m_abort_current_pmt(false)
	,m_flags(0)
	,m_usePAT(usePAT)
	,m_scan_debug(debug)
{
	if (m_channel->getDemux(m_demux))
		SCAN_eDebug("scan: failed to allocate demux!");
	m_channel->connectStateChange(sigc::mem_fun(*this, &eDVBScan::stateChange), m_stateChanged_connection);
	m_lcn_file = NULL;
}

eDVBScan::~eDVBScan()
{
	if (m_lcn_file)
		fclose(m_lcn_file);
}

int eDVBScan::isValidONIDTSID(int orbital_position, eOriginalNetworkID onid, eTransportStreamID tsid)
{
	int ret;
	switch (onid.get())
	{
	case 0:
	case 0x1111:
		ret=0;
		break;
	case 0x13E:  // workaround for 11258H and 11470V on hotbird with same ONID/TSID (0x13E/0x578)
		ret = orbital_position != 130 || tsid != 0x578;
		break;
	case 1:
		ret = orbital_position == 192;
		break;
	case 0x00B1:
		ret = tsid != 0x00B0;
		break;
	case 0x00eb:
		ret = tsid != 0x4321;
		break;
	case 0x0002:
		ret = absdiff(orbital_position, 282) < 6 && tsid != 2019;
		// 12070H and 10936V have same tsid/onid.. but even the same services are provided
		break;
	case 0x2000:
		ret = tsid != 0x1000;
		break;
	case 0x5E: // Sirius 4.8E 12322V and 12226H
		ret = absdiff(orbital_position, 48) < 3 && tsid != 1;
		break;
	case 0x0070: // Eutelsat W7 36.0E 12174L and 12284R have same ONID/TSID (0x0070/0x0008)
		ret = orbital_position != 360 || tsid != 0x0008;
		break;
	case 10100: // Eutelsat W7 36.0E 11644V and 11652V
		ret = orbital_position != 360 || tsid != 10187;
		break;
	case 42: // Tuerksat 42.0E
		ret = orbital_position != 420 || (
		    tsid != 8 && // 11830V 12729V
		    tsid != 5 && // 12679V 12685H
		    tsid != 2 && // 11096V 12015H
		    tsid != 55); // 11996V 11716V
		break;
	case 100: // Intelsat 10 68.5E 3808V 3796V 4012V, Amos 4.0W 10723V 11571H
		ret = (orbital_position != 685 && orbital_position != 3560) || tsid != 1;
		break;
	case 70: // Thor 0.8W 11862H 12341V
		ret = absdiff(orbital_position, 3592) < 3 && tsid != 46;
		break;
	case 32: // NSS 806 (40.5W) 4059R, 3774L
		ret = orbital_position != 3195 || tsid != 21;
		break;
	case 126:  // 11221H and 11387H on Utelsat 7.0E with same ONID/TSID (126/40700) and 11304H, 11262H (126/30300) 
		ret = orbital_position != 70 || (tsid != 40700 && tsid !=30300);
		break;
	case 3622:  // 11881H and 12284V on Badr 26.0E with same ONID/TSID (3622/100)
		ret = orbital_position != 260 || tsid != 100;
		break;
	default:
		ret = onid.get() < 0xFF00;
		break;
	}
	return ret;
}

eDVBNamespace eDVBScan::buildNamespace(eOriginalNetworkID onid, eTransportStreamID tsid, unsigned long hash)
{
	int orb_pos = (hash >> 16) & 0xFFFF;
	if (orb_pos == 0xFFFF) // cable
	{
		if (eConfigManager::getConfigBoolValue("config.usage.subnetwork_cable", true))
			hash &= ~0xFFFF;
	}
	else if (orb_pos == 0xEEEE) // terrestrial
	{
		if (eConfigManager::getConfigBoolValue("config.usage.subnetwork_terrestrial", true))
			hash &= ~0xFFFF;
	}
	else if (eConfigManager::getConfigBoolValue("config.usage.subnetwork", true)
		&& isValidONIDTSID(orb_pos, onid, tsid)) // on valid ONIDs, ignore frequency ("sub network") part
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
		if (m_ch_current && m_channel)
		{
			int type;
			m_ch_current->getSystem(type);
			if (type == iDVBFrontend::feTerrestrial)
			{
				eDVBFrontendParametersTerrestrial parm;
				m_ch_current->getDVBT(parm);
				if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T_T2)
				{
					/* we have a lock, this is a valid DVB-T transponder, set our system parameter */
					parm.system = eDVBFrontendParametersTerrestrial::System_DVB_T;
					m_ch_current->setDVBT(parm);
				}
			}
		}
		if (!m_ch_blindscan.empty())
		{
			/* update current blindscan iteration channel with scanned parameters */
			if (m_ch_current && m_channel)
			{
				ePtr<iDVBFrontend> fe;
				m_channel->getFrontend(fe);
				if (fe)
				{
					ePtr<iDVBTransponderData> tp;
					fe->getTransponderData(tp, false);
					if (tp)
					{
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						int type;
						m_ch_current->getSystem(type);
						switch (type)
						{
						case iDVBFrontend::feSatellite:
						{
							eDVBFrontendParametersSatellite parm;
							m_ch_current->getDVBS(parm);
							parm.system = tp->getSystem();
							parm.frequency = tp->getFrequency();
							parm.symbol_rate = tp->getSymbolRate();
							parm.modulation = tp->getModulation();
							feparm->setDVBS(parm);
							break;
						}
						case iDVBFrontend::feCable:
						{
							eDVBFrontendParametersCable parm;
							m_ch_current->getDVBC(parm);
							parm.system = tp->getSystem();
							parm.frequency = tp->getFrequency();
							parm.symbol_rate = tp->getSymbolRate();
							parm.modulation = tp->getModulation();
							feparm->setDVBC(parm);
							break;
						}
						case iDVBFrontend::feTerrestrial:
						{
							eDVBFrontendParametersTerrestrial parm;
							m_ch_current->getDVBT(parm);
							parm.system = tp->getSystem();
							parm.frequency = tp->getFrequency();
							parm.bandwidth = tp->getBandwidth();
							parm.modulation = tp->getConstellation();
							feparm->setDVBT(parm);
							break;
						}
						case iDVBFrontend::feATSC:
						{
							eDVBFrontendParametersATSC parm;
							m_ch_current->getATSC(parm);
							parm.system = tp->getSystem();
							parm.frequency = tp->getFrequency();
							feparm->setATSC(parm);
							break;
						}
						}
						m_ch_current = m_ch_blindscan_result = feparm;
					}
				}
			}
		}
		startFilter();
		m_channel_state = state;
	} else if (state == iDVBChannel::state_failed)
	{
		if (m_ch_current && m_channel)
		{
			int type;
			m_ch_current->getSystem(type);
			m_ch_unavailable.push_back(m_ch_current);
			if (type == iDVBFrontend::feTerrestrial)
			{
				eDVBFrontendParametersTerrestrial parm;
				m_ch_current->getDVBT(parm);
				if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T_T2)
				{
					/* we have to scan T2 as well as T */
					ePtr<iDVBFrontend> fe;
					eDVBFrontendParameters eparm;
					parm.system = eDVBFrontendParametersTerrestrial::System_DVB_T2;
					eparm.setDVBT(parm);
					m_channel->getFrontend(fe);
					if (fe)
					{
						ePtr<iDVBFrontendParameters> feparm = new eDVBFrontendParameters(eparm);
						/* but only if the frontend supports T2 */
						if (fe->isCompatibleWith(feparm))
						{
							addChannelToScan(feparm);
						}
					}
				}
			}
		}
		if (!m_ch_blindscan.empty())
		{
			/* tune failure, this means the blindscan channel iteration run has completed */
			SCAN_eDebug("[eDVBScan] blindscan channel completed");
			m_ch_blindscan.pop_front();
		}
		nextChannel();
	}
			/* unavailable will timeout, anyway. */
}

RESULT eDVBScan::nextChannel()
{
	ePtr<iDVBFrontend> fe;

	m_SDT = 0; m_PAT = 0; m_BAT = 0; m_NIT = 0, m_PMT = 0;

	m_ready = 0;

	m_pat_tsid = eTransportStreamID();

		/* check what we need */
	m_ready_all = readySDT;

	if (m_flags & scanNetworkSearch)
		m_ready_all |= readyNIT;

	if (m_flags & scanSearchBAT)
		m_ready_all |= readyBAT;

	if (m_usePAT)
		m_ready_all |= readyPAT;

	if (!m_ch_blindscan.empty())
	{
		/* keep iterating with the same 'channel' till we get a tune failure */
		SCAN_eDebug("[eDVBScan] blindscan channel iteration");
		m_ch_current = m_ch_blindscan.front();
	}
	else
	{
		m_ch_blindscan_result = NULL;
		if (m_ch_toScan.empty())
		{
			SCAN_eDebug("[eDVBScan] no channels left: %zd scanned, %zd unavailable, %zd database.",
				m_ch_scanned.size(), m_ch_unavailable.size(), m_new_channels.size());
			m_event(evtFinish);
			return -ENOENT;
		}

		m_ch_current = m_ch_toScan.front();

		m_ch_toScan.pop_front();
	}

	if (m_channel->getFrontend(fe))
	{
		m_event(evtFail);
		return -ENOTSUP;
	}

	m_chid_current = eDVBChannelID();

	m_channel_state = iDVBChannel::state_idle;

	if (fe->tune(*m_ch_current, !m_ch_blindscan.empty()))
		return nextChannel();

	m_event(evtUpdate);
	return 0;
}

RESULT eDVBScan::startFilter()
{
	bool startSDT=true;
	int system;
	ASSERT(m_demux);

			/* only start required filters filter */

	if (m_ready_all & readyPAT)
		startSDT = m_ready & readyPAT;

	// m_ch_current is not set, when eDVBScan is just used for a SDT update
	if (!m_ch_current)
	{
		unsigned int channelFlags;
		m_channel->getCurrentFrontendParameters(m_ch_current);
		m_ch_current->getFlags(channelFlags);
		if (channelFlags & iDVBFrontendParameters::flagOnlyFree)
			m_flags |= scanOnlyFree;
	}

	m_VCT = 0;
	m_ch_current->getSystem(system);
	if (system == iDVBFrontend::feATSC)
	{
		m_VCT = new eTable<VirtualChannelTableSection>;
		if (m_VCT->start(m_demux, eDVBVCTSpec()))
			return -1;
		CONNECT(m_VCT->tableReady, eDVBScan::VCTready);
		startSDT = false;
	}

	m_SDT = 0;
	if (startSDT && (m_ready_all & readySDT))
	{
		m_SDT = new eTable<ServiceDescriptionSection>;
		int tsid=-1;
		if (m_ready & readyPAT && m_ready & validPAT)
		{
			std::vector<ProgramAssociationSection*>::const_iterator i =
				m_PAT->getSections().begin();
			ASSERT(i != m_PAT->getSections().end());
			tsid = (*i)->getTableIdExtension(); // in PAT this is the transport stream id
			m_pat_tsid = eTransportStreamID(tsid);
			for (; i != m_PAT->getSections().end(); ++i)
			{
				const ProgramAssociationSection &pat = **i;
				ProgramAssociationConstIterator program = pat.getPrograms()->begin();
				for (; program != pat.getPrograms()->end(); ++program)
					m_pmts_to_read.insert(std::pair<unsigned short, service>((*program)->getProgramNumber(), service((*program)->getProgramMapPid())));
			}
			m_PMT = new eTable<ProgramMapSection>;
			CONNECT(m_PMT->tableReady, eDVBScan::PMTready);
			PMTready(-2);
			// KabelBW HACK ... on 618Mhz and 626Mhz the transport stream id in PAT and SDT is different

			{
				int type;
				m_ch_current->getSystem(type);
				if (type == iDVBFrontend::feCable)
				{
					eDVBFrontendParametersCable parm;
					m_ch_current->getDVBC(parm);
					if ((tsid == 0x00d7 && absdiff(parm.frequency, 618000) < 2000) ||
						(tsid == 0x00d8 && absdiff(parm.frequency, 626000) < 2000))
						tsid = -1;
				}
			}
		}
		if (tsid == -1)
		{
			if (m_SDT->start(m_demux, eDVBSDTSpec()))
				return -1;
		}
		else if (m_SDT->start(m_demux, eDVBSDTSpec(tsid, true)))
			return -1;
		CONNECT(m_SDT->tableReady, eDVBScan::SDTready);
	}

	if (!(m_ready & readyPAT))
	{
		m_PAT = 0;
		if (m_ready_all & readyPAT)
		{
			m_PAT = new eTable<ProgramAssociationSection>;
			if (m_PAT->start(m_demux, eDVBPATSpec(4000)))
				return -1;
			CONNECT(m_PAT->tableReady, eDVBScan::PATready);
		}

		m_NIT = 0;
		if (m_ready_all & readyNIT)
		{
			m_NIT = new eTable<NetworkInformationSection>;
			if (m_NIT->start(m_demux, eDVBNITSpec(m_networkid)))
				return -1;
			CONNECT(m_NIT->tableReady, eDVBScan::NITready);
		}

		m_BAT = 0;
		if (m_ready_all & readyBAT)
		{
			m_BAT = new eTable<BouquetAssociationSection>;
			if (m_BAT->start(m_demux, eDVBBATSpec()))
				return -1;
			CONNECT(m_BAT->tableReady, eDVBScan::BATready);
		}
	}
	return 0;
}

void eDVBScan::SDTready(int err)
{
	SCAN_eDebug("[eDVBScan] got sdt %d", err);
	m_ready |= readySDT;
	if (!err)
		m_ready |= validSDT;
	channelDone();
}

void eDVBScan::NITready(int err)
{
	SCAN_eDebug("[eDVBScan] got nit, err %d", err);
	m_ready |= readyNIT;
	if (!err)
		m_ready |= validNIT;
	channelDone();
}

void eDVBScan::BATready(int err)
{
	SCAN_eDebug("[eDVBScan] got bat, err %d", err);
	m_ready |= readyBAT;
	if (!err)
		m_ready |= validBAT;
	channelDone();
}

void eDVBScan::PATready(int err)
{
	SCAN_eDebug("[eDVBScan] got pat, err %d", err);
	m_ready |= readyPAT;
	if (!err)
		m_ready |= validPAT;
	startFilter(); // for starting the SDT filter
}

void eDVBScan::VCTready(int err)
{
	SCAN_eDebug("[eDVBScan] got vct %d", err);
	m_ready |= readySDT;
	if (!err)
		m_ready |= validVCT;
	channelDone();
}

void eDVBScan::PMTready(int err)
{
	SCAN_eDebug("[eDVBScan] got pmt %d", err);
	if (!err)
	{
		bool scrambled = false;
		bool have_audio = false;
		bool have_video = false;
		unsigned short pcrpid = 0xFFFF;
		std::vector<ProgramMapSection*>::const_iterator i;

		for (i = m_PMT->getSections().begin(); i != m_PMT->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;
			if (pcrpid == 0xFFFF)
				pcrpid = pmt.getPcrPid();
			else
				SCAN_eDebug("[eDVBScan]   already have a pcrpid %04x %04x", pcrpid, pmt.getPcrPid());
			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int isaudio = 0, isvideo = 0, is_scrambled = 0, forced_audio = 0, forced_video = 0;
				switch ((*es)->getType())
				{
				case 0x1b: // AVC Video Stream (MPEG4 H264)
				case 0x24: // H265 HEVC
				case 0x10: // MPEG 4 Part 2
				case 0x01: // MPEG 1 video
				case 0x02: // MPEG 2 video
					isvideo = 1;
					forced_video = 1;
					//break; fall through !!!
				case 0x03: // MPEG 1 audio
				case 0x04: // MPEG 2 audio
				case 0x0f: // MPEG 2 AAC
				case 0x11: // MPEG 4 AAC
					if (!isvideo)
					{
						forced_audio = 1;
						isaudio = 1;
					}
				case 0x06: // PES Private
				case 0x81: // user private
				case 0xEA: // TS_PSI_ST_SMPTE_VC1
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
							desc != (*es)->getDescriptors()->end(); ++desc)
					{
						uint8_t tag = (*desc)->getTag();
						/* PES private can contain AC-3, DTS or lots of other stuff.
						   check descriptors to get the exakt type. */
						if (!forced_video && !forced_audio)
						{
							switch (tag)
							{
							case 0x1C: // TS_PSI_DT_MPEG4_Audio
							case 0x2B: // TS_PSI_DT_MPEG2_AAC
							case AAC_DESCRIPTOR:
							case AC3_DESCRIPTOR:
							case DTS_DESCRIPTOR:
							case AUDIO_STREAM_DESCRIPTOR:
								isaudio = 1;
								break;
							case 0x28: // TS_PSI_DT_AVC
							case 0x1B: // TS_PSI_DT_MPEG4_Video
							case VIDEO_STREAM_DESCRIPTOR:
								isvideo = 1;
								break;
							case REGISTRATION_DESCRIPTOR: /* some services don't have a separate AC3 descriptor */
							{
								RegistrationDescriptor *d = (RegistrationDescriptor*)(*desc);
								switch (d->getFormatIdentifier())
								{
								case 0x44545331 ... 0x44545333: // DTS1/DTS2/DTS3
								case 0x41432d33: // == 'AC-3'
								case 0x42535344: // == 'BSSD' (LPCM)
									isaudio = 1;
									break;
								case 0x56432d31: // == 'VC-1'
									isvideo = 1;
									break;
								default:
									break;
								}
							}
							default:
								break;
							}
						}
						if (tag == CA_DESCRIPTOR)
							is_scrambled = 1;
					}
				default:
					break;
				}
				if (isvideo)
					have_video = true;
				else if (isaudio)
					have_audio = true;
				else
					continue;
				if (is_scrambled)
					scrambled = true;
			}
			for (DescriptorConstIterator desc = pmt.getDescriptors()->begin();
				desc != pmt.getDescriptors()->end(); ++desc)
			{
				if ((*desc)->getTag() == CA_DESCRIPTOR)
					scrambled = true;
			}
		}
		m_pmt_in_progress->second.scrambled = scrambled;
		if ( have_video )
			m_pmt_in_progress->second.serviceType = 1;
		else if ( have_audio )
			m_pmt_in_progress->second.serviceType = 2;
		else
			m_pmt_in_progress->second.serviceType = 100;
	}
	if (err == -1) // timeout or removed by sdt
		m_pmts_to_read.erase(m_pmt_in_progress++);
	else if (m_pmt_running)
		++m_pmt_in_progress;
	else
	{
		m_pmt_in_progress = m_pmts_to_read.begin();
		m_pmt_running = true;
	}

	if (m_pmt_in_progress != m_pmts_to_read.end())
		m_PMT->start(m_demux, eDVBPMTSpec(m_pmt_in_progress->second.pmtPid, m_pmt_in_progress->first, 4000));
	else
	{
		m_PMT = 0;
		m_pmt_running = false;
		channelDone();
	}
}


void eDVBScan::addKnownGoodChannel(const eDVBChannelID &chid, iDVBFrontendParameters *feparm)
{
		/* add it to the list of known channels. */
	if (chid)
		m_new_channels.insert(std::pair<eDVBChannelID,ePtr<iDVBFrontendParameters> >(chid, feparm));
}

void eDVBScan::addLcnToDB(eDVBNamespace ns, eOriginalNetworkID onid, eTransportStreamID tsid, eServiceID sid, uint16_t lcn, uint32_t signal)
{
	if (m_lcn_file)
	{
		int size = 0;
		char row[40];
		bool added = false;
		sprintf(row, "%08x:%04x:%04x:%04x:%05d:%08d\n", ns.get(), onid.get(), tsid.get(), sid.get(), lcn, signal);
		fseek(m_lcn_file, 0, SEEK_END);
		size = ftell(m_lcn_file);
		
		for (int i = 0; i < size / 39; i++)
		{
			char tmp[40];
			fseek(m_lcn_file, i*39, SEEK_SET);
			fread (tmp, 1, 39, m_lcn_file);
			if (memcmp(tmp, row, 23) == 0)
			{
				fseek(m_lcn_file, i*39, SEEK_SET);
				fwrite(row, 1, 39, m_lcn_file);
				added = true;
				break;
			}
		}
			
		if (!added)
		{
			fseek(m_lcn_file, 0, SEEK_END);
			fwrite(row, 1, 39, m_lcn_file);
		}
	}
}


void eDVBScan::addChannelToScan(iDVBFrontendParameters *feparm)
{
		/* check if we don't already have that channel ... */

	int type;
	feparm->getSystem(type);

	switch(type)
	{
	case iDVBFrontend::feSatellite:
	{
		eDVBFrontendParametersSatellite parm;
		feparm->getDVBS(parm);
		SCAN_eDebug("[eDVBScan] try to add %d %d %d %d %d %d",
			parm.orbital_position, parm.frequency, parm.symbol_rate, parm.polarisation, parm.fec, parm.modulation);
		break;
	}
	case iDVBFrontend::feCable:
	{
		eDVBFrontendParametersCable parm;
		feparm->getDVBC(parm);
		SCAN_eDebug("[eDVBScan] try to add %d %d %d %d",
			parm.frequency, parm.symbol_rate, parm.modulation, parm.fec_inner);
		break;
	}
	case iDVBFrontend::feTerrestrial:
	{
		eDVBFrontendParametersTerrestrial parm;
		feparm->getDVBT(parm);
		SCAN_eDebug("[eDVBScan] try to add %d %d %d %d %d %d %d %d",
			parm.frequency, parm.modulation, parm.transmission_mode, parm.hierarchy,
			parm.guard_interval, parm.code_rate_LP, parm.code_rate_HP, parm.bandwidth);
		break;
	}
	case iDVBFrontend::feATSC:
	{
		eDVBFrontendParametersATSC parm;
		feparm->getATSC(parm);
		SCAN_eDebug("[eDVBScan] try to add atsc %d %d %d %d",
			parm.frequency, parm.modulation, parm.inversion, parm.system);
		break;
	}
	}

	int found_count=0;
		/* ... in the list of channels to scan */
	for (std::list<ePtr<iDVBFrontendParameters> >::iterator i(m_ch_toScan.begin()); i != m_ch_toScan.end();)
	{
		if (sameChannel(*i, feparm))
		{
			if (!found_count)
			{
				*i = feparm;  // update
				SCAN_eDebug("[eDVBScan] update");
			}
			else
			{
				SCAN_eDebug("[eDVBScan] remove dupe");
				m_ch_toScan.erase(i++);
				continue;
			}
			++found_count;
		}
		++i;
	}

	if (found_count > 0)
	{
		SCAN_eDebug("[eDVBScan] already in todo list");
		return;
	}

		/* ... in the list of successfully scanned channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_scanned.begin()); i != m_ch_scanned.end(); ++i)
		if (sameChannel(*i, feparm))
		{
			SCAN_eDebug("[eDVBScan] successfully scanned");
			return;
		}

		/* ... in the list of unavailable channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_unavailable.begin()); i != m_ch_unavailable.end(); ++i)
		if (sameChannel(*i, feparm, true))
		{
			SCAN_eDebug("[eDVBScan] scanned but not available");
			return;
		}

		/* ... on the current channel */
	if (sameChannel(m_ch_current, feparm))
	{
		SCAN_eDebug("[eDVBScan] is current");
		return;
	}

	SCAN_eDebug("[eDVBScan] really add");
		/* otherwise, add it to the todo list. */
	m_ch_toScan.push_front(feparm); // better.. then the rotor not turning wild from east to west :)
}

int eDVBScan::sameChannel(iDVBFrontendParameters *ch1, iDVBFrontendParameters *ch2, bool exact) const
{
	int diff;
	if (ch1->calculateDifference(ch2, diff, exact))
		return 0;
	if (diff < 2000) // more than 2mhz difference?
		return 1;
	return 0;
}

void eDVBScan::channelDone()
{
	if (m_ready & validSDT && (!(m_flags & scanOnlyFree) || !m_pmt_running))
	{
		unsigned long hash = 0;

		m_ch_current->getHash(hash);

		eDVBNamespace dvbnamespace = buildNamespace(
			(**m_SDT->getSections().begin()).getOriginalNetworkId(),
			(**m_SDT->getSections().begin()).getTransportStreamId(),
			hash);

		SCAN_eDebug("[eDVBScan] SDT: ");
		std::vector<ServiceDescriptionSection*>::const_iterator i;
		for (i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
			processSDT(dvbnamespace, **i);
		m_ready &= ~validSDT;
	}

	if (m_ready & validVCT)
	{
		unsigned long hash = 0;

		m_ch_current->getHash(hash);

		int onid = 0; /* TODO: ATSC ONID? */
		eDVBNamespace dvbnamespace = buildNamespace(
			eOriginalNetworkID(onid),
			(**m_VCT->getSections().begin()).getTransportStreamId(),
			hash);

		SCAN_eDebug("[eDVBScan] VCT: ");
		std::vector<VirtualChannelTableSection*>::const_iterator i;
		for (i = m_VCT->getSections().begin(); i != m_VCT->getSections().end(); ++i)
			processVCT(dvbnamespace, **i, onid);
		m_ready &= ~validVCT;
	}

	if (m_ready & validNIT)
	{
		int system;
		std::list<ePtr<iDVBFrontendParameters> > m_ch_toScan_backup;
		m_ch_current->getSystem(system);
		SCAN_eDebug("[eDVBScan] dumping NIT");
		if (m_flags & clearToScanOnFirstNIT)
		{
			m_ch_toScan_backup = m_ch_toScan;
			m_ch_toScan.clear();
		}
		std::vector<NetworkInformationSection*>::const_iterator i;
		for (i = m_NIT->getSections().begin(); i != m_NIT->getSections().end(); ++i)
		{
			if (m_networkid && m_networkid != (*i)->getTableIdExtension()) // in NIT this is the network id
			{
				SCAN_eDebug("[eDVBScan] ignoring NetworkId %d!", (*i)->getTableIdExtension());
				continue;
			}

			const TransportStreamInfoList &tsinfovec = *(*i)->getTsInfo();

			for (TransportStreamInfoConstIterator tsinfo(tsinfovec.begin());
				tsinfo != tsinfovec.end(); ++tsinfo)
			{
				SCAN_eDebug("[eDVBScan] TSID: %04x ONID: %04x", (*tsinfo)->getTransportStreamId(),
					(*tsinfo)->getOriginalNetworkId());
				bool T2 = false;
				eDVBFrontendParametersTerrestrial t2transponder;
				eOriginalNetworkID onid = (*tsinfo)->getOriginalNetworkId();
				eTransportStreamID tsid = (*tsinfo)->getTransportStreamId();
				eDVBNamespace ns(0);

				for (DescriptorConstIterator desc = (*tsinfo)->getDescriptors()->begin();
						desc != (*tsinfo)->getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
					case CABLE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						if (system != iDVBFrontend::feCable)
							break; // when current locked transponder is no cable transponder ignore this descriptor
						CableDeliverySystemDescriptor &d = (CableDeliverySystemDescriptor&)**desc;
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersCable cable;
						cable.set(d);
						feparm->setDVBC(cable);

						addChannelToScan(feparm);
						break;
					}
					case TERRESTRIAL_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						if (system != iDVBFrontend::feTerrestrial)
							break; // when current locked transponder is no terrestrial transponder ignore this descriptor
						TerrestrialDeliverySystemDescriptor &d = (TerrestrialDeliverySystemDescriptor&)**desc;
						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersTerrestrial terr;
						terr.set(d);
						feparm->setDVBT(terr);
						
						unsigned long hash=0;
						feparm->getHash(hash);
						ns = buildNamespace(onid, tsid, hash);
						
						addChannelToScan(feparm);
						break;
					}
					case LOGICAL_CHANNEL_DESCRIPTOR:
					{
						// we handle it later
						break;
					}
					case S2_SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						eDebug("[eDVBScan] S2_SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR found");
						if (system != iDVBFrontend::feSatellite)
							break; // when current locked transponder is no satellite transponder ignore this descriptor

						S2SatelliteDeliverySystemDescriptor &d = (S2SatelliteDeliverySystemDescriptor&)**desc;
					}
					case SATELLITE_DELIVERY_SYSTEM_DESCRIPTOR:
					{
						if (system != iDVBFrontend::feSatellite)
							break; // when current locked transponder is no satellite transponder ignore this descriptor

						SatelliteDeliverySystemDescriptor &d = (SatelliteDeliverySystemDescriptor&)**desc;
						if (d.getFrequency() < 10000)
							break;

						ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
						eDVBFrontendParametersSatellite sat;
						sat.set(d);

						eDVBFrontendParametersSatellite p;
						m_ch_current->getDVBS(p);

						if ( absdiff(p.orbital_position, sat.orbital_position) < 5 )
							sat.orbital_position = p.orbital_position;

						if ( absdiff(absdiff(3600, p.orbital_position), sat.orbital_position) < 5 )
						{
							SCAN_eDebug("[eDVBScan] found transponder with incorrect west/east flag ... correct this");
							sat.orbital_position = p.orbital_position;
						}

						feparm->setDVBS(sat);

						if ( p.orbital_position != sat.orbital_position)
							SCAN_eDebug("[eDVBScan] dropping this transponder, it's on another satellite.");
						else
						{
							addChannelToScan(feparm);
						}
						break;
					}
					case EXTENSION_DESCRIPTOR:
					{
						if (system != iDVBFrontend::feTerrestrial)
							break; // when current locked transponder is no terrestrial transponder ignore this descriptor

						ExtensionDescriptor &d = (ExtensionDescriptor&)**desc;
						switch (d.getExtensionTag())
						{
						case T2_DELIVERY_SYSTEM_DESCRIPTOR:
							T2 = true;
							T2DeliverySystemDescriptor &d = (T2DeliverySystemDescriptor&)**desc;
							t2transponder.set(d);

							for (T2CellConstIterator cell = d.getCells()->begin();
								cell != d.getCells()->end(); ++cell)
							{
								for (T2FrequencyConstIterator freq = (*cell)->getCentreFrequencies()->begin();
									freq != (*cell)->getCentreFrequencies()->end(); ++freq)
								{
									t2transponder.frequency = (*freq) * 10;
									ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
									feparm->setDVBT(t2transponder);
									addChannelToScan(feparm);
								}
							}
						}
						break;
					}
					case FREQUENCY_LIST_DESCRIPTOR:
					{
						if (system != iDVBFrontend::feTerrestrial)
							break; // when current locked transponder is no terrestrial transponder ignore this descriptor
						if (!T2)
							break;

						FrequencyListDescriptor &d = (FrequencyListDescriptor&)**desc;
						if (d.getCodingType() != 0x03)
							break;

						for (CentreFrequencyConstIterator it = d.getCentreFrequencies()->begin();
								it != d.getCentreFrequencies()->end(); ++it)
						{
							t2transponder.frequency = (*it) * 10;
							ePtr<eDVBFrontendParameters> feparm = new eDVBFrontendParameters;
							feparm->setDVBT(t2transponder);
							addChannelToScan(feparm);
						}
						break;
					}
					default:
						SCAN_eDebug("[eDVBScan] descr<%x>", (*desc)->getTag());
						break;
					}
				}
				// we do this after the main loop because we absolutely need the namespace
				for (DescriptorConstIterator desc = (*tsinfo)->getDescriptors()->begin();
					desc != (*tsinfo)->getDescriptors()->end(); ++desc)
				{
					switch ((*desc)->getTag())
					{
						case LOGICAL_CHANNEL_DESCRIPTOR:
						{
							if (system != iDVBFrontend::feTerrestrial)
								break; // when current locked transponder is no terrestrial transponder ignore this descriptor
								
							if (ns.get() == 0)
								break; // invalid namespace
								
							int signal = 0;
							ePtr<iDVBFrontend> fe;
							
							if (!m_channel->getFrontend(fe))
								signal = fe->readFrontendData(iFrontendInformation_ENUMS::signalQuality);
							
							LogicalChannelDescriptor &d = (LogicalChannelDescriptor&)**desc;
							for (LogicalChannelListConstIterator it = d.getChannelList()->begin(); it != d.getChannelList()->end(); it++)
							{
								LogicalChannel *ch = *it;
								if (ch->getVisibleServiceFlag())
								{
									addLcnToDB(ns, onid, tsid, eServiceID(ch->getServiceId()), ch->getLogicalChannelNumber(), signal);
									SCAN_eDebug("NAMESPACE: %08x TSID: %04x ONID: %04x SID: %04x LCN: %05d SIGNAL: %08d", ns.get(), onid.get(), tsid.get(), ch->getServiceId(), ch->getLogicalChannelNumber(), signal);
								}
							}
							break;
						}
						default:
							break;
					}
				}
			}

		}

			/* a pitfall is to have the clearToScanOnFirstNIT-flag set, and having channels which have
			   no or invalid NIT. this code will not erase the toScan list unless at least one valid entry
			   has been found.

			   This is not a perfect solution, as the channel could contain a partial NIT. Life's bad.
			*/
		if (m_flags & clearToScanOnFirstNIT)
		{
			if (m_ch_toScan.empty())
			{
				eWarning("[eDVBScan] clearToScanOnFirstNIT was set, but NIT is invalid. Refusing to stop scan.");
				m_ch_toScan = m_ch_toScan_backup;
			} else
	 			m_flags &= ~clearToScanOnFirstNIT;
 		}
		m_ready &= ~validNIT;
	}

	if (m_pmt_running || (m_ready & m_ready_all) != m_ready_all)
	{
		if (m_abort_current_pmt)
		{
			m_abort_current_pmt = false;
			PMTready(-1);
		}
		return;
	}

	SCAN_eDebug("[eDVBScan] channel done!");

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

	int type;
	if (m_ch_current->getSystem(type))
		type = -1;

	for (m_pmt_in_progress = m_pmts_to_read.begin(); m_pmt_in_progress != m_pmts_to_read.end();)
	{
		eServiceReferenceDVB ref;
		ePtr<eDVBService> service = new eDVBService;

		if (!m_chid_current)
		{
			unsigned long hash = 0;

			m_ch_current->getHash(hash);

			m_chid_current = eDVBChannelID(
				buildNamespace(eOriginalNetworkID(0), m_pat_tsid, hash),
				m_pat_tsid, eOriginalNetworkID(0));
		}

		if (m_pmt_in_progress->second.serviceType == 1)
			SCAN_eDebug("[eDVBScan] SID %04x is VIDEO", m_pmt_in_progress->first);
		else if (m_pmt_in_progress->second.serviceType == 2)
			SCAN_eDebug("[eDVBScan] SID %04x is AUDIO", m_pmt_in_progress->first);
		else
			SCAN_eDebug("[eDVBScan] SID %04x is DATA", m_pmt_in_progress->first);

		ref.set(m_chid_current);
		ref.setServiceID(m_pmt_in_progress->first);
		ref.setServiceType(m_pmt_in_progress->second.serviceType);

		if (type != -1)
		{
			char sname[255];
			char pname[255];
			memset(pname, 0, sizeof(pname));
			memset(sname, 0, sizeof(sname));
			switch(type)
			{
				case iDVBFrontend::feSatellite:
				{
					eDVBFrontendParametersSatellite parm;
					m_ch_current->getDVBS(parm);
					snprintf(sname, 255, "%d%c SID 0x%02x",
							parm.frequency/1000,
							parm.polarisation ? 'V' : 'H',
							m_pmt_in_progress->first);
					snprintf(pname, 255, "%s %s %d%c %d.%d°%c",
						parm.system ? "DVB-S2" : "DVB-S",
						parm.modulation == eDVBFrontendParametersSatellite::Modulation_Auto ? "AUTO" :
						parm.modulation == eDVBFrontendParametersSatellite::Modulation_QPSK ? "QPSK" :
						parm.modulation == eDVBFrontendParametersSatellite::Modulation_8PSK ? "8PSK" :
						parm.modulation == eDVBFrontendParametersSatellite::Modulation_QAM16 ? "QAM16" :
						parm.modulation == eDVBFrontendParametersSatellite::Modulation_16APSK ? "16APSK" : "32APSK",
						parm.frequency/1000,
						parm.polarisation ? 'V' : 'H',
						parm.orbital_position/10,
						parm.orbital_position%10,
						parm.orbital_position > 0 ? 'E' : 'W');
					break;
				}
				case iDVBFrontend::feTerrestrial:
				{
					eDVBFrontendParametersTerrestrial parm;
					m_ch_current->getDVBT(parm);
					snprintf(sname, 255, "%d SID 0x%02x",
						parm.frequency/1000,
						m_pmt_in_progress->first);
					break;
				}
				case iDVBFrontend::feCable:
				{
					eDVBFrontendParametersCable parm;
					m_ch_current->getDVBC(parm);
					snprintf(sname, 255, "%d SID 0x%02x",
						parm.frequency/1000,
						m_pmt_in_progress->first);
					break;
				}
				case iDVBFrontend::feATSC:
				{
					eDVBFrontendParametersATSC parm;
					m_ch_current->getATSC(parm);
					snprintf(sname, 255, "%d SID 0x%02x",
						parm.frequency/1000,
						m_pmt_in_progress->first);
					break;
				}
			}
			SCAN_eDebug("[eDVBScan] name '%s', provider_name '%s'", sname, pname);
			int tsonid = 0;
			if( m_chid_current )
				tsonid = ( m_chid_current.transport_stream_id.get() << 16 )
					| m_chid_current.original_network_id.get();
			service->m_service_name = strip_non_graph(convertDVBUTF8(sname,-1,tsonid,0));
			service->genSortName();
			service->m_provider_name = strip_non_graph(convertDVBUTF8(pname,-1,tsonid,0));
		}

		if (!(m_flags & scanOnlyFree) || !m_pmt_in_progress->second.scrambled) {
			SCAN_eDebug("[eDVBScan] add not scrambled!");
			std::pair<std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator, bool> i =
				m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));
			if (i.second)
			{
				m_last_service = i.first;
				m_event(evtNewService);
			}
		}
		else
			SCAN_eDebug("[eDVBScan] dont add... is scrambled!");
		m_pmts_to_read.erase(m_pmt_in_progress++);
	}

	if (!m_chid_current)
		eWarning("[eDVBScan] the current channel's ID was not corrected - not adding channel.");
	else
	{
		addKnownGoodChannel(m_chid_current, m_ch_current);
		if (m_chid_current)
		{
			switch(type)
			{
				case iDVBFrontend::feSatellite:
				case iDVBFrontend::feTerrestrial:
				case iDVBFrontend::feCable:
				case iDVBFrontend::feATSC:
				{
					ePtr<iDVBFrontend> fe;
					if (!m_channel->getFrontend(fe))
					{
						int frequency = fe->readFrontendData(iFrontendInformation_ENUMS::frequency);
//						eDebug("[eDVBScan] add tuner data for tsid %04x, onid %04x, ns %08x",
//							m_chid_current.transport_stream_id.get(), m_chid_current.original_network_id.get(),
//							m_chid_current.dvbnamespace.get());
						m_tuner_data.insert(std::pair<eDVBChannelID, int>(m_chid_current, frequency));
					}
				}
				default:
					break;
			}
		}
	}

	m_ch_scanned.push_back(m_ch_current);

	for (std::list<ePtr<iDVBFrontendParameters> >::iterator i(m_ch_toScan.begin()); i != m_ch_toScan.end();)
	{
		if (sameChannel(*i, m_ch_current))
		{
			SCAN_eDebug("[eDVBScan] remove dupe 2");
			m_ch_toScan.erase(i++);
			continue;
		}
		++i;
	}

	nextChannel();
}

void eDVBScan::start(const eSmartPtrList<iDVBFrontendParameters> &known_transponders, int flags, int networkid)
{
	std::list<ePtr<iDVBFrontendParameters> > *transponderlist = &m_ch_toScan;
	m_flags = flags;
	m_networkid = networkid;
	m_ch_toScan.clear();
	m_ch_scanned.clear();
	m_ch_unavailable.clear();
	m_ch_blindscan.clear();
	m_new_channels.clear();
	m_tuner_data.clear();
	m_new_services.clear();
	m_last_service = m_new_services.end();

	if (m_lcn_file)
		fclose(m_lcn_file);
		
	if (m_flags & scanRemoveServices)
	{
		m_lcn_file = fopen(eEnv::resolve("${sysconfdir}/enigma2/lcndb").c_str(), "w");
		if (!m_lcn_file)
			eDebug("[eDVBScan] couldn't open file lcndb");
	}
	else
	{
		m_lcn_file = fopen(eEnv::resolve("${sysconfdir}/enigma2/lcndb").c_str(), "r+");
		if (!m_lcn_file)
		{
			m_lcn_file = fopen(eEnv::resolve("${sysconfdir}/enigma2/lcndb").c_str(), "w");
			if (!m_lcn_file)
				eDebug("[eDVBScan] couldn't open file lcndb");
		}
	}

	if (m_flags & scanBlindSearch)
	{
		/*
		 * NOTE: for blindscan, the initial list of transponders does not need to contain valid transponders.
		 * Each of the provided transponders will be iterated (i.e. tuned with blindscan parameter) several times
		 * until a tune failure occurs. Each time a blindscan tune iteration returns ok,
		 * a new transponder has been found and will be scanned.
		 * Each transponder in the initial transponder list causes a full blindscan iteration run.
		 *
		 * Some of the parameters of the initial transponders will be used for the blindscan,
		 * but most will be ignored.
		 *
		 * For DVB-S, you need to provide a list of 4 transponders for each orbital position:
		 * one for each polarity (H/V or L/R), one for each band (hi/lo).
		 * The frequency defines the starting frequency within the desired band.
		 * The symbolrate defines the frequency search range, in MHz (frequency / 1000).
		 * The polarity defines on which polarity the search should run.
		 * All remaining transponder parameters will be ignored.
		 * So for each orbital position, 4 blindscan iteration runs will be done, one for each polarity/band 'quadrant'.
		 *
		 * For DVB-C, only one initial transponder has to be provided.
		 * The frequency defines the start of the blindscan.
		 * The symbolrate defines the frequency search range, in MHz (frequency / 1000000).
		 *
		 * For DVB-T, usually only one initial transponder has to be provided.
		 * The frequency defines the start of the blindscan.
		 * The bandwidth defines both the search step as well as the search bandwidth.
		 */

		SCAN_eDebug("[eDVBScan] blind scan requested");
		transponderlist = &m_ch_blindscan;
	}


	for (eSmartPtrList<iDVBFrontendParameters>::const_iterator i(known_transponders.begin()); i != known_transponders.end(); ++i)
	{
		bool exist=false;
		for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator ii(transponderlist->begin()); ii != transponderlist->end(); ++ii)
		{
			if (sameChannel(*i, *ii, true))
			{
				exist=true;
				break;
			}
		}
		if (!exist)
			transponderlist->push_back(*i);
	}

	nextChannel();
}

void eDVBScan::insertInto(iDVBChannelList *db, bool backgroundscanresult)
{
	if (m_flags & scanRemoveServices)
	{
		bool clearTerrestrial=false;
		bool clearCable=false;
		std::set<unsigned int> scanned_sat_positions;

		std::list<ePtr<iDVBFrontendParameters> >::iterator it(m_ch_scanned.begin());
		for (;it != m_ch_scanned.end(); ++it)
		{
			if (m_flags & scanDontRemoveUnscanned)
				db->removeServices(&(*(*it)));
			else
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
					case iDVBFrontend::feATSC:
					{
						eDVBFrontendParametersATSC parm;
						(*it)->getATSC(parm);
						if (parm.system == eDVBFrontendParametersATSC::System_ATSC)
							clearTerrestrial = true;
						else
							clearCable = true;
						break;
					}
				}
			}
		}

		for (it=m_ch_unavailable.begin();it != m_ch_unavailable.end(); ++it)
		{
			if (m_flags & scanDontRemoveUnscanned)
				db->removeServices(&(*(*it)));
			else
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
					case iDVBFrontend::feATSC:
					{
						eDVBFrontendParametersATSC parm;
						(*it)->getATSC(parm);
						if (parm.system == eDVBFrontendParametersATSC::System_ATSC)
							clearTerrestrial = true;
						else
							clearCable = true;
						break;
					}
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
//			eDebug("[eDVBScan] remove %d %08x", *x, chid.dvbnamespace.get());
			db->removeServices(chid, *x);
		}
	}

	for (std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> >::const_iterator
			ch(m_new_channels.begin()); ch != m_new_channels.end(); ++ch)
	{
		int system;
		ch->second->getSystem(system);
		std::map<eDVBChannelID, int>::iterator it = m_tuner_data.find(ch->first);

		switch(system)
		{
			case iDVBFrontend::feTerrestrial:
			{
				eDVBFrontendParameters *p = (eDVBFrontendParameters*)&(*ch->second);
				eDVBFrontendParametersTerrestrial parm;
				int freq = it->second;
				p->getDVBT(parm);
//				eDebug("[eDVBScan] corrected freq for tsid %04x, onid %04x, ns %08x is %d, old was %d",
//					ch->first.transport_stream_id.get(), ch->first.original_network_id.get(),
//					ch->first.dvbnamespace.get(), freq, parm.frequency);
				parm.frequency = freq;
				p->setDVBT(parm);
				break;
			}
			case iDVBFrontend::feSatellite: // no update of any transponder parameter yet
			case iDVBFrontend::feCable:
			case iDVBFrontend::feATSC:
				break;
		}

		if (m_flags & scanOnlyFree)
		{
			eDVBFrontendParameters *ptr = (eDVBFrontendParameters*)&(*ch->second);
			ptr->setFlags(iDVBFrontendParameters::flagOnlyFree);
		}

		db->addChannelToList(ch->first, ch->second);
	}

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
			if (service->second->m_ca.size())
				dvb_service->m_ca = service->second->m_ca;
			if (!backgroundscanresult) // do not remove new found flags when this is the result of a 'background scan'
				dvb_service->m_flags &= ~eDVBService::dxNewFound;
		}
		else
		{
			db->addService(service->first, service->second);
			if (!(m_flags & scanRemoveServices))
				service->second->m_flags |= eDVBService::dxNewFound;
		}
	}

	if (!backgroundscanresult)
	{
		/* only create a 'Last Scanned' bouquet when this is not the result of a background scan */
		std::string bouquetname = "userbouquet.LastScanned.tv";
		std::string bouquetquery = "FROM BOUQUET \"" + bouquetname + "\" ORDER BY bouquet";
		eServiceReference bouquetref(eServiceReference::idDVB, eServiceReference::flagDirectory, bouquetquery);
		bouquetref.setData(0, 1); /* set bouquet 'servicetype' to tv (even though we probably have both tv and radio channels) */
		eBouquet *bouquet = NULL;
		eServiceReference rootref(eServiceReference::idDVB, eServiceReference::flagDirectory, "FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet");
		if (!db->getBouquet(bouquetref, bouquet) && bouquet)
		{
			/* bouquet already exists, empty it before we continue */
			bouquet->m_services.clear();
		}
		else
		{
			/* bouquet doesn't yet exist, create a new one */
			if (!db->getBouquet(rootref, bouquet) && bouquet)
			{
				bouquet->m_services.push_back(bouquetref);
				bouquet->flushChanges();
			}
			/* loading the bouquet seems to be the only way to add it to the bouquet list */
			eDVBDB *dvbdb = eDVBDB::getInstance();
			if (dvbdb) dvbdb->loadBouquet(bouquetname.c_str());
			/* and now that it has been added to the list, we can find it */
			db->getBouquet(bouquetref, bouquet);
		}
		if (bouquet)
		{
			bouquet->m_bouquet_name = "Last Scanned";

			for (std::map<eServiceReferenceDVB, ePtr<eDVBService> >::const_iterator
				service(m_new_services.begin()); service != m_new_services.end(); ++service)
			{
				bouquet->m_services.push_back(service->first);
			}
			bouquet->flushChanges();
			eDVBDB::getInstance()->renumberBouquet();
		}
		else
		{
			eDebug("[eDVBScan] failed to create 'Last Scanned' bouquet!");
		}
	}
}

RESULT eDVBScan::processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionSection &sdt)
{
	const ServiceDescriptionList &services = *sdt.getDescriptions();
	SCAN_eDebug("[eDVBScan] ONID: %04x", sdt.getOriginalNetworkId());
	eDVBChannelID chid(dvbnamespace, sdt.getTransportStreamId(), sdt.getOriginalNetworkId());

	/* save correct CHID for this channel */
	m_chid_current = chid;

	for (ServiceDescriptionConstIterator s(services.begin()); s != services.end(); ++s)
	{
		unsigned short service_id = (*s)->getServiceId();
		SCAN_eDebugNoNewLineStart("[eDVBScan] SID %04x: ", service_id);
		bool is_crypted = false;

		std::map<unsigned short, service>::iterator it = m_pmts_to_read.find(service_id);
		if (it != m_pmts_to_read.end())
		{
			if (it->second.scrambled)
			{
				SCAN_eDebugNoNewLineEnd("is scrambled!");
				is_crypted = true;
			}
			else
				SCAN_eDebugNoNewLineEnd("is free");
		}
		SCAN_eDebugNoNewLine("\n");

		if (!(m_flags & scanOnlyFree) || !is_crypted)
		{
			eServiceReferenceDVB ref;
			ePtr<eDVBService> service = new eDVBService;

			ref.set(chid);
			ref.setServiceID(service_id);

			for (DescriptorConstIterator desc = (*s)->getDescriptors()->begin();
					desc != (*s)->getDescriptors()->end(); ++desc)
			{
				switch ((*desc)->getTag())
				{
				case SERVICE_DESCRIPTOR:
				{
					ServiceDescriptor &d = (ServiceDescriptor&)**desc;
					int servicetype = d.getServiceType();

					/* NA scanning hack */
					switch (servicetype)
					{
					/* DISH/BEV servicetypes: */
					case 128:
					case 133:
					case 137:
					case 144:
					case 145:
					case 150:
					case 154:
					case 163:
					case 164:
					case 166:
					case 167:
					case 168:
						servicetype = 1;
						break;
					}
					/* */

					ref.setServiceType(servicetype);
					int tsonid=(sdt.getTransportStreamId() << 16) | sdt.getOriginalNetworkId();
					service->m_service_name = strip_non_graph(convertDVBUTF8(d.getServiceName(),-1,tsonid,0));
					service->genSortName();

					service->m_provider_name = strip_non_graph(convertDVBUTF8(d.getServiceProviderName(),-1,tsonid,0));
					SCAN_eDebug("[eDVBScan]   name '%s', provider_name '%s'", service->m_service_name.c_str(), service->m_provider_name.c_str());
					break;
				}
				case CA_IDENTIFIER_DESCRIPTOR:
				{
					CaIdentifierDescriptor &d = (CaIdentifierDescriptor&)**desc;
					const CaSystemIdList &caids = *d.getCaSystemIds();
					SCAN_eDebugNoNewLineStart("[eDVBScan] CA");
					for (CaSystemIdList::const_iterator i(caids.begin()); i != caids.end(); ++i)
					{
						SCAN_eDebugNoNewLine(" %04x", *i);
						service->m_ca.push_front(*i);
					}
					SCAN_eDebugNoNewLine("\n");
					break;
				}
				default:
					SCAN_eDebug("[eDVBScan]   descr<%x>", (*desc)->getTag());
					break;
				}
			}

			if (is_crypted and !service->m_ca.size())
				service->m_ca.push_front(0);

			std::pair<std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator, bool> i =
				m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));

			if (i.second)
			{
				m_last_service = i.first;
				m_event(evtNewService);
			}
		}
		if (m_pmt_running && m_pmt_in_progress->first == service_id)
			m_abort_current_pmt = true;
		else
			m_pmts_to_read.erase(service_id);
	}

	return 0;
}

RESULT eDVBScan::processVCT(eDVBNamespace dvbnamespace, const VirtualChannelTableSection &vct, int onid)
{
	const VirtualChannelList &services = *vct.getChannels();
	eDVBChannelID chid(dvbnamespace, vct.getTransportStreamId(), eOriginalNetworkID(onid));

	/* save correct CHID for this channel */
	m_chid_current = chid;

	for (VirtualChannelListConstIterator s(services.begin()); s != services.end(); ++s)
	{
		unsigned short service_id = (*s)->getServiceId();
		unsigned short source_id = (*s)->getSourceId();
		SCAN_eDebugNoNewLineStart("[eDVBScan] SID %04x, source_id %04x: ", service_id, source_id);
		bool is_crypted = (*s)->isAccessControlled();

		if (is_crypted)
		{
			SCAN_eDebugNoNewLine("is scrambled!");
		}
		else
		{
			SCAN_eDebugNoNewLine("is free");
		}
		SCAN_eDebugNoNewLine("\n");

		if (!(m_flags & scanOnlyFree) || !is_crypted)
		{
			char number[32];
			eServiceReferenceDVB ref;
			ePtr<eDVBService> service = new eDVBService;
			int servicetype = -1;

			if (((*s)->getMajorChannelNumber() & 0x3f0) == 0x3f0)
			{
				snprintf(number, sizeof(number), "%d ", (((*s)->getMajorChannelNumber() & 0x00f) << 10) | (*s)->getMinorChannelNumber());
			}
			else
			{
				snprintf(number, sizeof(number), "%d-%d ", (*s)->getMajorChannelNumber(), (*s)->getMinorChannelNumber());
			}

			switch ((*s)->getServiceType())
			{
			default:
			case 1: /* analog tv */
				break;
			case 2: /* ATSC digital tv */
				servicetype = 1;
				break;
			case 3: /* ATSC audio */
				servicetype = 2;
				break;
			}

			ref.set(chid);
			ref.setServiceID(service_id);
			ref.setServiceType(servicetype);
			ref.setSourceID(source_id);
			service->m_service_name = (*s)->getName();
			/* strip trailing spaces */
			service->m_service_name = service->m_service_name.erase(service->m_service_name.find_last_not_of(" ") + 1);
			/* strip leading spaces */
			service->m_service_name = service->m_service_name.erase(0, service->m_service_name.find_first_not_of(" "));

			for (DescriptorConstIterator desc = (*s)->getDescriptors()->begin();
					desc != (*s)->getDescriptors()->end(); ++desc)
			{
				switch ((*desc)->getTag())
				{
				case 0xa0: /* extended name descriptor */
				{
					ExtendedChannelNameDescriptor &d = (ExtendedChannelNameDescriptor&)**desc;
					if (d.getName().length())
					{
						service->m_service_name = d.getName();
					}
					break;
				}
				default:
					SCAN_eDebug("[eDVBScan]   descr<%x>", (*desc)->getTag());
					break;
				}
			}

			service->m_service_name = number + service->m_service_name;

			if (is_crypted and !service->m_ca.size())
				service->m_ca.push_front(0);

			std::pair<std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator, bool> i =
				m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));

			if (i.second)
			{
				m_last_service = i.first;
				m_event(evtNewService);
			}
		}
		if (m_pmt_running && m_pmt_in_progress->first == service_id)
			m_abort_current_pmt = true;
		else
			m_pmts_to_read.erase(service_id);
	}

	return 0;
}

RESULT eDVBScan::connectEvent(const sigc::slot1<void,int> &event, ePtr<eConnection> &connection)
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

void eDVBScan::getLastServiceRef(std::string &last_service_ref)
{
	if (m_last_service == m_new_services.end())
		last_service_ref = "";
	else
		last_service_ref = m_last_service->first.toString();
}

RESULT eDVBScan::getFrontend(ePtr<iDVBFrontend> &fe)
{
	if (m_channel)
		return m_channel->getFrontend(fe);
	fe = 0;
	return -1;
}

RESULT eDVBScan::getCurrentTransponder(ePtr<iDVBFrontendParameters> &tp)
{
	if (m_ch_blindscan_result)
	{
		tp = m_ch_blindscan_result;
		return 0;
	}
	else if (m_ch_current)
	{
		tp = m_ch_current;
		return 0;
	}
	tp = 0;
	return -1;
}
