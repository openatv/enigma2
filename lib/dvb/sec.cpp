#include <config.h>
#include <lib/dvb/sec.h>
#if HAVE_DVB_API_VERSION < 3
#include <ost/frontend.h>
#else
#include <linux/dvb/frontend.h>
#endif
#include <lib/base/eerror.h>

DEFINE_REF(eDVBSatelliteEquipmentControl);

eDVBSatelliteEquipmentControl::eDVBSatelliteEquipmentControl()
{
}

#if HAVE_DVB_API_VERSION < 3
RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, FrontendParameters &parm, eDVBFrontendParametersSatellite &sat)
#else
RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, struct dvb_frontend_parameters &parm, eDVBFrontendParametersSatellite &sat)
#endif
{
	int hi;
	eDebug("(very) ugly and hardcoded eDVBSatelliteEquipmentControl");
	
	if (sat.frequency > 11700000)
		hi = 1;
	else
		hi = 0;
	
	if (hi)
#if HAVE_DVB_API_VERSION < 3
		parm.Frequency = sat.frequency - 10600000;
#else
		parm.frequency = sat.frequency - 10600000;
#endif
	else
#if HAVE_DVB_API_VERSION < 3
		parm.Frequency = sat.frequency -  9750000;
#else
		parm.frequency = sat.frequency -  9750000;
#endif
	
//	frontend.sentDiseqc(...);

#if HAVE_DVB_API_VERSION < 3
	parm.Inversion = (!sat.inversion) ? INVERSION_ON : INVERSION_OFF;
#else
	parm.inversion = (!sat.inversion) ? INVERSION_ON : INVERSION_OFF;
#endif

	switch (sat.fec)
	{
//		case 1:
//		case ...:
	default:
#if HAVE_DVB_API_VERSION < 3
		parm.u.qpsk.FEC_inner = FEC_AUTO;
#else
		parm.u.qpsk.fec_inner = FEC_AUTO;
#endif
		break;
	}
#if HAVE_DVB_API_VERSION < 3
	parm.u.qpsk.SymbolRate = sat.symbol_rate;
#else
	parm.u.qpsk.symbol_rate = sat.symbol_rate;
#endif

	frontend.setVoltage((sat.polarisation == eDVBFrontendParametersSatellite::Polarisation::Vertical) ? iDVBFrontend::voltage13 : iDVBFrontend::voltage18);

	eDVBDiseqcCommand diseqc;
	
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
	frontend.setTone(hi ? iDVBFrontend::toneOn : iDVBFrontend::toneOff);

	return 0;
}

