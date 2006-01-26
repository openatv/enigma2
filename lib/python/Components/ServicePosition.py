from PerServiceDisplay import *
from enigma import eTimer


from enigma import iPlayableService, iSeekableServicePtr

class ServicePosition(PerServiceDisplay):
	TYPE_LENGTH = 0,
	TYPE_POSITION = 1,
	TYPE_REMAINING = 2
	
	def __init__(self, navcore, type):
		self.updateTimer = eTimer()
		self.updateTimer.timeout.get().append(self.update)
		PerServiceDisplay.__init__(self, navcore,
			{
				iPlayableService.evStart: self.newService,
				iPlayableService.evEnd: self.stopEvent
			})
		self.type = type
#		self.setType(type)

	def newService(self):
		self.setType(self.type)
	
	def setType(self, type):
		self.type = type
		
		seek = iSeekableServicePtr()
		service = self.navcore.getCurrentService()
		
		self.updateTimer.stop()
		self.available = 0
		
		if service != None:
			seek = service.seek()
			if seek != None:
				if self.type != self.TYPE_LENGTH:
					self.updateTimer.start(500)
				
				self.length = self.get(self.TYPE_LENGTH)
				self.available = 1

		self.update()
	
	def get(self, what):
		service = self.navcore.getCurrentService()
		
		if service != None:
			seek = service.seek()
			if seek != None:
				if what == self.TYPE_LENGTH:
					r = seek.getLength()
				elif what == self.TYPE_POSITION:
					r = seek.getPlayPosition()
				if not r[0]:
					return r[1] / 90000
		
		return -1
	
	def update(self):
		if self.available:
			if self.type == self.TYPE_LENGTH:
				l = self.length
			elif self.type == self.TYPE_POSITION:
				l = self.get(self.TYPE_POSITION)
			elif self.type == self.TYPE_REMAINING:
				l = self.length - self.get(self.TYPE_POSITION)
			
			self.setText("%d:%02d" % (l/60, l%60))
		else:
			self.setText("-:--")
	
	def stopEvent(self):
		self.updateTimer.stop()
		self.setText("");
