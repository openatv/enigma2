#include <config.h>
#include <lib/dvb/sec.h>
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

eDVBSatelliteEquipmentControl::eDVBSatelliteEquipmentControl()
{
	m_lnblist.push_back(eDVBSatelliteLNBParameters());
	eDVBSatelliteLNBParameters &lnb_ref = m_lnblist.front();
	eDVBSatelliteParameters &astra1 = lnb_ref.m_satellites[192];
	eDVBSatelliteDiseqcParameters &diseqc_ref = astra1.m_diseqc_parameters;
	eDVBSatelliteSwitchParameters &switch_ref = astra1.m_switch_parameters;

	lnb_ref.m_lof_hi = 10607000;
	lnb_ref.m_lof_lo = 9750000;
	lnb_ref.m_lof_threshold = 11700000;

	diseqc_ref.m_diseqc_mode = eDVBSatelliteDiseqcParameters::V1_0;
	diseqc_ref.m_committed_cmd = eDVBSatelliteDiseqcParameters::AA;
	diseqc_ref.m_repeats = 0;
	diseqc_ref.m_seq_repeat = false;
	diseqc_ref.m_swap_cmds = false;
	diseqc_ref.m_toneburst_param = eDVBSatelliteDiseqcParameters::NO;
	diseqc_ref.m_uncommitted_cmd = 0;
	diseqc_ref.m_use_fast = 1;

	switch_ref.m_22khz_signal = eDVBSatelliteSwitchParameters::HILO;
	switch_ref.m_voltage_mode = eDVBSatelliteSwitchParameters::HV;
}

RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat)
{
	std::list<eDVBSatelliteLNBParameters>::iterator it = m_lnblist.begin();
	for (;it != m_lnblist.end(); ++it )
	{
		eDVBSatelliteLNBParameters &lnb_param = *it;
		std::map<int, eDVBSatelliteParameters>::iterator sit =
			lnb_param.m_satellites.find(sat.orbital_position);
		if ( sit != lnb_param.m_satellites.end())
		{
			eDVBSatelliteDiseqcParameters &di_param = sit->second.m_diseqc_parameters;
			eDVBSatelliteSwitchParameters &sw_param = sit->second.m_switch_parameters;
			int hi=0,
				voltage = iDVBFrontend::voltageOff,
				tone = iDVBFrontend::toneOff,
				csw = di_param.m_committed_cmd,
				ucsw = di_param.m_uncommitted_cmd,
				toneburst = di_param.m_toneburst_param,
				lastcsw = -1,
				lastucsw = -1,
				lastToneburst = -1,
				curRotorPos = -1;

			frontend.getData(0, lastcsw);
			frontend.getData(1, lastucsw);
			frontend.getData(2, lastToneburst);
			frontend.getData(3, curRotorPos);

			if ( sat.frequency > lnb_param.m_lof_threshold )
				hi = 1;

			if (hi)
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_hi;
			else
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_lo;

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
				|| ( sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::HILO && hi ) )
				tone = iDVBFrontend::toneOn;
			else if ( (sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::OFF)
				|| ( sw_param.m_22khz_signal == eDVBSatelliteSwitchParameters::HILO && !hi ) )
				tone = iDVBFrontend::toneOff;

			eSecCommandList sec_sequence;

			if (di_param.m_diseqc_mode >= eDVBSatelliteDiseqcParameters::V1_0)
			{
				if ( di_param.m_committed_cmd < eDVBSatelliteDiseqcParameters::SENDNO )
				{
					csw = 0xF0 | (csw << 2);
					if (hi)
						csw |= 1;
					if (sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal)
						csw |= 2;
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
						send_diseqc = false;
				}

				if ( send_diseqc || changed_burst )
				{
					sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );
					sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );
					sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 30) );  // standard says 15 msek here
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

						if ( !send_csw || (di_param.m_swap_cmds && send_ucsw) )
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
									sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 30) );
							}
							else  // delay 120msek when no command is in repeat gap
								sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 120) );
						}
						else
							sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 30) );
					}
				}
				if ( di_param.m_diseqc_mode == eDVBSatelliteDiseqcParameters::V1_2 && curRotorPos != sat.orbital_position )
				{
				}
				if ( (changed_burst || send_diseqc) && di_param.m_toneburst_param != eDVBSatelliteDiseqcParameters::NO )
				{
					sec_sequence.push_back( eSecCommand(eSecCommand::SEND_TONEBURST, di_param.m_toneburst_param) );
					sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 30) );
				}
			}
			else
			{
				sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, voltage) );
				sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 10) );
			}

			sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, tone) );
			sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 15) );

			frontend.setSecSequence(sec_sequence);

			return 0;
		}
	}

	eDebug("not found satellite configuration for orbital position (%d)", sat.orbital_position );

	return -1;
}

