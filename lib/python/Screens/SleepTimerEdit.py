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

	skin = """
	<screen name="SleepTimerEdit" position="center,center" size="500,250"  flags="wfNoBorder" title="Sleep Timer" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="500,250" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="498,248" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="10,10" foregroundColor="#00ffffff" size="480,50" halign="center" font="Regular; 35" backgroundColor="#00000000" />
		<eLabel name="line" position="1,69" size="498,1" backgroundColor="#00ffffff" zPosition="1" />
		<widget name="config" position="10,90" size="480,60" itemHeight="30" font="Regular; 20" enableWrapAround="1" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget name="description" position="10,160" size="480,26" font="Regular; 16" foregroundColor="#00ffffff" halign="center" backgroundColor="#00000000" valign="center" />
		<widget source="key_red" render="Label" position="35,212" size="170,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="228,212" size="170,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<eLabel position="25,209" size="6,40" backgroundColor="#00e61700" />
		<eLabel position="216,209" size="6,40" backgroundColor="#0061e500" />
	</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.title = _("Sleep Timer")

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label("")

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.createSetup()

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.save,
			"red": self.cancel,
			"cancel": self.cancel,
			"ok": self.save,
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.title)

	def createSetup(self):
		self.list = []

		if not InfoBar and not InfoBar.instance:
			self.close()
		elif InfoBar.instance and InfoBar.instance.sleepTimer.isActive():
			statusSleeptimerText = _("Timer is activated: +%d min") % InfoBar.instance.sleepTimerState()
		else:
			statusSleeptimerText = _("Timer is not activated")

		self.list.append(getConfigListEntry(statusSleeptimerText, config.usage.sleep_timer, _("Configure the duration in minutes for the sleep timer.")))
		self.list.append(getConfigListEntry(_("Timer action"), config.usage.sleep_timer_action, _("Select the sleep timer action.")))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def save(self):
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].save()
		sleepTimer = config.usage.sleep_timer.value
		if sleepTimer == "event_standby":
			sleepTimer = self.useServiceTime()
		else:
			sleepTimer = int(sleepTimer)
		if sleepTimer or not self.getCurrentEntry().endswith(_("not activated")):
			InfoBar.instance.setSleepTimer(sleepTimer)
		self.close(True)

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

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def useServiceTime(self):
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
