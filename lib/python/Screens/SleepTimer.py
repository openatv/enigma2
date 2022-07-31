from time import time

from enigma import eEPGCache, eTimer

from Components.config import config
from Screens.InfoBar import InfoBar
from Screens.Setup import Setup


class SleepTimer(Setup):
	def __init__(self, session, setupMode=True):
		if not InfoBar and not InfoBar.instance:
			self.close()
		self.setupMode = setupMode
		Setup.__init__(self, session=session, setup="SleepTimer")
		self.timer = eTimer()
		self.timer.callback.append(self.timeout)
		self.timer.start(250)
		self.onClose.append(self.clearTimer)

	def selectionChanged(self):  # This is from Setup.py but it does not clear the footnote which stops the footnote flashing on the screen.
		self["description"].text = self.getCurrentDescription() if self["config"] else _("There are no items currently available for this screen.")

	def keySave(self):
		sleepTimer = config.usage.sleepTimer.value
		if sleepTimer == -1:
			sleepTimer = 0  # Default sleep timer if the event end time can't be determined, default is the sleep timer is disabled.
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref:
				path = ref.getPath()
				if path:  # Movie
					service = self.session.nav.getCurrentService()
					seek = service and service.seek()
					if seek:
						length = seek.getLength()
						position = seek.getPlayPosition()
						if length and position:
							sleepTimer = length[1] - position[1]
							if sleepTimer > 0:
								sleepTimer = int(sleepTimer // 90000)
				else:  # Service
					epg = eEPGCache.getInstance()
					event = epg.lookupEventTime(ref, -1, 0)
					if event:
						sleepTimer = event.getBeginTime() + event.getDuration() - int(time())
				sleepTimer += (config.recording.margin_after.value * 60)
		InfoBar.instance.setSleepTimer(sleepTimer)
		InfoBar.instance.setEnergyTimer(config.usage.energyTimer.value)
		Setup.keySave(self)

	def timeout(self):
		sleepTimer = InfoBar.instance.sleepTimerState()
		if sleepTimer > 60:
			sleepTimer //= 60
			sleepMsg = ngettext("SleepTimer: %d minute remains.", "SleepTimer: %d minutes remain.", sleepTimer) % sleepTimer
		elif sleepTimer:
			sleepMsg = ngettext("SleepTimer: %d second remains.", "SleepTimer: %d seconds remain.", sleepTimer) % sleepTimer
		else:
			sleepMsg = _("SleepTimer: Inactive.")
		energyTimer = InfoBar.instance.energyTimerState()
		if energyTimer > 60:
			energyTimer //= 60
			energyMsg = ngettext("Energy Timer: %d minute remains.", "Energy Timer: %d minutes remain.", energyTimer) % energyTimer
		elif energyTimer:
			energyMsg = ngettext("Energy Timer: %d second remains.", "Energy Timer: %d seconds remain.", energyTimer) % energyTimer
		else:
			energyMsg = _("Energy Timer: Inactive.")
		self.setFootnote("%s   %s" % (sleepMsg, energyMsg))
		self.timer.start(250)

	def clearTimer(self):
		self.timer.stop()
		self.timer.callback.remove(self.timeout)


class SleepTimerButton(SleepTimer):
	def __init__(self, session):
		SleepTimer.__init__(self, session, setupMode=False)

	def keySelect(self):
		SleepTimer.keySave(self)
