# -*- coding: utf-8 -*-
from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config, ConfigSelection, ConfigYesNo, getConfigListEntry, ConfigSubsection, ConfigText
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ServiceList import refreshServiceList
from Components.ActionMap import ActionMap

from enigma import eFastScan, eDVBFrontendParametersSatellite, eTimer

import os

config.misc.fastscan = ConfigSubsection()
config.misc.fastscan.last_configuration = ConfigText(default="()")
config.misc.fastscan.auto = ConfigSelection(default="true", choices=[("true", _("yes")), ("false", _("no")), ("multi", _("multi"))])
config.misc.fastscan.autoproviders = ConfigText(default="()")

class FastScanStatus(Screen):
	skin = """
	<screen position="150,115" size="420,180" title="Fast Scan">
		<widget name="frontend" pixmap="icons/scan-s.png" position="5,5" size="64,64" transparent="1" alphatest="on" />
		<widget name="scan_state" position="10,120" zPosition="2" size="400,30" font="Regular;18" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="progress_big.png" borderWidth="2" borderColor="#cccccc" />
	</screen>"""

	def __init__(self, session, scanTuner=0, transponderParameters=None, scanPid=900, keepNumbers=False, keepSettings=False, providerName='Favorites', createRadioBouquet=False):
		Screen.__init__(self, session)
		self.setTitle(_("Fast Scan"))
		self.scanPid = scanPid
		self.scanTuner = scanTuner
		self.transponderParameters = transponderParameters
		self.keepNumbers = keepNumbers
		self.keepSettings = keepSettings
		self.providerName = providerName
		self.createRadioBouquet = createRadioBouquet
		self.isDone = False

		self.onClose.append(self.__onClose)

		self["frontend"] = Pixmap()
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))

		if hasattr(self.session, "pipshown") and self.session.pipshown:
			from Screens.InfoBar import InfoBar
			InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()

		self.prevservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.cancel
			})

		self.onFirstExecBegin.append(self.doServiceScan)

	def __onClose(self):
		self.scan.scanCompleted.get().remove(self.scanCompleted)
		self.scan.scanProgress.get().remove(self.scanProgress)
		del self.scan

	def doServiceScan(self):
		self["scan_state"].setText(_('Scanning %s...') % (self.providerName))
		self["scan_progress"].setValue(0)
		self.scan = eFastScan(self.scanPid, self.providerName, self.transponderParameters, self.keepNumbers, self.keepSettings, self.createRadioBouquet)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		self.scan.scanProgress.get().append(self.scanProgress)
		fstfile = None
		fntfile = None
		for root, dirs, files in os.walk('/tmp/'):
			for f in files:
				if f.endswith('.bin'):
					if '_FST' in f:
						fstfile = os.path.join(root, f)
					elif '_FNT' in f:
						fntfile = os.path.join(root, f)
		if fstfile and fntfile:
			self.scan.startFile(fntfile, fstfile)
			os.unlink(fstfile)
			os.unlink(fntfile)
		else:
			self.scan.start(self.scanTuner)

	def scanProgress(self, progress):
		self["scan_progress"].setValue(progress)

	def scanCompleted(self, result):
		self.isDone = True
		if result < 0:
			self["scan_state"].setText(_('Scanning failed!'))
		else:
			self["scan_state"].setText(ngettext('List version %d, found %d channel', 'List version %d, found %d channels', result) % (self.scan.getVersion(), result))

	def restoreService(self):
		if self.prevservice:
			self.session.nav.playService(self.prevservice)

	def ok(self):
		if self.isDone:
			self.cancel()

	def cancel(self):
		if self.isDone:
			refreshServiceList()
		self.restoreService()
		self.close()

class FastScanScreen(ConfigListScreen, Screen):
	skin = """
	<screen position="100,115" size="520,290" title="Fast Scan">
		<widget name="config" position="10,10" size="500,250" scrollbarMode="showOnDemand" />
		<widget name="introduction" position="10,265" size="500,25" font="Regular;20" halign="center" />
	</screen>"""

	providers = [
		('Canal Digitaal', (1, 900, True)),
		('TV Vlaanderen', (1, 910, True)),
		('TéléSAT', (0, 920, True)),
		('HD Austria', (0, 950, False)),
		('Diveo', (0, 960, False)),
		('Skylink Czech Republic', (1, 30, False)),
		('Skylink Slovak Republic', (1, 31, False)),
		('KabelKiosk', (0, 970, False)),
		('TéléSAT Astra3', (1, 920, True)),
		('HD Austria Astra3', (1, 950, False)),
		('Diveo Astra3', (1, 960, False)),
		('Canal Digitaal Astra 1', (0, 900, True)),
		('TV Vlaanderen  Astra 1', (0, 910, True))]

	transponders = ((12515000, 22000000, eDVBFrontendParametersSatellite.FEC_5_6, 192,
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
		eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off),
		(12070000, 27500000, eDVBFrontendParametersSatellite.FEC_3_4, 235,
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
		eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off))

	def __init__(self, session, nimList):
		Screen.__init__(self, session)

		self.setTitle(_("Fast Scan"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		providerList = list(x[0] for x in self.providers)

		lastConfiguration = eval(config.misc.fastscan.last_configuration.value)
		if not lastConfiguration or not tuple(x for x in self.providers if x[0] == lastConfiguration[1]):
			lastConfiguration = (nimList[0][0], providerList[0], True, True, False, False)

		self.scan_nims = ConfigSelection(default = lastConfiguration[0], choices = nimList)
		self.scan_provider = ConfigSelection(default = lastConfiguration[1], choices = providerList)
		self.scan_hd = ConfigYesNo(default = lastConfiguration[2])
		self.scan_keepnumbering = ConfigYesNo(default = lastConfiguration[3])
		self.scan_keepsettings = ConfigYesNo(default = lastConfiguration[4])
		self.scan_create_radio_bouquet = ConfigYesNo(default = len(lastConfiguration) > 5 and lastConfiguration[5])
		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.scanProvider = getConfigListEntry(_("Provider"), self.scan_provider)
		self.scanHD = getConfigListEntry(_("HD list"), self.scan_hd)
		self.config_autoproviders = {}
		auto_providers = config.misc.fastscan.autoproviders.value.split(",")
		for provider in self.providers:
			self.config_autoproviders[provider[0]] = ConfigYesNo(default=provider[0] in auto_providers )
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
		self.finished_cb = None
		self["introduction"] = Label(_("Select your provider, and press OK to start the scan"))

	def createSetup(self):
		self.list = []
		self.list.append(self.tunerEntry)
		self.list.append(self.scanProvider)
		self.list.append(self.scanHD)
		self.list.append(getConfigListEntry(_("Use fastscan channel numbering"), self.scan_keepnumbering))
		self.list.append(getConfigListEntry(_("Use fastscan channel names"), self.scan_keepsettings))
		self.list.append(getConfigListEntry(_("Create seperate radio userbouquet"), self.scan_create_radio_bouquet))
		self.list.append(getConfigListEntry(_("Enable auto fast scan"), config.misc.fastscan.auto))
		if config.misc.fastscan.auto.value == "multi":
			for provider in self.providers:
				self.list.append(getConfigListEntry(_("Enable auto fast scan for %s") % provider[0], self.config_autoproviders[provider[0]]))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def saveConfiguration(self):
		config.misc.fastscan.last_configuration.value = `(self.scan_nims.value, self.scan_provider.value, self.scan_hd.value, self.scan_keepnumbering.value, self.scan_keepsettings.value, self.scan_create_radio_bouquet.value)`
		auto_providers = []
		for provider in self.providers:
			if self.config_autoproviders[provider[0]].value:
				auto_providers.append(provider[0])
		config.misc.fastscan.autoproviders.value = ",".join(auto_providers)
		config.misc.fastscan.save()

	def keySave(self):
		self.saveConfiguration()
		self.close()

	def keyGo(self):
		self.saveConfiguration()
		self.startScan()

	def getTransponderParameters(self, number):
		transponderParameters = eDVBFrontendParametersSatellite()
		transponderParameters.frequency = self.transponders[number][0]
		transponderParameters.symbol_rate = self.transponders[number][1]
		transponderParameters.fec = self.transponders[number][2]
		transponderParameters.orbital_position = self.transponders[number][3]
		transponderParameters.polarisation = self.transponders[number][4]
		transponderParameters.inversion = self.transponders[number][5]
		transponderParameters.system = self.transponders[number][6]
		transponderParameters.modulation = self.transponders[number][7]
		transponderParameters.rolloff = self.transponders[number][8]
		transponderParameters.pilot = self.transponders[number][9]
		transponderParameters.is_id = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
		transponderParameters.pls_mode = eDVBFrontendParametersSatellite.PLS_Gold
		transponderParameters.pls_code = 0
		transponderParameters.t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
		return transponderParameters

	def startScan(self):
		parameters = tuple(x[1] for x in self.providers if x[0] == self.scan_provider.value)[0]
		pid = parameters[1]
		if self.scan_hd.value and parameters[2]:
			pid += 1
		if self.scan_nims.value:
			self.session.open(FastScanStatus, scanTuner = int(self.scan_nims.value),
				transponderParameters = self.getTransponderParameters(parameters[0]),
				scanPid = pid, keepNumbers = self.scan_keepnumbering.value, keepSettings = self.scan_keepsettings.value, createRadioBouquet = self.scan_create_radio_bouquet.value,
				providerName = self.scan_provider.getText())

	def keyCancel(self):
		self.close()

class FastScanAutoScreen(FastScanScreen):

	def __init__(self, session, lastConfiguration):
		print "[AutoFastScan] start %s" % lastConfiguration[1]
		Screen.__init__(self, session)
		self.skinName="Standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		self.onClose.append(self.__onClose)

		parameters = tuple(x[1] for x in self.providers if x[0] == lastConfiguration[1])
		if parameters:
			parameters = parameters[0]
			pid = parameters[1]
			if lastConfiguration[2] and parameters[2]:
				pid += 1
			self.scan = eFastScan(pid, lastConfiguration[1], self.getTransponderParameters(parameters[0]), lastConfiguration[3], lastConfiguration[4], len(lastConfiguration) > 5 and lastConfiguration[5])
			self.scan.scanCompleted.get().append(self.scanCompleted)
			self.scan.start(int(lastConfiguration[0]))
		else:
			self.scan = None
			self.close(True)

	def __onClose(self):
		if self.scan:
			self.scan.scanCompleted.get().remove(self.scanCompleted)
			del self.scan

	def scanCompleted(self, result):
		print "[AutoFastScan] completed result = ", result
		refreshServiceList()
		self.close(result)

	def Power(self):
		from Screens.Standby import inStandby
		inStandby.Power()
		print "[AutoFastScan] aborted due to power button pressed"
		self.close(True)

	def createSummary(self):
		from Screens.Standby import StandbySummary
		return StandbySummary

def FastScanMain(session, **kwargs):
	if session.nav.RecordTimer.isRecording():
		session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to scan."), MessageBox.TYPE_ERROR)
	else:
		nimList = []
		# collect all nims which are *not* set to "nothing"
		for n in nimmanager.nim_slots:
			if not n.isCompatible("DVB-S"):
				continue
			if n.config.dvbs.configMode == "nothing":
				continue
			if n.config.dvbs.configMode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.dvbs.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			nimList.append((str(n.slot), n.friendly_full_description))
		if nimList:
			session.open(FastScanScreen, nimList)
		else:
			session.open(MessageBox, _("No suitable sat tuner found!"), MessageBox.TYPE_ERROR)

Session = None
FastScanAutoStartTimer = eTimer()
autoproviders = []

def restartScanAutoStartTimer(reply=False):
	if not reply:
		print "[AutoFastScan] Scan was not succesfully retry in one hour"
		FastScanAutoStartTimer.startLongTimer(3600)
	elif reply is not True:
		global autoproviders
		if autoproviders:
			provider = autoproviders.pop(0)
			if provider:
				lastConfiguration = eval(config.misc.fastscan.last_configuration.value)
				lastConfiguration = (lastConfiguration[0], provider, lastConfiguration[2], lastConfiguration[3], lastConfiguration[4], len(lastConfiguration) > 5 and lastConfiguration[5])
				Session.openWithCallback(restartScanAutoStartTimer, FastScanAutoScreen, lastConfiguration)
				return
		FastScanAutoStartTimer.startLongTimer(86400)

def FastScanAuto():
	lastConfiguration = eval(config.misc.fastscan.last_configuration.value)
	if not lastConfiguration or Session.nav.RecordTimer.isRecording():
		restartScanAutoStartTimer()
	else:
		if config.misc.fastscan.auto.value == "multi":
			global autoproviders
			autoproviders = config.misc.fastscan.autoproviders.value.split(",")
			if autoproviders:
				provider = autoproviders.pop(0)
				if provider:
					lastConfiguration = (lastConfiguration[0], provider, lastConfiguration[2], lastConfiguration[3], lastConfiguration[4], len(lastConfiguration) > 5 and lastConfiguration[5])
		Session.openWithCallback(restartScanAutoStartTimer, FastScanAutoScreen, lastConfiguration)

FastScanAutoStartTimer.callback.append(FastScanAuto)

def leaveStandby():
	FastScanAutoStartTimer.stop()

def standbyCountChanged(value):
	if config.misc.fastscan.auto.value != "false" and config.misc.fastscan.last_configuration.value:
		from Screens.Standby import inStandby
		inStandby.onClose.append(leaveStandby)
		FastScanAutoStartTimer.startLongTimer(90)

def autostart(reason, **kwargs):
	global Session
	if reason == 0 and "session" in kwargs and not Session:
		Session = kwargs["session"]
		config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call=False)
	elif reason == 1 and Session:
		Session = None
		config.misc.standbyCounter.removeNotifier(standbyCountChanged)

def FastScanStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Fast Scan"), FastScanMain, "fastscan", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return [PluginDescriptor(name=_("Fast Scan"), description="Scan M7 Brands, BE/NL/DE/AT/CZ", where = PluginDescriptor.WHERE_MENU, fnc=FastScanStart),
			PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc=autostart)]
	else:
		return []
