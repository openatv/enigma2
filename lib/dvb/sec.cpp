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
}

RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat)
{
	int hi;
	eDebug("(very) ugly and hardcoded eDVBSatelliteEquipmentControl");

	if (sat.frequency > 11700000)
		hi = 1;
	else
		hi = 0;
	
	if (hi)
		parm.FREQUENCY = sat.frequency - 10600000;
	else
		parm.FREQUENCY = sat.frequency -  9750000;
	
//	frontend.sentDiseqc(...);

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

	eDVBDiseqcCommand diseqc;

#if HAVE_DVB_API_VERSION < 3
	diseqc.voltage = sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Vertical ? iDVBFrontend::voltage13 : iDVBFrontend::voltage18;
	diseqc.tone = hi ? iDVBFrontend::toneOn : iDVBFrontend::toneOff;
#else
	frontend.setVoltage(sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Vertical ? iDVBFrontend::voltage13 : iDVBFrontend::voltage18);
#endif

	diseqc.len = 4;
	diseqc.data[0] = 0xe0;
	diseqc.data[1] = 0x10;
	diseqc.data[2] = 0x38;
	diseqc.data[3] = 0xF0;

	if (hi)
		diseqc.data[3] |= 1;

	if (sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Horizontal)
		diseqc.data[3] |= 2;

	frontend.sendDiseqc(diseqc);

#if HAVE_DVB_API_VERSION > 2
	frontend.setTone(hi ? iDVBFrontend::toneOn : iDVBFrontend::toneOff);
#endif

	return 0;
}

