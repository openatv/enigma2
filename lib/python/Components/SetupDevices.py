from config import config, ConfigSelection, ConfigSubsection, ConfigOnOff, ConfigText
from boxbranding import getBrandOEM, getMachineBrand
from Components.Timezones import timezones
from Components.Language import language
from Components.Keyboard import keyboard

def InitSetupDevices():

	def timezoneNotifier(configElement):
		timezones.activateTimezone(configElement.index)

	config.timezone = ConfigSubsection()
	config.timezone.val = ConfigSelection(default = timezones.getDefaultTimezone(), choices = timezones.getTimezoneList())
	config.timezone.val.addNotifier(timezoneNotifier)

	def keyboardNotifier(configElement):
		keyboard.activateKeyboardMap(configElement.index)

	config.keyboard = ConfigSubsection()
	config.keyboard.keymap = ConfigSelection(default = keyboard.getDefaultKeyboardMap(), choices = keyboard.getKeyboardMaplist())
	config.keyboard.keymap.addNotifier(keyboardNotifier)

	def languageNotifier(configElement):
		language.activateLanguage(configElement.value)

	config.osd = ConfigSubsection()
	if getMachineBrand() in ('Vimastec'):
		config.osd.language = ConfigText(default = "fr_FR")
	elif getMachineBrand() in ('Zgemma','Beyonwiz') or getBrandOEM() in ('airdigital'):
		config.osd.language = ConfigText(default = "en_US")
	else:
		config.osd.language = ConfigText(default = "de_DE")
	config.osd.language.addNotifier(languageNotifier)

	config.parental = ConfigSubsection()
	config.parental.lock = ConfigOnOff(default = False)
	config.parental.setuplock = ConfigOnOff(default = False)

	config.expert = ConfigSubsection()
	config.expert.satpos = ConfigOnOff(default = True)
	config.expert.fastzap = ConfigOnOff(default = True)
	config.expert.skipconfirm = ConfigOnOff(default = False)
	config.expert.hideerrors = ConfigOnOff(default = False)
	config.expert.autoinfo = ConfigOnOff(default = True)
