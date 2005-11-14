from Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label

class AudioSelection(Screen):
	def KeyOk(self):
		selection = self["tracks"].getCurrent()
		print "select track " + str(selection[1])
		self.audio.selectTrack(selection[1])
		self.close()
	def __init__(self, session, audio):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.close,
				"ok": self.KeyOk,
			})

		self.audio = audio

		tlist = []
		n = audio.getNumberOfTracks()
		for x in range(n):
			i = audio.getTrackInfo(x)
			tlist.append((i.getDescription(), x))

		self["tracks"] = MenuList(tlist)

		