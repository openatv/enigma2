from bisect import insort
from datetime import datetime
from os import fsync, remove, rename
from os.path import exists
from subprocess import call
from sys import maxsize
from time import ctime, localtime, mktime, strftime, time

from enigma import eActionMap, quitMainloop

import NavigationInstance
from timer import Timer, TimerEntry
from Components.config import config
from Components.SystemInfo import getBoxDisplayName
from Components.TimerSanityCheck import TimerSanityCheck
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools.Directories import SCOPE_CONFIG, fileReadLines, fileReadXML, resolveFilename
from Tools.Notifications import AddNotification, AddNotificationWithCallback, AddPopup
from Tools.XMLTools import stringToXML

# try:
# 	from Screens.InfoBar import InfoBar
# except Exception as err:
# 	print("[PowerTimer] Error: Import of 'InfoBar' from 'Screens.InfoBar' failed!  (%s)" % str(err))
# 	InfoBar = False
InfoBar = False

MODULE_NAME = __name__.split(".")[-1]
DEBUG = config.crash.debugTimers.value

TIMER_XML_FILE = resolveFilename(SCOPE_CONFIG, "pm_timers.xml")
TIMER_FLAG_FILE = "/tmp/was_powertimer_wakeup"

wasTimerWakeup = False
DSsave = False
RSsave = False
RBsave = False
aeDSsave = False

# ----------------------------------------------------------------------------------------------------
# Timer shut down, reboot and restart priority
# 1. wakeup
# 2. wakeuptostandby		-> (same as 1.)
# 3. deepstandby		-> DSsave
# 4. deppstandby after event	-> aeDSsave
# 5. reboot system		-> RBsave
# 6. restart gui		-> RSsave
# 7. standby
# 8. autostandby
# 9. nothing (no function, only for suppress autodeepstandby timer)
# 10. autodeepstandby
# -overlapping timers or next timer start is within 15 minutes, will only the high-order timer executed (at same types will executed the next timer)
# -autodeepstandby timer is only effective if no other timer is active or current time is in the time window
# -priority for repeated timer: shift from begin and end time only temporary, end-action priority is higher as the begin-action
# ----------------------------------------------------------------------------------------------------


class AFTEREVENT:
	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	STANDBY = 3
	DEEPSTANDBY = 4

	def __init__(self):
		pass


class TIMERTYPE:
	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	AUTOSTANDBY = 3
	AUTODEEPSTANDBY = 4
	STANDBY = 5
	DEEPSTANDBY = 6
	REBOOT = 7
	RESTART = 8

	def __init__(self):
		pass


# Parses an event, and gives out a (begin, end)-tuple.
#
def parseEvent(event):
	begin = event.getBeginTime()
	end = begin + event.getDuration()
	return (begin, end)


class PowerTimer(Timer):
	def __init__(self):
		Timer.__init__(self)

	def loadTimers(self):
		if exists(TIMER_XML_FILE):
			timerDom = fileReadXML(TIMER_XML_FILE, source=MODULE_NAME)
			if timerDom is None:
				AddPopup(_("The timer file '%s' is corrupt and could not be loaded.") % TIMER_XML_FILE, type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				try:
					rename(TIMER_XML_FILE, "%s_bad" % TIMER_XML_FILE)
				except OSError as err:
					print("[PowerTimer] Error %d: Unable to rename corrupt timer file out of the way!  (%s)" % (err.errno, err.strerror))
				return
		else:
			print("[PowerTimer] Note: The timer file '%s' was not found!" % TIMER_XML_FILE)
			return
		check = True  # Display a message when at least one timer overlaps another one.
		for timer in timerDom.findall("timer"):
			newTimer = self.createTimer(timer)
			if (self.record(newTimer, doSave=False) is not None) and (check is True):
				AddPopup(_("Timer overlap in '%s' detected!\nPlease recheck it!") % TIMER_XML_FILE, type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				check = False  # At the moment it is enough if the message is only displayed once.

	def saveTimers(self):
		saveDays = 3600 * 24 * 7  # Logs older than 7 days will not saved.
		timerList = ["<?xml version=\"1.0\" ?>", "", "<timers>"]
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue
			timerEntry = ["\t<timer"]
			timerEntry.append("timertype=\"%s\"" % stringToXML({
				TIMERTYPE.NONE: "nothing",
				TIMERTYPE.WAKEUP: "wakeup",
				TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
				TIMERTYPE.AUTOSTANDBY: "autostandby",
				TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
				TIMERTYPE.STANDBY: "standby",
				TIMERTYPE.DEEPSTANDBY: "deepstandby",
				TIMERTYPE.REBOOT: "reboot",
				TIMERTYPE.RESTART: "restart"
			}[timer.timerType]))
			timerEntry.append("begin=\"%d\"" % timer.begin)
			timerEntry.append("end=\"%d\"" % timer.end)
			timerEntry.append("repeated=\"%d\"" % timer.repeated)
			timerEntry.append("afterevent=\"%s\"" % stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.WAKEUP: "wakeup",
				AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby"
				}[timer.afterEvent]))
			timerEntry.append("disabled=\"%d\"" % timer.disabled)
			timerEntry.append("autosleepinstandbyonly=\"%s\"" % timer.autosleepinstandbyonly)
			timerEntry.append("autosleepdelay=\"%s\"" % timer.autosleepdelay)
			timerEntry.append("autosleeprepeat=\"%s\"" % timer.autosleeprepeat)
			timerEntry.append("autosleepwindow=\"%s\"" % timer.autosleepwindow)
			timerEntry.append("autosleepbegin=\"%d\"" % int(timer.autosleepbegin))
			timerEntry.append("autosleepend=\"%d\"" % int(timer.autosleepend))
			timerEntry.append("nettraffic=\"%s\"" % timer.nettraffic)
			timerEntry.append("trafficlimit=\"%s\"" % timer.trafficlimit)
			timerEntry.append("netip=\"%s\"" % timer.netip)
			timerEntry.append("ipadress=\"%s\"" % timer.ipadress)
			timerLog = []
			for logTime, logCode, logMsg in timer.log_entries:
				if logTime > int(time()) - saveDays:
					timerLog.append("\t\t<log code=\"%d\" time=\"%d\">%s</log>" % (logCode, logTime, stringToXML(logMsg)))
			if timerLog:
				timerList.append("%s>" % " ".join(timerEntry))
				timerList += timerLog
				timerList.append("\t</timer>")
			else:
				timerList.append("%s />" % " ".join(timerEntry))
		timerList.append("</timers>")
		timerList.append("")
		try:
			with open("%s.writing" % TIMER_XML_FILE, "w") as fd:
				fd.write("\n".join(timerList))
				fd.flush()
				fsync(fd.fileno())
			rename("%s.writing" % TIMER_XML_FILE, TIMER_XML_FILE)
		except OSError as err:
			print("[PowerTimer] Error %d: Unable to save timer entries to '%s'!  (%s)" % (err.errno, TIMER_XML_FILE, err.strerror))

	def createTimer(self, timerDom):
		begin = int(timerDom.get("begin"))
		end = int(timerDom.get("end"))
		disabled = int(timerDom.get("disabled") or "0")
		afterevent = {
			"nothing": AFTEREVENT.NONE,
			"wakeup": AFTEREVENT.WAKEUP,
			"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			"deepstandby": AFTEREVENT.DEEPSTANDBY
		}.get(timerDom.get("afterevent", "nothing"), "nothing")
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
		}.get(timerDom.get("timertype", "wakeup"), "wakeup")
		repeated = timerDom.get("repeated")
		autosleepbegin = int(timerDom.get("autosleepbegin") or begin)
		autosleepend = int(timerDom.get("autosleepend") or end)
		entry = PowerTimerEntry(begin, end, disabled, afterevent, timertype)
		entry.repeated = int(repeated)
		entry.autosleepinstandbyonly = timerDom.get("autosleepinstandbyonly", "no")
		entry.autosleepdelay = int(timerDom.get("autosleepdelay", "0"))
		entry.autosleeprepeat = timerDom.get("autosleeprepeat", "once")
		entry.autosleepwindow = timerDom.get("autosleepwindow", "false").lower() in ("true", "yes")
		entry.autosleepbegin = autosleepbegin
		entry.autosleepend = autosleepend
		entry.nettraffic = timerDom.get("nettraffic", "no").lower() in ("true", "yes")
		entry.trafficlimit = int(timerDom.get("trafficlimit", "100"))
		entry.netip = timerDom.get("netip", "false").lower() in ("true", "yes")
		entry.ipadress = timerDom.get("ipadress", "0.0.0.0")
		for log in timerDom.findall("log"):
			entry.log_entries.append((int(log.get("time")), int(log.get("code")), log.text.strip()))
		return entry

	# When activating a timer which has already passed, simply
	# abort the timer. Don't run trough all the stages.
	#
	def doActivate(self, timer):
		if timer.shouldSkip():
			timer.state = PowerTimerEntry.StateEnded
		else:
			# When active returns True this means "accepted", otherwise the current
			# state is kept. The timer entry itself will fix up the delay.
			if timer.activate():
				timer.state += 1
		try:
			self.timer_list.remove(timer)
		except ValueError:
			print("[PowerTimer] Remove timer from timer list failed!")
		if timer.state < PowerTimerEntry.StateEnded:  # Did this timer reached the last state?
			insort(self.timer_list, timer)  # No, sort it into active list.
		else:  # Yes, process repeated, and re-add.
			if timer.repeated:
				timer.processRepeated()
				timer.state = PowerTimerEntry.StateWaiting
				self.addTimerEntry(timer)
			else:

				self.cleanupDaily(config.recording.keep_timers.value)  # Remove old timers as set in config.
				insort(self.processed_timers, timer)
		self.stateChanged(timer)

	def cleanup(self):
		Timer.cleanup(self)
		self.saveTimers()

	def cleanupDaily(self, days):
		Timer.cleanupDaily(self, days)
		self.saveTimers()

	def shutdown(self):
		self.saveTimers()

	def getNextPowerManagerTimeOld(self, getNextStbPowerOn=False):
		now = int(time())
		nextPTlist = [(-1, None, None, None)]
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY and timer.timerType != TIMERTYPE.AUTODEEPSTANDBY:
				nextAct = timer.getNextWakeup(getNextStbPowerOn)
				if nextAct + 3 < now:
					continue
				if getNextStbPowerOn and DEBUG:
					print("[PowerTimer] Next STB power up %s." % strftime("%a, %Y/%m/%d %H:%M", localtime(nextAct)))
				nextTimerType = None
				nextAfterEvent = None
				if nextPTlist[0][0] == -1:
					if abs(nextAct - timer.begin) <= 30:
						nextTimerType = timer.timerType
					elif abs(nextAct - timer.end) <= 30:
						nextAfterEvent = timer.afterEvent
					nextPTlist = [(nextAct, nextTimerType, nextAfterEvent, timer.state)]
				else:
					if abs(nextAct - timer.begin) <= 30:
						nextTimerType = timer.timerType
					elif abs(nextAct - timer.end) <= 30:
						nextAfterEvent = timer.afterEvent
					nextPTlist.append((nextAct, nextTimerType, nextAfterEvent, timer.state))
		nextPTlist.sort()
		return nextPTlist

	# If getNextStbPowerOn is True returns tuple -> (timer.begin, set standby).
	# If getNextTimerTyp is True returns next timer list -> [(timer.begin, timer.timerType, timer.afterEvent, timer.state)].
	#
	def getNextPowerManagerTime(self, getNextStbPowerOn=False, getNextTimerTyp=False):
		global DSsave, RSsave, RBsave, aeDSsave
		nextRecTime = self.getNextPowerManagerTimeOld(getNextStbPowerOn)
		fakeTime = int(time()) + 300
		if getNextStbPowerOn:
			if config.timeshift.isRecording.value:
				if 0 < nextRecTime[0][0] < fakeTime:
					return nextRecTime[0][0], int(nextRecTime[0][1] == 2 or nextRecTime[0][2] == 2)
				else:
					return fakeTime, 0
			else:
				return nextRecTime[0][0], int(nextRecTime[0][1] == 2 or nextRecTime[0][2] == 2)
		elif getNextTimerTyp:  # Check entries and plausibility of shift state (manual canceled timer has shift/save state not reset).
			tt = []
			ae = []
			now = int(time())
			if DEBUG:
				print("[PowerTimer] +++++++++++++++")
			for entry in nextRecTime:
				if entry[0] < now + 900:
					tt.append(entry[1])
				if entry[0] < now + 900:
					ae.append(entry[2])
				if DEBUG:
					print("[PowerTimer] %s %s." % (ctime(entry[0]), str(entry)))
			if TIMERTYPE.RESTART not in tt:
				RSsave = False
			if TIMERTYPE.REBOOT not in tt:
				RBsave = False
			if TIMERTYPE.DEEPSTANDBY not in tt:
				DSsave = False
			if AFTEREVENT.DEEPSTANDBY not in ae:
				aeDSsave = False
			if DEBUG:
				print("[PowerTimer] RSsave=%s, RBsave=%s, DSsave=%s, aeDSsave=%s, wasTimerWakeup=%s" % (RSsave, RBsave, DSsave, aeDSsave, wasTimerWakeup))
			if DEBUG:
				print("[PowerTimer] +++++++++++++++")
			if config.timeshift.isRecording.value:
				if 0 < nextRecTime[0][0] < fakeTime:
					return nextRecTime
				else:
					nextRecTime.append((fakeTime, None, None, None))
					nextRecTime.sort()
					return nextRecTime
			else:
				return nextRecTime
		else:
			if config.timeshift.isRecording.value:
				if 0 < nextRecTime[0][0] < fakeTime:
					return nextRecTime[0][0]
				else:
					return fakeTime
			else:
				return nextRecTime[0][0]

	def isNextPowerManagerAfterEventActionAuto(self):
		for timer in self.timer_list:
			if timer.timerType in (TIMERTYPE.WAKEUPTOSTANDBY, TIMERTYPE.WAKEUP) or timer.afterEvent in (AFTEREVENT.WAKEUPTOSTANDBY, AFTEREVENT.WAKEUP):
				return True
		return False

	def record(self, timer, doSave=True):
		timer.timeChanged()
		print("[PowerTimer] Timer '%s'." % str(timer))
		timer.Timer = self
		self.addTimerEntry(timer)
		if doSave:
			self.saveTimers()
		return None

	def removeEntry(self, timer):
		print("[PowerTimer] Remove timer '%s'." % str(timer))
		timer.repeated = False  # Avoid re-queuing.
		timer.autoincrease = False
		timer.abort()  # Abort timer. This sets the end time to current time, so timer will be stopped.
		if timer.state != timer.StateEnded:
			self.timeChanged(timer)
		# print("[PowerTimer] State: %s." % timer.state)
		# print("[PowerTimer] In processed: %s." % timer in self.processed_timers)
		# print("[PowerTimer] In running: %s." % timer in self.timer_list)
		if timer.state != TimerEntry.StateEnded:  # Disable timer first.
			timer.disable()
		if not timer.dontSave:  # Auto increase instant timer if possible.
			for timerItem in self.timer_list:
				if timerItem.setAutoincreaseEnd():
					self.timeChanged(timerItem)
		if timer in self.processed_timers:  # Now the timer should be in the processed_timers list, remove it from there.
			self.processed_timers.remove(timer)
		self.saveTimers()

	def getNextZapTime(self):
		now = int(time())
		for timer in self.timer_list:
			if timer.begin < now:
				continue
			return timer.begin
		return -1

	def isAutoDeepstandbyEnabled(self):
		returnValue = True
		if Screens.Standby.inStandby:
			now = int(time())
			for timer in self.timer_list:
				if timer.timerType == TIMERTYPE.AUTODEEPSTANDBY:
					if timer.begin <= now + 900:
						returnValue = not (timer.getNetworkTraffic() or timer.getNetworkAdress())
					elif timer.autosleepwindow:
						returnValue = timer.autosleepbegin <= now + 900
				if not returnValue:
					break
		return returnValue

	def isProcessing(self, exceptTimer=None, endedTimer=None):
		isRunning = False
		for timer in self.timer_list:
			if timer.timerType not in (TIMERTYPE.AUTOSTANDBY, TIMERTYPE.AUTODEEPSTANDBY, exceptTimer, endedTimer):
				if timer.isRunning():
					isRunning = True
					break
		return isRunning


class PowerTimerEntry(TimerEntry, object):
	def __init__(self, begin, end, disabled=False, afterEvent=AFTEREVENT.NONE, timerType=TIMERTYPE.WAKEUP, checkOldTimers=False, autosleepdelay=60):
		TimerEntry.__init__(self, int(begin), int(end))
		print("[PowerTimerEntry] DEBUG: Running init code.")
		if checkOldTimers and self.begin < int(time()) - 1209600:
			self.begin = int(time())
		# Check auto PowerTimer.
		if (timerType == TIMERTYPE.AUTOSTANDBY or timerType == TIMERTYPE.AUTODEEPSTANDBY) and not disabled and int(time()) > 3600 and self.begin > int(time()):
			self.begin = int(time())  # The begin is in the future -> set to current time = no start delay of this timer.
		if self.end < self.begin:
			self.end = self.begin
		self.dontSave = False
		self.name = ""
		self.description = ""
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.timerType = timerType
		self.afterEvent = afterEvent
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24  # One day.
		self.autosleepinstandbyonly = "no"
		self.autosleepdelay = autosleepdelay
		self.autosleeprepeat = "once"
		self.autosleepwindow = False
		self.autosleepbegin = self.begin
		self.autosleepend = self.end
		self.nettraffic = False
		self.netbytes = 0
		self.netbytes_time = 0
		self.trafficlimit = 100
		self.netip = False
		self.ipadress = "0.0.0.0"
		self.log_entries = []
		self.resetState()
		self.messageBoxAnswerPending = False
		self.keyPressHooked = False

	def __repr__(self, getType=False):
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
		if getType:
			return timertype
		if not self.disabled:
			return "PowerTimerEntry(type=%s, begin=%s)" % (timertype, ctime(self.begin))
		else:
			return "PowerTimerEntry(type=%s, begin=%s Disabled)" % (timertype, ctime(self.begin))

	def activate(self):
		global DSsave, InfoBar, RBsave, RSsave, aeDSsave, wasTimerWakeup
		if not InfoBar:
			try:
				from Screens.InfoBar import InfoBar
			except Exception as err:
				print("[PowerTimer] Import 'InfoBar' from 'Screens.InfoBar' failed!  (%s)" % str(err))
		isRecTimerWakeup = breakPT = shiftPT = False
		now = int(time())
		nextState = self.state + 1
		autoSleepDelay = self.autosleepdelay * 60
		self.log(5, "Activating state %d." % nextState)
		if nextState == self.StatePrepared and self.timerType in (TIMERTYPE.AUTOSTANDBY, TIMERTYPE.AUTODEEPSTANDBY):
			eActionMap.getInstance().bindAction("", -maxsize, self.keyPressed)
			self.keyPressHooked = True
			if self.autosleepwindow:
				localTimeNow = localtime(now)
				autoSleepBegin = strftime("%H:%M", localtime(self.autosleepbegin)).split(":")
				autoSleepEnd = strftime("%H:%M", localtime(self.autosleepend)).split(":")
				self.autosleepbegin = int(mktime(datetime(localTimeNow.tm_year, localTimeNow.tm_mon, localTimeNow.tm_mday, int(autoSleepBegin[0]), int(autoSleepBegin[1])).timetuple()))
				self.autosleepend = int(mktime(datetime(localTimeNow.tm_year, localTimeNow.tm_mon, localTimeNow.tm_mday, int(autoSleepEnd[0]), int(autoSleepEnd[1])).timetuple()))
				if self.autosleepend <= self.autosleepbegin:
					self.autosleepbegin -= 86400
			if self.getAutoSleepWindow():
				startingPoint = self.autosleepbegin if now < self.autosleepbegin and now > self.autosleepbegin - self.prepare_time - 3 else now  # Is begin in the prepare time window?
				self.begin = startingPoint + autoSleepDelay
				self.end = self.begin
			else:
				return False
			if self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				self.getNetworkTraffic(getInitialValue=True)
		if nextState in (self.StateRunning, self.StateEnded):
			if NavigationInstance.instance.PowerTimer is None:
				# DEBUG: Running/Ended timer at system start has no navigation instance.
				# First fix: Crash in getPriorityCheck (NavigationInstance.instance.PowerTimer...).
				# Second fix: Suppress the message "A finished PowerTimer wants to ...".
				if DEBUG:
					print("[PowerTimer] *****NavigationInstance.instance.PowerTimer is None***** %s %s %s %s." % (self.timerType, self.state, ctime(self.begin), ctime(self.end)))
				return True
			elif (nextState == self.StateRunning and abs(self.begin - now) > 900) or (nextState == self.StateEnded and abs(self.end - now) > 900):
				if self.timerType in (TIMERTYPE.AUTODEEPSTANDBY, TIMERTYPE.AUTOSTANDBY):
					print("[PowerTimer] Time warp detected - set new begin time for %s timer." % self.__repr__(True))
					if not self.getAutoSleepWindow():
						return False
					else:
						self.begin = now + autoSleepDelay
						self.end = self.begin
						return False
				print("[PowerTimer] Time warp detected - timer %s ending without action." % self.__repr__(True))
				return True
			if NavigationInstance.instance.isRecordTimerImageStandard:
				isRecTimerWakeup = NavigationInstance.instance.RecordTimer.isRecTimerWakeup()
			if isRecTimerWakeup:
				wasTimerWakeup = True
			elif exists(TIMER_FLAG_FILE) and not wasTimerWakeup:
				wasTimerWakeup = int(open(TIMER_FLAG_FILE, "r").read()) and True or False
		if nextState == self.StatePrepared:
			self.log(6, "Prepare okay, waiting for begin %s." % ctime(self.begin))
			self.backoff = 0
			return True
		elif nextState == self.StateRunning:
			if self.cancelled or self.failed or self.timerType == TIMERTYPE.NONE:  # If this timer has been canceled, failed or undefined just go to "end" state.
				return True
			elif self.timerType == TIMERTYPE.WAKEUP:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.WAKEUP:")
				Screens.Standby.TVinStandby.skipHdmiCecNow("wakeuppowertimer")
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
				return True
			elif self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:")
				return True
			elif self.timerType == TIMERTYPE.STANDBY:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.STANDBY:")
				prioPT = [TIMERTYPE.WAKEUP, TIMERTYPE.RESTART, TIMERTYPE.REBOOT, TIMERTYPE.DEEPSTANDBY]
				prioPTae = [AFTEREVENT.WAKEUP, AFTEREVENT.DEEPSTANDBY]
				shiftPT, breakPT = self.getPriorityCheck(prioPT, prioPTae)
				if not Screens.Standby.inStandby and not breakPT:  # Not already in standby.
					message = _("A finished PowerTimer wants to set your %s %s to standby. Do that now?") % getBoxDisplayName()
					timeout = int(config.usage.shutdown_msgbox_timeout.value)
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(self.sendStandbyNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
					else:
						AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				return True
			elif self.timerType == TIMERTYPE.AUTOSTANDBY:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.AUTOSTANDBY:")
				if not self.getAutoSleepWindow():
					return False
				if not Screens.Standby.inStandby and not self.messageBoxAnswerPending:  # Not already in standby.
					self.messageBoxAnswerPending = True
					message = _("A finished PowerTimer wants to set your %s %s to standby. Do that now?") % getBoxDisplayName()
					timeout = int(config.usage.shutdown_msgbox_timeout.value)
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(self.sendStandbyNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
					else:
						AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
					if self.autosleeprepeat == "once":
						if self.keyPressHooked:
							eActionMap.getInstance().unbindAction("", self.keyPressed)
							self.keyPressHooked = False
						return True
					else:
						self.begin = now + autoSleepDelay
						self.end = self.begin
				else:
					self.begin = now + autoSleepDelay
					self.end = self.begin
			elif self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.AUTODEEPSTANDBY:")
				if not self.getAutoSleepWindow():
					return False
				if isRecTimerWakeup or (self.autosleepinstandbyonly == "yes" and not Screens.Standby.inStandby) \
				or NavigationInstance.instance.PowerTimer.isProcessing() or abs(NavigationInstance.instance.PowerTimer.getNextPowerManagerTime() - now) <= 900 or self.getNetworkAdress() or self.getNetworkTraffic() \
				or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					self.do_backoff()
					self.begin = self.end = int(now) + self.backoff  # Retry.
					return False
				elif not Screens.Standby.inTryQuitMainloop:  # Not if a shut down message box is open.
					if self.autosleeprepeat == "once":
						self.disabled = True
					if Screens.Standby.inStandby or self.autosleepinstandbyonly == "noquery":  # In standby or option "without query" is enabled.
						print("[PowerTimer] quitMainloop #1.")
						quitMainloop(1)
						return True
					elif not self.messageBoxAnswerPending:
						self.messageBoxAnswerPending = True
						message = _("A finished PowerTimer wants to shut down your %s %s. Do that now?") % getBoxDisplayName()
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryQuitMainloopNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						if self.autosleeprepeat == "once":
							if self.keyPressHooked:
								eActionMap.getInstance().unbindAction("", self.keyPressed)
								self.keyPressHooked = False
							return True
					self.begin = now + autoSleepDelay
					self.end = self.begin
			elif self.timerType == TIMERTYPE.RESTART:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.RESTART:")
				prioPT = [TIMERTYPE.RESTART, TIMERTYPE.REBOOT, TIMERTYPE.DEEPSTANDBY]  # Check priority.
				prioPTae = [AFTEREVENT.DEEPSTANDBY]
				shiftPT, breakPT = self.getPriorityCheck(prioPT, prioPTae)
				if RBsave or aeDSsave or DSsave:  # A timer with higher priority was shifted - no execution of current timer.
					if DEBUG:
						print("[PowerTimer] Break #1.")
					breakPT = True
				# NOTE: This code can *NEVER* run!
				# if False:  # A timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer.
				# 	if DEBUG:
				# 		print("[PowerTimer] Shift #1.")
				# 	breakPT = False
				# 	shiftPT = True
				if isRecTimerWakeup or shiftPT or breakPT or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not RSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						RSsave = True
					if not breakPT:
						self.do_backoff()
						if RSsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240:  # Check difference begin to end before shift begin time.
							breakPT = True
					if breakPT:
						if self.repeated and RSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except Exception:
								pass
						RSsave = False
						return True
					oldBegin = self.begin  # Retry.
					self.begin = now + self.backoff
					if abs(self.end - oldBegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop:  # Not if a shut down message box is open.
					if self.repeated and RSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except Exception:
							pass
					if Screens.Standby.inStandby:  # In standby.
						print("[PowerTimer] quitMainloop #4.")
						quitMainloop(3)
					else:
						message = _("A finished PowerTimer wants to restart the user interface. Do that now?")
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryToRestartNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryToRestartNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				RSsave = False
				return True
			elif self.timerType == TIMERTYPE.REBOOT:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.REBOOT:")
				prioPT = [TIMERTYPE.REBOOT, TIMERTYPE.DEEPSTANDBY]  # Check priority.
				prioPTae = [AFTEREVENT.DEEPSTANDBY]
				shiftPT, breakPT = self.getPriorityCheck(prioPT, prioPTae)
				if aeDSsave or DSsave:  # A timer with higher priority was shifted - no execution of current timer.
					if DEBUG:
						print("[PowerTimer] Break #1.")
					breakPT = True
				if RSsave:  # A timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer.
					if DEBUG:
						print("[PowerTimer] Shift #1.")
					breakPT = False
					shiftPT = True
				if isRecTimerWakeup or shiftPT or breakPT or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not RBsave:
						self.savebegin = self.begin
						self.saveend = self.end
						RBsave = True
					if not breakPT:
						self.do_backoff()
						if RBsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240:  # Check difference begin to end before shift begin time.
							breakPT = True
					if breakPT:
						if self.repeated and RBsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except Exception:
								pass
						RBsave = False
						return True
					oldBegin = self.begin  # Retry.
					self.begin = now + self.backoff
					if abs(self.end - oldBegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop:  # Not if a shut down message box is open.
					if self.repeated and RBsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except Exception:
							pass
					if Screens.Standby.inStandby:  # In standby.
						print("[PowerTimer] quitMainloop #3.")
						quitMainloop(2)
					else:
						message = _("A finished PowerTimer wants to reboot your %s %s. Do that now?") % getBoxDisplayName()
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryToRebootNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryToRebootNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				RBsave = False
				return True
			elif self.timerType == TIMERTYPE.DEEPSTANDBY:
				if DEBUG:
					print("[PowerTimer] self.timerType == TIMERTYPE.DEEPSTANDBY:")
				prioPT = [TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY, TIMERTYPE.DEEPSTANDBY]  # Check priority.
				prioPTae = [AFTEREVENT.WAKEUP, AFTEREVENT.WAKEUPTOSTANDBY, AFTEREVENT.DEEPSTANDBY]
				shiftPT, breakPT = self.getPriorityCheck(prioPT, prioPTae)
				# NOTE: This code can *NEVER* run!
				# if False:  # A timer with higher priority was shifted - no execution of current timer.
				# 	if DEBUG:
				# 		print("[PowerTimer] Break #1.")
				# 	breakPT = True
				if RSsave or RBsave or aeDSsave:  # A timer with lower priority was shifted - shift now current timer and wait for restore the saved time values from other timer.
					if DEBUG:
						print("[PowerTimer] Shift #1.")
					breakPT = False
					shiftPT = True
				if isRecTimerWakeup or shiftPT or breakPT or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not DSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						DSsave = True
					if not breakPT:
						self.do_backoff()
						if DSsave and self.end - self.begin > 3 and self.end - now - self.backoff <= 240:  # Check difference begin to end before shift begin time.
							breakPT = True
					if breakPT:
						if self.repeated and DSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except Exception:
								pass
						DSsave = False
						return True
					oldBegin = self.begin  # Retry.
					self.begin = now + self.backoff
					if abs(self.end - oldBegin) <= 3:
						self.end = self.begin
					else:
						if not self.repeated and self.end < self.begin + 300:
							self.end = self.begin + 300
					return False
				elif not Screens.Standby.inTryQuitMainloop:  # Not if a shut down message box is open.
					if self.repeated and DSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except Exception:
							pass
					if Screens.Standby.inStandby:  # In standby.
						print("[PowerTimer] quitMainloop #2.")
						quitMainloop(1)
					else:
						message = _("A finished PowerTimer wants to shut down your %s %s. Do that now?") % getBoxDisplayName()
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryQuitMainloopNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				DSsave = False
				return True
		elif nextState == self.StateEnded:
			if self.afterEvent == AFTEREVENT.WAKEUP:
				Screens.Standby.TVinStandby.skipHdmiCecNow("wakeuppowertimer")
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
			elif self.afterEvent == AFTEREVENT.STANDBY:
				if not Screens.Standby.inStandby:  # Not already in standby.
					message = _("A finished PowerTimer wants to set your %s %s to standby. Do that now?") % getBoxDisplayName()
					timeout = int(config.usage.shutdown_msgbox_timeout.value)
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(self.sendStandbyNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
					else:
						AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				if DEBUG:
					print("[PowerTimer] self.afterEvent == AFTEREVENT.DEEPSTANDBY:")
				prioPT = [TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY, TIMERTYPE.DEEPSTANDBY]  # Check priority.
				prioPTae = [AFTEREVENT.WAKEUP, AFTEREVENT.WAKEUPTOSTANDBY, AFTEREVENT.DEEPSTANDBY]
				shiftPT, breakPT = self.getPriorityCheck(prioPT, prioPTae)
				if DSsave:  # A timer with higher priority was shifted - no execution of current timer.
					if DEBUG:
						print("[PowerTimer] Break #1.")
					breakPT = True
				if RSsave or RBsave:  # A timer with lower priority was shifted - shift now current timer and wait for restore the saved time values.
					if DEBUG:
						print("[PowerTimer] Shift #1.")
					breakPT = False
					shiftPT = True
				runningPT = False
				# Option: Check other PowerTimer is running (currently disabled).
				# runningPT = NavigationInstance.instance.PowerTimer.isProcessing(exceptTimer = TIMERTYPE.NONE, endedTimer = self.timerType)
				if isRecTimerWakeup or shiftPT or breakPT or runningPT or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - now) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - now) <= 900:
					if self.repeated and not aeDSsave:
						self.savebegin = self.begin
						self.saveend = self.end
						aeDSsave = True
					if not breakPT:
						self.do_backoff()
					if breakPT:
						if self.repeated and aeDSsave:
							try:
								self.begin = self.savebegin
								self.end = self.saveend
							except Exception:
								pass
						aeDSsave = False
						return True
					self.end = now + self.backoff  # Retry.
					return False
				elif not Screens.Standby.inTryQuitMainloop:  # Not if a shut down message box is open.
					if self.repeated and aeDSsave:
						try:
							self.begin = self.savebegin
							self.end = self.saveend
						except Exception:
							pass
					if Screens.Standby.inStandby:  # In standby.
						print("[PowerTimer] quitMainloop #5.")
						quitMainloop(1)
					else:
						message = _("A finished PowerTimer wants to shut down your %s %s. Do that now?") % getBoxDisplayName()
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryQuitMainloopNotification, message, MessageBox.TYPE_YESNO, timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				aeDSsave = False
			NavigationInstance.instance.PowerTimer.saveTimers()
			self.resetTimerWakeup()
			return True

	def resetTimerWakeup(self):  # Reset wakeup state after ending timer.
		global wasTimerWakeup
		if exists(TIMER_FLAG_FILE):
			remove(TIMER_FLAG_FILE)
			if DEBUG:
				print("[PowerTimer] Reset wakeup state.")
		wasTimerWakeup = False

	def getNextActivation(self):
		if self.state in (self.StateEnded, self.StateFailed):
			return self.end
		nextState = self.state + 1
		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[nextState]

	def timeChanged(self):
		oldPrepare = int(self.start_prepare)
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0
		if oldPrepare > 60 and oldPrepare != int(self.start_prepare):
			self.log(15, "Time changed, start preparing is now %s." % ctime(self.start_prepare))

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
		self.log(10, "Backoff, retry in %d minutes." % (self.backoff // 60))

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))

	def setAutoincreaseEnd(self, timer=None):
		if not self.autoincrease:
			return False
		newEnd = int(time()) + self.autoincreasetime if timer is None else timer.begin - 30
		dummyTimer = PowerTimerEntry(self.begin, newEnd, disabled=True, afterEvent=self.afterEvent, timerType=self.timerType)
		dummyTimer.disabled = self.disabled
		timerSanityCheck = TimerSanityCheck(NavigationInstance.instance.PowerManager.timer_list, dummyTimer)
		if not timerSanityCheck.check():
			simulTimerList = timerSanityCheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				newEnd = simulTimerList[1].begin
				newEnd -= 30  # Allow 30 seconds of prepare time.
		if newEnd <= int(time()):
			return False
		self.end = newEnd
		return True

	def sendStandbyNotification(self, answer):
		self.messageBoxAnswerPending = False
		if answer:
			session = Screens.Standby.Standby
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, None)
			else:
				AddNotification(session)

	def sendTryQuitMainloopNotification(self, answer):
		self.messageBoxAnswerPending = False
		if answer:
			session = Screens.Standby.TryQuitMainloop
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, 1)
			else:
				AddNotification(session, 1)

	def sendTryToRebootNotification(self, answer):
		if answer:
			session = Screens.Standby.TryQuitMainloop
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, 2)
			else:
				AddNotification(session, 2)

	def sendTryToRestartNotification(self, answer):
		if answer:
			session = Screens.Standby.TryQuitMainloop
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, 3)
			else:
				AddNotification(session, 3)

	def keyPressed(self, key, tag):
		if self.getAutoSleepWindow():
			self.begin = int(time()) + (self.autosleepdelay * 60)
			self.end = self.begin

	def getAutoSleepWindow(self):
		now = int(time())
		if self.autosleepwindow:
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
				if self.keyPressHooked:
					eActionMap.getInstance().unbindAction("", self.keyPressed)
					self.keyPressHooked = False
				self.state = 0
				self.timeChanged()
				return False
		return True

	def getPriorityCheck(self, prioPT, prioPTae):
		shiftPT = False
		breakPT = False
		nextPTlist = NavigationInstance.instance.PowerTimer.getNextPowerManagerTime(getNextTimerTyp=True)
		for timer in nextPTlist:
			if abs(timer[0] - int(time())) > 900:  # Check timers within next 15 minutes will start or end.
				continue
			if timer[1] is None and timer[2] is None and timer[3] is None:  # Faketime.
				if DEBUG:
					print("[PowerTimer] Shift #2 - Timer is fake time %s %s." % (ctime(timer[0]), str(timer)))
				shiftPT = True
				continue
			if timer[0] == self.begin and timer[1] == self.timerType and timer[2] is None and timer[3] == self.state or timer[0] == self.end and timer[1] is None and timer[2] == self.afterEvent and timer[3] == self.state:  # Is timer in list itself?
				if DEBUG:
					print("[PowerTimer] Timer is itself %s %s." % (ctime(timer[0]), str(timer)))
				nextPTitself = True
			else:
				nextPTitself = False
			if (timer[1] in prioPT or timer[2] in prioPTae) and not nextPTitself:
				if DEBUG:
					print("[PowerTimer] Break #2 <= 900 %s %s." % (ctime(timer[0]), str(timer)))
				breakPT = True
				break
		return shiftPT, breakPT

	def getNextWakeup(self, getNextStbPowerOn=False):
		nextState = self.state + 1
		if getNextStbPowerOn:
			if nextState == 3 and (self.timerType in (TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY) or self.afterEvent in (AFTEREVENT.WAKEUP, AFTEREVENT.WAKEUPTOSTANDBY)):
				now = int(time())
				if self.start_prepare > now and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY):  # Timer start time is later as now - begin time was changed while running timer.
					return self.start_prepare
				elif self.begin > now and (self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY):  # Timer start time is later as now - begin time was changed while running timer.
					return self.begin
				if self.afterEvent in (AFTEREVENT.WAKEUP, AFTEREVENT.WAKEUPTOSTANDBY):
					return self.end
				nextDay = 0
				countDay = 0
				weekdayTimer = datetime.fromtimestamp(self.begin).isoweekday() * -1
				weekdayRepeated = bin(128 + self.repeated)
				for day in range(weekdayTimer - 1, -8, -1):
					countDay += 1
					if int(weekdayRepeated[day]):
						nextDay = day
						break
				if nextDay == 0:
					for day in range(-1, weekdayTimer - 1, -1):
						countDay += 1
						if int(weekdayRepeated[day]):
							break
				return self.start_prepare + 86400 * countDay
			elif nextState == 2 and self.timerType in (TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY):
				return self.begin
			elif nextState == 1 and self.timerType in (TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY):
				return self.start_prepare
			elif nextState < 3 and self.afterEvent in (AFTEREVENT.WAKEUP, AFTEREVENT.WAKEUPTOSTANDBY):
				return self.end
			else:
				return -1
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end
		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[nextState]

	def getNetworkAdress(self):
		retVal = False
		if self.netip:
			try:
				for ip in [x.strip() for x in self.ipadress.split(",")]:
					if call(("/bin/ping -q -w1 -c1 %s" % ip).split(" ")) == 0:
						retVal = True
						break
			except Exception:
				print("[PowerTimer] Error reading IP -> %s!" % self.ipadress)
		return retVal

	def getNetworkTraffic(self, getInitialValue=False):
		now = int(time())
		newBytes = 0
		if self.nettraffic:
			lines = fileReadLines("/proc/net/dev", source=MODULE_NAME)
			if lines:
				for line in lines:
					data = line.split()
					if data[0].endswith(":") and (data[0].startswith("eth") or data[0].startswith("wlan")):
						newBytes += int(data[1]) + int(data[9])
				if getInitialValue:
					self.netbytes = newBytes
					self.netbytes_time = now
					print("[PowerTimer] NetworkTraffic: Initial bytes=%d, time is %s." % (newBytes, ctime(now)))
					return
				oldBytes = self.netbytes
				seconds = now - self.netbytes_time
				self.netbytes = newBytes
				self.netbytes_time = now
				diffBytes = float(newBytes - oldBytes) * 8.0 / 1024.0 / seconds  # In kbit/s.
				if diffBytes < 0:
					print("[PowerTimer] NetworkTraffic: Overflow of interface counter, waiting for next value.")
					return True
				else:
					print("[PowerTimer] NetworkTraffic: %0.2f Kbps (%0.2f MByte in %d seconds), actualBytes=%d, time is %s." % (diffBytes, diffBytes / 8.0 / 1024.0 * seconds, seconds, newBytes, ctime(now)))
				if diffBytes > self.trafficlimit:
					return True
			else:
				print("[PowerTimer] NetworkTraffic: Unable to access network traffic information! (Try 'cat /proc/net/dev' for testing on command line.)")
		return False
