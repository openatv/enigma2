from os.path import join
from Components.config import config
from Components.TimeshiftStorage import checkStorageDirectory
from Screens.LocationBox import TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup
from Tools.StorageCheck import StoragePathCheck


class TimeshiftSettings(Setup):
	def __init__(self, session):
		self.pathItem = None
		self.status = None
		self._checkedPath = None
		self._savePending = False
		self._pathCheck = StoragePathCheck(checkStorageDirectory, self._pathChecked)
		self.buildChoices(config.timeshift.path, None)
		Setup.__init__(self, session=session, setup="Timeshift")
		for index, item in enumerate(self["config"].getList()):
			if len(item) > 1 and item[1] == config.timeshift.path:
				self.pathItem = index
				break
		else:
			print("[Timeshift] Error: ConfigList time shift path entry not found!")
			self.pathItem = None
		self.onClose.append(self._pathCheck.cancel)

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
		if self.getCurrentItem() == config.timeshift.path:
			path = config.timeshift.path.value
			if path != self._checkedPath:
				self._checkPath()
			else:
				self.setFootnote(self.status or "")

	def _checkPath(self, save=False):
		path = config.timeshift.path.value
		if self._savePending:
			return
		if self._pathCheck.start((path,)):
			self._checkedPath = path
			self._savePending = save
			self.status = _("Checking storage directory...")
			self.setFootnote(self.status)
		elif save:
			self.session.showInfo(_("A storage check is still running. Please try again shortly."))

	def _pathChecked(self, errors):
		save = self._savePending
		self._savePending = False
		if self._checkedPath != config.timeshift.path.value:
			self._checkedPath = None
			self.pathStatus()
			return
		if errors is None:
			self.status = _("The storage check did not finish. Please check the device or network and try again.")
		else:
			self.status = errors.get(self._checkedPath, "")
		if save or self.getCurrentItem() == config.timeshift.path:
			self.setFootnote(self.status)
		if save:
			if errors is None:
				self.session.showError(self.status)
			elif self.status:
				self.session.openWithCallback(self.keySaveCallback, MessageBox, "%s\n\n%s\n%s" % (self.status, _("Time shift may not work correctly without an acceptable directory."), _("Save these settings anyway?")), type=MessageBox.TYPE_YESNO, default=False)
			else:
				Setup.keySave(self)

	def keySelect(self):
		if self._savePending:
			return
		if self.getCurrentItem() == config.timeshift.path:
			self.session.openWithCallback(self.keySelectCallback, TimeshiftLocationBox)
		else:
			Setup.keySelect(self)

	def keySelectCallback(self, path):
		if path is not None:
			path = join(path, "")
			self.buildChoices(config.timeshift.path, path)
		self["config"].invalidateCurrent()
		self.changedEntry()

	def keySave(self):
		self._checkPath(save=True)

	def keySaveCallback(self, result):
		if result and self._checkedPath == config.timeshift.path.value:
			Setup.keySave(self)

	def closeConfigList(self, closeParameters=()):
		# Cancel before the discard-changes question opens, not only onClose.
		self._pathCheck.cancel()
		self._savePending = False
		self._checkedPath = None
		Setup.closeConfigList(self, closeParameters)
