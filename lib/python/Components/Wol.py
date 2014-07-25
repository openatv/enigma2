from config import config, ConfigSelection, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from boxbranding import getBoxType

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
	if SystemInfo["WakeOnLAN"] and not getBoxType() in ('gbquadplus', 'gbquad', 'gb800ueplus', 'gb800seplus', 'gbipbox'):
		def setWOLmode(value):
			iwol.setWolState(config.network.wol.value)
		iwol = WOL()
		config.network.wol = ConfigSelection([("disable", _("No")), ("enable", _("Yes"))], default = "disable")
		config.network.wol.addNotifier(setWOLmode, initial_call=True)

	elif SystemInfo["ETWOL"]:
		def setWOLmode(value):
			iwol.setWolState(config.network.wol.value)
		iwol = WOL()
		config.network.wol = ConfigSelection([("off", _("No")), ("on", _("Yes"))], default = "off")
		config.network.wol.addNotifier(setWOLmode, initial_call=True)

	elif SystemInfo["WakeOnLAN"] and getBoxType() in ('gbquadplus', 'gbquad', 'gb800ueplus', 'gb800seplus', 'gbipbox'):
		def setWOLmode(value):
			iwol.setWolState(config.network.wol.value)
		iwol = WOL()
		config.network.wol = ConfigSelection([("off", _("No")), ("on", _("Yes"))], default = "off")
		config.network.wol.addNotifier(setWOLmode, initial_call=True)

	else:
		def doNothing():
			pass
		config.network.wol = ConfigNothing()
