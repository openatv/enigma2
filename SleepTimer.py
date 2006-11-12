import timer
import time
import math

from enigma import quitMainloop

from Tools import Notifications

from Components.config import config, ConfigYesNo, ConfigSelection, ConfigSubsection

from Screens.MessageBox import MessageBox
from Screens.Standby import Standby

class SleepTimerEntry(timer.TimerEntry):
	def __init__(self, begin):
		timer.TimerEntry.__init__(self, int(begin), int(begin))
		
		self.prepare_time = 0
		
	def getNextActivation(self):
		return self.begin
		
	def activate(self):
		if self.state == self.StateRunning:
			if config.SleepTimer.action.value == "shutdown":
				if config.SleepTimer.ask.value:
					Notifications.AddNotificationWithCallback(self.shutdown, MessageBox, _("A sleep timer want's to shut down") + "\n" + _("your Dreambox. Shutdown now?"), timeout = 20)
				else:
					self.shutdown(True)
			elif config.SleepTimer.action.value == "standby":
				if config.SleepTimer.ask.value:
					Notifications.AddNotificationWithCallback(self.standby, MessageBox, _("A sleep timer want's to set your") + "\n" + _("Dreambox to standby. Do that now?"), timeout = 20)
				else:
					self.standby(True)

		return True
		
	def shouldSkip(self):
		return False
	
	def shutdown(self, answer):
		if answer is not None:
			if answer:
				quitMainloop(1)

	def standby(self, answer):
		if answer is not None:
			if answer:
				Notifications.AddNotification(Standby, self)
		
class SleepTimer(timer.Timer):
	def __init__(self):
		config.SleepTimer = ConfigSubsection()
		config.SleepTimer.ask = ConfigYesNo(default = True)
		config.SleepTimer.action = ConfigSelection(default = "shutdown", choices = [("shutdown", _("shutdown")), ("standby", _("standby"))])
		
		timer.Timer.__init__(self)
		self.defaultTime = 30
		
	def setSleepTime(self, sleeptime):
		self.clear()
		self.addTimerEntry(SleepTimerEntry(time.time() + 60 * sleeptime))

	def clear(self):
		self.timer_list = []
		
	def getCurrentSleepTime(self):
		if (self.getNextRecordingTime() == -1):
			return self.defaultTime
		return int(math.ceil((self.getNextRecordingTime() - time.time()) / 60))

	def isActive(self):
		return len(self.timer_list) > 0
	
	