from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigNothing
from Components.Label import Label

from Tools.ISO639 import LanguageCodes

class Subtitles(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
        
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.infobar = self.session.infobar
		if self.subtitlesEnabled():
			self.list.append(getConfigListEntry(_("Disable Subtitles"), ConfigNothing(), None))
			sel = self.infobar.selected_subtitle
		else:
			sel = None
		for x in self.getSubtitleList():
			if sel and sel[:4] == x[:4]: #ignore Language code in compare
				text = _("Running")
			else:
				text = _("Enable")
			if x[0] == 0:
				self.list.append(getConfigListEntry(text+" DVB "+LanguageCodes[x[4]][0], ConfigNothing(), x))
			elif x[0] == 1:
				if x[4] == 'und': #undefined
					self.list.append(getConfigListEntry(text+" TTX "+_("Page")+" "+str(x[2])+"/"+str(x[3]), ConfigNothing(), x))
				else:
					self.list.append(getConfigListEntry(text+" TTX "+LanguageCodes[x[4]][0], ConfigNothing(), x))
#		return _("Disable subtitles")
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def getSubtitleList(self):
		s = self.infobar and self.infobar.getCurrentServiceSubtitle()
		l = s and s.getSubtitleList() or [ ]
		return l

	def subtitlesEnabled(self):
		return self.infobar.subtitles_enabled

	def enableSubtitle(self, subtitles):
		if self.infobar.selected_subtitle != subtitles:
			self.infobar.subtitles_enabled = False
			self.infobar.selected_subtitle = subtitles
			self.infobar.subtitles_enabled = True

	def disableSubtitles(self):
		self.infobar.subtitles_enabled = False

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def ok(self):
		if len(self.list):
			cur = self["config"].getCurrent()
			self.enableSubtitle(cur[2])
		self.close(1)

	def cancel(self):
		self.close()
