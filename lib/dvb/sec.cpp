#include <config.h>
#include <lib/dvb/sec.h>
#if HAVE_DVB_API_VERSION < 3
#include <ost/frontend.h>
#define INVERSION Inversion
#define FREQUENCY Frequency
#define FEC_INNER FEC_inner
#define SYMBOLRATE SymbolRate
#else
#include <linux/dvb/frontend.h>
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

	lnb_ref.m_lof_hi = 10600000;
	lnb_ref.m_lof_lo = 9750000;
	lnb_ref.m_lof_threshold = 11700000;

	diseqc_ref.m_diseqc_mode = eDVBSatelliteDiseqcParameters::V1_0;
	diseqc_ref.m_commited_cmd = eDVBSatelliteDiseqcParameters::BB;
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
			int hi=0;
			int voltage = iDVBFrontend::voltageOff;
			int tone = iDVBFrontend::toneOff;

			eDVBSatelliteDiseqcParameters &di_param = sit->second.m_diseqc_parameters;
			eDVBSatelliteSwitchParameters &sw_param = sit->second.m_switch_parameters;

			if ( sat.frequency > lnb_param.m_lof_threshold )
				hi = 1;

			if (hi)
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_hi;
			else
				parm.FREQUENCY = sat.frequency - lnb_param.m_lof_lo;

			parm.INVERSION = (!sat.inversion) ? INVERSION_ON : INVERSION_OFF;

			switch (sat.fec)
			{
		//		case 1:
		//		case ...:
			default:
				parm.u.qpsk.FEC_INNER = FEC_AUTO;
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

			eDVBDiseqcCommand diseqc;

#if HAVE_DVB_API_VERSION < 3
			diseqc.voltage = voltage;
			diseqc.tone = tone;
#else
			frontend.setVoltage(voltage);
#endif

			if ( di_param.m_commited_cmd < eDVBSatelliteDiseqcParameters::NO )
			{
				diseqc.len = 4;
				diseqc.data[0] = 0xe0;
				diseqc.data[1] = 0x10;
				diseqc.data[2] = 0x38;
				diseqc.data[3] = di_param.m_commited_cmd;

				if (hi)
					diseqc.data[3] |= 1;

				if (sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal)
					diseqc.data[3] |= 2;
			}
			else
				diseqc.len = 0;

			frontend.sendDiseqc(diseqc);

#if HAVE_DVB_API_VERSION > 2
			frontend.setTone(tone);
#endif
			return 0;
		}
	}

	eDebug("not found satellite configuration for orbital position (%d)", sat.orbital_position );

	return -1;
}

