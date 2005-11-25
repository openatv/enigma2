import bisect
import time
from enigma import *

class TimerEntry:
	EventPrepare = 0
	EventStart   = 1
	EventEnd     = 2
	EventAbort   = 3
	
	StateWait    = 0
	StatePrepare = 1
	StateRunning = 2
	StateEnded   = 3
	
	def __init__(self, begin, end):
		self.begin = begin
		self.prepare_time = 10
		self.end = end
		self.state = 0
		self.resetRepeated()
		
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
		print time.strftime("%c", time.localtime(self.begin))
		print time.strftime("%c", time.localtime(self.end))
		if (self.repeated != 0):
			now = int(time.time()) + 1
			
			day = []
			flags = self.repeated
			for x in range(0, 7):
				if (flags & 1 == 1):
					day.append(0)
					print "Day: " + str(x)
				else:
					day.append(1)
				flags = flags >> 1

			print time.strftime("%c", time.localtime(now))
			print time.strftime("%c", time.localtime(self.begin))
			print time.strftime("%c", time.localtime(self.end))
			print str(time.localtime(self.begin).tm_wday)
			while ((day[time.localtime(self.begin).tm_wday] != 0) or ((day[time.localtime(self.begin).tm_wday] == 0) and self.end < now)):
				print time.strftime("%c", time.localtime(self.begin))
				print time.strftime("%c", time.localtime(self.end))
				self.begin += 86400
				self.end += 86400

	def getTime(self):
		if self.state == self.StateWait:
			return self.begin - self.prepare_time
		elif self.state == self.StatePrepare:
			return self.begin
		else:
			return self.end 
	
	def __lt__(self, o):
		return self.getTime() < o.getTime()
	
	def activate(self, event):
		print "[timer.py] timer %s got activated (%d)!" % (self.description, event)

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
	
	def addTimerEntry(self, entry, noRecalc=0):
		entry.processRepeated()

		# we either go trough Prepare/Start/End-state if the timer is still running,
		# or skip it when it's alrady past the end.
		
		if entry.end > time.time():
			bisect.insort(self.timer_list, entry)
			if not noRecalc:
				self.calcNextActivation()
		else:
			bisect.insort(self.processed_timers, entry)
	
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
				self.addTimerEntry(x, noRecalc=1)
		
		self.processActivation()
		self.lastActivation = time.time()
	
		min = int(time.time()) + self.MaxWaitTime
		
		# calculate next activation point
		if len(self.timer_list):
			w = self.timer_list[0].getTime()
			if w < min:
				min = w
		
		self.setNextActivation(min)
	
	def timeChanged(self, timer):
		self.timer_list.remove(timer)

		self.addTimerEntry(timer)
	
	def doActivate(self, w):
		w.activate(w.state)
		self.timer_list.remove(w)

		w.state += 1
		if w.state < TimerEntry.StateEnded:
			bisect.insort(self.timer_list, w)
		else:
			if (w.repeated != 0):
				w.processRepeated()
				w.state = TimerEntry.StateWait
				self.addTimerEntry(w)
			else:
				bisect.insort(self.processed_timers, w)

	
	def processActivation(self):
		t = int(time.time()) + 1
		
		# we keep on processing the first entry until it goes into the future.
		while len(self.timer_list) and self.timer_list[0].getTime() < t:
			self.doActivate(self.timer_list[0])
