from os.path import isdir

from Components.config import config
from Screens.LocationBox import LocationBox, DEFAULT_INHIBIT_DIRECTORIES
from Screens.Setup import Setup


class PiconSettings(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "Picon")

	def keySelect(self):
		def keySelectCallback(path):
			if path is not None:
				current.value = path
			self["config"].invalidateCurrent()

		current = self.getCurrentItem()
		paths = [getattr(config.picon, f"set{i}").path for i in range(5)]
		if current in paths:
			self.session.openWithCallback(
				keySelectCallback,
				LocationBox,
				windowTitle=_("Select Picon Directory"),
				text=_("What do you want to set as the picon location?"),
				currDir=current.value or "/",
				bookmarks=config.picon.allowedPaths,
				minFree=0,
				editDir=True,
				inhibitDirs=tuple(d for d in DEFAULT_INHIBIT_DIRECTORIES if d not in ("/picon", "/piconlcd", "/usr"))
			)
		else:
			Setup.keySelect(self)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		self.pathStatus()

	def changedEntry(self):
		Setup.changedEntry(self)
		self.pathStatus()

	def pathStatus(self):
		current = self.getCurrentItem()
		paths = [getattr(config.picon, f"set{i}").path for i in range(5)]
		if current in paths:
			path = self.getCurrentValue()
			if not isdir(path):
				footnote = _("Directory '%s' does not exist!") % path
			else:
				footnote = ""
			self.setFootnote(footnote)
			choices = [(x, _("Set Path %s") % (x + 1)) for x in range(5) if x == 0 or getattr(config.picon, f"set{x}").path.value]
			for cfg in (config.picon.infobar, config.picon.channelselection, config.picon.display, config.picon.openwebif):
				cfg.setChoices(choices)
