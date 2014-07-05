from Screens.Screen import Screen
from Components.Sources.Clock import Clock
#from Components.Sources.OnlineUpdate import OnlineUpdateStableCheck, OnlineUpdateUnstableCheck

class Globals(Screen):
	def __init__(self):
		Screen.__init__(self, None)
		self["CurrentTime"] = Clock()
		#self["OnlineStableUpdateState"] = OnlineUpdateStableCheck()
		#self["OnlineUnstableUpdateState"] = OnlineUpdateUnstableCheck()
