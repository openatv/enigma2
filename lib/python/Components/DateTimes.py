from locale import AM_STR, PM_STR, nl_langinfo
from time import localtime, strftime

from skin import onReload as skinOnReload, parameters
from Components.config import ConfigBoolean, ConfigSelection, ConfigSubsection, ConfigText, NoSave, config


class DateTimes:
	LAYOUT = 0  # Default layout.  (Upper case used for clarity that these are class global indexes.)
	LEGACY = 1  # Default legacy date layout for skins without enabled date/time parameters.
	LEGACY_NO_YEAR = 2  # Default legacy date layout with no year for skins without enabled date/time parameters.
	DAY_SEPARATOR = 3  # Default day separator.
	DATE = 4  # Default date format.
	MONTH = 5  # Default month format.
	FIRST_SEPARATOR = 6  # Default first separator.
	SECOND_SEPARATOR = 7  # Default second separator.
	SUFFIX = 8  # Default date suffix.
	DEFAULTS = {
		"de_DE": ("%A+%d=%m#%Y", "%d.%m.%Y", "%d.%m", ", ", "%d", "%m", ".", ".", ""),
		"en_AU": ("%A+%d=%m#%Y", "%d/%m/%Y", "%d/%m", ", ", "%d", "%B", "-", "-", ""),
		"en_GB": ("%A+%d=%m#%Y", "%d/%m/%Y", "%d/%m", ", ", "%d", "%B", "-", "-", ""),
	}
	DEFAULTS_US = ("%A+%m=%d#%Y", "%m/%d/%Y", "%m/%d", " ", "%-d", "%m", "/", "/", "")

	def initConfig(self):
		defaults = self.DEFAULTS.get(config.misc.locale.value, self.DEFAULTS_US)
		config.usage.date = ConfigSubsection()
		date = config.usage.date
		date.enabled = NoSave(ConfigBoolean(default=False))
		date.layout = ConfigSelection(default=defaults[self.LAYOUT], choices=[
			("%A+%d=%m#%Y", _("Day Date Month Year")),
			("%A+%m=%d#%Y", _("Day Month Date Year")),
			("%A+%Y=%m#%d", _("Day Year Month Date"))
		])
		date.dayFormat = ConfigSelection(default="%A", choices=[
			("", _("No day name")),
			("%a", _("Abbreviated day name")),
			("%A", _("Full day name"))
		])
		date.dateFormat = ConfigSelection(default=defaults[self.DATE], choices=[
			("%-d", _("One digit")),
			("%e", _("One digit, space padded")),
			("%d", _("Two digits"))
		])
		date.monthFormat = ConfigSelection(default=defaults[self.MONTH], choices=[
			("%-m", _("One digit")),
			("%m", _("Two digits")),
			("%b", _("Abbreviated month name")),
			("%B", _("Full month name"))
		])
		choices = [
			(" ", _("Space ' '")),
			("-", _("Hyphen '-'")),
			(".", _("Period '.'")),
			(". ", _("Period and space '. '")),
			(",", _("Comma ','")),
			(", ", _("Comma and space ', '")),
			(":", _("Colon ':'")),
			(";", _("Semicolon ';'")),
			("/", _("Forward slash '/'"))
		]
		date.daySeparator = ConfigSelection(default=defaults[self.DAY_SEPARATOR], choices=choices)
		date.firstSeparator = ConfigSelection(default=defaults[self.FIRST_SEPARATOR], choices=choices)
		date.secondSeparator = ConfigSelection(default=defaults[self.SECOND_SEPARATOR], choices=choices)
		date.suffix = ConfigSelection(default=defaults[self.SUFFIX], choices=[
			("", _("None")),
			(".", _("Period '.'")),
			(",", _("Comma ','"))
		])
		date.timeSeparator = ConfigSelection(default="  ", choices=[
			(" ", _("One space ' '")),
			("  ", _("Two spaces '  '")),
			(" - ", _("Space Hyphen Space ' - '"))
		])
		#
		config.usage.time = ConfigSubsection()
		time = config.usage.time
		time.enabled = NoSave(ConfigBoolean(default=False))
		time.layout = ConfigText(default="%H=%M=%S%P")
		time.hourFormat = ConfigSelection(default="%H", choices=[
			("%-H", _("One digit (24 hour time)")),
			("%k", _("One digit, space padded (24 hour time)")),
			("%H", _("Two digits (24 hour time)")),
			("%-I", _("One digit (12 hour time)")),
			("%l", _("One digit, space padded (12 hour time)")),
			("%I", _("Two digits (12 hour time)"))
		])
		choices = [("", _("No AM/PM display"))]
		if nl_langinfo(AM_STR) and nl_langinfo(PM_STR):
			choices.extend((
				("%P", _("am/pm display")),
				("%^p", _("AM/PM display"))
			))
		time.meridiemFormat = ConfigSelection(default="", choices=choices)
		time.meridiemActive = NoSave(ConfigText(default=""))
		time.secondsFormat = ConfigSelection(default="=%S", choices=[
			("", _("No")),
			("=%S", _("Yes"))
		])
		time.separator = ConfigSelection(default=":", choices=[
			("-", _("Hyphen '-'")),
			(".", _("Period '.'")),
			(":", _("Colon ':'")),
			(";", _("Semicolon ';'")),
			("/", _("Forward slash '/'"))
		])
		self.updateDatesAndTimes(init=True)
		if self.updateDatesAndTimes not in skinOnReload:
			skinOnReload.append(self.updateDatesAndTimes)

	def updateDatesAndTimes(self, init=False):
		try:
			dateEnabled, timeEnabled = parameters.get("AllowUserDatesAndTimes", (0, 0))
		except Exception as error:
			print(f"[DateTimes] Error loading 'AllowUserDatesAndTimes' skin parameter!  ({error})")
			dateEnabled, timeEnabled = (0, 0)
		dateEnabled = bool(dateEnabled)
		timeEnabled = bool(timeEnabled)
		date = config.usage.date
		date.enabled.value = dateEnabled
		if dateEnabled:
			daySeparator = "" if date.dayFormat.value == "" else date.daySeparator.value
			self.date = date.layout.value.replace("%A", date.dayFormat.value).replace("+", daySeparator).replace("%d", date.dateFormat.value).replace("%m", date.monthFormat.value).replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			if suffix := date.suffix.value:
				self.date = f"{self.date}{suffix}"
			self.dateNoDay = date.layout.value.replace("%A+", "").replace("%d", date.dateFormat.value).replace("%m", date.monthFormat.value).replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateNoDayNoYear = date.layout.value.replace("%A+", "").replace("%d", date.dateFormat.value).replace("%m", date.monthFormat.value).replace("#%Y", "").replace("%Y=", "").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateNoDayShortMonth = date.layout.value.replace("%A+", "").replace("%d", date.dateFormat.value).replace("%m", "%b").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateNoDayShortMonthNoYear = date.layout.value.replace("%A+", "").replace("%d", date.dateFormat.value).replace("%m", "%b").replace("#%Y", "").replace("%Y=", "").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateNoYear = date.layout.value.replace("%A", date.dayFormat.value).replace("+", daySeparator).replace("%d", date.dateFormat.value).replace("%m", date.monthFormat.value).replace("#%Y", "").replace("%Y=", "").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateShortDay = date.layout.value.replace("%A", "%a").replace("+", date.daySeparator.value).replace("%d", date.dateFormat.value).replace("%m", date.monthFormat.value).replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateShortDayNoMonthNoYear = f"%a{config.usage.date.daySeparator.value}{config.usage.date.dateFormat.value}"
			self.dateShortDayShortMonth = date.layout.value.replace("%A", "%a").replace("+", date.daySeparator.value).replace("%d", date.dateFormat.value).replace("%m", "%b").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			self.dateShortDayShortMonthNoYear = date.layout.value.replace("%A", "%a").replace("+", date.daySeparator.value).replace("%d", date.dateFormat.value).replace("%m", "%b").replace("#%Y", "").replace("%Y=", "").replace("=", date.firstSeparator.value).replace("#", date.secondSeparator.value)
			timeSeparator = date.timeSeparator.value
		else:
			defaults = self.DEFAULTS.get(config.misc.locale.value, self.DEFAULTS_US)
			self.date = defaults[self.LEGACY]
			self.dateNoDay = self.date
			self.dateNoDayNoYear = defaults[self.LEGACY_NO_YEAR]
			self.dateNoDayShortMonth = self.date
			self.dateNoDayShortMonthNoYear = self.dateNoDayNoYear
			self.dateNoYear = defaults[self.LEGACY_NO_YEAR]
			self.dateShortDay = self.date
			self.dateShortDayNoMonthNoYear = "%a %d"
			self.dateShortDayShortMonth = self.date
			self.dateShortDayShortMonthNoYear = self.dateNoYear
			timeSeparator = "  "
		time = config.usage.time
		time.enabled.value = timeEnabled
		if timeEnabled:
			time.meridiemActive.value = time.meridiemFormat.value if "H" not in time.hourFormat.value and "k" not in time.hourFormat.value else ""
			self.time = time.layout.value.replace("%H", time.hourFormat.value).replace("=%S", time.secondsFormat.value).replace("%P", time.meridiemActive.value).replace("=", time.separator.value)
			self.timeNoMeridiem = time.layout.value.replace("%H", time.hourFormat.value).replace("=%S", time.secondsFormat.value).replace("%P", "").replace("=", time.separator.value)
			self.timeShort = time.layout.value.replace("%H", time.hourFormat.value).replace("=%S", "").replace("%P", time.meridiemActive.value).replace("=", time.separator.value)
			self.timeShortNoMeridiem = time.layout.value.replace("%H", time.hourFormat.value).replace("=%S", "").replace("%P", "").replace("=", time.separator.value)
			self.timeMixed = self.timeShort if time.meridiemActive.value else self.time
		else:
			time.meridiemActive.value = ""
			time.meridiemActive.default = time.meridiemActive.value
			self.time = "%H:%M:%S"
			self.timeNoMeridiem = self.time
			self.timeShort = "%H:%M"
			self.timeShortNoMeridiem = self.timeShort
			self.timeMixed = self.time
		self.dateTime = f"{self.date}{timeSeparator}{self.time}"
		self.dateTimeShortDayShortMonthNoSeconds = f"{self.dateShortDayShortMonth} {self.timeShort}"
		self.dateTimeShortDayShortMonthNoYearNoSeconds = f"{self.dateShortDayShortMonthNoYear} {self.timeShort}"
		configItems = (
			(date, "date", self.date),
			(date, "noDay", self.dateNoDay),
			(date, "noDayNoYear", self.dateNoDayNoYear),
			(date, "noDayShortMonth", self.dateNoDayShortMonth),
			(date, "noDayShortMonthNoYear", self.dateNoDayShortMonthNoYear),
			(date, "noYear", self.dateNoYear),
			(date, "shortDay", self.dateShortDay),
			(date, "shortDayNoMonthNoYear", self.dateShortDayNoMonthNoYear),
			(date, "shortDayShortMonth", self.dateShortDayShortMonth),
			(date, "shortDayShortMonthNoYear", self.dateShortDayShortMonthNoYear),
			(time, "time", self.time),
			(time, "noMeridiem", self.timeNoMeridiem),
			(time, "short", self.timeShort),
			(time, "shortNoMeridiem", self.timeShortNoMeridiem),
			(time, "mixed", self.timeMixed),
			(time, "wide", bool(time.meridiemActive.value)),
			# These are legacy items retained for code functionality.
			(date, "dayfull", self.date),
			(date, "daylong", self.dateShortDayShortMonth),
			(date, "dayshort", self.dateShortDayShortMonthNoYear),
			(date, "full", self.dateNoDay),
			(date, "long", self.dateNoDayShortMonth),
			(date, "short", self.dateNoDayShortMonthNoYear),
			(time, "long", self.dateTime)
		)
		for key, attribute, value in configItems:
			if init:
				setattr(key, attribute, NoSave(ConfigBoolean(default=value)) if attribute == "wide" else NoSave(ConfigText(default=value)))
				getattr(key, attribute).value = value
			else:
				getattr(key, attribute).value = value
				getattr(key, attribute).default = value

	# This is a convenience to allow the DateTime to get the on screen configuration items
	# from here.  (It is assumed that this list will be maintained with any changes make to
	# the configuration items defined above!)
	#
	def getConfigElements(self):
		date = config.usage.date
		time = config.usage.time
		return (
			date.layout,
			date.dayFormat,
			date.dateFormat,
			date.monthFormat,
			date.daySeparator,
			date.firstSeparator,
			date.secondSeparator,
			date.suffix,
			date.timeSeparator,
			time.layout,
			time.hourFormat,
			time.meridiemFormat,
			time.secondsFormat,
			time.separator
		)
		
	def getDate(self, timestamp=None, forceNumeric=False, dataFormat=None):  # Day Date Month Year; Day and month names in full words.
		if timestamp is None:
			timestamp = localtime()
		if dataFormat is None:
			dataFormat = self.date
		if forceNumeric:
			replacement = "%-m" if config.usage.date.layout.value == "%A+%m=%d#%Y" else "%m"
			dataFormat = dataFormat.replace("%B", replacement).replace("%b", replacement)
		return strftime(dataFormat, timestamp)

	def getDateNoDay(self, timestamp=None, forceNumeric=False):  # Date Month Year; No day, month name in full word.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateNoDay)

	def getDateNoDayNoYear(self, timestamp=None, forceNumeric=False):  # Date Month; No day, month name in full words and no year.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateNoDayNoYear)

	def getDateNoDayShortMonth(self, timestamp=None, forceNumeric=False):  # Date Mon Year; No day, month name in short word.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateNoDayShortMonth)

	def getDateNoDayShortMonthNoYear(self, timestamp=None, forceNumeric=False):  #  Date Mon; No day, month name in short word and no year.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateNoDayShortMonthNoYear)

	def getDateNoYear(self, timestamp=None, forceNumeric=False):  # Day Date Month; Day and month names in full words and no year.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateNoYear)

	def getDateShortDay(self, timestamp=None, forceNumeric=False):  # Day Date Month Year; Day name in short word and month name full word.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateShortDay)

	def getDateShortDayNoMonthNoYear(self, timestamp=None):  # Day Date; Day name in short word and no month or year.
		return self.getDate(timestamp=timestamp, dataFormat=self.dateShortDayNoMonthNoYear)

	def getDateShortDayShortMonth(self, timestamp=None, forceNumeric=False):  # Day Date Mon Year; Day and month names in short words.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateShortDayShortMonth)

	def getDateShortDayShortMonthNoYear(self, timestamp=None, forceNumeric=False):  # Day Date Mon; Day and month names in short words and no year.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateShortDayShortMonthNoYear)

	def getDateTime(self, timestamp=None, forceNumeric=False):  # Day Date Month Year Hours Minutes Seconds Meridiem; Day and month names in full words with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateTime)

	def getDateTimeShortDayShortMonthNoSeconds(self, timestamp=None, forceNumeric=False):  # Day Date Mon Year Hours Minutes Meridiem; Day and month names in short words with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateTimeShortDayShortMonthNoSeconds)

	def getDateTimeShortDayShortMonthNoYearNoSeconds(self, timestamp=None, forceNumeric=False):  # Day Date Mon Hours Minutes Meridiem; Day and month names in short words and no year with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.dateTimeShortDayShortMonthNoYearNoSeconds)

	def getTime(self, timestamp=None, dataFormat=None):  # Hours Minutes Seconds Meridiem; Time in hours, minutes, seconds and meridiem (AM/PM).
		if timestamp is None:
			timestamp = localtime()
		if dataFormat is None:
			dataFormat = self.time
		return strftime(dataFormat, timestamp)

	def getTimeMixed(self, timestamp=None):  # Hours Minutes Seconds / Hours Minutes Meridiem; Time in hours, minutes and seconds for 24 hour clocks; hours, minutes and meridiem (AM/PM) for 12 hour clocks.
		return self.getTime(timestamp=timestamp, dataFormat=self.timeMixed)

	def getTimeNoMeridiem(self, timestamp=None):  # Hours Minutes Seconds; Time in hours, minutes, seconds and no meridiem (AM/PM) for a 12 hour clock.
		return self.getTime(timestamp=timestamp, dataFormat=self.timeNoMeridiem)

	def getTimeShort(self, timestamp=None):  # Hours Minutes Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getTime(timestamp=timestamp, dataFormat=self.timeShort)

	def getTimeShortNoMeridiem(self, timestamp=None):  # Hours Minutes; Time in hours, minutes and no meridiem (AM/PM) for a 12 hour clock.
		return self.getTime(timestamp=timestamp, dataFormat=self.timeShortNoMeridiem)

	def getVfdDisplay08(self, timestamp=None, forceNumeric=True):  # Hours Minutes Seconds Meridiem; Time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=self.timeShort)[:8]

	def getVfdDisplay12(self, timestamp=None, forceNumeric=True):  # Hours Minutes Meridiem; No day, month in digits with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=f"{self.dateNoDayShortMonthNoYear} {self.timeShort}")[:12]

	def getVfdDisplay14(self, timestamp=None, forceNumeric=True):  # Hours Minutes Meridiem; No day, month in digits with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=f"{self.dateNoDayShortMonthNoYear} {self.timeShort}")[:14]

	def getVfdDisplay18(self, timestamp=None, forceNumeric=True):  # Day Date Mon Year Hours Minutes Meridiem; Day name in short, month in digits with time in hours, minutes and meridiem (AM/PM) for a 12 hour clock.
		return self.getDate(timestamp=timestamp, forceNumeric=forceNumeric, dataFormat=f"{self.dateShortDayShortMonthNoYear} {self.timeShort}")[:18]


dateTimes = DateTimes()
