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
	
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label("scan state")
		self["scan"] = CScan(self["scan_progress"], self["scan_state"])

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.cancel
			})
