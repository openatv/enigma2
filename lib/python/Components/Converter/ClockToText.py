from Converter import Converter
from time import localtime, strftime
from Components.Element import cached
from Components.config import config


class ClockToText(Converter, object):
	TIME_OPTIONS = {
		# 		TRANSLATORS: short time representation hour:minute (Same as "Default")
		"": lambda t: strftime(config.usage.time.short.value, localtime(t)),  # _("%R")
		#
		"AsLength": lambda t: "" if t < 0 else "%d:%02d" % (t / 60, t % 60),
		"AsLengthHours": lambda t: "" if t < 0 else "%d:%02d" % (t / 3600, t / 60 % 60),
		"AsLengthSeconds": lambda t: "" if t < 0 else "%d:%02d:%02d" % (t / 3600, t / 60 % 60, t % 60),
		# 		TRANSLATORS: full date representation dayname daynum monthname year in strftime() format! See 'man strftime'
		"Date": lambda t: strftime(config.usage.date.dayfull.value, localtime(t)),  # _("%A %e %B %Y")
		# 		TRANSLATORS: short time representation hour:minute in strftime() format! See 'man strftime'
		"Default": lambda t: strftime(config.usage.time.short.value, localtime(t)),  # _("%R")
		# 		TRANSLATORS: short time representation hour:minute in strftime() format! See 'man strftime'
		"Display": lambda t: strftime(config.usage.time.display.value, localtime(t)),  # _("%R")
		# 		TRANSLATORS: short date representation daynum short monthname in strftime() format! See 'man strftime'
		"DisplayDate": lambda t: strftime(config.usage.date.display.value, localtime(t)),  # _("%e %b")
		# 		TRANSLATORS: short date representation daynum short monthname in strftime() format! See 'man strftime'
		"DisplayDayDate": lambda t: strftime(config.usage.date.displayday.value, localtime(t)),  # _("%a %e %b")
		# 		TRANSLATORS: short time representation hour:minute in strftime() format! See 'man strftime'
		"DisplayTime": lambda t: strftime(config.usage.time.display.value, localtime(t)),  # _("%R")
		# 		TRANSLATORS: long date representation short dayname daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"Full": lambda t: strftime(config.usage.date.dayshort.value + " " + config.usage.time.short.value, localtime(t)),  # _("%a %e %b %R")
		# 		TRANSLATORS: full date representations short dayname daynum monthname long year in strftime() format! See 'man strftime'
		"FullDate": lambda t: strftime(config.usage.date.shortdayfull.value, localtime(t)),  # _("%a %e %B %Y")
		#
		"InMinutes": lambda t: ngettext("%d Min", "%d Mins", (t / 60)) % (t / 60),
		# 		TRANSLATORS: long date representations dayname daynum monthname in strftime() format! See 'man strftime'
		"LongDate": lambda t: strftime(config.usage.date.dayshortfull.value, localtime(t)),  # _("%A %e %B")
		# 		TRANSLATORS: long date representation short dayname daynum short monthname year hour:minute in strftime() format! See 'man strftime'
		"LongFullDate": lambda t: strftime(config.usage.date.daylong.value + "  " + config.usage.time.short.value, localtime(t)),  # _("%a %e %b %Y  %R")
		# 		TRANSLATORS: mixed time representation hour:minute:seconds for 24 hour clock and hour:minute for 12 hour clocks
		"Mixed": lambda t: strftime(config.usage.time.mixed.value, localtime(t)),  # _("%T") or _("%-I:%M%p")
		# 		TRANSLATORS: short date representation short dayname daynum short monthname in strftime() format! See 'man strftime'
		"ShortDate": lambda t: strftime(config.usage.date.dayshort.value, localtime(t)),  # _("%a %e/%m")
		# 		TRANSLATORS: long date representation short dayname daynum short monthname year in strftime() format! See 'man strftime'
		"ShortFullDate": lambda t: strftime(config.usage.date.daylong.value, localtime(t)),  # _("%a %e %b %Y")
		#
		"Timestamp": lambda t: str(t),
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD": lambda t: strftime(config.usage.date.compact.value + config.usage.time.display.value, localtime(t)),  # _("%e%m%R")
		# 		TRANSLATORS: VFD08 hour:minute in strftime() format! See 'man strftime'
		"VFD08": lambda t: strftime(config.usage.time.display.value, localtime(t)),  # _("%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD11": lambda t: strftime(config.usage.date.compressed.value + config.usage.time.display.value, localtime(t)),  # _("%e%b%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD12": lambda t: strftime(config.usage.date.compact.value + config.usage.time.display.value, localtime(t)),  # _("%e%b%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD14": lambda t: strftime(config.usage.date.short.value + " " + config.usage.time.display.value, localtime(t)),  # _("%e/%b %R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD18": lambda t: strftime(config.usage.date.dayshort.value + " " + config.usage.time.display.value, localtime(t)),  # _("%a %e/%b %R")
		# 		TRANSLATORS: full time representation hour:minute:seconds
		"WithSeconds": lambda t: strftime(config.usage.time.long.value, localtime(t))  # _("%T")
	}

	# add: date, date as string, weekday, ...
	# (whatever you need!)

	def __init__(self, type):
		Converter.__init__(self, type)
		self.separator = " - "
		self.formats = []

		type = type.lstrip()
		if type[0:5] == "Parse":
			parse = type[5:6]
		else:
			# OpenViX used ";" as the only ClockToText token separator.  For legacy
			# support if the first token is "Format" skip the multiple parse character
			# processing.
			#
			# Otherwise, some builds use ";" as a separator, most use ",".  If "Parse"
			# is NOT used change "," to ";" and parse on ";".
			#
			parse = ";"
			if type[0:6] != "Format":
				type = type.replace(",", ";")

		args = [arg.lstrip() for arg in type.split(parse)]
		for arg in args:
			if arg[0:6] == "Format":
				self.formats.append(eval("lambda t: strftime(\"%s\", localtime(t))" % arg[7:]))
				continue
			if arg[0:7] == "NoSpace":
				# Eat old OpenVIX option as it doesn't make sense now.
				continue
			if arg[0:5] == "Parse":
				# Already processed.
				continue
			if arg[0:12] == "Proportional":
				# Eat old OpenVIX option as it doesn't make sense now.
				continue
			if arg[0:9] == "Separator":
				self.separator = arg[10:]
				continue
			self.formats.append(self.TIME_OPTIONS.get(arg, lambda t: "???"))
		if len(self.formats) == 0:
			self.formats.append(self.TIME_OPTIONS.get("Default", lambda t: "???"))

	@cached
	def getText(self):
		time = self.source.time
		if time is None:
			return ""

		if isinstance(time, tuple):
			entries = len(self.formats)
			index = 0
			results = []
			for t in time:
				if index < entries:
					results.append(self.formats[index](t))
				else:
					results.append(self.formats[-1](t))
				index += 1
			return self.separator.join(results)
		else:
			return self.formats[0](time)

	text = property(getText)
