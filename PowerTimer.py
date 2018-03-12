import os
from boxbranding import getMachineBrand, getMachineName
import xml.etree.cElementTree
from time import ctime, time
from bisect import insort

from enigma import eActionMap, quitMainloop

from Components.config import config
from Components.Harddisk import internalHDDNotSleeping
from Components.TimerSanityCheck import TimerSanityCheck
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools import Directories, Notifications
from Tools.XMLTools import stringToXML
import timer
import NavigationInstance


# parses an event and returns a (begin, end)-tuple.
def parseEvent(ev):
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	return begin, end

def recordingsActive(margin):
	recordTimer = NavigationInstance.instance.RecordTimer
	return (
		recordTimer.isRecording() or
		abs(recordTimer.getNextRecordingTime() - time()) <= margin or
		abs(recordTimer.getNextZapTime() - time()) <= margin
	)

class AFTEREVENT:
	def __init__(self):
		pass

	NONE = 0
	WAKEUPTOSTANDBY = 1
	STANDBY = 2
	DEEPSTANDBY = 3

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

# Please do not translate log messages
class PowerTimerEntry(timer.TimerEntry, object):
	def __init__(self, begin, end, disabled=False, afterEvent=AFTEREVENT.NONE, timerType=TIMERTYPE.WAKEUP, checkOldTimers=False):
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
		self.autoincreasetime = 3600 * 24  # 1 day
		self.autosleepinstandbyonly = 'no'
		self.autosleepdelay = 60
		self.autosleeprepeat = 'once'

		self.origbegin = self.begin
		self.origend = self.end

		self.log_entries = []
		self.resetState()

	def __repr__(self):
		timertype = {
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
		if self.backoff == 0:
			self.backoff = 5 * 60
		else:
			self.backoff *= 2
			if self.backoff > 1800:
				self.backoff = 1800
		self.log(10, "backoff: retry in %d minutes" % (int(self.backoff) / 60))
		#
		# If this is the first backoff of a repeat timer remember the original
		# begin/end times, so that we can use *these* when setting up the
		# repeat.
		# A repeat timer (self.repeat != 0) is one set for a given time on a
		# day.
		# A timer that repeats every <n> mins has autosleeprepeat="repeated" and
		# is a different beast, whcih doesn't need, and mustn't have, this.
		#
		if self.repeated and not hasattr(self, "real_begin"):
			self.real_begin = self.begin
			self.real_end = self.end

	def activate(self):
		next_state = self.state + 1
		self.log(5, "activating state %d" % next_state)

		if next_state == self.StatePrepared and self.timerType in (TIMERTYPE.AUTOSTANDBY, TIMERTYPE.AUTODEEPSTANDBY):
			eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.keyPressed)
			self.begin = time() + int(self.autosleepdelay) * 60
			if self.end <= self.begin:
				self.end = self.begin

		if next_state == self.StatePrepared:
			self.log(6, "prepare ok, waiting for begin")
			self.next_activation = self.begin
			self.backoff = 0
			return True

		elif next_state == self.StateRunning:
			self.wasPowerTimerWakeup = False
			if os.path.exists("/tmp/was_powertimer_wakeup"):
				self.wasPowerTimerWakeup = bool(int(open("/tmp/was_powertimer_wakeup", "r").read()))
				os.remove("/tmp/was_powertimer_wakeup")
			# If this timer has been cancelled or has failed,
			# just go to "end" state.
			if self.cancelled:
				return True

			if self.failed:
				return True

			if self.timerType == TIMERTYPE.WAKEUP:
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
				return True

			elif self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
				return True

			elif self.timerType == TIMERTYPE.STANDBY:
				if not Screens.Standby.inStandby:  # Not already in standby
					Notifications.AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A power timer wants to set your %s %s to standby mode.\nGo to standby mode now?") % (getMachineBrand(), getMachineName()), timeout=180)
				return True

			elif self.timerType == TIMERTYPE.AUTOSTANDBY:
				if NavigationInstance.instance.getCurrentlyPlayingServiceReference() and ('0:0:0:0:0:0:0:0:0' in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString() or '4097:' in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()):
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inStandby:  # Not already in standby
					Notifications.AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A power timer wants to set your %s %s to standby mode.\nGo to standby mode now?") % (getMachineBrand(), getMachineName()), timeout=180)
					if self.autosleeprepeat == "once":
						eActionMap.getInstance().unbindAction('', self.keyPressed)
						return True
					else:
						self.begin = time() + int(self.autosleepdelay) * 60
						if self.end <= self.begin:
							self.end = self.begin
				else:
					self.begin = time() + int(self.autosleepdelay) * 60
					if self.end <= self.begin:
						self.end = self.begin

			elif self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				# Check for there being any active
				# Movie playback or IPTV channel or
				# any streaming clients before going
				# to Deep Standby.  However, it is
				# possible to put the box into Standby
				# with the MoviePlayer still active
				# (it will play if the box is taken
				# out of Standby) - similarly for the
				# IPTV player. This should not prevent
				# a DeepStandby And check for existing
				# or imminent recordings, etc..  Also
				# added () around the test and split
				# them across lines to make it clearer
				# what each test is.
				from Components.Converter.ClientsStreaming import ClientsStreaming
				if ((
					not Screens.Standby.inStandby and NavigationInstance.instance.getCurrentlyPlayingServiceReference() and
					(
						'0:0:0:0:0:0:0:0:0' in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString() or
						'4097:' in NavigationInstance.instance.getCurrentlyPlayingServiceReference().toString()
					) or
					(int(ClientsStreaming("NUMBER").getText()) > 0)
				) or
					recordingsActive(900) or
					(self.autosleepinstandbyonly == 'yes' and not Screens.Standby.inStandby) or
					(self.autosleepinstandbyonly == 'yes' and Screens.Standby.inStandby and internalHDDNotSleeping())
				):
					self.do_backoff()
					# Retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop:  # The shutdown messagebox is not open
					if Screens.Standby.inStandby:  # In standby
						quitMainloop(Screens.Standby.QUIT_SHUTDOWN)
						return True
					else:
						Notifications.AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A power timer wants to shut down your %s %s.\nShut down now?") % (getMachineBrand(), getMachineName()), timeout=180)
						if self.autosleeprepeat == "once":
							eActionMap.getInstance().unbindAction('', self.keyPressed)
							return True
						else:
							self.begin = time() + int(self.autosleepdelay) * 60
							if self.end <= self.begin:
								self.end = self.begin

			elif self.timerType == TIMERTYPE.DEEPSTANDBY and self.wasPowerTimerWakeup:
				return True

			elif self.timerType == TIMERTYPE.DEEPSTANDBY and not self.wasPowerTimerWakeup:
				if recordingsActive(900):
					self.do_backoff()
					# Retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop:  # The shutdown messagebox is not open
					if Screens.Standby.inStandby:  # In standby
						quitMainloop(Screens.Standby.QUIT_SHUTDOWN)
					else:
						Notifications.AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A power timer wants to shut down your %s %s.\nShut down now?") % (getMachineBrand(), getMachineName()), timeout=180)
				return True

			elif self.timerType == TIMERTYPE.REBOOT:
				if recordingsActive(900):
					self.do_backoff()
					# Retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop:  # The shutdown messagebox is not open
					if Screens.Standby.inStandby:  # In standby
						quitMainloop(Screens.Standby.QUIT_REBOOT)
					else:
						Notifications.AddNotificationWithUniqueIDCallback(self.sendTryToRebootNotification, "PT_StateChange", MessageBox, _("A power timer wants to reboot your %s %s.\nReboot now?") % (getMachineBrand(), getMachineName()), timeout=180)
				return True

			elif self.timerType == TIMERTYPE.RESTART:
				if recordingsActive(900):
					self.do_backoff()
					# Retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop:  # The shutdown messagebox is not open
					if Screens.Standby.inStandby:  # In standby
						quitMainloop(Screens.Standby.QUIT_RESTART)
					else:
						Notifications.AddNotificationWithUniqueIDCallback(self.sendTryToRestartNotification, "PT_StateChange", MessageBox, _("A power timer wants to restart your %s %s user interface.\nRestart user interface now?") % (getMachineBrand(), getMachineName()), timeout=180)
				return True

		elif next_state == self.StateEnded:
			NavigationInstance.instance.PowerTimer.saveTimer()
			if self.afterEvent == AFTEREVENT.STANDBY:
				if not Screens.Standby.inStandby:  # Not already in standby
					Notifications.AddNotificationWithUniqueIDCallback(self.sendStandbyNotification, "PT_StateChange", MessageBox, _("A power timer wants to set your %s %s to standby mode.\nGo to standby mode now?") % (getMachineBrand(), getMachineName()), timeout=180)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				if recordingsActive(900):
					self.do_backoff()
					# Retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop:  # The shutdown messagebox is not open
					if Screens.Standby.inStandby:  # In standby
						quitMainloop(Screens.Standby.QUIT_SHUTDOWN)
					else:
						Notifications.AddNotificationWithUniqueIDCallback(self.sendTryQuitMainloopNotification, "PT_StateChange", MessageBox, _("A power timer wants to shut down your %s %s.\nShut down now?") % (getMachineBrand(), getMachineName()), timeout=180)
			return True

	# What is this doing here!?
	# It's only used for "indefinite" recording timers.
	# -prl
	def setAutoincreaseEnd(self, entry=None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end = int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin - 30

		dummyentry = PowerTimerEntry(self.begin, new_end, disabled=True, afterEvent=self.afterEvent, timerType=self.timerType)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.PowerManager.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30				# Allow 30 seconds preparation time
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def sendStandbyNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, Screens.Standby.QUIT_SHUTDOWN)

	def sendTryToRebootNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, Screens.Standby.QUIT_REBOOT)

	def sendTryToRestartNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, Screens.Standby.QUIT_RESTART)

	def keyPressed(self, key, tag):
		self.begin = time() + int(self.autosleepdelay) * 60
		if self.end <= self.begin:
			self.end = self.begin

	def getNextActivation(self):
		if self.state in (self.StateEnded, self.StateFailed):
			return self.end

		next_state = self.state + 1

		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[next_state]

	def getNextWakeup(self):
		if self.state in (self.StateEnded, self.StateFailed):
			return self.end

		if self.timerType not in (TIMERTYPE.WAKEUP, TIMERTYPE.WAKEUPTOSTANDBY):
			return self.end if self.afterEvent else -1
		next_state = self.state + 1
		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[next_state]

	def timeChanged(self):
		old_prepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		if self.origbegin is not None:
			self.begin = self.origbegin
		if self.origend is not None:
			self.end = self.origend
		self.backoff = 0

		if int(old_prepare) > 60 and int(old_prepare) != int(self.start_prepare):
			self.log(15, "time changed, start prepare is now: %s" % ctime(self.start_prepare))

	def processRepeated(self, findRunningEvent=True, findNextEvent=False):
		# Reset begin/end times
		self.begin = self.origbegin
		self.end = self.origend
		# Prevent timeChanged() from resetting updated times
		self.origbegin = None
		self.origend = None
		timer.TimerEntry.processRepeated(self, findRunningEvent, findNextEvent)
		# Update "original" begin/end times
		self.origbegin = self.begin
		self.origend = self.end

def createTimer(xml):
	timertype = str(xml.get("timertype") or "wakeup")
	timertype = {
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
		"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
		"standby": AFTEREVENT.STANDBY,
		"deepstandby": AFTEREVENT.DEEPSTANDBY
	}[afterevent]
	autosleepinstandbyonly = str(xml.get("autosleepinstandbyonly") or "no")
	autosleepdelay = str(xml.get("autosleepdelay") or "0")
	autosleeprepeat = str(xml.get("autosleeprepeat") or "once")

	entry = PowerTimerEntry(begin, end, disabled, afterevent, timertype)
	entry.repeated = int(repeated)
	entry.autosleepinstandbyonly = autosleepinstandbyonly
	entry.autosleepdelay = int(autosleepdelay)
	entry.autosleeprepeat = autosleeprepeat

	for l in xml.findall("log"):
		time = int(l.get("time"))
		code = int(l.get("code"))
		msg = l.text.strip().encode("utf-8")
		entry.log_entries.append((time, code, msg))

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
		# If the timer should be skipped, simply abort the timer.
		# Don't run through all the states.
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

		# Did this timer reach the final state?
		if w.state < PowerTimerEntry.StateEnded:
			# No, sort it into active list
			insort(self.timer_list, w)
		else:
			# Yes. Process repeat if necessary, and re-add.
			if w.repeated:
				# If we have saved original begin/end times for a backed off timer
				# restore those values now
				if hasattr(w, "real_begin"):
					w.begin = w.real_begin
					w.end = w.real_end
					# Now remove the temporary holding attributes...
					del w.real_begin
					del w.real_end
				w.processRepeated()
				w.state = PowerTimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				# Reset begin/end times
				w.begin = w.origbegin
				w.end = w.origend
				# Remove old timers as set in config
				self.cleanupDaily(config.recording.keep_timers.value)
				insort(self.processed_timers, w)
		self.stateChanged(w)

	def loadTimer(self):
		# TODO: PATH!
		if not Directories.fileExists(self.Filename):
			return
		try:
			f = open(self.Filename, 'r')
			doc = xml.etree.cElementTree.parse(f)
			f.close()
		except SyntaxError:
			from Tools.Notifications import AddPopup
			from Screens.MessageBox import MessageBox

			AddPopup(_("The timer file (pm_timers.xml) is corrupt and could not be loaded."), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")

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

		# Post a message if there are timer overlaps in the timer file
		checkit = True
		for timer in root.findall("timer"):
			newTimer = createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (checkit is True):
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				AddPopup(_("Timer overlap in pm_timers.xml detected!\nPlease recheck it!"), type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				checkit = False  # The message only needs to be displayed once

	def saveTimer(self):
		list = ['<?xml version="1.0" ?>\n', '<timers>\n']
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue
			list.append('<timer')
			list.append(' timertype="' + str(stringToXML({
				TIMERTYPE.WAKEUP: "wakeup",
				TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
				TIMERTYPE.AUTOSTANDBY: "autostandby",
				TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
				TIMERTYPE.STANDBY: "standby",
				TIMERTYPE.DEEPSTANDBY: "deepstandby",
				TIMERTYPE.REBOOT: "reboot",
				TIMERTYPE.RESTART: "restart"
			}[timer.timerType])) + '"')
			list.append(' begin="' + str(int(timer.origbegin)) + '"')
			list.append(' end="' + str(int(timer.origend)) + '"')
			list.append(' repeated="' + str(int(timer.repeated)) + '"')
			list.append(' afterevent="' + str(stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby"
			}[timer.afterEvent])) + '"')
			list.append(' disabled="' + str(int(timer.disabled)) + '"')
			list.append(' autosleepinstandbyonly="' + str(timer.autosleepinstandbyonly) + '"')
			list.append(' autosleepdelay="' + str(timer.autosleepdelay) + '"')
			list.append(' autosleeprepeat="' + str(timer.autosleeprepeat) + '"')
			list.append('>\n')

# 	Handle repeat entries, which never end and so never get pruned by cleanupDaily
#        Repeating timers get autosleeprepeat="repeated" or repeated="127" (daily) or
# 	"31" (weekdays) [dow bitmap] etc.
#
			ignore_before = 0
			if config.recording.keep_timers.value > 0:
				if str(timer.autosleeprepeat) == "repeated" or int(timer.repeated) > 0:
					ignore_before = time() - config.recording.keep_timers.value * 86400

			for log_time, code, msg in timer.log_entries:
				if log_time < ignore_before:
					continue
				list.append('<log')
				list.append(' code="' + str(code) + '"')
				list.append(' time="' + str(log_time) + '"')
				list.append('>')
				list.append(str(stringToXML(msg)))
				list.append('</log>\n')

			list.append('</timer>\n')

		list.append('</timers>\n')

		f = open(self.Filename + ".writing", "w")
		for x in list:
			f.write(x)
		f.flush()

		os.fsync(f.fileno())
		f.close()
		os.rename(self.Filename + ".writing", self.Filename)

	def getNextZapTime(self):
		now = time()
		for timer in self.timer_list:
			if timer.begin < now:
				continue
			return timer.begin
		return -1

	def getNextPowerManagerTimeOld(self):
		now = time()
		for timer in self.timer_list:
			if timer.timerType not in (TIMERTYPE.AUTOSTANDBY, TIMERTYPE.AUTODEEPSTANDBY):
				next_act = timer.getNextWakeup()
				if next_act < now:
					continue
				return next_act
		return -1

	def getNextPowerManagerTime(self):
		nextrectime = self.getNextPowerManagerTimeOld()
		faketime = time() + 300
		if config.timeshift.isRecording.value:
			if 0 < nextrectime < faketime:
				return nextrectime
			else:
				return faketime
		else:
			return nextrectime

	def isNextPowerManagerAfterEventActionAuto(self):
		for timer in self.timer_list:
			if timer.timerType == TIMERTYPE.WAKEUPTOSTANDBY or timer.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY:
				return True
		return False

	def record(self, entry, ignoreTSC=False, dosave=True):  # Called by loadTimer with dosave=False
		entry.timeChanged()
		print "[PowerTimer]", str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimer()
		return None

	def removeEntry(self, entry):
		print "[PowerTimer] Remove", str(entry)

		# Avoid re-enqueuing
		entry.repeated = False

		# Abort timer.
		# This sets the end time to current time, so timer will be stopped.
		entry.autoincrease = False
		entry.abort()

		if entry.state != entry.StateEnded:
			self.timeChanged(entry)

# 		print "state: ", entry.state
# 		print "in processed: ", entry in self.processed_timers
# 		print "in running: ", entry in self.timer_list
		# Disable timer first
		if entry.state != entry.StateEnded:
			entry.disable()
		# Autoincrease instanttimer if possible
		if not entry.dontSave:
			for x in self.timer_list:
				if x.setAutoincreaseEnd():
					self.timeChanged(x)
		# Now the timer should be in the processed_timers list.
		# Remove it from there.
		if entry in self.processed_timers:
			self.processed_timers.remove(entry)
		self.saveTimer()

	def shutdown(self):
		self.saveTimer()
