from Source import Source
from enigma import eTimer

class FrontendStatus(Source):
	def __init__(self, service_source = None, frontend_source = None, update_interval = 1000):
		Source.__init__(self)
		self.update_interval = update_interval
		self.service_source = service_source
		self.frontend_source = frontend_source
		self.invalidate()
		self.poll_timer = eTimer()
		self.poll_timer.callback.append(self.updateFrontendStatus)
		self.poll_timer.start(update_interval, True)

	def invalidate(self):
		self.snr = self.agc = self.ber = self.lock = self.snr_db = None

	def updateFrontendStatus(self):
		status = self.getFrontendStatus()
		if not status:
			self.invalidate()
		else:
			self.snr = status.get("tuner_signal_quality")
			self.snr_db = status.get("tuner_signal_quality_db")
			self.agc = status.get("tuner_signal_power")
			self.ber = status.get("tuner_bit_error_rate")
			self.lock = status.get("tuner_locked")
		self.changed((self.CHANGED_ALL, ))
		self.poll_timer.start(self.update_interval, True)

	def getFrontendStatus(self):
		if self.frontend_source:
			frontend = self.frontend_source()
			dict = { }
			if frontend:
				frontend.getFrontendStatus(dict)
			return dict
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
			self.updateFrontendStatus()

	def destroy(self):
		self.poll_timer.callback.remove(self.updateFrontendStatus)
		Source.destroy(self)

