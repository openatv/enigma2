from os.path import join
from Components.config import config
from Components.TimeshiftStorage import checkStorageDirectory
from Components.UsageConfig import preferredPath
from Screens.LocationBox import MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.StorageCheck import StoragePathCheck


class RecordingSettings(Setup):
	def __init__(self, session):
		self.status = {}
		self._checkedPaths = ()
		self._savePending = False
		self._pathCheck = StoragePathCheck(checkStorageDirectory, self._pathsChecked)
		self.styles = [("<default>", _("<Default movie location>")), ("<current>", _("<Current movie list location>")), ("<timer>", _("<Last timer location>"))]
		self.styleKeys = [x[0] for x in self.styles]
		self.buildChoices(config.usage.timer_path, None)
		self.buildChoices(config.usage.instantrec_path, None)
		self.buildChoices(config.timeshift.recordingPath, None)
		Setup.__init__(self, session=session, setup="Recording")
		self.onClose.append(self._pathCheck.cancel)

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
			path = self._resolvePath(self.getCurrentItem())
			if path not in self._checkedPaths:
				self._checkPaths((path,))
			else:
				self.setFootnote(self.status.get(path, _("Current location is '%s'.") % path))

	def _resolvePath(self, item):
		return {
			"<default>": config.usage.default_path.value,
			"<current>": config.movielist.last_videodir.value,
			"<timer>": config.movielist.last_timer_videodir.value
		}.get(item.value, item.value)

	def _recordingPaths(self):
		return tuple(self._resolvePath(x) for x in (config.usage.timer_path, config.usage.instantrec_path, config.timeshift.recordingPath))

	def _checkPaths(self, paths, save=False):
		if self._savePending:
			return
		if self._pathCheck.start(paths):
			self._checkedPaths = paths
			self._savePending = save
			self.status = {x: _("Checking storage directory...") for x in paths}
			self.setFootnote(_("Checking storage directory..."))
		elif save:
			self.session.showInfo(_("A storage check is still running. Please try again shortly."))

	def _pathsChecked(self, errors):
		save = self._savePending
		self._savePending = False
		if save and self._checkedPaths != self._recordingPaths():
			self._checkedPaths = ()
			self.pathStatus()
			return
		message = _("The storage check did not finish. Please check the device or network and try again.")
		self.status = {x: message for x in self._checkedPaths} if errors is None else errors
		if save:
			if errors is None:
				self.setFootnote(message)
				self.session.showError(message)
			elif errors:
				self.session.openWithCallback(self.keySaveCallback, MessageBox, "%s\n\n%s\n%s" % ("\n".join(errors.values()), _("Recordings may not work correctly without an acceptable directory."), _("Save these settings anyway?")), type=MessageBox.TYPE_YESNO, default=False)
			else:
				Setup.keySave(self)
		else:
			self.pathStatus()

	def keySelect(self):
		if self._savePending:
			return
		item = self.getCurrentItem()
		if item in (config.usage.timer_path, config.usage.instantrec_path, config.timeshift.recordingPath):
			self.session.openWithCallback(self.keySelectCallback, MovieLocationBox, self.getCurrentEntry(), preferredPath(item.value))
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path is not None:
			path = join(path, "")
			item = self.getCurrentItem()
			self.buildChoices(config.usage.timer_path, path if item == config.usage.timer_path else None)
			self.buildChoices(config.usage.instantrec_path, path if item == config.usage.instantrec_path else None)
			self.buildChoices(config.timeshift.recordingPath, path if item == config.timeshift.recordingPath else None)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def keySave(self):
		self._checkPaths(self._recordingPaths(), save=True)

	def keySaveCallback(self, result):
		if result and self._checkedPaths == self._recordingPaths():
			Setup.keySave(self)

	def closeConfigList(self, closeParameters=()):
		self._pathCheck.cancel()
		self._savePending = False
		self._checkedPaths = ()
		Setup.closeConfigList(self, closeParameters)
