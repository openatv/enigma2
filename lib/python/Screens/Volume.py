from Components.Label import Label
from Components.VolumeBar import VolumeBar
from Screens.Screen import Screen


class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["Volume"] = VolumeBar()
		self["VolumeText"] = Label()

	def setValue(self, volume):
		print(f"[Volume] Volume set to {volume}.")
		self["Volume"].setValue(volume)
		self["VolumeText"].setText(str(volume))
