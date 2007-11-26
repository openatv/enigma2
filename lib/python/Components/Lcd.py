from config import config, ConfigSubsection, ConfigSlider, ConfigYesNo, ConfigNothing

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

	def isOled(self):
		return eDBoxLCD.getInstance().isOled()

def InitLcd():

	def setLCDbright(configElement):
		ilcd.setBright(configElement.value);

	def setLCDcontrast(configElement):
		ilcd.setContrast(configElement.value);

	def setLCDinverted(configElement):
		ilcd.setInverted(configElement.value);

	ilcd = LCD()

	config.lcd = ConfigSubsection();

	config.lcd.bright = ConfigSlider(default=10, limits=(0, 10))
	config.lcd.bright.addNotifier(setLCDbright);
	config.lcd.bright.apply = lambda : setLCDbright(config.lcd.bright)

	if not ilcd.isOled():
		config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
		config.lcd.contrast.addNotifier(setLCDcontrast);
	else:
		config.lcd.contrast = ConfigNothing()

	config.lcd.standby = ConfigSlider(default=0, limits=(0, 10))
	config.lcd.standby.apply = lambda : setLCDbright(config.lcd.standby)

	config.lcd.invert = ConfigYesNo(default=False)
	config.lcd.invert.addNotifier(setLCDinverted);
