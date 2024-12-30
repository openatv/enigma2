from bisect import insort
from datetime import datetime, timedelta
from time import localtime, mktime, time

from enigma import eActionMap, eTimer


DAY_LIST = [
	"Mon",
	"Tue",
	"Wed",
	"Thu",
	"Fri",
	"Sat",
	"Sun"
]


# The time between "polls". We do this because we want to account for time jumps etc.
# Of course if they occur <100s before starting, it's not good. thus, you have to
# re-poll when you change the time.
#
# This is just in case. We don't want the timer hanging. We use this
# "edge-triggered-polling-scheme" anyway, so why don't make it a bit more fool-proof?
#
class Timer:
	MaxWaitTime = 100  # TODO: What is this time?

	def __init__(self):
		self.timer_list = []
		self.processed_timers = []
		self.timer = eTimer()
		self.timer.callback.append(self.calcNextActivation)
		self.lastActivation = time()
		self.calcNextActivation()
		self.on_state_change = []

	def calcNextActivation(self):
		now = int(time())
		if self.lastActivation > now:
			print("[Timer] Timewarp: Re-evaluating all processed timers.")
			processedTimers = self.processed_timers
			self.processed_timers = []
			for timer in processedTimers:  # Simulate a "waiting" state to give them a chance to re-occur.
				timer.resetState()
				self.addTimerEntry(timer, noRecalc=True)
		self.processActivation()
		self.lastActivation = now
		when = now + self.MaxWaitTime
		self.timer_list and self.timer_list.sort()  # Re-sort/Refresh list, try to fix hanging timers.
		timerList = [x for x in self.timer_list if not x.disabled]  # Calculate next activation point.
		if timerList:
			next = timerList[0].getNextActivation()
			if next < when:
				when = next
		if now < 1072224000 and when > now + 5:
			when = now + 5  # System time has not yet been set (before 01.01.2004), keep a short poll interval.
		self.setNextActivation(now, when)

	# We keep on processing the first entry until it goes into the future.
	#
	# As we activate a timer, mark it as such and don't activate it again if it is so marked. This
	# is to prevent a situation that obtains for RecordTimer timers. These do not remove themselves
	# from the timer_list at the start of their doActivate() (as various parts of that code expects
	# them to still be there - each timers steps through various states) and hence one thread can
	# activate it and then, on a file-system access, python switches to another thread and, if that
	# happens to end up running the timer code, the same timer will be run again.
	#
	# Since this tag is only for use here, we remove it after use.
	#
	def processActivation(self):
		timeStamp = int(time()) + 1
		while True:
			timerList = [x for x in self.timer_list if (not x.disabled and not getattr(x, "currentlyActivated", False))]
			if timerList and timerList[0].getNextActivation() < timeStamp:
				timerList[0].currentlyActivated = True
				self.doActivate(timerList[0])
				del timerList[0].currentlyActivated
			else:
				break

	def setNextActivation(self, now, when):
		delay = (when - now) * 1000
		if isinstance(delay, float):
			print("[Timer] DEBUG: The 'delay' variable is a float!  (It should be an integer.)")
			from traceback import print_stack
			print_stack()
			delay = int(delay)
		self.timer.start(delay, True)
		self.next = when

	def timeChanged(self, timer):
		timer.timeChanged()
		if timer.state == TimerEntry.StateEnded:
			self.processed_timers.remove(timer)
		else:
			try:
				self.timer_list.remove(timer)
			except:
				print("[Timer] Error: Failed to remove timer as it isn't in the timer list!")
				return
		if timer.state == TimerEntry.StateEnded:  # Give the timer a chance to re-enqueue.
			timer.state = TimerEntry.StateWaiting
		elif "SchedulerEntry" in repr(timer) and (timer.timerType == 3 or timer.timerType == 4):  # Types: 3=AUTOSTANDBY, 4=AUTODEEPSTANDBY.
			if timer.state > 0 and timer.keyPressHooked:
				eActionMap.getInstance().unbindAction("", timer.keyPressed)
				timer.keyPressHooked = False
			timer.state = TimerEntry.StateWaiting
		self.addTimerEntry(timer)

	def addTimerEntry(self, entry, noRecalc=False):
		entry.processRepeated()
		# When the timer has not yet started, and is already passed, don't go through
		# waiting/running/end-states, but sort it right into the processedTimers.
		if entry.shouldSkip() or entry.state == TimerEntry.StateEnded or (entry.state == TimerEntry.StateWaiting and entry.disabled):
			insort(self.processed_timers, entry)
			entry.state = TimerEntry.StateEnded
		else:
			insort(self.timer_list, entry)
			if not noRecalc:
				self.calcNextActivation()
		# Small piece of example code to understand how to use record simulation.
		# if NavigationInstance.instance:
		# 	timerList = []
		# 	for count, timer in enumerate(self.timer_list):
		# 		print("[Timer] Timer %d." % count)
		# 		if timer.state == 0:  # Waiting.
		# 			timerList.append(NavigationInstance.instance.recordService(timer.service_ref))
		# 		else:
		# 			print("[Timer] State: %d - %s." % (timer.state, {
		# 				# TimerEntry.StateWaiting: "Waiting",
		# 				TimerEntry.StatePrepared: "Prepared",
		# 				TimerEntry.StateRunning: "Running",
		# 				TimerEntry.StateEnded: "Ended",
		# 				TimerEntry.StateFailed: "Failed",
		# 				TimerEntry.StateDisabled: "Disabled"
		# 			}.get(timer.state)))
		# 	for recording in timerList:
		# 		print("[Timer] %s!" % ("Failed" if recording.start(True) else "Okay"))  # Simulate.
		# 		NavigationInstance.instance.stopRecordService(recording)
		# else:
		# 	print("[Timer] No navigation instance!")

	def doActivate(self, timer):
		self.timer_list.remove(timer)
		# When activating a timer which has already passed, simply abort the
		# timer. Don't run trough all the stages.
		if timer.shouldSkip():
			timer.state = TimerEntry.StateEnded
		else:
			# When active returns true, this means "accepted". Otherwise, the current state
			# is kept. The timer entry itself will fix up the delay then.
			if timer.activate():
				timer.state += 1
		if timer.state < TimerEntry.StateEnded:  # Did this timer reached the last state? No, sort it into active list.
			insort(self.timer_list, timer)
		else:  # Yes, process repeated, and re-add.
			if timer.repeated:
				timer.processRepeated()
				timer.state = TimerEntry.StateWaiting
				self.addTimerEntry(timer)
			else:
				insort(self.processed_timers, timer)
		self.stateChanged(timer)

	def stateChanged(self, entry):
		for callback in self.on_state_change:
			callback(entry)

	def cleanup(self):
		self.processed_timers = [x for x in self.processed_timers if x.disabled]

	def cleanupDisabled(self):
		disabledTimers = [x for x in self.processed_timers if x.disabled]
		for timer in disabledTimers:
			timer.shouldSkip()

	def cleanupDaily(self, days):
		limit = time() - (days * 3600 * 24)
		self.processed_timers = [x for x in self.processed_timers if (x.disabled and x.repeated) or (x.end and (x.end > limit))]


class TimerEntry:
	StateWaiting = 0
	StatePrepared = 1
	StateRunning = 2
	StateEnded = 3
	StateFailed = 4
	StateDisabled = 5

	def __init__(self, begin, end):
		self.prepare_time = 20
		self.begin = begin
		self.end = end
		self.state = 0
		self.findRunningEvent = True
		self.findNextEvent = False
		self.repeated = 0
		# beginDate = localtime(self.begin)
		# newDate = datetime(beginDate.tm_year, beginDate.tm_mon, beginDate.tm_mday 0, 0, 0);
		self.repeatedbegindate = begin
		self.backoff = 0
		self.disabled = False
		self.failed = False

	def __lt__(self, value):
		return self.getNextActivation() < value.getNextActivation()

	def activate(self):  # Must be overridden!
		pass

	def getNextActivation(self):  # Must be overridden!
		pass

	def setRepeated(self, day):
		if isinstance(day, str):
			day = DAY_LIST.index(day)
		self.repeated |= (2 ** day)

	def resetRepeated(self):
		self.repeated = 0

	def processRepeated(self, findRunningEvent=True, findNextEvent=False):  # Update self.begin and self.end according to the self.repeated-flags.
		if self.repeated != 0:
			now = int(time()) + 1
			if findNextEvent:
				now = self.end + 120
			self.findRunningEvent = findRunningEvent
			self.findNextEvent = findNextEvent
			# To avoid problems with daylight saving, we need to calculate with localtime, in struct_time representation.
			localRepeatedBeginDate = localtime(self.repeatedbegindate)
			localBegin = localtime(self.begin)
			localEnd = localtime(self.end)
			localNow = localtime(now)
			dayBitmap = self.repeated
			day = []
			for bits in (0, 1, 2, 3, 4, 5, 6):
				day.append(0 if dayBitmap & 1 == 1 else 1)
				dayBitmap >>= 1
			# If day is NOT in the list of repeated days OR if the day IS in the list of the repeated days,
			# check, if event is currently running then, if findRunningEvent is false, go to the next event.
			while ((day[localBegin.tm_wday] != 0) or (mktime(localRepeatedBeginDate) > mktime(localBegin)) or (day[localBegin.tm_wday] == 0 and (findRunningEvent and localEnd < localNow) or ((not findRunningEvent) and localBegin < localNow))):
				localBegin = self.addOneDay(localBegin)
				localEnd = self.addOneDay(localEnd)
			# We now have a struct_time representation of begin and end in localtime, but we have to calculate back to (GMT) seconds since epoch.
			self.begin = int(mktime(localBegin))
			self.end = int(mktime(localEnd))
			if self.begin == self.end:
				self.end += 1
			self.timeChanged()

	def addOneDay(self, timeStruct):
		oldHour = timeStruct.tm_hour
		newDate = (datetime(timeStruct.tm_year, timeStruct.tm_mon, timeStruct.tm_mday, timeStruct.tm_hour, timeStruct.tm_min, timeStruct.tm_sec) + timedelta(days=1)).timetuple()
		if localtime(mktime(newDate)).tm_hour != oldHour:
			return (datetime(timeStruct.tm_year, timeStruct.tm_mon, timeStruct.tm_mday, timeStruct.tm_hour, timeStruct.tm_min, timeStruct.tm_sec) + timedelta(days=2)).timetuple()
		return newDate

	def resetState(self):
		self.state = self.StateWaiting
		self.cancelled = False
		self.first_try_prepare = 0
		self.findRunningEvent = True
		self.findNextEvent = False
		self.timeChanged()

	def timeChanged(self):  # Can be overridden.
		pass

	def isRunning(self):
		return self.state == self.StateRunning

	def isFindRunningEvent(self):
		return self.findRunningEvent

	def isFindNextEvent(self):
		return self.findNextEvent

	def shouldSkip(self):  # Check if a timer entry must be skipped.
		if self.disabled:
			if self.end <= time() and "SchedulerEntry" not in repr(self):
				self.disabled = False
			return True
		if "SchedulerEntry" in repr(self):  # Types: 3=AUTOSTANDBY, 4=AUTODEEPSTANDBY.
			if (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat != "once":
				return False
			elif self.begin >= time() and (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat == "once":
				return False
			elif (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat == "once" and self.state != TimerEntry.StatePrepared:
				return True
			else:
				return self.end <= time() and self.state == TimerEntry.StateWaiting and self.timerType != 3 and self.timerType != 4
		else:
			return self.end <= time() and (self.state == TimerEntry.StateWaiting or self.state == TimerEntry.StateFailed)

	def abort(self):
		self.end = int(time())
		if self.begin > self.end:  # In case timer has not yet started, but gets aborted (so it's preparing), set begin to now.
			self.begin = self.end
		self.cancelled = True

	def fail(self):
		self.failed = True

	def disable(self):
		self.disabled = True

	def enable(self):
		self.disabled = False
