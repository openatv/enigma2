#ifndef __dvb_sec_h
#define __dvb_sec_h

#include <config.h>
#include <lib/dvb/idvb.h>

class eDVBSatelliteEquipmentControl: public iDVBSatelliteEquipmentControl
{
public:
	DECLARE_REF;
	eDVBSatelliteEquipmentControl();
#if HAVE_DVB_API_VERSION < 3
	RESULT prepare(iDVBFrontend &frontend, FrontendParameters &parm, eDVBFrontendParametersSatellite &sat);
#else
	RESULT prepare(iDVBFrontend &frontend, struct dvb_frontend_parameters &parm, eDVBFrontendParametersSatellite &sat);
#endif
};

#endif
