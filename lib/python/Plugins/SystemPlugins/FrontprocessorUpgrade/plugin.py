from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor

def getUpgradeVersion():
	import os
	try:
		r = os.popen("fpupgrade --version").read()
	except IOError:
		return None
	if r[:16] != "FP update tool v":
		return None
	else:
		return int(r[16:])

class FPUpgrade(Screen):
	skin = """
		<screen position="150,200" size="450,200" title="FP upgrade required" >
			<widget name="text" position="0,0" size="550,50" font="Regular;20" />
			<widget name="oldversion_label" position="10,100" size="290,25" font="Regular;20" />
			<widget name="newversion_label" position="10,125" size="290,25" font="Regular;20" />
			<widget name="oldversion" position="300,100" size="50,25" font="Regular;20" />
			<widget name="newversion" position="300,125" size="50,25" font="Regular;20" />
		</screen>"""
	def __init__(self, session):
		self.skin = FPUpgrade.skin
		Screen.__init__(self, session)
		
		from Tools.DreamboxHardware import getFPVersion
		version = str(getFPVersion() or "N/A")
		newversion = str(getUpgradeVersion() or "N/A")

		self["text"] = Label(_("Your frontprocessor firmware must be upgraded.\nPress OK to start upgrade."))
		self["oldversion_label"] = Label(_("Current version:"))
		self["newversion_label"] = Label(_("New version:"))

		self["oldversion"] = Label(version)
		self["newversion"] = Label(newversion)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.ok,
			"cancel": self.close,
		})

	def ok(self):
		self.close(4)

def Plugins(**kwargs):
	from Tools.DreamboxHardware import getFPVersion
	version = getFPVersion()
	newversion = getUpgradeVersion() or 0
	if version is not None and version < newversion:
		return PluginDescriptor(name="FP Upgrade", where = PluginDescriptor.WHERE_WIZARD, fnc=(8, FPUpgrade))
	else:
		return [ ]
