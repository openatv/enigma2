from bisect import insort
from time import strftime, time, localtime, mktime
from enigma import eTimer
import datetime

class TimerEntry:
	StateWaiting  = 0
	StatePrepared = 1
	StateRunning  = 2
	StateEnded    = 3
	
	def __init__(self, begin, end):
		self.begin = begin
		self.prepare_time = 20
		self.end = end
		self.state = 0
		self.resetRepeated()
		#begindate = localtime(self.begin)
		#newdate = datetime.datetime(begindate.tm_year, begindate.tm_mon, begindate.tm_mday 0, 0, 0);
		self.repeatedbegindate = begin
		self.backoff = 0
		
		self.disabled = False

	def resetState(self):
		self.state = self.StateWaiting
		self.cancelled = False
		self.first_try_prepare = True
		self.timeChanged()

	def resetRepeated(self):
		self.repeated = int(0)

	def setRepeated(self, day):
		self.repeated |= (2 ** day)
		
	def isRunning(self):
		return self.state == self.StateRunning
		
	def addOneDay(self, timedatestruct):
		oldHour = timedatestruct.tm_hour
		newdate =  (datetime.datetime(timedatestruct.tm_year, timedatestruct.tm_mon, timedatestruct.tm_mday, timedatestruct.tm_hour, timedatestruct.tm_min, timedatestruct.tm_sec) + datetime.timedelta(days=1)).timetuple()
		if localtime(mktime(newdate)).tm_hour != oldHour:
			return (datetime.datetime(timedatestruct.tm_year, timedatestruct.tm_mon, timedatestruct.tm_mday, timedatestruct.tm_hour, timedatestruct.tm_min, timedatestruct.tm_sec) + datetime.timedelta(days=2)).timetuple()			
		return newdate
		
	# update self.begin and self.end according to the self.repeated-flags
	def processRepeated(self, findRunningEvent = True):
		if (self.repeated != 0):
			now = int(time()) + 1

			#to avoid problems with daylight saving, we need to calculate with localtime, in struct_time representation
			localrepeatedbegindate = localtime(self.repeatedbegindate)
			localbegin = localtime(self.begin)
			localend = localtime(self.end)
			localnow = localtime(now)

			day = []
			flags = self.repeated
			for x in (0, 1, 2, 3, 4, 5, 6):
				if (flags & 1 == 1):
					day.append(0)
				else:
					day.append(1)
				flags = flags >> 1

			# if day is NOT in the list of repeated days
			# OR if the day IS in the list of the repeated days, check, if event is currently running... then if findRunningEvent is false, go to the next event
			while ((day[localbegin.tm_wday] != 0) or (mktime(localrepeatedbegindate) > mktime(localbegin))  or
				((day[localbegin.tm_wday] == 0) and ((findRunningEvent and localend < localnow) or ((not findRunningEvent) and localbegin < localnow)))):
				localbegin = self.addOneDay(localbegin)
				localend = self.addOneDay(localend)
				
			#we now have a struct_time representation of begin and end in localtime, but we have to calculate back to (gmt) seconds since epoch
			self.begin = int(mktime(localbegin))
			self.end = int(mktime(localend))
			if self.begin == self.end:
				self.end += 1

			self.timeChanged()

	def __lt__(self, o):
		return self.getNextActivation() < o.getNextActivation()
	
	# must be overridden
	def activate(self):
		pass
		
	# can be overridden
	def timeChanged(self):
		pass

	# check if a timer entry must be skipped
	def shouldSkip(self):
		return self.end <= time() and self.state == TimerEntry.StateWaiting

	def abort(self):
		self.end = time()
		
		# in case timer has not yet started, but gets aborted (so it's preparing),
		# set begin to now.
		if self.begin > self.end:
			self.begin = self.end

		self.cancelled = True
	
	# must be overridden!
	def getNextActivation():
		pass

	def disable(self):
		self.disabled = True
	
	def enable(self):
		self.disabled = False

class Timer:
	# the time between "polls". We do this because
	# we want to account for time jumps etc.
	# of course if they occur <100s before starting,
	# it's not good. thus, you have to repoll when
	# you change the time.
	#
	# this is just in case. We don't want the timer 
	# hanging. we use this "edge-triggered-polling-scheme"
	# anyway, so why don't make it a bit more fool-proof?
	MaxWaitTime = 100

	def __init__(self):
		self.timer_list = [ ]
		self.processed_timers = [ ]
		
		self.timer = eTimer()
		self.timer.callback.append(self.calcNextActivation)
		self.lastActivation = time()
		
		self.calcNextActivation()
		self.on_state_change = [ ]

	def stateChanged(self, entry):
		for f in self.on_state_change:
			f(entry)

	def cleanup(self):
		self.processed_timers = [entry for entry in self.processed_timers if entry.disabled]
	
	def cleanupDaily(self, days):
		limit = time() - (days * 3600 * 24) 
		self.processed_timers = [entry for entry in self.processed_timers if (entry.disabled and entry.repeated) or (entry.end and (entry.end > limit))]

	def addTimerEntry(self, entry, noRecalc=0):
		entry.processRepeated()

		# when the timer has not yet started, and is already passed,
		# don't go trough waiting/running/end-states, but sort it
		# right into the processedTimers.
		if entry.shouldSkip() or entry.state == TimerEntry.StateEnded or (entry.state == TimerEntry.StateWaiting and entry.disabled):
			insort(self.processed_timers, entry)
			entry.state = TimerEntry.StateEnded
		else:
			insort(self.timer_list, entry)
			if not noRecalc:
				self.calcNextActivation()

# small piece of example code to understand how to use record simulation
#		if NavigationInstance.instance:
#			lst = [ ]
#			cnt = 0
#			for timer in self.timer_list:
#				print "timer", cnt
#				cnt += 1
#				if timer.state == 0: #waiting
#					lst.append(NavigationInstance.instance.recordService(timer.service_ref))
#				else:
#					print "STATE: ", timer.state
#
#			for rec in lst:
#				if rec.start(True): #simulate
#					print "FAILED!!!!!!!!!!!!"
#				else:
#					print "OK!!!!!!!!!!!!!!"
#				NavigationInstance.instance.stopRecordService(rec)
#		else:
#			print "no NAV"
	
	def setNextActivation(self, when):
		delay = int((when - time()) * 1000)
		self.timer.start(delay, 1)
		self.next = when

	def calcNextActivation(self):
		if self.lastActivation > time():
			print "[timer.py] timewarp - re-evaluating all processed timers."
			tl = self.processed_timers
			self.processed_timers = [ ]
			for x in tl:
				# simulate a "waiting" state to give them a chance to re-occure
				x.resetState()
				self.addTimerEntry(x, noRecalc=1)
		
		self.processActivation()
		self.lastActivation = time()
	
		min = int(time()) + self.MaxWaitTime
		
		# calculate next activation point
		if self.timer_list:
			w = self.timer_list[0].getNextActivation()
			if w < min:
				min = w
		
		self.setNextActivation(min)
	
	def timeChanged(self, timer):
		print "time changed"
		timer.timeChanged()
		if timer.state == TimerEntry.StateEnded:
			self.processed_timers.remove(timer)
		else:
			try:
				self.timer_list.remove(timer)
			except:
				print "[timer] Failed to remove, not in list"
				return
		# give the timer a chance to re-enqueue
		if timer.state == TimerEntry.StateEnded:
			timer.state = TimerEntry.StateWaiting
		self.addTimerEntry(timer)
	
	def doActivate(self, w):
		self.timer_list.remove(w)

		# when activating a timer which has already passed,
		# simply abort the timer. don't run trough all the stages.
		if w.shouldSkip():
			w.state = TimerEntry.StateEnded
		else:
			# when active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# the timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1

		# did this timer reached the last state?
		if w.state < TimerEntry.StateEnded:
			# no, sort it into active list
			insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = TimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				insort(self.processed_timers, w)
		
		self.stateChanged(w)

	def processActivation(self):
		t = int(time()) + 1
		# we keep on processing the first entry until it goes into the future.
		while self.timer_list and self.timer_list[0].getNextActivation() < t:
			self.doActivate(self.timer_list[0])
