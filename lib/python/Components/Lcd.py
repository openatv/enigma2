from config import config				#global config instance
from config import ConfigSlider
from config import configSelection
from config import ConfigSubsection
from config import configElement

from enigma import *

class LCD:
	def __init__(self):
		pass

	def setBright(self, value):
		eDBoxLCD.getInstance().setLCDBrightness(value * 20)
		pass

	def setContrast(self, value):
		eDBoxLCD.getInstance().setLCDContrast(value)
		pass

	def setInverted(self, value):
		eDBoxLCD.getInstance().setInverted(value)
		pass

def InitLcd():
	config.lcd = ConfigSubsection();
	config.lcd.bright = configElement("config.lcd.bright", ConfigSlider, 7, "");
	config.lcd.contrast = configElement("config.lcd.contrast", ConfigSlider, 2, "");
	config.lcd.standby = configElement("config.lcd.standby", ConfigSlider, 1, "");
	config.lcd.invert = configElement("config.lcd.invert", configSelection, 1, ("Disable", "Enable") );

	ilcd = LCD()

	def setLCDbright(configElement):
		ilcd.setBright(configElement.value);

	def setLCDcontrast(configElement):
		ilcd.setContrast(configElement.value);

	def setLCDinverted(configElement):
		ilcd.setInverted(configElement.value);

	config.lcd.bright.addNotifier(setLCDbright);
	config.lcd.contrast.addNotifier(setLCDcontrast);
	config.lcd.invert.addNotifier(setLCDinverted);
	
	