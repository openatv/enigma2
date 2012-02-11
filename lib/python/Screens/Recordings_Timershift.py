from Screens.Screen import Screen
from Screens.LocationBox import MovieLocationBox, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.config import config, configfile, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
from Components.UsageConfig import preferredPath
from Components.Sources.Boolean import Boolean

class RecordingSettings(Screen,ConfigListScreen):
	skin = """
		<screen name="RecordPathsSettings" position="160,150" size="450,200" title="Recording paths">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="300,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="300,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,44" size="430,146" />
		</screen>"""

	def __init__(self, session):
		from Components.Sources.StaticText import StaticText
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setup_title = _("Recording Settings")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
		    "green": self.keySave,
		    "red": self.keyCancel,
		    "cancel": self.keyCancel,
		    "ok": self.ok,
			"menu": self.closeRecursive,
		}, -2)

	def checkReadWriteDir(self, configele):
		print "checkReadWrite: ", configele.value
		if configele.value in [x[0] for x in self.styles] or fileExists(configele.value, "w"):
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

	def createSetup(self):
		self.styles = [ ("<default>", _("<Default movie location>")), ("<current>", _("<Current movielist location>")), ("<timer>", _("<Last timer location>")) ]
		styles_keys = [x[0] for x in self.styles]
		tmp = config.movielist.videodirs.value
		default = config.usage.default_path.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print "DefaultPath: ", default, tmp
		self.default_dirname = ConfigSelection(default = default, choices = tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.timer_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
		print "TimerPath: ", default, tmp
		self.timer_dirname = ConfigSelection(default = default, choices = self.styles+tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.instantrec_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
		print "InstantrecPath: ", default, tmp
		self.instantrec_dirname = ConfigSelection(default = default, choices = self.styles+tmp)
		self.default_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timer_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.instantrec_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)

		self.list = []
		if config.usage.setup_level.index >= 2:
			self.default_entry = getConfigListEntry(_("Default movie location"), self.default_dirname)
			self.list.append(self.default_entry)
			self.timer_entry = getConfigListEntry(_("Timer record location"), self.timer_dirname)
			self.list.append(self.timer_entry)
			self.instantrec_entry = getConfigListEntry(_("Instant record location"), self.instantrec_dirname)
			self.list.append(self.instantrec_entry)
		else:
			self.default_entry = getConfigListEntry(_("Movie location"), self.default_dirname)
			self.list.append(self.default_entry)

		if config.usage.setup_level.index >= 1:
			self.list.append(getConfigListEntry(_("Recordings always have priority"), config.recording.asktozap))
		self.list.append(getConfigListEntry(_("Margin before record (minutes)"), config.recording.margin_before))
		self.list.append(getConfigListEntry(_("Margin after record"), config.recording.margin_after))
		if config.usage.setup_level.index >= 2:
			self.list.append(getConfigListEntry(_("Show Message when Recording starts"), config.usage.show_message_when_recording_starts))
			self.list.append(getConfigListEntry(_("Load Length of Movies in Movielist"), config.usage.load_length_of_movies_in_moviellist))
			self.list.append(getConfigListEntry(_("Show status icons in Movielist"), config.usage.show_icons_in_movielist))
			self.list.append(getConfigListEntry(_("Behavior when a movie is started"), config.usage.on_movie_start))
			self.list.append(getConfigListEntry(_("Behavior when a movie is stopped"), config.usage.on_movie_stop))
			self.list.append(getConfigListEntry(_("Behavior when a movie reaches the end"), config.usage.on_movie_eof))
			self.list.append(getConfigListEntry(_("Behavior of 'pause' when paused"), config.seek.on_pause))
			self.list.append(getConfigListEntry(_("Custom skip time for '1'/'3'-keys"), config.seek.selfdefined_13))
			self.list.append(getConfigListEntry(_("Custom skip time for '4'/'6'-keys"), config.seek.selfdefined_46))
			self.list.append(getConfigListEntry(_("Custom skip time for '7'/'9'-keys"), config.seek.selfdefined_79))
			self.list.append(getConfigListEntry(_("Seekbar sensibility"), config.seek.sensibility))
			self.list.append(getConfigListEntry(_("Fast Forward speeds"), config.seek.speeds_forward))
			self.list.append(getConfigListEntry(_("Rewind speeds"), config.seek.speeds_backward))
			self.list.append(getConfigListEntry(_("Slow Motion speeds"), config.seek.speeds_slowmotion))
			self.list.append(getConfigListEntry(_("Initial Fast Forward speed"), config.seek.enter_forward))
			self.list.append(getConfigListEntry(_("Initial Rewind speed"), config.seek.enter_backward))
			self.list.append(getConfigListEntry(_("Limited character set for recording filenames"), config.recording.ascii_filenames))
			self.list.append(getConfigListEntry(_("Composition of the recording filenames"), config.recording.filename_composition))
			self.list.append(getConfigListEntry(_("Keep old timers for how many days"), config.recording.keep_timers))
		if config.usage.setup_level.index >= 1:
			self.list.append(getConfigListEntry(_("Use trashcan in movielist"), config.usage.movielist_trashcan))
			self.list.append(getConfigListEntry(_("Remove items from trash after (days)"), config.usage.movielist_trashcan_days))
			self.list.append(getConfigListEntry(_("Disk space to reserve for recordings (in GB)"), config.usage.movielist_trashcan_reserve))
		if config.usage.setup_level.index >= 2:
			self.list.append(getConfigListEntry(_("Recording data sync size"), config.misc.flush_size))
			self.list.append(getConfigListEntry(_("Background delete option"), config.misc.erase_flags))
			self.list.append(getConfigListEntry(_("Background delete speed"), config.misc.erase_speed))
			self.list.append(getConfigListEntry(_("Record ECM"), config.recording.record_ecm))
			self.list.append(getConfigListEntry(_("Descramble recordings"), config.recording.descramble))
			self.list.append(getConfigListEntry(_("Offline decode delay (ms)"), config.recording.offline_decode_delay))
		self["config"].setList(self.list)

	# for summary:
	def changedEntry(self):
		if self["config"].getCurrent()[0] == _("Default movie location") or self["config"].getCurrent()[0] == _("Timer record location") or self["config"].getCurrent()[0] == _("Instant record location") or self["config"].getCurrent()[0] == _("Movie location"):
			self.checkReadWriteDir(self["config"].getCurrent()[1])
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def ok(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.value
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.value
		if config.usage.setup_level.index >= 2:
			txt = _("Default movie location")
		else:
			txt = _("Movie location")
		if currentry == self.default_entry:
			self.entrydirname = self.default_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				txt,
				preferredPath(self.default_dirname.value)
			)
		elif currentry == self.timer_entry:
			self.entrydirname = self.timer_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("New timers location"),
				preferredPath(self.timer_dirname.value)
			)
		elif currentry == self.instantrec_entry:
			self.entrydirname = self.instantrec_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("Instant recordings location"),
				preferredPath(self.instantrec_dirname.value)
			)

	def dirnameSelected(self, res):
		if res is not None:
			self.entrydirname.value = res
			if config.movielist.videodirs.value != self.lastvideodirs:
				styles_keys = [x[0] for x in self.styles]
				tmp = config.movielist.videodirs.value
				default = self.default_dirname.value
				if default not in tmp:
					tmp = tmp[:]
					tmp.append(default)
				self.default_dirname.setChoices(tmp, default=default)
				tmp = config.movielist.videodirs.value
				default = self.timer_dirname.value
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.timer_dirname.setChoices(self.styles+tmp, default=default)
				tmp = config.movielist.videodirs.value
				default = self.instantrec_dirname.value
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.instantrec_dirname.setChoices(self.styles+tmp, default=default)
				self.entrydirname.value = res
			if self.entrydirname.last_value != res:
				self.checkReadWriteDir(self.entrydirname)

	def saveAll(self):
		currentry = self["config"].getCurrent()
		config.usage.default_path.value = self.default_dirname.value
		config.usage.timer_path.value = self.timer_dirname.value
		config.usage.instantrec_path.value = self.instantrec_dirname.value 
		config.usage.default_path.save()
		config.usage.timer_path.save()
		config.usage.instantrec_path.save()
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
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
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

class TimeshiftSettings(Screen,ConfigListScreen):
	skin = """
		<screen name="RecordPathsSettings" position="160,150" size="450,200" title="Recording paths">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="300,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="10,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="300,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,44" size="430,146" />
		</screen>"""

	def __init__(self, session):
		from Components.Sources.StaticText import StaticText
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setup_title = _("Timshift Settings")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.keySave,
		    "red": self.keyCancel,
		    "cancel": self.keyCancel,
		    "ok": self.ok,
		}, -2)

	# for summary:
	def changedEntry(self):
		if self["config"].getCurrent()[0] == _("Permanent Timeshift Enable"):
			self.createSetup()
		if self["config"].getCurrent()[0] == _("Timeshift location"):
			self.checkReadWriteDir(self["config"].getCurrent()[1])
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())


	def checkReadWriteDir(self, configele):
		import os.path
		import Components.Harddisk
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts() 
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(configele.value))+'/' in locations:
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
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%res,
					type = MessageBox.TYPE_ERROR
					)
				return False
		else:
			self.session.open(
				MessageBox,
				_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%res,
				type = MessageBox.TYPE_ERROR
				)
			return False

	def createSetup(self):
		default = config.usage.timeshift_path.value
		tmp = config.usage.allowed_timeshift_paths.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print "TimeshiftPath: ", default, tmp
		self.timeshift_dirname = ConfigSelection(default = default, choices = tmp)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.list = []
		self.timeshift_entry = getConfigListEntry(_("Timeshift location"), self.timeshift_dirname)
		self.list.append(self.timeshift_entry)
		self.list.append(getConfigListEntry(_("Permanent Timeshift Enable"), config.timeshift.enabled))
		if config.usage.setup_level.index >= 2 and config.timeshift.enabled.value:
			self.list.append(getConfigListEntry(_("Permanent Timeshift Max Events"), config.timeshift.maxevents))
			self.list.append(getConfigListEntry(_("Permanent Timeshift Max Length"), config.timeshift.maxlength))
			self.list.append(getConfigListEntry(_("Permanent Timeshift Start Delay"), config.timeshift.startdelay))
			self.list.append(getConfigListEntry(_("Timeshift-Save Action on zap"), config.timeshift.favoriteSaveAction))
			self.list.append(getConfigListEntry(_("Stop timeshift while recording?"), config.timeshift.stopwhilerecording))
			self.list.append(getConfigListEntry(_("Show PTS Infobar while timeshifting?"), config.timeshift.showinfobar))
		self["config"].setList(self.list)

	def ok(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.value
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.value
		if currentry == self.timeshift_entry:
			self.entrydirname = self.timeshift_dirname
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			self.session.openWithCallback(
				self.dirnameSelected,
				TimeshiftLocationBox
			)

	def dirnameSelected(self, res):
		if res is not None:
			import os.path
			import Components.Harddisk
			supported_filesystems = frozenset(('ext4', 'ext3', 'ext2'))
			candidates = []
			mounts = Components.Harddisk.getProcMounts() 
			for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
				if partition.filesystem(mounts) in supported_filesystems:
					candidates.append((partition.description, partition.mountpoint)) 
			if candidates:
				locations = []
				for validdevice in candidates:
					locations.append(validdevice[1])
				if Components.Harddisk.findMountPoint(os.path.realpath(res))+'/' in locations:
					self.entrydirname.value = res
					if config.usage.allowed_timeshift_paths.value != self.lasttimeshiftdirs:
						tmp = config.usage.allowed_timeshift_paths.value
						default = self.timeshift_dirname.value
						if default not in tmp:
							tmp = tmp[:]
							tmp.append(default)
						self.timeshift_dirname.setChoices(tmp, default=default)
						self.entrydirname.value = res
				else:
					self.session.open(
						MessageBox,
						_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%res,
						type = MessageBox.TYPE_ERROR
						)
			else:
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%res,
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
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts() 
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint)) 
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(config.usage.timeshift_path.value))+'/' in locations:
				config.usage.timeshift_path.value = self.timeshift_dirname.value
				config.usage.timeshift_path.save()
				self.saveAll()
				self.close()
			else:
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
					type = MessageBox.TYPE_ERROR
					)
		else:
			self.session.open(
				MessageBox,
				_("The directory %s is not a EXT2, EXT3 or EXT4 partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
				type = MessageBox.TYPE_ERROR
				)
	
	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
