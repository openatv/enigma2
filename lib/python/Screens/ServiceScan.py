from Screen import Screen
from Components.ServiceScan import ServiceScan as CScan
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.FIFOList import FIFOList
from Components.Sources.FrontendInfo import FrontendInfo

class ServiceScan(Screen):
	def ok(self):
		print "ok"
		if self["scan"].isDone():
			self.close()
	
	def cancel(self):
		self.close()
	
	def __init__(self, session, scanList):
		Screen.__init__(self, session)
		
		self.session.nav.stopService()
		
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))
		self["network"] = Label()
		self["transponder"] = Label()

		self["pass"] = Label("")
		self["servicelist"] = FIFOList(len=10)
		self["FrontendInfo"] = FrontendInfo()
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], self["servicelist"], self["pass"], scanList, self["network"], self["transponder"], self["FrontendInfo"])

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.cancel
			})
