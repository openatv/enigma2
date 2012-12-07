from Screens.Screen import Screen
from Components.VolumeBar import VolumeBar

class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.volumeBar = VolumeBar()

		self["Volume"] = self.volumeBar

	def setValue(self, vol):
		print "setValue", vol
		self.volumeBar.setValue(vol)
