#include <lib/dvb/sec.h>
#include <linux/dvb/frontend.h>
#include <lib/base/eerror.h>

DEFINE_REF(eDVBSatelliteEquipmentControl);

eDVBSatelliteEquipmentControl::eDVBSatelliteEquipmentControl(): ref(0)
{
}

RESULT eDVBSatelliteEquipmentControl::prepare(iDVBFrontend &frontend, struct dvb_frontend_parameters &parm, eDVBFrontendParametersSatellite &sat)
{
	int hi;
	eDebug("(very) ugly and hardcoded eDVBSatelliteEquipmentControl");
	
	if (sat.frequency > 11700000)
		hi = 1;
	else
		hi = 0;
	
	if (hi)
		parm.frequency = sat.frequency - 10600000;
	else
		parm.frequency = sat.frequency -  9750000;
	
//	frontend.sentDiseqc(...);

	parm.inversion = sat.inversion ? INVERSION_ON : INVERSION_OFF;

	switch (sat.fec)
	{
//		case 1:
//		case ...:
	default:
		parm.u.qpsk.fec_inner = FEC_AUTO;
		break;
	}
	parm.u.qpsk.symbol_rate = sat.symbol_rate;
	

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

