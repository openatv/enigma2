from Screen import Screen
from Components.ServiceScan import ServiceScan as CScan
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.FIFOList import FIFOList
from Components.Sources.FrontendInfo import FrontendInfo
from enigma import eServiceCenter

class ServiceScanSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="Title" position="6,4" size="120,42" font="Regular;16" transparent="1" />
		<widget name="scan_progress" position="6,50" zPosition="1" borderWidth="1" size="56,12" backgroundColor="dark" />
		<widget name="Service" position="6,22" size="120,26" font="Regular;12" transparent="1" />
	</screen>"""
	
	def __init__(self, session, parent, showStepSlider = True):
		Screen.__init__(self, session, parent)
		
		self["Title"] = Label(parent.title or "ServiceScan")
		self["Service"] = Label("No Service")
		self["scan_progress"] = ProgressBar()
		
	def updateProgress(self, value):
		self["scan_progress"].setValue(value)

	def updateService(self, name):
		self["Service"].setText(name)

class ServiceScan(Screen):
	
	def ok(self):
		print "ok"
		if self["scan"].isDone():
			if `self.currentInfobar`.endswith(".InfoBar'>"):
				if self.currentServiceList is not None:
					self.currentServiceList.setTvMode()
					bouquets = self.currentServiceList.getBouquetList()
					for x in bouquets:
						if x[0] == 'Last Scanned':
							self.currentServiceList.setRoot(x[1])
							services = eServiceCenter.getInstance().list(self.currentServiceList.servicelist.getRoot())
							channels = services and services.getContent("R", True)
							if channels:
								self.session.postScanService = channels[0]
								self.currentServiceList.addToHistory(channels[0])
			self.close()

	def cancel(self):
		self.close()
		
	def __init__(self, session, scanList):
		Screen.__init__(self, session)
		
		self.scanList = scanList
		
		if hasattr(session, 'infobar'):
			self.currentInfobar = session.infobar
			self.currentServiceList = self.currentInfobar.servicelist
			if self.session.pipshown and self.currentServiceList:
				if self.currentServiceList.dopipzap:
					self.currentServiceList.togglePipzap()
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
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.cancel
			})

		self.onFirstExecBegin.append(self.doServiceScan)

	def doServiceScan(self):
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], self["servicelist"], self["pass"], self.scanList, self["network"], self["transponder"], self["FrontendInfo"], self.session.summary)

	def createSummary(self):
		print "ServiceScanCreateSummary"
		return ServiceScanSummary