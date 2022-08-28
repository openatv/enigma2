from Components.Label import Label
from Components.VolumeBar import VolumeBar
from Screens.Screen import Screen


class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.volumeBar = VolumeBar()
		self["Volume"] = self.volumeBar
		self["VolumeText"] = Label("")

	def setValue(self, volume):
		print("[Volume] Volume set to %d." % volume)
		self.volumeBar.setValue(volume)
		self["VolumeText"].text = str(volume)
