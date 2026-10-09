from time import localtime, strftime
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config


class ClockToText(Converter):
	TIME_OPTIONS = {
		# 		TRANSLATORS: short time representation hour:minute (Same as "Default")
		"": lambda t: strftime(config.usage.time.short.value, localtime(t)),  # _("%R")
		#
		"AsLength": lambda t: "" if t < 0 else f"{int(t // 60)}:{int(t % 60):02d}",
		"AsLengthHours": lambda t: "" if t < 0 else f"{int(t // 3600)}:{int(t // 60 % 60):02d}",
		"AsLengthSeconds": lambda t: "" if t < 0 else f"{int(t // 3600)}:{int(t // 60 % 60):02d}:{int(t % 60):02d}",
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
		"Full": lambda t: strftime(f"{config.usage.date.dayshort.value} {config.usage.time.short.value}", localtime(t)),  # _("%a %e %b %R")
		# 		TRANSLATORS: full date representations short dayname daynum monthname long year in strftime() format! See 'man strftime'
		"FullDate": lambda t: strftime(config.usage.date.shortdayfull.value, localtime(t)),  # _("%a %e %B %Y")
		#
		"InMinutes": lambda t: ngettext("%d Min", "%d Mins", (t // 60)) % (t // 60),
		# 		TRANSLATORS: long date representations dayname daynum monthname in strftime() format! See 'man strftime'
		"LongDate": lambda t: strftime(config.usage.date.dayshortfull.value, localtime(t)),  # _("%A %e %B")
		# 		TRANSLATORS: long date representation short dayname daynum short monthname year hour:minute in strftime() format! See 'man strftime'
		"LongFullDate": lambda t: strftime(f"{config.usage.date.daylong.value}  {config.usage.time.short.value}", localtime(t)),  # _("%a %e %b %Y  %R")
		# 		TRANSLATORS: mixed time representation hour:minute:seconds for 24 hour clock and hour:minute for 12 hour clocks
		"Mixed": lambda t: strftime(config.usage.time.mixed.value, localtime(t)),  # _("%T") or _("%-I:%M%p")
		# 		TRANSLATORS: short date representation short dayname daynum short monthname in strftime() format! See 'man strftime'
		"ShortDate": lambda t: strftime(config.usage.date.dayshort.value, localtime(t)),  # _("%a %e/%m")
		# 		TRANSLATORS: long date representation short dayname daynum short monthname year in strftime() format! See 'man strftime'
		"ShortFullDate": lambda t: strftime(config.usage.date.daylong.value, localtime(t)),  # _("%a %e %b %Y")
		#
		"Timestamp": lambda t: str(t),
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD": lambda t: strftime(f"{config.usage.date.compact.value}{config.usage.time.display.value}", localtime(t)),  # _("%e%m%R")
		# 		TRANSLATORS: VFD08 hour:minute in strftime() format! See 'man strftime'
		"VFD08": lambda t: strftime(config.usage.time.display.value, localtime(t)),  # _("%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD11": lambda t: strftime(f"{config.usage.date.compressed.value}{config.usage.time.display.value}", localtime(t)),  # _("%e%b%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD12": lambda t: strftime(f"{config.usage.date.compact.value}{config.usage.time.display.value}", localtime(t)),  # _("%e%b%R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD14": lambda t: strftime(f"{config.usage.date.short.value} {config.usage.time.display.value}", localtime(t)),  # _("%e/%b %R")
		# 		TRANSLATORS: VFD daynum short monthname hour:minute in strftime() format! See 'man strftime'
		"VFD18": lambda t: strftime(f"{config.usage.date.dayshort.value} {config.usage.time.display.value}", localtime(t)),  # _("%a %e/%b %R")
		# 		TRANSLATORS: full time representation hour:minute:seconds
		"WithSeconds": lambda t: strftime(config.usage.time.long.value, localtime(t))  # _("%T")
	}

	# Add: date, date as string, weekday, ...
	# (whatever you need!)

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
				self.formats.append(eval(f"lambda t: strftime(\"{arg[7:]}\", localtime(t))"))
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
