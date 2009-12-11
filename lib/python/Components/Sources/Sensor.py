from Components.Sensors import sensors

from enigma import eTimer

from Source import Source

class SensorSource(Source):
	def __init__(self, update_interval = 500, sensorid = None):
		self.update_interval = update_interval
		self.sensorid = sensorid
		Source.__init__(self)

		if sensorid is not None:
			self.update_timer = eTimer()
			self.update_timer.callback.append(self.updateValue)
			self.update_timer.start(self.update_interval)

	def getValue(self):
		if self.sensorid is not None:
			return sensors.getSensorValue(self.sensorid)
		return None
	
	def getUnit(self):
		return sensors.getSensorUnit(self.sensorid)

	def updateValue(self):
		self.changed((self.CHANGED_POLL,))

	def destroy(self):
		if self.sensorid is not None:
			self.update_timer.callback.remove(self.updateValue)
