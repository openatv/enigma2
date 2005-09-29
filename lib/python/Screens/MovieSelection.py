from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo

from Screens.FixedMenu import FixedMenu

from enigma import eServiceReference

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel):
		self.csel = csel
		
		menu = [("back", self.close), ("delete...", self.delete)]
		
		FixedMenu.__init__(self, session, "Movie Menu", menu)
		self.skinName = "Menu"

	def delete(self):
		print "deleting ALL SERVICES! HA HA HA!"
		pass
 
class MovieSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.movemode = False
		self.bouquet_mark_edit = False
		
		self["list"] = MovieList(eServiceReference("2:0:1:0:0:0:0:0:0:0:/hdd/movies/"))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		self["freeDiskSpace"] = DiskInfo("/hdd/movies", DiskInfo.FREE)
		
		self["actions"] = ActionMap(["OkCancelActions", "ContextMenuActions"],
			{
				"cancel": self.close,
				"ok": self.movieSelected,
				"contextMenu": self.doContext,
			})
		self["actions"].csel = self

	def movieSelected(self):
		self.session.nav.playService(self["list"].getCurrent()[0])
		self.close()

	def doContext(self):
		self.session.open(ChannelContextMenu, self)
