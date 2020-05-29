from __future__ import absolute_import
from boxbranding import getMachineBrand

from Components.config import ConfigOnOff, ConfigSelection, ConfigSubsection, ConfigText, config
from Components.Keyboard import keyboard
from Components.Language import language

def InitSetupDevices():
	def keyboardNotifier(configElement):
		keyboard.activateKeyboardMap(configElement.index)

	config.keyboard = ConfigSubsection()
	config.keyboard.keymap = ConfigSelection(default=keyboard.getDefaultKeyboardMap(), choices=keyboard.getKeyboardMaplist())
	config.keyboard.keymap.addNotifier(keyboardNotifier)

	def languageNotifier(configElement):
		language.activateLanguage(configElement.value)

	config.osd = ConfigSubsection()
	if getMachineBrand() == 'Atto.TV':
		defaultLanguage = "pt_BR"
	elif getMachineBrand() == 'Zgemma':
		defaultLanguage = "en_US"
	elif getMachineBrand() == 'Beyonwiz':
		defaultLanguage = "en_GB"
	else:
		defaultLanguage = "de_DE"
	config.osd.language = ConfigText(default=defaultLanguage)
	config.osd.language.addNotifier(languageNotifier)

	config.parental = ConfigSubsection()
	config.parental.lock = ConfigOnOff(default=False)
	config.parental.setuplock = ConfigOnOff(default=False)

	config.expert = ConfigSubsection()
	config.expert.satpos = ConfigOnOff(default=True)
	config.expert.fastzap = ConfigOnOff(default=True)
	config.expert.skipconfirm = ConfigOnOff(default=False)
	config.expert.hideerrors = ConfigOnOff(default=False)
	config.expert.autoinfo = ConfigOnOff(default=True)
