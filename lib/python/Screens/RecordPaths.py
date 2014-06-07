from Screens.Screen import Screen
from Screens.LocationBox import MovieLocationBox, TimeshiftLocationBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.config import config, ConfigSelection, getConfigListEntry, configfile
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Tools.Directories import fileExists
from Components.UsageConfig import preferredPath

class RecordPathsSettings(Screen,ConfigListScreen):
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
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		ConfigListScreen.__init__(self, [])
		self.initConfigList()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
		    "green": self.save,
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

	def initConfigList(self):
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
		default = config.usage.timeshift_path.value
		tmp = config.usage.allowed_timeshift_paths.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
		print "TimeshiftPath: ", default, tmp
		self.timeshift_dirname = ConfigSelection(default = default, choices = tmp)
		self.default_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timer_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.instantrec_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)

		self.list = []
		if config.usage.setup_level.index >= 2:
			self.default_entry = getConfigListEntry(_("Default movie location"), self.default_dirname)
			self.list.append(self.default_entry)
			self.timer_entry = getConfigListEntry(_("Timer recording location"), self.timer_dirname)
			self.list.append(self.timer_entry)
			self.instantrec_entry = getConfigListEntry(_("Instant recording location"), self.instantrec_dirname)
			self.list.append(self.instantrec_entry)
		else:
			self.default_entry = getConfigListEntry(_("Movie location"), self.default_dirname)
			self.list.append(self.default_entry)
		self.timeshift_entry = getConfigListEntry(_("Timeshift location"), self.timeshift_dirname)
		self.list.append(self.timeshift_entry)
		self["config"].setList(self.list)

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
				_("Initial location in new timers"),
				preferredPath(self.timer_dirname.value)
			)
		elif currentry == self.instantrec_entry:
			self.entrydirname = self.instantrec_dirname
			self.session.openWithCallback(
				self.dirnameSelected,
				MovieLocationBox,
				_("Location for instant recordings"),
				preferredPath(self.instantrec_dirname.value)
			)
		elif currentry == self.timeshift_entry:
			self.entrydirname = self.timeshift_dirname
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			self.session.openWithCallback(
				self.dirnameSelected,
				TimeshiftLocationBox
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
			if config.usage.allowed_timeshift_paths.value != self.lasttimeshiftdirs:
				tmp = config.usage.allowed_timeshift_paths.value
				default = self.instantrec_dirname.value
				if default not in tmp:
					tmp = tmp[:]
					tmp.append(default)
				self.timeshift_dirname.setChoices(tmp, default=default)
				self.entrydirname.value = res
			if self.entrydirname.last_value != res:
				self.checkReadWriteDir(self.entrydirname)

	def save(self):
		currentry = self["config"].getCurrent()
		if self.checkReadWriteDir(currentry[1]):
			config.usage.default_path.value = self.default_dirname.value
			config.usage.timer_path.value = self.timer_dirname.value
			config.usage.instantrec_path.value = self.instantrec_dirname.value
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			config.usage.default_path.save()
			config.usage.timer_path.save()
			config.usage.instantrec_path.save()
			config.usage.timeshift_path.save()
			self.close()
