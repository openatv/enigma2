from config import config, ConfigSubsection, ConfigSelection, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from boxbranding import getBoxType

class WOL:
	def __init__(self):
		pass

	def setWolState(self, value):
		print '[WOL] set:',value
		f = open("/proc/stb/fp/wol", "w")
		f.write(value)
		f.close()

def Init():
	if SystemInfo["WOL"]:
		self.BoxType = getBoxType()
		if not self.BoxType == 'gbquad' :
			def setWOLmode(value):
				iwol.setWolState(config.network.wol.value);
			iwol = WOL()
			config.network.wol = ConfigSelection([("disable", _("No")), ("enable", _("Yes"))], default = "disable")
			config.network.wol.addNotifier(setWOLmode, initial_call=True)
	else:
		def doNothing():
			pass
		config.network.wol = ConfigNothing()
