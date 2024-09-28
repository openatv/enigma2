from enigma import eComponentScan, eServiceReference, eTimer, iDVBFrontend

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.MenuList import MenuList
from Components.NimManager import iDVBFrontendDict, nimmanager
from Components.ProgressBar import ProgressBar
from Components.Sources.FrontendInfo import FrontendInfo
from Components.Sources.StaticText import StaticText
try:
	from Plugins.SystemPlugins.LCNScanner.plugin import LCNScanner
except ImportError:
	LCNScanner = None
from Screens.InfoBar import InfoBar
from Screens.Processing import Processing
from Screens.Screen import Screen, ScreenSummary
from Tools.Directories import SCOPE_CONFIG, fileReadLines, resolveFilename
from Tools.Transponder import getChannelNumber

MODULE_NAME = __name__.split(".")[-1]


class ServiceScan(Screen):
	RUNNING = 0
	DONE = 1
	ERROR = 2
	ERRORS = {
		0: _("Problem starting scan"),
		1: _("Problem while scanning"),
		2: _("No resource manager"),
		3: _("No channel list")
	}

	def __init__(self, session, scanList):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Service Scan"))
		self.scanList = scanList
		if hasattr(session, "infobar"):
			self.currentInfobar = InfoBar.instance
			if self.currentInfobar:
				self.currentServiceList = self.currentInfobar.servicelist
				if self.session.pipshown and self.currentServiceList:
					if self.currentServiceList.dopipzap:
						self.currentServiceList.togglePipzap()
					if hasattr(self.session, "pip"):
						del self.session.pip
					self.session.pipshown = False
		else:
			self.currentInfobar = None
		# if hasattr(session, "infobar") and InfoBar.instance and InfoBar.instance.servicelist and self.session.pipshown:
		# 	if InfoBar.instance.servicelist.dopipzap:
		# 		InfoBar.instance.servicelist.togglePipzap()
		# 	if hasattr(self.session, "pip"):
		# 		del self.session.pip
		# 	self.session.pipshown = False
		self.currentServiceRef = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self.serviceList = []
		self["servicelist"] = MenuList(self.serviceList)
		self["servicelist"].selectionEnabled(False)
		self["scan_progress"] = ProgressBar()
		self["pass"] = Label()
		self["network"] = Label()
		self["transponder"] = Label()
		self["scan_state"] = Label()
		self["FrontendInfo"] = FrontendInfo()
		self["FrontendInfo"].frontend_source = lambda *args: None
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["actions"] = HelpableActionMap(self, ["CancelActions"], {
			"cancel": (self.keyCancel, _("Cancel the scan and and exit the scanner")),
			"close": (self.keyCloseRecursive, _("Cancel the scan and exit all menus")),
		}, prio=0, description=_("Service Scan Actions"))
		self["doneActions"] = HelpableActionMap(self, ["CancelActions", "OkSaveActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Select the previous service and close the scanner")),
			"close": (self.keyCloseRecursive, _("Select the previous service and close the scanner and exit all menus")),
			"ok": (self.keySave, _("Select the currently highlighted service and exit")),
			"save": (self.keySave, _("Select the currently highlighted service and exit")),
			"top": (self["servicelist"].goTop, _("Move to first line / screen")),
			"pageUp": (self["servicelist"].goPageUp, _("Move up a screen")),
			"up": (self["servicelist"].goLineUp, _("Move up a line")),
			"down": (self["servicelist"].goLineDown, _("Move down a line")),
			"pageDown": (self["servicelist"].goPageDown, _("Move down a screen")),
			"bottom": (self["servicelist"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Service Scan Actions"))
		self["doneActions"].setEnabled(False)
		self.lcnScanner = LCNScanner() if LCNScanner else None
		self.timer = eTimer()
		self.onProgressChanged = []
		self.onServiceChanged = []
		self.run = 0
		self.state = self.RUNNING
		self.currentSystem = None
		self.foundServices = 0
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["servicelist"].enableAutoNavigation(False)
		self.runScan()

	def runScan(self):
		if self.session.nav.RecordTimer.isRecording():
			self["pass"].setText(_("Recording in progress!"))
			self["scan_state"].setText(_("Scanning can't be performed while recordings are in progress."))
		else:
			self.scan = eComponentScan()
			self.scan.newService.get().append(self.newService)
			self.scan.statusChanged.get().append(self.statusChanged)
			for transponder in self.scanList[self.run]["transponders"]:
				self.scan.addInitial(transponder)
			frontendID = self.scanList[self.run]["feid"]
			networkID = self.scanList[self.run]["networkid"] if "networkid" in self.scanList[self.run] else 0
			if self.scan.start(frontendID, self.scanList[self.run]["flags"], networkID):
				print(f"[ServiceScan] Error: Service scan run {self.run + 1} of {len(self.scanList)} failed to start!")
				self.state = self.ERROR
				self.statusChanged()
			else:
				print(f"[ServiceScan] Starting service scan run {self.run + 1} of {len(self.scanList)}.")
			self["pass"].setText(f"{_("Pass")} {self.run + 1}/{len(self.scanList)}: {_("Tuner")} {chr(ord("A") + frontendID)}")

	def newService(self):
		self.foundServices += 1
		serviceName = self.scan.getLastServiceName()
		serviceRef = self.scan.getLastServiceRef()
		self.serviceList.append((serviceName, serviceRef))
		self["servicelist"].setList(self.serviceList)
		self["servicelist"].goBottom()
		print(f"[ServiceScan] Found service '{serviceName}' with service reference '{serviceRef}'.")
		for callback in self.onServiceChanged:
			callback(serviceName)

	def statusChanged(self):
		errorCode = 0
		if self.state == self.RUNNING:
			transponderType = ""
			transponderText = ""
			if self.scan.isDone():
				errorCode = self.scan.getError()
				self.state = self.ERROR if errorCode else self.DONE
			else:
				scanInfo = []
				transponder = self.scan.getCurrentTransponder()
				if transponder:
					mhz = _("MHz")
					mod = _("Modulation")
					fec = _("FEC")
					match transponder.getSystem():
						case iDVBFrontend.feATSC:
							transponderType = _("ATSC")
							data = transponder.getATSC()
							scanInfo.append({
								data.System_ATSC: _("ATSC"),
								data.System_DVB_C_ANNEX_B: _("DVB-C ANNEX B")
							}.get(data.system, ""))
							scanInfo.append({
								data.Modulation_Auto: f"{mod} {_("Auto")}",
								data.Modulation_QAM16: f"{mod} QAM16",
								data.Modulation_QAM32: f"{mod} QAM32",
								data.Modulation_QAM64: f"{mod} QAM64",
								data.Modulation_QAM128: f"{mod} QAM128",
								data.Modulation_QAM256: f"{mod} QAM256",
								data.Modulation_VSB_8: f"{mod} 8VSB",
								data.Modulation_VSB_16: f"{mod} 16VSB"
							}.get(data.modulation, ""))
							scanInfo.append(f"{data.frequency / 1000000.0:0.3f} {mhz}".replace(".000", ""))
							inv = _("Inversion")
							scanInfo.append({
								data.Inversion_Off: f"{inv} {_("Off")}",
								data.Inversion_On: f"{inv} {_("On")}",
								data.Inversion_Unknown: f"{inv} {_("Auto")}"
							}.get(data.inversion, ""))
						case iDVBFrontend.feCable:
							transponderType = _("Cable")
							data = transponder.getDVBC()
							scanInfo.append("DVB-C")
							scanInfo.append({
								data.Modulation_Auto: f"{mod} {_("Auto")}",
								data.Modulation_QAM16: f"{mod} QAM16",
								data.Modulation_QAM32: f"{mod} QAM32",
								data.Modulation_QAM64: f"{mod} QAM64",
								data.Modulation_QAM128: f"{mod} QAM128",
								data.Modulation_QAM256: f"{mod} QAM256"
							}.get(data.modulation, ""))
							scanInfo.append(data.frequency)
							scanInfo.append(data.symbol_rate // 1000)
							scanInfo.append({
								data.FEC_Auto: f"{fec} {_("Auto")}",
								data.FEC_1_2: f"{fec} 1/2",
								data.FEC_2_3: f"{fec} 2/3",
								data.FEC_3_4: f"{fec} 3/4",
								data.FEC_3_5: f"{fec} 3/5",
								data.FEC_4_5: f"{fec} 4/5",
								data.FEC_5_6: f"{fec} 5/6",
								data.FEC_6_7: f"{fec} 6/7",
								data.FEC_7_8: f"{fec} 7/8",
								data.FEC_8_9: f"{fec} 8/9",
								data.FEC_9_10: f"{fec} 9/10",
								data.FEC_None: f"{fec} {_("None")}"
							}.get(data.fec_inner, ""))
						case iDVBFrontend.feSatellite:
							data = transponder.getDVBS()
							orbPos = data.orbital_position
							try:
								satName = str(nimmanager.getSatDescription(orbPos))
							except KeyError:
								satName = ""
							if orbPos > 1800:
								orbPos = 3600 - orbPos
								direction = _("W")
							else:
								direction = _("E")
							transponderType = f"{_("Satellite")} {satName if f"{orbPos // 10}.{orbPos % 10}" in satName else f"{satName} {orbPos // 10}.{orbPos % 10} {direction}"}"
							scanInfo.append({
								data.System_DVB_S: "DVB-S",
								data.System_DVB_S2: "DVB-S2"
							}.get(data.system, ""))
							if data.system == data.System_DVB_S2:
								scanInfo.append({
									data.Modulation_Auto: f"{mod} {_("Auto")}",
									data.Modulation_QPSK: f"{mod} QPSK",
									data.Modulation_8PSK: f"{mod} 8PSK",
									data.Modulation_QAM16: f"{mod} QAM16",
									data.Modulation_16APSK: f"{mod} 16APSK",
									data.Modulation_32APSK: f"{mod} 32APSK"
								}.get(data.modulation, ""))
							scanInfo.append("%d%c" % (data.frequency // 1000, {
								data.Polarisation_Horizontal: "H",
								data.Polarisation_Vertical: "V",
								data.Polarisation_CircularLeft: "L",
								data.Polarisation_CircularRight: "R"
							}.get(data.polarisation, "")))
							scanInfo.append(data.symbol_rate // 1000)
							scanInfo.append({
								data.FEC_Auto: f"{fec} {_("Auto")}",
								data.FEC_1_2: f"{fec} 1/2",
								data.FEC_2_3: f"{fec} 2/3",
								data.FEC_3_4: f"{fec} 3/4",
								data.FEC_3_5: f"{fec} 3/5",
								data.FEC_4_5: f"{fec} 4/5",
								data.FEC_5_6: f"{fec} 5/6",
								data.FEC_6_7: f"{fec} 6/7",
								data.FEC_7_8: f"{fec} 7/8",
								data.FEC_8_9: f"{fec} 8/9",
								data.FEC_9_10: f"{fec} 9/10",
								data.FEC_None: f"{fec} {_("None")}"
							}.get(data.fec, ""))
							if data.system == data.System_DVB_S2:
								if data.is_id > data.No_Stream_Id_Filter:
									scanInfo.append(f"MIS {data.is_id}")
								if data.pls_code > 0:
									scanInfo.append(f"Gold {data.pls_code}")
								if data.t2mi_plp_id > data.No_T2MI_PLP_Id:
									scanInfo.append(f"T2MI {data.t2mi_plp_id} PID {data.t2mi_pid}")
						case iDVBFrontend.feTerrestrial:
							transponderType = _("Terrestrial")
							data = transponder.getDVBT()
							scanInfo.append({
								data.System_DVB_T: "DVB-T",
								data.System_DVB_T2: "DVB-T2",
								data.System_DVB_T_T2: "DVB-T/T2"
							}.get(data.system, ""))
							bandwidth = _("Bandwidth")
							scanInfo.append(f"{bandwidth} {data.bandwidth / 1000000.0:0.3f} {mhz}".replace(".000", "") if data.bandwidth else f"{bandwidth} {_("Auto")}")
							scanInfo.append(f"{data.frequency / 1000000.0:0.3f} {mhz}")
							channel = getChannelNumber(data.frequency, self.scanList[self.run]["feid"])
							if channel:
								scanInfo.append(f"{_("Channel")} {channel}")
							scanInfo.append({
								data.Modulation_Auto: f"{mod} {_("Auto")}",
								data.Modulation_QAM16: f"{mod} QAM16",
								data.Modulation_QAM64: f"{mod} QAM64",
								data.Modulation_QAM256: f"{mod} QAM256",
								data.Modulation_QPSK: f"{mod} QPSK"
							}.get(data.modulation, ""))
						case _:
							transponderType = _("Unknown")
							print("[ServiceScan] Error: Unknown transponder type!")
				transponderText = f"{scanInfo[0]}: {" - ".join([str(x) for x in scanInfo[1:]])}"
				currentSystem = iDVBFrontendDict.get(transponder.getSystem())
				if self.currentSystem != currentSystem:
					self.currentSystem = currentSystem
					self["FrontendInfo"].frontend_type = currentSystem
					self["FrontendInfo"].changed((1,))
			self["scan_progress"].setValue(self.scan.getProgress())
			self["network"].setText(transponderType)
			self["transponder"].setText(transponderText)
		match self.state:
			case self.RUNNING:
				percentage = self.scan.getProgress()
				if percentage > 99:
					percentage = 99  # Don't allow 100% as this causes a visual jump on the screen just before the message is replaced.
				# TRANSLATORS: The receiver is performing a service scan, progress percentage is printed in '%d' (and '%%' will show a single '%' symbol).
				self["scan_state"].setText(f"{ngettext("Scanning: %d%% complete", "Scanning: %d%% complete", percentage) % percentage}, {ngettext("%d service found.", "%d services found.", self.foundServices) % self.foundServices}")
			case self.DONE:
				print(f"[ServiceScan] {self.foundServices} services found. This run found {self.scan.getNumServices()}.")
				self.scan.newService.get().remove(self.newService)
				self.scan.statusChanged.get().remove(self.statusChanged)
				self.scan.clear()
				self["scan_state"].setText(ngettext("Scanning completed, %d service found.", "Scanning completed, %d services found.", self.foundServices) % self.foundServices)
				if self.run != len(self.scanList) - 1:
					def delayNext1():
						self.timer.stop()
						self.timer.callback.remove(delayNext1)
						self.runScan()

					self.run += 1
					self.state = self.RUNNING
					self.timer.callback.append(delayNext1)  # Hack to work around a timing bug in eComponentScan!
					self.timer.startLongTimer(2)  # Delay the next step by 2 seconds to give eComponentScan time to finish.
				else:
					def delayNext2():
						self.timer.stop()
						self.timer.callback.remove(delayNext2)
						if self.foundServices:
							self.runLCNScanner()
							self["servicelist"].setCurrentIndex(0)
							self["servicelist"].selectionEnabled(True)
							self["key_green"].setText(_("Select"))
							self["doneActions"].setEnabled(True)
						self["key_red"].setText(_("Close"))
						self["pass"].setText("")

					self.timer.callback.append(delayNext2)  # Hack to work around a timing bug in eComponentScan!
					self.timer.startLongTimer(2)  # Delay the next step by 2 seconds to give eComponentScan time to finish.
			case self.ERROR:
				self["scan_state"].setText(_("Error: Failed to run service scan!  (%s)") % self.ERRORS[errorCode])

	def runLCNScanner(self):
		def performScan():
			def lcnScannerCallback():
				def clearProcessing():
					self.timer.stop()
					Processing.instance.hideProgress()

				self.timer.callback.append(clearProcessing)
				self.timer.startLongTimer(2)

			self.timer.callback.remove(performScan)
			try:
				self.lcnScanner.lcnScan(callback=lcnScannerCallback)
			except Exception as err:
				print(f"[ServiceScan] Error: Unable to run the LCNScanner!  ({err})")
				Processing.instance.hideProgress()

		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "lcndb"), default=[], source=MODULE_NAME)
		if self.lcnScanner and len(lines) > 1:
			print("[ServiceScan] Running the LCNScanner after a scan.")
			Processing.instance.setDescription(_("Please wait while LCN bouquets are created/updated..."))
			Processing.instance.showProgress(endless=True)
			self.timer.callback.append(performScan)
			self.timer.start(0, True)  # Yield to the idle loop to allow a screen update.

	def keyCancel(self):
		self.finish(False)

	def keyCloseRecursive(self):
		self.finish(True)

	def finish(self, returnValue):
		# try:
		# 	self.session.nav.playService(self.currentServiceRef)
		# except Exception:
		# 	pass
		if self.currentInfobar.__class__.__name__ == "InfoBar":
			self.close(returnValue)
		self.close(returnValue)

	def keySave(self):
		# try:
		# 	self.session.nav.playService(self["servicelist"].getCurrent()[1])
		# except Exception:
		# 	pass
		# self.close(True)
		if self.currentInfobar.__class__.__name__ == "InfoBar":
			selectedService = self["servicelist"].getCurrent()
			if selectedService and self.currentServiceList is not None:
				self.currentServiceList.setTvMode()
				bouquets = self.currentServiceList.getBouquetList()
				lastScannedBouquet = bouquets and next((x[1] for x in bouquets if x[0] == "Last Scanned"), None)
				if lastScannedBouquet:
					self.currentServiceList.enterUserbouquet(lastScannedBouquet)
					self.currentServiceList.setCurrentSelection(eServiceReference(selectedService[1]))
					service = self.currentServiceList.getCurrentSelection()
					if not self.session.postScanService or service != self.session.postScanService:
						self.session.postScanService = service
						self.currentServiceList.addToHistory(service)
					config.servicelist.lastmode.save()
					self.currentServiceList.saveChannel(service)
					self.keyCloseRecursive()
		self.keyCancel()

	def createSummary(self):
		return ServiceScanSummary


class ServiceScanSummary(ScreenSummary):
	skin = """
	<screen name="ServiceScanSummary" title="Service Scan Summary" position="0,0" size="132,64">
		<widget name="Title" position="6,4" size="120,42" font="Regular;16" />
		<widget name="scan_progress" position="6,50" size="56,12" borderWidth="1" />
		<widget name="Service" position="6,22" size="120,26" font="Regular;12" />
	</screen>"""

	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent)
		self["scan_progress"] = ProgressBar()
		self["Service"] = Label(_("No service"))
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.updateProgress not in self.parent.onProgressChanged:
			self.parent.onProgressChanged.append(self.updateProgress)
		if self.updateService not in self.parent.onServiceChanged:
			self.parent.onServiceChanged.append(self.updateService)

	def removeWatcher(self):
		if self.updateProgress in self.parent.onProgressChanged:
			self.parent.onProgressChanged.remove(self.updateProgress)
		if self.updateService in self.parent.onServiceChanged:
			self.parent.onServiceChanged.remove(self.updateService)

	def updateProgress(self, progress):
		self["scan_progress"].setValue(progress)

	def updateService(self, service):
		self["Service"].setText(service)
