from PerServiceDisplay import *
from enigma import eTimer

from enigma import iPlayableService, iSeekableServicePtr, ePositionGauge

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
		
		self.updateTimer.start(500)
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
		seek = None
		service = self.navcore.getCurrentService()
		if service != None:
			seek = service.seek()

		if seek is not None:
			if self.type == self.TYPE_LENGTH:
				l = self.get(self.TYPE_LENGTH)
			elif self.type == self.TYPE_POSITION:
				l = self.get(self.TYPE_POSITION)
			elif self.type == self.TYPE_REMAINING:
				l = self.get(self.TYPE_LENGTH) - self.get(self.TYPE_POSITION)
			
			self.setText("%d:%02d" % (l/60, l%60))
			self.updateTimer.start(500)
		else:
			self.updateTimer.start(10000)
			self.setText("-:--")
	
	def stopEvent(self):
		self.updateTimer.stop()
		self.setText("");

class ServicePositionGauge(PerServiceBase):
	def __init__(self, navcore):
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.newService,
				iPlayableService.evEnd: self.stopEvent
			})

	def newService(self):
		if self.get() is None:	
			self.disablePolling()
		else:
			self.enablePolling(interval=500)
	
	def get(self):
		service = self.navcore.getCurrentService()
		if service is None:
			return None
		seek = service.seek()
		if seek is None:
			return None

		len = seek.getLength()
		pos = seek.getPlayPosition()
		
		if len[0] or pos[0]:
			return (0, 0)
		return (len[1], pos[1])
	
	def poll(self):
		data = self.get()
		if data is None:
			return
		self.instance.setLength(data[0])
		self.instance.setPosition(data[1])
		
	def stopEvent(self):
		self.disablePolling()

	def GUIcreate(self, parent):
		self.instance = ePositionGauge(parent)
	
	def GUIdelete(self):
		self.instance = None
