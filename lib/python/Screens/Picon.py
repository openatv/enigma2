from os.path import isdir

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Sources.StaticText import StaticText
from Screens.LocationBox import LocationBox, DEFAULT_INHIBIT_DIRECTORIES
from Screens.Setup import Setup


class PiconSettings(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "Picon")
		self["key_yellow"] = StaticText(_("Add Path"))
		self["key_blue"] = StaticText(_("Remove Path"))
		self["actions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _("Add Path")),
			"blue": (self.keyBlue, _("Remove Path"))
		}, prio=0)
		self.updateButtons()

	def keyYellow(self):
		if not config.picon.set3.path.value:
			newPath = None
			for index in range(1, 4):
				path = getattr(config.picon, f"set{index}").path
				if not path.value:
					path.value = getattr(config.picon, f"set{index - 1}").path.value
					newPath = path
					break
			self.createSetup()
			self.updateButtons()
			self.openLocationBox(newPath)

	def keyBlue(self):
		settings = (config.picon.infobar, config.picon.channelselection, config.picon.display, config.picon.openwebif)
		for index in range(3, 0, -1):
			path = getattr(config.picon, f"set{index}").path
			if path.value:
				if any(setting.value == index for setting in settings):
					self.setFootnote(_("Picon path %s is in use and cannot be removed!") % (index + 1))
				else:
					path.value = ""
					self.createSetup()
					self.updateButtons()
				break

	def keySave(self):
		for index in range(4):
			path = getattr(config.picon, f"set{index}").path.value
			if path and not isdir(path):
				self.setFootnote(_("Directory '%s' does not exist!") % path)
				return
		Setup.keySave(self)

	def updateButtons(self):
		yellowText = "" if config.picon.mode.value == 0 or config.picon.set3.path.value else _("Add Path")
		blueText = _("Remove Path") if config.picon.mode.value == 1 and config.picon.set1.path.value else ""
		self["key_yellow"].setText(yellowText)
		self["key_blue"].setText(blueText)
		self["actions"].setEnabledAction("yellow", yellowText != "")
		self["actions"].setEnabledAction("blue", blueText != "")

	def keySelect(self):
		current = self.getCurrentItem()
		paths = [getattr(config.picon, f"set{i}").path for i in range(4)]
		if current in paths:
			self.openLocationBox(current)
		else:
			Setup.keySelect(self)

	def openLocationBox(self, current):
		def callback(path):
			if path is not None:
				current.value = path
			self["config"].invalidateCurrent()

		self.session.openWithCallback(
			callback,
			LocationBox,
			windowTitle=_("Select Picon Directory"),
			text=_("What do you want to set as the picon location?"),
			currDir=current.value or "/",
			bookmarks=config.picon.allowedPaths,
			minFree=0,
			editDir=True,
			inhibitDirs=tuple(d for d in DEFAULT_INHIBIT_DIRECTORIES if d not in ("/picon", "/piconlcd", "/usr"))
		)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.pathStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.pathStatus()

	def pathStatus(self):
		current = self.getCurrentItem()
		paths = [getattr(config.picon, f"set{i}").path for i in range(4)]
		if current in paths:
			path = self.getCurrentValue()
			if not isdir(path):
				footnote = _("Directory '%s' does not exist!") % path
			else:
				footnote = ""
			self.setFootnote(footnote)
			choices = [(x, _("Picon path %s") % (x + 1)) for x in range(4) if x == 0 or getattr(config.picon, f"set{x}").path.value]
			for cfg in (config.picon.infobar, config.picon.channelselection, config.picon.display, config.picon.openwebif):
				cfg.setChoices(choices)
