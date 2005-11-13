from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo

from Screens.MessageBox import MessageBox
from Screens.FixedMenu import FixedMenu

from enigma import eServiceReference, eServiceCenter

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel, service):
		self.csel = csel
		self.service = service
		
		menu = [("back", self.close), ("delete...", self.delete)]
		
		FixedMenu.__init__(self, session, "Movie Menu", menu)
		self.skinName = "Menu"

	def delete(self):
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		result = False
		if offline is not None:
			# simulate first
			if not offline.deleteFromDisk(1):
				result = True
		
		if result == True:
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, "Do you really want to delete this recording?")
		else:
			self.session.openWithCallback(self.close, MessageBox, "You cannot delete this!")

	def deleteConfirmed(self, confirmed):
		if not confirmed:
			return self.close()
			
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		result = False
		if offline is not None:
			# really delete!
			if not offline.deleteFromDisk(0):
				result = True
		
		if result == False:
			self.session.openWithCallback(self.close, MessageBox, "Delete failed!")
		else:
			self.csel["list"].reload()
			self.close()
		
 
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

	def getCurrent(self):
		return self["list"].getCurrent()[0]

	def movieSelected(self):
		self.session.nav.playService(self.getCurrent())
		self.close()

	def doContext(self):
		self.session.open(ChannelContextMenu, self, self.getCurrent())
