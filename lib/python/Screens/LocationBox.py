from os import lstat, sep, statvfs
from os.path import exists, isdir, join, splitext

from enigma import eTimer

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.FileList import FileList
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.BoundFunction import boundFunction
from Tools.Conversions import scaleNumber
from Tools.Directories import createDir, removeDir, renameDir
from Tools.NumericalTextInput import NumericalTextInput


DEFAULT_INHIBIT_DIRECTORIES = ("/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/picon", "/piconlcd", "/proc", "/run", "/sbin", "/share", "/sys", "/tmp", "/usr", "/var")
defaultInhibitDirs = list(DEFAULT_INHIBIT_DIRECTORIES)
DEFAULT_INHIBIT_DEVICES = []
for dir in DEFAULT_INHIBIT_DIRECTORIES + ("/", "/media"):
	if isdir(dir):
		device = lstat(dir).st_dev
		if device not in DEFAULT_INHIBIT_DEVICES:
			DEFAULT_INHIBIT_DEVICES.append(device)
DEFAULT_INHIBIT_DEVICES = tuple(DEFAULT_INHIBIT_DEVICES)


# Generic screen to select a path/filename combination.
#
class LocationBox(Screen, NumericalTextInput):
	"""Simple Class similar to MessageBox / ChoiceBox but used to choose a directory/pathname combination"""

	skin = """
	<screen name="LocationBox" position="center,center" size="1000,570" resolution="1280,720">
		<widget name="text" position="0,0" size="e,25" font="Regular;20" transparent="1" valign="center" />
		<widget name="targetfreespace" position="0,0" size="e,25" font="Regular;20" halign="right" transparent="1" valign="center" />
		<widget name="target" position="0,25" size="e,25" font="Regular;20" transparent="1" valign="center" />
		<widget name="fileheading" position="0,60" size="e,25" backgroundColor="#00ffffff" font="Regular;20" foregroundColor="#00000000" valign="center" />
		<widget name="filelist" position="0,85" size="e,245" font="Regular;20" itemHeight="25" scrollbarMode="showOnDemand" transparent="1" />
		<widget name="quickselect" position="0,85" size="e,245" font="Regular;100" foregroundColor="#0000ffff" halign="center" transparent="1" valign="center" zPosition="+1" />
		<widget name="bookmarkheading" position="0,345" size="e,25" backgroundColor="#00ffffff" font="Regular;20" foregroundColor="#00000000" valign="center" />
		<widget name="bookmarklist" position="0,370" size="e,150" font="Regular;20" itemHeight="25" scrollbarMode="showOnDemand" transparent="1" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-170,e-40" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, text="", filename="", currDir=None, bookmarks=None, windowTitle=_("Select Location"), minFree=None, autoAdd=False, editDir=False, inhibitDirs=None, inhibitMounts=None):
		Screen.__init__(self, session, mandatoryWidgets=["fileheading", "quickselect"], enableHelp=True)
		NumericalTextInput.__init__(self, handleTimeout=False, mode="SearchUpper")
		self.text = text
		self.filename = filename  # Filename is a proposed filename to be created/used by the *calling* code, it is not created here!
		self.bookmarks = bookmarks
		self.bookmarksList = bookmarks and bookmarks.value[:] or []
		self.minFree = minFree
		self.autoAdd = autoAdd
		self.editDir = editDir
		if not inhibitDirs:
			inhibitDirs = []
		if not inhibitMounts:
			inhibitMounts = []
		self["text"] = Label(text)
		self["target"] = Label()
		self["targetfreespace"] = Label()
		self["fileheading"] = Label(_("Directories"))
		self["filelist"] = FileList(currDir, showDirectories=True, showFiles=False, inhibitMounts=inhibitMounts, inhibitDirs=inhibitDirs, showCurrentDirectory=True)
		self["quickselect"] = Label("")
		self["quickselect"].visible = False
		self["bookmarkheading"] = Label(_("Bookmarks"))
		self["bookmarklist"] = MenuList(self.bookmarksList)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText(_("Remove Bookmark"))
		self["key_blue"] = StaticText(_("Rename"))
		self.currList = None

		class LocationBoxActionMap(HelpableActionMap):  # Custom action handler.
			def __init__(self, parent, context, actions=None, prio=0, description=None):
				if not actions:
					actions = {}
				HelpableActionMap.__init__(self, parent, context, actions, prio, description)
				self.box = parent

			def action(self, contexts, action):
				self.box.timeout(force=True)  # Reset QuickSelect.
				return HelpableActionMap.action(self, contexts, action)

		def getOkHelpText():
			return {
				"filelist": _("Navigate to the selected directory"),
				"bookmarklist": _("Select the current bookmarked location and exit")
			}.get(self.currList, _("Help text uninitialized"))

		def getYellowHelpText():
			return {
				"filelist": _("Add the current directory as a bookmark"),
				"bookmarklist": _("Remove the current bookmark")
			}.get(self.currList, _("Help text uninitialized"))

		self["actions"] = LocationBoxActionMap(self, ["OkCancelActions", "ColorActions", "MenuActions", "NavigationActions"], {  # Actions that will reset QuickSelect.
			"cancel": (self.keyCancel, _("Cancel selection and exit")),
			"ok": (self.keyOk, getOkHelpText),
			"menu": (self.keyShowMenu, _("Display context menu")),
			"red": (self.keyCancel, _("Cancel selection and exit")),
			"green": (self.keySelect, _("Use the current selection and exit")),
			"yellow": (self.addRemoveBookmark, getYellowHelpText),
			"top": (self.keyGoTop, _("Move to first line / screen in the panel")),
			"pageUp": (self.keyGoPageUp, _("Move up a screen in the panel")),
			"up": (self.keyGoLineUp, _("Move up a line in the panel")),
			"down": (self.keyGoLineDown, _("Move down a line in the panel")),
			"pageDown": (self.keyGoPageDown, _("Move down a screen in the panel")),
			"bottom": (self.keyGoBottom, _("Move to last line / screen in the panel"))
		}, prio=0, description=_("Location Selection Actions"))
		self["panelActions"] = LocationBoxActionMap(self, ["NavigationActions"], {  # Actions that will reset QuickSelect.
			"left": (self.switchToFileList, _("Switch to file list panel")),
			"right": (self.switchToBookmarkList, _("Switch to bookmarks panel")),
		}, prio=0, description=_("Location Selection Actions"))
		self["panelActions"].setEnabled(True)
		self["moveUpAction"] = HelpableActionMap(self, ["NavigationActions"], {  # Actions that will reset QuickSelect.
			"first": (self.keyMoveBookmarkUp, _("Move the current bookmark up"))
		}, prio=0, description=_("Bookmark Sequence Actions"))
		self["moveUpAction"].setEnabled(True)
		self["moveDownAction"] = HelpableActionMap(self, ["NavigationActions"], {  # Actions that will reset QuickSelect.
			"last": (self.keyMoveBookmarkDown, _("Move the current bookmark down"))
		}, prio=0, description=_("Bookmark Sequence Actions"))
		self["moveDownAction"].setEnabled(True)
		self["renameActions"] = LocationBoxActionMap(self, ["ColorActions"], {  # Actions that will reset QuickSelect.
			"blue": (self.renameProposedFile, _("Rename the proposed file to be created"))
		}, prio=0, description=_("Location Selection Actions"))
		self["renameActions"].setEnabled(True)
		smsMsg = _("SMS style QuickSelect location selection")
		self["numberActions"] = HelpableNumberActionMap(self, "NumberActions", {  # Action used by QuickSelect.
			"1": (self.keyNumberGlobal, smsMsg),
			"2": (self.keyNumberGlobal, smsMsg),
			"3": (self.keyNumberGlobal, smsMsg),
			"4": (self.keyNumberGlobal, smsMsg),
			"5": (self.keyNumberGlobal, smsMsg),
			"6": (self.keyNumberGlobal, smsMsg),
			"7": (self.keyNumberGlobal, smsMsg),
			"8": (self.keyNumberGlobal, smsMsg),
			"9": (self.keyNumberGlobal, smsMsg),
			"0": (self.keyNumberGlobal, smsMsg)
		}, prio=0, description=_("QuickSelect Actions"))
		self["numberActions"].setEnabled(True)
		self.setTitle(windowTitle)
		self.timer = eTimer()  # Initialize QuickSelect timer.
		self.timer.callback.append(self.timeout)
		self.timerType = 0
		self.quickSelect = ""
		self.quickSelectPos = -1
		self.onLayoutFinish.append(self.layoutFinished)

	def __repr__(self):
		return "%s(%s)" % (type(self), self.text)

	def layoutFinished(self):
		self["filelist"].enableAutoNavigation(False)  # Override listbox navigation.
		self["bookmarklist"].enableAutoNavigation(False)  # Override listbox navigation.
		if self.bookmarksList:
			self.switchToBookmarkList()
			directory = self["filelist"].getCurrentDirectory()
			if directory in self.bookmarksList:
				self["bookmarklist"].setCurrentIndex(self.bookmarksList.index(directory))
		else:
			self.switchToFileList()
		self.updateState()
		self.showHideRename()

	def updateState(self):
		directory = self.getSelectedDirectory()
		if self.currList == "filelist" and self["filelist"].getPath() is None:
			self["target"].setText(_("List of Storage Devices"))
			self["targetfreespace"].setText("")
		elif directory:  # Write combination of directory & filename when directory is valid.
			self["target"].setText("".join((directory, self.filename)))
			try:
				stat = statvfs(directory)
				free = f"{scaleNumber(stat.f_bfree * stat.f_frsize, format="%0.f")} {_("Free")}"
			except OSError as err:
				print("[LocationBox] Error %d: Unable to get '%s' status!  (%s)" % (err.errno, directory, err.strerror))
				free = ""
			self["targetfreespace"].setText(free)
		else:  # Display a warning otherwise.
			self["target"].setText(_("Invalid location!"))
			self["targetfreespace"].setText("")
		if self.currList == "filelist":
			if self.bookmarksList:
				self["panelActions"].setEnabled(True)
			self["key_yellow"].setText(_("Add Bookmark"))
			self["moveUpAction"].setEnabled(False)
			self["moveDownAction"].setEnabled(False)
		else:
			if self.bookmarksList:
				self["panelActions"].setEnabled(True)
				self["key_yellow"].setText(_("Remove Bookmark"))
				count = self["bookmarklist"].count()
				if count > 1:
					index = self["bookmarklist"].getCurrentIndex()
					self["moveUpAction"].setEnabled(index > 0)
					self["moveDownAction"].setEnabled(index < count - 1)
			else:
				self["panelActions"].setEnabled(False)
				self.switchToFileList()

	def getSelectedDirectory(self):
		if self.currList == "filelist":
			return self["filelist"].getPath() if self["filelist"].getPath() else self["filelist"].getCurrentDirectory()
		else:
			return self["bookmarklist"].getCurrent()

	def showHideRename(self):
		if self.filename:  # Don't allow renaming when filename is empty.
			self["key_blue"].setText(_("Rename"))
			self["renameActions"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["renameActions"].setEnabled(False)

	def keyCancel(self):
		self.disableTimer()
		self.close(None)

	def keyOk(self):
		if self.currList == "filelist":
			if self["filelist"].canDescent():
				self["filelist"].descent()
				self.updateState()
		else:
			self.keySelect()

	def keySelect(self):
		if self.currList == "filelist" and self["filelist"].getPath() is None:
			self.disableTimer()
			self.close("")
		else:
			currentFolder = self.getSelectedDirectory()
			if currentFolder is not None:  # Do nothing unless current directory is valid.
				if self.minFree is not None:  # Check if we need to have a minimum of free space available.
					try:
						status = statvfs(currentFolder)  # Try to read file system status.
						if (status.f_bavail * status.f_bsize) / 1000000 > self.minFree:
							return self.keySelectCallback(True)  # Automatically confirm if we have enough free disk space available.
					except OSError as err:
						print("[LocationBox] Error %d: Unable to get '%s' status!  (%s)" % (err.errno, currentFolder, err.strerror))
					self.session.openWithCallback(self.keySelectCallback, MessageBox, _("There might not be enough space on the selected partition. Do you really want to continue?"), type=MessageBox.TYPE_YESNO)
				else:  # No minimum free space means we can safely close.
					self.keySelectCallback(True)

	def keySelectCallback(self, answer):
		if answer:
			answer = self.getSelectedDirectory()
			if self.bookmarks:
				if self.autoAdd and answer not in self.bookmarksList:
					self.bookmarksList.insert(0, self.getSelectedDirectory())
				if self.bookmarksList != self.bookmarks.value:
					self.bookmarks.value = self.bookmarksList
					self.bookmarks.save()
			self.disableTimer()
			self.close(answer)

	def keyShowMenu(self):
		if self.bookmarks:
			if self.currList == "filelist":
				menu = [
					(_("Switch To Bookmarks Panel"), self.switchToBookmarkList),
					(_("Add Bookmark"), self.addRemoveBookmark),
					(_("Reload Bookmarks"), self.reloadBookmarks)
				]
				if self.editDir:
					menu.extend((
						(_("Create Directory"), self.createDirectory),
						(_("Rename Directory"), self.renameDirectory),
						(_("Delete Directory"), self.deleteDirectory)
					))
			else:
				menu = (
					(_("Switch To File List Panel"), self.switchToFileList),
					(_("Remove Bookmark"), self.addRemoveBookmark),
					(_("Sort Bookmarks"), self.sortBookmarks),
					(_("Reload Bookmarks"), self.reloadBookmarks)
				)
			self.session.openWithCallback(self.keyShowMenuCallback, ChoiceBox, title="Location Box Context Menu", list=menu)

	def keyShowMenuCallback(self, choice):
		if choice:
			choice[1]()

	def switchToFileList(self):
		self.currList = "filelist"
		self["filelist"].selectionEnabled(True)
		self["bookmarklist"].selectionEnabled(False)
		self["numberActions"].setEnabled(True)
		self.updateState()

	def switchToBookmarkList(self):
		self.currList = "bookmarklist"
		self["filelist"].selectionEnabled(False)
		self["bookmarklist"].selectionEnabled(True)
		self["numberActions"].setEnabled(False)
		self.updateState()

	def addRemoveBookmark(self):
		current = self.getSelectedDirectory()
		if self.currList == "filelist":  # Add bookmark.
			if current not in self.bookmarksList:
				self.bookmarksList.insert(0, current)
				self["bookmarklist"].setList(self.bookmarksList)
				self.updateState()
		else:  # Remove bookmark.
			self.session.openWithCallback(boundFunction(self.removeBookmarkCallback, current), MessageBox, _("Do you really want to remove your bookmark for '%s'?") % current)

	def removeBookmarkCallback(self, bookmark, answer):
		if answer and bookmark in self.bookmarksList:
			self.bookmarksList.remove(bookmark)
			self["bookmarklist"].setList(self.bookmarksList)
			self.updateState()

	def sortBookmarks(self):
		bookmark = self["bookmarklist"].getCurrent()
		self.bookmarksList.sort()
		self["bookmarklist"].setList(self.bookmarksList)
		self["bookmarklist"].setCurrentIndex(self.bookmarksList.index(bookmark))
		self.updateState()

	def reloadBookmarks(self):
		self.bookmarksList = self.bookmarks and self.bookmarks.value[:] or []
		self["bookmarklist"].setList(self.bookmarksList)
		self.updateState()

	def createDirectory(self):
		if self["filelist"].getCurrentDirectory():
			self.session.openWithCallback(self.createDirCallback, VirtualKeyBoard, title=_("Please enter a name for the new directory:"), text="")

	def createDirCallback(self, directory):
		if directory:
			path = join(self["filelist"].getCurrentDirectory(), directory)
			if not exists(path):
				if not createDir(path):
					self.session.open(MessageBox, _("Error: Creating directory '%s' failed!") % path, type=MessageBox.TYPE_ERROR, timeout=5)
				self["filelist"].refresh()
			else:
				self.session.open(MessageBox, _("Error: The path '%s' already exists!") % path, type=MessageBox.TYPE_ERROR, timeout=5)

	def renameDirectory(self):
		directory = self["filelist"].getCurrentDirectory()
		if isdir(directory):
			name = directory[:-1].split(sep)[-1]  # Extract the directory name, not the absolute path.
			self.session.openWithCallback(boundFunction(self.renameDirectoryCallback, directory), VirtualKeyBoard, title=_("Enter new directory name:"), text=name)
		else:
			self.session.open(MessageBox, _("Error: Invalid directory '%s' selected!") % directory, type=MessageBox.TYPE_ERROR, timeout=5)

	def renameDirectoryCallback(self, directory, newName):
		if newName:
			path = join(self["filelist"].getCurrentDirectory(), newName)
			if exists(path):
				self.session.open(MessageBox, _("Error: File or directory '%s' already exists!") % path, type=MessageBox.TYPE_ERROR, timeout=5)
			elif renameDir(directory, path):
				self["filelist"].refresh()
			else:
				self.session.open(MessageBox, _("Error: Unable to rename directory '%s' to '%s'!") % (directory, path), type=MessageBox.TYPE_ERROR, timeout=5)

	def deleteDirectory(self):
		directory = self["filelist"].getCurrentDirectory()
		if isdir(directory):
			self.session.openWithCallback(boundFunction(self.deleteDirectoryCallback, directory), MessageBox, _("Do you really want to remove directory '%s' from the disk?") % directory, type=MessageBox.TYPE_YESNO)
		else:
			self.session.open(MessageBox, _("Error: Invalid directory '%s' selected!") % directory, type=MessageBox.TYPE_ERROR, timeout=5)

	def deleteDirectoryCallback(self, directory, answer):
		if answer:
			if not removeDir(directory):
				self.session.open(MessageBox, _("Error: Removing directory '%s' failed! (Maybe the directory is not empty.)") % directory, type=MessageBox.TYPE_ERROR, timeout=5)
			else:
				self["filelist"].refresh()
				self.removeBookmarkCallback(directory, True)
				values = self.bookmarks and self.bookmarks.value
				if values and directory in values:
					values.remove(directory)
					self.bookmarks.value = values
					self.bookmarks.save()

	def keyGoTop(self):
		self[self.currList].goTop()
		self.updateState()

	def keyGoPageUp(self):
		self[self.currList].goPageUp()
		self.updateState()

	def keyGoLineUp(self):
		self[self.currList].goLineUp()
		self.updateState()

	def keyGoLineDown(self):
		self[self.currList].goLineDown()
		self.updateState()

	def keyGoPageDown(self):
		self[self.currList].goPageDown()
		self.updateState()

	def keyGoBottom(self):
		self[self.currList].goBottom()
		self.updateState()

	def renameProposedFile(self):
		filename = splitext(self.filename)[0]
		self.session.openWithCallback(self.renameFileCallback, VirtualKeyBoard, title=_("Please enter a new filename, the extension may not be changed:"), text=filename)

	def renameProposedFileCallback(self, filename):
		if filename is not None:
			if len(filename):
				extension = splitext(self.filename)[1]
				self.filename = "%s%s" % (filename, extension)
				self.updateState()
			else:
				self.session.open(MessageBox, _("Error: An empty filename is illegal!"), type=MessageBox.TYPE_ERROR, timeout=5)

	def keyMoveBookmarkUp(self):
		self.moveBookmark(-1)

	def keyMoveBookmarkDown(self):
		self.moveBookmark(+1)

	def moveBookmark(self, direction):
		index = self["bookmarklist"].getCurrentIndex() + direction
		self.bookmarksList.insert(index, self.bookmarksList.pop(index - direction))
		self["bookmarklist"].setList(self.bookmarksList)
		self["bookmarklist"].setCurrentIndex(index)
		self.updateState()

	def keyNumberGlobal(self, digit):
		self.timer.stop()
		if self.lastKey != digit:  # Is this a different digit?
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its keychange.
			self.selectByStart()
			self.quickSelectPos += 1
		char = self.getKey(digit)  # Get char and append to text.
		self.quickSelect = "%s%s" % (self.quickSelect[:self.quickSelectPos], str(char))
		self["quickselect"].setText(self.quickSelect)
		self["quickselect"].visible = True
		self.timerType = 0
		self.timer.start(1000, True)  # Allow 1 second to select the desired character for the QuickSelect text.

	def timeout(self, force=False):
		if not force and self.timerType == 0:
			self.selectByStart()
			self.timerType = 1
			self.timer.start(2000, True)  # Allow 2 seconds before reseting the QuickSelect text.
		else:  # Timeout QuickSelect
			self.timer.stop()
			self.quickSelect = ""
			self.quickSelectPos = -1
		self.lastKey = -1  # Finalize current character.

	def selectByStart(self):  # Try to select what was typed so far.
		currentDir = self["filelist"].getCurrentDirectory()
		if currentDir and self.quickSelect:  # Don't try to select if there is no directory or QuickSelect text.
			self["quickselect"].visible = False
			self["quickselect"].setText("")
			pattern = join(currentDir, self.quickSelect).lower()
			files = self["filelist"].getFileList()  # Files returned by getFileList() are absolute paths.
			for index, file in enumerate(files):
				if file[0][0] and file[0][0].lower().startswith(pattern):  # Select first file starting with case insensitive QuickSelect text.
					self["filelist"].setCurrentIndex(index)
					self.updateState()
					break

	def disableTimer(self):
		self.timer.stop()
		self.timer.callback.remove(self.timeout)


class MovieLocationBox(LocationBox):
	def __init__(self, session, text, currDir, minFree=None):
		LocationBox.__init__(
			self,
			session,
			text=text,
			# filename="",
			currDir=currDir,
			bookmarks=config.movielist.videodirs,
			windowTitle=_("Select Media Location"),
			minFree=minFree,
			autoAdd=True,
			editDir=True,
			inhibitDirs=DEFAULT_INHIBIT_DIRECTORIES,
			# inhibitMounts=None
		)
		self.skinName = ["MovieLocationBox", "LocationBox"]


class PlaybackLocationBox(LocationBox):
	def __init__(self, session):
		LocationBox.__init__(
			self,
			session,
			text=_("What do you want to set as the default movie location?"),
			# filename="",
			currDir=config.usage.default_path.value,
			bookmarks=config.movielist.videodirs,
			windowTitle=_("Select Playback Location"),
			# minFree=None,
			autoAdd=True,
			editDir=True,
			inhibitDirs=DEFAULT_INHIBIT_DIRECTORIES,
			# inhibitMounts=None
		)
		self.skinName = ["PlaybackLocationBox", "LocationBox"]


class TimeshiftLocationBox(LocationBox):
	def __init__(self, session):
		LocationBox.__init__(
			self,
			session,
			text=_("Where do you want to save temporary time shift recordings?"),
			# filename="",
			currDir=config.timeshift.path.value,
			bookmarks=config.timeshift.allowedPaths,
			windowTitle=_("Select Time Shift Location"),
			minFree=1024,  # The same minFree requirement is hard-coded in servicedvb.cpp.
			autoAdd=True,
			editDir=True,
			inhibitDirs=DEFAULT_INHIBIT_DIRECTORIES,
			# inhibitMounts=None
		)
		self.skinName = ["TimeshiftLocationBox", "LocationBox"]
