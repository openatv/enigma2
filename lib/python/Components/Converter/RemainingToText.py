from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config

class RemainingToText(Converter, object):
	DEFAULT = 0
	WITH_SECONDS = 1
	NO_SECONDS = 2
	IN_SECONDS = 3
	PERCENTAGE = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "WithSeconds":
			self.type_orig = self.WITH_SECONDS
		elif type == "NoSeconds":
			self.type_orig = self.NO_SECONDS
		elif type == "InSeconds":
			self.type_orig = self.IN_SECONDS	
		elif type == "Percentage":
			self.type_orig = self.PERCENTAGE	
		else:
			self.type_orig = self.DEFAULT

	@cached
	def getText(self):
		if config.usage.swap_time_display_on_osd.value == "1" or config.usage.swap_time_display_on_vfd.value == "1":
			self.type = self.DEFAULT
		elif config.usage.swap_time_display_on_osd.value == "2" or config.usage.swap_time_display_on_vfd.value == "2":
			self.type = self.NO_SECONDS
		elif config.usage.swap_time_display_on_osd.value == "3" or config.usage.swap_time_display_on_vfd.value == "3":
			self.type = self.PERCENTAGE	
		else:
			self.type = self.type_orig

		time = self.source.time
		if time is None:
			return ""

		if str(time[1]) != 'None':
			if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
				(duration, elapsed) = self.source.time
			if config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
				(duration, elapsed, remaining) = self.source.time
			elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
				(duration, remaining, elapsed) = self.source.time
			else:
				(duration, remaining) = self.source.time
		else:
			(duration, remaining) = self.source.time

		if self.type == self.WITH_SECONDS:
			if remaining is not None:
				if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
					return "-%d:%02d:%02d" % (elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60), elapsed % 60)
				elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
					return "-%d:%02d:%02d  +%d:%02d:%02d" % (elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60), elapsed % 60, remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60), remaining % 60)
				elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
					return "+%d:%02d:%02d  -%d:%02d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60), remaining % 60, elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60), elapsed % 60)
				else:
					return "+%d:%02d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60), remaining % 60)
			else:
				return "%02d:%02d:%02d" % (duration / 3600, (duration / 60) - ((duration / 3600) * 60), duration % 60)
		elif self.type == self.NO_SECONDS:
			if remaining is not None:
				if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
					return "-%d:%02d" % (elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60))
				elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
					return "-%d:%02d  +%d:%02d" % (elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60), remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60))
				elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
					return "+%d:%02d  -%d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60), elapsed / 3600, (elapsed / 60) - ((elapsed / 3600) * 60))
				else:
					return "+%d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60))
			else:
				return "%02d:%02d" % (duration / 3600, (duration / 60) - ((duration / 3600) * 60))
		elif self.type == self.IN_SECONDS:
			if remaining is not None:
				if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
					return "-%d" % (elapsed)
				elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
					return "-%d  +%d" % (elapsed, remaining)
				elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
					return "+%d  -%d" % (remaining, elapsed)
				else:
					return "+%d" % (remaining)
			else:
				return str(duration)
		elif self.type == self.PERCENTAGE:
			if remaining is not None:
				if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
					return "-%d%%" % ((float(elapsed + 0.0) / float(duration + 0.0)) * 100)
				elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
					return "-%d%%  +%d%%" % ((float(elapsed + 0.0) / float(duration + 0.0)) * 100, (float(remaining + 0.0) / float(duration + 0.0)) * 100)
				elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
					return "+%d%%  -%d%%" % ((float(remaining + 0.0) / float(duration + 0.0)) * 100, (float(elapsed + 0.0) / float(duration + 0.0)) * 100)
				else:
					return "+%d%%" % ((float(remaining + 0.0) / float(duration + 0.0)) * 100)
			else:
				return str(duration)
		elif self.type == self.DEFAULT:
			if remaining is not None:
				if config.usage.swap_time_remaining_on_osd.value == "1" or config.usage.swap_time_remaining_on_vfd.value == "1":
					return "-%d min" % (elapsed / 60)
				elif config.usage.swap_time_remaining_on_osd.value == "2" or config.usage.swap_time_remaining_on_vfd.value == "2":
					return "-%d min  +%d min" % ((elapsed / 60), (remaining / 60))
				elif config.usage.swap_time_remaining_on_osd.value == "3" or config.usage.swap_time_remaining_on_vfd.value == "3":
					return "+%d min  -%d min" % ((remaining / 60), (elapsed / 60))
				else:
					return "+%d min" % (remaining / 60)
			else:
				return "%d min" % (duration / 60)
		else:
			return "???"

	text = property(getText)
