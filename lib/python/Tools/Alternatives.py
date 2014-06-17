from enigma import eServiceCenter, eServiceReference

def getAlternativeChannels(service):
	alternativeServices = eServiceCenter.getInstance().list(eServiceReference(service))
	return alternativeServices and alternativeServices.getContent("S", True)

def CompareWithAlternatives(serviceA, serviceB):
	return serviceA and serviceB and (
		serviceA == serviceB or
		serviceA.startswith('1:134:') and serviceB in getAlternativeChannels(serviceA) or
		serviceB.startswith('1:134:') and serviceA in getAlternativeChannels(serviceB))

def GetWithAlternative(service):
	if service.startswith('1:134:'):
		channels = getAlternativeChannels(service)
		if channels:
			return channels[0]
	return service