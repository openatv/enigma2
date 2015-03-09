from Screen import Screen
import Screens.InfoBar
from Components.ServiceScan import ServiceScan as CScan
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.FIFOList import FIFOList
from Components.Sources.FrontendInfo import FrontendInfo
from Components.config import config
from enigma import eServiceCenter, eServiceReference

class ServiceScanSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="Title" position="6,4" size="120,42" font="Regular;16" transparent="1" />
		<widget name="scan_progress" position="6,50" zPosition="1" borderWidth="1" size="56,12" backgroundColor="dark" />
		<widget name="Service" position="6,22" size="120,26" font="Regular;12" transparent="1" />
	</screen>"""

	def __init__(self, session, parent, showStepSlider = True):
		Screen.__init__(self, session, parent)

		self["Title"] = Label(parent.title or _("Service scan"))
		self["Service"] = Label(_("No service"))
		self["scan_progress"] = ProgressBar()

	def updateProgress(self, value):
		self["scan_progress"].setValue(value)

	def updateService(self, name):
		self["Service"].setText(name)

class ServiceScan(Screen):

	def ok(self):
		print "ok"
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

	def __init__(self, session, scanList):
		Screen.__init__(self, session)

		self.scanList = scanList

		if hasattr(session, 'infobar'):
			self.currentInfobar = Screens.InfoBar.InfoBar.instance
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
		self["servicelist"] = FIFOList()
		self["FrontendInfo"] = FrontendInfo()
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"ok": self.ok,
			"save": self.ok,
			"cancel": self.cancel,
			"menu": self.doCloseRecursive
		}, -2)
		self.setTitle(_("Service scan"))
		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["servicelist"].len = self["servicelist"].instance.size().height() / self["servicelist"].l.getItemSize().height()
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], self["servicelist"], self["pass"], self.scanList, self["network"], self["transponder"], self["FrontendInfo"], self.session.summary)

	def createSummary(self):
		print "ServiceScanCreateSummary"
		return ServiceScanSummary
