from Components.Converter.Converter import Converter
from Components.Element import cached

class RemainingToText(Converter, object):
	DEFAULT = 0
	WITH_SECONDS = 1
	NO_SECONDS = 2
	IN_SECONDS = 3

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "WithSeconds":
			self.type = self.WITH_SECONDS
		elif type == "NoSeconds":
			self.type = self.NO_SECONDS
		elif type == "InSeconds":
			self.type = self.IN_SECONDS	
		else:
			self.type = self.DEFAULT

	@cached
	def getText(self):
		time = self.source.time
		if time is None:
			return ""

		(duration, remaining) = self.source.time

		if self.type == self.WITH_SECONDS:
			if remaining is not None:
				return "%d:%02d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60), remaining % 60)
			else:
				return "%02d:%02d:%02d" % (duration / 3600, (duration / 60) - ((duration / 3600) * 60), duration % 60)
		elif self.type == self.NO_SECONDS:
			if remaining is not None:
				return "+%d:%02d" % (remaining / 3600, (remaining / 60) - ((remaining / 3600) * 60))
			else:
				return "%02d:%02d" % (duration / 3600, (duration / 60) - ((duration / 3600) * 60))
		elif self.type == self.IN_SECONDS:
			if remaining is not None:
				return str(remaining)
			else:
				return str(duration)
		elif self.type == self.DEFAULT:
			if remaining is not None:
				return "+%d min" % (remaining / 60)
			else:
				return "%d min" % (duration / 60)
		else:
			return "???"

	text = property(getText)
