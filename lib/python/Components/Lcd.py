from config import config, ConfigSubsection, ConfigSlider, ConfigYesNo

from enigma import eDBoxLCD

class LCD:
	def __init__(self):
		pass

	def setBright(self, value):
		value *= 255
		value /= 10
		if value > 255:
			value = 255
		eDBoxLCD.getInstance().setLCDBrightness(value)

	def setContrast(self, value):
		value *= 63
		value /= 20
		if value > 63:
			value = 63
		eDBoxLCD.getInstance().setLCDContrast(value)

	def setInverted(self, value):
		if value:
			value = 255
		eDBoxLCD.getInstance().setInverted(value)

def InitLcd():
	config.lcd = ConfigSubsection();
	config.lcd.bright = ConfigSlider(default=10, limits=(0, 10))
	config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
	config.lcd.standby = ConfigSlider(default=0, limits=(0, 10))
	config.lcd.invert = ConfigYesNo(default=False)

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
