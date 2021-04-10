from Components.Label import Label
from Components.VolumeBar import VolumeBar
from Screens.Screen import Screen


class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.volumeBar = VolumeBar()
		self["Volume"] = self.volumeBar
		self["VolumeText"] = Label("")

	def setValue(self, vol):
		print "[Volume] Volume set to %d." % vol
		self.volumeBar.setValue(vol)
		self["VolumeText"].text = str(vol)
