from time import localtime, time

from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import ElementError, cached


class SCServicePosition(Poll, Converter):
	TYPE_LENGTH = 0
	TYPE_POSITION = 1
	TYPE_REMAINING = 2
	TYPE_GAUGE = 3
	TYPE_ENDTIME = 4

	def __init__(self, tokens):
		Poll.__init__(self)
		Converter.__init__(self, tokens)
		args = tokens.split(",")
		self.type = {
			"EndTime": self.TYPE_ENDTIME,
			"Gauge": self.TYPE_GAUGE,
			"Length": self.TYPE_LENGTH,
			"Position": self.TYPE_POSITION,
			"Remaining": self.TYPE_REMAINING
		}.get(args.pop(0))
		if self.type is None:
			raise ElementError("type must be {Length|Position|Remaining|Gauge|EndTime} with optional arguments {Negate|Detailed|ShowHours|ShowNoSeconds} for SCServicePosition converter")
		self.negate = "Negate" in args
		self.detailed = "Detailed" in args
		self.showHours = "ShowHours" in args
		self.showNoSeconds = "ShowNoSeconds" in args
		# FIXME: The original code checked "elif self.TYPE_ENDTIME:" which is always true, so every type
		# that is not detailed polls with 1000. The intended values were 1000 for EndTime, 2000 for Length and 500 for all others.
		self.poll_interval = 100 if self.detailed else 1000
		self.poll_enabled = True

	def changed(self, what):
		cutlistRefresh = what[0] != self.CHANGED_SPECIFIC or what[1] == iPlayableService.evCuesheetChanged
		timeRefresh = what[0] == self.CHANGED_POLL or what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evCuesheetChanged
		if cutlistRefresh and self.type == self.TYPE_GAUGE:
			self.downstream_elements.cutlist_changed()
		if timeRefresh:
			self.downstream_elements.changed(what)

	@cached
	def getCutlist(self):
		service = self.source.service
		cue = service and service.cueSheet()
		return cue and cue.getCutList()

	cutlist = property(getCutlist)

	@cached
	def getLength(self):
		result = None
		seek = self.getSeek()
		if seek is not None:
			length = seek.getLength()
			result = 0 if length[0] else length[1]
		return result

	length = property(getLength)

	@cached
	def getPosition(self):
		result = None
		seek = self.getSeek()
		if seek is not None:
			position = seek.getPlayPosition()
			result = 0 if position[0] else position[1]
		return result

	position = property(getPosition)

	def getSeek(self):
		service = self.source.service
		return service and service.seek()

	@cached
	def getText(self):
		text = ""
		if self.getSeek() is not None:
			if self.type == self.TYPE_ENDTIME:
				endTime = localtime(time() + (self.length - self.position) / 90000)
				text = f"{endTime.tm_hour:02d}:{endTime.tm_min:02d}" if self.showNoSeconds else f"{endTime.tm_hour:02d}:{endTime.tm_min:02d}:{endTime.tm_sec:02d}"
			else:
				match self.type:
					case self.TYPE_LENGTH:
						timeValue = self.length
					case self.TYPE_POSITION:
						timeValue = self.position
					case self.TYPE_REMAINING:
						timeValue = self.length - self.position
					case _:
						timeValue = 0
				if not self.detailed:
					timeValue /= 90000
				if self.negate:
					timeValue = -timeValue
				if timeValue > 0:
					sign = ""
				else:
					timeValue = -timeValue
					sign = "-"
				if self.detailed:
					if self.showHours:
						text = f"{sign}{int(timeValue / 3600 / 90000)}:{int((timeValue / 90000) % 3600 / 60):02d}:{int((timeValue / 90000) % 60):02d}:{int((timeValue % 90000) / 90):03d}"
					else:
						text = f"{sign}{int(timeValue / 60 / 90000)}:{int((timeValue / 90000) % 60):02d}:{int((timeValue % 90000) / 90):03d}"
				elif self.showHours:
					text = f"{sign}{int(timeValue / 3600)}:{int(timeValue % 3600 / 60):02d}" if self.showNoSeconds else f"{sign}{int(timeValue / 3600)}:{int(timeValue % 3600 / 60):02d}:{int(timeValue % 60):02d}"
				else:
					text = f"{sign}{int(timeValue / 60)}" if self.showNoSeconds else f"{sign}{int(timeValue / 60)}:{int(timeValue % 60):02d}"
		return text

	text = property(getText)

	range = 10000  # The range/value are for the Progress renderer.

	@cached
	def getValue(self):
		position = self.position
		length = self.length
		return None if position is None or length is None or length <= 0 else position * 10000 / length

	value = property(getValue)
