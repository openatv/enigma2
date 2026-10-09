from time import localtime, strftime, time as getTime

from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import ElementError, cached
from Components.config import config


class ServicePosition(Poll, Converter):
	TYPE_LENGTH = 0
	TYPE_POSITION = 1
	TYPE_REMAINING = 2
	TYPE_GAUGE = 3
	TYPE_SUMMARY = 4
	TYPE_ENDTIME = 5
	TYPE_VFD_LENGTH = 6
	TYPE_VFD_POSITION = 7
	TYPE_VFD_REMAINING = 8
	TYPE_VFD_GAUGE = 9
	TYPE_VFD_SUMMARY = 10

	def __init__(self, tokens):
		Poll.__init__(self)
		Converter.__init__(self, tokens)
		args = tokens.split(",")
		self.type = {
			"EndTime": self.TYPE_ENDTIME,
			"Gauge": self.TYPE_GAUGE,
			"Length": self.TYPE_LENGTH,
			"Position": self.TYPE_POSITION,
			"Remaining": self.TYPE_REMAINING,
			"Summary": self.TYPE_SUMMARY,
			"VFDGauge": self.TYPE_VFD_GAUGE,
			"VFDLength": self.TYPE_VFD_LENGTH,
			"VFDPosition": self.TYPE_VFD_POSITION,
			"VFDRemaining": self.TYPE_VFD_REMAINING,
			"VFDSummary": self.TYPE_VFD_SUMMARY
		}.get(args.pop(0))
		if self.type is None:
			raise ElementError("type must be {Length|Position|Remaining|Gauge|Summary} with optional arguments {Negate|Detailed|ShowHours|ShowNoSeconds|ShowNoSeconds2} for ServicePosition converter")
		self.negate = "Negate" in args
		self.detailed = "Detailed" in args
		self.showHours = "ShowHours" in args
		self.showNoSeconds = "ShowNoSeconds" in args
		self.showNoSeconds2 = "ShowNoSeconds2" in args
		self.OnlyMinute = "OnlyMinute" in args
		self.vfd = "7segment" in args
		if self.detailed:
			self.poll_interval = 100
		else:
			self.poll_interval = {
				self.TYPE_ENDTIME: 1000,
				self.TYPE_LENGTH: 2000,
				self.TYPE_VFD_LENGTH: 2000
			}.get(self.type, 500)
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
		def detailedHourMinSec(value):
			return f"{int(value / 3600 / 90000)}:{int((value / 90000) % 3600 / 60):02d}:{int((value / 90000) % 60):02d}:{int((value % 90000) / 90):03d}"

		def detailedMinSec(value):
			return f"{int(value / 60 / 90000)}:{int((value / 90000) % 60):02d}:{int((value % 90000) / 90):03d}"

		def formatByType(formatter, lengthSign, swapped=False):
			match baseType:
				case self.TYPE_LENGTH:
					result = f"{lengthSign}{formatter(lVal)}"
				case self.TYPE_POSITION:
					result = f"{signRemaining}{formatter(rVal)}" if swapped else f"{signPosition}{formatter(pVal)}"
				case self.TYPE_REMAINING:
					result = f"{signPosition}{formatter(pVal)}" if swapped else f"{signRemaining}{formatter(rVal)}"
				case _:
					result = ""
			return result

		def formatValue(value, offset=0):  # Format a value for the selected display mode.
			match displayMode:
				case "1":
					result = minutes(value)
				case "2":
					result = minSec(value)
				case "3":
					result = hourMin(value)
				case "4":
					result = hourMinSec(value)
				case _:
					result = f"{int(value / lVal * 100 + offset)}%"
			return result

		def hourMin(value):
			return f"{int(value / 3600)}:{int(value % 3600 / 60):02d}"

		def hourMinSec(value):
			return f"{int(value / 3600)}:{int(value % 3600 / 60):02d}:{int(value % 60):02d}"

		def minSec(value):
			return f"{int(value / 60)}:{int(value % 60):02d}"

		def minutes(value):
			count = int(value / 60)
			return ngettext("%d Min", "%d Mins", count) % count

		text = ""
		if self.getSeek() is not None:
			if self.type in (self.TYPE_SUMMARY, self.TYPE_ENDTIME):
				sVal = self.position / 90000
				eVal = (self.length / 90000) - sVal
				if self.type == self.TYPE_SUMMARY:
					text = f"{int(sVal / 60):02d}:{int(sVal % 60):02d} +{int(eVal / 60):2d}m"
				else:
					text = strftime("%H:%M" if self.showNoSeconds or self.showNoSeconds2 else "%H:%M:%S", localtime(getTime() + eVal))
			elif self.length >= 0:
				lVal = self.length
				pVal = self.position
				rVal = self.length - self.position  # Remaining.
				if not self.detailed:
					lVal /= 90000
					pVal /= 90000
					rVal /= 90000
				if lVal == 0 and pVal > 0:  # Set position to 0 if length = 0 and pos > 0.
					pVal = 0
				if self.negate:
					lVal = -lVal
					pVal = -pVal
					rVal = -rVal
				signLength = "" if lVal >= 0 else "-"
				lVal = abs(lVal)
				pVal = abs(pVal)
				rVal = abs(rVal)
				isVfd = self.type >= self.TYPE_VFD_LENGTH
				if isVfd:
					baseType = self.type - self.TYPE_VFD_LENGTH
					displayMode = config.usage.swap_media_time_display_on_vfd.value
					remainingMode = config.usage.swap_time_remaining_on_vfd.value
					elapsedPositive = config.usage.elapsed_time_positive_vfd.value
				else:
					baseType = self.type
					displayMode = config.usage.swap_media_time_display_on_osd.value
					remainingMode = config.usage.swap_time_remaining_on_osd.value
					elapsedPositive = config.usage.elapsed_time_positive_osd.value
					signLength = ""
				signPosition, signRemaining = ("+", "-") if elapsedPositive else ("-", "+")
				if displayMode in ("1", "2", "3", "4", "5"):  # 1=Mins, 2=Mins Secs, 3=Hours Mins, 4=Hours Mins Secs, 5=Percentage.
					try:
						match baseType:
							case self.TYPE_LENGTH:
								match displayMode:
									case "1":
										text = minutes(lVal)
									case "5":
										text = f"{signLength}{hourMin(lVal)}"
									case _:
										text = f"{signLength}{formatValue(lVal)}"
							case self.TYPE_POSITION | self.TYPE_REMAINING:
								match remainingMode:
									case "1":  # Elapsed.
										text = f"{signPosition}{formatValue(pVal)}"
									case "2" | "3" if baseType == self.TYPE_REMAINING:
										text = ""
									case "2":  # Elapsed & Remaining.
										first = f"{int(pVal / 60)}" if displayMode == "1" else formatValue(pVal)
										text = f"{signPosition}{first}  {signRemaining}{formatValue(rVal, 1)}"
									case "3":  # Remaining & Elapsed.
										first = f"{int(rVal / 60)}" if displayMode == "1" else formatValue(rVal, 1)
										text = f"{signRemaining}{first}  {signPosition}{formatValue(pVal)}"
									case _:  # Remaining.
										text = f"{signRemaining}{formatValue(pVal if displayMode == '5' else rVal)}"
					except ZeroDivisionError:
						text = ""
				else:  # Skin setting.
					noSeconds = self.showNoSeconds or (self.showNoSeconds2 and not isVfd)
					# FIXME: The VFD skin setting checks TYPE_REMAINING instead of TYPE_VFD_REMAINING, so VFDRemaining
					# is only shown with ShowNoSeconds and without ShowHours.
					hideVfdRemaining = isVfd and baseType == self.TYPE_REMAINING
					if self.detailed:
						# FIXME: Position and remaining are swapped with ShowHours.
						text = "" if hideVfdRemaining else formatByType(detailedHourMinSec if self.showHours else detailedMinSec, signLength, swapped=self.showHours)
					elif self.vfd and not isVfd:  # 7-segment display.
						minutesLeft = rVal / 60
						text = f"{int(minutesLeft):2d}:{int(rVal % 60):02d}" if minutesLeft < 60 else f"{int(minutesLeft / 60):2d}:{int(rVal % 3600 / 60):02d}"
					elif self.showHours:
						text = "" if hideVfdRemaining else formatByType(hourMin if noSeconds else hourMinSec, signLength)
					elif noSeconds:
						if baseType == self.TYPE_REMAINING and self.OnlyMinute and not isVfd:
							if self.showNoSeconds:
								text = f"{int(rVal / 60)}"
							else:
								restMinutes = " " if rVal == 0 else f"{int(rVal / 60) if config.usage.elapsed_time_positive_vfd.value else int(rVal / 60 * -1):+6d}"
								text = f"{strftime(_('%-H:%M'), localtime(getTime()))}{restMinutes}"
						else:
							text = formatByType(minutes, "")
					else:
						text = "" if hideVfdRemaining else formatByType(minSec, signLength)
		return text

	text = property(getText)

	range = 10000  # The range/value are for the Progress renderer.

	@cached
	def getValue(self):
		position = self.position
		length = self.length
		return None if position is None or length is None or length <= 0 else position * 10000 // length

	value = property(getValue)
