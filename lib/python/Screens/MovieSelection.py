from Screen import Screen
from Components.Button import Button
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.MenuList import MenuList
from Components.MovieList import MovieList
from Components.DiskInfo import DiskInfo
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.config import config, ConfigSubsection, ConfigText, ConfigInteger, ConfigLocations, ConfigSet
from Components.Sources.ServiceEvent import ServiceEvent
from Components.UsageConfig import defaultMoviePath

from Plugins.Plugin import PluginDescriptor

from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.HelpMenu import HelpableScreen

from Tools.Directories import *
from Tools.BoundFunction import boundFunction

from enigma import eServiceReference, eServiceCenter, eTimer, eSize

config.movielist = ConfigSubsection()
config.movielist.moviesort = ConfigInteger(default=MovieList.SORT_RECORDED)
config.movielist.listtype = ConfigInteger(default=MovieList.LISTTYPE_ORIGINAL)
config.movielist.description = ConfigInteger(default=MovieList.HIDE_DESCRIPTION)
config.movielist.last_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.last_timer_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.videodirs = ConfigLocations(default=[resolveFilename(SCOPE_HDD)])
config.movielist.first_tags = ConfigText(default="")
config.movielist.second_tags = ConfigText(default="")
config.movielist.last_selected_tags = ConfigSet([], default=[])


def setPreferredTagEditor(te):
	global preferredTagEditor
	try:
		if preferredTagEditor == None:
			preferredTagEditor = te
			print "Preferred tag editor changed to ", preferredTagEditor
		else:
			print "Preferred tag editor already set to ", preferredTagEditor
			print "ignoring ", te
	except:
		preferredTagEditor = te
		print "Preferred tag editor set to ", preferredTagEditor

def getPreferredTagEditor():
	global preferredTagEditor
	return preferredTagEditor

setPreferredTagEditor(None)

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
		menu.extend([(p.description, boundFunction(self.execPlugin, p)) for p in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST)])

		if config.movielist.moviesort.value == MovieList.SORT_ALPHANUMERIC:
			menu.append((_("sort by date"), boundFunction(self.sortBy, MovieList.SORT_RECORDED)))
		else:
			menu.append((_("alphabetic sort"), boundFunction(self.sortBy, MovieList.SORT_ALPHANUMERIC)))
		
		menu.extend((
			(_("list style default"), boundFunction(self.listType, MovieList.LISTTYPE_ORIGINAL)),
			(_("list style compact with description"), boundFunction(self.listType, MovieList.LISTTYPE_COMPACT_DESCRIPTION)),
			(_("list style compact"), boundFunction(self.listType, MovieList.LISTTYPE_COMPACT)),
			(_("list style single line"), boundFunction(self.listType, MovieList.LISTTYPE_MINIMAL))
		))

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
		config.movielist.moviesort.value = newType
		self.csel.setSortType(newType)
		self.csel.reloadList()
		self.close()

	def listType(self, newType):
		config.movielist.listtype.value = newType
		self.csel.setListType(newType)
		self.csel.list.redrawList()
		self.close()

	def showDescription(self, newType):
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
			self.csel["list"].removeService(self.service)
			self.csel["freeDiskSpace"].update()
			self.close()

class SelectionEventInfo:
	def __init__(self):
		self["Service"] = ServiceEvent()
		self.list.connectSelChanged(self.__selectionChanged)
		self.timer = eTimer()
		self.timer.callback.append(self.updateEventInfo)
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

		self.tags = [ ]
		if selectedmovie:
			self.selected_tags = config.movielist.last_selected_tags.value
		else:
			self.selected_tags = None
		self.selected_tags_ele = None

		self.movemode = False
		self.bouquet_mark_edit = False

		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.updateHDDData)

		self["waitingtext"] = Label(_("Please wait... Loading list..."))

		# create optional description border and hide immediately
		self["DescriptionBorder"] = Pixmap()
		self["DescriptionBorder"].hide()

		if not fileExists(config.movielist.last_videodir.value):
			config.movielist.last_videodir.value = defaultMoviePath()
			config.movielist.last_videodir.save()
		self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + config.movielist.last_videodir.value)

		self["list"] = MovieList(None,
			config.movielist.listtype.value,
			config.movielist.moviesort.value,
			config.movielist.description.value)

		self.list = self["list"]
		self.selectedmovie = selectedmovie

		# Need list for init
		SelectionEventInfo.__init__(self)

		self["key_red"] = Button(_("All"))
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		self["freeDiskSpace"] = self.diskinfo = DiskInfo(config.movielist.last_videodir.value, DiskInfo.FREE, update=False)

		if config.usage.setup_level.index >= 2: # expert+
			self["InfobarActions"] = HelpableActionMap(self, "InfobarActions", 
				{
					"showMovies": (self.doPathSelect, _("select the movie path")),
				})


		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.doContext, _("menu")),
				"showEventInfo": (self.showEventInformation, _("show event details")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"red": (self.showAll, _("show all")),
				"green": (self.showTagsFirst, _("show first selected tag")),
				"yellow": (self.showTagsSecond, _("show second selected tag")),
				"blue": (self.showTagsSelect, _("show tag menu")),
			})

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"cancel": (self.abort, _("exit movielist")),
				"ok": (self.movieSelected, _("select movie")),
			})

		self.onShown.append(self.go)
		self.onLayoutFinish.append(self.saveListsize)
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

	def saveListsize(self):
			listsize = self["list"].instance.size()
			self.listWidth = listsize.width()
			self.listHeight = listsize.height()
			self.updateDescription()

	def updateHDDData(self):
 		self.reloadList(self.selectedmovie)
		self["waitingtext"].visible = False

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
		config.movielist.last_selected_tags.value = self.selected_tags
		config.movielist.moviesort.save()
		config.movielist.listtype.save()
		config.movielist.description.save()

	def getTagDescription(self, tag):
		# TODO: access the tag database
		return tag

	def updateTags(self):
		# get a list of tags available in this list
		self.tags = list(self["list"].tags)

		if not self.tags:
			# by default, we do not display any filtering options
			self.tag_first = ""
			self.tag_second = ""
		else:
			tmp = config.movielist.first_tags.value
			if tmp in self.tags:
				self.tag_first = tmp
			else:
				self.tag_first = "<"+_("Tag 1")+">"
			tmp = config.movielist.second_tags.value
			if tmp in self.tags:
				self.tag_second = tmp
			else:
				self.tag_second = "<"+_("Tag 2")+">"
		self["key_green"].text = self.tag_first
		self["key_yellow"].text = self.tag_second
		
		# the rest is presented in a list, available on the
		# fourth ("blue") button
		if self.tags:
			self["key_blue"].text = _("Tags")+"..."
		else:
			self["key_blue"].text = ""

	def setListType(self, type):
		self["list"].setListType(type)

	def setDescriptionState(self, val):
		self["list"].setDescriptionState(val)

	def setSortType(self, type):
		self["list"].setSortType(type)

	def reloadList(self, sel = None, home = False):
		if not fileExists(config.movielist.last_videodir.value):
			path = defaultMoviePath()
			config.movielist.last_videodir.value = path
			config.movielist.last_videodir.save()
			self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + path)
			self["freeDiskSpace"].path = path
		if sel is None:
			sel = self.getCurrent()
		self["list"].reload(self.current_ref, self.selected_tags)
		title = _("Recorded files...")
		if config.usage.setup_level.index >= 2: # expert+
			title += "  " + config.movielist.last_videodir.value
		if self.selected_tags is not None:
			title += " - " + ','.join(self.selected_tags)
		self.setTitle(title)
 		if not (sel and self["list"].moveTo(sel)):
			if home:
				self["list"].moveToIndex(0)
		self.updateTags()
		self["freeDiskSpace"].update()

	def doPathSelect(self):
		self.session.openWithCallback(
			self.gotFilename,
			MovieLocationBox,
			_("Please select the movie path..."),
			config.movielist.last_videodir.value
		)

	def gotFilename(self, res):
		if res is not None and res is not config.movielist.last_videodir.value:
			if fileExists(res):
				config.movielist.last_videodir.value = res
				config.movielist.last_videodir.save()
				self.current_ref = eServiceReference("2:0:1:0:0:0:0:0:0:0:" + res)
				self["freeDiskSpace"].path = res
				self.reloadList(home = True)
			else:
				self.session.open(
					MessageBox,
					_("Directory %s nonexistent.") % (res),
					type = MessageBox.TYPE_ERROR,
					timeout = 5
					)

	def showAll(self):
		self.selected_tags_ele = None
		self.selected_tags = None
		self.reloadList(home = True)

	def showTagsN(self, tagele):
		if not self.tags:
			self.showTagWarning()
		elif not tagele or (self.selected_tags and tagele.value in self.selected_tags) or not tagele.value in self.tags:
			self.showTagsMenu(tagele)
		else:
			self.selected_tags_ele = tagele
			self.selected_tags = set([tagele.value])
			self.reloadList(home = True)

	def showTagsFirst(self):
		self.showTagsN(config.movielist.first_tags)

	def showTagsSecond(self):
		self.showTagsN(config.movielist.second_tags)

	def showTagsSelect(self):
		self.showTagsN(None)

	def tagChosen(self, tag):
		if tag is not None:
			self.selected_tags = set([tag[0]])
			if self.selected_tags_ele:
				self.selected_tags_ele.value = tag[0]
				self.selected_tags_ele.save()
			self.reloadList(home = True)

	def showTagsMenu(self, tagele):
		self.selected_tags_ele = tagele
		list = [(tag, self.getTagDescription(tag)) for tag in self.tags ]
		self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select tag to filter..."), list = list)

	def showTagWarning(self):
		self.session.open(MessageBox, _("No tags are set on these movies."), MessageBox.TYPE_ERROR)
