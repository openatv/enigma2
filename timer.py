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
		self.Begin = begin
		self.Prepare = 10
		self.End = end
		self.State = 0
	
	def getTime(self):
		if self.State == 0:
			return self.Begin - self.Prepare
		elif self.State == 1:
			return self.Begin
		else:
			return self.End 
	
	def __lt__(self, o):
		return self.getTime() < o.getTime()
	
	def activate(self, event):
		print "timer %s got activated (%d)!" % (self.Description, event)

class Timer:

	MaxWaitTime = 100

	def __init__(self):
		self.TimerList = [ ]
		self.ProcessedTimers = [ ]
		
		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.calcNextActivation)
		
		self.calcNextActivation()
	
	def addTimerEntry(self, entry):
		bisect.insort(self.TimerList, entry)
		self.calcNextActivation()
	
	def setNextActivation(self, when):
		delay = int((when - time()) * 1000)
		print "next activation: %d (in %d seconds)" % (when, delay)
		
		self.Timer.start(delay, 1)
		self.next = when

	def calcNextActivation(self):
		self.processActivation()
	
		min = int(time()) + self.MaxWaitTime
		
		# calculate next activation point
		if len(self.TimerList):
			w = self.TimerList[0].getTime()
			if w < min:
				min = w
		
		self.setNextActivation(min)
	
	def doActivate(self, w):
		w.activate(w.State)
		self.TimerList.remove(w)
		w.State += 1
		if w.State < TimerEntry.StateEnded:
			bisect.insort(self.TimerList, w)
		else:
			bisect.insort(self.ProcessedTimers, w)
	
	def processActivation(self):
		t = int(time()) + 1
		
		# we keep on processing the first entry until it goes into the future.
		while len(self.TimerList) and self.TimerList[0].getTime() < t:
			self.doActivate(self.TimerList[0])

#t = Timer()
#base = time() + 5
#t.addTimerEntry(TimerEntry(base+10, base+20, None, None, "test #1: 10 - 20"))
#t.addTimerEntry(TimerEntry(base+10, base+30, None, None, "test #2: 10 - 30"))
#t.addTimerEntry(TimerEntry(base+15, base+20, None, None, "test #3: 15 - 20"))
#t.addTimerEntry(TimerEntry(base+20, base+35, None, None, "test #4: 20 - 35"))
