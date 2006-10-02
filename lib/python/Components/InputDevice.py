from config import config, ConfigSlider, ConfigSubsection

class inputDevices:
	def __init__(self):
		pass
	def setRepeat(self, value):
		#print "setup rc repeat"
		pass
	def setDelay(self, value):
		#print "setup rc delay"
		pass

def InitInputDevices():
	config.inputDevices = ConfigSubsection();
	config.inputDevices.repeat = ConfigSlider(default=5, limits=(1, 10))
	config.inputDevices.delay = ConfigSlider(default=4, limits=(1, 10))

	#this instance anywhere else needed?	
	iDevices = inputDevices();	
	
	def inputDevicesRepeatChanged(configElement):
		iDevices.setRepeat(configElement.value);

	def inputDevicesDelayChanged(configElement):
		iDevices.setDelay(configElement.value);

	# this will call the "setup-val" initial
	config.inputDevices.repeat.addNotifier(inputDevicesRepeatChanged);
	config.inputDevices.delay.addNotifier(inputDevicesDelayChanged);
