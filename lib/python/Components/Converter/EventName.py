from Components.Converter.Converter import Converter
from Components.Element import cached

class EventName(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	SHORT_AND_EXTENDED_DESCRIPTION = 3
	ID = 4
	
	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Description":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		elif type == "ShortAndExtendedDescription":
			self.type = SHORT_AND_EXTENDED_DESCRIPTION:
		elif type == "ID":
			self.type = self.ID
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""
			
		if self.type == self.NAME:
			return event.getEventName()
		elif self.type == self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type == self.EXTENDED_DESCRIPTION:
			return event.getExtendedDescription()
		elif self.type == self.SHORT_AND_EXTENDED_DESCRIPTION:
			description = event.getShortDescription()
			extended = event.getExtendedDescription()
			if description and extended:
				description += '\n\n'
			return description + event.getExtendedDescription()
		elif self.type == self.ID:
			return str(event.getEventId())
		
	text = property(getText)
