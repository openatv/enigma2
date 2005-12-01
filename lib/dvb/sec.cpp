#include <config.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/dvb/rotor_calc.h>

#if HAVE_DVB_API_VERSION < 3
#define INVERSION Inversion
#define FREQUENCY Frequency
#define FEC_INNER FEC_inner
#define SYMBOLRATE SymbolRate
#else
#define INVERSION inversion
#define FREQUENCY frequency
#define FEC_INNER fec_inner
#define SYMBOLRATE symbol_rate
#endif
#include <lib/base/eerror.h>

DEFINE_REF(eDVBSatelliteEquipmentControl);

eDVBSatelliteEquipmentControl *eDVBSatelliteEquipmentControl::instance;

eDVBSatelliteEquipmentControl::eDVBSatelliteEquipmentControl(eSmartPtrList<eDVBRegisteredFrontend> &avail_frontends)
	:m_lnbidx(-1), m_curSat(m_lnbs[0].m_satellites.end()), m_avail_frontends(avail_frontends)
{
	if (!instance)
		instance = this;

	clear();

#if 0
// ASTRA
	addLNB();
	setLNBTunerMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11750000);
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
	setLNBTunerMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11750000);
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
#endif

// Rotor
	addLNB();
	setLNBTunerMask(3);
	setLNBLOFL(9750000);
	setLNBThreshold(11750000);
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

	addSatellite(130);
	setVoltageMode(eDVBSatelliteSwitchParameters::HV);
	setToneMode(eDVBSatelliteSwitchParameters::HILO);
	setRotorPosNum(0);

	addSatellite(192);
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

int eDVBSatelliteEquipmentControl::canTune(const eDVBFrontendParametersSatellite &sat, iDVBFrontend *fe, int frontend_id )
{
	int ret=0;

	for (int idx=0; idx <= m_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = m_lnbs[idx];
		if ( lnb_param.tuner_mask & frontend_id ) // lnb for correct tuner?
		{
			eDVBSatelliteDiseqcParameters &di_param = lnb_param.m_diseqc_parameters;

			std::map<int, eDVBSatelliteSwitchParameters>::iterator sit =
				lnb_param.m_satellites.find(sat.orbital_position);
			if ( sit != lnb_param.m_satellites.end())
			{
				int band=0,
					linked_to=0, // linked tuner
					csw = di_param.m_committed_cmd,
					ucsw = di_param.m_uncommitted_cmd,
					toneburst = di_param.m_toneburst_param,
					curRotorPos;

				fe->getData(6, curRotorPos);
				fe->getData(7, linked_to);

				if ( sat.frequency > lnb_param.m_lof_threshold )
					band |= 1;
				if (sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal)
					band |= 2;

				bool rotor=false;
				bool diseqc=false;

				if (di_param.m_diseqc_mode >= eDVBSatelliteDiseqcParameters::V1_0)
				{
					diseqc=true;
					if ( di_param.m_committed_cmd < eDVBSatelliteDiseqcParameters::SENDNO )
					{
						csw = 0xF0 | (csw << 2);
						csw |= band;
					}

					if ( di_param.m_diseqc_mode == eDVBSatelliteDiseqcParameters::V1_2 )  // ROTOR
					{
						rotor=true;
						if ( curRotorPos == sat.orbital_position )
							ret=20;
						else
							ret=10;
					}
				}
				
				if (!ret)
					ret=40;

				if (linked_to != -1)  // check for linked tuners..
				{
					bool found=false;
					eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin());
					for (; it != m_avail_frontends.end(); ++it)
						if ( !linked_to )
						{
							found=true;
							break;
						}
						else
							--linked_to;

					if (found && it->m_inuse)
					{
						int ocsw = -1,
							oucsw = -1,
							oToneburst = -1,
							oRotorPos = -1;
						it->m_frontend->getData(0, ocsw);
						it->m_frontend->getData(1, oucsw);
						it->m_frontend->getData(2, oToneburst);
						it->m_frontend->getData(6, oRotorPos);

						eDebug("compare csw %02x == lcsw %02x",
							csw, ocsw);
						if ( diseqc )
							eDebug("compare ucsw %02x == lucsw %02x\ncompare toneburst %02x == oToneburst %02x",
								ucsw, oucsw, toneburst, oToneburst);
						if ( rotor )
							eDebug("compare pos %d == current pos %d",
								sat.orbital_position, oRotorPos);

						if ( (csw != ocsw) ||
							( diseqc && (ucsw != oucsw || toneburst != oToneburst) ) ||
							( rotor && oRotorPos != sat.orbital_position ) )
						{
							eDebug("can not tune this transponder with linked tuner in use!!");
							ret=0;
						}
						else
							eDebug("OK .. can tune this transponder with linked tuner in use :)");
					}
				}
			}
		}
	}
	return ret;
}

RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat, int frontend_id)
{
	bool linked=false;

	for (int idx=0; idx <= m_lnbidx; ++idx )
	{
		eDVBSatelliteLNBParameters &lnb_param = m_lnbs[idx];
		if (!(lnb_param.tuner_mask & frontend_id)) // lnb for correct tuner?
			continue;
		eDVBSatelliteDiseqcParameters &di_param = lnb_param.m_diseqc_parameters;
		eDVBSatelliteRotorParameters &rotor_param = lnb_param.m_rotor_parameters;

		std::map<int, eDVBSatelliteSwitchParameters>::iterator sit =
			lnb_param.m_satellites.find(sat.orbital_position);
		if ( sit != lnb_param.m_satellites.end())
		{
			eDVBSatelliteSwitchParameters &sw_param = sit->second;

			int band=0,
				linked_to=-1, // linked tuner
				voltage = iDVBFrontend::voltageOff,
				tone = iDVBFrontend::toneOff,
				csw = di_param.m_committed_cmd,
				ucsw = di_param.m_uncommitted_cmd,
				toneburst = di_param.m_toneburst_param,
				lastcsw = -1,
				lastucsw = -1,
				lastToneburst = -1,
				lastRotorCmd = -1,
				curRotorPos = -1;

			frontend.getData(0, lastcsw);
			frontend.getData(1, lastucsw);
			frontend.getData(2, lastToneburst);
			frontend.getData(5, lastRotorCmd);
			frontend.getData(6, curRotorPos);
			frontend.getData(7, linked_to);

			if (linked_to != -1)
			{
				bool found=false;
				eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin());
				for (; it != m_avail_frontends.end(); ++it)
					if ( !linked_to )
					{
						found=true;
						break;
					}
					else
						--linked_to;
				if (found && it->m_inuse)
				{
					eDebug("[SEC] frontend is linked with another one and the other is in use.. so we dont do SEC!!");
					linked=true;
				}
			}

			if ( sat.frequency > lnb_param.m_lof_threshold )
				band |= 1;

			if (band&1)
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_hi;
			else
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_lo;

			if (sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal)
				band |= 2;

			parm.INVERSION = (!sat.inversion) ? INVERSION_ON : INVERSION_OFF;

			switch (sat.fec)
			{
				default:
				case eDVBFrontendParametersSatellite::FEC::fNone:
					eDebug("no fec set.. assume auto");
				case eDVBFrontendParametersSatellite::FEC::fAuto:
					parm.u.qpsk.FEC_INNER = FEC_AUTO;
					break;
				case eDVBFrontendParametersSatellite::FEC::f1_2:
					parm.u.qpsk.FEC_INNER = FEC_1_2;
					break;
				case eDVBFrontendParametersSatellite::FEC::f2_3:
					parm.u.qpsk.FEC_INNER = FEC_2_3;
					break;
				case eDVBFrontendParametersSatellite::FEC::f3_4:
					parm.u.qpsk.FEC_INNER = FEC_3_4;
					break;
				case eDVBFrontendParametersSatellite::FEC::f5_6:
					parm.u.qpsk.FEC_INNER = FEC_5_6;
					break;
				case eDVBFrontendParametersSatellite::FEC::f7_8: 
					parm.u.qpsk.FEC_INNER = FEC_7_8;
					break;
			}

			parm.u.qpsk.SYMBOLRATE = sat.symbol_rate;

			if ( sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::_14V
				|| ( sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Vertical
					&& sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::HV )  )
				voltage = iDVBFrontend::voltage13;
			else if ( sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::_18V
				|| ( sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal
					&& sw_param.m_voltage_mode == eDVBSatelliteSwitchParameters::HV )  )
				voltage = iDVBFrontend::voltage18;

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
				{
					csw = 0xF0 | (csw << 2);
					csw |= band;
				}

				bool send_csw =
					(di_param.m_committed_cmd != eDVBSatelliteDiseqcParameters::SENDNO);
				bool changed_csw = send_csw && csw != lastcsw;

				bool send_ucsw =
					(di_param.m_uncommitted_cmd && di_param.m_diseqc_mode > eDVBSatelliteDiseqcParameters::V1_0);
				bool changed_ucsw = send_ucsw && ucsw != lastucsw;

				bool send_burst =
					(di_param.m_toneburst_param != eDVBSatelliteDiseqcParameters::NO);
				bool changed_burst = send_burst && toneburst != lastToneburst;

				bool send_diseqc = changed_ucsw;
				if (!send_diseqc)
					send_diseqc = changed_burst && (send_ucsw || send_csw);
				if (!send_diseqc)
				{
					send_diseqc = changed_csw;
					if ( send_diseqc && di_param.m_use_fast && (csw & 0xF0) && (lastcsw & 0xF0) && ((csw / 4) == (lastcsw / 4)) )
					{
						frontend.setData(0, csw);  // needed for linked tuner handling
						send_diseqc = false;
					}
				}

				if ( send_diseqc || changed_burst )
				{
					sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );
					eSecCommand::pair compare;
					compare.voltage = voltage;
					compare.steps = +3;
					sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) ); // voltage already correct ?
					sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );
					sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );
				}

				for (int seq_repeat = 0; seq_repeat < (di_param.m_seq_repeat?2:1); ++seq_repeat)
				{
					if ( di_param.m_command_order & 1 && // toneburst at begin of sequence
						changed_burst && di_param.m_toneburst_param != eDVBSatelliteDiseqcParameters::NO )
					{
						sec_sequence.push_back( eSecCommand(eSecCommand::SEND_TONEBURST, di_param.m_toneburst_param) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );
					}

					if ( send_diseqc )
					{
						int loops=0;

						if ( send_csw )
							++loops;
						if ( send_ucsw )
							++loops;

						for ( int i=0; i < di_param.m_repeats; ++i )
							loops *= 2;

						for ( int i = 0; i < loops;)  // fill commands...
						{
							eDVBDiseqcCommand diseqc;
							diseqc.len = 4;
							diseqc.data[0] = i ? 0xE1 : 0xE0;
							diseqc.data[1] = 0x10;

							if ( !send_csw || (send_ucsw && (di_param.m_command_order & 4) ) )
							{
								diseqc.data[2] = 0x39;
								diseqc.data[3] = ucsw;
							}
							else
							{
								diseqc.data[2] = 0x38;
								diseqc.data[3] = csw;
							}
							sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );

							i++;
							if ( i < loops )
							{
								int cmd=0;
								if (diseqc.data[2] == 0x38 && send_ucsw)
									cmd=0x39;
								else if (diseqc.data[2] == 0x39 && send_csw)
									cmd=0x38;
								if (cmd)
								{
									static int delay = (120 - 54) / 2;  // standard says 100msek between two repeated commands
									sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, delay) );
									diseqc.data[2]=cmd;
									diseqc.data[3]=(cmd==0x38) ? csw : ucsw;
									sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
									++i;
									if ( i < loops )
										sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, delay ) );
									else
										sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );
								}
								else  // delay 120msek when no command is in repeat gap
									sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 120) );
							}
							else
								sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );

							frontend.setData(0, csw);
							frontend.setData(1, ucsw);
							frontend.setData(2, di_param.m_toneburst_param);
						}
					}

					if ( !(di_param.m_command_order & 1) && // toneburst at end of sequence
						(changed_burst || send_diseqc) && di_param.m_toneburst_param != eDVBSatelliteDiseqcParameters::NO )
					{
						sec_sequence.push_back( eSecCommand(eSecCommand::SEND_TONEBURST, di_param.m_toneburst_param) );
						sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );
						frontend.setData(2, di_param.m_toneburst_param);
					}
				}

				if ( di_param.m_diseqc_mode == eDVBSatelliteDiseqcParameters::V1_2 )
				{
					int RotorCmd=0;
					bool useGotoXX = false;

					if (sw_param.m_rotorPosNum) // we have stored rotor pos?
						RotorCmd=sw_param.m_rotorPosNum;
					else  // we must calc gotoxx cmd
					{
						eDebug("Entry for %d,%d? not in Rotor Table found... i try gotoXX?", sat.orbital_position / 10, sat.orbital_position % 10 );
						useGotoXX = true;

						int satDir = sat.orbital_position < 0 ?
							eDVBSatelliteRotorParameters::WEST :
							eDVBSatelliteRotorParameters::EAST;

						double	SatLon = abs(sat.orbital_position)/10.00,
								SiteLat = rotor_param.m_gotoxx_parameters.m_latitude,
								SiteLon = rotor_param.m_gotoxx_parameters.m_longitude;

						if ( rotor_param.m_gotoxx_parameters.m_la_direction == eDVBSatelliteRotorParameters::SOUTH )
							SiteLat = -SiteLat;

						if ( rotor_param.m_gotoxx_parameters.m_lo_direction == eDVBSatelliteRotorParameters::WEST )
							SiteLon = 360 - SiteLon;

						if (satDir == eDVBSatelliteRotorParameters::WEST )
							SatLon = 360 - SatLon;

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
							else					// west
							{          
								int tmp=(int)round( fabs( 360 - satHourAngle ) * 10.0 );
								RotorCmd = (tmp/10)*0x10 + gotoXTable[ tmp % 10 ];
								RotorCmd |= 0xE000;
							}
						}
						eDebug("RotorCmd = %04x", RotorCmd);
					}
					if ( RotorCmd != lastRotorCmd )
					{
						if ( changed_burst || send_diseqc )
						{
							// override first voltage change
							*(++(++sec_sequence.begin()))=eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13);
							// wait 1 second after first switch diseqc command
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 1000) );
						}
						else  // no other diseqc commands before
						{
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 15) );  // wait 15msec after tone change
							eSecCommand::pair compare;
							compare.voltage = voltage;
							compare.steps = +3;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) ); // voltage already correct ?
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec after voltage change
						}

						eDVBDiseqcCommand diseqc;
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
						}

						if ( rotor_param.m_inputpower_parameters.m_use )
						{ // use measure rotor input power to detect rotor state
							eSecCommand::rotor cmd;
// measure idle power values
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_IDLE_INPUTPOWER_AVAIL_GOTO, +8) ); // already measured?
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec after voltage change
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_IDLE_INPUTPOWER, 0) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage18) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 100) );  // wait 100msec before measure
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_IDLE_INPUTPOWER, 1) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13) ); // back to lower voltage
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec
////////////////////////////
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeStatic) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec after voltage change
							sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TIMEOUT, 40) );  // 2 seconds rotor start timout
// rotor start loop
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // 50msec delay
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_RUNNING_INPUTPOWER) );
							cmd.direction=1;  // check for running rotor
							cmd.deltaA=rotor_param.m_inputpower_parameters.m_delta;
							cmd.steps=+3;
							cmd.okcount=0;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_INPUTPOWER_DELTA_GOTO, cmd ) );  // check if rotor has started
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TIMEOUT_GOTO, +10 ) );  // timeout .. we assume now the rotor is already at the correct position
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -4) );  // goto loop start
////////////////////
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_TIMEOUT, 2400) );  // 2 minutes running timeout
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage18) );
							sec_sequence.push_back( eSecCommand(eSecCommand::SET_POWER_LIMITING_MODE, eSecCommand::modeDynamic) );
// rotor running loop
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 50) );  // wait 50msec
							sec_sequence.push_back( eSecCommand(eSecCommand::MEASURE_RUNNING_INPUTPOWER) );
							cmd.direction=0;  // check for stopped rotor
							cmd.steps=+3;
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_INPUTPOWER_DELTA_GOTO, cmd ) );
							sec_sequence.push_back( eSecCommand(eSecCommand::IF_TIMEOUT_GOTO, +3 ) );  // timeout ? this should never happen
							sec_sequence.push_back( eSecCommand(eSecCommand::GOTO, -4) );  // running loop start
/////////////////////
							sec_sequence.push_back( eSecCommand(eSecCommand::UPDATE_CURRENT_ROTORPARAMS) );
							if ( linked )
							{
								frontend.setData(5, RotorCmd);
								frontend.setData(6, sat.orbital_position);
							}
							else
							{
								frontend.setData(3, RotorCmd);
								frontend.setData(4, sat.orbital_position);
							}
						}
						else
							eFatal("rotor turning without inputpowermeasure not implemented yet");
					}
				}
			}
			else
				frontend.setData(0, band); // store band as csw .. needed for linked tuner handling

			if ( linked )
				return 0;

			eSecCommand::pair compare;
			compare.voltage = voltage;
			compare.steps = +3;
			sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) ); // voltage already correct ?
			sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );
			sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 10) );

			sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, tone) );
			sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 15) );

			frontend.setSecSequence(sec_sequence);

			return 0;
		}
	}

	if (linked)
		return 0;

	eDebug("found no satellite configuration for orbital position (%d)", sat.orbital_position );
	return -1;
}

RESULT eDVBSatelliteEquipmentControl::clear()
{
	for (int i=0; i < m_lnbidx; ++i)
	{
		m_lnbs[i].m_satellites.clear();
		m_lnbs[i].tuner_mask = 0;
	}
	m_lnbidx=-1;

// clear linked tuner configuration
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it)
		it->m_frontend->setData(7, -1);

	return 0;
}

/* LNB Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::addLNB()
{
	if ( m_lnbidx < (int)(sizeof(m_lnbs) / sizeof(eDVBSatelliteLNBParameters)))
		m_curSat=m_lnbs[++m_lnbidx].m_satellites.end();
	else
	{
		eDebug("no more LNB free... cnt is %d", m_lnbidx);
		return -ENOSPC;
	}
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBTunerMask(int tunermask)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].tuner_mask = tunermask;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBLOFL(int lofl)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_lo = lofl;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBLOFH(int lofh)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_hi = lofh;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBThreshold(int threshold)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_lof_threshold = threshold;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLNBIncreasedVoltage(bool onoff)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_increased_voltage = onoff;
	else
		return -ENOENT;
	return 0;
}

/* DiSEqC Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::setDiSEqCMode(int diseqcmode)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_diseqc_mode = (eDVBSatelliteDiseqcParameters::t_diseqc_mode)diseqcmode;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setToneburst(int toneburst)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_toneburst_param = (eDVBSatelliteDiseqcParameters::t_toneburst_param)toneburst;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setRepeats(int repeats)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_repeats=repeats;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setCommittedCommand(int command)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_committed_cmd=command;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setUncommittedCommand(int command)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_uncommitted_cmd = command;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setCommandOrder(int order)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_command_order=order;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setFastDiSEqC(bool onoff)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_use_fast=onoff;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setSeqRepeat(bool onoff)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_diseqc_parameters.m_seq_repeat = onoff;
	else
		return -ENOENT;
	return 0;
}

/* Rotor Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::setLongitude(float longitude)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_longitude=longitude;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLatitude(float latitude)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_latitude=latitude;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLoDirection(int direction)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_lo_direction=direction;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setLaDirection(int direction)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_gotoxx_parameters.m_la_direction=direction;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setUseInputpower(bool onoff)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_inputpower_parameters.m_use=onoff;
	else
		return -ENOENT;
	return 0;
}

RESULT eDVBSatelliteEquipmentControl::setInputpowerDelta(int delta)
{
	if ( currentLNBValid() )
		m_lnbs[m_lnbidx].m_rotor_parameters.m_inputpower_parameters.m_delta=delta;
	else
		return -ENOENT;
	return 0;
}

/* Satellite Specific Parameters */
RESULT eDVBSatelliteEquipmentControl::addSatellite(int orbital_position)
{
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
	if ( currentLNBValid() && m_curSat != m_lnbs[m_lnbidx].m_satellites.end() )
		m_curSat->second.m_voltage_mode = (eDVBSatelliteSwitchParameters::t_voltage_mode)mode;
	else
		return -ENOENT;
	return 0;

}

RESULT eDVBSatelliteEquipmentControl::setToneMode(int mode)
{
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

RESULT eDVBSatelliteEquipmentControl::setTunerLinked(int tu1, int tu2)
{
	if (tu1 == tu2)
		return -1;

	eDVBFrontend *p1=NULL, *p2=NULL;
	int tmp1=tu1, tmp2=tu2;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_avail_frontends.begin()); it != m_avail_frontends.end(); ++it)
	{
		if ( !tmp1 )
			p1 = it->m_frontend;
		else
			--tmp1;
		if (!tmp2)
			p2 = it->m_frontend;
		else
			--tmp2;
	}
	if (p1 && p2)
	{
		p1->setData(7, tu2);
		p1->setTone(iDVBFrontend::toneOff);
		p1->setVoltage(iDVBFrontend::voltageOff);

		p2->setData(7, tu1);
		return 0;
	}
	return -1;
}

bool eDVBSatelliteEquipmentControl::isRotorMoving()
{
	return false;
}
