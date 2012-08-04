from enigma import eServiceCenter, eServiceReference 

def getAlternativeChannels(service):
	alternativeServices = eServiceCenter.getInstance().list(eServiceReference(service))
	return alternativeServices and alternativeServices.getContent("S", True)

def CompareWithAlternatives(service,serviceToCompare):
	if service == serviceToCompare:
		return True
	if service.startswith('1:134:'):
		for channel in getAlternativeChannels(service):
			if channel == serviceToCompare:
				return True
	return False

def GetWithAlternative(service):
	if service.startswith('1:134:'):
		channels = getAlternativeChannels(service)
		if channels:
			return channels[0]
	return service