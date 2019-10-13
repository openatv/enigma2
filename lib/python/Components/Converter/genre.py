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
		_("Childrens"),
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
			_("childrens (general)"),
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
			_("Unused 0x22"),  # 0x22
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
			_("Unused 0x52"),  # 0x52
			_("Unused 0x53"),  # 0x53
			_("Unused 0x54"),  # 0x54
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
			_("Unused 0x71"),  # 0x71
			_("Unused 0x72"),  # 0x72
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
			_("Unused 0xb1"),  # 0xb1
			_("Unused 0xb2"),  # 0xb2
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

class GenresDEUIceTV:
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
			'',  # 0x00
			_('Abenteuer'),  # 0x01
			_('Zirkus'),  # 0x02 remapped from 0x01
			_('Zeichentrick'),  # 0x03 remapped from 0x01
			_('Wissenschaft'),  # 0x04 remapped from 0x01
			_('Wirtschaft'),  # 0x05 remapped from 0x01
			_('Wintersport'),  # 0x06 remapped from 0x01
			_('Wetter'),  # 0x07 remapped from 0x01
			_('Wettbewerb'),  # 0x08 remapped from 0x01
			_('Western'),  # 0x09 remapped from 0x01
			_('Werbung'),  # 0x0a remapped from 0x01
			_('Wassersport'),  # 0x0b remapped from 0x01
			_('Waffen'),  # 0x0c remapped from 0x01
			_('Vorschau'),  # 0x0d remapped from 0x01
			_('Videoclip'),  # 0x0e remapped from 0x01
			_('Verschiedenes'),  # 0x0f remapped from 0x01
		),
		# Movie/Drama
		1: (
			_('Kunst'),  # 0x10 remapped from 0x01
			_('Kultur'),  # 0x11 remapped from 0x01
			_('Kriminalit\xc3\xa4t'),  # 0x12 remapped from 0x01
			_('Krimi'),  # 0x13 remapped from 0x01
			_('Comedy'),  # 0x14
			_('Krieg'),  # 0x15 remapped from 0x01
			_('Kraftsport'),  # 0x16 remapped from 0x01
			_('Kom\xc3\xb6die'),  # 0x17 remapped from 0x01
			_('Kneipensport'),  # 0x18 remapped from 0x01
			_('Klassiker'),  # 0x19 remapped from 0x01
			_('Kinder'),  # 0x1a remapped from 0x01
			_('Katastrophe'),  # 0x1b remapped from 0x01
			_('Kampfsport'),  # 0x1c remapped from 0x01
			_('Justiz'),  # 0x1d remapped from 0x01
			_('Jugend'),  # 0x1e remapped from 0x01
			_('International'),  # 0x1f remapped from 0x01
		),
		# News/Current Affairs
		2: (
			_('Information'),  # 0x20 remapped from 0x01
			_('Independent'),  # 0x21 remapped from 0x01
			_('Horror'),  # 0x22 remapped from 0x01
			_('Hobbys'),  # 0x23 remapped from 0x01
			_('Heimwerker'),  # 0x24 remapped from 0x01
			_('Heimat'),  # 0x25 remapped from 0x01
			_('Handball'),  # 0x26 remapped from 0x01
			_('Gesundheit'),  # 0x27 remapped from 0x01
			_('Gesellschaft'),  # 0x28 remapped from 0x01
			_('Geschichte'),  # 0x29 remapped from 0x01
			_('Garten'),  # 0x2a remapped from 0x01
			_('Gangster'),  # 0x2b remapped from 0x01
			_('F\xc3\xbcr Kinder'),  # 0x2c remapped from 0x01
			_('Fu\xc3\x9fball'),  # 0x2d remapped from 0x01
			_('Frauen'),  # 0x2e remapped from 0x01
			_('Fantasy'),  # 0x2f remapped from 0x01
		),
		# Show/Games show
		3: (
			_('Familie'),  # 0x30 remapped from 0x01
			_('Extremsport'),  # 0x31 remapped from 0x01
			_('Event'),  # 0x32 remapped from 0x01
			_('Essen'),  # 0x33 remapped from 0x01
			_('Esoterik'),  # 0x34 remapped from 0x01
			_('Erotik'),  # 0x35 remapped from 0x01
			_('Epos'),  # 0x36 remapped from 0x01
			_('Energie'),  # 0x37 remapped from 0x01
			_('Einzelsportart'),  # 0x38 remapped from 0x01
			_('Eastern'),  # 0x39 remapped from 0x01
			_('Drogen'),  # 0x3a remapped from 0x01
			_('Drama'),  # 0x3b remapped from 0x01
			_('Dokumentation'),  # 0x3c remapped from 0x01
			_('Detektiv'),  # 0x3d remapped from 0x01
			_('Dating'),  # 0x3e remapped from 0x01
			_('Computer'),  # 0x3f remapped from 0x01
		),
		# Sports
		4: (
			_('Sport'),  # 0x40
			_('Comic'),  # 0x41 remapped from 0x01
			_('Chronik'),  # 0x42 remapped from 0x01
			_('Casting'),  # 0x43 remapped from 0x01
			_('Call-in'),  # 0x44 remapped from 0x01
			_('Boxen'),  # 0x45 remapped from 0x01
			_('Boulevard'),  # 0x46 remapped from 0x01
			_('Bollywood'),  # 0x47 remapped from 0x01
			_('Biografie'),  # 0x48 remapped from 0x01
			_('Bildung'),  # 0x49 remapped from 0x01
			_('Beziehung'),  # 0x4a remapped from 0x01
			_('Berufe'),  # 0x4b remapped from 0x01
			_('Bericht'),  # 0x4c remapped from 0x01
			_('B-Movie'),  # 0x4d remapped from 0x01
			_('Automobil'),  # 0x4e remapped from 0x01
			_('Arzt'),  # 0x4f remapped from 0x01
		),
		# Children/Youth
		5: (
			_('Architektur'),  # 0x50 remapped from 0x01
			_('Anime'),  # 0x51 remapped from 0x01
			_('American Sports'),  # 0x52 remapped from 0x01
			_('Agenten'),  # 0x53 remapped from 0x01
			_('Adel'),  # 0x54 remapped from 0x01
			_('Animation'),  # 0x55
			_('Action'),  # 0x56 remapped from 0x01
		),
		# Social/Political/Economics
		8: (
			_('Unused 0x80'),  # 0x80
			_('Current Affairs'),  # 0x81
		),
		# Special
		11: (
			_('Special'),  # 0xb0
		),
		# Comedy
		12: (
			_('Comedy'),  # 0xc0
			_('Show'),  # 0xc1 remapped from 0x01
			_('Serie'),  # 0xc2 remapped from 0x01
			_('Science-Fiction'),  # 0xc3 remapped from 0x01
			_('Satire'),  # 0xc4 remapped from 0x01
			_('Saga'),  # 0xc5 remapped from 0x01
			_('Romantik'),  # 0xc6 remapped from 0x01
			_('Revue'),  # 0xc7 remapped from 0x01
			_('Reportage'),  # 0xc8 remapped from 0x01
			_('Religion'),  # 0xc9 remapped from 0x01
			_('Reiten'),  # 0xca remapped from 0x01
			_('Reisen'),  # 0xcb remapped from 0x01
			_('Regional'),  # 0xcc remapped from 0x01
			_('Reality'),  # 0xcd remapped from 0x01
			_('Radsport'),  # 0xce remapped from 0x01
			_('Quiz'),  # 0xcf remapped from 0x01
		),
		# Drama
		13: (
			_('Drama'),  # 0xd0
			_('Puppentrick'),  # 0xd1 remapped from 0x01
			_('Psychologie'),  # 0xd2 remapped from 0x01
			_('Prominent'),  # 0xd3 remapped from 0x01
			_('Portr\xc3\xa4t'),  # 0xd4 remapped from 0x01
			_('Politik'),  # 0xd5 remapped from 0x01
			_('Poker'),  # 0xd6 remapped from 0x01
			_('Parodie'),  # 0xd7 remapped from 0x01
			_('Parabel'),  # 0xd8 remapped from 0x01
			_('Outdoor'),  # 0xd9 remapped from 0x01
			_('Olympia'),  # 0xda remapped from 0x01
			_('Neue Medien'),  # 0xdb remapped from 0x01
			_('Natur'),  # 0xdc remapped from 0x01
			_('National'),  # 0xdd remapped from 0x01
			_('Nachrichten'),  # 0xde remapped from 0x01
			_('M\xc3\xa4rchen'),  # 0xdf remapped from 0x01
		),
		# Documentary
		14: (
			_('Documentary'),  # 0xe0
			_('Mystery'),  # 0xe1 remapped from 0x01
			_('Musik'),  # 0xe2 remapped from 0x01
			_('Musical'),  # 0xe3 remapped from 0x01
			_('Motorsport'),  # 0xe4 remapped from 0x01
			_('Mode'),  # 0xe5 remapped from 0x01
			_('Medien'),  # 0xe6 remapped from 0x01
			_('Mannschaftssport'),  # 0xe7 remapped from 0x01
			_('Magazin'),  # 0xe8 remapped from 0x01
			_('Literaturverfilmung'),  # 0xe9 remapped from 0x01
			_('Literatur'),  # 0xea remapped from 0x01
			_('Lifestyle'),  # 0xeb remapped from 0x01
			_('Leichtathletik'),  # 0xec remapped from 0x01
			_('Late Night'),  # 0xed remapped from 0x01
			_('Landestypisch'),  # 0xee remapped from 0x01
			_('Kurzfilm'),  # 0xef remapped from 0x01
		),
		# Real Life
		15: (
			_('Verkehr'),  # 0xf0 remapped from 0x01
			_('Unterhaltung'),  # 0xf1 remapped from 0x01
			_('Umweltbewusstsein'),  # 0xf2 remapped from 0x01
			_('Trag\xc3\xb6die'),  # 0xf3 remapped from 0x01
			_('Tiere'),  # 0xf4 remapped from 0x01
			_('Thriller'),  # 0xf5 remapped from 0x01
			_('Theater'),  # 0xf6 remapped from 0x01
			_('Technik'),  # 0xf7 remapped from 0x01
			_('Tanz'),  # 0xf8 remapped from 0x01
			_('Talk'),  # 0xf9 remapped from 0x01
			_('Stumm'),  # 0xfa remapped from 0x01
			_('Sprache'),  # 0xfb remapped from 0x01
			_('Spielfilm'),  # 0xfc remapped from 0x01
			_('Spiele'),  # 0xfd remapped from 0x01
			_('Soap'),  # 0xfe remapped from 0x01
			_('Slapstick'),  # 0xff remapped from 0x01
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
	"DEUIceTV": (__getGenreStringMainIceTV, __getGenreStringSubIceTV, GenresDEUIceTV()),
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
		iceTVCountry = country + "IceTV"
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
		return _("User defined") + " " + str(ln)
	main = getGenreStringMain(hn, ln, country=country)
	sub = getGenreStringSub(hn, ln, country=country)
	if main and main != sub:
		return main + ": " + sub
	else:
		return main
# 	return _("Reserved") + " " + str(hn) + "," + str(ln)

#
# The End
#
