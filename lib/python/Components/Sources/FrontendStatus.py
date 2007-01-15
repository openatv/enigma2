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
		print "updateFrontendStatus"
		status = self.getFrontendStatus()
		if not status:
			self.invalidate()
		else:
			self.snr = status.get("tuner_signal_power")
			self.agc = status.get("tuner_signal_quality")
			self.ber = status.get("tuner_bit_error_rate")
			self.lock = status.get("tuner_locked")
		self.changed((self.CHANGED_ALL, ))

	def getFrontendStatus(self):
		if self.frontend_source:
			frontend = self.frontend_source()
			if frontend:
				dict = { }
				frontend.getFrontendStatus(dict)
		elif self.service_source:
			service = self.service_source()
			feinfo = service and service.frontendInfo()
			return feinfo and feinfo.getFrontendStatus()
		else:
			return None

	def doSuspend(self, suspended):
		if suspended:
			self.poll_timer.stop()
		else:
			self.poll_timer.start(1000)

