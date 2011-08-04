# -*- coding: utf-8 -*-
from os import path as os_path, walk as os_walk, unlink as os_unlink

from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config, ConfigSelection, ConfigYesNo, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager

from enigma import eFastScan

class FastScan:
	def __init__(self, text, progressbar, scanTuner = 0, scanPid = 900, keepNumbers = False, keepSettings = False, providerName = 'Favorites'):
		self.text = text;
		self.progressbar = progressbar;
		self.scanPid = scanPid
		self.scanTuner = scanTuner
		self.keepNumbers = keepNumbers
		self.keepSettings = keepSettings
		self.providerName = providerName
		self.done = False

	def execBegin(self):
		self.text.setText(_('Scanning %s...') % (self.providerName))
		self.progressbar.setValue(0)
		self.scan = eFastScan(self.scanPid, self.providerName, self.keepNumbers, self.keepSettings)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		self.scan.scanProgress.get().append(self.scanProgress)
		fstfile = None
		fntfile = None
		for root, dirs, files in os_walk('/tmp/'):
			for f in files:
				if f.endswith('.bin'):
					if '_FST' in f:
						fstfile = os_path.join(root, f)
					elif '_FNT' in f:
						fntfile = os_path.join(root, f)
		if fstfile and fntfile:
			self.scan.startFile(fntfile, fstfile)
			os_unlink(fstfile)
			os_unlink(fntfile)
		else:
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
			self.text.setText(_('List version %d, found %d channels') % (self.scan.getVersion(), result))

	def destroy(self):
		pass

	def isDone(self):
		return self.done

class FastScanStatus(Screen):
	skin = """
	<screen position="150,115" size="420,180" title="Fast Scan">
		<widget name="frontend" pixmap="skin_default/icons/scan-s.png" position="5,5" size="64,64" transparent="1" alphatest="on" />
		<widget name="scan_state" position="10,120" zPosition="2" size="400,30" font="Regular;18" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="skin_default/progress_big.png" borderWidth="2" borderColor="#cccccc" />
	</screen>"""

	def __init__(self, session, scanTuner = 0, scanPid = 900, keepNumbers = False, keepSettings = False, providerName = 'Favorites'):
		Screen.__init__(self, session)
		self.scanPid = scanPid
		self.scanTuner = scanTuner
		self.keepNumbers = keepNumbers
		self.keepSettings = keepSettings
		self.providerName = providerName

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
		self["scan"] = FastScan(self["scan_state"], self["scan_progress"], self.scanTuner, self.scanPid, self.keepNumbers, self.keepSettings, self.providerName)

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

class FastScanScreen(ConfigListScreen, Screen):
	skin = """
	<screen position="100,115" size="520,290" title="Fast Scan">
		<widget name="config" position="10,10" size="500,250" scrollbarMode="showOnDemand" />
		<widget name="introduction" position="10,265" size="500,25" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		nim_list = []
		# collect all nims which are *not* set to "nothing"
		for n in nimmanager.nim_slots:
			if not n.isCompatible("DVB-S"):
				continue
			if n.config_mode == "nothing":
				continue
			if n.config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			nim_list.append((str(n.slot), n.friendly_full_description))

		self.scan_nims = ConfigSelection(choices = nim_list)
		provider_list = []
		provider_list.append((str(900), 'Canal Digitaal'))
		provider_list.append((str(910), 'TV Vlaanderen'))
		provider_list.append((str(920), 'TéléSAT'))
		provider_list.append((str(930), 'Mobistar NL'))
		provider_list.append((str(940), 'Mobistar FR'))
		provider_list.append((str(950), 'AustriaSat'))
		provider_list.append((str(30),  'Czech Republic'))
		provider_list.append((str(31),  'Slovak Republic'))

		self.scan_provider = ConfigSelection(choices = provider_list)
		self.scan_hd = ConfigYesNo(default = False)
		self.scan_keepnumbering = ConfigYesNo(default = False)
		self.scan_keepsettings = ConfigYesNo(default = False)

		self.list = []
		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.list.append(self.tunerEntry)

		self.scanProvider = getConfigListEntry(_("Provider"), self.scan_provider)
		self.list.append(self.scanProvider)

		self.scanHD = getConfigListEntry(_("HD list"), self.scan_hd)
		self.list.append(self.scanHD)

		self.list.append(getConfigListEntry(_("Use fastscan channel numbering"), self.scan_keepnumbering))

		self.list.append(getConfigListEntry(_("Use fastscan channel names"), self.scan_keepsettings))

		ConfigListScreen.__init__(self, self.list)
		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.finished_cb = None

		ConfigListScreen.__init__(self, self.list)

		self["introduction"] = Label(_("Select your provider, and press OK to start the scan"))

	def keyGo(self):
		self.startScan()

	def startScan(self):
		pid = int(self.scan_provider.value)
		if self.scan_hd.value and pid >=900 and pid < 930:
			pid += 1
		if self.scan_nims.value:
			self.session.open(FastScanStatus, scanTuner = int(self.scan_nims.value), scanPid = pid, keepNumbers = self.scan_keepnumbering.value, keepSettings = self.scan_keepsettings.value, providerName = self.scan_provider.getText())

	def keyCancel(self):
		self.close()

def FastScanMain(session, **kwargs):
	nims = nimmanager.getNimListOfType("DVB-S")

	nimList = []
	for x in nims:
		nimList.append(x)

	if len(nimList) == 0:
		session.open(MessageBox, _("No sat tuner found!"), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to scan."), MessageBox.TYPE_ERROR)
		else:
			session.open(FastScanScreen)

def FastScanStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Fast Scan"), FastScanMain, "fastscan", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Fast Scan"), description="Scan Dutch/Belgian sat provider", where = PluginDescriptor.WHERE_MENU, fnc=FastScanStart)
	else:
		return []
