from datetime import datetime

from enigma import iPlayableService
from Poll import Poll
from Components.Converter.Converter import Converter
from Components.Element import cached


class VfdDisplay(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.num = None
		self.showclock = 0
		self.delay = 5000
		self.loop = -1
		self.type = type.lower().split(';')
		if 'number' in self.type and 'clock' not in self.type:  # Only channel number
			self.delay = 0
			self.poll_enabled = False
		else:
			self.poll_enabled = True
			if 'clock' in self.type and 'number' not in self.type:  # Only clock
				self.showclock = 1
				self.delay = -1
			else:
				for x in self.type:
					if x.isdigit():
						self.delay = int(x) * 1000
						break
				if 'loop' in self.type and self.delay:
					self.loop = self.delay
			if '12h' in self.type and 'nozero' in self.type:
				self.hour = '%l'
			elif '12h' in self.type:
				self.hour = '%I'
			elif 'nozero' in self.type:
				self.hour = '%k'
			else:
				self.hour = '%H'

	@cached
	def getText(self):
		if self.showclock == 0:
			if self.delay:
				self.poll_interval = self.delay
				self.showclock = 1
			if self.num:
				return self.num
		else:
			if self.showclock == 1:
				if 'noblink' in self.type:
					self.poll_interval = self.delay
				else:
					self.poll_interval = 1000
					self.showclock = 3
				clockformat = self.hour + '%02M'
			elif self.showclock == 2:
				self.showclock = 3
				clockformat = self.hour + '%02M'
			else:
				self.showclock = 2
				clockformat = self.hour + ':%02M'
			if self.loop != -1:
				self.loop -= 1000
				if self.loop <= 0:
					self.loop = self.delay
					self.showclock = 0
			return datetime.today().strftime(clockformat)

	text = property(getText)

	def changed(self, what):
		if what[0] is self.CHANGED_SPECIFIC and self.delay >= 0 and what[1] == iPlayableService.evStart:
			self.showclock = 0
			if self.loop != -1:
				self.loop = self.delay
			service = self.source.serviceref
			self.num = service and ('%d' if 'nozero' in self.type else '%04d') % service.getChannelNum() or None
			Converter.changed(self, what)
		elif what[0] is self.CHANGED_POLL:
			Converter.changed(self, what)
 
