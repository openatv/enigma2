from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigSelection
from enigma import eDBoxLCD
from Components.SystemInfo import SystemInfo

config.plugins.minitv = ConfigSubsection()
config.plugins.minitv.enable = ConfigSelection(default = "disable", choices = [ ("enable", "enable"), ("disable", "disable")])
config.plugins.minitv.decoder = ConfigSelection(default = "0", choices = [ ("0", "0"), ("1", "1")])

class MiniTV:
	def __init__(self):
		config.plugins.minitv.enable.addNotifier(self.miniTVChanged, initial_call = True)
		config.plugins.minitv.decoder.addNotifier(self.miniTVDecoderChanged, initial_call = True)
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call = False)

	def getExtensionName(self):
		if config.plugins.minitv.enable.value == "enable":
			return _("Disable MiniTV")

		return _("Enable MiniTV")

	def getExtensionNameDecoder(self):
		if config.plugins.minitv.decoder.value == "0":
			return _("Show PIP in MiniTV")

		return _("Show Live in MiniTV")

	def showMiniTV(self):
		old_value = config.plugins.minitv.enable.value
		config.plugins.minitv.enable.value = (old_value == "enable") and "disable" or "enable"
		config.plugins.minitv.enable.save()

	def showMiniTVDecoder(self):
		old_value = config.plugins.minitv.decoder.value
		if old_value == "0":
			config.plugins.minitv.decoder.value =  "1"
		else:
			config.plugins.minitv.decoder.value =  "0"
		config.plugins.minitv.decoder.save()

	def miniTVChanged(self, configElement):
		self.setMiniTV(configElement.value)

	def miniTVDecoderChanged(self, configElement):
		self.setMiniTVDecoder(configElement.value)

	def setMiniTV(self, value):
		cur_value = open("/proc/stb/lcd/live_enable", "r").read().strip()
		if cur_value != value:
			open("/proc/stb/lcd/live_enable", "w").write(value)

	def setMiniTVDecoder(self, value):
		if SystemInfo["LcdLiveTVPiP"]:
			cur_value = open("/proc/stb/lcd/live_decoder", "r").read()
			if cur_value != value:
				open("/proc/stb/lcd/live_decoder", "w").write(value)

	def standbyCounterChanged(self, configElement):
		from Screens.Standby import inStandby
		if self.leaveStandby not in inStandby.onClose:
			inStandby.onClose.append(self.leaveStandby)

		self.setMiniTV("disable")
		self.setMiniTVDecoder("0")

	def leaveStandby(self):
		self.setMiniTV(config.plugins.minitv.enable.value)
		self.setMiniTVDecoder(config.plugins.minitv.decoder.value)

minitv_instance = MiniTV()

def addExtentions(infobarExtensions):
	infobarExtensions.addExtension((minitv_instance.getExtensionName, minitv_instance.showMiniTV, lambda: True), None)
	if SystemInfo["LcdLiveTVPiP"]:
		infobarExtensions.addExtension((minitv_instance.getExtensionNameDecoder, minitv_instance.showMiniTVDecoder, lambda: True), None)

def autoStart(reason, **kwargs):
	if reason == 1:
		minitv_instance.setMiniTV("standby")
		minitv_instance.setMiniTVDecoder("0")

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

