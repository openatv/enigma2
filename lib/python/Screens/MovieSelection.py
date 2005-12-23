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
		
		menu = [(_("back"), self.close), (_("delete..."), self.delete)]
		
		FixedMenu.__init__(self, session, _("Movie Menu"), menu)
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
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Do you really want to delete this recording?"))
		else:
			self.session.openWithCallback(self.close, MessageBox, _("You cannot delete this!"), MessageBox.TYPE_ERROR)

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
			self.session.openWithCallback(self.close, MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
		else:
			list = self.csel["list"]
			currentIndex = list.getCurrentIndex()
			list.moveDown()
			if list.getCurrentIndex() == currentIndex:
				currentIndex -= 1
			list.reload()
			list.moveToIndex(currentIndex)
			self.close()
 
class MovieSelection(Screen):
	def __init__(self, session, selectedmovie = None):
		Screen.__init__(self, session)
		
		self.movemode = False
		self.bouquet_mark_edit = False
		
		self["list"] = MovieList(eServiceReference("2:0:1:0:0:0:0:0:0:0:/hdd/movies/"))
		if (selectedmovie is not None):
			self.onShown.append(self.moveTo)
			self.selectedmovie = selectedmovie
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		self["freeDiskSpace"] = DiskInfo("/hdd/movies", DiskInfo.FREE)
		
		self["actions"] = ActionMap(["OkCancelActions", "ContextMenuActions"],
			{
				"cancel": self.abort,
				"ok": self.movieSelected,
				"contextMenu": self.doContext,
			})
		self["actions"].csel = self

	def moveTo(self):
		self["list"].moveTo(self.selectedmovie)

	def getCurrent(self):
		return self["list"].getCurrent()[0]

	def movieSelected(self):
		self.close(self.getCurrent())

	def doContext(self):
		self.session.open(ChannelContextMenu, self, self.getCurrent())

	def abort(self):
		self.close(None)
