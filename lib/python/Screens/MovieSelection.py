from Screen import Screen
from Components.Button import Button
from Components.ActionMap import ActionMap
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo
from Components.Label import Label
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor

from Screens.MessageBox import MessageBox
from Screens.FixedMenu import FixedMenu
from Screens.ChoiceBox import ChoiceBox

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
		
		self.tags = [ ]
		self.selected_tags = None
		
		self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + resolveFilename(SCOPE_HDD))
		
		self.movemode = False
		self.bouquet_mark_edit = False
		
		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.updateHDDData)
		
		self["waitingtext"] = Label(_("Please wait... Loading list..."))
		
		self["list"] = MovieList(None)
		self.list = self["list"]
		self.selectedmovie = selectedmovie
		
		self["key_red"] = Button(_("All..."))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		self["freeDiskSpace"] = DiskInfo(resolveFilename(SCOPE_HDD), DiskInfo.FREE, update=False)
		
		self["actions"] = ActionMap(["OkCancelActions", "MovieSelectionActions", "ColorActions"],
			{
				"cancel": self.abort,
				"ok": self.movieSelected,
				"showEventInfo": self.showEventInformation,
				"contextMenu": self.doContext,
				
				"red": self.showAll,
				"green": self.showTagsFirst,
				"yellow": self.showTagsSecond,
				"blue": self.showTagsMenu,
			})
		self["actions"].csel = self
		self.onShown.append(self.go)
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
 		self.reloadList()
 		if self.selectedmovie is not None:
			self.moveTo()
		self["waitingtext"].instance.hide()

		self["freeDiskSpace"].update()

		self.updateTags()

	def moveTo(self):
		self["list"].moveTo(self.selectedmovie)

	def getCurrent(self):
		return self["list"].getCurrent()

	def movieSelected(self):
		current = self.getCurrent()
		if current is not None:
			self.close(current)

	def doContext(self):
		current = self.getCurrent()
		if current is not None:
			self.session.open(ChannelContextMenu, self, current)

	def abort(self):
		self.close(None)

	def getTagDescription(self, tag):
		# TODO: access the tag database
		return tag

	def updateTags(self):
		# get a list of tags available in this list
		self.tags = list(self["list"].tags)
		
		# by default, we do not display any filtering options
		self.tag_first = ""
		self.tag_second = ""
		
		# when tags are present, however, the first two are 
		# directly mapped to the second, third ("green", "yellow") buttons
		if len(self.tags) > 0:
			self.tag_first = self.getTagDescription(self.tags[0])
		
		if len(self.tags) > 1:
			self.tag_second = self.getTagDescription(self.tags[1])
		
		self["key_green"].text = self.tag_first
		self["key_yellow"].text = self.tag_second
		
		# the rest is presented in a list, available on the
		# fourth ("blue") button
		if len(self.tags) > 2:
			self["key_blue"].text = _("Other...")
		else:
			self["key_blue"].text = ""

	def reloadList(self):
		self["list"].reload(self.current_ref, self.selected_tags)
		title = _("Recorded files...")
		if self.selected_tags is not None:
			title += " - " + ','.join(self.selected_tags)
		self.setTitle(title)

	def showAll(self):
		self.selected_tags = None
		self.reloadList()

	def showTagsN(self, n):
		if len(self.tags) < n:
			self.showTagWarning()
		else:
			print "select tag #%d, %s, %s" % (n, self.tags[n - 1], ','.join(self.tags))
			self.selected_tags = set([self.tags[n - 1]])
			self.reloadList()

	def showTagsFirst(self):
		self.showTagsN(1)

	def showTagsSecond(self):
		self.showTagsN(2)

	def tagChosen(self, tag):
		if tag is not None:
			self.selected_tags = set([tag[0]])
			self.reloadList()

	def showTagsMenu(self):
		if len(self.tags) < 3:
			self.showTagWarning()
		else:
			list = [(tag, self.getTagDescription(tag)) for tag in self.tags ]
			self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select keyword to filter..."), list = list)

	def showTagWarning(self):
		# TODO
		self.session.open(MessageBox, _("You need to define some keywords first!\nPress the menu-key to define keywords.\nDo you want to define keywords now?"), MessageBox.TYPE_ERROR)
