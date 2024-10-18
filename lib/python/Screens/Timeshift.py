from os import stat
from os.path import isdir, join as pathjoin

from Components.config import config
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.Directories import fileAccess, hasHardLinks


class TimeshiftSettings(Setup):
	def __init__(self, session):
		self.buildChoices(config.timeshift.path, None)
		Setup.__init__(self, session=session, setup="Timeshift")
		for index, item in enumerate(self["config"].getList()):
			if len(item) > 1 and item[1] == config.timeshift.path:
				self.pathItem = index
				break
		else:
			print("[Timeshift] Error: ConfigList time shift path entry not found!")
			self.pathItem = None
		self.status = None

	def buildChoices(self, configEntry, path):
		configList = config.timeshift.allowedPaths.value[:]
		if configEntry.saved_value and configEntry.saved_value not in configList:
			configList.append(configEntry.saved_value)
			configEntry.value = configEntry.saved_value
		if path is None:
			path = configEntry.value
		if path and path not in configList:
			configList.append(path)
		configEntry.value = path
		configEntry.setChoices([(x, x) for x in configList], default=configEntry.default)
		# print("[Timeshift] buildChoices DEBUG: Current='%s', Default='%s', Choices=%s." % (configEntry.value, configEntry.default, configList))

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
			elif stat(path).st_dev in DEFAULT_INHIBIT_DEVICES and config.timeshift.skipReturnToLive.value is False:  # allow timeshift on flash for audio plugins and no other volume availabe
				footnote = _("Flash directory '%s' not allowed!") % path
			elif not fileAccess(path, "w"):
				footnote = _("Directory '%s' not writable!") % path
			elif not hasHardLinks(path):
				footnote = _("Directory '%s' can't be linked to recordings!") % path
			else:
				footnote = ""
			self.setFootnote(footnote)
			self.status = footnote

	def keySelect(self):
		if self.getCurrentItem() == config.timeshift.path:
			self.session.openWithCallback(self.keySelectCallback, TimeshiftLocationBox)
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path is not None:
			path = pathjoin(path, "")
			self.buildChoices(config.timeshift.path, path)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def keySave(self):
		if self.status:
			self.session.openWithCallback(self.keySaveCallback, MessageBox, "%s\n\n%s" % (self.status, _("Time shift may not work correctly without an acceptable directory.")), type=MessageBox.TYPE_WARNING)
		else:
			Setup.keySave(self)

	def keySaveCallback(self, result):
		Setup.keySave(self)
