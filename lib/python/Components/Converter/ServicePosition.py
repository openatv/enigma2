from Converter import Converter
from Poll import Poll
from enigma import iPlayableService

class ServicePosition(Converter, Poll, object):
	TYPE_LENGTH = 0,
	TYPE_POSITION = 1,
	TYPE_REMAINING = 2,
	TYPE_GAUGE = 3
	
	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		if type == "Length":
			self.type = self.TYPE_LENGTH
		elif type == "Position":
			self.type = self.TYPE_POSITION
		elif type == "Remaining":
			self.type = self.TYPE_REMAINING
		elif type == "Gauge":
			self.type = self.TYPE_GAUGE

		self.poll_interval = 500
		self.poll_enabled = self.type != self.TYPE_LENGTH
	
	def getSeek(self):
		s = self.source.service
		return s and s.seek()
	
	def getPosition(self):
		seek = self.getSeek()
		if seek is None:
			return None
		pos = seek.getPlayPosition()
		if pos[0]:
			return 0
		return pos[1]
	
	def getLength(self):
		seek = self.getSeek()
		if seek is None:
			return None
		length = seek.getLength()
		if length[0]:
			return 0
		return length[1]
	
	def getCutlist(self):
		service = self.source.service
		cue = service and service.cueSheet()
		return cue and cue.getCutList()
	
	def getText(self):
		seek = self.getSeek()
		if seek is None:
			return ""
		else:
			if self.type == self.TYPE_LENGTH:
				l = self.length
			elif self.type == self.TYPE_POSITION:
				l = self.position
			elif self.type == self.TYPE_REMAINING:
				l = self.length - self.position
			
			l /= 90000
			return "%d:%02d" % (l/60, l%60)

	position = property(getPosition)
	length = property(getLength)
	cutlist = property(getCutlist)
	text = property(getText)
	
	def changed(self, *args):
		cutlist_refresh = len(args) and args[0] in [iPlayableService.evCuesheetChanged, iPlayableService.evStart, iPlayableService.evEnd]
		time_refresh = not len(args) or args[0] in [iPlayableService.evStart, iPlayableService.evEnd]
		
		if cutlist_refresh:
			if self.type == self.TYPE_GAUGE:
				self.downstream_elements.cutlist_changed()

		if time_refresh:
			self.downstream_elements.changed()
