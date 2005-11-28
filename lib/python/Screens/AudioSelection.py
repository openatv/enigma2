from Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Tools.ISO639 import LanguageCodes

class AudioSelection(Screen):
	def KeyOk(self):
		selection = self["tracks"].getCurrent()
		print "select track " + str(selection[1])
		
		self.audio.selectTrack(selection[1])
		self.close()
	def __init__(self, session, audio):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.KeyOk,
			})

		self.audio = audio

		tlist = []
		n = audio.getNumberOfTracks()
		for x in range(n):
			i = audio.getTrackInfo(x)
			langCode = i.getLanguage()
			
			description = i.getDescription();
			
			if langCode in LanguageCodes:
				language = LanguageCodes[langCode][0]
				if len(description):
					description += " (" + language + ")"
				else:
					description = language

			tlist.append((description, x))

		self["tracks"] = MenuList(tlist)
