from config import config, ConfigSelection, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists


class WOL:
	def __init__(self):
		pass

	def setWolState(self, value):
		print '[WakeOnLAN] set:',value
		if fileExists("/proc/stb/fp/wol"):
			f = open("/proc/stb/fp/wol", "w")
			f.write(value)
			f.close()
		elif fileExists("/proc/stb/power/wol"):
			f = open("/proc/stb/power/wol", "w")
			f.write(value)
			f.close()

def Init():
	if SystemInfo["WakeOnLAN"]:
		def setWOLmode(value):
			iwol.setWolState(config.network.wol.value)

		iwol = WOL()
		config.network.wol = ConfigSelection([("disable", _("No")), ("enable", _("Yes"))], default = "disable")
		config.network.wol.addNotifier(setWOLmode, initial_call=True)
	else:
		def doNothing():
			pass
		config.network.wol = ConfigNothing()
