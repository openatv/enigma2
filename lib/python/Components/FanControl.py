import os

from Components.config import config, ConfigSubList, ConfigSubsection, ConfigSlider
from Tools.BoundFunction import boundFunction

class FanControl:
	# ATM there's only support for one fan
	def __init__(self):
		if os.path.exists("/proc/stb/fp/fan_vlt") or os.path.exists("/proc/stb/fp/fan_pwm") or os.path.exists("/proc/stb/fp/fan_speed"):
			self.fancount = 1
		else:
			self.fancount = 0
		self.createConfig()

	def createConfig(self):
		def setVlt(fancontrol, fanid, configElement):
			fancontrol.setVoltage(fanid, configElement.value)
		def setPWM(fancontrol, fanid, configElement):
			fancontrol.setPWM(fanid, configElement.value)
		
		config.fans = ConfigSubList()
		for fanid in range(self.getFanCount()):
			default_vlt = self.getVoltage(fanid)
			default_pwm = self.getPWM(fanid)
			fan = ConfigSubsection()
			fan.vlt = ConfigSlider(default = 16, increment = 5, limits = (0, 255))
			fan.pwm = ConfigSlider(default = 0, increment = 5, limits = (0, 255))
			fan.vlt.addNotifier(boundFunction(setVlt, self, fanid))
			fan.pwm.addNotifier(boundFunction(setPWM, self, fanid))
			config.fans.append(fan)
			
	def getConfig(self, fanid):
		return config.fans[fanid]
	
	def getFanCount(self):
		return self.fancount
	
	def hasRPMSensor(self, fanid):
		return os.path.exists("/proc/stb/fp/fan_speed")
	
	def hasFanControl(self, fanid):
		return os.path.exists("/proc/stb/fp/fan_vlt") or os.path.exists("/proc/stb/fp/fan_pwm")
	
	def getFanSpeed(self, fanid):
		f = open("/proc/stb/fp/fan_speed", "r")
		value = int(f.readline().strip()[:-4])
		f.close()
		return value
	
	def getVoltage(self, fanid):
		f = open("/proc/stb/fp/fan_vlt", "r")
		value = int(f.readline().strip(), 16)
		f.close()
		return value
	
	def setVoltage(self, fanid, value):
		if value > 255:
			return
		f = open("/proc/stb/fp/fan_vlt", "w")
		f.write("%x" % value)
		f.close()
		
	def getPWM(self, fanid):
		f = open("/proc/stb/fp/fan_pwm", "r")
		value = int(f.readline().strip(), 16)
		f.close()
		return value
	
	def setPWM(self, fanid, value):
		if value > 255:
			return
		f = open("/proc/stb/fp/fan_pwm", "w")
		f.write("%x" % value)
		f.close()
	
fancontrol = FanControl()