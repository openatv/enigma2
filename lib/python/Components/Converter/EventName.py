from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eEPGCache

class EventName(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	FULL_DESCRIPTION = 3
	ID = 4
	NEXT_NAME = 5
	NEXT_DESCRIPTION = 6
	THIRD_NAME = 7
	THIRD_DESCRIPTION = 8

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()
		if type == "Description":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		elif type == "FullDescription":
			self.type = self.FULL_DESCRIPTION
		elif type == "ID":
			self.type = self.ID
		elif type == "NextName":
			self.type = self.NEXT_NAME
		elif type == "NextDescription":
			self.type = self.NEXT_DESCRIPTION
		elif type == "ThirdName":
			self.type = self.THIRD_NAME
		elif type == "ThirdDescription":
			self.type = self.THIRD_DESCRIPTION
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""

		if self.type == self.NAME:
			if event.getEventName() == "Visibile in analogico o digit. terrestre":
				return event.getShortDescription().title()
			else:
				return event.getEventName()
		elif self.type == self.SHORT_DESCRIPTION:
			return event.getShortDescription()
		elif self.type == self.EXTENDED_DESCRIPTION:
			return event.getExtendedDescription() or event.getShortDescription()
		elif self.type == self.FULL_DESCRIPTION:
			description = event.getShortDescription()
			extended = event.getExtendedDescription()
			if description and extended:
				description += '\n'
			return description + extended
		elif self.type == self.ID:
			return str(event.getEventId())
		elif int(self.type) > 4:
			reference = self.source.service
			info = reference and self.source.info
			if info is None:
				return
			test = [ 'ITSECX', (reference.toString(), 1, -1, 1440) ] # search next 24 hours
			self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
			if self.list:
				try:
					if self.type == self.NEXT_NAME and self.list[1][1]:
						return self.list[1][1]
					elif self.type == self.NEXT_DESCRIPTION and (self.list[1][2] or self.list[1][3]):
						description = self.list[1][2]
						extended = self.list[1][3]
						if (description and extended) and (description[0:20] != extended[0:20]):
							description += '\n'
						return description + extended
					elif self.type == self.THIRD_NAME and self.list[2][1]:
						return self.list[2][1]
					elif self.type == self.THIRD_DESCRIPTION and (self.list[2][2] or self.list[2][3]):
						description = self.list[2][2]
						extended = self.list[2][3]
						if (description and extended) and (description[0:20] != extended[0:20]):
							description += '\n'
						return description + extended
					else:
						# failed to return any epg data.
						return ""
				except:
					# failed to return any epg data.
					return ""

	text = property(getText)
