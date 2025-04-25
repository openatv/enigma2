from Components.config import config

#
# Genre types taken from DVB standards documentation
#
# some broadcaster do define other types so this list
# may grow or be replaced..
#


class GenresETSI:
	maintype = (
		_("Reserved"),
		_("Movie/Drama"),
		_("News/Current Affairs"),
		_("Show/Games show"),
		_("Sports"),
		_("Children/Youth"),
		_("Music/Ballet/Dance"),
		_("Arts/Culture"),
		_("Social/Political/Economics"),
		_("Education/Science/Factual"),
		_("Leisure hobbies"),
		_("Other")
	)

	subtype = {
		# Movie/Drama
		1: (
			_("movie/drama (general)"),
			_("detective/thriller"),
			_("adventure/western/war"),
			_("science fiction/fantasy/horror"),
			_("comedy"),
			_("soap/melodrama/folkloric"),
			_("romance"),
			_("serious/classical/religious/historical movie/drama"),
			_("adult movie/drama")
		),
		# News/Current Affairs
		2: (
			_("news/current affairs (general)"),
			_("news/weather report"),
			_("news magazine"),
			_("documentary"),
			_("discussion/interview/debate")
		),
		# Show/Game show
		3: (
			_("show/game show (general)"),
			_("game show/quiz/contest"),
			_("variety show"),
			_("talk show")
		),
		# Sports
		4: (
			_("sports (general)"),
			_("special events"),
			_("sports magazine"),
			_("football/soccer"),
			_("tennis/squash"),
			_("team sports"),
			_("athletics"),
			_("motor sport"),
			_("water sport"),
			_("winter sport"),
			_("equestrian"),
			_("martial sports")
		),
		# Children/Youth
		5: (
			_("children's/youth program (general)"),
			_("pre-school children's program"),
			_("entertainment (6-14 year old)"),
			_("entertainment (10-16 year old)"),
			_("information/education/school program"),
			_("cartoon/puppets")
		),
		# Music/Ballet/Dance
		6: (
			_("music/ballet/dance (general)"),
			_("rock/pop"),
			_("serious music/classic music"),
			_("folk/traditional music"),
			_("jazz"),
			_("musical/opera"),
			_("ballet")
		),
		# Arts/Culture
		7: (
			_("arts/culture (without music, general)"),
			_("performing arts"),
			_("fine arts"),
			_("religion"),
			_("popular culture/traditional arts"),
			_("literature"),
			_("film/cinema"),
			_("experimental film/video"),
			_("broadcasting/press"),
			_("new media"),
			_("arts/culture magazine"),
			_("fashion")
		),
		# Social/Political/Economics
		8: (
			_("social/political issues/economics (general)"),
			_("magazines/reports/documentary"),
			_("economics/social advisory"),
			_("remarkable people")
		),
		# Education/Science/...
		9: (
			_("education/science/factual topics (general)"),
			_("nature/animals/environment"),
			_("technology/natural science"),
			_("medicine/physiology/psychology"),
			_("foreign countries/expeditions"),
			_("social/spiritual science"),
			_("further education"),
			_("languages")
		),

		# Leisure hobies
		10: (
			_("leisure hobbies (general)"),
			_("tourism/travel"),
			_("handicraft"),
			_("motoring"),
			_("fitness & health"),
			_("cooking"),
			_("advertisement/shopping"),
			_("gardening")
		),
		# Other
		11: (
			_("original language"),
			_("black & white"),
			_("unpublished"),
			_("live broadcast")
		),
	}


class GenresAUS:
	maintype = (
		_("Undefined"),
		_("Movie"),
		_("News"),
		_("Entertainment"),
		_("Sport"),
		_("Children's"),
		_("Music"),
		_("Arts/Culture"),
		_("Current Affairs"),
		_("Education/Information"),
		_("Infotainment"),
		_("Special"),
		_("Comedy"),
		_("Drama"),
		_("Documentary"),
	)

	subtype = {
		# Movie/Drama
		1: (
			_("movie (general)"),
		),
		# News
		2: (
			_("news (general)"),
		),
		# Entertainment
		3: (
			_("entertainment (general)"),
		),
		# Sport
		4: (
			_("sport (general)"),
		),
		# Childrens
		5: (
			_("children's (general)"),
		),
		# Music
		6: (
			_("music (general)"),
		),
		# Arts/Culture
		7: (
			_("arts/culture (general)"),
		),
		# Current Affairs
		8: (
			_("current affairs (general)"),
		),
		# Education/Information
		9: (
			_("education/information (general)"),
		),
		# Infotainment
		10: (
			_("infotainment (general)"),
		),
		# Special
		11: (
			_("special (general)"),
		),
		# Comedy
		12: (
			_("comedy (general)"),
		),
		# Drama
		13: (
			_("drama (general)"),
		),
		# Documentary
		14: (
			_("documentary (general)"),
		),
	}


class GenresAUSIceTV:
	maintype = (
		_("Miscellaneous"),
		_("Movie/Drama"),
		_("News/Current Affairs"),
		_("Show/Games show"),
		_("Sports"),
		_("Children/Youth"),
		_("Music/Ballet/Dance"),
		_("Arts/Culture"),
		_("Social/Political/Economics"),
		_("Education/Science/Factual"),
		_("Leisure hobbies"),
		_("Special"),
		_("Comedy"),
		_("Drama"),
		_("Documentary"),
		_("Real Life"),
	)

	subtype = {
		# Miscellaneous
		0: (
			_(""),  # 0x00
			_("Cult"),  # 0x01
			_("Youth"),  # 0x02 remapped from 0x01
			_("Wrestling"),  # 0x03 remapped from 0x01
			_("Violence"),  # 0x04 remapped from 0x01
			_("Short Film"),  # 0x05 remapped from 0x01
			_("Sailing"),  # 0x06 remapped from 0x01
			_("Renovation"),  # 0x07 remapped from 0x01
			_("Mini Series"),  # 0x08 remapped from 0x01
			_("MMA"),  # 0x09 remapped from 0x01
			_("Horse Racing"),  # 0x0a remapped from 0x01
			_("Finance"),  # 0x0b remapped from 0x01
			_("Film-Noir"),  # 0x0c remapped from 0x01
			_("Family"),  # 0x0d remapped from 0x01
			_("Cycling"),  # 0x0e remapped from 0x01
		),
		# Movie/Drama
		1: (
			_("Movie"),  # 0x10
			_("Crime"),  # 0x11
			_("Adventure"),  # 0x12
			_("Sci-Fi"),  # 0x13
			_("Comedy"),  # 0x14
			_("Soap Opera"),  # 0x15
			_("Romance"),  # 0x16
			_("Historical"),  # 0x17
			_("Adult"),  # 0x18
			_("Drama"),  # 0x19 remapped from 0x10
			_("Thriller"),  # 0x1a remapped from 0x11
			_("Mystery"),  # 0x1b remapped from 0x11
			_("Murder"),  # 0x1c remapped from 0x11
			_("Western"),  # 0x1d remapped from 0x12
			_("War"),  # 0x1e remapped from 0x12
			_("Action"),  # 0x1f remapped from 0x12
		),
		# News/Current Affairs
		2: (
			_("News"),  # 0x20
			_("Weather"),  # 0x21
			_("Unused %s") % "0x22",  # 0x22
			_("Documentary"),  # 0x23
		),
		# Show/Games show
		3: (
			_("Entertainment"),  # 0x30
			_("Game Show"),  # 0x31
			_("Variety"),  # 0x32
			_("Talk Show"),  # 0x33
		),
		# Sports
		4: (
			_("Sport"),  # 0x40
			_("Olympics"),  # 0x41
			_("Golf"),  # 0x42 remapped from 0x40
			_("Soccer"),  # 0x43
			_("Tennis"),  # 0x44
			_("Football"),  # 0x45
			_("Athletics"),  # 0x46
			_("Motor Sport"),  # 0x47
			_("Swimming"),  # 0x48
			_("Winter Sports"),  # 0x49
			_("Boxing"),  # 0x4a remapped from 0x40
			_("Rugby League"),  # 0x4b remapped from 0x45
			_("Rugby"),  # 0x4c remapped from 0x45
			_("Netball"),  # 0x4d remapped from 0x45
			_("Hockey"),  # 0x4e remapped from 0x45
			_("Cricket"),  # 0x4f remapped from 0x45
		),
		# Children/Youth
		5: (
			_("Children"),  # 0x50
			_("Cartoon"),  # 0x51 remapped from 0x55
			_("Unused %s") % "0x52",  # 0x52
			_("Unused %s") % "0x53",  # 0x53
			_("Unused %s") % "0x54",  # 0x54
			_("Animation"),  # 0x55
		),
		# Music/Ballet/Dance
		6: (
			_("Music"),  # 0x60
			_("Musical"),  # 0x61 remapped from 0x60
			_("Dance"),  # 0x62 remapped from 0x60
		),
		# Arts/Culture
		7: (
			_("Arts & Culture"),  # 0x70
			_("Unused %s") % "0x71",  # 0x71
			_("Unused %s") % "0x72",  # 0x72
			_("Religion"),  # 0x73
		),
		# Social/Political/Economics
		8: (
			_("Society & Culture"),  # 0x80
			_("Current Affairs"),  # 0x81
			_("Parliament"),  # 0x82 remapped from 0x80
			_("Biography"),  # 0x83
			_("Business & Finance"),  # 0x84 remapped from 0x80
		),
		# Education/Science/Factual
		9: (
			_("Education"),  # 0x90
			_("Nature"),  # 0x91
			_("Science & Tech"),  # 0x92
			_("Medical"),  # 0x93
			_("Science"),  # 0x94 remapped from 0x90
		),
		# Leisure hobbies
		10: (
			_("Infotainment"),  # 0xa0
			_("Travel"),  # 0xa1
			_("Lifestyle"),  # 0xa2 remapped from 0xa0
			_("Fishing"),  # 0xa3 remapped from 0xa0
			_("Food/Wine"),  # 0xa4 remapped from 0xa5
			_("Cooking"),  # 0xa5
			_("Shopping"),  # 0xa6
			_("Gardening"),  # 0xa7
		),
		# Special
		11: (
			_("Special"),  # 0xb0
			_("Unused %s") % "0xb1",  # 0xb1
			_("Unused %s") % "0xb2",  # 0xb2
			_("Live"),  # 0xb3
		),
		# Comedy
		12: (
			_("Comedy"),  # 0xc0
		),
		# Drama
		13: (
			_("Drama"),  # 0xd0
		),
		# Documentary
		14: (
			_("Documentary"),  # 0xe0
		),
		# Real Life
		15: (
			_("Real Life"),  # 0xf0
			_("Horror"),  # 0xf1 remapped from 0x13
			_("Fantasy"),  # 0xf2 remapped from 0x13
			_("Sitcom"),  # 0xf3 remapped from 0x14
			_("Basketball"),  # 0xf4 remapped from 0x45
			_("Baseball"),  # 0xf5 remapped from 0x45
			_("American Football"),  # 0xf6 remapped from 0x45
			_("AFL"),  # 0xf7 remapped from 0x45
			_("Rowing"),  # 0xf8 remapped from 0x48
		),
	}


def __getGenreStringMain(hn, ln, genres):
	# if hn == 0:
	# 	return _("Undefined content")
	if hn == 15:
		return _("User defined")
	if 0 < hn < len(genres.maintype):
		return genres.maintype[hn]
	# return _("Reserved") + " " + str(hn)
	return ""


def __getGenreStringSub(hn, ln, genres):
	# if hn == 0:
	# 	return _("Undefined content") + " " + str(ln)
	if hn == 15:
		return _("User defined") + " " + str(ln)
	if 0 < hn < len(genres.maintype):
		if ln == 15:
			return _("User defined")
		if ln < len(genres.subtype[hn]):
			return genres.subtype[hn][ln]
	# 	return _("Reserved") " " + str(ln)
	# return _("Reserved") + " " + str(hn) + "," + str(ln)
	return ""


def __getGenreStringMainIceTV(hn, ln, genres):
	if hn < len(genres.maintype):
		return genres.maintype[hn]
	if hn == 15:
		return _("User defined 0x%02x" % ((hn << 4) | ln))
	return ""


def __getGenreStringSubIceTV(hn, ln, genres):
	if hn in genres.subtype and ln < len(genres.subtype[hn]):
		return genres.subtype[hn][ln]
	if hn == 15 or ln == 15:
		return _("User defined 0x%02x" % ((hn << 4) | ln))
	return ""


countries = {
	"AUS": (__getGenreStringMain, __getGenreStringMain, GenresAUS()),
	# Use illegal country names for IceTV genre tables so that they won't match real countries
	"AUSIceTV": (__getGenreStringMainIceTV, __getGenreStringSubIceTV, GenresAUSIceTV()),
}

defaultGenre = GenresETSI()
defaultCountryInfo = (__getGenreStringMain, __getGenreStringSub, defaultGenre)

# Backwards compatibility - use deprecated

maintype = defaultGenre.maintype
subtype = defaultGenre.subtype


def __remapCountry(country):
	if hasattr(config.plugins, "icetv") and config.plugins.icetv.enable_epg.value:
		if not country:
			country = config.plugins.icetv.member.country.value
		iceTVCountry = f"{country}IceTV"
		if iceTVCountry in countries:
			return iceTVCountry
	return country


def getGenreStringMain(hn, ln, country=None):
	countryInfo = countries.get(__remapCountry(country), defaultCountryInfo)
	return countryInfo[0](hn, ln, countryInfo[2])


def getGenreStringSub(hn, ln, country=None):
	countryInfo = countries.get(__remapCountry(country), defaultCountryInfo)
	return countryInfo[1](hn, ln, countryInfo[2])


def getGenreStringLong(hn, ln, country=None):
	# if hn == 0:
	# 	return _("Undefined content") + " " + str(ln)
	if hn == 15 and not (hasattr(config.plugins, "icetv") and config.plugins.icetv.enable_epg.value):
		return f'{_("User defined")} {str(ln)}'
	main = getGenreStringMain(hn, ln, country=country)
	sub = getGenreStringSub(hn, ln, country=country)
	if main and main != sub:
		return f"{main}: {sub}"
	else:
		return main
# 	return _("Reserved") + " " + str(hn) + "," + str(ln)

#
# The End
#
