from config import *
from enigma import *

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
	config.rfmod.enable = configElement("config.rfmod.enable", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.test = configElement("config.rfmod.test", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.sound = configElement("config.rfmod.sound", configBoolean, 0, ("Enable", "Disable") );
	config.rfmod.soundcarrier = configElement("config.rfmod.soundcarrier", configBoolean, 1, ("4.5 MHz", "5.5 MHz", "6.0 MHz", "6.5 MHz") );
	config.rfmod.channel = configElement("config.rfmod.channel", configBoolean, 6, ("30", "31", "32", "33", "34", "35", "36", "37", "38", "39") );
	config.rfmod.finetune = configElement("config.rfmod.finetune", ConfigSlider, 5, "");

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
		iRFmod.setChannel(configElement.value);
	def setFinetune(configElement):
		iRFmod.setFinetune(configElement.value);

	# this will call the "setup-val" initial
	config.rfmod.enable.addNotifier(setFunction);
	config.rfmod.test.addNotifier(setTestmode);
	config.rfmod.sound.addNotifier(setSoundFunction);
	config.rfmod.soundcarrier.addNotifier(setSoundCarrier);
	config.rfmod.channel.addNotifier(setChannel);
	config.rfmod.finetune.addNotifier(setFinetune);
