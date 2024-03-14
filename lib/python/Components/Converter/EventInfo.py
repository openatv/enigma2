from time import localtime, mktime, strftime, time

from enigma import eEPGCache, eServiceEventEnums

from ServiceReference import ServiceReference
from Components.config import config
from Components.Element import cached
from Components.Converter.genre import getGenreStringSub
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Tools.Conversions import UnitScaler, scaleNumber
from Tools.Directories import SCOPE_GUISKIN, resolveFilename


class ETSIClassifications(dict):
	def __init__(self):
		def shortRating(age):
			if age == 0:
				return _("All ages")
			elif age <= 15:
				age += 3
				return f"{age}+"

		def longRating(age):
			if age == 0:
				return _("Rating undefined")
			elif age <= 15:
				age += 3
				return _("Minimum age %d years") % age

		def imageRating(age):
			if age == 0:
				return "ratings/ETSI-ALL.png"
			elif age <= 15:
				age += 3
				return "ratings/ETSI-%d.png" % age

		self.update([(index, (shortRating(classification), longRating(classification), imageRating(classification))) for index, classification in enumerate(range(16))])


class AusClassifications(dict):
	def __init__(self):
		# In Australia "Not Classified" (NC) is to be displayed as an empty string.
		#            0   1   2    3    4    5    6    7    8     9     10   11   12    13    14    15
		shortText = ("", "", "P", "P", "C", "C", "G", "G", "PG", "PG", "M", "M", "MA", "MA", "AV", "R")
		longText = {
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
		images = {
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
		self.update([(index, (classification, longText[classification], images[classification])) for index, classification in enumerate(shortText)])


# Each country classification object in the map tuple must be an object that
# supports obj.get(key[, default]). It need not actually be a dict object.
#
# The other element is how the rating number should be formatted if there
# is no match in the classification object.
#
# If there is no matching country then the default ETSI should be selected.
#
COUNTRIES = {
	"ETSI": (ETSIClassifications(), lambda age: (_("bc%d") % age, _("Rating defined by broadcaster - %d") % age, "ratings/ETSI-na.png")),
	"AUS": (AusClassifications(), lambda age: (_("BC%d") % age, _("Rating defined by broadcaster - %d") % age, "ratings/AUS-na.png"))
}


class EventInfo(Converter, Poll):
	CRID_EPISODE = 0
	CRID_RECOMMENDATION = 1
	CRID_SERIES = 2
	DURATION = 3
	ELAPSED = 4
	ELAPSED_VFD = 5
	END_TIME = 6
	EPG_SOURCE = 7
	EXTENDED_DESCRIPTION = 8
	EXTRA_DATA = 9
	FILE_SIZE = 10
	FULL_DESCRIPTION = 11
	GENRE = 12
	GENRE_LIST = 13
	ID = 14
	MEDIA_PATH = 15
	NAME = 16
	NAME_NEXT = 17
	NAME_NEXT2 = 18
	NAME_NOW = 19
	NEXT_DESCRIPTION = 20
	NEXT_DURATION = 21
	NEXT_END_TIME = 22
	NEXT_START_TIME = 23
	NEXT_TIMES = 24
	PDC = 25
	PDC_TIME = 26
	PDC_TIME_SHORT = 27
	PROGRESS = 28
	RATING = 29
	RATING_CODE = 30
	RATING_COUNTRY = 31
	RATING_ICON = 32
	RATING_RAW = 33
	REMAINING = 34
	REMAINING_VFD = 35
	RUNNING_STATUS = 36
	SERVICE_NAME = 37
	SERVICE_REFERENCE = 38
	SHORT_DESCRIPTION = 39
	START_TIME = 40
	THIRD_DESCRIPTION = 41
	THIRD_DURATION = 42
	THIRD_END_TIME = 43
	THIRD_NAME = 44
	THIRD_NAME2 = 45
	THIRD_START_TIME = 46
	THIRD_TIMES = 47
	TIMES = 48

	RATING_SHORT = 0
	RATING_LONG = 1
	RATING_IMAGE = 2

	RATING_NORMAL = 0
	RATING_DEFAULT = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		tokenDictionary = {
			# Arguments...
			"CRIDEpisode": ("token", self.CRID_EPISODE, 0),
			"CRIDRecommendation": ("token", self.CRID_RECOMMENDATION, 0),
			"CRIDSeries": ("token", self.CRID_SERIES, 0),
			"Description": ("token", self.SHORT_DESCRIPTION, 0),
			"Duration": ("token", self.DURATION, 0),
			"EPGSource": ("token", self.EPG_SOURCE, 0),
			"Elapsed": ("token", self.ELAPSED, 60000),
			"ElapsedVFD": ("token", self.ELAPSED_VFD, 60000),
			"EndTime": ("token", self.END_TIME, 0),
			"ExtendedDescription": ("token", self.EXTENDED_DESCRIPTION, 0),
			"ExtraData": ("token", self.EXTRA_DATA, 0),
			"FileSize": ("token", self.FILE_SIZE, 0),
			"FullDescription": ("token", self.FULL_DESCRIPTION, 0),
			"Genre": ("token", self.GENRE, 0),
			"GenreList": ("token", self.GENRE_LIST, 0),
			"ID": ("token", self.ID, 0),
			"IsRunningStatus": ("token", self.RUNNING_STATUS, 0),  # Deprecated.
			"MediaPath": ("token", self.MEDIA_PATH, 0),
			"Name": ("token", self.NAME, 0),
			"NameNext": ("token", self.NAME_NEXT, 0),
			"NameNextOnly": ("token", self.NAME_NEXT2, 0),
			"NameNow": ("token", self.NAME_NOW, 0),
			"NextDescription": ("token", self.NEXT_DESCRIPTION, 0),
			"NextDuration": ("token", self.NEXT_DURATION, 0),
			"NextEndTime": ("token", self.NEXT_END_TIME, 0),
			"NextName": ("token", self.NAME_NEXT, 0),
			"NextNameOnly": ("token", self.NAME_NEXT2, 0),
			"NextStartTime": ("token", self.NEXT_START_TIME, 0),
			"NextTimes": ("token", self.NEXT_TIMES, 0),
			"NowName": ("token", self.NAME_NOW, 0),
			"Pdc": ("token", self.PDC, 0),
			"PdcTime": ("token", self.PDC_TIME, 0),
			"PdcTimeShort": ("token", self.PDC_TIME_SHORT, 0),
			"Progress": ("token", self.PROGRESS, 30000),
			"Rating": ("token", self.RATING, 0),
			"RatingCode": ("token", self.RATING_CODE, 0),
			"RatingCountry": ("token", self.RATING_COUNTRY, 0),
			"RatingIcon": ("token", self.RATING_ICON, 0),
			"RatingRaw": ("token", self.RATING_RAW, 0),
			"RawRating": ("token", self.RATING_RAW, 0),
			"Remaining": ("token", self.REMAINING, 60000),
			"RemainingVFD": ("token", self.REMAINING_VFD, 60000),
			"RunningStatus": ("token", self.RUNNING_STATUS, 0),
			"ServiceName": ("token", self.SERVICE_NAME, 0),
			"ServiceReference": ("token", self.SERVICE_REFERENCE, 0),
			"ShortDescription": ("token", self.SHORT_DESCRIPTION, 0),
			"SmallRating": ("token", self.RATING_CODE, 0),  # Deprecated?
			"StartTime": ("token", self.START_TIME, 0),
			"ThirdDescription": ("token", self.THIRD_DESCRIPTION, 0),
			"ThirdDuration": ("token", self.THIRD_DURATION, 0),
			"ThirdEndTime": ("token", self.THIRD_END_TIME, 0),
			"ThirdName": ("token", self.THIRD_NAME, 0),
			"ThirdNameOnly": ("token", self.THIRD_NAME2, 0),
			"ThirdStartTime": ("token", self.THIRD_START_TIME, 0),
			"ThirdTimes": ("token", self.THIRD_TIMES, 0),
			"Times": ("token", self.TIMES, 0),
			"VFDElapsed": ("token", self.ELAPSED_VFD, 60000),
			"VFDRemaining": ("token", self.REMAINING_VFD, 60000),
			# Options...
			"NotSeparated": ("separator", "\n", 0),
			"NotTrimmed": ("trim", False, 0),
			"Separated": ("separator", "\n\n", 0),
			"SeparatorComma": ("separator", ", ", 0),
			"SeparatorSlash": ("separator", "/", 0),
			"Trimmed": ("trim", True, 0)
		}
		self.token = self.NAME
		self.separator = None
		self.trim = False
		parse = ","
		tokens.replace(";", parse)  # Some builds use ";" as a separator, most use ",".
		tokens = [x.strip() for x in tokens.split(parse)]
		for token in tokens:
			variable, value, poll = tokenDictionary.get(token, (None, None, 0))
			if variable:
				setattr(self, variable, value)
				if variable == "token" and poll:
					self.poll_interval = poll
					self.poll_enabled = True
			elif token:
				print(f"[EventInfo] Error: Converter argument '{token}' is invalid!")
		if self.separator is None:
			self.separator = tokenDictionary["SeparatorComma" if self.token == self.GENRE_LIST else "NotSeparated"][1]
		self.epgCache = eEPGCache.getInstance()
		# self.tokenText = tokens  # DEBUG: This is only for testing purposes.

	@cached
	def getBoolean(self):
		result = False
		event = self.source.event
		if event:
			result = bool(event.getPdcPil() if self.token == self.PDC else self.getText())
		# print(f"[EventInfo] DEBUG: Converter Boolean token {self.tokenText} result is '{result}'{"." if isinstance(result, bool) else " TYPE MISMATCH!"}")
		return result

	boolean = property(getBoolean)

	@cached
	def getText(self):
		def trimText(text):
			return str(text).strip() if self.trim else str(text)

		def getCRID(event, types):
			CRIDs = event.getCridData(types)
			# print(f"[EventInfo] getCRID DEBUG: Type='{types}', CRIDs='{CRIDs}'.")
			return CRIDs and CRIDs[0][2] or ""

		def formatDescription(description, extended):
			description = trimText(description)
			extended = trimText(extended)
			if description[:20] == extended[:20]:
				return extended
			if description and extended:
				description = f"{description}{self.separator}"
			return f"{description}{extended}"

		def getEPGData():
			epgData = []
			serviceReference = self.source.service
			if serviceReference:
				search = ["ITSECX", (serviceReference.toString(), 1, -1, 1440)]  # Search next 24 hours.
				if self.epgCache:
					epgData = self.epgCache.lookupEvent(search)
			return epgData

		result = ""
		event = self.source.event
		if event:
			match self.token:
				case self.CRID_EPISODE:
					result = trimText(getCRID(event, eServiceEventEnums.EPISODE_MATCH))
				case self.CRID_RECOMMENDATION:
					result = trimText(getCRID(event, eServiceEventEnums.RECOMMENDATION_MATCH))
				case self.CRID_SERIES:
					result = trimText(getCRID(event, eServiceEventEnums.SERIES_MATCH))
				case self.EPG_SOURCE:
					result = event.getEPGSource()
				case self.EXTENDED_DESCRIPTION:
					result = trimText(event.getExtendedDescription() or event.getShortDescription())
				case self.EXTRA_DATA:
					result = event.getExtraEventData()
				case self.FILE_SIZE:
					info = self.source.info
					serviceReference = self.source.service
					if info and serviceReference:
						if (serviceReference.flags & eServiceReference.flagDirectory) == eServiceReference.flagDirectory:
							result = _("Directory")
						else:
							fileSize = info.getInfoObject(serviceReference, iServiceInformation.sFileSize)
							if fileSize:
								result = _("%s %sB") % UnitScaler()(fileSize) if fileSize > 0 else ""
				case self.FULL_DESCRIPTION:
					result = formatDescription(event.getShortDescription(), event.getExtendedDescription())
				case self.GENRE | self.GENRE_LIST:
					if config.usage.show_genre_info.value:
						genres = event.getGenreDataList()
						if genres:
							if self.token == self.GENRE:
								genres = genres[0:1]
							rating = event.getParentalData()
							country = rating.getCountryCode().upper() if rating else "ETSI"
							if config.misc.epggenrecountry.value:
								country = config.misc.epggenrecountry.value
							result = self.separator.join((genreText for genreText in (trimText(getGenreStringSub(genre[0], genre[1], country=country)) for genre in genres) if genreText))
				case self.ID:
					result = trimText(event.getEventId())
				case self.MEDIA_PATH:
					serviceReference = self.source.service
					if serviceReference:
						result = serviceReference.getPath()
				case self.NAME:
					result = trimText(event.getEventName())
				case self.NAME_NEXT:
					epgData = getEPGData()
					try:
						if epgData and epgData[1][1]:
							# result = f"{pgettext("now/next: 'next' event label", "Next")}: {trimText(epgData[1][1])}"
							label = pgettext("now/next: 'next' event label", "Next")
							result = f"{label}: {trimText(epgData[1][1])}"
					except IndexError:  # Failed to return any EPG data.
						# result = f"{pgettext("now/next: 'next' event label", "Next")}: {trimText(event.getEventName())}"
						label = pgettext("now/next: 'next' event label", "Next")
						result = f"{label}: {trimText(event.getEventName())}"
				case self.NAME_NEXT2:
					epgData = getEPGData()
					try:
						if epgData and epgData[1][1]:
							result = trimText(epgData[1][1])
					except IndexError:  # Failed to return any EPG data.
						pass
				case self.NAME_NOW:
					# result = f"{pgettext("now/next: 'now' event label", "Now")}: {trimText(event.getEventName())}"
					label = pgettext("now/next: 'now' event label", "Now")
					result = f"{label}: {trimText(event.getEventName())}"
				case self.NEXT_DESCRIPTION:
					epgData = getEPGData()
					try:
						if epgData and (epgData[1][2] or epgData[1][3]):
							result = formatDescription(epgData[1][2], epgData[1][3])
					except IndexError:  # Failed to return any EPG data.
						pass
				case self.PDC:
					if event.getPdcPil():
						result = _("PDC")
				case self.PDC_TIME | self.PDC_TIME_SHORT:
					pcdPil = event.getPdcPil()
					if pcdPil:
						begin = localtime(event.getBeginTime())
						start = localtime(mktime((begin.tm_year, (pcdPil & 0x7800) >> 11, (pcdPil & 0xF8000) >> 15, (pcdPil & 0x7C0) >> 6, (pcdPil & 0x3F), 0, begin.tm_wday, begin.tm_yday, begin.tm_isdst)))
						if self.token == self.PDC_TIME_SHORT:
							result = strftime(config.usage.time.short.value, start)
						else:
							result = strftime(f"{config.usage.date.short.value} {config.usage.time.short.value}", start)
				case self.RATING | self.RATING_CODE | self.RATING_ICON:
					rating = event.getParentalData()
					if rating:
						age = rating.getRating()
						country = rating.getCountryCode().upper()
						classifications = COUNTRIES[country] if country in COUNTRIES else COUNTRIES["ETSI"]
						if config.misc.epgratingcountry.value:
							classifications = COUNTRIES[config.misc.epgratingcountry.value]
						rating = classifications[self.RATING_NORMAL].get(age, classifications[self.RATING_DEFAULT](age))
						if rating:
							result = {
								self.RATING: trimText(rating[self.RATING_LONG]),
								self.RATING_CODE: trimText(rating[self.RATING_SHORT]),
								self.RATING_ICON: resolveFilename(SCOPE_GUISKIN, rating[self.RATING_IMAGE])
							}.get(self.token)
				case self.RATING_COUNTRY:
					rating = event.getParentalData()
					if rating:
						result = rating.getCountryCode().upper()
				case self.RATING_RAW:
					rating = event.getParentalData()
					if rating:
						result = f"{rating.getRating()}"
				case self.RUNNING_STATUS:
					if event.getPdcPil():
						result = {
							1: _("Not running"),
							2: _("Starts in a few seconds"),
							3: _("Pausing"),
							4: _("Running"),
							5: _("Service off-air"),
							6: _("Reserved for future use"),
							7: _("Reserved for future use")
						}.get(event.getRunningStatus(), _("Undefined"))
				case self.SERVICE_NAME:
					info = self.source.info
					serviceReference = self.source.service
					if info and serviceReference:
						result = ServiceReference(info.getInfoString(serviceReference, iServiceInformation.sServiceref)).getServiceName()
				case self.SERVICE_REFERENCE:
					info = self.source.info
					serviceReference = self.source.service
					if info and serviceReference:
						result = ServiceReference(info.getInfoString(serviceReference, iServiceInformation.sServiceref))
				case self.SHORT_DESCRIPTION:
					result = trimText(event.getShortDescription())
				case self.THIRD_DESCRIPTION:
					epgData = getEPGData()
					try:
						if epgData and (epgData[2][2] or epgData[2][3]):
							result = formatDescription(epgData[2][2], epgData[2][3])
					except IndexError:  # Failed to return any EPG data.
						pass
				case self.THIRD_NAME:
					epgData = getEPGData()
					try:
						if epgData and epgData[2][1]:
							# result = f"{pgettext("third event: 'third' event label", "Later")}: {trimText(epgData[2][1])}"
							label = pgettext("third event: 'third' event label", "Later")
							result = f"{label}: {trimText(epgData[2][1])}"
					except IndexError:  # Failed to return any EPG data.
						pass
				case self.THIRD_NAME2:
					epgData = getEPGData()
					try:
						if epgData and epgData[2][1]:
							result = trimText(epgData[2][1])
					except IndexError:  # Failed to return any EPG data.
						pass
		# print(f"[EventInfo] DEBUG: Converter string token {self.tokenText} result is '{result}'{"." if isinstance(result, str) else " TYPE MISMATCH!"}")
		return result

	text = property(getText)

	@cached
	def getTime(self):
		result = None
		if self.token != self.PROGRESS:
			event = self.source.event
			if event:
				startTime = event.getBeginTime()
				duration = event.getDuration()
				endTime = startTime + duration
				now = int(time())
				elapsed = now - startTime
				remaining = endTime - now
				if remaining < 0:
					remaining = 0
				inProgress = startTime <= now <= endTime
				match self.token:
					case self.DURATION:
						result = duration
					case self.ELAPSED | self.ELAPSED_VFD:
						if inProgress:
							value = config.usage.swap_time_remaining_on_osd.value if self.token == self.ELAPSED else config.usage.swap_time_remaining_on_vfd.value
							result = {
								"0": (duration, elapsed),
								"1": (duration, remaining),
								"2": (duration, elapsed, remaining),
								"3": (duration, remaining, elapsed)
							}.get(value)
						else:
							result = (duration, None)
					case self.END_TIME:
						result = endTime
					case self.NEXT_DURATION | self.NEXT_END_TIME | self.NEXT_START_TIME | self.NEXT_TIMES | self.THIRD_DURATION | self.THIRD_END_TIME | self.THIRD_START_TIME | self.THIRD_TIMES:
						serviceReference = self.source.service
						info = serviceReference and self.source.info
						if info is not None:
							search = ["IBDCX", (serviceReference.toString(), 1, -1, 1440)]  # Search next 24 hours.
							searchList = [] if self.epgCache is None else self.epgCache.lookupEvent(search)
							if searchList:
								try:
									result = {
										self.NEXT_DURATION: searchList[1][2],
										self.NEXT_END_TIME: searchList[1][1] + searchList[1][2],
										self.NEXT_START_TIME: searchList[1][1],
										self.NEXT_TIMES: (searchList[1][1], searchList[1][1] + searchList[1][2]),
										self.THIRD_DURATION: searchList[2][2],
										self.THIRD_END_TIME: searchList[2][1] + searchList[2][2],
										self.THIRD_START_TIME: searchList[2][1],
										self.THIRD_TIMES: (searchList[2][1], searchList[2][1] + searchList[2][2])
									}.get(self.token)
								except IndexError:
									pass
					case self.REMAINING | self.REMAINING_VFD:
						if inProgress:
							value = config.usage.swap_time_remaining_on_osd.value if self.token == self.REMAINING else config.usage.swap_time_remaining_on_vfd.value
							result = {
								"0": (duration, remaining),
								"1": (duration, elapsed),
								"2": (duration, elapsed, remaining),
								"3": (duration, remaining, elapsed)
							}.get(value)
						else:
							result = (duration, None)
					case self.START_TIME:
						result = startTime
					case self.TIMES:
						result = (startTime, endTime)
		# print(f"[EventInfo] DEBUG: Converter time token {self.tokenText} result is '{result}'{"." if result is None or isinstance(result, int) or isinstance(result, tuple) else " TYPE MISMATCH!"}")
		return result

	time = property(getTime)

	@cached
	def getValue(self):
		result = None
		if self.token == self.PROGRESS:
			event = self.source.event
			if event:
				progress = int(time()) - event.getBeginTime()
				duration = event.getDuration()
				if duration > 0 and progress >= 0:
					if progress > duration:
						progress = duration
					result = progress * 1000 // duration
		# print(f"[EventInfo] DEBUG: Converter value token {self.tokenText} result is '{result}'{"." if result is None or isinstance(result, int) else " TYPE MISMATCH!"}")
		return result

	value = property(getValue)
	range = 1000

	def changed(self, what):
		Converter.changed(self, what)
		if self.token == self.PROGRESS and len(self.downstream_elements):
			if not self.source.event and self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = False
			elif self.source.event and not self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = True
