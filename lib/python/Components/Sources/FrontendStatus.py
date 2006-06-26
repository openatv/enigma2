from Source import Source
from enigma import eTimer, iFrontendInformation

class FrontendStatus(Source):
	def __init__(self, service_source = None, frontend_source = None):
		Source.__init__(self)
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.invalidate()
		
		self.poll_timer = eTimer()
		self.poll_timer.timeout.get().append(self.updateFrontendStatus)
		self.poll_timer.start(1000)

	def invalidate(self):
		self.snr = self.agc = self.ber = self.lock = None

	def updateFrontendStatus(self):
		print "update frontend status. %d downstream elements" % len(self.downstream_elements)
		feinfo = self.getFrontendInfo()
		if feinfo is None:
			self.invalidate()
		else:
			(self.snr, self.agc, self.ber, self.lock) = \
				[feinfo.getFrontendInfo(x) \
					for x in [iFrontendInformation.signalPower, 
						iFrontendInformation.signalQuality, 
						iFrontendInformation.bitErrorRate, 
						iFrontendInformation.lockState] ]

		self.changed()

	def getFrontendInfo(self):
		if self.frontend_source:
			return self.frontend_source()
		elif self.service_source:
			service = self.service_source()
			return service and service.frontendInfo()
		else:
			return None
