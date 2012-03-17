#include <lib/dvb/idvb.h>
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/service_descriptor.h>
#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/ca_identifier_descriptor.h>
#include <dvbsi++/registration_descriptor.h>
#include <lib/dvb/specs.h>
#include <lib/dvb/esection.h>
#include <lib/dvb/scan.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/python/python.h>
#include <errno.h>

#define SCAN_eDebug(x...) do { if (m_scan_debug) eDebug(x); } while(0)
#define SCAN_eDebugNoNewLine(x...) do { if (m_scan_debug) eDebugNoNewLine(x); } while(0)

DEFINE_REF(eDVBScan);

eDVBScan::eDVBScan(iDVBChannel *channel, bool usePAT, bool debug)
	:m_channel(channel), m_channel_state(iDVBChannel::state_idle)
	,m_ready(0), m_ready_all(usePAT ? (readySDT|readyPAT) : readySDT)
	,m_pmt_running(false), m_abort_current_pmt(false), m_flags(0)
	,m_usePAT(usePAT), m_scan_debug(debug), m_show_add_tsid_onid_check_failed_msg(true)
{
	if (m_channel->getDemux(m_demux))
		SCAN_eDebug("scan: failed to allocate demux!");
	m_channel->connectStateChange(slot(*this, &eDVBScan::stateChange), m_stateChanged_connection);
	std::string filename = eEnv::resolve("${sysconfdir}/scan_tp_valid_check.py");
	FILE *f = fopen(filename.c_str(), "r");
	if (f)
	{
		char code[16384];
		size_t rd = fread(code, 1, 16383, f);
		if (rd)
		{
			code[rd]=0;
			m_additional_tsid_onid_check_func = Py_CompileString(code, filename.c_str(), Py_file_input);
		}
		fclose(f);
	}
}

eDVBScan::~eDVBScan()
{
	if (m_additional_tsid_onid_check_func)
		Py_DECREF(m_additional_tsid_onid_check_func);
}

int eDVBScan::isValidONIDTSID(int orbital_position, eOriginalNetworkID onid, eTransportStreamID tsid)
{
	/*
	 * Assume cable and terrestrial ONIDs/TSIDs are always valid,
	 * don't check them against the satellite blacklist.
	 */
	if (orbital_position == 0xFFFF || orbital_position == 0xEEEE) return 1;

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
		ret = abs(orbital_position-282) < 6 && tsid != 2019;
		// 12070H and 10936V have same tsid/onid.. but even the same services are provided
		break;
	case 0x2000:
		ret = tsid != 0x1000;
		break;
	case 0x5E: // Sirius 4.8E 12322V and 12226H
		ret = abs(orbital_position-48) < 3 && tsid != 1;
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
		ret = abs(orbital_position-3592) < 3 && tsid != 46;
		break;
	case 32: // NSS 806 (40.5W) 4059R, 3774L
		ret = orbital_position != 3195 || tsid != 21;
		break;
	default:
		ret = onid.get() < 0xFF00;
		break;
	}
	if (ret && m_additional_tsid_onid_check_func)
	{
		bool failed = true;
		ePyObject dict = PyDict_New();
		extern void PutToDict(ePyObject &, const char *, long);
		PyDict_SetItemString(dict, "__builtins__", PyEval_GetBuiltins());
		PutToDict(dict, "orbpos", orbital_position);
		PutToDict(dict, "tsid", tsid.get());
		PutToDict(dict, "onid", onid.get());
		ePyObject r = PyEval_EvalCode((PyCodeObject*)(PyObject*)m_additional_tsid_onid_check_func, dict, dict);
		if (r)
		{
			ePyObject o = PyDict_GetItemString(dict, "ret");
			if (o)
			{
				if (PyInt_Check(o))
				{
					ret = PyInt_AsLong(o);
					failed = false;
				}
			}
			Py_DECREF(r);
		}
		if (failed && m_show_add_tsid_onid_check_failed_msg)
		{
			eDebug("execing /etc/enigma2/scan_tp_valid_check failed!\n"
				"usable global variables in scan_tp_valid_check.py are 'orbpos', 'tsid', 'onid'\n"
				"the return value must be stored in a global var named 'ret'");
			m_show_add_tsid_onid_check_failed_msg=false;
		}
		Py_DECREF(dict);
	}
	return ret;
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

	if (m_ch_toScan.empty())
	{
		SCAN_eDebug("no channels left to scan.");
		SCAN_eDebug("%zd channels scanned, %zd were unavailable.",
				m_ch_scanned.size(), m_ch_unavailable.size());
		SCAN_eDebug("%zd channels in database.", m_new_channels.size());
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

	m_chid_current = eDVBChannelID();

	m_channel_state = iDVBChannel::state_idle;

	if (fe->tune(*m_ch_current))
		return nextChannel();

	m_event(evtUpdate);
	return 0;
}

RESULT eDVBScan::startFilter()
{
	bool startSDT=true;
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
					if ((tsid == 0x00d7 && abs(parm.frequency-618000) < 2000) ||
						(tsid == 0x00d8 && abs(parm.frequency-626000) < 2000))
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
	SCAN_eDebug("got sdt %d", err);
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

void eDVBScan::PATready(int err)
{
	SCAN_eDebug("got pat");
	m_ready |= readyPAT;
	if (!err)
		m_ready |= validPAT;
	startFilter(); // for starting the SDT filter
}

void eDVBScan::PMTready(int err)
{
	SCAN_eDebug("got pmt %d", err);
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
				SCAN_eDebug("already have a pcrpid %04x %04x", pcrpid, pmt.getPcrPid());
			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int isaudio = 0, isvideo = 0, is_scrambled = 0, forced_audio = 0, forced_video = 0;
				switch ((*es)->getType())
				{
				case 0x1b: // AVC Video Stream (MPEG4 H264)
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

void eDVBScan::addChannelToScan(const eDVBChannelID &chid, iDVBFrontendParameters *feparm)
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
		SCAN_eDebug("try to add %d %d %d %d %d %d",
			parm.orbital_position, parm.frequency, parm.symbol_rate, parm.polarisation, parm.fec, parm.modulation);
		break;
	}
	case iDVBFrontend::feCable:
	{
		eDVBFrontendParametersCable parm;
		feparm->getDVBC(parm);
		SCAN_eDebug("try to add %d %d %d %d",
			parm.frequency, parm.symbol_rate, parm.modulation, parm.fec_inner);
		break;
	}
	case iDVBFrontend::feTerrestrial:
	{
		eDVBFrontendParametersTerrestrial parm;
		feparm->getDVBT(parm);
		SCAN_eDebug("try to add %d %d %d %d %d %d %d %d",
			parm.frequency, parm.modulation, parm.transmission_mode, parm.hierarchy,
			parm.guard_interval, parm.code_rate_LP, parm.code_rate_HP, parm.bandwidth);
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
				SCAN_eDebug("update");
			}
			else
			{
				SCAN_eDebug("remove dupe");
				m_ch_toScan.erase(i++);
				continue;
			}
			++found_count;
		}
		++i;
	}

	if (found_count > 0)
	{
		SCAN_eDebug("already in todo list");
		return;
	}

		/* ... in the list of successfully scanned channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_scanned.begin()); i != m_ch_scanned.end(); ++i)
		if (sameChannel(*i, feparm))
		{
			SCAN_eDebug("successfully scanned");
			return;
		}

		/* ... in the list of unavailable channels */
	for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator i(m_ch_unavailable.begin()); i != m_ch_unavailable.end(); ++i)
		if (sameChannel(*i, feparm, true))
		{
			SCAN_eDebug("scanned but not available");
			return;
		}

		/* ... on the current channel */
	if (sameChannel(m_ch_current, feparm))
	{
		SCAN_eDebug("is current");
		return;
	}

	SCAN_eDebug("really add");
		/* otherwise, add it to the todo list. */
	m_ch_toScan.push_front(feparm); // better.. then the rotor not turning wild from east to west :)
}

int eDVBScan::sameChannel(iDVBFrontendParameters *ch1, iDVBFrontendParameters *ch2, bool exact) const
{
	int diff;
	if (ch1->calculateDifference(ch2, diff, exact))
		return 0;
	if (diff < 4000) // more than 4mhz difference?
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
		
		SCAN_eDebug("SDT: ");
		std::vector<ServiceDescriptionSection*>::const_iterator i;
		for (i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
			processSDT(dvbnamespace, **i);
		m_ready &= ~validSDT;
	}
	
	if (m_ready & validNIT)
	{
		int system;
		std::list<ePtr<iDVBFrontendParameters> > m_ch_toScan_backup;
		m_ch_current->getSystem(system);
		SCAN_eDebug("dumping NIT");
		if (m_flags & clearToScanOnFirstNIT)
		{
			m_ch_toScan_backup = m_ch_toScan;
			m_ch_toScan.clear();
		}
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
						if (system != iDVBFrontend::feCable)
							break; // when current locked transponder is no cable transponder ignore this descriptor
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
						if (system != iDVBFrontend::feTerrestrial)
							break; // when current locked transponder is no terrestrial transponder ignore this descriptor
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

						if ( abs(p.orbital_position - sat.orbital_position) < 5 )
							sat.orbital_position = p.orbital_position;

						if ( abs(abs(3600 - p.orbital_position) - sat.orbital_position) < 5 )
						{
							SCAN_eDebug("found transponder with incorrect west/east flag ... correct this");
							sat.orbital_position = p.orbital_position;
						}

						feparm->setDVBS(sat);

						if ( p.orbital_position != sat.orbital_position)
							SCAN_eDebug("dropping this transponder, it's on another satellite.");
						else
						{
							unsigned long hash=0;
							feparm->getHash(hash);
							addChannelToScan(
									eDVBChannelID(buildNamespace(onid, tsid, hash), tsid, onid),
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

			/* a pitfall is to have the clearToScanOnFirstNIT-flag set, and having channels which have
			   no or invalid NIT. this code will not erase the toScan list unless at least one valid entry
			   has been found.

			   This is not a perfect solution, as the channel could contain a partial NIT. Life's bad.
			*/
		if (m_flags & clearToScanOnFirstNIT)
		{
			if (m_ch_toScan.empty())
			{
				eWarning("clearToScanOnFirstNIT was set, but NIT is invalid. Refusing to stop scan.");
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
			SCAN_eDebug("SID %04x is VIDEO", m_pmt_in_progress->first);
		else if (m_pmt_in_progress->second.serviceType == 2)
			SCAN_eDebug("SID %04x is AUDIO", m_pmt_in_progress->first);
		else
			SCAN_eDebug("SID %04x is DATA", m_pmt_in_progress->first);

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
						parm.modulation == 1 ? "QPSK" : "8PSK",
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
			}
			SCAN_eDebug("name '%s', provider_name '%s'", sname, pname);
			service->m_service_name = convertDVBUTF8(sname);
			service->genSortName();
			service->m_provider_name = convertDVBUTF8(pname);
		}

		if (!(m_flags & scanOnlyFree) || !m_pmt_in_progress->second.scrambled) {
			SCAN_eDebug("add not scrambled!");
			std::pair<std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator, bool> i =
				m_new_services.insert(std::pair<eServiceReferenceDVB, ePtr<eDVBService> >(ref, service));
			if (i.second)
			{
				m_last_service = i.first;
				m_event(evtNewService);
			}
		}
		else
			SCAN_eDebug("dont add... is scrambled!");
		m_pmts_to_read.erase(m_pmt_in_progress++);
	}

	if (!m_chid_current)
		eWarning("SCAN: the current channel's ID was not corrected - not adding channel.");
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
				{
					ePtr<iDVBFrontend> fe;
					if (!m_channel->getFrontend(fe))
					{
						ePyObject tp_dict = PyDict_New();
						fe->getTransponderData(tp_dict, false);
//						eDebug("add tuner data for tsid %04x, onid %04x, ns %08x",
//							m_chid_current.transport_stream_id.get(), m_chid_current.original_network_id.get(),
//							m_chid_current.dvbnamespace.get());
						m_tuner_data.insert(std::pair<eDVBChannelID, ePyObjectWrapper>(m_chid_current, tp_dict));
						Py_DECREF(tp_dict);
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
			SCAN_eDebug("remove dupe 2");
			m_ch_toScan.erase(i++);
			continue;
		}
		++i;
	}
	
	nextChannel();
}

void eDVBScan::start(const eSmartPtrList<iDVBFrontendParameters> &known_transponders, int flags, int networkid)
{
	m_flags = flags;
	m_networkid = networkid;
	m_ch_toScan.clear();
	m_ch_scanned.clear();
	m_ch_unavailable.clear();
	m_new_channels.clear();
	m_tuner_data.clear();
	m_new_services.clear();
	m_last_service = m_new_services.end();

	for (eSmartPtrList<iDVBFrontendParameters>::const_iterator i(known_transponders.begin()); i != known_transponders.end(); ++i)
	{
		bool exist=false;
		for (std::list<ePtr<iDVBFrontendParameters> >::const_iterator ii(m_ch_toScan.begin()); ii != m_ch_toScan.end(); ++ii)
		{
			if (sameChannel(*i, *ii, true))
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
	{
		int system;
		ch->second->getSystem(system);
		std::map<eDVBChannelID, ePyObjectWrapper>::iterator it = m_tuner_data.find(ch->first);

		switch(system)
		{
			case iDVBFrontend::feTerrestrial:
			{
				eDVBFrontendParameters *p = (eDVBFrontendParameters*)&(*ch->second);
				eDVBFrontendParametersTerrestrial parm;
				int freq = PyInt_AsLong(PyDict_GetItemString(it->second, "frequency"));
				p->getDVBT(parm);
//				eDebug("corrected freq for tsid %04x, onid %04x, ns %08x is %d, old was %d",
//					ch->first.transport_stream_id.get(), ch->first.original_network_id.get(),
//					ch->first.dvbnamespace.get(), freq, parm.frequency);
				parm.frequency = freq;
				p->setDVBT(parm);
				break;
			}
			case iDVBFrontend::feSatellite: // no update of any transponder parameter yet
			case iDVBFrontend::feCable:
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
		}
		else
		{
			eDebug("failed to create 'Last Scanned' bouquet!");
		}
	}
}

RESULT eDVBScan::processSDT(eDVBNamespace dvbnamespace, const ServiceDescriptionSection &sdt)
{
	const ServiceDescriptionList &services = *sdt.getDescriptions();
	SCAN_eDebug("ONID: %04x", sdt.getOriginalNetworkId());
	eDVBChannelID chid(dvbnamespace, sdt.getTransportStreamId(), sdt.getOriginalNetworkId());
	
	/* save correct CHID for this channel */
	m_chid_current = chid;

	for (ServiceDescriptionConstIterator s(services.begin()); s != services.end(); ++s)
	{
		unsigned short service_id = (*s)->getServiceId();
		SCAN_eDebugNoNewLine("SID %04x: ", service_id);
		bool add = true;

		if (m_flags & scanOnlyFree)
		{
			std::map<unsigned short, service>::iterator it =
				m_pmts_to_read.find(service_id);
			if (it != m_pmts_to_read.end())
			{
				if (it->second.scrambled)
				{
					SCAN_eDebug("is scrambled!");
					add = false;
				}
				else
					SCAN_eDebug("is free");
			}
			else {
				SCAN_eDebug("not found in PAT.. so we assume it is scrambled!!");
				add = false;
			}
		}

		if (add)
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
					service->m_service_name = convertDVBUTF8(d.getServiceName());
					service->genSortName();

					service->m_provider_name = convertDVBUTF8(d.getServiceProviderName());
					SCAN_eDebug("name '%s', provider_name '%s'", service->m_service_name.c_str(), service->m_provider_name.c_str());
					break;
				}
				case CA_IDENTIFIER_DESCRIPTOR:
				{
					CaIdentifierDescriptor &d = (CaIdentifierDescriptor&)**desc;
					const CaSystemIdList &caids = *d.getCaSystemIds();
					SCAN_eDebugNoNewLine("CA ");
					for (CaSystemIdList::const_iterator i(caids.begin()); i != caids.end(); ++i)
					{
						SCAN_eDebugNoNewLine("%04x ", *i);
						service->m_ca.push_front(*i);
					}
					SCAN_eDebug("");
					break;
				}
				default:
					SCAN_eDebug("descr<%x>", (*desc)->getTag());
					break;
				}
			}

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

RESULT eDVBScan::getFrontend(ePtr<iDVBFrontend> &fe)
{
	if (m_channel)
		return m_channel->getFrontend(fe);
	fe = 0;
	return -1;
}

RESULT eDVBScan::getCurrentTransponder(ePtr<iDVBFrontendParameters> &tp)
{
	if (m_ch_current)
	{
		tp = m_ch_current;
		return 0;
	}
	tp = 0;
	return -1;
}
