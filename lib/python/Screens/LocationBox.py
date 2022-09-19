from os import stat, statvfs
from os.path import isdir, join as pathjoin

from enigma import eTimer

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import config
from Components.FileList import FileList
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction
from Tools.Directories import createDir, pathExists, removeDir
from Tools.NumericalTextInput import NumericalTextInput


DEFAULT_INHIBIT_DIRECTORIES = ("/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/picon", "/piconlcd", "/proc", "/run", "/sbin", "/share", "/sys", "/tmp", "/usr", "/var")
defaultInhibitDirs = list(DEFAULT_INHIBIT_DIRECTORIES)
DEFAULT_INHIBIT_DEVICES = []
for dir in DEFAULT_INHIBIT_DIRECTORIES + ("/", "/media"):
	if isdir(dir):
		device = stat(dir).st_dev
		if device not in DEFAULT_INHIBIT_DEVICES:
			DEFAULT_INHIBIT_DEVICES.append(device)
DEFAULT_INHIBIT_DEVICES = tuple(DEFAULT_INHIBIT_DEVICES)


# Generic screen to select a path/filename combination.
#
class LocationBox(Screen, NumericalTextInput, HelpableScreen):
	"""Simple Class similar to MessageBox / ChoiceBox but used to choose a folder/pathname combination"""

	def __init__(self, session, text="", filename="", currDir=None, bookmarks=None, userMode=False, windowTitle=_("Select Location"), minFree=None, autoAdd=False, editDir=False, inhibitDirs=None, inhibitMounts=None):
		Screen.__init__(self, session)
		NumericalTextInput.__init__(self, handleTimeout=False)
		HelpableScreen.__init__(self)
		if not inhibitDirs:
			inhibitDirs = []
		if not inhibitMounts:
			inhibitMounts = []
		self.setUseableChars("1234567890abcdefghijklmnopqrstuvwxyz")
		self.qs_timer = eTimer()
		self.qs_timer.callback.append(self.timeout)
		self.qs_timer_type = 0
		self.curr_pos = -1
		self.quickselect = ""
		self["text"] = Label(text)
		self["textbook"] = Label(_("Bookmarks"))
		self.text = text
		self.filename = filename
		self.minFree = minFree
		self.realBookmarks = bookmarks
		self.bookmarks = bookmarks and bookmarks.value[:] or []
		self.userMode = userMode
		self.autoAdd = autoAdd
		self.editDir = editDir
		self.inhibitDirs = inhibitDirs
		self["filelist"] = FileList(currDir, showDirectories=True, showFiles=False, inhibitMounts=inhibitMounts, inhibitDirs=inhibitDirs)
		self["booklist"] = MenuList(self.bookmarks)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Rename"))
		self["key_blue"] = StaticText(_("Remove Bookmark"))
		self["target"] = Label()
		self["targetfreespace"] = Label()
		if self.userMode:
			self.usermodeOn()

		# Custom action handler.
		class LocationBoxActionMap(HelpableActionMap):
			def __init__(self, parent, context, actions=None, prio=0, description=None):
				if not actions:
					actions = {}
				HelpableActionMap.__init__(self, parent, context, actions, prio, description)
				self.box = parent

			def action(self, contexts, action):
				self.box.timeout(force=True)  # Reset QuickSelect
				return HelpableActionMap.action(self, contexts, action)

		# Actions that will reset QuickSelect.
		self["WizardActions"] = LocationBoxActionMap(self, "WizardActions", {
			"ok": (self.ok, _("Select")),
			"back": (self.cancel, _("Cancel")),
		}, prio=-2)
		self["DirectionActions"] = LocationBoxActionMap(self, "NavigationActions", {
			"top": self.goTop,
			"pageUp": self.goPageUp,
			"up": self.goLineUp,
			# "left": self.left,
			# "right": self.right,
			"down": self.goLineDown,
			"pageDown": self.goPageDown,
			"bottom": self.goBottom
		}, prio=-2)
		self["ColorActions"] = LocationBoxActionMap(self, "ColorActions", {
			"red": self.cancel,
			"green": self.select,
			"yellow": self.changeName,
			"blue": self.addRemoveBookmark
		}, prio=-2)
		self["EPGSelectActions"] = LocationBoxActionMap(self, "EPGSelectActions", {
			"prevService": (self.switchToBookList, _("Switch to bookmarks")),
			"nextService": (self.switchToFileList, _("Switch to file list")),
		}, prio=-2)
		self["MenuActions"] = LocationBoxActionMap(self, "MenuActions", {
			"menu": (self.showMenu, _("Menu")),
		}, prio=-2)
		# Actions used by QuickSelect
		smsMsg = _("SMS style QuickSelect location selection")
		self["numberActions"] = HelpableNumberActionMap(self, "NumberActions", {
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
		# Run some functions when shown
		self.onShown.extend((boundFunction(self.setTitle, _("Select Location")), self.updateTarget, self.showHideRename))
		self.onLayoutFinish.append(self.switchToFileListOnStart)
		self.onClose.append(self.disableTimer)  # Make sure we remove our callback.

	def __repr__(self):
		return "%s(%s)" % (type(self), self.text)

	def switchToFileListOnStart(self):
		self.switchToFileList()

	def disableTimer(self):
		self.qs_timer.callback.remove(self.timeout)

	def showHideRename(self):
		self["key_yellow"].setText("" if self.filename == "" else _("Rename"))  # Don't allow renaming when filename is empty.

	def switchToFileList(self):
		if not self.userMode:
			self.currList = "filelist"
			self["filelist"].selectionEnabled(True)
			self["booklist"].selectionEnabled(False)
			self["key_blue"].setText(_("Add Bookmark"))
			self.updateTarget()

	def switchToBookList(self):
		self.currList = "booklist"
		self["filelist"].selectionEnabled(False)
		self["booklist"].selectionEnabled(True)
		self["key_blue"].setText(_("Remove Bookmark"))
		self.updateTarget()

	def addRemoveBookmark(self):
		if self.currList == "filelist":  # Add bookmark.
			folder = self["filelist"].getSelection()[0]
			if folder is not None and not folder in self.bookmarks:
				self.bookmarks.append(folder)
				self.bookmarks.sort()
				self["booklist"].setList(self.bookmarks)
		else:  # Remove bookmark.
			if not self.userMode:
				name = self["booklist"].getCurrent()
				self.session.openWithCallback(boundFunction(self.removeBookmark, name), MessageBox, _("Do you really want to remove your bookmark for '%s'?") % name)

	def removeBookmark(self, name, ret):
		if not ret:
			return
		if name in self.bookmarks:
			self.bookmarks.remove(name)
			self["booklist"].setList(self.bookmarks)

	def createDir(self):
		if self["filelist"].current_directory is not None:
			self.session.openWithCallback(self.createDirCallback, InputBox, title=_("Please enter a name for the new directory:"), text="")

	def createDirCallback(self, res):
		if res:
			path = pathjoin(self["filelist"].current_directory, res)
			if not pathExists(path):
				if not createDir(path):
					self.session.open(MessageBox, _("Error: Creating directory '%s' failed!") % path, type=MessageBox.TYPE_ERROR, timeout=5)
				self["filelist"].refresh()
			else:
				self.session.open(MessageBox, _("Error: The path '%s' already exists!") % path, type=MessageBox.TYPE_ERROR, timeout=5)

	def removeDir(self):
		sel = self["filelist"].getSelection()
		if sel and pathExists(sel[0]):
			self.session.openWithCallback(boundFunction(self.removeDirCallback, sel[0]), MessageBox, _("Do you really want to remove directory '%s' from the disk?") % (sel[0]), type=MessageBox.TYPE_YESNO)
		else:
			self.session.open(MessageBox, _("Error: Invalid directory '%s' selected!") % (sel[0]), type=MessageBox.TYPE_ERROR, timeout=5)

	def removeDirCallback(self, name, res):
		if res:
			if not removeDir(name):
				self.session.open(MessageBox, _("Error: Removing directory '%s' failed! (Maybe the directory is not empty.)") % name, type=MessageBox.TYPE_ERROR, timeout=5)
			else:
				self["filelist"].refresh()
				self.removeBookmark(name, True)
				val = self.realBookmarks and self.realBookmarks.value
				if val and name in val:
					val.remove(name)
					self.realBookmarks.value = val
					self.realBookmarks.save()

	def goTop(self):
		self[self.currList].goTop()
		self.updateTarget()

	def goPageUp(self):
		self[self.currList].goPageUp()
		self.updateTarget()

	def goLineUp(self):
		self[self.currList].goLineUp()
		self.updateTarget()

	def goLineDown(self):
		self[self.currList].goLineDown()
		self.updateTarget()

	def goPageDown(self):
		self[self.currList].goPageDown()
		self.updateTarget()

	def goBottom(self):
		self[self.currList].goBottom()
		self.updateTarget()

	def ok(self):
		if self.currList == "filelist":
			if self["filelist"].canDescent():
				self["filelist"].descent()
				self.updateTarget()
		else:
			self.select()

	def cancel(self):
		self.close(None)

	def getPreferredFolder(self):
		if self.currList == "filelist":
			return self["filelist"].getSelection()[0]  # XXX: We might want to change this for parent folder...
		else:
			return self["booklist"].getCurrent()

	def selectConfirmed(self, ret):
		if ret:
			ret = "".join((self.getPreferredFolder(), self.filename))
			if self.realBookmarks:
				if self.autoAdd and not ret in self.bookmarks:
					self.bookmarks.append(self.getPreferredFolder())
					self.bookmarks.sort()
				if self.bookmarks != self.realBookmarks.value:
					self.realBookmarks.value = self.bookmarks
					self.realBookmarks.save()
			self.close(ret)

	def select(self):
		currentFolder = self.getPreferredFolder()
		if currentFolder is not None:  # Do nothing unless current directory is valid.
			if self.minFree is not None:  # Check if we need to have a minimum of free space available.
				try:
					s = statvfs(currentFolder)  # Try to read filesystem status.
					if (s.f_bavail * s.f_bsize) / 1000000 > self.minFree:
						return self.selectConfirmed(True)  # Automatically confirm if we have enough free disk space available.
				except OSError as err:
					print("[LocationBox] Error %d: Unable to get '%s' status!  (%s)" % (err.errno, currFolder, err.strerror))
				self.session.openWithCallback(self.selectConfirmed, MessageBox, _("There might not be enough space on the selected partition. Do you really want to continue?"), type=MessageBox.TYPE_YESNO)
			else:  # No minimum free space means we can safely close.
				self.selectConfirmed(True)

	def changeName(self):  # TODO: Add Information that changing extension is bad? Disallow?
		if self.filename != "":
			self.session.openWithCallback(self.nameChanged, InputBox, title=_("Please enter a new filename:"), text=self.filename)

	def nameChanged(self, res):
		if res is not None:
			if len(res):
				self.filename = res
				self.updateTarget()
			else:
				self.session.open(MessageBox, _("Error: An empty filename is illegal!"), type=MessageBox.TYPE_ERROR, timeout=5)

	def updateTarget(self):
		currFolder = self.getPreferredFolder()
		if currFolder is not None:  # Write combination of folder & filename when folder is valid.
			free = ""
			try:
				status = statvfs(currFolder)
				free = ("%0.f GB " + _("Free")) % (float(status.f_bavail) * status.f_bsize / 1024 / 1024 / 1024)
			except OSError as err:
				print("[LocationBox] Error %d: Unable to get '%s' status!  (%s)" % (err.errno, currFolder, err.strerror))
			self["targetfreespace"].setText(free)
			self["target"].setText("".join((currFolder, self.filename)))
		else:  # Display a warning otherwise.
			self["target"].setText(_("Invalid location!"))

	def showMenu(self):
		if not self.userMode and self.realBookmarks:
			if self.currList == "filelist":
				menu = [
					(_("Switch to bookmarks"), self.switchToBookList),
					(_("Add Bookmark"), self.addRemoveBookmark)
				]
				if self.editDir:
					menu.extend((
						(_("Create directory"), self.createDir),
						(_("Remove directory"), self.removeDir)
					))
			else:
				menu = (
					(_("Switch to file list"), self.switchToFileList),
					(_("Remove Bookmark"), self.addRemoveBookmark)
				)
			self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice:
			choice[1]()

	def usermodeOn(self):
		self.switchToBookList()
		self["filelist"].hide()
		self["key_blue"].setText("")

	def keyNumberGlobal(self, number):
		self.qs_timer.stop()  # Cancel timeout.
		if number != self.lastKey:  # See if another key was pressed before.
			self.nextKey()  # Reset lastKey again so NumericalTextInput triggers its keychange event.
			self.selectByStart()  # Try to select what was typed.
			self.curr_pos += 1  # Increment position.
		self.quickselect = self.quickselect[:self.curr_pos] + str(self.getKey(number))  # Get char and append to text.
		self.qs_timer_type = 0
		self.qs_timer.start(1000, 1)  # Start timeout.

	def selectByStart(self):
		if not self.quickselect:  # Don't do anything on initial call.
			return
		if self["filelist"].getCurrentDirectory():  # Don't select if no directory.
			files = self["filelist"].getFileList()  # TODO: Implement proper method in Components.FileList.
			lookFor = self["filelist"].getCurrentDirectory() + self.quickselect  # We select by filename which is absolute.
			for index, file in enumerate(files):  # Select file starting with generated text.
				if file[0][0] and file[0][0].lower().startswith(lookFor):
					self["filelist"].instance.moveSelectionTo(index)
					break

	def timeout(self, force=False):
		if not force and self.qs_timer_type == 0:  # Timeout key.
			self.selectByStart()  # Try to select what was typed.
			self.lastKey = -1  # Reset key.
			self.qs_timer_type = 1  # Change type.
			self.qs_timer.start(1000, 1)  # Start timeout again.
		else:  # Timeout QuickSelect.
			self.qs_timer.stop()  # Eventually stop timer.
			self.lastKey = -1  # Invalidate.
			self.curr_pos = -1
			self.quickselect = ""


class MovieLocationBox(LocationBox):
	def __init__(self, session, text, currDir, minFree=None):
		LocationBox.__init__(
			self,
			session,
			text=text,
			# filename="",
			currDir=currDir,
			bookmarks=config.movielist.videodirs,
			# userMode=False,
			windowTitle=_("Select Movie Location"),
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
			# userMode=False,
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
			# userMode=False,
			windowTitle=_("Select Time Shift Location"),
			minFree=1024,  # The same minFree requirement is hardcoded in servicedvb.cpp.
			autoAdd=True,
			editDir=True,
			inhibitDirs=DEFAULT_INHIBIT_DIRECTORIES,
			# inhibitMounts=None
		)
		self.skinName = ["TimeshiftLocationBox", "LocationBox"]

	def cancel(self):
		config.timeshift.path.cancel()
		LocationBox.cancel(self)

	def selectConfirmed(self, answer):
		if answer:
			config.timeshift.path.value = self.getPreferredFolder()
			config.timeshift.path.save()
			LocationBox.selectConfirmed(self, answer)
