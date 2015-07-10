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
	RAWRATING = 11
	RATINGCOUNTRY = 12

	NEXT_DESCRIPTION = 21
	THIRD_NAME = 22
	THIRD_DESCRIPTION = 23

	AUSSHORT = 0
	AUSLONG  = 1
	AUSTEXT = {
		"NC"	: (" ",  "Not Classified"),
		"P"	: ("P",  "Preschool"),
		"C"	: ("C",  "Children"),
		"G"	: ("G",  "General"),
		"PG"	: ("PG", "Parental Guidance Recommended"),
		"M"	: ("M",  "Mature Audience 15+"),
		"MA"	: ("MA", "Mature Adult Audience 15+"),
		"AV"	: ("AV", "Adult Audience, Strong Violence 15+"),
		"R"	: ("R",  "Restricted 18+")
	}

	AUSRATINGS = {
		0	: AUSTEXT["NC"],
		1	: AUSTEXT["NC"],
		2	: AUSTEXT["P"],
		3	: AUSTEXT["P"],
		4	: AUSTEXT["C"],
		5	: AUSTEXT["C"],
		6	: AUSTEXT["G"],
		7	: AUSTEXT["G"],
		8	: AUSTEXT["PG"],
		9	: AUSTEXT["PG"],
		10	: AUSTEXT["M"],
		11	: AUSTEXT["M"],
		12	: AUSTEXT["MA"],
		13	: AUSTEXT["MA"],
		14	: AUSTEXT["AV"],
		15	: AUSTEXT["R"]
	}

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()

		args = type.split(',')
		args = [arg.strip() for arg in args]
		type = args.pop(0)

		if "Separated" in args:
			self.SEPARATOR = "\n\n"
		else:
			self.SEPARATOR = "\n"
		if "Trimmed" in args:
			self.TRIM = True
		else:
			self.TRIM = False

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
		elif type == "RawRating":
			self.type = self.RAWRATING
		elif type == "RatingCountry":
			self.type = self.RATINGCOUNTRY

		elif type == "NextDescription":
			self.type = self.NEXT_DESCRIPTION
		elif type == "ThirdName":
			self.type = self.THIRD_NAME
		elif type == "ThirdDescription":
			self.type = self.THIRD_DESCRIPTION
		else:
			self.type = self.NAME

	def trimText(self, text):
		if self.TRIM:
			return str(text).strip()
		else:
			return text

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""

		if self.type == self.NAME:
			return self.trimText(event.getEventName())
		elif self.type == self.RATINGCOUNTRY:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				return rating.getCountryCode()
		elif self.type == self.RAWRATING:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				return "%d" % int(rating.getRating())
		elif self.type == self.SRATING:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				country = rating.getCountryCode()
				age = int(rating.getRating())
				if country.upper() == "AUS":
					errmsg = _("BC%d") % age
					undef = (errmsg, "")
					return _(self.AUSRATINGS.get(age, undef)[self.AUSSHORT])
				else:
					if age == 0:
						return _("All ages")
					elif age > 15:
						return _("bc%d") % age
					else:
						age += 3
						return " %d+" % age
		elif self.type == self.RATING:
			rating = event.getParentalData()
			if rating is None:
				return ""
			else:
				country = rating.getCountryCode()
				age = int(rating.getRating())
				if country.upper() == "AUS":
					errmsg = _("Defined By Broadcaster (%d)") % age
					undef = ("",  errmsg)
					return _(self.AUSRATINGS.get(age, undef)[self.AUSLONG])
				else:
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
				return self.trimText(getGenreStringSub(genre.getLevel1(), genre.getLevel2()))
		elif self.type == self.NAME_NOW:
			return pgettext("now/next: 'now' event label", "Now") + ": " + self.trimText(event.getEventName())
		elif self.type == self.SHORT_DESCRIPTION:
			return self.trimText(event.getShortDescription())
		elif self.type == self.EXTENDED_DESCRIPTION:
			return self.trimText(event.getExtendedDescription() or event.getShortDescription())
		elif self.type == self.FULL_DESCRIPTION:
			description = self.trimText(event.getShortDescription())
			extended = self.trimText(event.getExtendedDescription())
			if description and extended:
				description += self.SEPARATOR
			return description + extended
		elif self.type == self.ID:
			return str(event.getEventId())
		elif int(self.type) in (6, 7) or int(self.type) >= 21:
			try:
				reference = self.source.service
				info = reference and self.source.info
				if info is None:
					return
				test = ['ITSECX', (reference.toString(), 1, -1, 1440)]  # search next 24 hours
				self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
				if self.list:
					if self.type == self.NAME_NEXT and self.list[1][1]:
						return pgettext("now/next: 'next' event label", "Next") + ": " + self.trimText(self.list[1][1])
					elif self.type == self.NAME_NEXT2 and self.list[1][1]:
						return self.trimText(self.list[1][1])
					elif self.type == self.NEXT_DESCRIPTION and (self.list[1][2] or self.list[1][3]):
						description = self.trimText(self.list[1][2])
						extended = self.trimText(self.list[1][3])
						if (description and extended) and (description[0:20] != extended[0:20]):
							description += self.SEPARATOR
						return description + extended
					elif self.type == self.THIRD_NAME and self.list[2][1]:
						return pgettext("third event: 'third' event label", "Later") + ": " + self.trimText(self.list[2][1])
					elif self.type == self.THIRD_DESCRIPTION and (self.list[2][2] or self.list[2][3]):
						description = self.trimText(self.list[2][2])
						extended = self.trimText(self.list[2][3])
						if (description and extended) and (description[0:20] != extended[0:20]):
							description += self.SEPARATOR
						return description + extended
					else:
						# failed to return any epg data.
						return ""
			except:
				# failed to return any epg data.
				if self.type == self.NAME_NEXT:
					return pgettext("now/next: 'next' event label", "Next") + ": " + self.trimText(event.getEventName())
				return ""

	text = property(getText)
