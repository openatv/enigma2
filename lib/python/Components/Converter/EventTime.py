from Converter import Converter
from Poll import Poll
from time import time
from Components.Element import cached, ElementError

class EventTime(Poll, Converter, object):
	STARTTIME = 0
	ENDTIME = 1
	REMAINING = 2
	PROGRESS = 3
	DURATION = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		if type == "EndTime":
			self.type = self.ENDTIME
		elif type == "Remaining":
			self.type = self.REMAINING
			self.poll_interval = 60*1000
			self.poll_enabled = True
		elif type == "StartTime":
			self.type = self.STARTTIME
		elif type == "Duration":
			self.type = self.DURATION
		elif type == "Progress":
			self.type = self.PROGRESS
			self.poll_interval = 30*1000
			self.poll_enabled = True
		else:
			raise ElementError("'%s' is not <StartTime|EndTime|Remaining|Duration|Progress> for EventTime converter" % type)

	@cached
	def getTime(self):
		assert self.type != self.PROGRESS

		event = self.source.event
		if event is None:
			return None

		st = event.getBeginTime()
		if self.type == self.STARTTIME:
			return st

		duration = event.getDuration()
		if self.type == self.DURATION:
			return duration
		st += duration
		if self.type == self.ENDTIME:
			return st
		if self.type == self.REMAINING:
			return (duration, st - int(time()))

	@cached
	def getValue(self):
		assert self.type == self.PROGRESS

		event = self.source.event
		if event is None:
			return None

		progress = int(time()) - event.getBeginTime()
		duration = event.getDuration()
		if duration > 0 and progress >= 0:
			if progress > duration:
				progress = duration
			return progress * 1000 / duration
		else:
			return None

	time = property(getTime)
	value = property(getValue)
	range = 1000

	def changed(self, what):
		Converter.changed(self, what)
		if self.type == self.PROGRESS and len(self.downstream_elements):
			if not self.source.event and self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = False
			elif self.source.event and not self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = True
