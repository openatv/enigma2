from Screen import Screen

from Components.Label import Label

from enigma import *

class PVRState(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["state"] = Label(text="blub")
