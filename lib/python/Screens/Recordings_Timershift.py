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
		self.setup_title = _("Recording settings")
		Screen.setTitle(self, _(self.setup_title))
		self["status"] = StaticText()
		self['footnote'] = Label()
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
		if not self.SelectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.SelectionChanged)

	def checkReadWriteDir(self, configele):
		print "checkReadWrite: ", configele.getValue()
		if configele.getValue() in [x[0] for x in self.styles] or fileExists(configele.value, "w"):
			configele.last_value = configele.getValue()
			return True
		else:
			dir = configele.getValue()
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
		tmp = config.movielist.videodirs.getValue()
		default = config.usage.default_path.getValue()
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print "DefaultPath: ", default, tmp
		self.default_dirname = ConfigSelection(default = default, choices = tmp)
		tmp = config.movielist.videodirs.getValue()
		default = config.usage.timer_path.getValue()
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
		print "TimerPath: ", default, tmp
		self.timer_dirname = ConfigSelection(default = default, choices = self.styles+tmp)
		tmp = config.movielist.videodirs.getValue()
		default = config.usage.instantrec_path.getValue()
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
			self.default_entry = getConfigListEntry(_("Default movie location"), self.default_dirname, _("Set the default location for your recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			self.list.append(self.default_entry)
			self.timer_entry = getConfigListEntry(_("Timer record location"), self.timer_dirname, _("Set the default location for your timers. Press 'OK' to add new locations, select left/right to select an existing location."))
			self.list.append(self.timer_entry)
			self.instantrec_entry = getConfigListEntry(_("Instant record location"), self.instantrec_dirname, _("Set the default location for your instant recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			self.list.append(self.instantrec_entry)
		else:
			self.default_entry = getConfigListEntry(_("Movie location"), self.default_dirname, _("Set the default location for your recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			self.list.append(self.default_entry)

		if config.usage.setup_level.index >= 1:
			self.list.append(getConfigListEntry(_("Recordings always have priority"), config.recording.asktozap, _("Select 'Yes' if you want recordings to have priority over live-TV.")))
		self.list.append(getConfigListEntry(_("Margin before record (minutes)"), config.recording.margin_before, _("Set the time you want recordings to start before the event start-time.")))
		self.list.append(getConfigListEntry(_("Margin after record"), config.recording.margin_after, _("Set the time you want recordings to stop after the event stop-time.")))
		if config.usage.setup_level.index >= 2:
			self.list.append(getConfigListEntry(_("Show Message when Recording starts"), config.usage.show_message_when_recording_starts, _("Do you want a pop-up message saying 'a recording has started'?")))
			self.list.append(getConfigListEntry(_("Behavior when a movie is started"), config.usage.on_movie_start, _("On starting playback of a file, you can choose the box's behaviour.")))
			self.list.append(getConfigListEntry(_("Behavior when a movie is stopped"), config.usage.on_movie_stop, _("On stopping playback of a file, you can choose the box's behaviour.")))
			self.list.append(getConfigListEntry(_("Behavior when a movie reaches the end"), config.usage.on_movie_eof, _("On reaching the end of a file during playback, you can choose the box's behaviour.")))
			self.list.append(getConfigListEntry(_("Behavior of 'pause' when paused"), config.seek.on_pause, _("Here you can select the behaviour of the 'puase'-button when playback has been paused.")))
			self.list.append(getConfigListEntry(_("Custom skip time for '1'/'3'-keys"), config.seek.selfdefined_13, _("Set the skip-forward/backward time of the 1-3 number keys.")))
			self.list.append(getConfigListEntry(_("Custom skip time for '4'/'6'-keys"), config.seek.selfdefined_46, _("Set the skip-forward/backward time of the 4-6 number keys.")))
			self.list.append(getConfigListEntry(_("Custom skip time for '7'/'9'-keys"), config.seek.selfdefined_79, _("Set the skip-forward/backward time of the 7-9 number keys.")))
			self.list.append(getConfigListEntry(_("Display message before next played movie"), config.usage.next_movie_msg, _("Show a popup message after a recording has finished and before start next in queue.")))
			self.list.append(getConfigListEntry(_("Seekbar activation"), config.seek.baractivation, _("Select seekbar to be activated by arrow L/R (long) or << >> (long).")))
			self.list.append(getConfigListEntry(_("Seekbar sensibility"), config.seek.sensibility, _("Set the jump-size of the seekbar.")))
			self.list.append(getConfigListEntry(_("Fast Forward speeds"), config.seek.speeds_forward, _("Set the values for fast-forward speeds.")))
			self.list.append(getConfigListEntry(_("Rewind speeds"), config.seek.speeds_backward, _("Set the values for fast-backward speeds.")))
			self.list.append(getConfigListEntry(_("Slow Motion speeds"), config.seek.speeds_slowmotion, _("Set the values for slow-motion speeds.")))
			self.list.append(getConfigListEntry(_("Initial Fast Forward speed"), config.seek.enter_forward, _("Set the value for the initial fast-forward speed.")))
			self.list.append(getConfigListEntry(_("Initial Rewind speed"), config.seek.enter_backward, _("Set the value for the initial fast-backward speed.")))
			self.list.append(getConfigListEntry(_("Limited character set for recording filenames"), config.recording.ascii_filenames, _("Select 'Yes' if you want only a small number of characters to be used for recording names.")))
			self.list.append(getConfigListEntry(_("Composition of the recording filenames"), config.recording.filename_composition, _("Select how you want recording names to be populated.")))
			self.list.append(getConfigListEntry(_("Keep old timers for how many days"), config.recording.keep_timers, _("Set the number of days you want old timers to be kept.")))
		if config.usage.setup_level.index >= 1:
			self.list.append(getConfigListEntry(_("Use trashcan in movielist"), config.usage.movielist_trashcan, _("If set to 'Yes' recordings will be deleted to a trashcan. That way thay can still be played.")))
			self.list.append(getConfigListEntry(_("Remove items from trash after (days)"), config.usage.movielist_trashcan_days, _("Select the number of days after which the box is allowed to permanently delete recordings (from the trashcan).")))
			self.list.append(getConfigListEntry(_("Disk space to reserve for recordings (in GB)"), config.usage.movielist_trashcan_reserve, _("Items in trashcan will be deleted if less then the set space is available.")))
		if config.usage.setup_level.index >= 2:
			self.list.append(getConfigListEntry(_("Background delete option"), config.misc.erase_flags, _("Only change for debugging; default is 'Internal hdd only'.")))
			self.list.append(getConfigListEntry(_("Background delete speed"), config.misc.erase_speed, _("Only change for debugging; default is '20 MB/s'.")))
			self.list.append(getConfigListEntry(_("Offline decode delay (ms)"), config.recording.offline_decode_delay, _("Change this value if your smartcard can't doesn't handle off-line decoding well; default is '1000'.")))
		self["config"].setList(self.list)
		if config.usage.sort_settings.getValue():
			self["config"].list.sort()

	def SelectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

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
		self.lastvideodirs = config.movielist.videodirs.getValue()
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.getValue()
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
				preferredPath(self.default_dirname.getValue())
			)
		elif currentry == self.timer_entry:
			self.entrydirname = self.timer_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("New timers location"),
				preferredPath(self.timer_dirname.getValue())
			)
		elif currentry == self.instantrec_entry:
			self.entrydirname = self.instantrec_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("Instant recordings location"),
				preferredPath(self.instantrec_dirname.getValue())
			)

	def dirnameSelected(self, res):
		if res is not None:
			self.entrydirname.value = res
			if config.movielist.videodirs.getValue() != self.lastvideodirs:
				styles_keys = [x[0] for x in self.styles]
				tmp = config.movielist.videodirs.getValue()
				default = self.default_dirname.getValue()
				if default not in tmp:
					tmp = tmp[:]
					tmp.append(default)
				self.default_dirname.setChoices(tmp, default=default)
				tmp = config.movielist.videodirs.getValue()
				default = self.timer_dirname.getValue()
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.timer_dirname.setChoices(self.styles+tmp, default=default)
				tmp = config.movielist.videodirs.getValue()
				default = self.instantrec_dirname.getValue()
				if default not in tmp and default not in styles_keys:
					tmp = tmp[:]
					tmp.append(default)
				self.instantrec_dirname.setChoices(self.styles+tmp, default=default)
				self.entrydirname.value = res
			if self.entrydirname.last_value != res:
				self.checkReadWriteDir(self.entrydirname)

	def saveAll(self):
		currentry = self["config"].getCurrent()
		config.usage.default_path.value = self.default_dirname.getValue()
		config.usage.timer_path.value = self.timer_dirname.getValue()
		config.usage.instantrec_path.value = self.instantrec_dirname.getValue()
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
		self.setup_title = _("Timeshift settings")
		Screen.setTitle(self, _(self.setup_title))
		self["status"] = StaticText()
		self['footnote'] = Label(_("* = Restart timeshift required"))
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
		if not self.SelectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.SelectionChanged)

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
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts()
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(configele.getValue()))+'/' in locations or Components.Harddisk.findMountPoint(os.path.realpath(configele.getValue())) in locations:
				if fileExists(configele.value, "w"):
					configele.last_value = configele.getValue()
					return True
				else:
					dir = configele.getValue()
					configele.value = configele.last_value
					self.session.open(
						MessageBox,
						_("The directory %s is not writable.\nMake sure you select a writable directory instead.")%dir,
						type = MessageBox.TYPE_ERROR
						)
					return False
			else:
				dir = configele.getValue()
				configele.value = configele.last_value
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%dir,
					type = MessageBox.TYPE_ERROR
					)
				return False
		else:
			dir = configele.getValue()
			configele.value = configele.last_value
			self.session.open(
				MessageBox,
				_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%dir,
				type = MessageBox.TYPE_ERROR
				)
			return False

	def createSetup(self):
		default = config.usage.timeshift_path.getValue()
		tmp = config.usage.allowed_timeshift_paths.getValue()
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print "TimeshiftPath: ", default, tmp
		self.timeshift_dirname = ConfigSelection(default = default, choices = tmp)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.list = []
		self.timeshift_entry = getConfigListEntry(_("Timeshift location"), self.timeshift_dirname, _("Set the default location for your timeshift-files. Press 'OK' to add new locations, select left/right to select an existing location."))
		self.list.append(self.timeshift_entry)
		self.list.append(getConfigListEntry(_("Permanent Timeshift Enable"), config.timeshift.enabled, _("Enable or disable Permanent Timeshift. When activated, you can wind back until the time you zapped to a channel, and you can make recordings in retrospect.")))
		if config.usage.setup_level.index >= 2 and config.timeshift.enabled.getValue():
			self.list.append(getConfigListEntry(_("Permanent Timeshift Max Events"), config.timeshift.maxevents, _("Set the maximum number of events (programs) that timeshift may handle.")))
			self.list.append(getConfigListEntry(_("Permanent Timeshift Max Length"), config.timeshift.maxlength, _("Set the maximum length a timeshift file may be.")))
			self.list.append(getConfigListEntry(_("Permanent Timeshift Start Delay"), config.timeshift.startdelay, _("Timeshift will only start when the start delay time has passed. This prevents numurous very short files when zapping.")))
			self.list.append(getConfigListEntry(_("Stop timeshift while recording?"), config.timeshift.stopwhilerecording, _("Select if timeshift must continue when set to record.")))
			self.list.append(getConfigListEntry(_("Timeshift-Save Action on zap"), config.timeshift.favoriteSaveAction, _("Set what the required action must be when zapping while a timeshift has been set as recording.")))
			self.list.append(getConfigListEntry(_("Use PTS seekbar while timeshifting? *"), config.timeshift.showinfobar, _("If set to 'yes' a special seekbar is available during timeshift.")))
		self["config"].setList(self.list)
		if config.usage.sort_settings.getValue():
			self["config"].list.sort()

	def SelectionChanged(self):
		self["status"].setText(self["config"].getCurrent()[2])

	def ok(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.getValue()
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.getValue()
		if currentry == self.timeshift_entry:
			self.entrydirname = self.timeshift_dirname
			config.usage.timeshift_path.value = self.timeshift_dirname.getValue()
			self.session.openWithCallback(
				self.dirnameSelected,
				TimeshiftLocationBox
			)

	def dirnameSelected(self, res):
		if res is not None:
			import os.path
			import Components.Harddisk
			supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs'))
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
					if config.usage.allowed_timeshift_paths.getValue() != self.lasttimeshiftdirs:
						tmp = config.usage.allowed_timeshift_paths.getValue()
						default = self.timeshift_dirname.getValue()
						if default not in tmp:
							tmp = tmp[:]
							tmp.append(default)
						self.timeshift_dirname.setChoices(tmp, default=default)
						self.entrydirname.value = res
				else:
					self.session.open(
						MessageBox,
						_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%res,
						type = MessageBox.TYPE_ERROR
						)
			else:
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%res,
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
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'nfs'))
		candidates = []
		mounts = Components.Harddisk.getProcMounts()
		for partition in Components.Harddisk.harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint))
		if candidates:
			locations = []
			for validdevice in candidates:
				locations.append(validdevice[1])
			if Components.Harddisk.findMountPoint(os.path.realpath(config.usage.timeshift_path.getValue()))+'/' in locations or Components.Harddisk.findMountPoint(os.path.realpath(config.usage.timeshift_path.getValue())) in locations:
				config.usage.timeshift_path.value = self.timeshift_dirname.getValue()
				config.usage.timeshift_path.save()
				self.saveAll()
				self.close()
			else:
				if config.timeshift.enabled.getValue():
					self.session.open(
						MessageBox,
						_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
						type = MessageBox.TYPE_ERROR
						)
				else:
					config.timeshift.enabled.setValue(False)
					self.saveAll()
					self.close()
		else:
			if config.timeshift.enabled.getValue():
				self.session.open(
					MessageBox,
					_("The directory %s is not a EXT2, EXT3, EXT4 or NFS partition.\nMake sure you select a valid partition type.")%config.usage.timeshift_path.value,
					type = MessageBox.TYPE_ERROR
					)
			else:
				config.timeshift.enabled.setValue(False)
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
