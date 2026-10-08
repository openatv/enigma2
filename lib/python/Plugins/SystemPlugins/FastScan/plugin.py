# -*- coding: utf-8 -*-
from os import unlink, walk
from os.path import join

from enigma import eDVBFrontendParametersSatellite, eFastScan, eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigInteger, ConfigSelection, ConfigYesNo, ConfigSubsection, ConfigText, config
from Components.Label import Label
from Components.NimManager import nimManager
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ServiceList import refreshServiceList
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.Setup import Setup

config.plugins.FastScan = ConfigSubsection()
config.plugins.FastScan.tuner = ConfigText(default="")
config.plugins.FastScan.provider = ConfigInteger(default=0)
config.plugins.FastScan.hd = ConfigYesNo(default=True)
config.plugins.FastScan.keepNumbering = ConfigYesNo(default=True)
config.plugins.FastScan.keepSettings = ConfigYesNo(default=False)
config.plugins.FastScan.createRadioBouquet = ConfigYesNo(default=False)
config.plugins.FastScan.auto = ConfigSelection(default="true", choices=[("true", _("Yes")), ("false", _("No")), ("multi", _("Multi"))])
config.plugins.FastScan.autoProviders = ConfigText(default="")
config.plugins.FastScan.drop = ConfigYesNo(default=True)

config.misc.fastscan = ConfigSubsection()  # Old settings, only used for the conversion below.
config.misc.fastscan.last_configuration = ConfigText(default="()")
config.misc.fastscan.auto = ConfigSelection(default="true", choices=["true", "false", "multi"])
config.misc.fastscan.autoproviders = ConfigText(default="()")


class FastScanHelper:
	PROVIDERS = {  # PID: (Name, Transponder index, Has HD list). The PID is also used as provider number.
		900: ("Canal Digitaal", 1, True),
		910: ("TV Vlaanderen", 1, True),
		920: ("TéléSAT", 0, True),
		950: ("HD Austria", 0, False),
		960: ("Diveo", 0, False),
		970: ("KabelKiosk", 0, False),
		30: ("Skylink Czech Republic", 1, False),
		31: ("Skylink Slovak Republic", 1, False),
		82: ("FreeSAT Czech Republic", 2, False),
		83: ("FreeSAT Slovak Republic", 2, False),
		84: ("FocusSAT Thor", 2, False),
		81: ("UPC Direct Thor", 2, False)
	}

	TRANSPONDERS = ((
			12515000, 22000000, eDVBFrontendParametersSatellite.FEC_5_6, 192,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
			eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off
		), (
			12070000, 27500000, eDVBFrontendParametersSatellite.FEC_3_4, 235,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.Inversion_Unknown,
			eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off
		), (
			11727000, 28000000, eDVBFrontendParametersSatellite.FEC_7_8, 3592,
			eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.Inversion_Unknown,
			eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_QPSK,
			eDVBFrontendParametersSatellite.RollOff_alpha_0_35, eDVBFrontendParametersSatellite.Pilot_Off
		)
	)

	@classmethod
	def getProviderName(cls, provider):
		return cls.PROVIDERS[provider][0] if provider in cls.PROVIDERS else ""

	@classmethod
	def getProviderNimList(cls, provider):
		orbitalPosition = cls.TRANSPONDERS[cls.PROVIDERS[provider][1]][3] if provider in cls.PROVIDERS else None
		return [x for x in nimManager.getNimListForSat(orbitalPosition) if nimManager.nim_slots[x].isCompatible("DVB-S")] if orbitalPosition is not None else []

	@classmethod
	def getProviderList(cls):
		return [x for x in cls.PROVIDERS if cls.getProviderNimList(x)]

	@classmethod
	def getProviderTuner(cls, provider, tuner):
		nimList = [str(x) for x in cls.getProviderNimList(provider)]
		return tuner if tuner in nimList else (nimList[0] if nimList else None)

	@staticmethod
	def getAutoProviders():
		return [int(x) for x in config.plugins.FastScan.autoProviders.value.split(",") if x.isdigit()]

	@classmethod
	def hasHDList(cls, provider):
		return provider in cls.PROVIDERS and cls.PROVIDERS[provider][2]

	@classmethod
	def createScan(cls, provider):
		providerName, transponder, hasHDList = cls.PROVIDERS[provider]
		pid = provider + 1 if hasHDList and config.plugins.FastScan.hd.value else provider
		transponder = cls.TRANSPONDERS[transponder]
		transponderParameters = eDVBFrontendParametersSatellite()
		transponderParameters.frequency = transponder[0]
		transponderParameters.symbol_rate = transponder[1]
		transponderParameters.fec = transponder[2]
		transponderParameters.orbital_position = transponder[3]
		transponderParameters.polarisation = transponder[4]
		transponderParameters.inversion = transponder[5]
		transponderParameters.system = transponder[6]
		transponderParameters.modulation = transponder[7]
		transponderParameters.rolloff = transponder[8]
		transponderParameters.pilot = transponder[9]
		transponderParameters.is_id = eDVBFrontendParametersSatellite.No_Stream_Id_Filter
		transponderParameters.pls_mode = eDVBFrontendParametersSatellite.PLS_Gold
		transponderParameters.pls_code = eDVBFrontendParametersSatellite.PLS_Default_Gold_Code
		transponderParameters.t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
		return eFastScan(pid, providerName, transponderParameters, config.plugins.FastScan.keepNumbering.value, config.plugins.FastScan.keepSettings.value, config.plugins.FastScan.createRadioBouquet.value, config.plugins.FastScan.drop.value)


oldSettings = (config.misc.fastscan.last_configuration, config.misc.fastscan.auto, config.misc.fastscan.autoproviders)
if any(x.value != x.default for x in oldSettings):  # Convert the old settings once.
	providerNumbers = {x[1][0]: x[0] for x in FastScanHelper.PROVIDERS.items()}  # Provider name to provider number.
	lastConfiguration = [x.strip().strip("'\"") for x in config.misc.fastscan.last_configuration.value.strip("()").split(",")]
	if len(lastConfiguration) > 4:
		config.plugins.FastScan.tuner.value = "" if lastConfiguration[0] == "None" else lastConfiguration[0]
		config.plugins.FastScan.provider.value = providerNumbers.get(lastConfiguration[1], 0)
		config.plugins.FastScan.hd.value = lastConfiguration[2] == "True"
		config.plugins.FastScan.keepNumbering.value = lastConfiguration[3] == "True"
		config.plugins.FastScan.keepSettings.value = lastConfiguration[4] == "True"
		config.plugins.FastScan.createRadioBouquet.value = len(lastConfiguration) > 5 and lastConfiguration[5] == "True"
	config.plugins.FastScan.auto.value = config.misc.fastscan.auto.value
	config.plugins.FastScan.autoProviders.value = ",".join(str(providerNumbers[x]) for x in config.misc.fastscan.autoproviders.value.split(",") if x in providerNumbers)
	config.plugins.FastScan.save()
	for configElement in oldSettings:  # Reset to default so the old settings are removed from the settings file.
		configElement.value = configElement.default
	config.misc.fastscan.save()


class FastScanSettings(Setup):
	def __init__(self, session):
		def providerChanged(configElement):
			if configElement.value:
				nimList = [(str(x), nimManager.nim_slots[x].friendly_full_description) for x in FastScanHelper.getProviderNimList(configElement.value)]
				self.scanNims.setChoices(nimList, default=FastScanHelper.getProviderTuner(configElement.value, config.plugins.FastScan.tuner.value))

		providerList = FastScanHelper.getProviderList()
		provider = config.plugins.FastScan.provider.value
		self.scanProvider = ConfigSelection(default=provider if provider in providerList else 0, choices=[(0, _("None"))] + [(x, FastScanHelper.getProviderName(x)) for x in providerList])
		self.scanNims = ConfigSelection(default=None, choices=[(None, _("None"))])
		self.scanProvider.addNotifier(providerChanged)
		autoProviders = FastScanHelper.getAutoProviders()
		self.configAutoProviders = {x: ConfigYesNo(default=x in autoProviders) for x in FastScanHelper.PROVIDERS}
		self["key_blue"] = StaticText()
		Setup.__init__(self, session=session, setup="FastScan", plugin="SystemPlugins/FastScan")
		self["colorActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyStartScan, _("Start the fast scan"))
		}, prio=0, description=_("Fast Scan Actions"))

	def createSetup(self):
		configList = []
		if self.scanProvider.value and config.plugins.FastScan.auto.value == "multi":
			for provider in FastScanHelper.getProviderList():
				configList.append((_("Enable auto fast scan for '%s'") % FastScanHelper.getProviderName(provider), self.configAutoProviders[provider]))
		Setup.createSetup(self, appendItems=configList)
		self["key_blue"].setText(_("Start") if self.scanProvider.value else "")

	def hasHDList(self):
		return FastScanHelper.hasHDList(self.scanProvider.value)

	def keyDefault(self):
		for configElement in [config.plugins.FastScan.hd, config.plugins.FastScan.keepNumbering, config.plugins.FastScan.keepSettings, config.plugins.FastScan.createRadioBouquet, config.plugins.FastScan.drop, config.plugins.FastScan.auto] + list(self.configAutoProviders.values()):
			configElement.value = configElement.default
		self.createSetup()
		for item in self["config"].getList():
			self["config"].invalidate(item)

	def keyStartScan(self):
		if self.scanProvider.value and self.scanNims.value:
			self.saveConfiguration()
			self.session.open(FastScanStatus, provider=self.scanProvider.value, tuner=int(self.scanNims.value))

	def keySave(self):
		self.saveConfiguration()
		Setup.keySave(self)

	def saveConfiguration(self):
		config.plugins.FastScan.provider.value = self.scanProvider.value
		config.plugins.FastScan.tuner.value = (self.scanNims.value or "") if self.scanProvider.value else ""
		config.plugins.FastScan.autoProviders.value = ",".join(str(x) for x in FastScanHelper.PROVIDERS if self.configAutoProviders[x].value)
		config.plugins.FastScan.save()


class FastScanStatus(Screen):
	skin = """
	<screen name="FastScanStatus" title="Fast Scan" position="150,115" size="420,180">
		<widget name="frontend" position="5,5" size="64,64" pixmap="icons/scan-s.png" alphaTest="on" transparent="1" />
		<widget name="scan_state" position="10,120" size="400,30" font="Regular;18" zPosition="2" />
		<widget name="scan_progress" position="10,155" size="400,15" pixmap="progress_big.png" borderColor="#00CCCCCC" borderWidth="2" />
	</screen>"""

	def __init__(self, session, provider, tuner):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Fast Scan"))
		self["frontend"] = Pixmap()
		self["scan_state"] = Label()
		self["scan_progress"] = ProgressBar()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.keyOk, _("Close the screen after the scan has finished")),
			"cancel": (self.keyCancel, _("Close the screen and stop a running scan"))
		}, prio=0, description=_("Fast Scan Actions"))
		if hasattr(self.session, "pipshown") and self.session.pipshown:
			from Screens.InfoBar import InfoBar
			InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
		self.previousService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()
		self.provider = provider
		self.tuner = tuner
		self.scan = None
		self.isDone = False
		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["scan_state"].setText(_("Scanning '%s'...") % FastScanHelper.getProviderName(self.provider))
		self["scan_progress"].setValue(0)
		self.scan = FastScanHelper.createScan(self.provider)
		self.scan.scanProgress.get().append(self.scanProgress)
		self.scan.scanCompleted.get().append(self.scanCompleted)
		fstFile = None
		fntFile = None
		for root, dirs, files in walk("/tmp/"):
			for file in files:
				if file.endswith(".bin"):
					if "_FST" in file:
						fstFile = join(root, file)
					elif "_FNT" in file:
						fntFile = join(root, file)
		if fstFile and fntFile:
			self.scan.startFile(fntFile, fstFile)
			unlink(fstFile)
			unlink(fntFile)
		else:
			self.scan.start(self.tuner)

	def scanProgress(self, progress):
		self["scan_progress"].setValue(progress)

	def scanCompleted(self, result):
		self.isDone = True
		if result < 0:
			self["scan_state"].setText(_("Error: Scan failed!"))
		else:
			self["scan_state"].setText(ngettext("Fast Scan version %d: Found %d channel.", "Fast Scan version %d: Found %d channels.", result) % (self.scan.getVersion(), result))

	def keyOk(self):
		if self.isDone:
			self.keyCancel()

	def keyCancel(self):
		if self.scan:
			self.scan.scanProgress.get().remove(self.scanProgress)
			self.scan.scanCompleted.get().remove(self.scanCompleted)
			self.scan = None
		if self.isDone:
			refreshServiceList()
		if self.previousService:
			self.session.nav.playService(self.previousService)
		self.close()


class FastScanAutoStart:
	instance = None

	def __init__(self, session):
		self.session = session
		self.providers = []
		self.failedProviders = []
		self.provider = 0
		self.scan = None
		self.timer = eTimer()
		self.timer.callback.append(self.startScan)
		self.nextTimer = eTimer()  # Delay the next scan so eFastScan is not deleted inside its own callback.
		self.nextTimer.callback.append(self.scanNextProvider)
		config.misc.standbyCounter.addNotifier(self.enterStandby, initial_call=False)

	def enterStandby(self, configElement):
		if config.plugins.FastScan.auto.value != "false" and config.plugins.FastScan.provider.value:
			from Screens.Standby import inStandby
			inStandby.onClose.insert(0, self.leaveStandby)  # Stop the scan before Standby restores the service.
			self.failedProviders = []
			self.timer.startLongTimer(90)

	def leaveStandby(self):
		self.timer.stop()
		self.nextTimer.stop()
		if self.scan:
			print("[FastScan] Auto fast scan aborted due to leaving standby.")
			self.stopScan()
		self.providers = []
		self.failedProviders = []

	def startScan(self):
		if self.session.nav.RecordTimer.isRecording():
			print("[FastScan] Recording in progress, retry the auto fast scan in one hour.")
			self.timer.startLongTimer(3600)
		else:
			if self.failedProviders:
				self.providers = self.failedProviders
			else:
				self.providers = FastScanHelper.getAutoProviders() if config.plugins.FastScan.auto.value == "multi" else []
				self.providers = self.providers or [config.plugins.FastScan.provider.value]
			self.failedProviders = []
			self.scanNextProvider()

	def scanNextProvider(self):
		if self.scan:
			self.stopScan()
		tuner = None
		while self.providers and tuner is None:
			self.provider = self.providers.pop(0)
			tuner = FastScanHelper.getProviderTuner(self.provider, config.plugins.FastScan.tuner.value)
		if tuner is not None:
			print(f"[FastScan] Start auto fast scan for '{FastScanHelper.getProviderName(self.provider)}'.")
			self.scan = FastScanHelper.createScan(self.provider)
			self.scan.scanCompleted.get().append(self.scanCompleted)
			self.scan.start(int(tuner))
		elif self.failedProviders:
			print("[FastScan] Auto fast scan was not successful for all providers, retry the failed providers in one hour.")
			self.timer.startLongTimer(3600)
		else:
			self.timer.startLongTimer(86400)

	def scanCompleted(self, result):
		print(f"[FastScan] Auto fast scan completed, result={result}.")
		if result > 0:
			refreshServiceList()
		else:
			self.failedProviders.append(self.provider)
		self.nextTimer.start(0, True)

	def stopScan(self):
		self.scan.scanCompleted.get().remove(self.scanCompleted)
		self.scan = None


def sessionStart(reason, session=None, **kwargs):
	if reason == 0 and session and FastScanAutoStart.instance is None:
		FastScanAutoStart.instance = FastScanAutoStart(session)


def menuStart(menuId, **kwargs):
	def main(session, **kwargs):
		if session.nav.RecordTimer.isRecording():
			session.showError(_("Error: A recording is currently in progress! Stop the recording or allow it to finish before trying to perform a scan."))
		else:
			session.open(FastScanSettings)

	return [(_("Fast Scan"), main, "fastscan", None)] if menuId == "scan" and FastScanHelper.getProviderList() else []


def Plugins(**kwargs):
	return [
		PluginDescriptor(name=_("Fast Scan"), description="Scan M7 Brands, BE/NL/DE/AT/CZ", where=PluginDescriptor.WHERE_MENU, fnc=menuStart),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionStart)
	] if nimManager.hasNimType("DVB-S") else []
