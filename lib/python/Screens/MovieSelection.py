from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from Components.MovieList import MovieList

from enigma import eServiceReference

class MovieSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.movemode = False
		self.bouquet_mark_edit = False
		
		self["list"] = MovieList(eServiceReference("2:0:1:0:0:0:0:0:0:0:/hdd/movies/"))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.movieSelected,
			})
		self["actions"].csel = self

	def movieSelected(self):
		self.session.nav.playService(self["list"].getCurrent()[0])
		self.close()
