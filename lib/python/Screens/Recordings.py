from Screens.Screen import Screen
from Screens.Setup import setupdom
from Screens.LocationBox import MovieLocationBox
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.config import config, configfile, ConfigYesNo, ConfigNothing, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Tools.Directories import fileExists
from Components.UsageConfig import preferredPath
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

class RecordingSettings(Screen,ConfigListScreen):
	def removeNotifier(self):
		if config.usage.setup_level.notifiers:
			config.usage.setup_level.notifiers.remove(self.levelChanged)

	def removeNotifierRecordFrontendPriority(self):
		if config.usage.recording_frontend_priority.notifiers:
			config.usage.recording_frontend_priority.notifiers.remove(self.levelChanged)

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
		from Components.Sources.StaticText import StaticText
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
		self.setup = "recording"
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

	def checkReadWriteDir(self, configele):
# 		print "checkReadWrite: ", configele.value
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
# 		print "DefaultPath: ", default, tmp
		self.default_dirname = ConfigSelection(default = default, choices = tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.timer_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
# 		print "TimerPath: ", default, tmp
		self.timer_dirname = ConfigSelection(default = default, choices = self.styles+tmp)
		tmp = config.movielist.videodirs.value
		default = config.usage.instantrec_path.value
		if default not in tmp and default not in styles_keys:
			tmp = tmp[:]
			tmp.append(default)
# 		print "InstantrecPath: ", default, tmp
		self.instantrec_dirname = ConfigSelection(default = default, choices = self.styles+tmp)
		self.default_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.timer_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		self.instantrec_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)

		list = []

		if config.usage.setup_level.index >= 2:
			self.default_entry = getConfigListEntry(_("Default movie location"), self.default_dirname, _("Set the default location for your recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			list.append(self.default_entry)
			self.timer_entry = getConfigListEntry(_("Timer recording location"), self.timer_dirname, _("Set the default location for your timers. Press 'OK' to add new locations, select left/right to select an existing location."))
			list.append(self.timer_entry)
			self.instantrec_entry = getConfigListEntry(_("Instant recording location"), self.instantrec_dirname, _("Set the default location for your instant recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			list.append(self.instantrec_entry)
		else:
			self.default_entry = getConfigListEntry(_("Movie location"), self.default_dirname, _("Set the default location for your recordings. Press 'OK' to add new locations, select left/right to select an existing location."))
			list.append(self.default_entry)
			self.timer_entry = self.instantrec_entry = None

		self.refill(list)
		self["config"].setList(list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def layoutFinished(self):
		self.setTitle(_(self.setup_title))

	# for summary:
	def changedEntry(self):
		self.item = self["config"].getCurrent()
		if self["config"].getCurrent()[0] == _("Default movie location") or self["config"].getCurrent()[0] == _("Timer record location") or self["config"].getCurrent()[0] == _("Instant record location") or self["config"].getCurrent()[0] == _("Movie location"):
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

	def ok(self):
		currentry = self["config"].getCurrent()
		self.lastvideodirs = config.movielist.videodirs.value
		self.lasttimeshiftdirs = config.usage.allowed_timeshift_paths.value
		self.lastautorecorddirs = config.usage.allowed_autorecord_paths.value
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
				item_rectunerlevel = int(x.get("rectunerlevel", 0))

				if not self.levelChanged in config.usage.setup_level.notifiers:
					config.usage.setup_level.notifiers.append(self.levelChanged)
					self.onClose.append(self.removeNotifier)
				if not self.levelChanged in config.usage.recording_frontend_priority.notifiers:
					config.usage.recording_frontend_priority.notifiers.append(self.levelChanged)
					self.onClose.append(self.removeNotifierRecordFrontendPriority)

				if item_level > config.usage.setup_level.index:
					continue
				if item_rectunerlevel == 1 and not config.usage.recording_frontend_priority.value in ("expert_mode", "experimental_mode"):
					continue
				if item_rectunerlevel == 2 and not config.usage.recording_frontend_priority.value == "experimental_mode":
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

