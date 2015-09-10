from enigma import eServiceReference, eServiceID

# type 1 = digital television service
# type 4 = nvod reference service (NYI)
# type 17 = MPEG-2 HD digital television service
# type 22 = advanced codec SD digital television
# type 24 = advanced codec SD NVOD reference service (NYI)
# type 25 = advanced codec HD digital television
# type 27 = advanced codec HD NVOD reference service (NYI)
# type 2 = digital radio sound service
# type 10 = advanced codec digital radio sound service

# Generate an eServiceRef query path containing
# '(type == serviceTypes[0]) || (type == serviceTypes[1]) || ...'

def makeServiceQueryStr(serviceTypes):
	return ' || '.join(map(lambda x: '(type == %d)' % x, serviceTypes))

def serviceRefAppendPath(sref, path):
	nsref = eServiceReference(sref)
	nsref.setPath(nsref.getPath() + path)
	return nsref

service_types_tv_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceID.dTv)

service_types_tv_ref.setPath(makeServiceQueryStr((
	eServiceID.dTv,
	eServiceID.mpeg2HdTv,
	eServiceID.avcSdTv,
	eServiceID.avcHdTv,
	eServiceID.user134,
	eServiceID.user195,
)))

service_types_radio_ref = eServiceReference(eServiceReference.idDVB, eServiceReference.flagDirectory, eServiceID.dRadio)
service_types_radio_ref.setPath(makeServiceQueryStr((
	eServiceID.dRadio,
	eServiceID.dRadioAvc,
)))

def hdmiInServiceRef():
	return eServiceReference(eServiceReference.idServiceHDMIIn, eServiceReference.noFlags, eServiceID.dTv)

