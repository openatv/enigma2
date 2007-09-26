from Screen import Screen
from Components.Button import Button
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.MenuList import MenuList
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigInteger, configfile
from Components.Sources.ServiceEvent import ServiceEvent

from Plugins.Plugin import PluginDescriptor

from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen

from Tools.Directories import *
from Tools.BoundFunction import boundFunction

from enigma import eServiceReference, eServiceCenter, eTimer, eSize

config.movielist = ConfigSubsection()
config.movielist.moviesort = ConfigInteger(default=MovieList.SORT_RECORDED)
config.movielist.listtype = ConfigInteger(default=MovieList.LISTTYPE_ORIGINAL)
config.movielist.description = ConfigInteger(default=MovieList.HIDE_DESCRIPTION)

class MovieContextMenu(Screen):
	def __init__(self, session, csel, service):
		Screen.__init__(self, session)
		self.csel = csel
		self.service = service

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})

		menu = [(_("delete..."), self.delete)]
		
		for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST):
			menu.append((p.description, boundFunction(self.execPlugin, p)))
		
		if config.movielist.moviesort.value == MovieList.SORT_ALPHANUMERIC:
			menu.append((_("sort by date"), boundFunction(self.sortBy, MovieList.SORT_RECORDED)))
		else:
			menu.append((_("alphabetic sort"), boundFunction(self.sortBy, MovieList.SORT_ALPHANUMERIC)))
		
		menu.append((_("list style default"), boundFunction(self.listType, MovieList.LISTTYPE_ORIGINAL)))
		menu.append((_("list style compact with description"), boundFunction(self.listType, MovieList.LISTTYPE_COMPACT_DESCRIPTION)))
		menu.append((_("list style compact"), boundFunction(self.listType, MovieList.LISTTYPE_COMPACT)))
		menu.append((_("list style single line"), boundFunction(self.listType, MovieList.LISTTYPE_MINIMAL)))
		
		if config.movielist.description.value == MovieList.SHOW_DESCRIPTION:
			menu.append((_("hide extended description"), boundFunction(self.showDescription, MovieList.HIDE_DESCRIPTION)))
		else:
			menu.append((_("show extended description"), boundFunction(self.showDescription, MovieList.SHOW_DESCRIPTION)))
		self["menu"] = MenuList(menu)

	def okbuttonClick(self):
		self["menu"].getCurrent()[1]()

	def cancelClick(self):
		self.close(False)

	def sortBy(self, newType):
		self.csel.saveflag = True
		config.movielist.moviesort.value = newType
		self.csel.selectedmovie = self.csel.getCurrent()
		self.csel.setSortType(newType)
		self.csel.reloadList()
		self.csel.moveTo()
		self.close()

	def listType(self, newType):
		self.csel.saveflag = True
		config.movielist.listtype.value = newType
		self.csel.setListType(newType)
		self.csel.list.redrawList()
		self.close()

	def showDescription(self, newType):
		self.csel.saveflag = True
		config.movielist.description.value = newType
		self.csel.setDescriptionState(newType)
		self.csel.updateDescription()
		self.close()

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

class SelectionEventInfo:
	def __init__(self):
		self["Service"] = ServiceEvent()
		self.list.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.timeout.get().append(self.updateEventInfo)
		self.onShown.append(self.__selectionChanged)

	def __selectionChanged(self):
		if self.execing and config.movielist.description.value == MovieList.SHOW_DESCRIPTION:
			self.timer.start(100, True)

	def updateEventInfo(self):
		serviceref = self.getCurrent()
		self["Service"].newService(serviceref)

class MovieSelection(Screen, HelpableScreen, SelectionEventInfo):
	def __init__(self, session, selectedmovie = None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.saveflag = False

		self.tags = [ ]
		self.selected_tags = None

		self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + resolveFilename(SCOPE_HDD))

		self.movemode = False
		self.bouquet_mark_edit = False

		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.updateHDDData)

		self["waitingtext"] = Label(_("Please wait... Loading list..."))

		# create optional description border and hide immediately
		self["DescriptionBorder"] = Pixmap()
		self["DescriptionBorder"].hide()

		self["list"] = MovieList(None,
			config.movielist.listtype.value,
			config.movielist.moviesort.value,
			config.movielist.description.value)

		self.list = self["list"]
		self.selectedmovie = selectedmovie

		# Need list for init
		SelectionEventInfo.__init__(self)

		self["key_red"] = Button(_("All..."))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		#self["freeDiskSpace"] = DiskInfo(resolveFilename(SCOPE_HDD), DiskInfo.FREE, update=False)
		self["freeDiskSpace"] = self.diskinfo = DiskInfo(resolveFilename(SCOPE_HDD), DiskInfo.FREE, update=False)

		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.doContext, _("menu")),
				"showEventInfo": (self.showEventInformation, _("show event details")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"red": (self.showAll, _("show all")),
				"green": (self.showTagsFirst, _("show first tag")),
				"yellow": (self.showTagsSecond, _("show second tag")),
				"blue": (self.showTagsMenu, _("show tag menu")),
			})

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"cancel": (self.abort, _("exit movielist")),
				"ok": (self.movieSelected, _("select movie")),
			})

		self.onShown.append(self.go)
		self.inited = False

	def updateDescription(self):
		if config.movielist.description.value == MovieList.SHOW_DESCRIPTION:
			self["DescriptionBorder"].show()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight-self["DescriptionBorder"].instance.size().height()))
		else:
			self["Service"].newService(None)
			self["DescriptionBorder"].hide()
			self["list"].instance.resize(eSize(self.listWidth, self.listHeight))

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
		# as this workaround is here anyways we can wait until the skin is initialized
		# and afterwards read out the information we need to draw the dynamic style
			listsize = self["list"].instance.size()
			self.listWidth = listsize.width()
			self.listHeight = listsize.height()
			self.updateDescription()

	def updateHDDData(self):
 		self.reloadList()
 		if self.selectedmovie is not None:
			self.moveTo()
		self["waitingtext"].visible = False
		self["freeDiskSpace"].update()
		self.updateTags()

	def moveTo(self):
		self["list"].moveTo(self.selectedmovie)

	def getCurrent(self):
		return self["list"].getCurrent()

	def movieSelected(self):
		current = self.getCurrent()
		if current is not None:
			self.saveconfig()
			self.close(current)

	def doContext(self):
		current = self.getCurrent()
		if current is not None:
			self.session.open(MovieContextMenu, self, current)

	def abort(self):
		self.saveconfig()
		self.close(None)

	def saveconfig(self):
		if self.saveflag == True:
			config.movielist.moviesort.save()
			config.movielist.listtype.save()
			config.movielist.description.save()
			configfile.save()
			self.saveflag = False

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

	def setListType(self, type):
		self["list"].setListType(type)

	def setDescriptionState(self, val):
		self["list"].setDescriptionState(val)

	def setSortType(self, type):
		self["list"].setSortType(type)

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
