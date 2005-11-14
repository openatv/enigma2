from Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label

class AudioSelection(Screen):
	def __init__(self, session, audio):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.close,
			})

		tlist = []

		n = audio.getNumberOfTracks()
		print "AUDIO TRACKS:"
		for x in range(n):
			i = audio.getTrackInfo(x)
			print i.getDescription()
			tlist.append((i.getDescription(), x))

		self["tracks"] = MenuList(tlist)
		#self["tracks"] = Label("Blasel")
		