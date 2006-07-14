from Screen import Screen
from Components.Button import Button
from Components.ServiceList import ServiceList
from Components.ActionMap import ActionMap
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo
from Components.Label import Label
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor

from Screens.MessageBox import MessageBox
from Screens.FixedMenu import FixedMenu

from Tools.Directories import *
from Tools.BoundFunction import boundFunction

from enigma import eServiceReference, eServiceCenter, eTimer

class ChannelContextMenu(FixedMenu):
	def __init__(self, session, csel, service):
		self.csel = csel
		self.service = service

		menu = [(_("back"), self.close), (_("delete..."), self.delete)]

		for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
			menu.append((p.description, boundFunction(self.execPlugin, p)))

		FixedMenu.__init__(self, session, _("Movie Menu"), menu)
		self.skinName = "Menu"

	def execPlugin(self, plugin):
		plugin(session=self.session, service=self.service)

	def delete(self):
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(self.service)
		info = serviceHandler.info(self.service)
		name = info and info.getName(self.service) or _("this recording")
		result = False
		if offline is not None:
			# simulate first
			if not offline.deleteFromDisk(1):
				result = True
		
		if result == True:
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Do you really want to delete %s?") % (name))
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
			list = self.csel["list"].removeService(self.service)
			self.close()
 
class MovieSelection(Screen):
	def __init__(self, session, selectedmovie = None):
		Screen.__init__(self, session)
		
		self.movemode = False
		self.bouquet_mark_edit = False
		
		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.updateHDDData)
		
		self["waitingtext"] = Label(_("Please wait... Loading list..."))
		
		self["list"] = MovieList(None)
		self.list = self["list"]
		self.selectedmovie = selectedmovie
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		self["freeDiskSpace"] = DiskInfo(resolveFilename(SCOPE_HDD), DiskInfo.FREE, update=False)
		
		self["actions"] = ActionMap(["OkCancelActions", "MovieSelectionActions"],
			{
				"cancel": self.abort,
				"ok": self.movieSelected,
				"showEventInfo": self.showEventInformation,
				"contextMenu": self.doContext,
			})
		self["actions"].csel = self
		self.onShown.append(self.go)
		
		self.lengthTimer = eTimer()
		self.lengthTimer.timeout.get().append(self.updateLengthData)
		self.inited = False

	def showEventInformation(self):
		from Screens.EventView import EventViewSimple
		from ServiceReference import ServiceReference
		evt = self["list"].getCurrentEvent()
		if evt:
			self.session.open(EventViewSimple, evt, ServiceReference(self.getCurrent()))

	def go(self):
		if not self.inited:
		# ouch. this should redraw our "Please wait..."-text.
		# this is of course not the right way to do this.
			self.delayTimer.start(10, 1)
			self.inited=True

	def updateHDDData(self):
		self["list"].reload(eServiceReference("2:0:1:0:0:0:0:0:0:0:" + resolveFilename(SCOPE_HDD)))
		if (self.selectedmovie is not None):
			self.moveTo()
		self["waitingtext"].instance.hide()
						
		self["freeDiskSpace"].update()
		
		self.lengthTimer.start(10, 1)
		self.lengthPosition = 0
		self.lengthLength = len(self["list"])
		
	def updateLengthData(self):
		self.list.updateLengthOfIndex(self.lengthPosition)
		self.lengthPosition += 1
		if self.lengthPosition < self.lengthLength:
			self.lengthTimer.start(10, 1)

	def moveTo(self):
		self["list"].moveTo(self.selectedmovie)

	def getCurrent(self):
		return self["list"].getCurrent()

	def movieSelected(self):
		self.lengthTimer.stop()
		current = self.getCurrent()
		if current is not None:
			self.close(current)

	def doContext(self):
		current = self.getCurrent()
		if current is not None:
			self.session.open(ChannelContextMenu, self, current)

	def abort(self):
		self.close(None)
