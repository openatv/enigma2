from config import *
from enigma import *

# CHECK ME.
RFMOD_CHANNEL_MIN = 21
RFMOD_CHANNEL_MAX = 69 + 1

class RFmod:
	def __init__(self):
		pass

	def setFunction(self, value):
		eRFmod.getInstance().setFunction(value)
	def setTestmode(self, value):
		eRFmod.getInstance().setTestmode(value)
	def setSoundFunction(self, value):
		eRFmod.getInstance().setSoundFunction(value)
	def setSoundCarrier(self, value):
		eRFmod.getInstance().setSoundCarrier(value)
	def setChannel(self, value):
		eRFmod.getInstance().setChannel(value)
	def setFinetune(self, value):
		eRFmod.getInstance().setFinetune(value)

def InitRFmod():

	config.rfmod = ConfigSubsection();
	config.rfmod.enable = configElement("config.rfmod.enable", configSelection, 1, (("enable", _("Enable")), ("disable", _("Disable"))) );
	config.rfmod.test = configElement("config.rfmod.test", configSelection, 0, (("disable", _("Disable")), ("enable", _("Enable"))) );
	config.rfmod.sound = configElement("config.rfmod.sound", configSelection, 0, (("enable", _("Enable")), ("disable", _("Disable"))) );
	config.rfmod.soundcarrier = configElement("config.rfmod.soundcarrier", configSelection, 1, ("4.5 MHz", "5.5 MHz", "6.0 MHz", "6.5 MHz") );
	config.rfmod.channel = configElement("config.rfmod.channel", configSelection, 36 - RFMOD_CHANNEL_MIN, tuple(["%d" % x for x in range(RFMOD_CHANNEL_MIN, RFMOD_CHANNEL_MAX)]))
	config.rfmod.finetune = configElement("config.rfmod.finetune", configSlider, 5, (1, 10));

	iRFmod = RFmod()

	def setFunction(configElement):
		iRFmod.setFunction(configElement.value);
	def setTestmode(configElement):
		iRFmod.setTestmode(configElement.value);
	def setSoundFunction(configElement):
		iRFmod.setSoundFunction(configElement.value);
	def setSoundCarrier(configElement):
		iRFmod.setSoundCarrier(configElement.value);
	def setChannel(configElement):
		iRFmod.setChannel(configElement.value +  30);
	def setFinetune(configElement):
		iRFmod.setFinetune(configElement.value - 5);

	# this will call the "setup-val" initial
	config.rfmod.enable.addNotifier(setFunction);
	config.rfmod.test.addNotifier(setTestmode);
	config.rfmod.sound.addNotifier(setSoundFunction);
	config.rfmod.soundcarrier.addNotifier(setSoundCarrier);
	config.rfmod.channel.addNotifier(setChannel);
	config.rfmod.finetune.addNotifier(setFinetune);
