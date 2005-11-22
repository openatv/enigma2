from Screen import Screen
from Components.ServiceScan import ServiceScan as CScan
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ActionMap import ActionMap

class ServiceScan(Screen):
	def ok(self):
		print "ok"
		if self["scan"].isDone():
			self.close()
	
	def cancel(self):
		self.close()
	
	def __init__(self, session, transponders, feid, flags):
		Screen.__init__(self, session)
		
		self.session.nav.stopService()
		
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], transponders, feid, flags)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.cancel
			})
