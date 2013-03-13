from Screens.InfoBar import InfoBar
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.config import config, getConfigListEntry
from enigma import eEPGCache
from time import time

class SleepTimerEdit(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["SleepTimerSetup", "Setup"]
		self.setup_title = _("SleepTimer Configuration")
		self.onChangedEntry = [ ]

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label("")

		self.list = []
		self.list.append(getConfigListEntry(_("Sleeptimer"),
			config.usage.sleep_timer,
			_("Configure the duration in minutes and action (shut down or standby) for the sleeptimer. Select this entry and click OK or green to start/stop the sleeptimer")))
		self.list.append(getConfigListEntry(_("Action when receiver is not controlled"),
			config.usage.inactivity_timer,
			_("Configure the duration in hours and action (shut down or standby) when the receiver is not controlled.")))

		ConfigListScreen.__init__(self, self.list, session = session)
		
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.ok,
		    "red": self.cancel,
		    "cancel": self.cancel,
		    "ok": self.ok,
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def ok(self):
		config.usage.sleep_timer.save()
		config.usage.inactivity_timer.save()
		if self.getCurrentEntry() == _("Sleeptimer"):
			sleepTimer = config.usage.sleep_timer.value
			if sleepTimer == "event_shutdown":
				sleepTimer = -self.currentEventTime()
			elif sleepTimer == "event_standby":
				sleepTimer = self.currentEventTime()
			else:
				sleepTimer = int(sleepTimer)
			InfoBar.instance.setSleepTimer(sleepTimer)
			self.close(True)
		self.close()

	def cancel(self, answer = None):
		if answer is None:
			if self["config"].isChanged():
				self.session.openWithCallback(self.cancel, MessageBox, _("Really close without saving settings?"))
			else:
				self.close()
		elif answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

	def currentEventTime(self):
		remaining = 0
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
		return remaining + config.recording.margin_after.value * 60
