from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.MenuList import MenuList
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ProgressBar import ProgressBar
from Components.Pixmap import Pixmap
from Components.ServiceList import refreshServiceList

from enigma import eCableScan, eDVBFrontendParametersCable, eTimer

class CableScan:
	def __init__(self, text, progressbar, scanTuner, scanNetwork, scanFrequency, scanSymbolRate, scanModulation, keepNumbers, hdList):
		self.text = text;
		self.progressbar = progressbar;
		self.scanTuner = scanTuner
		self.scanNetwork = scanNetwork
		self.scanFrequency = scanFrequency
		self.scanSymbolRate = scanSymbolRate
		self.scanModulation = scanModulation
		self.keepNumbers = keepNumbers
		self.hdList = hdList
		self.done = False

	def execBegin(self):
		self.text.setText(_('Scanning...'))
		self.progressbar.setValue(0)
		self.scan = eCableScan(self.scanNetwork, self.scanFrequency, self.scanSymbolRate, self.scanModulation, self.keepNumbers, self.hdList)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		self.scan.scanProgress.get().append(self.scanProgress)
		self.scan.start(self.scanTuner)

	def execEnd(self):
		self.scan.scanCompleted.get().remove(self.scanCompleted)
		self.scan.scanProgress.get().remove(self.scanProgress)
		del self.scan

	def scanProgress(self, progress):
		self.progressbar.setValue(progress)

	def scanCompleted(self, result):
		self.done = True
		if result < 0:
			self.text.setText(_('Scanning failed!'))
		else:
			self.text.setText(ngettext("Scanning completed, %d channel found", "Scanning completed, %d channels found", result) % result)

	def destroy(self):
		pass

	def isDone(self):
		return self.done

class CableScanStatus(Screen):
	skin = """
	<screen position="150,115" size="420,180" title="Cable Scan">
		<widget name="frontend" pixmap="skin_default/icons/scan-c.png" position="5,5" size="64,64" transparent="1" alphatest="on" />
		<widget name="scan_state" position="10,120" zPosition="2" size="400,30" font="Regular;18" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="skin_default/progress_big.png" borderWidth="2" borderColor="#cccccc" />
	</screen>"""

	def __init__(self, session, scanTuner, scanNetwork, scanFrequency, scanSymbolRate, scanModulation, keepNumbers, hdList):
		Screen.__init__(self, session)
		self.scanTuner = scanTuner
		self.scanNetwork = scanNetwork
		self.scanFrequency = scanFrequency
		self.scanSymbolRate = scanSymbolRate
		self.scanModulation = scanModulation
		self.keepNumbers = keepNumbers
		self.hdList = hdList

		self["frontend"] = Pixmap()
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))

		self.prevservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.cancel
			})

		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["scan"] = CableScan(self["scan_state"], self["scan_progress"], self.scanTuner, self.scanNetwork, self.scanFrequency, self.scanSymbolRate, self.scanModulation, self.keepNumbers, self.hdList)

	def restoreService(self):
		if self.prevservice:
			self.session.nav.playService(self.prevservice)

	def ok(self):
		if self["scan"].isDone():
			self.restoreService()
			self.close()

	def cancel(self):
		self.restoreService()
		self.close()

config.plugins.CableScan = ConfigSubsection()
config.plugins.CableScan.keepnumbering = ConfigYesNo(default = False)
config.plugins.CableScan.hdlist = ConfigYesNo(default = False)
config.plugins.CableScan.frequency = ConfigInteger(default = 323, limits = (1, 999))
config.plugins.CableScan.symbolrate = ConfigInteger(default = 6875, limits = (1, 9999))
config.plugins.CableScan.networkid = ConfigInteger(default = 0, limits = (0, 99999))
config.plugins.CableScan.modulation = ConfigSelection(
	choices =
		[(str(eDVBFrontendParametersCable.Modulation_QAM16), "QAM16"),
		(str(eDVBFrontendParametersCable.Modulation_QAM32), "QAM32"),
		(str(eDVBFrontendParametersCable.Modulation_QAM64), "QAM64"),
		(str(eDVBFrontendParametersCable.Modulation_QAM128), "QAM128"),
		(str(eDVBFrontendParametersCable.Modulation_QAM256), "QAM256")],
	default = str(eDVBFrontendParametersCable.Modulation_QAM64))
config.plugins.CableScan.auto = ConfigYesNo(default = True)

class CableScanScreen(ConfigListScreen, Screen):
	skin = """
	<screen position="100,115" size="520,290" title="Cable Scan">
		<widget name="config" position="10,10" size="500,250" scrollbarMode="showOnDemand" />
		<widget name="introduction" position="10,265" size="500,25" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
			"save": self.keySave,
			"menu": self.closeRecursive,
		}, -2)

		nimlist = nimmanager.getNimListOfType("DVB-C")
		nim_list = []
		for x in nimlist:
			nim_list.append((nimmanager.nim_slots[x].slot, nimmanager.nim_slots[x].friendly_full_description))

		self.scan_nims = ConfigSelection(choices = nim_list)

		self.list = []
		self.list.append(getConfigListEntry(_("Tuner"), self.scan_nims))

		self.list.append(getConfigListEntry(_('Frequency'), config.plugins.CableScan.frequency))
		self.list.append(getConfigListEntry(_('Symbol rate'), config.plugins.CableScan.symbolrate))
		self.list.append(getConfigListEntry(_('Modulation'), config.plugins.CableScan.modulation))
		self.list.append(getConfigListEntry(_('Network ID'), config.plugins.CableScan.networkid))
		self.list.append(getConfigListEntry(_("Use official channel numbering"), config.plugins.CableScan.keepnumbering))
		self.list.append(getConfigListEntry(_("HD list"), config.plugins.CableScan.hdlist))
		self.list.append(getConfigListEntry(_("Enable auto cable scan"), config.plugins.CableScan.auto))

		ConfigListScreen.__init__(self, self.list)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.finished_cb = None

		self["introduction"] = Label(_("Configure your network settings, and press OK to start the scan"))

	def keySave(self):
		config.plugins.CableScan.save()
		self.close()

	def keyGo(self):
		config.plugins.CableScan.save()
		self.startScan()

	def startScan(self):
		self.session.open(CableScanStatus, scanTuner = int(self.scan_nims.value), scanNetwork = config.plugins.CableScan.networkid.value, scanFrequency = config.plugins.CableScan.frequency.value * 1000, scanSymbolRate = config.plugins.CableScan.symbolrate.value * 1000, scanModulation = int(config.plugins.CableScan.modulation.value), keepNumbers = config.plugins.CableScan.keepnumbering.value, hdList = config.plugins.CableScan.hdlist.value)

	def keyCancel(self):
		self.close()

class CableScanAutoScreen(CableScanScreen):

	def __init__(self, session, nimlist):
		print "[AutoCableScan] start"
		Screen.__init__(self, session)
		self.skinName="Standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		self.onClose.append(self.__onClose)

		self.scan = eCableScan(config.plugins.CableScan.networkid.value, config.plugins.CableScan.frequency.value * 1000, config.plugins.CableScan.symbolrate.value * 1000, int(config.plugins.CableScan.modulation.value), config.plugins.CableScan.keepnumbering.value, config.plugins.CableScan.hdlist.value)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		self.scan.start(int(nimlist[0]))

	def __onClose(self):
		if self.scan:
			self.scan.scanCompleted.get().remove(self.scanCompleted)
			del self.scan

	def scanCompleted(self, result):
		print "[AutoCableScan] completed result = ", result
		refreshServiceList()
		self.close(result>0)

	def Power(self):
		from Screens.Standby import inStandby
		inStandby.Power()
		print "[AutoCableScan] aborted due to power button pressed"
		self.close(True)

	def createSummary(self):
		from Screens.Standby import StandbySummary
		return StandbySummary

def CableScanMain(session, **kwargs):
	nims = nimmanager.getNimListOfType("DVB-C")

	nimList = []
	for x in nims:
		nimList.append(x)

	if len(nimList) == 0:
		session.open(MessageBox, _("No cable tuner found!"), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to scan."), MessageBox.TYPE_ERROR)
		else:
			session.open(CableScanScreen)
Session = None
CableScanAutoStartTimer = eTimer()

def restartScanAutoStartTimer(reply=False):
	if not reply:
		print "[AutoCableScan] Scan was not succesfully retry in one hour"
		CableScanAutoStartTimer.startLongTimer(3600)
	else:
		CableScanAutoStartTimer.startLongTimer(86400)

def CableScanAuto():
	nimlist = nimmanager.getNimListOfType("DVB-C")
	if nimlist:
		if Session.nav.RecordTimer.isRecording():
			restartScanAutoStartTimer()
		else:
			Session.openWithCallback(restartScanAutoStartTimer, CableScanAutoScreen, nimlist)

CableScanAutoStartTimer.callback.append(CableScanAuto)

def leaveStandby():
	CableScanAutoStartTimer.stop()

def standbyCountChanged(value):
	if config.plugins.CableScan.auto.value:
		from Screens.Standby import inStandby
		inStandby.onClose.append(leaveStandby)
		CableScanAutoStartTimer.startLongTimer(150)

def startSession(session, **kwargs):
	global Session
	Session = session
	config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call=False)

def CableScanStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Cable Scan"), CableScanMain, "cablescan", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-C")):
		return [PluginDescriptor(name=_("Cable Scan"), description="Scan cable provider channels", where = PluginDescriptor.WHERE_MENU, fnc=CableScanStart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=startSession)]
	else:
		return []
