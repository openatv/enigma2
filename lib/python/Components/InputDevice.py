from config import configElement
from config import config

class inputDevices:
	def __init__(self):
		pass
	def setRepeat(self, value):
		pass
	def setDelay(self, value):
		pass

def InitInputDevices():
	config.inputDevices = config;
	config.inputDevices.repeat = configElement("config.inputDevices.repeat", config.Slider, 10);
	config.inputDevices.delay = configElement("config.inputDevices.delay", config.Slider, 10);
	
	def inputDevicesRepeatChanged(configElement):
		print "setup rc repeat"
		#inputDevices.setRepeat(configElement.value);

	def inputDevicesDelayChanged(configElement):
		print "setup rc delay"
		#inputDevices.setDelay(configElement.value);

	# this will call the "setup-val" initial
	config.inputDevices.repeat.addNotifier(inputDevicesRepeatChanged);
	config.inputDevices.delay.addNotifier(inputDevicesDelayChanged);
