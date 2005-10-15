import bisect
from time import *
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
		print "timer %s got activated (%d)!" % (self.description, event)

class Timer:

	MaxWaitTime = 100

	def __init__(self):
		self.timer_list = [ ]
		self.processed_timers = [ ]
		
		self.timer = eTimer()
		self.timer.timeout.get().append(self.calcNextActivation)
		
		self.calcNextActivation()
	
	def addTimerEntry(self, entry):
		bisect.insort(self.timer_list, entry)
		self.calcNextActivation()
	
	def setNextActivation(self, when):
		delay = int((when - time()) * 1000)
		print "next activation: %d (in %d ms)" % (when, delay)
		
		self.timer.start(delay, 1)
		self.next = when

	def calcNextActivation(self):
		self.processActivation()
	
		min = int(time()) + self.MaxWaitTime
		
		# calculate next activation point
		if len(self.timer_list):
			w = self.timer_list[0].getTime()
			if w < min:
				min = w
		
		self.setNextActivation(min)
	
	def timeChanged(self, timer):
		self.timer_list.remove(timer)
		bisect.insort(self.timer_list, timer)
	
	def doActivate(self, w):
		w.activate(w.state)
		self.timer_list.remove(w)
		w.state += 1
		if w.state < TimerEntry.StateEnded:
			bisect.insort(self.timer_list, w)
		else:
			bisect.insort(self.processed_timers, w)
	
	def processActivation(self):
		t = int(time()) + 1
		
		# we keep on processing the first entry until it goes into the future.
		while len(self.timer_list) and self.timer_list[0].getTime() < t:
			self.doActivate(self.timer_list[0])

#t = Timer()
#base = time() + 5
#t.addTimerEntry(TimerEntry(base+10, base+20, None, None, "test #1: 10 - 20"))
#t.addTimerEntry(TimerEntry(base+10, base+30, None, None, "test #2: 10 - 30"))
#t.addTimerEntry(TimerEntry(base+15, base+20, None, None, "test #3: 15 - 20"))
#t.addTimerEntry(TimerEntry(base+20, base+35, None, None, "test #4: 20 - 35"))
