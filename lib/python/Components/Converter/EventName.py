from enigma import eEPGCache

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.genre import getGenreStringSub


class EventName(Converter, object):
	NAME = 0
	SHORT_DESCRIPTION = 1
	EXTENDED_DESCRIPTION = 2
	FULL_DESCRIPTION = 3
	ID = 4
	NAME_NOW = 5
	NAME_NEXT = 6
	NAME_NEXT2 = 7
	GENRE = 8
	RATING = 9
	SRATING = 10

	NEXT_DESCRIPTION = 21
	THIRD_NAME = 22
	THIRD_DESCRIPTION = 23

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
		elif type == "NameNow" or type == "NowName":
			self.type = self.NAME_NOW
		elif type == "NameNext" or type == "NextName":
			self.type = self.NAME_NEXT
		elif type == "NameNextOnly" or type == "NextNameOnly":
			self.type = self.NAME_NEXT2
		elif type == "Genre":
			self.type = self.GENRE
		elif type == "Rating":
			self.type = self.RATING
		elif type == "SmallRating":
			self.type = self.SRATING

		elif type == "NextDescription":
			self.type = self.NEXT_DESCRIPTION
		elif type == "ThirdName":
			self.type = self.THIRD_NAME
		elif type == "ThirdDescription":
			self.type = self.THIRD_DESCRIPTION
		else:
			self.type = self.NAME

	def getName(self, event):
		name = event.getEventName()
		if name == "Visibile gratis su tv terrestre e TivuSat":
			return event.getShortDescription().title()
		else:
			return name

	def getSRating(self, event):
		rating = event.getParentalData()
		if rating is None:
			return ""
		else:
			age = rating.getRating()
			if age == 0:
				return _("All ages")
			elif age > 15:
				return _("bc%s") % age
			else:
				age += 3
				return " %d+" % age

	def getRating(self, event):
		rating = event.getParentalData()
		if rating is None:
			return ""
		else:
			age = rating.getRating()
			if age == 0:
				return _("Rating undefined")
			elif age > 15:
				return _("Rating defined by broadcaster - %d") % age
			else:
				age += 3
				return _("Minimum age %d years") % age

	def getGenre(self, event):
		genre = event.getGenreData()
		if genre is None:
			return ""
		else:
			return getGenreStringSub(genre.getLevel1(), genre.getLevel2())

	def getShortDescription(self, event):
		return event.getShortDescription()

	def getExtendedDescription(self, event):
		return event.getExtendedDescription() or event.getShortDescription()

	def getFullDescription(self, event):
		description = self.getShortDescription(event)
		extended = self.getExtendedDescription(event)
		if description[0:20] == extended[0:20]:
			return extended
		if description and extended:
			description += '\n\n'
		return description + extended

	def getId(self, event):
		return str(event.getEventId())

	def getNameNext(self, list):
		return list[1][1]

	def getNextDescription(self, list):
		description = list[1][2]
		extended = list[1][3]
		if description[0:20] == extended[0:20]:
			return extended
		if description and extended:
			description += '\n'
		return description + extended

	def getThirdDescription(self, list):
		description = self.list[2][2]
		extended = self.list[2][3]
		if description[0:20] == extended[0:20]:
			return extended
		if description and extended:
			description += '\n'
		return description + extended

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""

		if self.type == self.NAME:
			return self.getName(event)
		elif self.type == self.SRATING:
			return self.getSRating(event)
		elif self.type == self.RATING:
			return self.getRating(event)
		elif self.type == self.GENRE:
			return self.getGenre(event)
		elif self.type == self.NAME_NOW:
			return pgettext("now/next: 'now' event label", "Now") + ": " + self.getName(event)
		elif self.type == self.SHORT_DESCRIPTION:
			return self.getShortDescription(event)
		elif self.type == self.EXTENDED_DESCRIPTION:
			return self.getExtendedDescription(event)
		elif self.type == self.FULL_DESCRIPTION:
			return self.getFullDescription(event)
		elif self.type == self.ID:
			return self.getId(event)
		elif self.type in (self.NAME_NEXT, self.NAME_NEXT2) or self.type >= self.NEXT_DESCRIPTION:
			try:
				reference = self.source.service
				info = reference and self.source.info
				if info is None:
					return
				test = ['ITSECX', (reference.toString(), 1, -1, 1440)]  # search next 24 hours
				self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
				if self.list:
					if self.type == self.NAME_NEXT and self.list[1][1]:
						return pgettext("now/next: 'next' event label", "Next") + ": " + self.getNameNext(list)
					elif self.type == self.NAME_NEXT2 and self.list[1][1]:
						return self.getNameNext(list)
					elif self.type == self.NEXT_DESCRIPTION and (self.list[1][2] or self.list[1][3]):
						return self.getNextDescription(list)
					elif self.type == self.THIRD_NAME and self.list[2][1]:
						return pgettext("third event: 'third' event label", "Later") + ": " + self.list[2][1]
					elif self.type == self.THIRD_DESCRIPTION and (self.list[2][2] or self.list[2][3]):
						return self.getThirdDescription(list)
					else:
						# failed to return any epg data.
						return ""
			except:
				# failed to return any epg data.
				if self.type == self.NAME_NEXT:
					return pgettext("now/next: 'next' event label", "Next") + ": " + self.getName(event)
				return ""

	text = property(getText)
