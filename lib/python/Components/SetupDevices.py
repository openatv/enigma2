from config import config, ConfigSlider, ConfigSelection, ConfigSubsection, ConfigOnOff, ConfigText
from Components.Timezones import timezones
from Components.Language import language

def InitSetupDevices():
	
	def timezoneNotifier(configElement):
		timezones.activateTimezone(configElement.index)
		
	config.timezone = ConfigSubsection();
	config.timezone.val = ConfigSelection(default = timezones.getDefaultTimezone(), choices = timezones.getTimezoneList())
	config.timezone.val.addNotifier(timezoneNotifier)

	config.keyboard = ConfigSubsection();
	config.keyboard.keymap = ConfigSelection(choices = [("en", _("English")), ("de",_("German"))])

	def languageNotifier(configElement):
		language.activateLanguage(configElement.value)
	
	config.osd = ConfigSubsection()
	config.osd.language = ConfigText(default = "en_EN");
	config.osd.language.addNotifier(languageNotifier)

	config.parental = ConfigSubsection();
	config.parental.lock = ConfigOnOff(default = False)
	config.parental.setuplock = ConfigOnOff(default = False)

	config.expert = ConfigSubsection();
	config.expert.satpos = ConfigOnOff(default = True)
	config.expert.fastzap = ConfigOnOff(default = True)
	config.expert.skipconfirm = ConfigOnOff(default = False)
	config.expert.hideerrors = ConfigOnOff(default = False)
	config.expert.autoinfo = ConfigOnOff(default = True)
