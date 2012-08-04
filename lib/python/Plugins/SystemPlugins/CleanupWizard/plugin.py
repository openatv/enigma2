from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigYesNo, ConfigNumber
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from CleanupWizard import checkFreeSpaceAvailable

config.plugins.cleanupwizard = ConfigSubsection()
config.plugins.cleanupwizard.enable = ConfigYesNo(default = True)
config.plugins.cleanupwizard.threshold = ConfigNumber(default = 2048)

freeSpace = checkFreeSpaceAvailable()
print "[CleanupWizard] freeSpaceAvailable-->",freeSpace

if freeSpace is None:
	internalMemoryExceeded = 0
elif int(freeSpace) <= config.plugins.cleanupwizard.threshold.value:
	internalMemoryExceeded = 1
else:
	internalMemoryExceeded = 0

class CleanupWizardConfiguration(Screen, ConfigListScreen):

	skin = """
		<screen name="CleanupWizardConfiguration" position="center,center" size="560,440" title="CleanupWizard settings" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" zPosition="2" position="5,50" size="550,300" scrollbarMode="showOnDemand" transparent="1" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,390" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="status" render="Label" position="10,400" size="540,40" zPosition="10" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1"/>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.EnableEntry = None
		self.freeSpaceEntry = None
		self.onChangedEntry = [ ]
		self.setup_title = _("Cleanup Wizard")

		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["status"] = StaticText()
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Cleanup Wizard settings"))

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def createSetup(self):
		self.list = []
		self.EnableEntry = getConfigListEntry(_("Enable Cleanup Wizard?"), config.plugins.cleanupwizard.enable)
		self.freeSpaceEntry = getConfigListEntry(_("Warn if free space drops below (kB):"), config.plugins.cleanupwizard.threshold)
		self.list.append( self.EnableEntry )
		if config.plugins.cleanupwizard.enable.value is True:
			self.list.append( self.freeSpaceEntry )

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def newConfig(self):
		if self["config"].getCurrent() == self.EnableEntry:
			self.createSetup()

	def selectionChanged(self):
		current = self["config"].getCurrent()
		if current == self.EnableEntry:
			self["status"].setText(_("Decide if you want to enable or disable the Cleanup Wizard."))
		elif current == self.freeSpaceEntry:
			self["status"].setText(_("Set available internal memory threshold for the warning."))

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


def CleanupWizard(*args, **kwargs):
	from CleanupWizard import CleanupWizard
	return CleanupWizard(*args, **kwargs)

def openconfig(session, **kwargs):
	session.open(CleanupWizardConfiguration)

def selSetup(menuid, **kwargs):
	if menuid != "system":
		return [ ]

	return [(_("Cleanup Wizard settings"), openconfig, "cleanup_config", 71)]

def Plugins(**kwargs):
	list = []
	list.append(PluginDescriptor(name=_("CleanupWizard"), description=_("Cleanup Wizard settings"),where=PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=selSetup))
	if config.plugins.cleanupwizard.enable.value:
		if not config.misc.firstrun.value:
			if internalMemoryExceeded:
				list.append(PluginDescriptor(name=_("Cleanup Wizard"), where = PluginDescriptor.WHERE_WIZARD, needsRestart = False, fnc=(1, CleanupWizard)))
	return list

