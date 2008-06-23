import timer
import time
import math

from Tools import Notifications

from Components.config import config, ConfigYesNo, ConfigSelection, ConfigSubsection

from Screens.MessageBox import MessageBox
import Screens.Standby

config.SleepTimer = ConfigSubsection()
config.SleepTimer.ask = ConfigYesNo(default = True)
config.SleepTimer.action = ConfigSelection(default = "shutdown", choices = [("shutdown", _("shutdown")), ("standby", _("standby"))])

class SleepTimerEntry(timer.TimerEntry):
	def __init__(self, begin):
		timer.TimerEntry.__init__(self, int(begin), int(begin))
		
		self.prepare_time = 0
		
	def getNextActivation(self):
		return self.begin
		
	def activate(self):
		if self.state == self.StateRunning:
			if config.SleepTimer.action.value == "shutdown":
				if config.SleepTimer.ask.value and not Screens.Standby.inTryQuitMainloop:
					Notifications.AddNotificationWithCallback(self.shutdown, MessageBox, _("A sleep timer wants to shut down\nyour Dreambox. Shutdown now?"), timeout = 20)
				else:
					self.shutdown(True)
			elif config.SleepTimer.action.value == "standby":
				if config.SleepTimer.ask.value and not Screens.Standby.inStandby:
					Notifications.AddNotificationWithCallback(self.standby, MessageBox, _("A sleep timer wants to set your\nDreambox to standby. Do that now?"), timeout = 20)
				else:
					self.standby(True)

		return True
		
	def shouldSkip(self):
		return False
	
	def shutdown(self, answer):
		if answer is not None:
			if answer and not Screens.Standby.inTryQuitMainloop:
				Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 1)

	def standby(self, answer):
		if answer is not None:
			if answer and not Screens.Standby.inStandby:
				Notifications.AddNotification(Screens.Standby.Standby)

class SleepTimer(timer.Timer):
	def __init__(self):
		timer.Timer.__init__(self)
		self.defaultTime = 30

	def setSleepTime(self, sleeptime):
		self.clear()
		self.addTimerEntry(SleepTimerEntry(time.time() + 60 * sleeptime))

	def clear(self):
		self.timer_list = []

	def getCurrentSleepTime(self):
		llen = len(self.timer_list)
		idx = 0
		while idx < llen:
			timer = self.timer_list[idx]
			return int(math.ceil((timer.begin - time.time()) / 60))
		return self.defaultTime

	def isActive(self):
		return len(self.timer_list) > 0
