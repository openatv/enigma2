from os import stat
from os.path import isdir, join as pathjoin

from Components.config import config
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES, PlaybackLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.Directories import fileAccess


class PlaybackSettings(Setup):
	def __init__(self, session):
		self.buildChoices(config.usage.default_path, None)
		Setup.__init__(self, session=session, setup="Playback")
		for index, item in enumerate(self["config"].getList()):
			if len(item) > 1 and item[1] == config.usage.default_path:
				self.pathItem = index
				break
		else:
			print("[Playback] Error: ConfigList movie playback path entry not found!")
			self.pathItem = None
		self.status = None

	def buildChoices(self, configEntry, path):
		configList = config.movielist.videodirs.value[:]
		if configEntry.saved_value and configEntry.saved_value not in configList:
			configList.append(configEntry.saved_value)
			configEntry.value = configEntry.saved_value
		if path is None:
			path = configEntry.value
		if path and path not in configList:
			configList.append(path)
		configEntry.value = path
		configEntry.setChoices([(x, x) for x in configList], default=configEntry.default)
		# print("[Playback] buildChoices DEBUG: Current='%s', Default='%s', Choices=%s." % (configEntry.value, configEntry.default, configList))

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.pathStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.pathStatus()

	def pathStatus(self):
		if self["config"].getCurrentIndex() == self.pathItem:
			path = self.getCurrentValue()
			if not isdir(path):
				footnote = _("Directory '%s' does not exist!") % path
			elif stat(path).st_dev in DEFAULT_INHIBIT_DEVICES:
				footnote = _("Flash directory '%s' not allowed!") % path
			elif not fileAccess(path, "w"):
				footnote = _("Directory '%s' not writable!") % path
			else:
				footnote = ""
			self.setFootnote(footnote)
			self.status = footnote

	def keySelect(self):
		if self.getCurrentItem() == config.usage.default_path:
			self.session.openWithCallback(self.keySelectCallback, PlaybackLocationBox)
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path is not None:
			path = pathjoin(path, "")
			self.buildChoices(config.usage.default_path, path)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def keySave(self):
		if self.status:
			self.session.openWithCallback(self.keySaveCallback, MessageBox, "%s\n\n%s" % (self.status, _("Movie playback may not use an invalid/inappropriate directory.")), type=MessageBox.TYPE_WARNING)
		else:
			Setup.keySave(self)

	def keySaveCallback(self, result):
		Setup.keySave(self)
