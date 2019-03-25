from Screens.Screen import Screen
from Screens.Setup import setupdom
from Screens.LocationBox import TimeshiftLocationBox
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
		Screen.__init__(self, session, parent=parent)
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
		if hasattr(self.parent, "getCurrentDescription"):
			self.parent["description"].text = self.parent.getCurrentDescription()
		if self.parent.has_key('footnote'):
			if self.parent.getCurrentEntry().endswith('*'):
				self.parent['footnote'].text = _("* = Restart Required")
			else:
				self.parent['footnote'].text = ""

class TimeshiftSettings(Screen, ConfigListScreen):
	def removeNotifier(self):
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

	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		self.menu_path = menu_path
		self.skinName = "Setup"
		self["menu_path_compressed"] = StaticText()
		self['footnote'] = Label()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label("")

		self.onChangedEntry = []
		self.setup = "timeshift"
		list = []
		ConfigListScreen.__init__(self, list, session=session, on_change=self.changedEntry)
		self.createSetup()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"], {
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

	def checkTSFS(self, path, showError=True):
		from os import link, unlink, tempnam
		temp = tempnam(path, 'ts')
		try:
			open(temp, 'w').close()
			try:
				link(temp, temp + '.link')
				unlink(temp + '.link')
				linkable = True
			except:
				linkable = False
			finally:
				unlink(temp)
			if linkable:
				return True
		except:
			pass
		if showError:
			self.session.open(
				MessageBox,
				_("The directory %s does not support hard links.\nMake sure you select a valid partition type.") % path,
				type=MessageBox.TYPE_ERROR
			)
		return False

	def checkReadWriteDir(self, configele):
		if self.checkTSFS(configele.value):
			if fileExists(configele.value, "w"):
				configele.last_value = configele.value
				return True

			self.session.open(
				MessageBox,
				_("The directory %s is not writable.\nMake sure you select a writable directory instead.") % configele.value,
				type=MessageBox.TYPE_ERROR
			)
		configele.value = configele.last_value
		return False

	def createSetup(self):
		default = config.usage.timeshift_path.value
		tmp = config.usage.allowed_timeshift_paths.value
		if default not in tmp:
			tmp = tmp[:]
			tmp.append(default)
# 		print "TimeshiftPath: ", default, tmp
		self.timeshift_dirname = ConfigSelection(default=default, choices=tmp)
		self.timeshift_dirname.addNotifier(self.checkReadWriteDir, initial_call=False, immediate_feedback=False)
		list = []
		self.timeshift_entry = getConfigListEntry(_("Timeshift location"), self.timeshift_dirname, _("Set the default location for your timeshift-files. Press 'OK' to add new locations, select left/right to select an existing location."))
		list.append(self.timeshift_entry)

		self.refill(list)
		self["config"].setList(list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def layoutFinished(self):
		if config.usage.show_menupath.value == 'large' and self.menu_path:
			title = self.menu_path + _(self.setup_title)
			self["menu_path_compressed"].setText("")
		elif config.usage.show_menupath.value == 'small':
			title = _(self.setup_title)
			self["menu_path_compressed"].setText(self.menu_path + " >" if not self.menu_path.endswith(' / ') else self.menu_path[:-3] + " >" or "")
		else:
			title = _(self.setup_title)
			self["menu_path_compressed"].setText("")
		self.setup_title = title
		self.setTitle(title)

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
			if self.checkTSFS(res):
				self.entrydirname.value = res
				if config.usage.allowed_timeshift_paths.value != self.lasttimeshiftdirs:
					tmp = config.usage.allowed_timeshift_paths.value
					default = self.timeshift_dirname.value
					if default not in tmp:
						tmp = tmp[:]
						tmp.append(default)
					self.timeshift_dirname.setChoices(tmp, default=default)
					self.entrydirname.value = res

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		ts_enabled = int(config.timeshift.startdelay.value) > 0
		if self.checkTSFS(config.usage.timeshift_path.value, ts_enabled):
			config.usage.timeshift_path.value = self.timeshift_dirname.value
			config.usage.timeshift_path.save()
			self.saveAll()
			self.close()
		else:
			if not ts_enabled:
				config.timeshift.startdelay.value = "0"
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
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
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

				if self.levelChanged not in config.usage.setup_level.notifiers:
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
				# add to configlist
				item = b
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				if not isinstance(item, ConfigNothing):
					list.append((item_text, item, item_description))
