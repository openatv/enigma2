from Screen import Screen
from Components.ActionMap import ActionMap
	
class Setup(Screen):
	def __init__(self, session, setup):
		Screen.__init__(self, session)

		print "request setup for " + setup

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				#"ok": self.inc,
				"cancel": self.close
			})
			
