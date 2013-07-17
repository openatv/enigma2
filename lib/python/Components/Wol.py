from config import config, ConfigSubsection, ConfigSelection, ConfigNothing
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from os import system

class WOL:
	def __init__(self):
		pass

	def setWolState(self, value):
		print 'setWOL',value
		f = open("/proc/stb/fp/wol", "w")
		f.write(value)
		f.close()
		enable = value == 'enable' and True or False
		system("ethtool -s eth0 wol %s" % (enable and "g" or "d"))

def Init():
	if SystemInfo["WOL"]:
		def setWOLmode(configElement):
			iwol.setWolState(configElement.value);
		iwol = WOL()
		config.network.wol = ConfigSelection([("disable", _("No")), ("enable", _("Yes"))], default = "disable")
		config.network.wol.addNotifier(setWOLmode, immediate_feedback=True);
		config.network.wol.apply = lambda : setWOLmode(config.network.wol)
	else:
		def doNothing():
			pass
		config.network.wol = ConfigNothing()
		config.network.wol.apply = lambda : doNothing()
