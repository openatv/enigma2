
from enigma import *

import NavigationInstance

class ServiceReference(eServiceReference):
	def __init__(self, ref):
		if isinstance(ref, str):
			ref = eServiceReference(ref)
		self.ref = ref
		self.serviceHandler = eServiceCenter.getInstance()

	def __str__(self):
		return self.ref.toString()
	
	def getServiceName(self):
		info = self.info()
		if info is None:
			return None
		
		return info.getName(self.ref)

	def play(self):
		return self.serviceHandler.info(self.ref)
	
	def record(self):
		return self.serviceHandler.record(self.ref)
	
	def list(self):
		return self.serviceHandler.list(self)
	
	def info(self):
		return self.serviceHandler.info(self)

	def offlineOperations(self):
		return self.serviceHandler.offlineOperations(self.ref)
