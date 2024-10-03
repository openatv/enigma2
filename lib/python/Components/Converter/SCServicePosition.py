from time import localtime, time
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from enigma import iPlayableService
from Components.Element import cached, ElementError


class SCServicePosition(Poll, Converter):
	TYPE_LENGTH = 0
	TYPE_POSITION = 1
	TYPE_REMAINING = 2
	TYPE_GAUGE = 3
	TYPE_ENDTIME = 4

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)

		args = type.split(',')
		type = args.pop(0)

		self.negate = 'Negate' in args
		self.detailed = 'Detailed' in args
		self.showHours = 'ShowHours' in args
		self.showNoSeconds = 'ShowNoSeconds' in args

		if type == "Length":
			self.type = self.TYPE_LENGTH
		elif type == "Position":
			self.type = self.TYPE_POSITION
		elif type == "Remaining":
			self.type = self.TYPE_REMAINING
		elif type == "Gauge":
			self.type = self.TYPE_GAUGE
		elif type == "EndTime":
			self.type = self.TYPE_ENDTIME
		else:
			raise ElementError("type must be {Length|Position|Remaining|Gauge|EndTime} with optional arguments {Negate|Detailed|ShowHours|ShowNoSeconds} for SCServicePosition converter")

		if self.detailed:
			self.poll_interval = 100
		elif self.TYPE_ENDTIME:
			self.poll_interval = 1000
		elif self.type == self.TYPE_LENGTH:
			self.poll_interval = 2000
		else:
			self.poll_interval = 500

		self.poll_enabled = True

	def getSeek(self):
		s = self.source.service
		return s and s.seek()

	@cached
	def getPosition(self):
		seek = self.getSeek()
		if seek is None:
			return None
		pos = seek.getPlayPosition()
		if pos[0]:
			return 0
		return pos[1]

	@cached
	def getLength(self):
		seek = self.getSeek()
		if seek is None:
			return None
		length = seek.getLength()
		if length[0]:
			return 0
		return length[1]

	@cached
	def getCutlist(self):
		service = self.source.service
		cue = service and service.cueSheet()
		return cue and cue.getCutList()

	@cached
	def getText(self):
		seek = self.getSeek()
		if seek is None:
			return ""
		else:
			if self.type == self.TYPE_LENGTH:
				lVal = self.length
			elif self.type == self.TYPE_POSITION:
				lVal = self.position
			elif self.type == self.TYPE_REMAINING:
				lVal = self.length - self.position
			elif self.type == self.TYPE_ENDTIME:
				lVal = (self.length - self.position) / 90000
				tVal = time()
				tVal = localtime(tVal + lVal)
				if self.showNoSeconds:
					return "%02d:%02d" % (tVal.tm_hour, tVal.tm_min)
				else:
					return "%02d:%02d:%02d" % (tVal.tm_hour, tVal.tm_min, tVal.tm_sec)

			if not self.detailed:
				lVal /= 90000

			if self.negate:
				lVal = -lVal

			if lVal > 0:
				sign = ""
			else:
				lVal = -lVal
				sign = "-"

			if not self.detailed:
				if self.showHours:
					if self.showNoSeconds:
						return sign + "%d:%02d" % (lVal / 3600, lVal % 3600 / 60)
					else:
						return sign + "%d:%02d:%02d" % (lVal / 3600, lVal % 3600 / 60, lVal % 60)
				else:
					if self.showNoSeconds:
						return sign + "%d" % (lVal / 60)
					else:
						return sign + "%d:%02d" % (lVal / 60, lVal % 60)
			else:
				if self.showHours:
					return sign + "%d:%02d:%02d:%03d" % ((lVal / 3600 / 90000), (lVal / 90000) % 3600 / 60, (lVal / 90000) % 60, (lVal % 90000) / 90)
				else:
					return sign + "%d:%02d:%03d" % ((lVal / 60 / 90000), (lVal / 90000) % 60, (lVal % 90000) / 90)

	# range/value are for the Progress renderer
	range = 10000

	@cached
	def getValue(self):
		pos = self.position
		lVal = self.length
		if pos is None or lVal is None or lVal <= 0:
			return None
		return pos * 10000 / lVal

	position = property(getPosition)
	length = property(getLength)
	cutlist = property(getCutlist)
	text = property(getText)
	value = property(getValue)

	def changed(self, what):
		cutlist_refresh = what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evCuesheetChanged,)
		time_refresh = what[0] == self.CHANGED_POLL or what[0] == self.CHANGED_SPECIFIC and what[1] in (iPlayableService.evCuesheetChanged,)

		if cutlist_refresh:
			if self.type == self.TYPE_GAUGE:
				self.downstream_elements.cutlist_changed()

		if time_refresh:
			self.downstream_elements.changed(what)
