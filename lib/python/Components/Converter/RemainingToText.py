from time import localtime, strftime

from Components.config import config
from Components.Element import cached
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll


class RemainingToText(Converter, Poll):
	DEFAULT = 0
	IN_SECONDS = 1
	IN_SECONDS_VFD = 7
	NO_SECONDS = 2
	NO_SECONDS_VFD = 8
	ONLY_MINUTE = 3
	ONLY_MINUTE2 = 4
	PERCENTAGE = 5
	PERCENTAGE_VFD = 9
	VFD = 6
	WITH_SECONDS = 11
	WITH_SECONDS_VFD = 10

	def __init__(self, token):
		Converter.__init__(self, token)
		Poll.__init__(self)
		self.token, self.poll_interval = {
			"Default": (self.DEFAULT, 0),
			"InSeconds": (self.IN_SECONDS, 1000),
			"NoSeconds": (self.NO_SECONDS, 1000),
			"OnlyMinute": (self.ONLY_MINUTE, 0),
			"OnlyMinute2": (self.ONLY_MINUTE2, 0),
			"Percentage": (self.PERCENTAGE, 60000),
			"VFD": (self.VFD, 0),
			"VFDInSeconds": (self.IN_SECONDS_VFD, 1000),
			"VFDNoSeconds": (self.NO_SECONDS_VFD, 60000),
			"VFDPercentage": (self.PERCENTAGE_VFD, 60000),
			"VFDWithSeconds": (self.WITH_SECONDS_VFD, 1000),
			"WithSeconds": (self.WITH_SECONDS, 1000)
		}.get(token, (None, 0))
		if token and self.token is None:
			print(f"[RemainingToText] Error: Converter argument '{token}' is invalid!")
		if self.token is None:
			self.token = self.DEFAULT
		if config.usage.swap_time_display_on_osd.value in ("1", "3", "5") or config.usage.swap_time_display_on_vfd.value in ("1", "3", "5"):
			self.poll_interval = 60000
		elif config.usage.swap_time_display_on_osd.value in ("2", "4") or config.usage.swap_time_display_on_vfd.value in ("2", "4"):
			self.poll_interval = 1000
		if self.poll_interval:
			self.poll_enabled = True
		# self.tokenText = token  # DEBUG: This is only for testing purposes.

	@cached
	def getText(self):
		result = ""
		sourceTime = self.source.time
		if sourceTime:
			duration = 0
			elapsed = 0
			remaining = 0
			# print(f"[RemainingToText] DEBUG: sourceTime={sourceTime}.")
			if str(sourceTime[1]) != "None":
				if self.token in (self.DEFAULT, self.WITH_SECONDS, self.NO_SECONDS, self.IN_SECONDS, self.PERCENTAGE, self.ONLY_MINUTE, self.ONLY_MINUTE2):
					match config.usage.swap_time_remaining_on_osd.value:
						case "0":
							duration, remaining = sourceTime
						case "1":
							duration, elapsed = sourceTime
						case "2":
							duration, elapsed, remaining = sourceTime
						case "3":
							duration, remaining, elapsed = sourceTime
				else:
					match config.usage.swap_time_remaining_on_vfd.value:
						case "0":
							duration, remaining = sourceTime
						case "1":
							duration, elapsed = sourceTime
						case "2":
							duration, elapsed, remaining = sourceTime
						case "3":
							duration, remaining, elapsed = sourceTime
			else:
				duration, remaining = sourceTime
			signDuration = ""
			if self.token in (self.DEFAULT, self.WITH_SECONDS, self.NO_SECONDS, self.IN_SECONDS, self.PERCENTAGE, self.ONLY_MINUTE, self.ONLY_MINUTE2):
				if config.usage.elapsed_time_positive_osd.value:
					signElapsed = "+"
					signRemaining = "-"
				else:
					signElapsed = "-"
					signRemaining = "+"
				match config.usage.swap_time_display_on_osd.value:
					case "1":
						if remaining is None:
							result = ngettext("%d Min", "%d Mins", (duration // 60)) % (duration // 60)
						else:
							result = {
								# "1": f"{signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
								"1": f"{signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
								# "2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
								"2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
								# "3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
								"3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}")
							# }.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}")
					case "2":
						if remaining is None:
							result = f"{duration // 60}:{duration % 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 60}:{elapsed % 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 60}:{elapsed % 60:02d}  {signRemaining}{remaining // 60}:{remaining % 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 60}:{remaining % 60:02d}  {signElapsed}{elapsed // 60}:{elapsed % 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 60}:{remaining % 60:02d}")
					case "3":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}")
					case "4":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}")
					case "5":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
						else:
							try:
								result = {
									"1": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%",  # Elapsed
									"2": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%  {signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%",  # Elapsed & Remaining
									"3": f"{signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%  {signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%"  # Remaining & Elapsed
								}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{int((float(elapsed) / float(duration)) * 100.0)}%")
							except ZeroDivisionError:
								pass
					case _:
						match self.token:
							case self.DEFAULT:
								if remaining is None:
									result = ngettext("%d Min", "%d Mins", (duration // 60)) % (duration // 60)
								else:
									result = {
										# "1": f"{signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
										"1": f"{signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
										# "2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
										"2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
										# "3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
										"3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}")
									# }.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}")
							case self.IN_SECONDS:
								if remaining is None:
									result = ngettext("%d Min", "%d Mins", (duration // 60)) % (duration // 60)
								else:
									result = {
										"1": f"{signElapsed}{elapsed} ",  # Elapsed
										"2": f"{signElapsed}{elapsed}  {signRemaining}{remaining} ",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining}  {signElapsed}{elapsed} "  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining} ")
							case self.NO_SECONDS:
								if remaining is None:
									result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}"
								else:
									result = {
										"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}",  # Elapsed
										"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}")
							case self.ONLY_MINUTE:
								if remaining is not None:
									result = f"{remaining // 60}"
							case self.ONLY_MINUTE2:
								now = localtime()
								timeFormat = _("%-H:%M")
								if remaining is None:
									result = strftime(timeFormat, now)
								else:
									value = f"{(remaining // 60) if config.usage.elapsed_time_positive_vfd.value else (remaining // 60 * -1):+6d}"
									if (remaining // 60) == 0:
										value = " "
									result = f"{strftime(timeFormat, now)}{value}"
							case self.PERCENTAGE:
								try:
									result = {
										"1": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%",  # Elapsed
										"2": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%  {signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%",  # Elapsed & Remaining
										"3": f"{signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%  {signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{int((float(elapsed) / float(duration)) * 100.0)}%")
								except ZeroDivisionError:
									pass
							case self.WITH_SECONDS:
								if remaining is None:
									result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
								else:
									result = {
										"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",  # Elapsed
										"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}")
							case _:
								result = f"{signDuration}{duration}"
			else:
				if config.usage.elapsed_time_positive_vfd.value:
					signElapsed = "+"
					signRemaining = "-"
				else:
					signElapsed = "-"
					signRemaining = "+"
				match config.usage.swap_time_display_on_vfd.value:
					case "1":
						if remaining is None:
							result = ngettext("%d Min", "%d Mins", (duration // 60)) % (duration // 60)
						else:
							result = {
								# "1": f"{signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
								"1": f"{signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
								# "2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
								"2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
								# "3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
								"3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}")
							# }.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}")
					case "2":
						if remaining is None:
							result = f"{duration // 60}:{duration % 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 60}:{elapsed % 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 60}:{elapsed % 60:02d}  {signRemaining}{remaining // 60}:{remaining % 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 60}:{remaining % 60:02d}  {signElapsed}{elapsed // 60}:{elapsed % 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{remaining // 60}:{remaining % 60:02d}")
					case "3":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}")
					case "4":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
						else:
							result = {
								"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",  # Elapsed
								"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}",  # Elapsed & Remaining
								"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}"  # Remaining & Elapsed
							}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}")
					case "5":
						if remaining is None:
							result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
						else:
							try:
								result = {
									"1": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%",  # Elapsed
									"2": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%  {signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%",  # Elapsed & Remaining
									"3": f"{signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%  {signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%"  # Remaining & Elapsed
								}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{int((float(elapsed) / float(duration)) * 100.0)}%")
							except ZeroDivisionError:
								pass
					case _:
						match self.token:
							case self.IN_SECONDS_VFD:
								if remaining is None:
									result = ngettext("%d Min", "%d Mins", duration) % duration
								else:
									result = {
										"1": f"{signElapsed}{elapsed} ",  # Elapsed
										"2": f"{signElapsed}{elapsed}  {signRemaining}{remaining} ",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining}  {signElapsed}{elapsed} "  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{remaining} ")
							case self.NO_SECONDS_VFD:
								if remaining is None:
									result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}"
								else:
									result = {
										"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}",  # Elapsed
										"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}")
							case self.PERCENTAGE_VFD:
								try:
									result = {
										"1": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%",  # Elapsed
										"2": f"{signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%  {signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%",  # Elapsed & Remaining
										"3": f"{signRemaining}{int((float(remaining) / float(duration)) * 100.0 + 1.0)}%  {signElapsed}{int((float(elapsed) / float(duration)) * 100.0)}%"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{int((float(elapsed) / float(duration)) * 100.0)}%")
								except ZeroDivisionError:
									pass
							case self.VFD:
								if remaining is None:
									result = ngettext("%d Min", "%d Mins", (duration // 60)) % (duration // 60)
								else:
									result = {
										# "1": f"{signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
										"1": f"{signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}",  # Elapsed
										# "2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
										"2": f"{signElapsed}{elapsed // 60}  {signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}",  # Elapsed & Remaining
										# "3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext("%d Min", "%d Mins", (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
										"3": f"{signRemaining}{remaining // 60}  {signElapsed}{ngettext('%d Min', '%d Mins', (elapsed // 60)) % (elapsed // 60)}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{ngettext('%d Min', '%d Mins', (remaining // 60)) % (remaining // 60)}")
									# }.get(config.usage.swap_time_remaining_on_vfd.value, f"{signRemaining}{ngettext("%d Min", "%d Mins", (remaining // 60)) % (remaining // 60)}")
							case self.WITH_SECONDS_VFD:
								if remaining is None:
									result = f"{signDuration}{duration // 3600}:{duration % 3600 // 60:02d}:{duration % 60:02d}"
								else:
									result = {
										"1": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}",  # Elapsed
										"2": f"{signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}  {signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}",  # Elapsed & Remaining
										"3": f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}  {signElapsed}{elapsed // 3600}:{elapsed % 3600 // 60:02d}:{elapsed % 60:02d}"  # Remaining & Elapsed
									}.get(config.usage.swap_time_remaining_on_osd.value, f"{signRemaining}{remaining // 3600}:{remaining % 3600 // 60:02d}:{remaining % 60:02d}")
							case _:
								result = f"{signDuration}{duration}"
		# print(f"[RemainingToText] DEBUG: Converter string token '{self.tokenText}' result is '{result}'{"." if isinstance(result, str) else " TYPE MISMATCH!"}")
		return result

	text = property(getText)
