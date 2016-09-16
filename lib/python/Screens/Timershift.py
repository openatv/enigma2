from Screens.Screen import Screen
from Screens.Setup import setupdom
from Screens.LocationBox import AutorecordLocationBox, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.config import config, configfile, ConfigYesNo, ConfigNothing, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo


class SetupSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["SetupTitle"] = StaticText(_(parent.setup_title))
		self["SetupEntry"] = StaticText("")
		self["SetupValue"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)
		self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()
		if hasattr(self.parent,"getCurrentDescription"):
			self.parent["description"].text = self.parent.getCurrentDescription()
		if self.parent.has_key('footnote'):
			if self.parent.getCurrentEntry().endswith('*'):
				self.parent['footnote'].text = (_("* = Restart Required"))
			else:
				self.parent['footnote'].text = (_(" "))

class TimeshiftSettings(Screen,ConfigListScreen):
	def removeNotifier(self):
		if config.usage.setup_level.notifiers:
			config.usage.setup_level.notifiers.remove(self.levelChanged)

	def levelChanged(self, configElement):
		list = []
		self.refill(list)
		self["config"].setList(list)

	def refill(self, list):
		xmldata = setupdom().getroot()
		for x in xmldata.findall("setup"):
			if x.get("key") != self.setup:
				continue
			self.addItems(list, x)
			self.setup_title = x.get("title", "").encode("UTF-8")
			self.seperation = int(x.get('separation', '0'))

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self['footnote'] = Label()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label(_(""))

		self.onChangedEntry = [ ]
		self.setup = "timeshift"
		list = []
		ConfigListScreen.__init__(self, list, session = session, on_change = self.changedEntry)
		self.createSetup()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"green": self.keySave,
			"red": self.keyCancel,
			"cancel": self.keyCancel,
			"ok": self.ok,
			"menu": self.closeRecursive,
		}, -2)
		self.onLayoutFinish.append(self.layoutFinished)

	# for summary:
	def changedEntry(self):
		self.item = self["config"].getCurrent()
		if self["config"].getCurrent()[0] == _("Timeshift location"):
			self.checkReadWriteDir(self["config"].getCurrent()[1])
		if self["config"].getCurrent()[0] == _("Autorecord location"):
			self.checkReadWriteDir(self["config"].getCurrent()[1])
		for x in self.onChangedEntry:
			x()
		try:
			if isinstance(self["config"].getCurrent()[1], ConfigYesNo) or isinstance(self["config"].getCurrent()[1], ConfigSelection):
				self.createSetup()
		except:
			pass

	def getCurrentEntry(self):
		return self["config"].getCurrent() and self["config"].getCurrent()[0] or ""

	def getCurrentValue(self):
		return self["config"].getCurrent() and str(self["config"].getCurrent()[1].getText()) or ""

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def checkReadWriteDir(self, configele):
		import os.path
		import Components.Harddisk
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs', 'cifs'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts()
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(configele.value))+'/' in locations or Components.Harddisk.findMountPoint(os.path.realpath(configele.value)) in locations:
				if fileExists(configele.value, "w"):
					configele.last_value = configele.value
					return True
				else:
					dir = configele.value
					configele.value = configele.last_value
					self.session.open(
						MessageBox,
						_("The directory %s is not writable.\nMake sure you select a writable directory instead.")%dir,
						type = MessageBox.TYPE_ERROR
						)
					return False
			else:
				dir = configele.value
				configele.value = configele.last_value
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%dir,
					type = MessageBox.TYPE_ERROR
					)
				return False
		else:
			dir = configele.value
			configele.value = configele.last_value
			self.session.open(
				MessageBox,
				_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%dir,
				type = MessageBox.TYPE_ERROR
				)
			return False

	def createSetup(self):
		default = config.usage.timeshift_path.value
		cooldefault = config.usage.autorecord_path.value
		tmp = config.usage.allowed_timeshift_paths.value
		cooltmp = config.usage.allowed_autorecord_paths.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		if cooldefault not in cooltmp:
			cooltmp = cooltmp[:]
			cooltmp.append(cooldefault)
# 		print "TimeshiftPath: ", default, tmp
		self.timeshift_dirname = ConfigSelection(default = default, choices = tmp)
		self.autorecord_dirname = ConfigSelection(default = cooldefault, choices = cooltmp)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.autorecord_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		list = []
		self.timeshift_entry = getConfigListEntry(_("Timeshift location"), self.timeshift_dirname, _("Set the default location for your timeshift-files. Press 'OK' to add new locations, select left/right to select an existing location."))
		list.append(self.timeshift_entry)
		self.autorecord_entry = getConfigListEntry(_("Autorecord location"), self.autorecord_dirname, _("Set the default location for your autorecord-files. Press 'OK' to add new locations, select left/right to select an existing location."))
		list.append(self.autorecord_entry)

		self.refill(list)
		self["config"].setList(list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	def ok(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.value
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.value
		self.lastautorecorddirs = config.usage.allowed_autorecord_paths.value
		if currentry == self.timeshift_entry:
			self.entrydirname = self.timeshift_dirname
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			self.session.openWithCallback(
				self.dirnameSelected,
				TimeshiftLocationBox
			)
		if currentry == self.autorecord_entry:
			self.entrydirname = self.autorecord_dirname
			config.usage.autorecord_path.value = self.autorecord_dirname.value
			self.session.openWithCallback(
				self.dirnameSelected,
				AutorecordLocationBox
			)

	def dirnameSelected(self, res):
		if res is not None:
			import os.path
			import Components.Harddisk
			supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs', 'cifs'))
			candidates = []
			mounts = Components.Harddisk.getProcMounts()
			for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
				if partition.filesystem(mounts) in supported_filesystems:
					candidates.append((partition.description, partition.mountpoint))
			if candidates:
				locations = []
				for validdevice in candidates:
					locations.append(validdevice[1])
				if Components.Harddisk.findMountPoint(os.path.realpath(res))+'/' in locations or Components.Harddisk.findMountPoint(os.path.realpath(res)) in locations:
					self.entrydirname.value = res
					if config.usage.allowed_timeshift_paths.value != self.lasttimeshiftdirs:
						tmp = config.usage.allowed_timeshift_paths.value
						default = self.timeshift_dirname.value
						if default not in tmp:
							tmp = tmp[:]
							tmp.append(default)
						self.timeshift_dirname.setChoices(tmp, default=default)
						self.entrydirname.value = res
					if config.usage.allowed_autorecord_paths.value != self.lastautorecorddirs:
						tmp = config.usage.allowed_autorecord_paths.value
						default = self.autorecord_dirname.value
						if default not in tmp:
							tmp = tmp[:]
							tmp.append(default)
						self.autorecord_dirname.setChoices(tmp, default=default)
						self.entrydirname.value = res
				else:
					self.session.open(
						MessageBox,
						_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%res,
						type = MessageBox.TYPE_ERROR
						)
			else:
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%res,
					type = MessageBox.TYPE_ERROR
					)

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		import os.path
		import Components.Harddisk
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs', 'cifs'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts()
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(config.usage.timeshift_path.value))+'/' in locations or Components.Harddisk.findMountPoint(os.path.realpath(config.usage.timeshift_path.value)) in locations:
				config.usage.timeshift_path.value = self.timeshift_dirname.value
				config.usage.timeshift_path.save()
				self.saveAll()
				self.close()
			else:
				if int(config.timeshift.startdelay.value) > 0:
					self.session.open(
						MessageBox,
						_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
						type = MessageBox.TYPE_ERROR
						)
				else:
					config.timeshift.startdelay.setValue(0)
					self.saveAll()
					self.close()
		else:
			if int(config.timeshift.startdelay.value) > 0:
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4, NFS or CIFS partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
					type = MessageBox.TYPE_ERROR
					)
			else:
				config.timeshift.startdelay.setValue(0)
				self.saveAll()
				self.close()

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			self.close()

	def createSummary(self):
		return SetupSummary

	def addItems(self, list, parentNode):
		for x in parentNode:
			if not x.tag:
				continue
			if x.tag == 'item':
				item_level = int(x.get("level", 0))

				if not self.levelChanged in config.usage.setup_level.notifiers:
					config.usage.setup_level.notifiers.append(self.levelChanged)
					self.onClose.append(self.removeNotifier)

				if item_level > config.usage.setup_level.index:
					continue

				requires = x.get("requires")
				if requires and requires.startswith('config.'):
					item = eval(requires or "")
					if item.value and not item.value == "0":
						SystemInfo[requires] = True
					else:
						SystemInfo[requires] = False

				if requires and not SystemInfo.get(requires, False):
					continue

				item_text = _(x.get("text", "??").encode("UTF-8"))
				item_description = _(x.get("description", " ").encode("UTF-8"))
				b = eval(x.text or "")
				if b == "":
					continue
				#add to configlist
				item = b
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				if not isinstance(item, ConfigNothing):
					list.append((item_text, item, item_description))

