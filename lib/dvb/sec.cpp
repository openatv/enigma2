#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/dvb/rotor_calc.h>
#include <lib/dvb/dvbtime.h>

#include <set>

#if HAVE_DVB_API_VERSION < 3
#define FREQUENCY Frequency
#else
#define FREQUENCY frequency
#endif
#include <lib/base/eerror.h>

//#define SEC_DEBUG

#ifdef SEC_DEBUG
#define eSecDebug(arg...) eDebug(arg)
#else
#define eSecDebug(arg...)
#endif

DEFINE_REF(eDVBSatelliteEquipmentControl);

eDVBSatelliteEquipmentControl *eDVBSatelliteEquipmentControl::instance;

int eDVBSatelliteEquipmentControl::m_params[MAX_PARAMS];
/*
   defaults are set in python lib/python/Components/NimManager.py
   in InitSecParams function via setParam call
*/

void eDVBSatelliteEquipmentControl::setParam(int param, int value)
{
	if (param >= 0 && param < MAX_PARAMS)
		m_params[param]=value;
}

eDVBSatelliteEquipmentControl::eDVBSatelliteEquipmentControl(eSmartPtrList<eDVBRegisteredFrontend> &avail_frontends)
	:m_lnbidx(-1), m_curSat(m_lnbs[0].m_satellites.end()), m_avail_frontends(avail_frontends), m_rotorMoving(false)
{
	if (!instance)
		instance = this;

	clear();

// ASTRA
	addLNB();
	setLNBSlotMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11700000);
	setLNBLOFH(10607000);
	setDiSEqCMode(eDVBSatelliteDiseqcParameters::V1_0);
	setToneburst(eDVBSatelliteDiseqcParameters::NO);
	setRepeats(0);
	setCommittedCommand(eDVBSatelliteDiseqcParameters::BB);
	setCommandOrder(0); // committed, toneburst
	setFastDiSEqC(true);
	setSeqRepeat(false);
	addSatellite(192);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);

// Hotbird
	addLNB();
	setLNBSlotMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11700000);
	setLNBLOFH(10600000);
	setDiSEqCMode(eDVBSatelliteDiseqcParameters::V1_0);
	setToneburst(eDVBSatelliteDiseqcParameters::NO);
	setRepeats(0);
	setCommittedCommand(eDVBSatelliteDiseqcParameters::AB);
	setCommandOrder(0); // committed, toneburst
	setFastDiSEqC(true);
	setSeqRepeat(false);
	addSatellite(130);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);

// Rotor
	addLNB();
	setLNBSlotMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11700000);
	setLNBLOFH(10600000);
	setDiSEqCMode(eDVBSatelliteDiseqcParameters::V1_2);
	setToneburst(eDVBSatelliteDiseqcParameters::NO);
	setRepeats(0);
	setCommittedCommand(eDVBSatelliteDiseqcParameters::AA);
	setCommandOrder(0); // committed, toneburst
	setFastDiSEqC(true);
	setSeqRepeat(false);
	setLaDirection(eDVBSatelliteRotorParameters::NORTH);
	setLoDirection(eDVBSatelliteRotorParameters::EAST);
	setLatitude(51.017);
	setLongitude(8.683);
	setUseInputpower(true);
	setInputpowerDelta(50);

	addSatellite(235);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);
	setRotorPosNum(0);

	addSatellite(284);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);
	setRotorPosNum(0);

	addSatellite(420);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);
	setRotorPosNum(1); // stored pos 1
}

static void checkLinkedParams(int direction, long &linked_ptr, int &ret, const eDVBFrontendParametersSatellite &sat, int csw, int ucsw, int toneburst, bool diseqc, bool rotor, int RotorPos)
{
	eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*) linked_ptr;
	if (linked_fe->m_inuse)
	{
		long ocsw = -1,
			oucsw = -1,
			oToneburst = -1;
		linked_fe->m_frontend->getData(eDVBFrontend::CSW, ocsw);
		linked_fe->m_frontend->getData(eDVBFrontend::UCSW, oucsw);
		linked_fe->m_frontend->getData(eDVBFrontend::TONEBURST, oToneburst);
#if 0
		eDebug("compare csw %02x == lcsw %02x",
			csw, ocsw);
		if ( diseqc )
			eDebug("compare ucsw %02x == lucsw %02x\ncompare toneburst %02x == oToneburst %02x",
				ucsw, oucsw, toneburst, oToneburst);
		if ( rotor )
			eDebug("compare pos %d == current pos %d",
				sat.orbital_position, oRotorPos);
#endif
		if ( (csw != ocsw) ||
			( diseqc && (ucsw != oucsw || toneburst != oToneburst) ) ||
			( rotor && RotorPos != sat.orbital_position ) )
		{
//			eDebug("can not tune this transponder with linked tuner in use!!");
			ret=0;
		}
//		else
//			eDebug("OK .. can tune this transponder with linked tuner in use :)");
	}
	linked_fe->m_frontend->getData(direction, (long&)linked_ptr);
}

int eDVBSatelliteEquipmentControl::canTune(const eDVBFrontendParametersSatellite &sat, iDVBFrontend *fe, int slot_id )
{
	int ret=0, satcount=0;

	for (int idx=0; idx <= m_lnbidx; ++idx )
	{
		bool rotor=false;
		eDVBSatelliteLNBParameters &lnb_param = m_lnbs[idx];
		if ( lnb_param.slot_mask & slot_id ) // lnb for correct tuner?
		{
			eDVBSatelliteDiseqcParameters &di_param = lnb_param.m_diseqc_parameters;

			satcount += lnb_param.m_satellites.size();

			std::map<int, eDVBSatelliteSwitchParameters>::iterator sit =
				lnb_param.m_satellites.find(sat.orbital_position);
			if ( sit != lnb_param.m_satellites.end())
			{
				long band=0,
					linked_prev_ptr=-1,
					linked_next_ptr=-1,
					satpos_depends_ptr=-1,
					csw = di_param.m_committed_cmd,
					ucsw = di_param.m_uncommitted_cmd,
					toneburst = di_param.m_toneburst_param,
					curRotorPos;

				fe->getData(eDVBFrontend::ROTOR_POS, curRotorPos);
				fe->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
				fe->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
				fe->getData(eDVBFrontend::SATPOS_DEPENDS_PTR, satpos_depends_ptr);

				if ( sat.frequency > lnb_param.m_lof_threshold )
					band |= 1;
				if (!(sat.polarisation & eDVBFrontendParametersSatellite::Polarisation::Vertical))
					band |= 2;

				bool diseqc=false;

				if (di_param.m_diseqc_mode >= eDVBSatelliteDiseqcParameters::V1_0)
				{
					diseqc=true;
					if ( di_param.m_committed_cmd < eDVBSatelliteDiseqcParameters::SENDNO )
						csw = 0xF0 | (csw << 2);

					if (di_param.m_committed_cmd <= eDVBSatelliteDiseqcParameters::SENDNO)
						csw |= band;

					if ( di_param.m_diseqc_mode == eDVBSatelliteDiseqcParameters::V1_2 )  // ROTOR
						rotor = true;

					ret=10000;
					if (rotor && curRotorPos != -1)
						ret -= abs(curRotorPos-sat.orbital_position);
				}
				else
				{
					csw = band;
					ret = 15000;
				}

				while (ret && linked_prev_ptr != -1)  // check for linked tuners..
					checkLinkedParams(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr, ret, sat, csw, ucsw, toneburst, diseqc, rotor, curRotorPos);

				while (ret && linked_next_ptr != -1)  // check for linked tuners..
					checkLinkedParams(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr, ret, sat, csw, ucsw, toneburst, diseqc, rotor, curRotorPos);

				if (ret)
					if (satpos_depends_ptr != -1)
					{
						eDVBRegisteredFrontend *satpos_depends_to_fe = (eDVBRegisteredFrontend*) satpos_depends_ptr;
						if ( satpos_depends_to_fe->m_inuse )
						{
							if (!rotor || curRotorPos != sat.orbital_position)
							{
//								eDebug("can not tune this transponder ... rotor on other tuner is positioned to %d", oRotorPos);
								ret=0;
							}
						}
//						else
//							eDebug("OK .. can tune this transponder satpos is correct :)");
					}

				if (ret)
				{
					int lof = sat.frequency > lnb_param.m_lof_threshold ?
						lnb_param.m_lof_hi : lnb_param.m_lof_lo;
					int tuner_freq = abs(sat.frequency - lof);
//					eDebug("tuner freq %d", tuner_freq);
					if (tuner_freq < 900000 || tuner_freq > 2200000)
					{
						ret=0;
//						eDebug("Transponder not tuneable with this lnb... %d Khz out of tuner range",
//							tuner_freq);
					}
				}
			}
		}
	}
	if (ret && satcount)
		ret -= (satcount-1);
	if (ret && m_not_linked_slot_mask & slot_id)
		ret += 5; // increase score for tuners with direct sat connection
	return ret;
}

bool need_turn_fast(int turn_speed)
{
	if (turn_speed == eDVBSatelliteRotorParameters::FAST)
		return true;
	else if (turn_speed != eDVBSatelliteRotorParameters::SLOW)
	{
		int begin = turn_speed >> 16; // high word is start time
		int end = turn_speed&0xFFFF; // low word is end time
		time_t now_time = eDVBLocalTimeHandler::getInstance()->nowTime();
		tm nowTime;
		localtime_r(&now_time, &nowTime);
		int now = (nowTime.tm_hour + 1) * 60 + nowTime.tm_min + 1;
		bool neg = end <= begin;
		if (neg) {
			int tmp = begin;
			begin = end;
			end = tmp;
		}
		if ((now >= begin && now < end) ^ neg)
			return true;
	}
	return false;
}

#define VOLTAGE(x) (lnb_param.m_increased_voltage ? iDVBFrontend::voltage##x##_5 : iDVBFrontend::voltage##x)

RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, const eDVBFrontendParametersSatellite &sat, int slot_id)
{
	for (int idx=0; idx <= m_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = m_lnbs[idx];
		if (!(lnb_param.slot_mask & slot_id)) // lnb for correct tuner?
			continue;
		eDVBSatelliteDiseqcParameters &di_param = lnb_param.m_diseqc_parameters;
		eDVBSatelliteRotorParameters &rotor_param = lnb_param.m_rotor_parameters;

		std::map<int, eDVBSatelliteSwitchParameters>::iterator sit =
			lnb_param.m_satellites.find(sat.orbital_position);
		if ( sit != lnb_param.m_satellites.end())
		{
			eDVBSatelliteSwitchParameters &sw_param = sit->second;
			bool doSetFrontend = true;
			bool doSetVoltageToneFrontend = m_not_linked_slot_mask & slot_id;
			bool allowDiseqc1_2 = true;
			long band=0,
				voltage = iDVBFrontend::voltageOff,
				tone = iDVBFrontend::toneOff,
				csw = di_param.m_committed_cmd,
				ucsw = di_param.m_uncommitted_cmd,
				toneburst = di_param.m_toneburst_param,
				lastcsw = -1,
				lastucsw = -1,
				lastToneburst = -1,
				lastRotorCmd = -1,
				curRotorPos = -1,
				satposDependPtr = -1;

			frontend.getData(eDVBFrontend::CSW, lastcsw);
			frontend.getData(eDVBFrontend::UCSW, lastucsw);
			frontend.getData(eDVBFrontend::TONEBURST, lastToneburst);
			frontend.getData(eDVBFrontend::ROTOR_CMD, lastRotorCmd);
			frontend.getData(eDVBFrontend::ROTOR_POS, curRotorPos);
			frontend.getData(eDVBFrontend::SATPOS_DEPENDS_PTR, satposDependPtr);

			if (satposDependPtr != -1 && !doSetVoltageToneFrontend)
			{
				allowDiseqc1_2 = false;
				doSetVoltageToneFrontend = true;
			}

			if ( sat.frequency > lnb_param.m_lof_threshold )
				band |= 1;

			if (band&1)
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_hi;
			else
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_lo;

			parm.FREQUENCY = abs(parm.FREQUENCY);

			frontend.setData(eDVBFrontend::FREQ_OFFSET, sat.frequency - parm.FREQUENCY);

			if (!(sat.polarisation & eDVBFrontendParametersSatellite::Polarisation::Vertical))
				band |= 2;

			if ( sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::_14V
				|| ( sat.polarisation & eDVBFrontendParametersSatellite::Polarisation::Vertical
					&& sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::HV )  )
				voltage = VOLTAGE(13);
			else if ( sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::_18V
				|| ( !(sat.polarisation & eDVBFrontendParametersSatellite::Polarisation::Vertical)
					&& sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::HV )  )
				voltage = VOLTAGE(18);
			if ( (sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::ON)
				|| ( sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::HILO && (band&1) ) )
				tone = iDVBFrontend::toneOn;
			else if ( (sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::OFF)
				|| ( sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::HILO && !(band&1) ) )
				tone = iDVBFrontend::toneOff;

			eSecCommandList sec_sequence;

			if (di_param.m_diseqc_mode >= eDVBSatelliteDiseqcParameters::V1_0)
			{
				if ( di_param.m_committed_cmd < eDVBSatelliteDiseqcParameters::SENDNO )
					csw = 0xF0 | (csw << 2);

				if (di_param.m_committed_cmd <= eDVBSatelliteDiseqcParameters::SENDNO)
					csw |= band;

				bool send_csw =
					(di_param.m_committed_cmd != eDVBSatelliteDiseqcParameters::SENDNO);
				bool changed_csw = send_csw && csw != lastcsw;

				bool send_ucsw =
					(di_param.m_uncommitted_cmd && di_param.m_diseqc_mode > eDVBSatelliteDiseqcParameters::V1_0);
				bool changed_ucsw = send_ucsw && ucsw != lastucsw;

				bool send_burst =
					(di_param.m_toneburst_param != eDVBSatelliteDiseqcParameters::NO);
				bool changed_burst = send_burst && toneburst != lastToneburst;

				int send_mask = 0; /*
					1 must send csw
					2 must send ucsw
					4 send toneburst first
					8 send toneburst at end */
				if (changed_burst) // toneburst first and toneburst changed
				{
					if (di_param.m_command_order&1)
					{
						send_mask |= 4;
						if ( send_csw )
							send_mask |= 1;
						if ( send_ucsw )
							send_mask |= 2;
					}
					else
						send_mask |= 8;
				}
				if (changed_ucsw)
				{
					send_mask |= 2;
					if ((di_param.m_command_order&4) && send_csw)
						send_mask |= 1;
					if (di_param.m_command_order==4 && send_burst)
						send_mask |= 8;
				}
				if (changed_csw) 
				{
					if ( di_param.m_use_fast
						&& di_param.m_committed_cmd < eDVBSatelliteDiseqcParameters::SENDNO
						&& (lastcsw & 0xF0)
						&& ((csw / 4) == (lastcsw / 4)) )
						eDebug("dont send committed cmd (fast diseqc)");
					else
					{
						send_mask |= 1;
						if (!(di_param.m_command_order&4) && send_ucsw)
							send_mask |= 2;
						if (!(di_param.m_command_order&1) && send_burst)
							send_mask |= 8;
					}
				}

#if 0
				eDebugNoNewLine("sendmask: ");
				for (int i=3; i >= 0; --i)
					if ( send_mask & (1<<i) )
						eDebugNoNewLine("1");
					else
						eDebugNoNewLine("0");
				eDebug("");
#endif

				if (doSetVoltageToneFrontend)
				{
					int RotorCmd=-1;
					bool useGotoXX = false;
					if ( di_param.m_diseqc_mode == eDVBSatelliteDiseqcParameters::V1_2
						&& !sat.no_rotor_command_on_tune
						&& allowDiseqc1_2 )
					{
						if (sw_param.m_rotorPosNum) // we have stored rotor pos?
							RotorCmd=sw_param.m_rotorPosNum;
						else  // we must calc gotoxx cmd
						{
							eDebug("Entry for %d,%d? not in Rotor Table found... i try gotoXX?", sat.orbital_position / 10, sat.orbital_position % 10 );
							useGotoXX = true;
	
							double	SatLon = abs(sat.orbital_position)/10.00,
									SiteLat = rotor_param.m_gotoxx_parameters.m_latitude,
									SiteLon = rotor_param.m_gotoxx_parameters.m_longitude;
	
							if ( rotor_param.m_gotoxx_parameters.m_la_direction == eDVBSatelliteRotorParameters::SOUTH )
								SiteLat = -SiteLat;
	
							if ( rotor_param.m_gotoxx_parameters.m_lo_direction == eDVBSatelliteRotorParameters::WEST )
								SiteLon = 360 - SiteLon;
	
							eDebug("siteLatitude = %lf, siteLongitude = %lf, %lf degrees", SiteLat, SiteLon, SatLon );
							double satHourAngle =
								calcSatHourangle( SatLon, SiteLat, SiteLon );
							eDebug("PolarmountHourAngle=%lf", satHourAngle );
	
							static int gotoXTable[10] =
								{ 0x00, 0x02, 0x03, 0x05, 0x06, 0x08, 0x0A, 0x0B, 0x0D, 0x0E };
	
							if (SiteLat >= 0) // Northern Hemisphere
							{
								int tmp=(int)round( fabs( 180 - satHourAngle ) * 10.0 );
								RotorCmd = (tmp/10)*0x10 + gotoXTable[ tmp % 10 ];
	
								if (satHourAngle < 180) // the east
									RotorCmd |= 0xE000;
								else					// west
									RotorCmd |= 0xD000;
							}
							else // Southern Hemisphere
							{
								if (satHourAngle < 180) // the east
								{
									int tmp=(int)round( fabs( satHourAngle ) * 10.0 );
									RotorCmd = (tmp/10)*0x10 + gotoXTable[ tmp % 10 ];
									RotorCmd |= 0xD000;
								}
								else // west
								{
									int tmp=(int)round( fabs( 360 - satHourAngle ) * 10.0 );
									RotorCmd = (tmp/10)*0x10 + gotoXTable[ tmp % 10 ];
									RotorCmd |= 0xE000;
								}
							}
							eDebug("RotorCmd = %04x", RotorCmd);
						}
					}

					if ( send_mask )
					{
						int vlt = iDVBFrontend::voltageOff;
						eSecCommand::pair compare;
						compare.steps = +3;
						compare.tone = iDVBFrontend::toneOff;
						sec_sequence.push_back( eSecCommand(eSecCommand::IF_TONE_GOTO, compare) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_CONT_TONE]) );

						if ( RotorCmd != -1 && RotorCmd != lastRotorCmd )
						{
							if (rotor_param.m_inputpower_parameters.m_use)
								vlt = VOLTAGE(18);  // in input power mode set 18V for measure input power
							else
								vlt = VOLTAGE(13);  // in normal mode start turning with 13V
						}
						else
							vlt = voltage;

						// check if voltage is already correct..
						compare.voltage = vlt;
						compare.steps = +7;
						sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) );

						// check if voltage is disabled
						compare.voltage = iDVBFrontend::voltageOff;
						compare.steps = +4;
						sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) );

						// voltage is changed... use DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_SWITCH_CMDS
						sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, vlt) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_SWITCH_CMDS]) );
						sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, +3) );

						// voltage was disabled.. use DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_SWITCH_CMDS
						sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, vlt) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_SWITCH_CMDS]) );

						for (int seq_repeat = 0; seq_repeat < (di_param.m_seq_repeat?2:1); ++seq_repeat)
						{
							if ( send_mask & 4 )
							{
								sec_sequence.push_back( eSecCommand(eSecCommand::SEND_TONEBURST, di_param.m_toneburst_param) );
								sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_TONEBURST]) );
							}

							int loops=0;

							if ( send_mask & 1 )
								++loops;
							if ( send_mask & 2 )
								++loops;

							loops <<= di_param.m_repeats;

							for ( int i = 0; i < loops;)  // fill commands...
							{
								eDVBDiseqcCommand diseqc;
								diseqc.len = 4;
								diseqc.data[0] = i ? 0xE1 : 0xE0;
								diseqc.data[1] = 0x10;
								if ( (send_mask & 2) && (di_param.m_command_order & 4) )
								{
									diseqc.data[2] = 0x39;
									diseqc.data[3] = ucsw;
								}
								else if ( send_mask & 1 )
								{
									diseqc.data[2] = 0x38;
									diseqc.data[3] = csw;
								}
								else  // no committed command confed.. so send uncommitted..
								{
									diseqc.data[2] = 0x39;
									diseqc.data[3] = ucsw;
								}
								sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );

								i++;
								if ( i < loops )
								{
									int cmd=0;
									if (diseqc.data[2] == 0x38 && (send_mask & 2))
										cmd=0x39;
									else if (diseqc.data[2] == 0x39 && (send_mask & 1))
										cmd=0x38;
									int tmp = m_params[DELAY_BETWEEN_DISEQC_REPEATS];
									if (cmd)
									{
										int delay = di_param.m_repeats ? (tmp - 54) / 2 : tmp;  // standard says 100msek between two repeated commands
										sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, delay) );
										diseqc.data[2]=cmd;
										diseqc.data[3]=(cmd==0x38) ? csw : ucsw;
										sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
										++i;
										if ( i < loops )
											sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, delay ) );
										else
											sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_LAST_DISEQC_CMD]) );
									}
									else  // delay 120msek when no command is in repeat gap
										sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, tmp) );
								}
								else
									sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_LAST_DISEQC_CMD]) );
							}

							if ( send_mask & 8 )  // toneburst at end of sequence
							{
								sec_sequence.push_back( eSecCommand(eSecCommand::SEND_TONEBURST, di_param.m_toneburst_param) );
								sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_TONEBURST]) );
							}
						}
					}

					eDebug("RotorCmd %02x, lastRotorCmd %02lx", RotorCmd, lastRotorCmd);
					if ( RotorCmd != -1 && RotorCmd != lastRotorCmd )
					{
						eSecCommand::pair compare;
						if (!send_mask)
						{
							compare.steps = +3;
							compare.tone = iDVBFrontend::toneOff;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TONE_GOTO, compare) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_CONT_TONE]) );

							compare.voltage = iDVBFrontend::voltageOff;
							compare.steps = +4;
							// the next is a check if voltage is switched off.. then we first set a voltage :)
							// else we set voltage after all diseqc stuff..
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_NOT_VOLTAGE_GOTO, compare) );

							if (rotor_param.m_inputpower_parameters.m_use)
								sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, VOLTAGE(18)) ); // set 18V for measure input power
							else
								sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, VOLTAGE(13)) ); // in normal mode start turning with 13V

							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_MOTOR_CMD]) ); // wait 750ms when voltage was disabled
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, +9) );  // no need to send stop rotor cmd and recheck voltage
						}
						else
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_BETWEEN_SWITCH_AND_MOTOR_CMD]) ); // wait 700ms when diseqc changed

						eDVBDiseqcCommand diseqc;
						diseqc.len = 3;
						diseqc.data[0] = 0xE0;
						diseqc.data[1] = 0x31;	// positioner
						diseqc.data[2] = 0x60;	// stop
						sec_sequence.push_back( eSecCommand(eSecCommand::IF_ROTORPOS_VALID_GOTO, +5) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
						// wait 150msec after send rotor stop cmd
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_MOTOR_STOP_CMD]) );

						diseqc.data[0] = 0xE0;
						diseqc.data[1] = 0x31;		// positioner
						if ( useGotoXX )
						{
							diseqc.len = 5;
							diseqc.data[2] = 0x6E;	// drive to angular position
							diseqc.data[3] = ((RotorCmd & 0xFF00) / 0x100);
							diseqc.data[4] = RotorCmd & 0xFF;
						}
						else
						{
							diseqc.len = 4;
							diseqc.data[2] = 0x6B;	// goto stored sat position
							diseqc.data[3] = RotorCmd;
							diseqc.data[4] = 0x00;
						}

						if ( rotor_param.m_inputpower_parameters.m_use )
						{ // use measure rotor input power to detect rotor state
							eSecCommand::rotor cmd;
							eSecCommand::pair compare;
							compare.voltage = VOLTAGE(18);
							compare.steps = +3;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, compare.voltage) );
// measure idle power values
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MEASURE_IDLE_INPUTPOWER]) );  // wait 150msec after voltage change
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_IDLE_INPUTPOWER, 1) );
							compare.val = 1;
							compare.steps = -2;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_MEASURE_IDLE_WAS_NOT_OK_GOTO, compare) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, VOLTAGE(13)) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MEASURE_IDLE_INPUTPOWER]) );  // wait 150msec before measure
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_IDLE_INPUTPOWER, 0) );
							compare.val = 0;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_MEASURE_IDLE_WAS_NOT_OK_GOTO, compare) );
////////////////////////////
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeStatic) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_ROTOR_DISEQC_RETRYS, m_params[MOTOR_COMMAND_RETRIES]) );  // 2 retries
							sec_sequence.push_back( eSecCommand(eSecCommand::INVALIDATE_CURRENT_ROTORPARMS) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TIMEOUT, 40) );  // 2 seconds rotor start timout
// rotor start loop
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // 50msec delay
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_RUNNING_INPUTPOWER) );
							cmd.direction=1;  // check for running rotor
							cmd.deltaA=rotor_param.m_inputpower_parameters.m_delta;
							cmd.steps=+5;
							cmd.okcount=0;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_INPUTPOWER_DELTA_GOTO, cmd ) );  // check if rotor has started
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TIMEOUT_GOTO, +2 ) );  // timeout .. we assume now the rotor is already at the correct position
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -4) );  // goto loop start
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_NO_MORE_ROTOR_DISEQC_RETRYS_GOTO, +9 ) );  // timeout .. we assume now the rotor is already at the correct position
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -8) );  // goto loop start
////////////////////
							if (need_turn_fast(rotor_param.m_inputpower_parameters.m_turning_speed))
								sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, VOLTAGE(18)) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TIMEOUT, m_params[MOTOR_RUNNING_TIMEOUT]*20) );  // 2 minutes running timeout
// rotor running loop
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_RUNNING_INPUTPOWER) );
							cmd.direction=0;  // check for stopped rotor
							cmd.steps=+4;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_INPUTPOWER_DELTA_GOTO, cmd ) );
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TIMEOUT_GOTO, +3 ) );  // timeout ? this should never happen
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -4) );  // running loop start
/////////////////////
							sec_sequence.push_back( eSecCommand(eSecCommand::UPDATE_CURRENT_ROTORPARAMS) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeDynamic) );
						}
						else
						{  // use normal turning mode
							doSetVoltageToneFrontend=false;
							doSetFrontend=false;
							eSecCommand::rotor cmd;
							eSecCommand::pair compare;
							compare.voltage = VOLTAGE(13);
							compare.steps = +3;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, compare.voltage) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MOTOR_CMD]) );  // wait 150msec after voltage change

							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeStatic) );
							sec_sequence.push_back( eSecCommand(eSecCommand::INVALIDATE_CURRENT_ROTORPARMS) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );

							compare.voltage = voltage;
							compare.steps = +3;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) ); // correct final voltage?
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 2000) );  // wait 2 second before set high voltage
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );

							compare.tone = tone;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TONE_GOTO, compare) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, tone) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_CONT_TONE]) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );

							cmd.direction=1;  // check for running rotor
							cmd.deltaA=0;
							cmd.steps=+3;
							cmd.okcount=0;
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TIMEOUT, m_params[MOTOR_RUNNING_TIMEOUT]*4) );  // 2 minutes running timeout
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 250) );  // 250msec delay
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TUNER_LOCKED_GOTO, cmd ) );
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TIMEOUT_GOTO, +3 ) ); 
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -3) );  // goto loop start
							sec_sequence.push_back( eSecCommand(eSecCommand::UPDATE_CURRENT_ROTORPARAMS) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeDynamic) );
						}
						frontend.setData(eDVBFrontend::NEW_ROTOR_CMD, RotorCmd);
						frontend.setData(eDVBFrontend::NEW_ROTOR_POS, sat.orbital_position);
					}
				}
			}
			else
				csw = band;

			frontend.setData(eDVBFrontend::CSW, csw);
			frontend.setData(eDVBFrontend::UCSW, ucsw);
			frontend.setData(eDVBFrontend::TONEBURST, di_param.m_toneburst_param);

			if (doSetVoltageToneFrontend)
			{
				eSecCommand::pair compare;
				compare.voltage = voltage;
				compare.steps = +3;
				sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) ); // voltage already correct ?
				sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );
				sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_FINAL_VOLTAGE_CHANGE]) );
				compare.tone = tone;
				sec_sequence.push_back( eSecCommand(eSecCommand::IF_TONE_GOTO, compare) );
				sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, tone) );
				sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, m_params[DELAY_AFTER_CONT_TONE]) );
			}

			if (doSetFrontend)
			{
				sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT) );
				sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );
			}
			frontend.setSecSequence(sec_sequence);

			return 0;
		}
	}

	eDebug("found no useable satellite configuration for orbital position (%d)", sat.orbital_position );
	return -1;
}

RESULT eDVBSatelliteEquipmentControl::clear()
{
	eSecDebug("eDVBSatelliteEquipmentControl::clear()");
	for (int i=0; i <= m_lnbidx; ++i)
	{
		m_lnbs[i].m_satellites.clear();
		m_lnbs[i].slot_mask = 0;
	}
	m_lnbidx=-1;

	m_not_linked_slot_mask=0;

	//reset some tuner configuration
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it)
	{
		long tmp;
		if (!strcmp(it->m_frontend->getDescription(), "BCM4501 (internal)") && !it->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp) && tmp != -1)
		{
			FILE *f=fopen("/proc/stb/tsmux/lnb_b_input", "w");
			if (!f || fwrite("B", 1, 1, f) != 1)
				eDebug("set /proc/stb/tsmux/lnb_b_input to B failed!! (%m)");
			else
			{
				eDebug("set /proc/stb/tsmux/lnb_b_input to B OK");
				fclose(f);
			}
		}
		it->m_frontend->setData(eDVBFrontend::SATPOS_DEPENDS_PTR, -1);
		it->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, -1);
		it->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, -1);
		it->m_frontend->setData(eDVBFrontend::ROTOR_POS, -1);
		it->m_frontend->setData(eDVBFrontend::ROTOR_CMD, -1);
	}

	return 0;
}

/* LNB Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::addLNB()
{
	if ( (m_lnbidx+1) < (int)(sizeof(m_lnbs) / sizeof(eDVBSatelliteLNBParameters)))
		m_curSat=m_lnbs[++m_lnbidx].m_satellites.end();
	else
	{
		eDebug("no more LNB free... cnt is %d", m_lnbidx);
		return -ENOSPC;
	}
	eSecDebug("eDVBSatelliteEquipmentControl::addLNB(%d)", m_lnbidx-1);
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBSlotMask(int slotmask)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLNBSlotMask(%d)", slotmask);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].slot_mask = slotmask;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBLOFL(int lofl)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLNBLOFL(%d)", lofl);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_lo = lofl;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBLOFH(int lofh)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLNBLOFH(%d)", lofh);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_hi = lofh;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBThreshold(int threshold)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLNBThreshold(%d)", threshold);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_threshold = threshold;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBIncreasedVoltage(bool onoff)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLNBIncreasedVoltage(%d)", onoff);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_increased_voltage = onoff;
	else
		return -ENOENT;
	return 0;
}

/* DiSEqC Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::setDiSEqCMode(int diseqcmode)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setDiSEqcMode(%d)", diseqcmode);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_diseqc_mode = (eDVBSatelliteDiseqcParameters::t_diseqc_mode)diseqcmode;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setToneburst(int toneburst)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setToneburst(%d)", toneburst);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_toneburst_param = (eDVBSatelliteDiseqcParameters::t_toneburst_param)toneburst;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setRepeats(int repeats)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setRepeats(%d)", repeats);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_repeats=repeats;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setCommittedCommand(int command)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setCommittedCommand(%d)", command);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_committed_cmd=command;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setUncommittedCommand(int command)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setUncommittedCommand(%d)", command);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_uncommitted_cmd = command;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setCommandOrder(int order)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setCommandOrder(%d)", order);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_command_order=order;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setFastDiSEqC(bool onoff)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setFastDiSEqc(%d)", onoff);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_use_fast=onoff;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setSeqRepeat(bool onoff)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setSeqRepeat(%d)", onoff);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_seq_repeat = onoff;
	else
		return -ENOENT;
	return 0;
}

/* Rotor Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::setLongitude(float longitude)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLongitude(%f)", longitude);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_longitude=longitude;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLatitude(float latitude)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLatitude(%f)", latitude);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_latitude=latitude;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLoDirection(int direction)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLoDirection(%d)", direction);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_lo_direction=direction;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLaDirection(int direction)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setLaDirection(%d)", direction);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_la_direction=direction;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setUseInputpower(bool onoff)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setUseInputpower(%d)", onoff);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_inputpower_parameters.m_use=onoff;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setInputpowerDelta(int delta)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setInputpowerDelta(%d)", delta);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_inputpower_parameters.m_delta=delta;
	else
		return -ENOENT;
	return 0;
}

/* Satellite Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::addSatellite(int orbital_position)
{
	eSecDebug("eDVBSatelliteEquipmentControl::addSatellite(%d)", orbital_position);
	if ( currentLNBValid() )
	{
		std::map<int, eDVBSatelliteSwitchParameters>::iterator it =
			m_lnbs[m_lnbidx].m_satellites.find(orbital_position);
		if ( it == m_lnbs[m_lnbidx].m_satellites.end() )
		{
			std::pair<std::map<int, eDVBSatelliteSwitchParameters>::iterator, bool > ret =
				m_lnbs[m_lnbidx].m_satellites.insert(
					std::pair<int, eDVBSatelliteSwitchParameters>(orbital_position, eDVBSatelliteSwitchParameters())
				);
			if ( ret.second )
				m_curSat = ret.first;
			else
				return -ENOMEM;
		}
		else
			return -EEXIST;
	}
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setVoltageMode(int mode)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setVoltageMode(%d)", mode);
	if ( currentLNBValid() && m_curSat != m_lnbs[m_lnbidx].m_satellites.end() )
		m_curSat->second.m_voltage_mode = (eDVBSatelliteSwitchParameters::t_voltage_mode)mode;
	else
		return -ENOENT;
	return 0;

}

RESULT eDVBSatelliteEquipmentControl::setToneMode(int mode)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setToneMode(%d)", mode);
	if ( currentLNBValid() )
	{
		if ( m_curSat != m_lnbs[m_lnbidx].m_satellites.end() )
			m_curSat->second.m_22khz_signal = (eDVBSatelliteSwitchParameters::t_22khz_signal)mode;
		else
			return -EPERM;
	}
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setRotorPosNum(int rotor_pos_num)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setRotorPosNum(%d)", rotor_pos_num);
	if ( currentLNBValid() )
	{
		if ( m_curSat != m_lnbs[m_lnbidx].m_satellites.end() )
			m_curSat->second.m_rotorPosNum=rotor_pos_num;
		else
			return -EPERM;
	}
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setRotorTurningSpeed(int speed)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setRotorTurningSpeed(%d)", speed);
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_inputpower_parameters.m_turning_speed = speed;
	else
		return -ENOENT;
	return 0;
}

struct sat_compare
{
	int orb_pos, lofl, lofh;
	sat_compare(int o, int lofl, int lofh)
		:orb_pos(o), lofl(lofl), lofh(lofh)
	{}
	sat_compare(const sat_compare &x)
		:orb_pos(x.orb_pos), lofl(x.lofl), lofh(x.lofh)
	{}
	bool operator < (const sat_compare & cmp) const
	{
		if (orb_pos == cmp.orb_pos)
		{
			if ( abs(lofl-cmp.lofl) < 200000 )
			{
				if (abs(lofh-cmp.lofh) < 200000)
					return false;
				return lofh<cmp.lofh;
			}
			return lofl<cmp.lofl;
		}
		return orb_pos < cmp.orb_pos;
	}
};

PyObject *eDVBSatelliteEquipmentControl::get_exclusive_satellites(int tu1, int tu2)
{
	ePyObject ret;

	if (tu1 != tu2)
	{
		eDVBRegisteredFrontend *p1=NULL, *p2=NULL;
		int cnt=0;
		for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it, ++cnt)
		{
			if (cnt == tu1)
				p1 = *it;
			else if (cnt == tu2)
				p2 = *it;
		}

		if (p1 && p2)
		{
			// check for linked tuners

			do 
			{
				long tmp;
				p1->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp);
				if (tmp != -1)
					p1 = (eDVBRegisteredFrontend*)tmp;
				else
					break;
			}
			while (true);

			do 
			{
				long tmp;
				p2->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp);
				if (tmp != -1)
					p2 = (eDVBRegisteredFrontend*)tmp;
				else
					break;
			}
			while (true);

			if (p1 != p2)
			{
				long tmp1=-1;
				long tmp2=-1;
				// check for rotor dependency
				p1->m_frontend->getData(eDVBFrontend::SATPOS_DEPENDS_PTR, tmp1);
				if (tmp1 != -1)
					p1 = (eDVBRegisteredFrontend*)tmp1;
				p2->m_frontend->getData(eDVBFrontend::SATPOS_DEPENDS_PTR, tmp2);
				if (tmp2 != -1)
					p2 = (eDVBRegisteredFrontend*)tmp2;
				if (p1 != p2)
				{
					int tu1_mask = 1 << p1->m_frontend->getSlotID(),
						tu2_mask = 1 << p2->m_frontend->getSlotID();
					std::set<sat_compare> tu1sats, tu2sats;
					std::list<sat_compare> tu1difference, tu2difference;
					std::insert_iterator<std::list<sat_compare> > insert1(tu1difference, tu1difference.begin()),
						insert2(tu2difference, tu2difference.begin());
					for (int idx=0; idx <= m_lnbidx; ++idx )
					{
						eDVBSatelliteLNBParameters &lnb_param = m_lnbs[idx];
						for (std::map<int, eDVBSatelliteSwitchParameters>::iterator sit(lnb_param.m_satellites.begin());
							sit != lnb_param.m_satellites.end(); ++sit)
						{
							if ( lnb_param.slot_mask & tu1_mask )
								tu1sats.insert(sat_compare(sit->first, lnb_param.m_lof_lo, lnb_param.m_lof_hi));
							if ( lnb_param.slot_mask & tu2_mask )
								tu2sats.insert(sat_compare(sit->first, lnb_param.m_lof_lo, lnb_param.m_lof_hi));
						}
					}
					std::set_difference(tu1sats.begin(), tu1sats.end(),
						tu2sats.begin(), tu2sats.end(),
						insert1);
					std::set_difference(tu2sats.begin(), tu2sats.end(),
						tu1sats.begin(), tu1sats.end(),
						insert2);
					if (!tu1sats.empty() || !tu2sats.empty())
					{
						int idx=0;
						ret = PyList_New(2+tu1difference.size()+tu2difference.size());

						PyList_SET_ITEM(ret, idx++, PyInt_FromLong(tu1difference.size()));
						for(std::list<sat_compare>::iterator it(tu1difference.begin()); it != tu1difference.end(); ++it)
							PyList_SET_ITEM(ret, idx++, PyInt_FromLong(it->orb_pos));

						PyList_SET_ITEM(ret, idx++, PyInt_FromLong(tu2difference.size()));
						for(std::list<sat_compare>::iterator it(tu2difference.begin()); it != tu2difference.end(); ++it)
							PyList_SET_ITEM(ret, idx++, PyInt_FromLong(it->orb_pos));
					}
				}
			}
		}
	}
	if (!ret)
	{
		ret = PyList_New(2);
		PyList_SET_ITEM(ret, 0, PyInt_FromLong(0));
		PyList_SET_ITEM(ret, 1, PyInt_FromLong(0));
	}
	return ret;
}

RESULT eDVBSatelliteEquipmentControl::setTunerLinked(int tu1, int tu2)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setTunerLinked(%d, %d)", tu1, tu2);
	if (tu1 != tu2)
	{
		eDVBRegisteredFrontend *p1=NULL, *p2=NULL;

		int cnt=0;
		for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it, ++cnt)
		{
			if (cnt == tu1)
				p1 = *it;
			else if (cnt == tu2)
				p2 = *it;
		}
		if (p1 && p2)
		{
			p1->m_frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)p2);
			p2->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)p1);
			if (!strcmp(p1->m_frontend->getDescription(), p2->m_frontend->getDescription()) && !strcmp(p1->m_frontend->getDescription(), "BCM4501 (internal)"))
			{
				FILE *f=fopen("/proc/stb/tsmux/lnb_b_input", "w");
				if (!f || fwrite("A", 1, 1, f) != 1)
					eDebug("set /proc/stb/tsmux/lnb_b_input to A failed!! (%m)");
				else
				{
					eDebug("set /proc/stb/tsmux/lnb_b_input to A OK");
					fclose(f);
				}
			}
			return 0;
		}
	}
	return -1;
}

RESULT eDVBSatelliteEquipmentControl::setTunerDepends(int tu1, int tu2)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setTunerDepends(%d, %d)", tu1, tu2);
	if (tu1 == tu2)
		return -1;

	eDVBRegisteredFrontend *p1=NULL, *p2=NULL;

	int cnt=0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it, ++cnt)
	{
		if (cnt == tu1)
			p1 = *it;
		else if (cnt == tu2)
			p2 = *it;
	}
	if (p1 && p2)
	{
		p1->m_frontend->setData(eDVBFrontend::SATPOS_DEPENDS_PTR, (long)p2);
		p2->m_frontend->setData(eDVBFrontend::SATPOS_DEPENDS_PTR, (long)p1);
		return 0;
	}
	return -1;
}

void eDVBSatelliteEquipmentControl::setSlotNotLinked(int slot_no)
{
	eSecDebug("eDVBSatelliteEquipmentControl::setSlotNotLinked(%d)", slot_no);
	m_not_linked_slot_mask |= (1 << slot_no);
}

bool eDVBSatelliteEquipmentControl::isRotorMoving()
{
	return m_rotorMoving;
}

void eDVBSatelliteEquipmentControl::setRotorMoving(bool b)
{
	m_rotorMoving=b;
}
