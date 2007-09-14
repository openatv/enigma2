from Source import Source
from enigma import eTimer

class FrontendInfo(Source):
	def __init__(self, service_source = None, frontend_source = None):
		Source.__init__(self)
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.updateFrontendData()

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
			service = self.service_source()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendData()
		else:
			return None
