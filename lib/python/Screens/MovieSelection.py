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
import os

config.movielist = ConfigSubsection()
config.movielist.moviesort = ConfigInteger(default=MovieList.SORT_RECORDED)
config.movielist.listtype = ConfigInteger(default=MovieList.LISTTYPE_COMPACT)
config.movielist.description = ConfigInteger(default=MovieList.HIDE_DESCRIPTION)
config.movielist.last_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.last_timer_videodir = ConfigText(default=resolveFilename(SCOPE_HDD))
config.movielist.videodirs = ConfigLocations(default=[resolveFilename(SCOPE_HDD)])
#config.movielist.first_tags = ConfigText(default="")
#config.movielist.second_tags = ConfigText(default="")
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

		menu = [(_("delete..."), self.delete), (_("Move"), self.moveMovie)]
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
		self.csel.delete()
		self.close()

	def moveMovie(self):
		self.csel.moveMovie()
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

		self.tags = {}
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

		self["key_red"] = Button(_("Delete"))
		self["key_green"] = Button(_("Move"))
		self["key_yellow"] = Button(_("Location"))
		self["key_blue"] = Button(_("Tags"))

		self["freeDiskSpace"] = self.diskinfo = DiskInfo(config.movielist.last_videodir.value, DiskInfo.FREE, update=False)

		#if config.usage.setup_level.index >= 2: # expert? nah.
		self["InfobarActions"] = HelpableActionMap(self, "InfobarActions", 
			{
				"showMovies": (self.doPathSelect, _("select the movie path")),
				#"showTv": (self.goHome, _("Go to default movie dir")),
			})


		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.doContext, _("menu")),
				"showEventInfo": (self.showEventInformation, _("show event details")),
			})

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
				"red": (self.delete, _("delete...")),
				"green": (self.moveMovie, _("Move to other directory")),
				"yellow": (self.showBookmarks, _("select the movie path")),
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
			if current.flags & eServiceReference.mustDescent:
				self.gotFilename(current.getPath())
			else:
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
		self.tags = self["list"].tags

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
			self.selected_tags = self.tags[tagele.value]
			self.reloadList(home = True)

	def showTagsFirst(self):
		self.showTagsN(config.movielist.first_tags)

	def showTagsSecond(self):
		self.showTagsN(config.movielist.second_tags)

	def showTagsSelect(self):
		self.showTagsN(None)

	def tagChosen(self, tag):
		if tag is not None:
			if tag[1] is None: # all
				self.showAll()
				return
			# TODO: Some error checking maybe, don't wanna crash on KeyError
			self.selected_tags = self.tags[tag[0]]
			if self.selected_tags_ele:
				self.selected_tags_ele.value = tag[0]
				self.selected_tags_ele.save()
			self.reloadList(home = True)

	def showTagsMenu(self, tagele):
		self.selected_tags_ele = tagele
		lst = [(_("show all tags"), None)] + [(tag, self.getTagDescription(tag)) for tag in self.tags]
		self.session.openWithCallback(self.tagChosen, ChoiceBox, title=_("Please select tag to filter..."), list = lst)

	def showTagWarning(self):
		self.session.open(MessageBox, _("No tags are set on these movies."), MessageBox.TYPE_ERROR)

	def selectMovieLocation(self, title, callback):
		paths = list(config.movielist.videodirs.value)
		moviePath = resolveFilename(SCOPE_HDD)
		for fn in os.listdir(moviePath):
			pn = os.path.join(moviePath, fn)
			if os.path.isdir(pn):
				if not pn.endswith('/'):
					pn += '/'
				if pn not in paths:
					paths.append(pn)
		bookmarks = [(d,d) for d in paths]
		self.session.openWithCallback(callback, ChoiceBox, title=title, list = bookmarks)

	def showBookmarks(self):
		self.selectMovieLocation(title=_("Please select the movie path..."), callback=self.bookmarkChosen)

	def bookmarkChosen(self, bookmark):
		if bookmark:
			self.gotFilename(bookmark[0])

	def moveMovie(self):
		current = self.getCurrent()
		if (current is not None) and (not current.flags & eServiceReference.mustDescent):
			serviceHandler = eServiceCenter.getInstance()
			info = serviceHandler.info(current)
			name = info and info.getName(current) or _("this recording")
			self.selectMovieLocation(title=_("Select destination for:") + " " + name, callback=self.gotMoveMovieDest)

	def gotMoveMovieDest(self, choice):
		if not choice:
			return
		dest = os.path.normpath(choice[0])
		print "[Movie] Moving to:", dest
		current = self.getCurrent()
		src = current.getPath()
		srcPath, srcName = os.path.split(src)
		if os.path.normpath(srcPath) == dest:
			# move file to itself is allowed, so we have to check it
			print "[Movie] Refusing to move to the same directory", srcPath
			return
		srcBase = os.path.splitext(src)[0]
		baseName = os.path.split(srcBase)[1]
		moveList = [(src, os.path.join(dest, srcName))]
		eitName =  srcBase + '.eit' 
		if os.path.exists(eitName):
			moveList.append((eitName, os.path.join(dest, baseName+'.eit')))
		baseName = os.path.split(src)[1]
		for ext in ('.ap', '.cuts', '.meta', '.sc'):
			candidate = src + ext
			if os.path.exists(candidate):
				moveList.append((candidate, os.path.join(dest, baseName+ext)))
		# Try to "atomically" move these files
		movedList = []
		try:
			for item in moveList:
				print "[MOVE]", item[0], "->", item[1]
				os.rename(item[0], item[1])
				movedList.append(item)
			self["list"].removeService(current)
		except Exception, e:
			print "[MovieSelection] Failed move:", e
			for item in movedList:
				try:
					os.rename(item[1], item[0])
				except:
					print "[MovieSelection] Failed to undo move:", item
			# this will crash (RuntimeError: modal open are allowed only from a screen which is modal)
			# self.session.openWithCallback(self.noop, MessageBox, str(e), MessageBox.TYPE_ERROR)			

	def delete(self):
		current = self.getCurrent()
		if (current is not None) and (not current.flags & eServiceReference.mustDescent):
			serviceHandler = eServiceCenter.getInstance()
			offline = serviceHandler.offlineOperations(current)
			info = serviceHandler.info(current)
			name = info and info.getName(current) or _("this recording")
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
			return

		current = self.getCurrent()
		if current is None:
			# huh?
			return
		serviceHandler = eServiceCenter.getInstance()
		offline = serviceHandler.offlineOperations(current)
		result = False
		if offline is not None:
			# really delete!
			if not offline.deleteFromDisk(0):
				result = True

		if result == False:
			self.session.open(MessageBox, _("Delete failed!"), MessageBox.TYPE_ERROR)
		else:
			self["list"].removeService(current)
			self["freeDiskSpace"].update()

	def noop(self):
		pass
