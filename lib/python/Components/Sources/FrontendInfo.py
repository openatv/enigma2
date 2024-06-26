from enigma import iPlayableService, eDVBResourceManager, iServiceInformation
from Components.PerServiceDisplay import PerServiceBase
from Components.Sources.Source import Source


class FrontendInfo(Source, PerServiceBase):
	def __init__(self, service_source=None, frontend_source=None, navcore=None):
		self.navcore = None
		Source.__init__(self)
		if navcore:
			PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evTunedIn: self.updateFrontendData,
				iPlayableService.evEnd: self.serviceEnd
			})
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			res_mgr.frontendUseMaskChanged.get().append(self.updateTunerMask)
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.tuner_mask = 0
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
			if not self.frontend_source:
				self.frontend_type = self.getFrontendTransponderType()
			if not self.frontend_type:
				self.frontend_type = data.get("tuner_type")
		self.changed((self.CHANGED_ALL, ))

	def updateTunerMask(self, mask):
		self.tuner_mask = mask
		if mask:
			self.updateFrontendData()
		self.changed((self.CHANGED_ALL, ))

	def getFrontendData(self):
		if self.frontend_source:
			feinfo = {}
			try:
				frontend = self.frontend_source()
				if frontend:
					frontend.getFrontendData(feinfo)
			except AttributeError:
				pass
			return feinfo
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

	def getFrontendTransponderType(self):
		service = None
		if self.service_source:
			service = self.navcore and self.service_source()
		elif self.navcore:
			service = self.navcore.getCurrentService()
		info = service and service.info()
		data = info and info.getInfoObject(iServiceInformation.sTransponderData)
		if data and data != -1:
			return data.get("tuner_type")
		return None

	def destroy(self):
		if not self.frontend_source and not self.service_source:
			PerServiceBase.destroy(self)
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			res_mgr.frontendUseMaskChanged.get().remove(self.updateTunerMask)
		Source.destroy(self)
