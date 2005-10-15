
from enigma import *

import NavigationInstance

class ServiceReference(eServiceReference):
	def __init__(self, ref):
		if isinstance(ref, str):
			ref = eServiceReference(ref)
		self.ref = ref

	def getStaticServiceInformation(self):
		return NavigationInstance.instance.ServiceHandler.info(self.ref)
	
	def __str__(self):
		return self.ref.toString()
	
	def getServiceName(self):
		info = self.getStaticServiceInformation()
		if info is None:
			return None
		
		return info.getName(self.ref)
