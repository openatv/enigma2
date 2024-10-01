from Components.Label import Label
from Components.VolumeBar import VolumeBar
from Screens.Screen import Screen


class Mute(Screen):
	pass


class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["VolumeText"] = Label()
		self["Volume"] = VolumeBar()

	def setValue(self, volume):
		print(f"[Volume] Volume set to {volume}.")
		self["VolumeText"].setText(str(volume))
		self["Volume"].setValue(volume)
