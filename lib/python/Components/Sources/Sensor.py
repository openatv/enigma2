from enigma import eTimer

from Components.Sensors import sensors
from Components.Sources.Source import Source


class SensorSource(Source):
	def __init__(self, update_interval=500, sensorid=None):
		Source.__init__(self)
		self.updateInterval = update_interval
		self.sensorId = sensorid
		if sensorid is not None:
			self.updateTimer = eTimer()
			self.updateTimer.callback.append(self.updateValue)
			self.updateTimer.start(self.updateInterval)

	def getValue(self):
		if self.sensorId is not None:
			return sensors.getSensorValue(self.sensorId)
		return None

	def getUnit(self):
		return sensors.getSensorUnit(self.sensorId)

	def updateValue(self):
		self.changed((self.CHANGED_POLL,))

	def destroy(self):
		if self.sensorId is not None:
			self.updateTimer.callback.remove(self.updateValue)
