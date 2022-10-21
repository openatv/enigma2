from time import localtime, mktime, strftime

from enigma import eEPGCache, eServiceEventEnums

from Components.config import config
from Components.Element import cached
from Components.Converter.Converter import Converter
from Components.Converter.genre import getGenreStringSub
from Tools.Directories import resolveFilename, SCOPE_GUISKIN


class ETSIClassifications(dict):
	def shortRating(self, age):
		if age == 0:
			return _("All ages")
		elif age <= 15:
			age += 3
			return " %d+" % age

	def longRating(self, age):
		if age == 0:
			return _("Rating undefined")
		elif age <= 15:
			age += 3
			return _("Minimum age %d years") % age

	def imageRating(self, age):
		if age == 0:
			return "ratings/ETSI-ALL.png"
		elif age <= 15:
			age += 3
			return "ratings/ETSI-%d.png" % age

	def __init__(self):
		self.update([(i, (self.shortRating(c), self.longRating(c), self.imageRating(c))) for i, c in enumerate(range(0, 15))])


class AusClassifications(dict):
	# In Australia "Not Classified" (NC) is to be displayed as an empty string.
	#            0   1   2    3    4    5    6    7    8     9     10   11   12    13    14    15
	SHORTTEXT = ("", "", "P", "P", "C", "C", "G", "G", "PG", "PG", "M", "M", "MA", "MA", "AV", "R")
	LONGTEXT = {
		"": _("Not Classified"),
		"P": _("Preschool"),
		"C": _("Children"),
		"G": _("General"),
		"PG": _("Parental Guidance Recommended"),
		"M": _("Mature Audience 15+"),
		"MA": _("Mature Adult Audience 15+"),
		"AV": _("Adult Audience, Strong Violence 15+"),
		"R": _("Restricted 18+")
	}
	IMAGES = {
		"": "ratings/blank.png",
		"P": "ratings/AUS-P.png",
		"C": "ratings/AUS-C.png",
		"G": "ratings/AUS-G.png",
		"PG": "ratings/AUS-PG.png",
		"M": "ratings/AUS-M.png",
		"MA": "ratings/AUS-MA.png",
		"AV": "ratings/AUS-AV.png",
		"R": "ratings/AUS-R.png"
	}

	def __init__(self):
		self.update([(i, (c, self.LONGTEXT[c], self.IMAGES[c])) for i, c in enumerate(self.SHORTTEXT)])


# Each country classification object in the map tuple must be an object that
# supports obj.get(key[, default]). It need not actually be a dict object.
#
# The other element is how the rating number should be formatted if there
# is no match in the classification object.
#
# If there is no matching country then the default ETSI should be selected.

COUNTRIES = {
	"ETSI": (ETSIClassifications(), lambda age: (_("bc%d") % age, _("Rating defined by broadcaster - %d") % age, "ratings/ETSI-na.png")),
	"AUS": (AusClassifications(), lambda age: (_("BC%d") % age, _("Rating defined by broadcaster - %d") % age, "ratings/AUS-na.png"))
}


class EventName(Converter):
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
	RATING_SMALL = 10
	PDC = 11
	PDC_TIME = 12
	PDC_TIME_SHORT = 13
	IS_RUNNING_STATUS = 14
	GENRE_LIST = 15
	EVENT_EXTRA_DATA = 16
	EPG_SOURCE = 17

	NEXT_DESCRIPTION = 21
	THIRD_NAME = 22
	THIRD_NAME2 = 23
	THIRD_DESCRIPTION = 24

	RAW_RATING = 31
	RATING_COUNTRY = 32
	RATING_ICON = 33

	CRID_SERIES = 41
	CRID_EPISODE = 42
	CRID_RECOMMENDATION = 43

	KEYWORDS = {
		# Arguments...
		"Name": ("type", NAME),
		"Description": ("type", SHORT_DESCRIPTION),
		"ShortDescription": ("type", SHORT_DESCRIPTION),
		"ExtendedDescription": ("type", EXTENDED_DESCRIPTION),
		"FullDescription": ("type", FULL_DESCRIPTION),
		"ID": ("type", ID),
		"NowName": ("type", NAME_NOW),
		"NameNow": ("type", NAME_NOW),
		"NextName": ("type", NAME_NEXT),
		"NameNext": ("type", NAME_NEXT),
		"NextNameOnly": ("type", NAME_NEXT2),
		"NameNextOnly": ("type", NAME_NEXT2),
		"Genre": ("type", GENRE),
		"GenreList": ("type", GENRE_LIST),
		"Rating": ("type", RATING),
		"SmallRating": ("type", RATING_SMALL),
		"CRIDSeries": ("type", CRID_SERIES),
		"CRIDEpisode": ("type", CRID_EPISODE),
		"CRIDRecommendation": ("type", CRID_RECOMMENDATION),
		"Pdc": ("type", PDC),
		"PdcTime": ("type", PDC_TIME),
		"PdcTimeShort": ("type", PDC_TIME_SHORT),
		"IsRunningStatus": ("type", IS_RUNNING_STATUS),
		"NextDescription": ("type", NEXT_DESCRIPTION),
		"ThirdName": ("type", THIRD_NAME),
		"ThirdNameOnly": ("type", THIRD_NAME2),
		"ThirdDescription": ("type", THIRD_DESCRIPTION),
		"RawRating": ("type", RAW_RATING),
		"RatingCountry": ("type", RATING_COUNTRY),
		"RatingIcon": ("type", RATING_ICON),
		# Options...
		"Separated": ("separator", "\n\n"),
		"NotSeparated": ("separator", "\n"),
		"SeparatorSlash": ("separator", "/"),
		"SeparatorComma": ("separator", ", "),
		"Trimmed": ("trim", True),
		"NotTrimmed": ("trim", False)
	}

	RATING_SHORT = 0
	RATING_LONG = 1
	RATING_IMAGE = 2
	RATSHORT = 0  # Deprecated name.
	RATLONG = 1  # Deprecated name.
	RATICON = 2  # Deprecated name.

	RATING_NORMAL = 0
	RATING_DEFAULT = 1
	RATNORMAL = 0  # Deprecated name.
	RATDEFAULT = 1  # Deprecated name.

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgcache = eEPGCache.getInstance()

		self.type = self.NAME
		self.separator = None
		self.trim = False

		parse = ","
		type.replace(";", parse)  # Some builds use ";" as a separator, most use ",".
		args = [arg.strip() for arg in type.split(parse)]
		for arg in args:
			name, value = self.KEYWORDS.get(arg, ("Error", None))
			if name == "Error":
				print("[EventName] ERROR: Unexpected / Invalid argument token '%s'!" % arg)
			else:
				setattr(self, name, value)
		if self.separator is None:
			self.separator = self.KEYWORDS["SeparatorComma" if self.type == self.GENRE_LIST else "NotSeparated"][1]

	def trimText(self, text):
		return str(text).strip() if self.trim else str(text)

	def getCRID(self, event, types):
		print("[EventName] getCRID %s" % types)
		CRIDs = event.getCridData(types)
		print("[EventName] getCRID %s" % CRIDs)
		return CRIDs and CRIDs[0][2] or ""

	def formatDescription(self, description, extended):
		description = self.trimText(description)
		extended = self.trimText(extended)
		if description[0:20] == extended[0:20]:
			return extended
		if description and extended:
			description += self.separator
		return description + extended

	@cached
	def getBoolean(self):
		event = self.source.event
		return True if event and self.type == self.PDC and event.getPdcPil() else False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		event = self.source.event
		if event is None:
			return ""

		if self.type == self.NAME:
			return self.trimText(event.getEventName())
		elif self.type in (self.RATING, self.RATING_SMALL, self.RATING_ICON):
			rating = event.getParentalData()
			if rating:
				age = rating.getRating()
				country = rating.getCountryCode().upper()
				c = COUNTRIES[country] if country in COUNTRIES else COUNTRIES["ETSI"]
				if config.misc.epgratingcountry.value:
					c = COUNTRIES[config.misc.epgratingcountry.value]
				rating = c[self.RATNORMAL].get(age, c[self.RATDEFAULT](age))
				if rating:
					if self.type == self.RATING:
						return self.trimText(rating[self.RATLONG])
					elif self.type == self.RATING_SMALL:
						return self.trimText(rating[self.RATSHORT])
					return resolveFilename(SCOPE_GUISKIN, rating[self.RATICON])
		elif self.type in (self.GENRE, self.GENRE_LIST):
			if not config.usage.show_genre_info.value:
				return ""
			genres = event.getGenreDataList()
			if genres:
				if self.type == self.GENRE:
					genres = genres[0:1]
				rating = event.getParentalData()
				country = rating.getCountryCode().upper() if rating else "ETSI"
				if config.misc.epggenrecountry.value:
					country = config.misc.epggenrecountry.value
				return self.separator.join((genretext for genretext in (self.trimText(getGenreStringSub(genre[0], genre[1], country=country)) for genre in genres) if genretext))
		elif self.type == self.CRID_EPISODE:
			return self.trimText(self.getCRID(event, eServiceEventEnums.EPISODE_MATCH))
		elif self.type == self.CRID_SERIES:
			return self.trimText(self.getCRID(event, eServiceEventEnums.SERIES_MATCH))
		elif self.type == self.CRID_RECOMMENDATION:
			return self.trimText(self.getCRID(event, eServiceEventEnums.RECOMMENDATION_MATCH))
		elif self.type == self.NAME_NOW:
			return "%s: %s" % (pgettext("now/next: 'now' event label", "Now"), self.trimText(event.getEventName()))
		elif self.type == self.SHORT_DESCRIPTION:
			return self.trimText(event.getShortDescription())
		elif self.type == self.EXTENDED_DESCRIPTION:
			return self.trimText(event.getExtendedDescription() or event.getShortDescription())
		elif self.type == self.FULL_DESCRIPTION:
			return self.formatDescription(event.getShortDescription(), event.getExtendedDescription())
		elif self.type == self.ID:
			return self.trimText(event.getEventId())
		elif self.type == self.EVENT_EXTRA_DATA:
			pass
			# Not included yet.
			# ret = event.getExtraEventData()
		elif self.type == self.EPG_SOURCE:
			pass
			# Not included yet.
			# ret = event.getEPGSource()
		elif self.type == self.PDC:
			if event.getPdcPil():
				return _("PDC")
		elif self.type in (self.PDC_TIME, self.PDC_TIME_SHORT):
			pil = event.getPdcPil()
			if pil:
				begin = localtime(event.getBeginTime())
				start = localtime(mktime([begin.tm_year, (pil & 0x7800) >> 11, (pil & 0xF8000) >> 15, (pil & 0x7C0) >> 6, (pil & 0x3F), 0, begin.tm_wday, begin.tm_yday, begin.tm_isdst]))
				if self.type == self.PDC_TIME_SHORT:
					return strftime(config.usage.time.short.value, start)
				return strftime("%s %s" % (config.usage.date.short.value, config.usage.time.short.value), start)
		elif self.type == self.IS_RUNNING_STATUS:
			if event.getPdcPil():
				runningStatus = event.getRunningStatus()
				if runningStatus == 1:
					return _("Not running")
				if runningStatus == 2:
					return _("Starts in a few seconds")
				if runningStatus == 3:
					return _("Pausing")
				if runningStatus == 4:
					return _("Running")
				if runningStatus == 5:
					return _("Service off-air")
				if runningStatus in (6, 7):
					return _("Reserved for future use")
				return _("Undefined")
		elif self.type in (self.NAME_NEXT, self.NAME_NEXT2) or self.type >= self.NEXT_DESCRIPTION:
			try:
				reference = self.source.service
				info = reference and self.source.info
				if info:
					test = ["ITSECX", (reference.toString(), 1, -1, 1440)]  # Search next 24 hours
					self.epgData = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
					if self.epgData:
						if self.type == self.NAME_NEXT and self.epgData[1][1]:
							return "%s: %s" % (pgettext("now/next: 'next' event label", "Next"), self.trimText(self.epgData[1][1]))
						elif self.type == self.NAME_NEXT2 and self.epgData[1][1]:
							return self.trimText(self.epgData[1][1])
						elif self.type == self.NEXT_DESCRIPTION and (self.epgData[1][2] or self.epgData[1][3]):
							return self.formatDescription(self.epgData[1][2], self.epgData[1][3])
						if self.type == self.THIRD_NAME and self.epgData[2][1]:
							return "%s: %s" % (pgettext("third event: 'third' event label", "Later"), self.trimText(self.epgData[2][1]))
						elif self.type == self.THIRD_NAME2 and self.epgData[2][1]:
							return self.trimText(self.epgData[2][1])
						elif self.type == self.THIRD_DESCRIPTION and (self.epgData[2][2] or self.epgData[2][3]):
							return self.formatDescription(self.epgData[2][2], self.epgData[2][3])
			except IndexError:  # Failed to return any EPG data.
				if self.type == self.NAME_NEXT:
					return "%s: %s" % (pgettext("now/next: 'next' event label", "Next"), self.trimText(event.getEventName()))
		elif self.type == self.RAW_RATING:
			rating = event.getParentalData()
			if rating:
				return "%d" % rating.getRating()
		elif self.type == self.RATING_COUNTRY:
			rating = event.getParentalData()
			if rating:
				return rating.getCountryCode().upper()
		return ""

	text = property(getText)
