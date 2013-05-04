from Screen import Screen

from Components.Label import Label
from Components.Pixmap import Pixmap, MultiPixmap

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["eventname"] = Label()
		self["state"] = Label()
		self["speed"] = Label()
		self["statusicon"] = MultiPixmap()

class TimeshiftState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["eventname"] = Label()
		self["state"] = Label()
		self["speed"] = Label()
		self["statusicon"] = MultiPixmap()
		self["PTSSeekBack"] = Pixmap()
		self["PTSSeekPointer"] = Pixmap()
