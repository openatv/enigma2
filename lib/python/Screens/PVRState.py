from Screen import Screen

from Components.Label import Label
from Components.Sources.CurrentService import CurrentService

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["state"] = Label(text="")

class TimeshiftState(PVRState):
	def __init__(self, session):
		PVRState.__init__(self, session)
		
		self["CurrentService"] = CurrentService(self.session.nav)
