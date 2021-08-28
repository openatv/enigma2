from os import stat
from os.path import isdir, join as pathjoin

from Components.config import config
from Components.UsageConfig import preferredPath
from Screens.LocationBox import defaultInhibitDirs, MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.Directories import fileAccess


class RecordingSettings(Setup):
	def __init__(self, session):
		self.styles = [("<default>", _("<Default movie location>")), ("<current>", _("<Current movielist location>")), ("<timer>", _("<Last timer location>"))]
		self.styleKeys = [x[0] for x in self.styles]
		self.inhibitDevs = []
		for dir in defaultInhibitDirs + ["/", "/media"]:
			if isdir(dir):
				device = stat(dir).st_dev
				if device not in self.inhibitDevs:
					self.inhibitDevs.append(device)
		self.buildChoices("DefaultPath", config.usage.default_path, None)
		self.buildChoices("TimerPath", config.usage.timer_path, None)
		self.buildChoices("InstantPath", config.usage.instantrec_path, None)
		Setup.__init__(self, session=session, setup="Recording")
		self.greenText = self["key_green"].text
		self.errorItem = -1
		if self.getCurrentItem() in (config.usage.default_path, config.usage.timer_path, config.usage.instantrec_path):
			self.pathStatus(self.getCurrentValue())

	def selectionChanged(self):
		if self.errorItem == -1:
			Setup.selectionChanged(self)
		else:
			self["config"].setCurrentIndex(self.errorItem)

	def changedEntry(self):
		if self.getCurrentItem() in (config.usage.default_path, config.usage.timer_path, config.usage.instantrec_path):
			self.pathStatus(self.getCurrentValue())
		Setup.changedEntry(self)

	def keySelect(self):
		item = self.getCurrentItem()
		if item in (config.usage.default_path, config.usage.timer_path, config.usage.instantrec_path):
			# print("[Recordings] DEBUG: '%s', '%s', '%s'." % (self.getCurrentEntry(), item.value, preferredPath(item.value)))
			self.session.openWithCallback(self.pathSelect, MovieLocationBox, self.getCurrentEntry(), preferredPath(item.value))
		else:
			Setup.keySelect(self)

	def keySave(self):
		if self.errorItem == -1:
			Setup.keySave(self)
		else:
			self.session.open(MessageBox, "%s\n\n%s" % (self.getFootnote(), _("Please select an acceptable directory.")), type=MessageBox.TYPE_ERROR)

	def buildChoices(self, item, configEntry, path):
		configList = config.movielist.videodirs.value[:]
		styleList = [] if item == "DefaultPath" else self.styleKeys
		if configEntry.saved_value and configEntry.saved_value not in styleList + configList:
			configList.append(configEntry.saved_value)
			configEntry.value = configEntry.saved_value
		if path is None:
			path = configEntry.value
		if path and path not in styleList + configList:
			configList.append(path)
		pathList = [(x, x) for x in configList] if item == "DefaultPath" else self.styles + [(x, x) for x in configList]
		configEntry.value = path
		configEntry.setChoices(pathList, default=configEntry.default)
		# print("[Recordings] DEBUG %s: Current='%s', Default='%s', Choices='%s'." % (item, configEntry.value, configEntry.default, styleList + configList))

	def pathSelect(self, path):
		if path is not None:
			path = pathjoin(path, "")
			item = self.getCurrentItem()
			if item is config.usage.default_path:
				self.buildChoices("DefaultPath", config.usage.default_path, path)
			else:
				self.buildChoices("DefaultPath", config.usage.default_path, None)
			if item is config.usage.timer_path:
				self.buildChoices("TimerPath", config.usage.timer_path, path)
			else:
				self.buildChoices("TimerPath", config.usage.timer_path, None)
			if item is config.usage.instantrec_path:
				self.buildChoices("InstantPath", config.usage.instantrec_path, path)
			else:
				self.buildChoices("InstantPath", config.usage.instantrec_path, None)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def pathStatus(self, path):
		if path.startswith("<"):
			self.errorItem = -1
			footnote = ""
			green = self.greenText
		elif not isdir(path):
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("Directory '%s' does not exist!") % path
			green = ""
		elif stat(path).st_dev in self.inhibitDevs:
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("Flash directory '%s' not allowed!") % path
			green = ""
		elif not fileAccess(path, "w"):
			self.errorItem = self["config"].getCurrentIndex()
			footnote = _("Directory '%s' not writable!") % path
			green = ""
		else:
			self.errorItem = -1
			footnote = ""
			green = self.greenText
		self.setFootnote(footnote)
		self["key_green"].text = green
