from bisect import insort
from time import time, localtime, mktime
from enigma import eTimer, eActionMap
import datetime

class TimerEntry:
	StateWaiting = 0
	StatePrepared = 1
	StateRunning = 2
	StateEnded = 3
	StateFailed = 4

	def __init__(self, begin, end):
		self.begin = begin
		self.prepare_time = 20
		self.end = end
		self.state = 0
		self.findRunningEvent = True
		self.findNextEvent = False
		self.resetRepeated()
		# begindate = localtime(self.begin)
		# newdate = datetime.datetime(begindate.tm_year, begindate.tm_mon, begindate.tm_mday 0, 0, 0);
		self.repeatedbegindate = begin
		self.backoff = 0

		self.disabled = False
		self.failed = False

	def resetState(self):
		self.state = self.StateWaiting
		self.cancelled = False
		self.first_try_prepare = True
		self.findRunningEvent = True
		self.findNextEvent = False
		self.timeChanged()

	def resetRepeated(self):
		self.repeated = int(0)

	def setRepeated(self, day):
		self.repeated |= (2 ** day)

	def isRunning(self):
		return self.state == self.StateRunning

	def addOneDay(self, timedatestruct):
		oldHour = timedatestruct.tm_hour
		newdate = (datetime.datetime(timedatestruct.tm_year, timedatestruct.tm_mon, timedatestruct.tm_mday, timedatestruct.tm_hour, timedatestruct.tm_min, timedatestruct.tm_sec) + datetime.timedelta(days=1)).timetuple()
		if localtime(mktime(newdate)).tm_hour != oldHour:
			return (datetime.datetime(timedatestruct.tm_year, timedatestruct.tm_mon, timedatestruct.tm_mday, timedatestruct.tm_hour, timedatestruct.tm_min, timedatestruct.tm_sec) + datetime.timedelta(days=2)).timetuple()
		return newdate

	def isFindRunningEvent(self):
		return self.findRunningEvent

	def isFindNextEvent(self):
		return self.findNextEvent

	# Update self.begin and self.end using the self.repeated flags
	def processRepeated(self, findRunningEvent=True, findNextEvent=False):
		if self.repeated != 0:
			now = int(time()) + 1
			if findNextEvent:
				now = self.end + 120
			self.findRunningEvent = findRunningEvent
			self.findNextEvent = findNextEvent
			# To avoid problems with daylight saving,
			# we need to calculate with localtime,
			# in struct_time representation
			localrepeatedbegindate = localtime(self.repeatedbegindate)
			localbegin = localtime(self.begin)
			localend = localtime(self.end)
			localnow = localtime(now)

			# Expand the repeat flags out into day[].
			# In this process the flags are *inverted* in day[] from
			# their values in self.repeated.

			day = []
			flags = self.repeated
			for x in (0, 1, 2, 3, 4, 5, 6):
				if flags & 1 == 1:
					day.append(0)
				else:
					day.append(1)
				flags >>= 1

			# Step through the days until the day for the new timer
			# start/end is:
			#     a day on which the timer repeats (day[localbegin.tm_wday] == 0)
			#  and
			#     the start is after the initial start time for the repeat timer
			#  and
			#     if findRunningEvent
			#        the new timer end has not passed
			#     otherwise
			#        the new timer start has not passed

			while (
				(day[localbegin.tm_wday] != 0) or
				(mktime(localrepeatedbegindate) > mktime(localbegin)) or
				(
					day[localbegin.tm_wday] == 0 and (findRunningEvent and localend < localnow) or
					((not findRunningEvent) and localbegin < localnow)
				)
			):
				localbegin = self.addOneDay(localbegin)
				localend = self.addOneDay(localend)

			# We now have a struct_time representation of
			# begin and end in localtime,
			# but we have to calculate back to (gmt) seconds since epoch
			self.begin = int(mktime(localbegin))
			self.end = int(mktime(localend))
			if self.begin == self.end:
				self.end += 1

			self.timeChanged()

	def __lt__(self, o):
		return self.getNextActivation() < o.getNextActivation()

	# Must be overridden
	def activate(self):
		pass

	# Can be overridden
	def timeChanged(self):
		pass

	# Check if a timer entry must be skipped
	def shouldSkip(self):
		if self.disabled:
			if self.end <= time() and not self.repeated and "PowerTimerEntry" not in repr(self):
				self.disabled = False
			return True
		if "PowerTimerEntry" in repr(self):
			if (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat != 'once':
				return False
			elif self.begin >= time() and (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat == 'once':
				return False
			elif (self.timerType == 3 or self.timerType == 4) and self.autosleeprepeat == 'once' and self.state != TimerEntry.StatePrepared:
				return True
			else:
				return self.end <= time() and self.state == TimerEntry.StateWaiting and self.timerType != 3 and self.timerType != 4
		else:
			return self.end <= time() and (self.state == TimerEntry.StateWaiting or self.state == TimerEntry.StateFailed)

	def abort(self):
		self.end = time()

		# If timer has not yet started when it is aborted (i.e. it's preparing),
		# set begin to now.
		if self.begin > self.end:
			self.begin = self.end

		self.cancelled = True

	# Must be overridden!
	def getNextActivation(self):
		pass

	def fail(self):
		self.failed = True

	def disable(self):
		self.disabled = True

	def enable(self):
		self.disabled = False

class Timer:
	# The maximum time between "polls". We do this because
	# we want to account for time jumps etc.
	# of course if they occur <100s before starting,
	# it's not good. So you have to repoll when
	# you change the time.
	#
	# This is just in case. We don't want the timer
	# hanging. We use a "edge-triggered-polling-scheme"
	# anyway, so why not make it a bit more fool-proof?
	MaxWaitTime = 100

	def __init__(self):
		self.timer_list = []
		self.processed_timers = []

		self.timer = eTimer()
		self.timer.callback.append(self.calcNextActivation)
		self.lastActivation = time()

		self.calcNextActivation()
		self.on_state_change = []

	def stateChanged(self, entry):
		for f in self.on_state_change:
			f(entry)

	def cleanup(self):
		self.processed_timers = [entry for entry in self.processed_timers if entry.disabled]

	def cleanupDisabled(self):
		disabled_timers = [entry for entry in self.processed_timers if entry.disabled]
		for timer in disabled_timers:
			timer.shouldSkip()

	def cleanupDaily(self, days):
		limit = time() - (days * 3600 * 24)
		self.processed_timers = [entry for entry in self.processed_timers if (entry.disabled and entry.repeated) or (entry.end and (entry.end > limit))]

	def addTimerEntry(self, entry, noRecalc=0):
		entry.processRepeated()

		# If this timer needs to be skipped, has completed
		# or has been disabled, don't go through
		# waiting/running/end-states, but sort it straight into
		# the processedTimers.
		if entry.shouldSkip() or entry.state == TimerEntry.StateEnded or (entry.state == TimerEntry.StateWaiting and entry.disabled):
			insort(self.processed_timers, entry)
			entry.state = TimerEntry.StateEnded
		else:
			insort(self.timer_list, entry)
			if not noRecalc:
				self.calcNextActivation()

# Small piece of example code to demonstrate how to use record simulation
# 		if NavigationInstance.instance:
# 			lst = [ ]
# 			cnt = 0
# 			for timer in self.timer_list:
# 				print "timer", cnt
# 				cnt += 1
# 				if timer.state == 0: #waiting
# 					lst.append(NavigationInstance.instance.recordService(timer.service_ref))
# 				else:
# 					print "STATE: ", timer.state
#
# 			for rec in lst:
# 				if rec.start(True): #simulate
# 					print "FAILED!!!!!!!!!!!!"
# 				else:
# 					print "OK!!!!!!!!!!!!!!"
# 				NavigationInstance.instance.stopRecordService(rec)
# 		else:
# 			print "no NAV"

	def setNextActivation(self, now, when):
		delay = int((when - now) * 1000)
		self.timer.start(delay, 1)
		self.next = when

	def calcNextActivation(self):
		now = time()
		if self.lastActivation > now:
			print "[timer.py] timewarp - re-evaluating all processed timers."
			tl = self.processed_timers
			self.processed_timers = []
			for x in tl:
				# Simulate a "waiting" state to give them a chance to re-occur
				x.resetState()
				self.addTimerEntry(x, noRecalc=1)

		self.processActivation()
		self.lastActivation = now

		min = int(now) + self.MaxWaitTime

		# Calculate next activation point
		if self.timer_list:
			w = self.timer_list[0].getNextActivation()
			if w < min:
				min = w

		if int(now) < 1072224000 and min > now + 5:
			# System time has not yet been set (before ~01.01.2004), keep a short poll interval
			min = now + 5

		self.setNextActivation(now, min)

	def timeChanged(self, timer):
		timer.timeChanged()
		if timer.state == TimerEntry.StateEnded:
			self.processed_timers.remove(timer)
		else:
			try:
				self.timer_list.remove(timer)
			except:
				print "[timer] Failed to remove, not in list"
				return
		# Give the timer a chance to re-enqueue
		if timer.state == TimerEntry.StateEnded:
			timer.state = TimerEntry.StateWaiting
		elif "PowerTimerEntry" in repr(timer) and (timer.timerType == 3 or timer.timerType == 4):
			if timer.state > 0:
				eActionMap.getInstance().unbindAction('', timer.keyPressed)
			timer.state = TimerEntry.StateWaiting

		self.addTimerEntry(timer)

	def doActivate(self, w):
		self.timer_list.remove(w)

		# If the timer should be skipped (e.g. disabled or
		# its end time has past), simply abort the timer.
		# Don't run through all the states.
		if w.shouldSkip():
			w.state = TimerEntry.StateEnded
		else:
			# If active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# The timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1

		# Did this timer reached the final state?
		if w.state < TimerEntry.StateEnded:
			# No, sort it into active list
			insort(self.timer_list, w)
		else:
			# Yes. Process repeat if necessary, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = TimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				insort(self.processed_timers, w)

		self.stateChanged(w)

	def processActivation(self):
		t = int(time()) + 1
		# We keep on processing the first entry until it goes into the future.
		while self.timer_list and self.timer_list[0].getNextActivation() < t:
			self.doActivate(self.timer_list[0])
