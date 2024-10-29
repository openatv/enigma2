from os import stat
from os.path import isdir, join as pathjoin

from Components.config import config
from Components.UsageConfig import preferredPath
from Screens.LocationBox import DEFAULT_INHIBIT_DEVICES, MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.Directories import fileAccess


class RecordingSettings(Setup):
	def __init__(self, session):
		self.styles = [("<default>", _("<Default movie location>")), ("<current>", _("<Current movie list location>")), ("<timer>", _("<Last timer location>"))]
		self.styleKeys = [x[0] for x in self.styles]
		self.buildChoices(config.usage.timer_path, None)
		self.buildChoices(config.usage.instantrec_path, None)
		self.buildChoices(config.timeshift.recordingPath, None)
		Setup.__init__(self, session=session, setup="Recording")
		self.status = {}

	def buildChoices(self, configEntry, path):
		configList = config.movielist.videodirs.value[:]
		if configEntry.saved_value and configEntry.saved_value not in self.styleKeys + configList:
			configList.append(configEntry.saved_value)
			configEntry.value = configEntry.saved_value
		if path is None:
			path = configEntry.value
		if path and path not in self.styleKeys + configList:
			configList.append(path)
		configEntry.value = path
		configEntry.setChoices(self.styles + [(x, x) for x in configList], default=configEntry.default)
		# print("[Recordings] DEBUG: Current='%s', Default='%s', Choices='%s'." % (configEntry.value, configEntry.default, self.styleKeys + configList))

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.pathStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.pathStatus()

	def pathStatus(self):
		if self.getCurrentItem() in (config.usage.timer_path, config.usage.instantrec_path, config.timeshift.recordingPath):
			item = self["config"].getCurrentIndex()
			if item in self.status:
				del self.status[item]
			path = self.getCurrentValue()
			if path.startswith("<"):
				directory = {
					"<default>": config.usage.default_path.value,
					"<current>": config.movielist.last_videodir.value,
					"<timer>": config.movielist.last_timer_videodir.value
				}.get(self.getCurrentItem().value)
				footnote = _("Current location is '%s'.") % (self.getCurrentItem().value if directory is None else directory)
			elif not isdir(path):
				footnote = _("Directory '%s' does not exist!") % path
				self.status[item] = (self.getCurrentEntry(), footnote)
			elif stat(path).st_dev in DEFAULT_INHIBIT_DEVICES:
				footnote = _("Flash directory '%s' not allowed!") % path
				self.status[item] = (self.getCurrentEntry(), footnote)
			elif not fileAccess(path, "w"):
				footnote = _("Directory '%s' not writable!") % path
				self.status[item] = (self.getCurrentEntry(), footnote)
			else:
				footnote = ""
			self.setFootnote(footnote)

	def keySelect(self):
		item = self.getCurrentItem()
		if item in (config.usage.timer_path, config.usage.instantrec_path, config.timeshift.recordingPath):
			self.session.openWithCallback(self.keySelectCallback, MovieLocationBox, self.getCurrentEntry(), preferredPath(item.value))
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path is not None:
			path = pathjoin(path, "")
			item = self.getCurrentItem()
			self.buildChoices(config.usage.timer_path, path if item == config.usage.timer_path else None)
			self.buildChoices(config.usage.instantrec_path, path if item == config.usage.instantrec_path else None)
			self.buildChoices(config.timeshift.recordingPath, path if item == config.timeshift.recordingPath else None)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def keySave(self):
		msg = []
		for item in self.status.keys():
			msg.append("%s: %s" % self.status[item])
		if msg:
			self.session.openWithCallback(self.keySaveCallback, MessageBox, "%s\n\n%s" % ("\n".join(msg), _("Recordings may not work correctly without an acceptable directory.")), type=MessageBox.TYPE_WARNING)
		else:
			Setup.keySave(self)

	def keySaveCallback(self, result):
		Setup.keySave(self)
