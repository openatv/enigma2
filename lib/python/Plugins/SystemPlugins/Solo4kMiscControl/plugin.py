from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists

config.plugins.solo4kMiscControl = ConfigSubsection()
config.plugins.solo4kMiscControl.forceLnbPower = ConfigSelection(default = "off", choices = [ ("on", _("Yes")), ("off", _("No"))] )
config.plugins.solo4kMiscControl.forceToneBurst = ConfigSelection(default = "disable", choices = [ ("enable", _("Yes")), ("disable", _("No"))] )
config.plugins.solo4kMiscControl.dvbCiDelay = ConfigSelection(default = "256", choices = [ ("16", _("16")), ("32", _("32")), ("64", _("64")), ("128", _("128")), ("256", _("256"))] )

PROC_FORCE_LNBPOWER = "/proc/stb/frontend/fbc/force_lnbon"
PROC_FORCE_TONEBURST = "/proc/stb/frontend/fbc/force_toneburst"
PROC_DVB_CI_DELAY = "/proc/stb/tsmux/rmx_delay"

def setProcValueOnOff(value, procPath):
	try:
		print "[Solo4kMiscControl] set %s : %s" % (procPath, value)
		fd = open(procPath,'w')
		fd.write(value)
		fd.close()
		return 0
	except Exception, e:
		print "[Solo4kMiscControl] proc write Error", e
		return -1


from enigma import eTimer
class checkDriverSupport:
	def __init__(self):
		self.onLayoutFinish.append(self.procCheck)
		self.dispErrorTimer = eTimer()
		self.dispErrorTimer.callback.append(self.dispErrorMsg)

	def procCheck(self):
		if not (fileExists(PROC_FORCE_LNBPOWER) and fileExists(PROC_FORCE_TONEBURST) and fileExists(PROC_DVB_CI_DELAY)):
			self.dispErrorTimer.start(0, True)

	def dispErrorMsg(self):
		self.session.openWithCallback(self.close ,MessageBox, _("Driver is not supported."), MessageBox.TYPE_ERROR)

class Solo4kMiscControl(Screen, ConfigListScreen, checkDriverSupport):
	skin = 	"""
		<screen position="center,center" size="400,250" title="Solo4K Misc. Control" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="30,10" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="230,10" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="30,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="230,10" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget name="config" zPosition="2" position="5,70" size="380,180" scrollbarMode="showOnDemand" transparent="1" />
		</screen>
		"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.session = session
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self.createSetup()

		checkDriverSupport.__init__(self)

	def createSetup(self):
		self.list = []
		self.lnbPowerEntry = getConfigListEntry(_("Force LNB Power"), config.plugins.solo4kMiscControl.forceLnbPower)
		self.toneBurstEntry = getConfigListEntry(_("Force ToneBurst"), config.plugins.solo4kMiscControl.forceToneBurst)
		self.ciDelayEntry = getConfigListEntry(_("DVB CI Delay"), config.plugins.solo4kMiscControl.dvbCiDelay)
		self.list.append( self.lnbPowerEntry )
		self.list.append( self.toneBurstEntry )
		self.list.append( self.ciDelayEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keySave(self):
		res = setProcValueOnOff(config.plugins.solo4kMiscControl.forceLnbPower.value, PROC_FORCE_LNBPOWER)
		if res == 0:
			res = setProcValueOnOff(config.plugins.solo4kMiscControl.forceToneBurst.value, PROC_FORCE_TONEBURST)
		if res == 0:
			res = setProcValueOnOff(config.plugins.solo4kMiscControl.dvbCiDelay.value, PROC_DVB_CI_DELAY)

		if res == -1:
			self.resetConfig()
			self.session.openWithCallback(self.close, MessageBox, _("SET FAILED!\n"), MessageBox.TYPE_ERROR)
		else:
			self.saveAll()
			self.close()

	def resetConfig(self):
		for x in self["config"].list:
			x[1].cancel()

def Solo4kMiscControlStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Solo4K Misc. Control"), Solo4kMiscControlMain, "Solo4kMiscControl", 75)]
	else:
		return []

def Solo4kMiscControlMain(session, **kwargs):
	session.open(Solo4kMiscControl)

def OnSessionStart(session, **kwargs):
	setProcValueOnOff(config.plugins.solo4kMiscControl.forceLnbPower.value, PROC_FORCE_LNBPOWER)
	setProcValueOnOff(config.plugins.solo4kMiscControl.forceToneBurst.value, PROC_FORCE_TONEBURST)
	setProcValueOnOff(config.plugins.solo4kMiscControl.dvbCiDelay.value, PROC_DVB_CI_DELAY)

def Plugins(**kwargs):
	pList = []
	pList.append( PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=OnSessionStart) )
	pList.append( PluginDescriptor(name=_("Solo4K Misc. Control"), description="Set Solo4K LNB power, etc.", where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=Solo4kMiscControlStart) )
	return pList
