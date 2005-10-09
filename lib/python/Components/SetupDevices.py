import os

from config import config				#global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configSelection

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
	config.timezone.val = configElement("config.timezone.val", configSelection, 1, ("GMT", "GMT+1", "GMT+2", "GMT+3", "GMT+4", "GMT+5", "GMT+6", "GMT+7", "GMT+8", "GMT+9") );

	config.rc = ConfigSubsection();
	config.rc.map = configElement("config.rc.map", configSelection, 0, ("Default", "Classic") );

	config.keyboard = ConfigSubsection();
	config.keyboard.keymap = configElement("config.keyboard.keymap", configSelection, 1, ("English", "German") );

	config.osd = ConfigSubsection();
	config.osd.alpha = configElement("config.osd.alpha", ConfigSlider, 0, "");
	config.osd.bright = configElement("config.osd.bright", ConfigSlider, 5, "");
	config.osd.contrast = configElement("config.osd.contrast", ConfigSlider, 5, "");
	config.osd.language = configElement("config.osd.language", configSelection, 0, ("English", "English US") );

	config.lcd = ConfigSubsection();
	config.lcd.bright = configElement("config.lcd.bright", ConfigSlider, 7, "");
	config.lcd.contrast = configElement("config.lcd.contrast", ConfigSlider, 2, "");
	config.lcd.standby = configElement("config.lcd.standby", ConfigSlider, 1, "");
	config.lcd.invert = configElement("config.lcd.invert", configSelection, 1, ("Enable", "Disable") );

	ilcd = LCD()

	def setLCDbright(configElement):
		ilcd.setBright(configElement.value);

	def setLCDcontrast(configElement):
		ilcd.setContrast(configElement.value);

	config.lcd.bright.addNotifier(setLCDbright);
	config.lcd.contrast.addNotifier(setLCDcontrast);

	config.parental = ConfigSubsection();
	config.parental.lock = configElement("config.parental.lock", configSelection, 1, ("Enable", "Disable") );
	config.parental.setuplock = configElement("config.parental.setuplock", configSelection, 1, ("Enable", "Disable") );

	config.expert = ConfigSubsection();
	config.expert.splitsize = configElement("config.expert.splitsize", configSelection, 1, ("0.5Gbyte", "1.0 GByte", "1.5 GByte", "2.0 GByte") );
	config.expert.satpos = configElement("config.expert.satpos", configSelection, 1, ("Enable", "Disable") );
	config.expert.fastzap = configElement("config.expert.fastzap", configSelection, 0, ("Enable", "Disable") );
	config.expert.skipconfirm = configElement("config.expert.skipconfirm", configSelection, 1, ("Enable", "Disable") );
	config.expert.hideerrors = configElement("config.expert.hideerrors", configSelection, 1, ("Enable", "Disable") );
	config.expert.autoinfo = configElement("config.expert.autoinfo", configSelection, 1, ("Enable", "Disable") );
