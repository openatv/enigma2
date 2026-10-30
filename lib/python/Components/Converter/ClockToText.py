from time import localtime, strftime

from Components.DateTimes import dateTimes
from Components.Element import cached
from Components.Converter.Converter import Converter


class ClockToText(Converter):
	TIME_OPTIONS = {
		"": lambda t: dateTimes.getTimeShort(localtime(t)),  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		"AsLength": lambda t: "" if t < 0 else f"{int(t // 60)}:{int(t % 60):02d}",
		"AsLengthHours": lambda t: "" if t < 0 else f"{int(t // 3600)}:{int(t // 60 % 60):02d}",
		"AsLengthSeconds": lambda t: "" if t < 0 else f"{int(t // 3600)}:{int(t // 60 % 60):02d}:{int(t % 60):02d}",
		"Date": lambda t: dateTimes.getDate(localtime(t)),  # Day Date Month Year; Day and month names in full words.
		"DateNoDay": lambda t: dateTimes.getDateNoDay(localtime(t)),  # Date Month Year; No day and month name in full word.
		"DateNoDayNoYear": lambda t: dateTimes.getDateNoDayNoYear(localtime(t)),  # Date Month; No day, month name in full word and no year.
		"DateNoDayShortMonth": lambda t: dateTimes.getDateNoDayShortMonth(localtime(t)),  # Date Mon Year; No day and month name in short word.
		"DateNoDayShortMonthNoYear": lambda t: dateTimes.getDateNoDayShortMonthNoYear(localtime(t)),  #  Date Mon; No day, month name in short word and no year.
		"DateNoYear": lambda t: dateTimes.getDateNoYear(localtime(t)),  # Day Date Month; Day and month names in full words and no year.
		"DateShortDay": lambda t: dateTimes.getDateShortDay(localtime(t)),  # Day Date Month Year; Day name in short word and month name full word.
		"DateShortDayNoMonthNoYear": lambda t: dateTimes.getDateShortDayNoMonthNoYear(localtime(t)),  # Day Date; Day name in short word and no month or year.
		"DateShortDayShortMonth": lambda t: dateTimes.getDateShortDayShortMonth(localtime(t)),  # Day Date Mon Year; Day and month names in short words.
		"DateShortDayShortMonthNoYear": lambda t: dateTimes.getDateShortDayShortMonthNoYear(localtime(t)),  # Day Date Mon; Day and month names in short words and no year.
		"DateTime": lambda t: dateTimes.getDateTime(localtime(t)),  # "Date" followed by the date/time separator then "Time".
		"Default": lambda t: dateTimes.getTimeShort(localtime(t)),  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		"Display": lambda t: dateTimes.getTimeShort(localtime(t)),  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		"DisplayDate": lambda t: dateTimes.getDateNoDayShortMonthNoYear(localtime(t)),  #  Date Mon; No day, month name in short word and no year.
		"DisplayDayDate": lambda t: dateTimes.getDateShortDayShortMonthNoYear(localtime(t)),  #  Day Date Mon; Day and month names in short words and no year.
		"DisplayTime": lambda t: dateTimes.getTimeShort(localtime(t)),  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM).
		"Full": lambda t: dateTimes.getDateTimeShortDayShortMonthNoYear(localtime(t)),  # Short day and month, no year, followed by hours and minutes.
		"FullDate": lambda t: dateTimes.getDateShortDay(localtime(t)),  # Day Date Month Year; Day name in short word and month name full word.
		"InMinutes": lambda t: ngettext("%d Min", "%d Mins", (t // 60)) % (t // 60),
		"LongDate": lambda t: dateTimes.getDateNoYear(localtime(t)),  # Day Date Month; Day and month names in full words.
		"LongFullDate": lambda t: dateTimes.getDateTimeShortDayShortMonthNoSeconds(localtime(t)),  # Day Date Mon Year Hours Minutes Meridiem; Day and month names in short words and time with no seconds and meridiem (AM/PM) for 12 hour clocks.
		"Mixed": lambda t: dateTimes.getTimeMixed(localtime(t)),  # Hours Minutes Seconds / Hours Minutes Meridiem; Time in hours, minutes and seconds for 24 hour clocks; hours, minutes and meridiem (AM/PM) for 12 hour clocks.
		"ShortDate": lambda t: dateTimes.getDateShortDayShortMonthNoYear(localtime(t)),  #  Date Mon; Month name in short word and no day or year.
		"ShortFullDate": lambda t: dateTimes.getDateShortDayShortMonth(localtime(t)),  # Day Date Mon Year; Day and month names in short words.
		"Time": lambda t: dateTimes.getTime(localtime(t)),  # Hours Minutes Seconds Meridiem; Time in hours, minutes, seconds and meridiem (AM/PM).
		"TimeLong": lambda t: dateTimes.getTime(localtime(t)),  # Hours Minutes Seconds Meridiem; Time in hours, minutes, seconds and meridiem (AM/PM).
		"TimeMixed": lambda t: dateTimes.getTimeMixed(localtime(t)),  # Hours Minutes Seconds / Hours Minutes Meridiem; Time in hours, minutes and seconds for 24 hour clocks; hours, minutes and meridiem (AM/PM) for 12 hour clocks.
		"TimeNoMeridiem": lambda t: dateTimes.getTimeNoMeridiem(localtime(t)),  # Hours Minutes Seconds; Time in hours, minutes, seconds and no meridiem (AM/PM).
		"TimeShort": lambda t: dateTimes.getTimeShort(localtime(t)),  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		"TimeShortNoMeridiem": lambda t: dateTimes.getTimeShortNoMeridiem(localtime(t)),  # Hours Minutes; Time in hours, minutes and no meridiem (AM/PM) for a 12 hour clock.
		"Timestamp": lambda t: str(t),
		"VFD": lambda t: dateTimes.getVfdDisplay12(localtime(t)),  # Same as "VFD12".
		"VFD08": lambda t: dateTimes.getVfdDisplay08(localtime(t)),  # Hours Minutes Seconds Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		"VFD12": lambda t: dateTimes.getVfdDisplay12(localtime(t)),  # Date Month Hours Minutes Meridiem; Date, month in digits with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock trimmed to 12 characters (meridiem is dropped if it does not fit).
		"VFD14": lambda t: dateTimes.getVfdDisplay14(localtime(t)),  # Date and time in 14 characters, dropping the whole meridiem if needed.
		"VFD18": lambda t: dateTimes.getVfdDisplay18(localtime(t)),  # Short day, date and time in 18 characters, dropping the whole meridiem if needed.
		"WithSeconds": lambda t: dateTimes.getTimeWithSeconds(localtime(t))  # Explicit seconds, independent of the optional seconds setting.
	}

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.separator = " - "
		self.formats = []
		tokens = tokens.lstrip()
		if tokens.startswith("Parse"):
			parse = tokens[5:6]
		else:
			# OpenViX used ";" as the only ClockToText token separator. For legacy support skip the
			# multiple parse character processing if the first token is "Format". Otherwise, some
			# builds use ";" as a separator, most use ",". If "Parse" is NOT used change "," to ";".
			parse = ";"
			if not tokens.startswith("Format"):
				tokens = tokens.replace(",", ";")
		for arg in [x.lstrip() for x in tokens.split(parse)]:
			if arg.startswith("Format"):
				self.formats.append(lambda t, dateFormat=arg[7:]: strftime(dateFormat, localtime(t)))
			elif arg.startswith("Separator"):
				self.separator = arg[10:]
			elif not arg.startswith(("NoSpace", "Parse", "Proportional")):  # Ignore old OpenViX options and the already processed "Parse".
				self.formats.append(self.TIME_OPTIONS.get(arg, lambda t: "???"))
		if not self.formats:
			self.formats.append(self.TIME_OPTIONS.get("Default", lambda t: "???"))

	@cached
	def getText(self):
		text = ""
		sourceTime = self.source.time
		if sourceTime is not None:
			if isinstance(sourceTime, tuple):
				text = self.separator.join(self.formats[min(index, len(self.formats) - 1)](x) for index, x in enumerate(sourceTime))
			else:
				text = self.formats[0](sourceTime)
		return text

	text = property(getText)
