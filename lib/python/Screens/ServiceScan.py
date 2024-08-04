from enigma import eServiceReference, eTimer

from Components.ActionMap import ActionMap
from Components.config import config
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ProgressBar import ProgressBar
from Components.ServiceScan import ServiceScan as CScan
from Components.Sources.FrontendInfo import FrontendInfo
try:
	from Plugins.SystemPlugins.LCNScanner.plugin import LCNScanner
except ImportError:
	LCNScanner = None
import Screens.InfoBar
from Screens.Processing import Processing
from Screens.Screen import Screen
from Tools.Directories import SCOPE_CONFIG, fileReadLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]


class FIFOList(MenuList):
	def __init__(self, len=10):
		self.len = len
		self.list = []
		MenuList.__init__(self, self.list)

	def addItem(self, item):
		self.list.append(item)
		self.l.setList(self.list[-self.len:])

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)

	def getCurrentSelection(self):
		return self.list and self.getCurrent() or None

	def listAll(self):
		self.l.setList(self.list)
		self.selectionEnabled(True)


class ServiceScanSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="Title" position="6,4" size="120,42" font="Regular;16" transparent="1" />
		<widget name="scan_progress" position="6,50" zPosition="1" borderWidth="1" size="56,12" backgroundColor="dark" />
		<widget name="Service" position="6,22" size="120,26" font="Regular;12" transparent="1" />
	</screen>"""

	def __init__(self, session, parent, showStepSlider=True):
		Screen.__init__(self, session, parent)

		self["Title"] = Label(parent.title or _("Service scan"))
		self["Service"] = Label(_("No service"))
		self["scan_progress"] = ProgressBar()

	def updateProgress(self, value):
		self["scan_progress"].setValue(value)

	def updateService(self, name):
		self["Service"].setText(name)


class ServiceScan(Screen):
	def __init__(self, session, scanList):
		Screen.__init__(self, session)
		self["Title"] = Label(_("Scanning..."))
		self.scanList = scanList
		if hasattr(session, 'infobar'):
			self.currentInfobar = Screens.InfoBar.InfoBar.instance
			if self.currentInfobar:
				self.currentServiceList = self.currentInfobar.servicelist
				if self.session.pipshown and self.currentServiceList:
					if self.currentServiceList.dopipzap:
						self.currentServiceList.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
		else:
			self.currentInfobar = None
		self.session.nav.stopService()
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))
		self["network"] = Label()
		self["transponder"] = Label()
		self["pass"] = Label("")
		self["servicelist"] = FIFOList(len=10)
		self["FrontendInfo"] = FrontendInfo()
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["actions"] = ActionMap(["SetupActions", "MenuActions"], {
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"save": self.ok,
			"cancel": self.cancel,
			"menu": self.doCloseRecursive
		}, -2)
		self.setTitle(_("Service Scan"))
		self.onFirstExecBegin.append(self.doServiceScan)
		self.scanTimer = eTimer()
		self.scanTimer.callback.append(self.scanPoll)
		self.LCNScanner = LCNScanner() if LCNScanner else None

	def up(self):
		self["servicelist"].up()
		selectedService = self["servicelist"].getCurrentSelection()
		if selectedService:
			self.session.summary.updateService(selectedService[0])

	def down(self):
		self["servicelist"].down()
		selectedService = self["servicelist"].getCurrentSelection()
		if selectedService:
			self.session.summary.updateService(selectedService[0])

	def ok(self):
		if self["scan"].isDone():
			if self.currentInfobar.__class__.__name__ == "InfoBar":
				selectedService = self["servicelist"].getCurrentSelection()
				if selectedService and self.currentServiceList is not None:
					self.currentServiceList.setTvMode()
					bouquets = self.currentServiceList.getBouquetList()
					last_scanned_bouquet = bouquets and next((x[1] for x in bouquets if x[0] == "Last Scanned"), None)
					if last_scanned_bouquet:
						self.currentServiceList.enterUserbouquet(last_scanned_bouquet)
						self.currentServiceList.setCurrentSelection(eServiceReference(selectedService[1]))
						service = self.currentServiceList.getCurrentSelection()
						if not self.session.postScanService or service != self.session.postScanService:
							self.session.postScanService = service
							self.currentServiceList.addToHistory(service)
						config.servicelist.lastmode.save()
						self.currentServiceList.saveChannel(service)
						self.doCloseRecursive()
			self.cancel()

	def cancel(self):
		self.exit(False)

	def doCloseRecursive(self):
		self.exit(True)

	def exit(self, returnValue):
		if self.currentInfobar.__class__.__name__ == "InfoBar":
			self.close(returnValue)
		self.close()

	def scanPoll(self):
		if self["scan"].isDone():
			self.scanTimer.stop()
			self.runLCNScanner()
			self["servicelist"].moveToIndex(0)
			selectedService = self["servicelist"].getCurrentSelection()
			if selectedService:
				self.session.summary.updateService(selectedService[0])

	def doServiceScan(self):
		self["servicelist"].len = self["servicelist"].instance.size().height() // self["servicelist"].l.getItemSize().height()
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], self["servicelist"], self["pass"], self.scanList, self["network"], self["transponder"], self["FrontendInfo"], self.session.summary)
		self.scanTimer.start(250)

	def runLCNScanner(self):
		def performScan():
			def lcnScannerCallback():
				def clearProcessing():
					Processing.instance.hideProgress()

				self.timer = eTimer()  # This must be in the self context to keep the code alive when the method exits.
				self.timer.callback.append(clearProcessing)
				self.timer.startLongTimer(2)

			try:
				self.LCNScanner.lcnScan(callback=lcnScannerCallback)
			except Exception as err:
				print(f"[ServiceScan] Error: Unable to run the LCNScanner!  ({err})")
				Processing.instance.hideProgress()

		lines = fileReadLines(resolveFilename(SCOPE_CONFIG, "lcndb"), default=[], source=MODULE_NAME)
		if self.LCNScanner and len(lines) > 1:
			print("[ServiceScan] Running the LCNScanner after a scan.")
			Processing.instance.setDescription(_("Please wait while LCN bouquets are created/updated..."))
			Processing.instance.showProgress(endless=True)
			self.timer = eTimer()  # This must be in the self context to keep the code alive when the method exits.
			self.timer.callback.append(performScan)
			self.timer.start(0, True)  # Yield to the idle loop to allow a screen update.

	def createSummary(self):
		return ServiceScanSummary
