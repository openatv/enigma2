from Components.NimManager import nimmanager
from time import localtime

class TimerSanityCheck:
	def __init__(self, timerlist, newtimer):
		self.timerlist = timerlist
		self.newtimer = newtimer
		self.simultimer = []
				
	def check(self):
		self.simultimer = [ self.newtimer ]
		for timer in self.timerlist:
			if self.isSimultaneous(timer, self.newtimer):
				self.simultimer.append(timer)
		
		if len(self.simultimer) > 1:
			return self.checkRecordable(self.simultimer)
		
		return True

	def getSimulTimerList(self):
		return self.simultimer
	
	def isSimultaneous(self, timer1, timer2):
		# both timers are repeated
		if (timer1.repeated & timer2.repeated):
			return self.timeEquals(timer1, timer2)

		# one timer is repeated
		if not timer1.repeated:
			tmp = timer1
			timer1 = timer2
			timer2 = tmp

		if timer1.repeated:
			dow2 = (localtime(timer2.begin).tm_wday - 1) % 7
			
			if timer1.repeated & (2 ** dow2):
				return self.timeEquals(timer1, timer2)
		else:
			if (timer1.begin <= timer2.begin < timer1.end) or (timer2.begin <= timer1.begin < timer2.end):
				return True

		return False

	def timeEquals(self, timer1, timer2):
		ltb1 = localtime(timer1.begin)
		ltb2 = localtime(timer2.begin)
				
		begin1 = ltb1.tm_hour * 3600 + ltb1.tm_min * 60 + ltb1.tm_sec
		begin2 = ltb2.tm_hour * 3600 + ltb2.tm_min * 60 + ltb2.tm_sec
		
		end1 = begin1 + timer1.end - timer1.begin
		end2 = begin2 + timer2.end - timer2.begin
		
		return (begin1 <= begin2 < end1) or (begin2 <= begin1 < end2)
	
	def checkRecordable(self, timerlist):
		# TODO: Add code here
		return True