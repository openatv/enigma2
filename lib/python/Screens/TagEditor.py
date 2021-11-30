from os.path import isdir, isfile

from enigma import eServiceCenter, eServiceReference, iDVBMetaFile, iServiceInformation

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.SelectionList import SelectionList
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import SCOPE_CONFIG, fileReadLines, fileWriteLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]


class TagManager():
	def __init__(self):
		self.fileTags = self.loadTags()
		self.tags = self.fileTags[:] if self.fileTags else []

	def loadTags(self):
		tags = []
		filename = resolveFilename(SCOPE_CONFIG, "movietags")
		tags = fileReadLines(filename, tags, source=MODULE_NAME)
		tags = [self.formatTag(x) for x in tags]
		while "" in tags:
			tags.remove("")
		tags.sort()
		print("[TagEditor] %d tags read from '%s'." % (len(tags), filename))
		return tags

	def saveTags(self):
		if self.tags != self.fileTags:
			filename = resolveFilename(SCOPE_CONFIG, "movietags")
			if fileWriteLines(filename, self.tags, source=MODULE_NAME):
				print("[TagEditor] %d tags written to '%s'." % (len(self.tags), filename))

	def getTags(self):
		return self.tags

	def getCount(self):
		return len(self.tags)

	def tagsChanged(self):
		return self.tags != self.fileTags

	def formatTag(self, tag):
		return tag.strip().replace(" ", "_")

	def displayTag(self, tag):
		return tag.replace("_", " ")

	def addTag(self, tag):
		tag = self.formatTag(tag)
		if tag not in self.tags:
			self.tags.append(tag)
			self.tags.sort()
		return tag

	def renameTag(self, oldTag, newTag):
		if oldTag in self.tags:
			self.deleteTag(oldTag)
		if newTag not in self.tags:
			newTag = self.addTag(newTag)
		return newTag

	def deleteTag(self, tag):
		if tag in self.tags:
			self.tags.remove(tag)

	def purgeTags(self):
		self.tags = []

	def resetTags(self):
		self.tags = self.fileTags
		return self.tags

	def verifyTags(self, tags):  # Helper method for timers to check that all tags are properly defined in the master tags list.
		for index, tag in enumerate(tags):
			if tag not in self.tags:
				self.tags = self.mergeTags(tags[index:])
				self.saveTagsFile(self.tags)
				print("[TagEditor] Tag verification resulted in a tag update.")
				return False
		print("[TagEditor] Tag verification completed.")
		return True

	def mergeTags(self, tags):  # Merge the provided tags into the master tags list.
		changed = False
		selfTags = self.tags
		for tag in tags:
			if tag not in selfTags:
				selfTags.append(tag)
				changed = True
		if changed:
			selfTags.sort()
		return selfTags


class TagEditor(Screen, HelpableScreen, TagManager):
	skin = """
	<screen name="TagEditor" title="Tag Editor" position="center,center" size="810,395" resolution="1280,720">
		<widget name="taglist" position="10,10" size="790,315" scrollbarMode="showOnDemand" transparent="1" />
		<widget source="key_red" render="Label" position="10,e-50" size="140,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_green" render="Label" position="160,e-50" size="140,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_yellow" render="Label" position="310,e-50" size="140,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_blue" render="Label" position="460,e-50" size="140,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_menu" render="Label" position="e-200,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session, tags=None, service=None, parent=None):
		Screen.__init__(self, session, parent=parent)
		HelpableScreen.__init__(self)
		TagManager.__init__(self)
		self.setTitle(_("Tag Editor"))
		if isinstance(service, eServiceReference):
			tags = eServiceCenter.getInstance().info(service).getInfoString(service, iServiceInformation.sTags)
			tags = tags.split(" ") if tags else []
		elif tags is None:
			tags = []
		elif isinstance(tags, list):
			pass
		elif isinstance(tags, str):
			tags = [x.strip() for x in tags.split(",")] if "," in tags else [tags]
		else:
			raise TypeError("[TagEditor] Error: Must be called with a service as a movie service reference or a tag list!")
		self.service = service
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "MenuActions"], {
			"cancel": (self.keyCancel, _("Cancel any changed tags and exit")),
			"save": (self.keySave, _("Save all changed tags and exit")),
			"ok": (self.toggleSelection, _("Toggle selection of the current tag")),
			"red": (self.keyCancel, _("Cancel any changed tags and exit")),
			"green": (self.keySave, _("Save all changed tags and exit")),
			"yellow": (self.addNewTag, _("Add a new tag")),
			"blue": (self.loadFromDisk, _("Load tags from the timer and recordings")),
			"menu": (self.showMenu, _("Display the tags context menu"))
		}, prio=0, description=_("Tag Editor Actions"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("New"))
		self["key_blue"] = StaticText(_("Load"))
		self["key_menu"] = StaticText(_("MENU"))
		self["taglist"] = SelectionList(enableWrapAround=True)
		self.tags = self.mergeTags(tags)
		self.updateMenuList(self.tags, extraSelected=tags)
		self.ghostList = tags[:]
		self.ghostTags = self.tags[:]

	def updateMenuList(self, tags, extraSelected=None):
		if extraSelected is None:
			extraSelected = []
		selectedTags = [x[1] for x in self["taglist"].getSelectionsList()] + extraSelected
		tags.sort()
		self["taglist"].setList([])
		for index, tag in enumerate(tags):
			self["taglist"].addSelection(self.displayTag(tag), tag, index, tag in selectedTags)

	def keyCancel(self):
		self.close(None)

	def keySave(self):
		if self.tagsChanged():
			self.saveTags()
		# self.close([x[1] for x in self["taglist"].getSelectionsList()])
		# The above code is suspended and the following code is temporary used until MovieSelection.py is updated/corrected to manage its own meta file.
		selectedtags = [x[1] for x in self["taglist"].getSelectionsList()]
		if self.service:
			self.setMovieTags(self.service, selectedtags)
		self.close(selectedtags)

	def toggleSelection(self):
		self["taglist"].toggleSelection()

	def loadFromDisk(self):
		tags = self.tags[:]
		self.foreachTimerTags(lambda t, tg: self.buildTags(tags, tg))
		self.foreachMovieTags(lambda r, tg: self.buildTags(tags, tg))
		self.updateMenuList(tags)
		self.tags = tags

	def buildTags(self, tagList, newTags):
		for tag in newTags:
			if tag not in tagList:
				tagList.append(tag)
	def showMenu(self):
		menu = [
			(_("Add new tag"), self.addNewTag),
			(_("Rename this tag"), self.renameOldTag),
			(_("Delete this tag"), self.removeTag),
			(_("Delete unused tags"), self.removeUnusedTags),
			(_("Delete all tags"), self.removeAllTags),
		]
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice:
			choice[1]()

	def addNewTag(self):
		self.session.openWithCallback(self.addNewTagCallback, VirtualKeyBoard, title=_("Please enter the new tag:"), windowTitle=_("Tag Editor"))

	def addNewTagCallback(self, tag):
		tags = self.tags
		if tag and tag not in tags:
			tag = tag and self.addTag(tag)
			self.tags = self.getTags()
			self.updateMenuList(self.tags, extraSelected=[tag])

	def renameOldTag(self):
		self.currentTag = self["taglist"].list[self["taglist"].getSelectedIndex()][0]
		self.session.openWithCallback(self.renameOldTagCallback, VirtualKeyBoard, title=_("Replace all '%s' tags with:\n(NOTE: 'Cancel' cannot undo this!)") % self.currentTag[1], text=self.currentTag[1], windowTitle=_("Tag Editor"))

	def renameOldTagCallback(self, tag):
		tag = tag and self.formatTag(tag)
		if tag and len(tag) and tag != self.currentTag[1]:
			currentTag = self.currentTag[1]
			tag = self.renameTag(currentTag, tag)
			self.foreachTimerTags(lambda t, tg: (currentTag in tg) and self.setTimerTags(t, self.listReplace(tg, currentTag, tag)))
			self.foreachMovieTags(lambda r, tg: (currentTag in tg) and self.setMovieTags(r, self.listReplace(tg, currentTag, tag)))
			self.listReplace(self.tags, currentTag, tag)
			self.listReplace(self.ghostTags, currentTag, tag)
			self.listReplace(self.ghostList, currentTag, tag)
			self.updateMenuList(self.tags, extraSelected=self.currentTag[3] and [tag] or [])

	def removeTag(self):
		self.currentTag = self["taglist"].list[self["taglist"].getSelectedIndex()][0]
		self.session.openWithCallback(self.removeTagCallback, MessageBox, _("Do you really want to delete all '%s' tags?\n(NOTE: 'Cancel' cannot undo this!)") % self.currentTag[1])

	def removeTagCallback(self, answer):
		if answer:
			currentTag = self.currentTag[1]
			self.deleteTag(currentTag)
			self.deleteTag(self.currentTag[1])
			self.foreachTimerTags(lambda t, tg: (currentTag in tg) and self.setTimerTags(t, self.listReplace(tg, currentTag)))
			self.foreachMovieTags(lambda r, tg: (currentTag in tg) and self.setMovieTags(r, self.listReplace(tg, currentTag)))
			self.listReplace(self.tags, currentTag)
			self.listReplace(self.ghostTags, currentTag)
			self.listReplace(self.ghostList, currentTag)
			self.updateMenuList(self.tags)

	def removeUnusedTags(self):
		tags = [x[1] for x in self["taglist"].getSelectionsList()]
		self.foreachTimerTags(lambda t, tg: self.buildTags(tags, tg))
		self.foreachMovieTags(lambda r, tg: self.buildTags(tags, tg))
		self.updateMenuList(tags)
		self.tags = tags

	def removeAllTags(self):
		self.session.openWithCallback(self.removeAllTagsCallback, MessageBox, _("Do you really want to delete all tags?\n(Note that 'Cancel' will not undo this!)"))

	def removeAllTagsCallback(self, answer):
		if answer:
			self.foreachTimerTags(lambda t, tg: tg and self.setTimerTags(t, []))
			self.foreachMovieTags(lambda r, tg: tg and self.setMovieTags(r, []))
			self.purgeTags()
			self.tags = []
			self.ghostTags = []
			self.ghostList = []
			self.updateMenuList(self.tags)

	def listReplace(self, tagList, fromTag, toTag=None):
		if fromTag in tagList:
			tagList.remove(fromTag)
			if toTag is not None and toTag not in tagList:
				tagList.append(toTag)
				tagList.sort()
		return tagList

	def foreachTimerTags(self, method):
		self.timerDirty = False
		for timer in self.session.nav.RecordTimer.timer_list + self.session.nav.RecordTimer.processed_timers:
			if timer.tags:
				method(timer, timer.tags[:])
		if self.timerDirty:
			self.session.nav.RecordTimer.saveTimer()

	def setTimerTags(self, timer, tags):
		if timer.tags != tags:
			timer.tags = tags
			self.timerDirty = True

	def foreachMovieTags(self, method):
		serviceHandler = eServiceCenter.getInstance()
		for dir in config.movielist.videodirs.value:
			if isdir(dir):
				movieList = serviceHandler.list(eServiceReference("2:0:1:0:0:0:0:0:0:0:%s" % dir))
				if movieList is None:
					continue
				while True:
					serviceRef = movieList.getNext()
					if not serviceRef.valid():
						break
					if (serviceRef.flags & eServiceReference.mustDescent):
						continue
					info = serviceHandler.info(serviceRef)
					if info is None:
						continue
					tags = info.getInfoString(serviceRef, iServiceInformation.sTags).split(" ")
					if not tags or tags == [""]:
						continue
					method(serviceRef, tags)

	def setMovieTags(self, serviceRef, tags):
		filename = serviceRef.getPath()
		filename = "%s.meta" % filename if filename.endswith(".ts") else "%s.ts.meta" % filename
		if isfile(filename):
			lines = fileReadLines(filename, source=MODULE_NAME)
			idTags = iDVBMetaFile.idTags
			if len(lines) > idTags:
				tagList = " ".join(tags)
				if tagList != lines[idTags]:
					lines[idTags] = tagList
					fileWriteLines(filename, lines, source=MODULE_NAME)


tagManager = TagManager()
