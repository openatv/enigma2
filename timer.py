import bisect
import time
import calendar
from enigma import *

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
		self.backoff = 0
		
		self.disabled = False
		
	def resetRepeated(self):
		self.repeated = int(0)

	def setRepeated(self, day):
		self.repeated |= (2 ** day)
		print "Repeated: " + str(self.repeated)
		
	def isRunning(self):
		return self.state == self.StateRunning
		
	# update self.begin and self.end according to the self.repeated-flags
	def processRepeated(self):
		print "ProcessRepeated"
		if (self.repeated != 0):
			now = int(time.time()) + 1

			#to avoid problems with daylight saving, we need to calculate with localtime, in struct_time representation
			localbegin = time.localtime(self.begin)
			localend = time.localtime(self.end)
			localnow = time.localtime(now)

			print time.strftime("%c", localbegin)
			print time.strftime("%c", localend)

			day = []
			flags = self.repeated
			for x in range(0, 7):
				if (flags & 1 == 1):
					day.append(0)
					print "Day: " + str(x)
				else:
					day.append(1)
				flags = flags >> 1

			print time.strftime("%c", localnow)
			while ((day[localbegin.tm_wday] != 0) or ((day[localbegin.tm_wday] == 0) and localend < localnow)):
				print time.strftime("%c", localbegin)
				print time.strftime("%c", localend)
				#add one day to the struct_time, we have to convert using gmt functions, because the daylight saving flag might change after we add our 86400 seconds
				localbegin = time.gmtime(calendar.timegm(localbegin) + 86400)
				localend = time.gmtime(calendar.timegm(localend) + 86400)

			#we now have a struct_time representation of begin and end in localtime, but we have to calculate back to (gmt) seconds since epoch
			self.begin = int(time.mktime(localbegin))
			self.end = int(time.mktime(localend)) + 1

			print "ProcessRepeated result"
			print time.strftime("%c", time.localtime(self.begin))
			print time.strftime("%c", time.localtime(self.end))

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
		return self.end <= time.time() and self.state == TimerEntry.StateWaiting

	def abort(self):
		self.end = time.time()
		
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
		self.timer.timeout.get().append(self.calcNextActivation)
		self.lastActivation = time.time()
		
		self.calcNextActivation()
		self.on_state_change = [ ]
	
	def stateChanged(self, entry):
		for f in self.on_state_change:
			f(entry)
			
	def getNextRecordingTime(self):
		if len(self.timer_list) > 0:
			return self.timer_list[0].begin
		return -1
			
	def cleanup(self):
		self.processed_timers = [entry for entry in self.processed_timers if entry.disabled]
	
	def addTimerEntry(self, entry, noRecalc=0):
		entry.processRepeated()

		# when the timer has not yet started, and is already passed,
		# don't go trough waiting/running/end-states, but sort it
		# right into the processedTimers.
		if entry.shouldSkip() or entry.state == TimerEntry.StateEnded or (entry.state == TimerEntry.StateWaiting and entry.disabled):
			print "already passed, skipping"
			print "shouldSkip:", entry.shouldSkip()
			print "state == ended", entry.state == TimerEntry.StateEnded
			print "waiting && disabled:", (entry.state == TimerEntry.StateWaiting and entry.disabled)
			bisect.insort(self.processed_timers, entry)
			entry.state = TimerEntry.StateEnded
		else:
			bisect.insort(self.timer_list, entry)
			if not noRecalc:
				self.calcNextActivation()
	
	def setNextActivation(self, when):
		delay = int((when - time.time()) * 1000)
		print "[timer.py] next activation: %d (in %d ms)" % (when, delay)
		
		self.timer.start(delay, 1)
		self.next = when

	def calcNextActivation(self):
		if self.lastActivation > time.time():
			print "[timer.py] timewarp - re-evaluating all processed timers."
			tl = self.processed_timers
			self.processed_timers = [ ]
			for x in tl:
				# simulate a "waiting" state to give them a chance to re-occure
				x.resetState()
				self.addTimerEntry(x, noRecalc=1)
		
		self.processActivation()
		self.lastActivation = time.time()
	
		min = int(time.time()) + self.MaxWaitTime
		
		# calculate next activation point
		if len(self.timer_list):
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
			self.timer_list.remove(timer)

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
			bisect.insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = TimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				bisect.insort(self.processed_timers, w)
		
		self.stateChanged(w)

	def processActivation(self):
		print "It's now ", time.strftime("%c", time.localtime(time.time()))
		t = int(time.time()) + 1
		
		# we keep on processing the first entry until it goes into the future.
		while len(self.timer_list) and self.timer_list[0].getNextActivation() < t:
			self.doActivate(self.timer_list[0])
