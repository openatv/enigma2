from enigma import iPlayableService
from Source import Source
from Components.PerServiceDisplay import PerServiceBase

class FrontendInfo(Source, PerServiceBase):
	def __init__(self, service_source = None, frontend_source = None, navcore = None):
		self.navcore = None
		Source.__init__(self)
		if navcore:
			PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evTunedIn: self.updateFrontendData,
				iPlayableService.evEnd: self.serviceEnd
			})
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.updateFrontendData()

	def serviceEnd(self):
#		import pdb
#		pdb.set_trace()
		self.slot_number = self.frontend_type = None
		self.changed((self.CHANGED_CLEAR, ))

	def updateFrontendData(self):
		data = self.getFrontendData()
		if not data:
			self.slot_number = self.frontend_type = None
		else:
			self.slot_number = data.get("tuner_number")
			self.frontend_type = data.get("tuner_type")
		self.changed((self.CHANGED_ALL, ))

	def getFrontendData(self):
		if self.frontend_source:
			frontend = self.frontend_source()
			dict = { }
			if frontend:
				frontend.getFrontendData(dict)
			return dict
		elif self.service_source:
			service = self.navcore and self.service_source()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendData()
		elif self.navcore:
			service = self.navcore.getCurrentService()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendData()
		else:
			return None

	def destroy(self):
		if not self.frontend_source and not self.service_source:
			PerServiceBase.destroy(self)
		Source.destroy(self)
