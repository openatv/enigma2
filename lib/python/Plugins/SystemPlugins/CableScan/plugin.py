from enigma import eCableScan, eDVBFrontendParametersCable, eTimer

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigFloat
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ProgressBar import ProgressBar
from Components.Pixmap import Pixmap
from Components.ServiceList import refreshServiceList

class CableScan:
	def __init__(self, text, progressbar, scanTuner, scanNetwork, scanFrequency, scanSymbolRate, scanModulation, keepNumbers, hdList):
		self.text = text
		self.progressbar = progressbar
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
		<widget name="frontend" pixmap="icons/scan-c.png" position="5,5" size="64,64" transparent="1" alphatest="on" />
		<widget name="scan_state" position="10,120" zPosition="2" size="400,30" font="Regular;18" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="progress_big.png" borderWidth="2" borderColor="#cccccc" />
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

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.cancel
			})

		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["scan"] = CableScan(self["scan_state"], self["scan_progress"], self.scanTuner, self.scanNetwork, self.scanFrequency, self.scanSymbolRate, self.scanModulation, self.keepNumbers, self.hdList)

	def ok(self):
		if self["scan"].isDone():
			self.close()

	def cancel(self):
		self.close()

config.plugins.CableScan = ConfigSubsection()
config.plugins.CableScan.keepnumbering = ConfigYesNo(default = False)
config.plugins.CableScan.hdlist = ConfigYesNo(default = False)
config.plugins.CableScan.frequency = ConfigFloat(default = [323, 0], limits = [(50, 999),(0, 999)])
config.plugins.CableScan.symbolrate = ConfigInteger(default = 6875, limits = (1, 9999))
config.plugins.CableScan.networkid = ConfigInteger(default = 0, limits = (0, 99999))
config.plugins.CableScan.modulation = ConfigSelection(
	choices =
		[(str(eDVBFrontendParametersCable.Modulation_QAM16), "16-QAM"),
		(str(eDVBFrontendParametersCable.Modulation_QAM32), "32-QAM"),
		(str(eDVBFrontendParametersCable.Modulation_QAM64), "64-QAM"),
		(str(eDVBFrontendParametersCable.Modulation_QAM128), "128-QAM"),
		(str(eDVBFrontendParametersCable.Modulation_QAM256), "256-QAM")],
	default = str(eDVBFrontendParametersCable.Modulation_QAM64))
config.plugins.CableScan.auto = ConfigYesNo(default = True)

class CableScanScreen(ConfigListScreen, Screen):
	skin = """
	<screen position="100,115" size="520,290" title="Cable Scan">
		<widget name="config" position="10,10" size="500,250" scrollbarMode="showOnDemand" />
		<widget name="introduction" position="10,265" size="500,25" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session, nimlist):
		Screen.__init__(self, session)

		self.setTitle(_("Cable Scan"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
			"save": self.keySave,
			"menu": self.closeRecursive,
		}, -2)

		self.nimlist = nimlist
		self.prevservice = None

		self.list = []
		self.list.append(getConfigListEntry(_('Frequency'), config.plugins.CableScan.frequency))
		self.list.append(getConfigListEntry(_('Symbol rate'), config.plugins.CableScan.symbolrate))
		self.list.append(getConfigListEntry(_('Modulation'), config.plugins.CableScan.modulation))
		self.list.append(getConfigListEntry(_('Network ID') + _(' (0 - all networks)'), config.plugins.CableScan.networkid))
		self.list.append(getConfigListEntry(_("Use official channel numbering"), config.plugins.CableScan.keepnumbering))
		self.list.append(getConfigListEntry(_("HD list"), config.plugins.CableScan.hdlist))
		self.list.append(getConfigListEntry(_("Enable auto cable scan"), config.plugins.CableScan.auto))

		ConfigListScreen.__init__(self, self.list)
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self["introduction"] = Label(_("Configure your network settings, and press OK to start the scan"))

	def restoreService(self):
		if self.prevservice:
			self.session.nav.playService(self.prevservice)

	def keySave(self):
		self.restoreService()
		config.plugins.CableScan.save()
		self.close()

	def keyGo(self):
		config.plugins.CableScan.save()
		self.startScan()

	def getFreeTuner(self):
		dvbc_tuners_mask = sum([2**int(x) for x in self.nimlist])
		freeTunerMask = dvbc_tuners_mask - (self.session.screen["TunerInfo"].tuner_use_mask & dvbc_tuners_mask)
		if not freeTunerMask:
			service = self.session.nav.getCurrentService()
			if service:
				tunedTunerMask = 2**service.frontendInfo().getAll(True)["tuner_number"]
				recordingMask = sum([2**int(x) for x in [recording.frontendInfo().getAll(True)["tuner_number"] for recording in self.session.nav.getRecordings()]])
				if not(tunedTunerMask & recordingMask):
					self.prevservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
					self.session.nav.stopService()
					freeTunerMask = tunedTunerMask
		import math
		self.freeTuner = freeTunerMask and int(math.log(freeTunerMask, 2))
		return freeTunerMask > 0

	def startScan(self):
		if self.getFreeTuner():
			self.session.open(CableScanStatus, scanTuner=self.freeTuner, scanNetwork=config.plugins.CableScan.networkid.value, scanFrequency=config.plugins.CableScan.frequency.floatint, scanSymbolRate=config.plugins.CableScan.symbolrate.value * 1000, scanModulation=int(config.plugins.CableScan.modulation.value), keepNumbers=config.plugins.CableScan.keepnumbering.value, hdList=config.plugins.CableScan.hdlist.value)
		else:
			self.session.open(MessageBox, _("A recording is currently running on the selected tuner. Please select a different tuner or consider to stop the recording to try again."), type=MessageBox.TYPE_ERROR)

	def keyCancel(self):
		refreshServiceList()
		self.restoreService()
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].cancel()
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
		self.nimlist = nimlist

		self.scan = eCableScan(config.plugins.CableScan.networkid.value, config.plugins.CableScan.frequency.floatint, config.plugins.CableScan.symbolrate.value * 1000, int(config.plugins.CableScan.modulation.value), config.plugins.CableScan.keepnumbering.value, config.plugins.CableScan.hdlist.value)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		if self.getFreeTuner():
			self.scan.start(self.freeTuner)
		else:
			self.close(False)

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

Session = None
CableScanAutoStartTimer = eTimer()

def getNimList():
	return [x for x in nimmanager.getNimListOfType("DVB-C") if config.Nims[x].configMode.value != "nothing"]

def CableScanMain(session, **kwargs):
	nimlist = getNimList()
	if nimlist:
		Session.open(CableScanScreen, nimlist)
	else:
		Session.open(MessageBox, _("No cable tuner found!"), type=MessageBox.TYPE_ERROR)

def restartScanAutoStartTimer(reply=False):
	if reply:
		CableScanAutoStartTimer.startLongTimer(86400)
	else:
		print "[AutoCableScan] Scan was not succesfully retry in one hour"
		CableScanAutoStartTimer.startLongTimer(3600)

def CableScanAuto():
	nimlist = getNimList()
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
	if nimmanager.hasNimType("DVB-C"):
		return [PluginDescriptor(name=_("Cable Scan"), description="Scan cable provider channels", where = PluginDescriptor.WHERE_MENU, fnc=CableScanStart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=startSession)]
	else:
		return []
