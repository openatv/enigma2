from subprocess import DEVNULL, SubprocessError, check_output as checkOutput

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.StbHardware import getFPVersion


def getUpgradeVersion():
	version = None
	try:
		output = checkOutput(("/usr/sbin/fpupgrade", "--version"), stderr=DEVNULL, text=True, timeout=5)
		if output.startswith("FP update tool v"):
			versionText = output[16:].strip()
			if versionText.isdecimal():
				version = int(versionText)
	except (OSError, SubprocessError, UnicodeError):
		pass
	return version


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

		version = str(getFPVersion() or "N/A")
		newVersion = str(getUpgradeVersion() or "N/A")

		self["text"] = Label(_("Your front panel processor firmware must be upgraded.\nPress OK to start upgrade."))
		self["oldversion_label"] = Label(_("Current version:"))
		self["newversion_label"] = Label(_("New version:"))

		self["oldversion"] = Label(version)
		self["newversion"] = Label(newVersion)

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
			<ePixmap pixmap="icons/input_error.png" position="5,5" size="53,53" alphatest="on" />
		</screen>"""

	def __init__(self, session, message):
		Screen.__init__(self, session)

		self["text"] = StaticText(message)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.ok,
		})

	def ok(self):
		self.close()


def Plugins(**kwargs):
	version = getFPVersion()
	newVersion = getUpgradeVersion()
	pluginList = []
	if newVersion is not None:
		# The legacy fpupgrade tool uses integer revisions; newer Dreamboxes
		# report dotted versions and use a different firmware update path.
		try:
			version = int(version)
		except (TypeError, ValueError):
			version = None
		if version is not None and version < newVersion:
			pluginList.append(PluginDescriptor(name=_("FP Upgrade"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=True, fnc=(8, FPUpgrade)))

	try:
		with open("/proc/stb/message") as messageFile:
			message = messageFile.read()
		pluginList.append(PluginDescriptor(name=_("System Message Check"), where=PluginDescriptor.WHERE_WIZARD, needsRestart=True, fnc=(9, SystemMessage, message)))
	except OSError:
		pass

	return pluginList
