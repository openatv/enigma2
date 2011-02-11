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
		return int(r[16:17])

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

class SystemMessage(Screen):
	skin = """
		<screen position="150,200" size="450,200" title="System Message" >
			<widget source="text" position="0,0" size="450,200" font="Regular;20" halign="center" valign="center" render="Label" />
			<ePixmap pixmap="skin_default/icons/input_error.png" position="5,5" size="53,53" alphatest="on" />
		</screen>"""
	def __init__(self, session, message):
		from Components.Sources.StaticText import StaticText

		Screen.__init__(self, session)

		self["text"] = StaticText(message)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.ok,
		})

	def ok(self):
		self.close()

def Plugins(**kwargs):
	from Tools.DreamboxHardware import getFPVersion
	from Screens.MessageBox import MessageBox

	version = getFPVersion()
	newversion = getUpgradeVersion() or 0
	list = []
	if version is not None and version < newversion:
		list.append(PluginDescriptor(name="FP Upgrade", where = PluginDescriptor.WHERE_WIZARD, needsRestart = True, fnc=(8, FPUpgrade)))

	try:
		msg = open("/proc/stb/message").read()
		list.append(PluginDescriptor(name="System Message Check", where = PluginDescriptor.WHERE_WIZARD, needsRestart = True, fnc=(9, SystemMessage, msg)))
	except:
		pass

	return list
