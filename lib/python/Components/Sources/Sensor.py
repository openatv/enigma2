from Components.Sensors import sensors

from enigma import eTimer

from Source import Source

class SensorSource(Source):
	def __init__(self, update_interval = 500, sensorid = 0):
		self.update_interval = update_interval
		self.sensorid = sensorid
		Source.__init__(self)

		self.update_timer = eTimer()
		self.update_timer.callback.append(self.updateValue)
		self.update_timer.start(self.update_interval)

	def getValue(self):
		return sensors.getSensorValue(self.sensorid)
	
	def getUnit(self):
		return sensors.getSensorUnit(self.sensorid)

	def updateValue(self):
		self.changed((self.CHANGED_POLL,))

	def destroy(self):
		self.update_timer.callback.remove(self.updateValue)
