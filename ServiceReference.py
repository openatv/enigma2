
from enigma import *

import NavigationInstance

class ServiceReference(eServiceReference):
	def __init__(self, ref):
		if isinstance(ref, str):
			ref = eServiceReference(ref)
		self.ref = ref

	def getStaticServiceInformation(self):
		info = iStaticServiceInformationPtr()
		if NavigationInstance.instance.ServiceHandler.info(self.ref, info):
			info = None
		return info
	
	def __str__(self):
		return self.ref.toString()
	
	def getServiceName(self):
		info = self.getStaticServiceInformation()
		if not info:
			return None
		
		return info.getName(self.ref)
