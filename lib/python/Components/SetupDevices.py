import os

from config import config				#global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configBoolean

#temp. class for exhibition

class LCD:
	def __init__(self):
		pass

	def setBright(self, value):
		os.system("lcddimm " + str(value * 10))

	def setContrast(self, value):
		os.system("lcdcontrast " + str(value * 6))

def InitSetupDevices():
	config.timezone = ConfigSubsection();
	config.timezone.val = configElement("config.timezone.val", configBoolean, 1, ("GMT", "GMT+1", "GMT+2", "GMT+3", "GMT+4", "GMT+5", "GMT+6", "GMT+7", "GMT+8", "GMT+9") );

	config.rc = ConfigSubsection();
	config.rc.map = configElement("config.rc.map", configBoolean, 0, ("Default", "Classic") );

	config.rfmod = ConfigSubsection();
	config.rfmod.enable = configElement("config.rfmod.enable", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.test = configElement("config.rfmod.test", configBoolean, 1, ("Enable", "Disable") );
	config.rfmod.sound = configElement("config.rfmod.sound", configBoolean, 0, ("Enable", "Disable") );
	config.rfmod.soundcarrier = configElement("config.rfmod.soundcarrier", configBoolean, 1, ("4.5 MHz", "5.5 MHz", "6.0 MHz", "6.5 MHz") );
	config.rfmod.channel = configElement("config.rfmod.channel", configBoolean, 6, ("30", "31", "32", "33", "34", "35", "36", "37", "38", "39") );
	config.rfmod.finetune = configElement("config.rfmod.finetune", ConfigSlider, 5, "");

	config.keyboard = ConfigSubsection();
	config.keyboard.keymap = configElement("config.keyboard.keymap", configBoolean, 1, ("English", "German") );

	config.osd = ConfigSubsection();
	config.osd.alpha = configElement("config.osd.alpha", ConfigSlider, 0, "");
	config.osd.bright = configElement("config.osd.bright", ConfigSlider, 5, "");
	config.osd.contrast = configElement("config.osd.contrast", ConfigSlider, 5, "");
	config.osd.language = configElement("config.osd.language", configBoolean, 0, ("English", "English US") );

	config.lcd = ConfigSubsection();
	config.lcd.bright = configElement("config.lcd.bright", ConfigSlider, 7, "");
	config.lcd.contrast = configElement("config.lcd.contrast", ConfigSlider, 2, "");
	config.lcd.standby = configElement("config.lcd.standby", ConfigSlider, 1, "");
	config.lcd.invert = configElement("config.lcd.invert", configBoolean, 1, ("Enable", "Disable") );

	ilcd = LCD()

	def setLCDbright(configElement):
		ilcd.setBright(configElement.value);

	def setLCDcontrast(configElement):
		ilcd.setContrast(configElement.value);

	config.lcd.bright.addNotifier(setLCDbright);
	config.lcd.contrast.addNotifier(setLCDcontrast);

	config.parental = ConfigSubsection();
	config.parental.lock = configElement("config.parental.lock", configBoolean, 1, ("Enable", "Disable") );
	config.parental.setuplock = configElement("config.parental.setuplock", configBoolean, 1, ("Enable", "Disable") );

	config.expert = ConfigSubsection();
	config.expert.splitsize = configElement("config.expert.splitsize", configBoolean, 1, ("0.5Gbyte", "1.0 GByte", "1.5 GByte", "2.0 GByte") );
	config.expert.satpos = configElement("config.expert.satpos", configBoolean, 1, ("Enable", "Disable") );
	config.expert.fastzap = configElement("config.expert.fastzap", configBoolean, 0, ("Enable", "Disable") );
	config.expert.skipconfirm = configElement("config.expert.skipconfirm", configBoolean, 1, ("Enable", "Disable") );
	config.expert.hideerrors = configElement("config.expert.hideerrors", configBoolean, 1, ("Enable", "Disable") );
	config.expert.autoinfo = configElement("config.expert.autoinfo", configBoolean, 1, ("Enable", "Disable") );

	config.sat = ConfigSubsection();
	config.sat.satA = configElement("config.sat.satA", configBoolean, 1, ("Disabled" ,"Astra 19.2", "Hotbird 13.0") );
	config.sat.satB = configElement("config.sat.satB", configBoolean, 0, ("Disabled" ,"Astra 19.2", "Hotbird 13.0") );
	config.sat.diseqcA = configElement("config.sat.diseqcA", configBoolean, 3, ("no DiSEqC", "DiSEqC 1.0", "DiSEqC 1.1", "DiSEqC 1.2") );
	config.sat.diseqcB = configElement("config.sat.diseqcB", configBoolean, 0, ("no DiSEqC", "DiSEqC 1.0", "DiSEqC 1.1", "DiSEqC 1.2") );
	config.sat.posA = configElement("config.sat.posA", configBoolean, 0, ("DiSEqC A", "DiSEqC B", "DiSEqC C", "DiSEqC D") );
	config.sat.posB = configElement("config.sat.posB", configBoolean, 1, ("DiSEqC A", "DiSEqC B", "DiSEqC C", "DiSEqC D") );

	#config.blasel = ConfigSubsection();
	#config.blasel.val = configElement("", configBoolean, 0, ("bunt", "s/w", "gruen") );
	#config.inputDevices.delay = configElement("config.inputDevices.delay", ConfigSlider, 3);

	#this instance anywhere else needed?	
	#iDevices = inputDevices();	
	
	#def inputDevicesRepeatChanged(configElement):
	#	iDevices.setRepeat(configElement.value);

	#def inputDevicesDelayChanged(configElement):
	#	iDevices.setDelay(configElement.value);

	# this will call the "setup-val" initial
	#config.inputDevices.repeat.addNotifier(inputDevicesRepeatChanged);
	#config.inputDevices.delay.addNotifier(inputDevicesDelayChanged);
