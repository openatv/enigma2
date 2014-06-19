from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.genre import getGenreStringLong, getGenreStringSub

class EventName(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	FULL_DESCRIPTION = 3
	ID = 4
	NAME_NOW = 5
	NAME_NEXT = 6
	GENRE = 7
	RATING = 8
	SRATING = 9

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Description":
			self.type = self.SHORT_DESCRIPTION
		elif type == "ExtendedDescription":
			self.type = self.EXTENDED_DESCRIPTION
		elif type == "FullDescription":
			self.type = self.FULL_DESCRIPTION
		elif type == "ID":
			self.type = self.ID
		elif type == "NameNow":
			self.type = self.NAME_NOW
		elif type == "NameNext":
			self.type = self.NAME_NEXT
		elif type == "Genre":
			self.type = self.GENRE
		elif type == "Rating":
			self.type = self.RATING
		elif type == "SmallRating":
			self.type = self.SRATING
		else:
			self.type = self.NAME

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""

		if self.type == self.NAME:
			return event.getEventName()
		elif self.type == self.SRATING:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				country = rating.getCountryCode()
				age = rating.getRating()
				if age == 0:
					return _("All ages")
				elif age > 15:
					return _("bc%s") % age
				else:
					age += 3
					return " %d+" % age
		elif self.type == self.RATING:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				country = rating.getCountryCode()
				age = rating.getRating()
				if age == 0:
					return _("Rating undefined")
				elif age > 15:
					return _("Rating defined by broadcaster - %d") % age
				else:
					age += 3
					return _("Minimum age %d years") % age
		elif self.type == self.GENRE:
			genre = event.getGenreData()
			if genre is None:
				return ""
			else:
				return getGenreStringSub(genre.getLevel1(), genre.getLevel2())
		elif self.type == self.NAME_NOW:
			return pgettext("now/next: 'now' event label", "Now") + ": " + event.getEventName()
		elif self.type == self.NAME_NEXT:
			return pgettext("now/next: 'next' event label", "Next") + ": " + event.getEventName()
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

	text = property(getText)
