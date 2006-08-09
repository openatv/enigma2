from Components.Converter.Converter import Converter
from Components.Element import cached

class EventName(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Description":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return "N/A"
			
		if self.type == self.NAME:
			return event.getEventName()
		elif self.type == self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type == self.EXTENDED_DESCRIPTION:
			return event.getExtendedDescription()
			
	text = property(getText)
