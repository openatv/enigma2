from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Tools.Notifications import AddPopup
from enigma import eEPGCache
from time import time

class SleepTimerEdit(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["current_status"] = Label()
		try:
			self.is_active = self.session.nav.SleepTimer.isActive()
		except:
			self.close()
			return
		if self.is_active:
			config.SleepTimer.defaulttime.setValue(self.session.nav.SleepTimer.getCurrentSleepTime())
		else:
			config.SleepTimer.enabled.setValue(False)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"],
		{
		  "cancel": self.keyCancel,
		  "save": self.keySave,
		  "menu": self.keyCancel,
		}, -2)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self.is_active = self.session.nav.SleepTimer.isActive()
		if self.is_active:
			self["current_status"].setText(_("Timer status:") + " " + _("Enabled"))
		else:
			self["current_status"].setText(_("Timer status:") + " " + _("Disabled"))

	# for summary:
	def changedEntry(self):
		self.is_active = self.session.nav.SleepTimer.isActive()
		if self["config"].getCurrent()[0] == _("Enable timer"):
			self.createSetup()
		elif self["config"].getCurrent()[0] == _("Use time of currently running service"):
			if config.SleepTimer.servicetime.value:
				self.useServiceTime()
			else:
				if self.is_active:
					config.SleepTimer.defaulttime.setValue(self.session.nav.SleepTimer.getCurrentSleepTime())
			self.createSetup()
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enable timer"), config.SleepTimer.enabled))
		if config.SleepTimer.enabled.value:
			self.list.append(getConfigListEntry(_("Use time of currently running service"), config.SleepTimer.servicetime))
			self.list.append(getConfigListEntry(_("Shutdown in (mins)"), config.SleepTimer.defaulttime))
			self.list.append(getConfigListEntry(_("Action"), config.SleepTimer.action))
			self.list.append(getConfigListEntry(_("Ask before shutdown"), config.SleepTimer.ask))

		self["config"].list = self.list
		self["config"].setList(self.list)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keySave(self):
		if config.SleepTimer.enabled.value:
			for x in self["config"].list:
				x[1].save()
			self.session.nav.SleepTimer.setSleepTime(config.SleepTimer.defaulttime.value)
			AddPopup(_("The sleep timer has been activated."), type = MessageBox.TYPE_INFO, timeout = 3)
			self.close(True)
		else:
			self.session.nav.SleepTimer.clear()
			AddPopup(_("The sleep timer has been disabled."), type = MessageBox.TYPE_INFO, timeout = 3)
			self.close(True)

	def useServiceTime(self):
		remaining = None
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if ref:
			path = ref.getPath()
			if path: # Movie
				service = self.session.nav.getCurrentService()
				seek = service and service.seek()
				if seek:
					length = seek.getLength()
					position = seek.getPlayPosition()
					if length and position:
						remaining = length[1] - position[1]
						if remaining > 0:
							remaining = remaining / 90000
			else: # DVB
				epg = eEPGCache.getInstance()
				event = epg.lookupEventTime(ref, -1, 0)
				if event:
					now = int(time())
					start = event.getBeginTime()
					duration = event.getDuration()
					end = start + duration
					remaining = end - now
		if remaining:
			config.SleepTimer.defaulttime.setValue((remaining / 60) + 2)
