#ifndef __dvb_sec_h
#define __dvb_sec_h

#include <lib/dvb/idvb.h>

class eDVBSatelliteEquipmentControl: public iDVBSatelliteEquipmentControl
{
public:
	DECLARE_REF;
	RESULT prepare(iDVBFrontend &frontend, struct dvb_frontend_parameters &parm, eDVBFrontendParametersSatellite &sat);
};

#endif
