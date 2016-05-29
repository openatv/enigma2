from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigSelection
from enigma import eDBoxLCD

config.plugins.minitv = ConfigSubsection()
config.plugins.minitv.enable = ConfigSelection(default = "disable", choices = [ ("enable", "enable"), ("disable", "disable")])

class MiniTV:
	def __init__(self):
		config.plugins.minitv.enable.addNotifier(self.miniTVChanged, initial_call = True)
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call = False)

	def getExtensionName(self):
		if config.plugins.minitv.enable.value == "enable":
			return _("Disable MiniTV")

		return _("Enable MiniTV")

	def showMiniTV(self):
		old_value = config.plugins.minitv.enable.value
		config.plugins.minitv.enable.value = (old_value == "enable") and "disable" or "enable"
		config.plugins.minitv.enable.save()

	def miniTVChanged(self, configElement):
		self.setMiniTV(configElement.value)

	def setMiniTV(self, value):
		cur_value = open("/proc/stb/lcd/live_enable", "r").read().strip()
		if cur_value != value:
			open("/proc/stb/lcd/live_enable", "w").write(value)

	def standbyCounterChanged(self, configElement):
		from Screens.Standby import inStandby
		if self.leaveStandby not in inStandby.onClose:
			inStandby.onClose.append(self.leaveStandby)

		self.setMiniTV("disable")

	def leaveStandby(self):
		self.setMiniTV(config.plugins.minitv.enable.value)

minitv_instance = MiniTV()

def addExtentions(infobarExtensions):
	infobarExtensions.addExtension((minitv_instance.getExtensionName, minitv_instance.showMiniTV, lambda: True), None)

def autoStart(reason, **kwargs):
	if reason == 1:
		minitv_instance.setMiniTV("standby")

def Plugins(**kwargs):
	list = []
	list.append(
		PluginDescriptor(name="MiniTV",
		description="MiniTV",
		where = [PluginDescriptor.WHERE_EXTENSIONSINGLE],
		fnc = addExtentions))

	list.append(
		PluginDescriptor(
		where = [PluginDescriptor.WHERE_AUTOSTART],
		fnc = autoStart))

	return list

