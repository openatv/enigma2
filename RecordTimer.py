from timer import *
import time

class RecordTimerEntry(TimerEntry):
	def __init__(self, begin, end, nav, serviceref, epg):
		TimerEntry.__init__(self, begin, end)
		self.ServiceRef = serviceref
		self.EpgData = epg
		self.Timer = None
		self.Nav = nav
		self.RecordService = None
		
		# build filename from epg
		
		# pff das geht noch nicht...
		if epg == None:
			self.Filename = "recording.ts"
		else:
			self.Filename = "record_" + str(epg.m_event_name) + ".ts"
		
		print "------------ record filename: %s" % (self.Filename)
		
	def activate(self, event):
		if event == self.EventPrepare:
			self.RecordService = self.Nav.recordService(self.ServiceRef)
			if self.RecordService == None:
				print "timer record failed."
			else:	
				self.RecordService.prepare()
		elif self.RecordService == None:
			if event != self.EventAbort:
				print "timer record start failed, can't finish recording."
		elif event == self.EventStart:
			self.RecordService.start()
			print "timer started!"
		elif event == self.EventEnd or event == self.EventAbort:
			self.RecordService.stop()
			self.RecordService = None
			print "Timer successfully ended"

class RecordTimer(Timer):
	def __init__(self):
		Timer.__init__(self)
		
	def loadTimer(self):
		print "TODO: load timers from xml"
	
	def saveTimer(self):
		print "TODO: save timers to xml"
	
	def record(self, entry):
		entry.Timer = self
		self.addTimerEntry(entry)

	def removeEntry(self, entry):
		if entry.State == TimerEntry.StateRunning:
			entry.End = time.time()
			print "aborting timer"
		elif entry.State != TimerEntry.StateEnded:
			entry.activate(TimerEntry.EventAbort)
			self.TimerList.remove(entry)
			print "timer did not yet start - removing"
		else:
			print "timer did already end - doing nothing."

		self.calcNextActivation()
