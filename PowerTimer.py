import os
from boxbranding import getMachineBrand, getMachineName
import xml.etree.cElementTree
from datetime import datetime
from time import ctime, time, strftime, localtime, mktime
from bisect import insort

from enigma import eActionMap, quitMainloop

from Components.config import config
from Components.TimerSanityCheck import TimerSanityCheck
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools import Directories, Notifications
from Tools.XMLTools import stringToXML
import timer
import NavigationInstance

#global variables begin
DSsave = False
RSsave = False
RBsave = False
aeDSsave = False
wasTimerWakeup = False
try:
	from Screens.InfoBar import InfoBar
except Exception, e:
	print "[PowerTimer] import from 'Screens.InfoBar import InfoBar' failed:", e
	InfoBar = False
#+++
debug = False
#+++
#global variables end
#----------------------------------------------------------------------------------------------------
#Timer shutdown, reboot and restart priority
#1. wakeup
#2. wakeuptostandby						-> (same as 1.)
#3. deepstandby							->	DSsave
#4. deppstandby after event				->	aeDSsave
#5. reboot system						->	RBsave
#6. restart gui							->	RSsave
#7. standby
#8. autostandby
#9. nothing (no function, only for suppress autodeepstandby timer)
#10. autodeepstandby
#-overlapping timers or next timer start is within 15 minutes, will only the high-order timer executed (at same types will executed the next timer)
#-autodeepstandby timer is only effective if no other timer is active or current time is in the time window
#-priority for repeated timer: shift from begin and end time only temporary, end-action priority is higher as the begin-action
#----------------------------------------------------------------------------------------------------

#reset wakeup state after ending timer
def resetTimerWakeup():
	global wasTimerWakeup
	if os.path.exists("/tmp/was_powertimer_wakeup"):
		os.remove("/tmp/was_powertimer_wakeup")
		if debug: print "[POWERTIMER] reset wakeup state"
	wasTimerWakeup = False

# parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
# begin and end will be corrected
def parseEvent(ev):
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	return begin, end

class AFTEREVENT:
	def __init__(self):
		pass

	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	STANDBY = 3
	DEEPSTANDBY = 4

class TIMERTYPE:
	def __init__(self):
		pass

	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	AUTOSTANDBY = 3
	AUTODEEPSTANDBY = 4
	STANDBY = 5
	DEEPSTANDBY = 6
	REBOOT = 7
	RESTART = 8

# please do not translate log messages
class PowerTimerEntry(timer.TimerEntry, object):
	def __init__(self, begin, end, disabled = False, afterEvent = AFTEREVENT.NONE, timerType = TIMERTYPE.WAKEUP, checkOldTimers = False, autosleepdelay = 60):
		timer.TimerEntry.__init__(self, int(begin), int(end))
		if checkOldTimers:
			if self.begin < time() - 1209600:
				self.begin = int(time())

		if self.end < self.begin:
			self.end = self.begin

		self.dontSave = False
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.timerType = timerType
		self.afterEvent = afterEvent
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24 # 1 day
		self.autosleepinstandbyonly = 'no'
		self.autosleepdelay = autosleepdelay
		self.autosleeprepeat = 'once'
		self.autosleepwindow = 'no'
		self.autosleepbegin = self.begin
		self.autosleepend = self.end

		self.nettraffic = 'no'
		self.trafficlimit = 100
		self.netip = 'no'
		self.ipadress = "0.0.0.0"

		self.log_entries = []
		self.resetState()

		self.messageBoxAnswerPending = False

		#check autopowertimer
		if (self.timerType == TIMERTYPE.AUTOSTANDBY or self.timerType == TIMERTYPE.AUTODEEPSTANDBY) and not self.disabled and time() > 3600 and self.begin > time():
			self.begin = int(time())						#the begin is in the future -> set to current time = no start delay of this timer

	def __repr__(self):
		timertype = {
			TIMERTYPE.NONE: "nothing",
			TIMERTYPE.WAKEUP: "wakeup",
			TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
			TIMERTYPE.AUTOSTANDBY: "autostandby",
			TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
			TIMERTYPE.STANDBY: "standby",
			TIMERTYPE.DEEPSTANDBY: "deepstandby",
			TIMERTYPE.REBOOT: "reboot",
			TIMERTYPE.RESTART: "restart"
			}[self.timerType]
		if not self.disabled:
			return "PowerTimerEntry(type=%s, begin=%s)" % (timertype, ctime(self.begin))
		else:
			return "PowerTimerEntry(type=%s, begin=%s Disabled)" % (timertype, ctime(self.begin))

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))

	def do_backoff(self):
		if Screens.Standby.inStandby and not wasTimerWakeup or RSsave or RBsave or aeDSsave or DSsave:
			self.backoff = 300
		else:
			if self.backoff == 0:
				self.backoff = 300
			else:
				self.backoff += 300
				if self.backoff > 900:
					self.backoff = 900
		self.log(10, "backoff: retry in %d minutes" % (int(self.backoff)/60))

	def activate(self):
		global RSsave, RBsave, DSsave, aeDSsave, wasTimerWakeup, InfoBar

		if not InfoBar:
			try:
				from Screens.InfoBar import InfoBar
			except Exception, e:
				print "[PowerTimer] import from 'Screens.InfoBar import InfoBar' failed:", e

		isRecTimerWakeup = breakPT = shiftPT = False
		now = time()
		next_state = self.state + 1
		self.log(5, "activating state %d" % next_state)
		if next_state == self.StatePrepared and (self.timerType == TIMERTYPE.AUTOSTANDBY or self.timerType == TIMERTYPE.AUTODEEPSTANDBY):
			eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.keyPressed)
			if self.autosleepwindow == 'yes':
				ltm = localtime(now)
				asb = strftime("%H:%M", localtime(self.autosleepbegin)).split(':')
				ase = strftime("%H:%M", localtime(self.autosleepend)).split(':')
				self.autosleepbegin = int(mktime(datetime(ltm.tm_year, ltm.tm_mon, ltm.tm_mday, int(asb[0]), int(asb[1])).timetuple()))
				self.autosleepend = int(mktime(datetime(ltm.tm_year, ltm.tm_mon, ltm.tm_mday, int(ase[0]), int(ase[1])).timetuple()))
				if self.autosleepend <= self.autosleepbegin:
					self.autosleepbegin -= 86400
			if self.getAutoSleepWindow():
				if now < self.autosleepbegin and now > self.autosleepbegin - self.prepare_time - 3:	#begin is in prepare time window
					self.begin = self.end = self.autosleepbegin + int(self.autosleepdelay)*60
				else:
					self.begin = self.end = int(now) + int(self.autosleepdelay)*60
			else:
				return False
			if self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				self.getNetworkTraffic(getInitialValue = True)

		if (next_state == self.StateRunning or next_state == self.StateEnded) and NavigationInstance.instance.PowerTimer is None:
			#TODO: running/ended timer at system start has no nav instance
			#First fix: crash in getPriorityCheck (NavigationInstance.instance.PowerTimer...)
			#Second fix: suppress the message (A finished powertimer wants to ...)
			if debug: print "*****NavigationInstance.instance.PowerTimer is None*****", self.timerType, self.state, ctime(self.begin), ctime(self.end)
			return True
		elif next_state == self.StateRunning and abs(self.begin - now) > 900: return True
		elif next_state == self.StateEnded and abs(self.end - now) > 900: return True

		if next_state == self.StateRunning or next_state == self.StateEnded:
			if NavigationInstance.instance.isRecordTimerImageStandard:
				isRecTimerWakeup = NavigationInstance.instance.RecordTimer.isRecTimerWakeup()
			if isRecTimerWakeup:
				wasTimerWakeup = True
			elif os.path.exists("/tmp/was_powertimer_wakeup") and not wasTimerWakeup:
				wasTimerWakeup = int(open("/tmp/was_powertimer_wakeup", "r").read()) and True or False

		if next_state == self.StatePrepared:
			self.log(6, "prepare ok, waiting for begin: %s" % ctime(self.begin))
			self.backoff = 0
			return True

		elif next_state == self.StateRunning:

			# if this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True

			if self.failed:
				return True

			if self.timerType == TIMERTYPE.NONE:
				return True

			elif self.timerType == TIMERTYPE.WAKEUP:
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
				return True

			elif self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
				return True

			elif self.timerType == TIMERTYPE.STANDBY:
				if debug: print "self.timerType == TIMERTYPE.STANDBY:"
				prioPT = [TIMERTYPE.WAKEUP,TIMERTYPE.RESTART,TIMERTYPE.REBOOT,TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.WAKEUP,AFTEREVENT.DEEPSTANDBY]
				shiftPT,breakPT = self.getPriorityCheck(prioPT,prioPTae)
				if not Screens.Standby.inStandby and not breakPT: # not already in standby
					callback = self.sendStandbyNotification
					message = _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName())
					messageboxtyp = MessageBox.TYPE_YESNO
					timeout = 180
					default = True
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
					else:
						Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
				return True

			elif self.timerType == TIMERTYPE.AUTOSTANDBY:
				if debug: print "self.timerType == TIMERTYPE.AUTOSTANDBY:"
				if not self.getAutoSleepWindow():
					return False
				if not Screens.Standby.inStandby and not self.messageBoxAnswerPending: # not already in standby
					self.messageBoxAnswerPending = True
					callback = self.sendStandbyNotification
					message = _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName())
					messageboxtyp = MessageBox.TYPE_YESNO
					timeout = 180
					default = True
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
					else:
						Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
					if self.autosleeprepeat == "once":
						eActionMap.getInstance().unbindAction('', self.keyPressed)
						return True
					else:
						self.begin = self.end = int(now) + int(self.autosleepdelay)*60
				else:
					self.begin = self.end = int(now) + int(self.autosleepdelay)*60

			elif self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				if debug: print "self.timerType == TIMERTYPE.AUTODEEPSTANDBY:"
				if not self.getAutoSleepWindow():
					return False
				if isRecTimerWakeup or (self.autosleepinstandbyonly == 'yes' and not Screens.Standby.inStandby) \
					or NavigationInstance.instance.PowerTimer.isProcessing() or abs(NavigationInstance.instance.PowerTimer.getNextPowerManagerTime() - now) <= 900 or self.getNetworkAdress() or self.getNetworkTraffic() \
					or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					self.do_backoff()
					# retry
					self.begin = self.end = int(now) + self.backoff
					return False
				elif not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.autosleeprepeat == "once":
						self.disabled = True
					if Screens.Standby.inStandby or self.autosleepinstandbyonly == 'noquery': # in standby or option 'without query' is enabled
						print "[PowerTimer] quitMainloop #1"
						quitMainloop(1)
						return True
					elif not self.messageBoxAnswerPending:
						self.messageBoxAnswerPending = True
						callback = self.sendTryQuitMainloopNotification
						message = _("A finished powertimer wants to shutdown your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName())
						messageboxtyp = MessageBox.TYPE_YESNO
						timeout = 180
						default = True
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
						else:
							Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
						if self.autosleeprepeat == "once":
							eActionMap.getInstance().unbindAction('', self.keyPressed)
							return True
					self.begin = self.end = int(now) + int(self.autosleepdelay)*60

			elif self.timerType == TIMERTYPE.RESTART:
				if debug: print "self.timerType == TIMERTYPE.RESTART:"
				#check priority
				prioPT = [TIMERTYPE.RESTART,TIMERTYPE.REBOOT,TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.DEEPSTANDBY]
				shiftPT,breakPT = self.getPriorityCheck(prioPT,prioPTae)
				#a timer with higher priority was shifted - no execution of current timer
				if RBsave or aeDSsave or DSsave:
					if debug: print "break#1"
					breakPT = True
				#a timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer
				if False:
					if debug: print "shift#1"
					breakPT = False
					shiftPT = True
				#shift or break
				if isRecTimerWakeup or shiftPT or breakPT \
					or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not RSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						RSsave = True
					if not breakPT:
						self.do_backoff()
						#check difference begin to end before shift begin time
						if RSsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240: breakPT = True
					#breakPT
					if breakPT:
						if self.repeated and RSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except:
								pass
						RSsave = False
						return True
					# retry
					oldbegin = self.begin
					self.begin = int(now) + self.backoff
					if abs(self.end - oldbegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.repeated and RSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except:
							pass
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #4"
						quitMainloop(3)
					else:
						callback = self.sendTryToRestartNotification
						message = _("A finished powertimer wants to restart the user interface.\nDo that now?") % (getMachineBrand(), getMachineName())
						messageboxtyp = MessageBox.TYPE_YESNO
						timeout = 180
						default = True
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
						else:
							Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
				RSsave = False
				return True

			elif self.timerType == TIMERTYPE.REBOOT:
				if debug: print "self.timerType == TIMERTYPE.REBOOT:"
				#check priority
				prioPT = [TIMERTYPE.REBOOT,TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.DEEPSTANDBY]
				shiftPT,breakPT = self.getPriorityCheck(prioPT,prioPTae)
				#a timer with higher priority was shifted - no execution of current timer
				if aeDSsave or DSsave:
					if debug: print "break#1"
					breakPT = True
				#a timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer
				if RSsave:
					if debug: print "shift#1"
					breakPT = False
					shiftPT = True
				#shift or break
				if isRecTimerWakeup or shiftPT or breakPT \
					or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not RBsave:
						self.savebegin = self.begin
						self.saveend = self.end
						RBsave = True
					if not breakPT:
						self.do_backoff()
						#check difference begin to end before shift begin time
						if RBsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240: breakPT = True
					#breakPT
					if breakPT:
						if self.repeated and RBsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except:
								pass
						RBsave = False
						return True
					# retry
					oldbegin = self.begin
					self.begin = int(now) + self.backoff
					if abs(self.end - oldbegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.repeated and RBsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except:
							pass
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #3"
						quitMainloop(2)
					else:
						callback = self.sendTryToRebootNotification
						message = _("A finished powertimer wants to reboot your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName())
						messageboxtyp = MessageBox.TYPE_YESNO
						timeout = 180
						default = True
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
						else:
							Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
				RBsave = False
				return True

			elif self.timerType == TIMERTYPE.DEEPSTANDBY:
				if debug: print "self.timerType == TIMERTYPE.DEEPSTANDBY:"
				#check priority
				prioPT = [TIMERTYPE.WAKEUP,TIMERTYPE.WAKEUPTOSTANDBY,TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.WAKEUP,AFTEREVENT.WAKEUPTOSTANDBY,AFTEREVENT.DEEPSTANDBY]
				shiftPT,breakPT = self.getPriorityCheck(prioPT,prioPTae)
				#a timer with higher priority was shifted - no execution of current timer
				if False:
					if debug: print "break#1"
					breakPT = True
				#a timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer
				if RSsave or RBsave or aeDSsave:
					if debug: print "shift#1"
					breakPT = False
					shiftPT = True
				#shift or break
				if isRecTimerWakeup or shiftPT or breakPT \
					or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not DSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						DSsave = True
					if not breakPT:
						self.do_backoff()
						#check difference begin to end before shift begin time
						if DSsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240: breakPT = True
					#breakPT
					if breakPT:
						if self.repeated and DSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except:
								pass
						DSsave = False
						return True
					# retry
					oldbegin = self.begin
					self.begin = int(now) + self.backoff
					if abs(self.end - oldbegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.repeated and DSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except:
							pass
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #2"
						quitMainloop(1)
					else:
						callback = self.sendTryQuitMainloopNotification
						message = _("A finished powertimer wants to shutdown your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName())
						messageboxtyp = MessageBox.TYPE_YESNO
						timeout = 180
						default = True
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
						else:
							Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
				DSsave = False
				return True

		elif next_state == self.StateEnded:
			if self.afterEvent == AFTEREVENT.WAKEUP:
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
			elif self.afterEvent == AFTEREVENT.STANDBY:
				if not Screens.Standby.inStandby: # not already in standby
					callback = self.sendStandbyNotification
					message = _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName())
					messageboxtyp = MessageBox.TYPE_YESNO
					timeout = 180
					default = True
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
					else:
						Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				if debug: print "self.afterEvent == AFTEREVENT.DEEPSTANDBY:"
				#check priority
				prioPT = [TIMERTYPE.WAKEUP,TIMERTYPE.WAKEUPTOSTANDBY,TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.WAKEUP,AFTEREVENT.WAKEUPTOSTANDBY,AFTEREVENT.DEEPSTANDBY]
				shiftPT,breakPT = self.getPriorityCheck(prioPT,prioPTae)
				#a timer with higher priority was shifted - no execution of current timer
				if DSsave:
					if debug: print "break#1"
					breakPT = True
				#a timer with lower priority was shifted - shift now current timer and wait for restore the saved time values
				if RSsave or RBsave:
					if debug: print "shift#1"
					breakPT = False
					shiftPT = True
				#shift or break
				runningPT = False
				#option: check other powertimer is running (current disabled)
				#runningPT = NavigationInstance.instance.PowerTimer.isProcessing(exceptTimer = TIMERTYPE.NONE, endedTimer = self.timerType)
				if isRecTimerWakeup or shiftPT or breakPT or runningPT \
					or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not aeDSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						aeDSsave = True
					if not breakPT: self.do_backoff()
					#breakPT
					if breakPT:
						if self.repeated and aeDSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except:
								pass
						aeDSsave = False
						return True
					# retry
					self.end = int(now) + self.backoff
					return False
				elif not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.repeated and aeDSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except:
							pass
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #5"
						quitMainloop(1)
					else:
						callback = self.sendTryQuitMainloopNotification
						message = _("A finished powertimer wants to shutdown your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName())
						messageboxtyp = MessageBox.TYPE_YESNO
						timeout = 180
						default = True
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(callback, message, messageboxtyp, timeout, default)
						else:
							Notifications.AddNotificationWithCallback(callback, MessageBox, message, messageboxtyp, timeout = timeout, default = default)
				aeDSsave = False
			NavigationInstance.instance.PowerTimer.saveTimer()
			resetTimerWakeup()
			return True

	def setAutoincreaseEnd(self, entry = None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end = int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin - 30

		dummyentry = PowerTimerEntry(self.begin, new_end, disabled=True, afterEvent = self.afterEvent, timerType = self.timerType)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.PowerManager.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30				# 30 Sekunden Prepare-Zeit lassen
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def sendStandbyNotification(self, answer):
		self.messageBoxAnswerPending = False
		if answer:
			session = Screens.Standby.Standby
			option = None
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, option)
			else:
				Notifications.AddNotification(session)

	def sendTryQuitMainloopNotification(self, answer):
		self.messageBoxAnswerPending = False
		if answer:
			session = Screens.Standby.TryQuitMainloop
			option = 1
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, option)
			else:
				Notifications.AddNotification(session, option)

	def sendTryToRebootNotification(self, answer):
		if answer:
			session = Screens.Standby.TryQuitMainloop
			option = 2
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, option)
			else:
				Notifications.AddNotification(session, option)

	def sendTryToRestartNotification(self, answer):
		if answer:
			session = Screens.Standby.TryQuitMainloop
			option = 3
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, option)
			else:
				Notifications.AddNotification(session, option)

	def keyPressed(self, key, tag):
		if self.getAutoSleepWindow():
			self.begin = self.end = int(time()) + int(self.autosleepdelay)*60

	def getAutoSleepWindow(self):
		now = time()
		if self.autosleepwindow == 'yes':
			if now < self.autosleepbegin and now < self.autosleepend:
				self.begin = self.autosleepbegin
				self.end = self.autosleepend
			elif now > self.autosleepbegin and now > self.autosleepend:
				while self.autosleepend < now:
					self.autosleepend += 86400
				while self.autosleepbegin + 86400 < self.autosleepend:
					self.autosleepbegin += 86400
				self.begin = self.autosleepbegin
				self.end = self.autosleepend
			if not (now > self.autosleepbegin - self.prepare_time - 3 and now < self.autosleepend):
				eActionMap.getInstance().unbindAction('', self.keyPressed)
				self.state = 0
				self.timeChanged()
				return False
		return True

	def getPriorityCheck(self,prioPT,prioPTae):
		shiftPT = breakPT = False
		nextPTlist = NavigationInstance.instance.PowerTimer.getNextPowerManagerTime(getNextTimerTyp = True)
		for entry in nextPTlist:
			#check timers within next 15 mins will started or ended
			if abs(entry[0] - time()) > 900:
				continue
			#faketime
			if entry[1] is None and entry[2] is None and entry[3] is None:
				if debug: print "shift#2 - entry is faketime", ctime(entry[0]), entry
				shiftPT = True
				continue
			#is timer in list itself?
			if entry[0] == self.begin and entry[1] == self.timerType and entry[2] is None and entry[3] == self.state \
				or entry[0] == self.end and entry[1] is None and entry[2] == self.afterEvent and entry[3] == self.state:
				if debug: print "entry is itself", ctime(entry[0]), entry
				nextPTitself = True
			else:
				nextPTitself = False
			if (entry[1] in prioPT or entry[2] in prioPTae) and not nextPTitself:
				if debug: print "break#2 <= 900", ctime(entry[0]), entry
				breakPT = True
				break
		return shiftPT, breakPT

	def getNextActivation(self):
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end

		next_state = self.state + 1

		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end }[next_state]

	def getNextWakeup(self, getNextStbPowerOn = False):
		next_state = self.state + 1
		if getNextStbPowerOn:
			if next_state == 3 and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY or self.afterEvent == AFTEREVENT.WAKEUP or  self.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY):
				if self.start_prepare > time() and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY): #timer start time is later as now - begin time was changed while running timer
					return self.start_prepare
				elif self.begin > time() and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY): #timer start time is later as now - begin time was changed while running timer
					return self.begin
				if self.afterEvent == AFTEREVENT.WAKEUP or self.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY:
					return self.end
				next_day = 0
				count_day = 0
				wd_timer = datetime.fromtimestamp(self.begin).isoweekday()*-1
				wd_repeated = bin(128+self.repeated)
				for s in range(wd_timer-1,-8,-1):
					count_day +=1
					if int(wd_repeated[s]):
						next_day = s
						break
				if next_day == 0:
					for s in range(-1,wd_timer-1,-1):
						count_day +=1
						if int(wd_repeated[s]):
							next_day = s
							break
				#return self.begin + 86400 * count_day
				return self.start_prepare + 86400 * count_day
			elif next_state == 2 and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY):
				return self.begin
			elif next_state == 1 and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY):
				return self.start_prepare
			elif next_state < 3 and (self.afterEvent == AFTEREVENT.WAKEUP or self.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY):
				return self.end
			else:
				return -1

		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end
		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end}[next_state]

	def timeChanged(self):
		old_prepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0

		if int(old_prepare) > 60 and int(old_prepare) != int(self.start_prepare):
			self.log(15, "time changed, start prepare is now: %s" % ctime(self.start_prepare))

	def getNetworkAdress(self):
		ret = False
		if self.netip == 'yes':
			try:
				for ip in self.ipadress.split(','):
					if not os.system("ping -q -w1 -c1 " + ip):
						ret = True
						break
			except:
				print '[PowerTimer] Error reading ip! -> %s' % self.ipadress
		return ret

	def getNetworkTraffic(self, getInitialValue = False):
		now = time()
		newbytes = 0
		if self.nettraffic == 'yes':
			try:
				if os.path.exists('/proc/net/dev'):
					f = open('/proc/net/dev', 'r')
					temp = f.readlines()
					f.close()
					for lines in temp:
						lisp = lines.split()
						if lisp[0].endswith(':') and (lisp[0].startswith('eth') or lisp[0].startswith('wlan')):
							newbytes += long(lisp[1]) + long(lisp[9])
					if getInitialValue:
						self.netbytes = newbytes
						self.netbytes_time = now
						print '[PowerTimer] Receive/Transmit initialBytes=%d, time is %s' % (self.netbytes, ctime(self.netbytes_time))
						return
					oldbytes = self.netbytes
					seconds = int(now-self.netbytes_time)
					self.netbytes = newbytes
					self.netbytes_time = now
					diffbytes = float(newbytes - oldbytes) * 8 / 1024 / seconds 	#in kbit/s
					if diffbytes < 0:
						print '[PowerTimer] Receive/Transmit -> overflow interface counter, waiting for next value'
						return True
					else:
						print '[PowerTimer] Receive/Transmit kilobits per second: %0.2f (%0.2f MByte in %d seconds), actualBytes=%d, time is %s' % (diffbytes, diffbytes/8/1024*seconds, seconds, self.netbytes, ctime(self.netbytes_time))
					if diffbytes > self.trafficlimit:
						return True
			except:
				print '[PowerTimer] Receive/Transmit Bytes: Error reading values! Use "cat /proc/net/dev" for testing on command line.'
		return False

def createTimer(xml):
	timertype = str(xml.get("timertype") or "wakeup")
	timertype = {
		"nothing": TIMERTYPE.NONE,
		"wakeup": TIMERTYPE.WAKEUP,
		"wakeuptostandby": TIMERTYPE.WAKEUPTOSTANDBY,
		"autostandby": TIMERTYPE.AUTOSTANDBY,
		"autodeepstandby": TIMERTYPE.AUTODEEPSTANDBY,
		"standby": TIMERTYPE.STANDBY,
		"deepstandby": TIMERTYPE.DEEPSTANDBY,
		"reboot": TIMERTYPE.REBOOT,
		"restart": TIMERTYPE.RESTART
		}[timertype]
	begin = int(xml.get("begin"))
	end = int(xml.get("end"))
	repeated = xml.get("repeated").encode("utf-8")
	disabled = long(xml.get("disabled") or "0")
	afterevent = str(xml.get("afterevent") or "nothing")
	afterevent = {
		"nothing": AFTEREVENT.NONE,
		"wakeup": AFTEREVENT.WAKEUP,
		"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
		"standby": AFTEREVENT.STANDBY,
		"deepstandby": AFTEREVENT.DEEPSTANDBY
		}[afterevent]
	autosleepinstandbyonly = str(xml.get("autosleepinstandbyonly") or "no")
	autosleepdelay = str(xml.get("autosleepdelay") or "0")
	autosleeprepeat = str(xml.get("autosleeprepeat") or "once")
	autosleepwindow = str(xml.get("autosleepwindow") or "no")
	autosleepbegin = int(xml.get("autosleepbegin") or begin)
	autosleepend = int(xml.get("autosleepend") or end)

	nettraffic = str(xml.get("nettraffic") or "no")
	trafficlimit = int(xml.get("trafficlimit") or 100)
	netip = str(xml.get("netip") or "no")
	ipadress = str(xml.get("ipadress") or "0.0.0.0")

	entry = PowerTimerEntry(begin, end, disabled, afterevent, timertype)
	entry.repeated = int(repeated)
	entry.autosleepinstandbyonly = autosleepinstandbyonly
	entry.autosleepdelay = int(autosleepdelay)
	entry.autosleeprepeat = autosleeprepeat
	entry.autosleepwindow = autosleepwindow
	entry.autosleepbegin = autosleepbegin
	entry.autosleepend = autosleepend

	entry.nettraffic = nettraffic
	entry.trafficlimit = trafficlimit
	entry.netip = netip
	entry.ipadress = ipadress

	for l in xml.findall("log"):
		ltime = int(l.get("time"))
		code = int(l.get("code"))
		msg = l.text.strip().encode("utf-8")
		entry.log_entries.append((ltime, code, msg))

	return entry

class PowerTimer(timer.Timer):
	def __init__(self):
		timer.Timer.__init__(self)

		self.Filename = Directories.resolveFilename(Directories.SCOPE_CONFIG, "pm_timers.xml")

		try:
			self.loadTimer()
		except IOError:
			print "unable to load timers from file!"

	def doActivate(self, w):
		# when activating a timer which has already passed,
		# simply abort the timer. don't run trough all the stages.
		if w.shouldSkip():
			w.state = PowerTimerEntry.StateEnded
		else:
			# when active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# the timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1

		try:
			self.timer_list.remove(w)
		except:
			print '[PowerManager]: Remove list failed'

		# did this timer reached the last state?
		if w.state < PowerTimerEntry.StateEnded:
			# no, sort it into active list
			insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = PowerTimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				# Remove old timers as set in config
				self.cleanupDaily(config.recording.keep_timers.value)
				insort(self.processed_timers, w)
		self.stateChanged(w)

	def loadTimer(self):
		# TODO: PATH!
		if not Directories.fileExists(self.Filename):
			return
		try:
			file = open(self.Filename, 'r')
			doc = xml.etree.cElementTree.parse(file)
			file.close()
		except SyntaxError:
			from Tools.Notifications import AddPopup
			from Screens.MessageBox import MessageBox

			AddPopup(_("The timer file (pm_timers.xml) is corrupt and could not be loaded."), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")

			print "pm_timers.xml failed to load!"
			try:
				import os
				os.rename(self.Filename, self.Filename + "_old")
			except (IOError, OSError):
				print "renaming broken timer failed"
			return
		except IOError:
			print "pm_timers.xml not found!"
			return

		root = doc.getroot()

		# put out a message when at least one timer overlaps
		checkit = True
		for timer in root.findall("timer"):
			newTimer = createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (checkit == True):
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				AddPopup(_("Timer overlap in pm_timers.xml detected!\nPlease recheck it!"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")
				checkit = False # at moment it is enough when the message is displayed one time

	def saveTimer(self):
		savedays = 3600 * 24 * 7	#logs older 7 Days will not saved
		list = ['<?xml version="1.0" ?>\n', '<timers>\n']
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue
			list.append('<timer')
			list.append(' timertype="' + str(stringToXML({
				TIMERTYPE.NONE: "nothing",
				TIMERTYPE.WAKEUP: "wakeup",
				TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
				TIMERTYPE.AUTOSTANDBY: "autostandby",
				TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
				TIMERTYPE.STANDBY: "standby",
				TIMERTYPE.DEEPSTANDBY: "deepstandby",
				TIMERTYPE.REBOOT: "reboot",
				TIMERTYPE.RESTART: "restart"
				}[timer.timerType])) + '"')
			list.append(' begin="' + str(int(timer.begin)) + '"')
			list.append(' end="' + str(int(timer.end)) + '"')
			list.append(' repeated="' + str(int(timer.repeated)) + '"')
			list.append(' afterevent="' + str(stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.WAKEUP: "wakeup",
				AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby"
				}[timer.afterEvent])) + '"')
			list.append(' disabled="' + str(int(timer.disabled)) + '"')
			list.append(' autosleepinstandbyonly="' + str(timer.autosleepinstandbyonly) + '"')
			list.append(' autosleepdelay="' + str(timer.autosleepdelay) + '"')
			list.append(' autosleeprepeat="' + str(timer.autosleeprepeat) + '"')
			list.append(' autosleepwindow="' + str(timer.autosleepwindow) + '"')
			list.append(' autosleepbegin="' + str(int(timer.autosleepbegin)) + '"')
			list.append(' autosleepend="' + str(int(timer.autosleepend)) + '"')

			list.append(' nettraffic="' + str(timer.nettraffic) + '"')
			list.append(' trafficlimit="' + str(int(timer.trafficlimit)) + '"')
			list.append(' netip="' + str(timer.netip) + '"')
			list.append(' ipadress="' + str(timer.ipadress) + '"')

			list.append('>\n')

			for ltime, code, msg in timer.log_entries:
				if ltime > time() - savedays:
					list.append('<log')
					list.append(' code="' + str(code) + '"')
					list.append(' time="' + str(ltime) + '"')
					list.append('>')
					list.append(str(stringToXML(msg)))
					list.append('</log>\n')

			list.append('</timer>\n')

		list.append('</timers>\n')

		file = open(self.Filename + ".writing", "w")
		for x in list:
			file.write(x)
		file.flush()

		os.fsync(file.fileno())
		file.close()
		os.rename(self.Filename + ".writing", self.Filename)

	def isProcessing(self, exceptTimer = None, endedTimer = None):
		isRunning = False
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY and timer.timerType != TIMERTYPE.AUTODEEPSTANDBY and timer.timerType != exceptTimer and timer.timerType != endedTimer:
				if timer.isRunning():
					isRunning = True
					break
		return isRunning

	def getNextZapTime(self):
		now = time()
		for timer in self.timer_list:
			if timer.begin < now:
				continue
			return timer.begin
		return -1

	def getNextPowerManagerTimeOld(self, getNextStbPowerOn = False):
		now = int(time())
		nextPTlist = [(-1,None,None,None)]
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY and timer.timerType != TIMERTYPE.AUTODEEPSTANDBY:
				next_act = timer.getNextWakeup(getNextStbPowerOn)
				if next_act + 3 < now:
					continue
				if getNextStbPowerOn and debug:
					print "[powertimer] next stb power up", strftime("%a, %Y/%m/%d %H:%M", localtime(next_act))
				next_timertype = next_afterevent = None
				if nextPTlist[0][0] == -1:
					if abs(next_act - timer.begin) <= 30:
						next_timertype = timer.timerType
					elif abs(next_act - timer.end) <= 30:
						next_afterevent = timer.afterEvent
					nextPTlist = [(next_act,next_timertype,next_afterevent,timer.state)]
				else:
					if abs(next_act - timer.begin) <= 30:
						next_timertype = timer.timerType
					elif abs(next_act - timer.end) <= 30:
						next_afterevent = timer.afterEvent
					nextPTlist.append((next_act,next_timertype,next_afterevent,timer.state))
		nextPTlist.sort()
		return nextPTlist

	def getNextPowerManagerTime(self, getNextStbPowerOn = False, getNextTimerTyp = False):
		#getNextStbPowerOn = True returns tuple -> (timer.begin, set standby)
		#getNextTimerTyp = True returns next timer list -> [(timer.begin, timer.timerType, timer.afterEvent, timer.state)]
		global DSsave, RSsave, RBsave, aeDSsave
		nextrectime = self.getNextPowerManagerTimeOld(getNextStbPowerOn)
		faketime = int(time()) + 300

		if getNextStbPowerOn:
			if config.timeshift.isRecording.value:
				if 0 < nextrectime[0][0] < faketime:
					return nextrectime[0][0], int(nextrectime[0][1] == 2 or nextrectime[0][2] == 2)
				else:
					return faketime, 0
			else:
				return nextrectime[0][0], int(nextrectime[0][1] == 2 or nextrectime[0][2] == 2)
		elif getNextTimerTyp:
			#check entrys and plausibility of shift state (manual canceled timer has shift/save state not reset)
			tt = ae = []
			now = time()
			if debug: print "+++++++++++++++"
			for entry in nextrectime:
				if entry[0] < now + 900: tt.append(entry[1])
				if entry[0] < now + 900: ae.append(entry[2])
				if debug: print ctime(entry[0]), entry
			if not TIMERTYPE.RESTART in tt: RSsave = False
			if not TIMERTYPE.REBOOT in tt: RBsave = False
			if not TIMERTYPE.DEEPSTANDBY in tt: DSsave = False
			if not AFTEREVENT.DEEPSTANDBY in ae: aeDSsave = False
			if debug: print "RSsave=%s, RBsave=%s, DSsave=%s, aeDSsave=%s, wasTimerWakeup=%s" %(RSsave, RBsave, DSsave, aeDSsave, wasTimerWakeup)
			if debug: print "+++++++++++++++"
			###
			if config.timeshift.isRecording.value:
				if 0 < nextrectime[0][0] < faketime:
					return nextrectime
				else:
					nextrectime.append((faketime,None,None,None))
					nextrectime.sort()
					return nextrectime
			else:
				return nextrectime
		else:
			if config.timeshift.isRecording.value:
				if 0 < nextrectime[0][0] < faketime:
					return nextrectime[0][0]
				else:
					return faketime
			else:
				return nextrectime[0][0]

	def isNextPowerManagerAfterEventActionAuto(self):
		for timer in self.timer_list:
			if timer.timerType == TIMERTYPE.WAKEUPTOSTANDBY or timer.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY or timer.timerType == TIMERTYPE.WAKEUP or timer.afterEvent == AFTEREVENT.WAKEUP:
				return True
		return False

	def record(self, entry, ignoreTSC=False, dosave=True):		#wird von loadTimer mit dosave=False aufgerufen
		entry.timeChanged()
		print "[PowerTimer]",str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimer()
		return None

	def removeEntry(self, entry):
		print "[PowerTimer] Remove",str(entry)

		# avoid re-enqueuing
		entry.repeated = False

		# abort timer.
		# this sets the end time to current time, so timer will be stopped.
		entry.autoincrease = False
		entry.abort()

		if entry.state != entry.StateEnded:
			self.timeChanged(entry)

# 		print "state: ", entry.state
# 		print "in processed: ", entry in self.processed_timers
# 		print "in running: ", entry in self.timer_list
		# disable timer first
		if entry.state != 3:
			entry.disable()
		# autoincrease instanttimer if possible
		if not entry.dontSave:
			for x in self.timer_list:
				if x.setAutoincreaseEnd():
					self.timeChanged(x)
		# now the timer should be in the processed_timers list. remove it from there.
		if entry in self.processed_timers:
			self.processed_timers.remove(entry)
		self.saveTimer()

	def shutdown(self):
		self.saveTimer()
