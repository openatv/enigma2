#ifndef __dvb_sec_h
#define __dvb_sec_h

#include <config.h>
#include <lib/dvb/idvb.h>

class eDVBSatelliteEquipmentControl: public iDVBSatelliteEquipmentControl
{
public:
	DECLARE_REF;
	eDVBSatelliteEquipmentControl();
	RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat);
};

#endif
