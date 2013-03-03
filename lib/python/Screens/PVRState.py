from Screen import Screen

from Components.Label import Label
from Components.Pixmap import Pixmap, MultiPixmap

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["speed"] = Label(text="")
		self["statusicon"] = MultiPixmap()

class TimeshiftState(PVRState):
	pass

class PTSTimeshiftState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["state"] = Label(text="")
		self["speed"] = Label(text="")
		self["statusicon"] = MultiPixmap()
		self["PTSSeekBack"] = Pixmap()
		self["PTSSeekPointer"] = Pixmap()
		self["eventname"] = Label(text="")
