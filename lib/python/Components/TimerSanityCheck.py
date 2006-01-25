from Components.config import config
from Components.NimManager import nimmanager
from time import localtime

class TimerSanityCheck:
	def __init__(self, timerlist, newtimer):
		self.timerlist = timerlist
		self.newtimer = newtimer
		
	def check(self):
		simultimer = [ self.newtimer ]
		for timer in self.timerlist:
			if self.isSimultaneous(timer, self.newtimer):
				simultimer.append(timer)
				
		if len(simultimer) > 1:
			return self.checkRecordable(simultimer)
		
		return True
	
	def isSimultaneous(self, timer1, timer2):
		# both timers are repeated
		if (timer1.repeated & timer2.repeated):
			return True

		# one timer is repeated
		if not timer1.repeated:
			tmp = timer1
			timer1 = timer2
			timer2 = tmp

		if timer1.repeated:
			dow2 = (localtime(timer2.begin).tm_wday - 1) % 7
			
			if timer1.repeated & (2 ** dow2):
				return True
		else:
			if (timer1.begin < timer2.begin < timer1.end) or (timer2.begin < timer1.begin < timer2.end):
				return True

		return False
	
	def checkRecordable(self, timerlist):
		# TODO: Add code here
		return True