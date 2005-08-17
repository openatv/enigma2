from PerServiceDisplay import *
from enigma import eTimer


from enigma import pNavigation, iSeekableServicePtr

class ServicePosition(PerServiceDisplay):
	def __init__(self, navcore):
		self.updateTimer = eTimer()
		self.updateTimer.timeout.get().append(self.update)
		PerServiceDisplay.__init__(self, navcore,
			{
				pNavigation.evNewService: self.newService,
				pNavigation.evStopService: self.stopEvent
			})

	def newService(self):
		seek = iSeekableServicePtr()
		service = self.navcore.getCurrentService()
		
		self.updateTimer.stop()
		
		if service != None:
			if not service.seek(seek):
				self.updateTimer.start(500)
		
	
	def update(self):
		seek = iSeekableServicePtr()
		service = self.navcore.getCurrentService()
		
		l = -1
		
		if service != None:
			if not service.seek(seek):
				# r = seek.getLength()
				r = seek.getPlayPosition()
				if not r[0]:
					l = r[1] / 90000

		if l != -1:
			self.setText("%d:%02d" % (l/60, l%60))
		else:
			self.setText("-:--")
	
	def stopEvent(self):
		self.updateTimer.stop()
		self.setText("");
