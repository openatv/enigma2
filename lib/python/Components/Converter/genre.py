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
		_("News/Current affairs"),
		_("Show/Game show"),
		_("Sports"),
		_("Children/Youth"),
		_("Music/Ballet/Dance"),
		_("Arts/Culture"),
		_("Social/Political/Economics"),
		_("Education/Science/Factual"),
		_("Leisure hobbies"),
		_("Special characteristics")
	)

	subtype = {
		# Movie/Drama
		1: (
			_("movie/drama (general)"),
			_("Detective/Thriller"),
			_("Adventure/Western/War"),
			_("Science fiction/Fantasy/Horror"),
			_("Comedy"),
			_("Soap/Melodrama/Folkloric"),
			_("Romance"),
			_("Serious/Classical/Religious/Historical/Drama"),
			_("Adult movie/Drama")
		),
		# News/Current Affairs
		2: (
			_("News/Current affairs"),
			_("News/Weather report"),
			_("News magazine"),
			_("Documentary"),
			_("Discussion/Interview/Debate")
		),
		# Show/Game show
		3: (
			_("Show/Game show"),
			_("Game show/Quiz/Contest"),
			_("Variety show"),
			_("Talk show")
		),
		# Sports
		4: (
			_("Sports"),
			_("special events"),
			_("Sports magazines"),
			_("Football/Soccer"),
			_("Tennis/Squash"),
			_("team sports"),
			_("Athletics"),
			_("Motor sport"),
			_("Water sport"),
			_("Winter sport"),
			_("Equestrian"),
			_("Martial sports")
		),
		# Children/Youth
		5: (
			_("children's/youth program (general)"),
			_("pre-school children's program"),
			_("entertainment (6-14 year old)"),
			_("entertainment (10-16 year old)"),
			_("information/education/school program"),
			_("Cartoons/Puppets")
		),
		# Music/Ballet/Dance
		6: (
			_("Music/Ballet/Dance"),
			_("Rock/Pop"),
			_("Serious music/Classic music"),
			_("Folk/Traditional music"),
			_("Jazz"),
			_("Musical/Opera"),
			_("Ballet")
		),
		# Arts/Culture
		7: (
			_("arts/culture (without music, general)"),
			_("Performing arts"),
			_("Fine arts"),
			_("Religion"),
			_("Popular culture/Traditional arts"),
			_("Literature"),
			_("Film/Cinema"),
			_("Experimental film/video"),
			_("Broadcasting/Press"),
			_("New media"),
			_("Arts/Culture magazines"),
			_("Fashion")
		),
		# Social/Political/Economics
		8: (
			_("social/political issues/economics (general)"),
			_("Magazines/Reports/Documentary"),
			_("Economics/Social advisory"),
			_("Remarkable people")
		),
		# Education/Science/...
		9: (
			_("Education/Science/Factual"),
			_("Nature/Animals/Environment"),
			_("Technology/Natural sciences"),
			_("Medicine/Physiology/Psychology"),
			_("Foreign countries/Expeditions"),
			_("Social/Spiritual sciences"),
			_("Further education"),
			_("Languages")
		),

		# Leisure hobbies
		10: (
			_("Leisure hobbies"),
			_("Tourism/Travel"),
			_("Handicraft"),
			_("Motoring"),
			_("Fitness and Health"),
			_("Cooking"),
			_("Advertisement/Shopping"),
			_("Gardening")
		),
		# Special characteristics
		11: (
			_("Original language"),
			_("Black & White"),
			_("Unpublished"),
			_("Live broadcast")
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
		_("Current affairs"),
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
		_("News/Current affairs"),
		_("Show/Game show"),
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
		_("Real life"),
	)

	subtype = {
		# Miscellaneous
		0: (
			_(""),  # 0x00
			_("Cult"),  # 0x01
			_("Youth"),  # 0x02 remapped from 0x01
			_("Wrestling"),  # 0x03 remapped from 0x01
			_("Violence"),  # 0x04 remapped from 0x01
			_("Short film"),  # 0x05 remapped from 0x01
			_("Sailing"),  # 0x06 remapped from 0x01
			_("Renovation"),  # 0x07 remapped from 0x01
			_("Mini series"),  # 0x08 remapped from 0x01
			_("MMA"),  # 0x09 remapped from 0x01
			_("Horse racing"),  # 0x0a remapped from 0x01
			_("Finance"),  # 0x0b remapped from 0x01
			_("Film-noir"),  # 0x0c remapped from 0x01
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
			_("Soap opera"),  # 0x15
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
			_("Game show"),  # 0x31
			_("Variety"),  # 0x32
			_("Talk show"),  # 0x33
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
			_("Motor sport"),  # 0x47
			_("Swimming"),  # 0x48
			_("Winter sport"),  # 0x49
			_("Boxing"),  # 0x4a remapped from 0x40
			_("Rugby league"),  # 0x4b remapped from 0x45
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
			_("Arts/Culture"),  # 0x70
			_("Unused %s") % "0x71",  # 0x71
			_("Unused %s") % "0x72",  # 0x72
			_("Religion"),  # 0x73
		),
		# Social/Political/Economics
		8: (
			_("Society & Culture"),  # 0x80
			_("Current affairs"),  # 0x81
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
			_("Real life"),  # 0xf0
			_("Horror"),  # 0xf1 remapped from 0x13
			_("Fantasy"),  # 0xf2 remapped from 0x13
			_("Sitcom"),  # 0xf3 remapped from 0x14
			_("Basketball"),  # 0xf4 remapped from 0x45
			_("Baseball"),  # 0xf5 remapped from 0x45
			_("American football"),  # 0xf6 remapped from 0x45
			_("AFL"),  # 0xf7 remapped from 0x45
			_("Rowing"),  # 0xf8 remapped from 0x48
		),
	}


class GenresGBROpenTV:
	maintype = (
		_("General"),  # 0x0
		_("General"),  # 0x1
		_("General"),  # 0x2
		_("General"),  # 0x3
		_("Children"),  # 0x4
		_("Children"),  # 0x5
		_("Entertainment"),  # 0x6
		_("Entertainment"),  # 0x7
		_("Music"),  # 0x8
		_("Music"),  # 0x9
		_("News/Documentary"),  # 0xa
		_("News/Documentary"),  # 0xb
		_("Movie"),  # 0xc
		_("Movie"),  # 0xd
		_("Sports"),  # 0xe
		_("Sports"),  # 0xf
	)

	subtype = {
		# General
		0: (
			_("No Category"),  # 0x00
		),
		# General
		2: (
			_("No Category"),  # 0x20
			_("Adult"),  # 0x21
			_("Unused %s") % "0x22",  # 0x22
			_("Shopping"),  # 0x23
		),
		# Children
		4: (
			_("General"),  # 0x40
			_("Cartoons"),  # 0x41
			_("Comedy"),  # 0x42
			_("Drama"),  # 0x43
			_("Educational"),  # 0x44
			_("Under 5"),  # 0x45
			_("Factual"),  # 0x46
			_("Magazine"),  # 0x47
		),
		# Entertainment
		6: (
			_("General"),  # 0x60
			_("Action"),  # 0x61
			_("Comedy"),  # 0x62
			_("Detective"),  # 0x63
			_("Drama"),  # 0x64
			_("Game show"),  # 0x65
			_("Sci-FI"),  # 0x66
			_("Soap"),  # 0x67
			_("Animation"),  # 0x68
			_("Chat Show"),  # 0x69
			_("Cooking"),  # 0x6a
			_("Factual"),  # 0x6b
			_("Fashion"),  # 0x6c
			_("Home and Garden"),  # 0x6d
			_("Travel"),  # 0x6e
			_("Technology"),  # 0x6f
		),
		# Entertainment cont...
		7: (
			_("Arts"),  # 0x70
			_("Lifestyle"),  # 0x71
			_("Home"),  # 0x72
			_("Magazine"),  # 0x73
			_("Medical"),  # 0x74
			_("Review"),  # 0x75
			_("Antiques"),  # 0x76
			_("Motors"),  # 0x77
			_("Art/Literature"),  # 0x78
			_("Ballet"),  # 0x79
			_("Opera"),  # 0x7a
		),
		# Music
		8: (
			_("General"),  # 0x80
			_("Classical"),  # 0x81
			_("Folk and Country"),  # 0x82
			_("National Music"),  # 0x83
			_("Jazz"),  # 0x84
			_("Opera"),  # 0x85
			_("Rock/Pop"),  # 0x86
			_("Alternative"),  # 0x87
			_("Events"),  # 0x88
			_("Club/Dance"),  # 0x89
			_("Hip Hop"),  # 0x8a
			_("Soul/Rhythm Blues"),  # 0x8b
			_("Dance"),  # 0x8c
			_("Unused %s") % "0x8d",  # 0x8d
			_("Unused %s") % "0x8e",  # 0x8e
			_("Unused %s") % "0x8f",  # 0x8f
		),
		# Music cont...
		9: (
			_("Features"),  # 0x90
			_("Unused %s") % "0x91",  # 0x91
			_("Unused %s") % "0x92",  # 0x92
			_("Unused %s") % "0x93",  # 0x93
			_("Unused %s") % "0x94",  # 0x94
			_("Lifestyle"),  # 0x95
			_("News and Weather"),  # 0x96
			_("Easy Listening"),  # 0x97
			_("Discussion"),  # 0x98
			_("Entertainment"),  # 0x99
			_("Religious"),  # 0x9a
		),
		# News/Documentary
		10: (
			_("General"),  # 0xa0
			_("Business"),  # 0xa1
			_("World Cultures"),  # 0xa2
			_("Adventure"),  # 0xa3
			_("Biography"),  # 0xa4
			_("Educational"),  # 0xa5
			_("Feature"),  # 0xa6
			_("Politics"),  # 0xa7
			_("News"),  # 0xa8
			_("Nature"),  # 0xa9
			_("Religious"),  # 0xaa
			_("Science"),  # 0xab
			_("Showbiz"),  # 0xac
			_("War"),  # 0xad
			_("Historical"),  # 0xae
			_("Ancient"),  # 0xaf
		),
		# News/Documentary cont...
		11: (
			_("Transport"),  # 0xb0
			_("Docudrama"),  # 0xb1
			_("World Affairs"),  # 0xb2
			_("Events"),  # 0xb3
			_("Entertainment"),  # 0xb4
		),
		# Movie
		12: (
			_("General"),  # 0xc0
			_("Action"),  # 0xc1
			_("Animation"),  # 0xc2
			_("Unused %s") % "0xc3",  # 0xc3
			_("Comedy"),  # 0xc4
			_("Family"),  # 0xc5
			_("Drama"),  # 0xc6
			_("Unused %s") % "0xc7",  # 0xc7
			_("Sci-Fi"),  # 0xc8
			_("Thriller"),  # 0xc9
			_("Horror"),  # 0xca
			_("Romance"),  # 0xcb
			_("Musical"),  # 0xcc
			_("Mystery"),  # 0xcd
			_("Western"),  # 0xce
			_("Factual"),  # 0xcf
		),
		# Movie cont...
		13: (
			_("Fantasy"),  # 0xd0
			_("Erotic"),  # 0xd1
			_("Adventure"),  # 0xd2
			_("War"),  # 0xd3
		),
		# Sports
		14: (
			_("General"),  # 0xe0
			_("American football"),  # 0xe1
			_("Athletics"),  # 0xe2
			_("Baseball"),  # 0xe3
			_("Basketball"),  # 0xe4
			_("Boxing"),  # 0xe5
			_("Cricket"),  # 0xe6
			_("Fishing"),  # 0xe7
			_("Football"),  # 0xe8
			_("Golf"),  # 0xe9
			_("Ice Hockey"),  # 0xea
			_("Motor sport"),  # 0xeb
			_("Racing"),  # 0xec
			_("Rugby"),  # 0xed
			_("Equestrian"),  # 0xee
			_("Winter sport"),  # 0xef
		),
		# Sports cont...
		15: (
			_("Snooker/Pool"),  # 0xf0
			_("Tennis"),  # 0xf1
			_("Wrestling"),  # 0xf2
			_("Darts"),  # 0xf3
			_("Watersports"),  # 0xf4
			_("Extreme"),  # 0xf5
		),
	}


class GenresITAOpenTV:
	maintype = (
		"Generale",  # 0x0
		"Generale",  # 0x1
		"Intrattenimento",  # 0x2
		"Intrattenimento",  # 0x3
		"Sport",  # 0x4
		"Sport",  # 0x5
		"Film",  # 0x6
		"Film",  # 0x7
		"Mondo e Tendenze",  # 0x8
		"Mondo e Tendenze",  # 0x9
		"Informazione",  # 0xa
		"Informazione",  # 0xb
		"Ragazzi e Musica",  # 0xc
		"Ragazzi e Musica",  # 0xd
		"Altri Programmi",  # 0xe
		"Altri Programmi",  # 0xf
	)

	subtype = {
		# Generale
		0: (
			"Non Definito",  # 0x00
		),
		# Intrattenimento
		2: (
			"Generale",  # 0x20
			"Fiction",  # 0x21
			"Sit Com",  # 0x22
			"Show",  # 0x23
			"Telefilm",  # 0x24
			"Soap opera",  # 0x25
			"Telenovela",  # 0x26
			"Fantascienza",  # 0x27
			"Animazione",  # 0x28
			"Giallo",  # 0x29
			"Drammatico",  # 0x2a
			"Romantico",  # 0x2b
			"Miniserie",  # 0x2c
			"Spettacolo",  # 0x2d
			"Quiz",  # 0x2e
			"Talk show",  # 0x2f
		),
		# Intrattenimento cont..
		3: (
			"Varieta",  # 0x30
			"Festival",  # 0x31
			"Teatro",  # 0x32
			"Gioco",  # 0x33
		),
		# Sport
		4: (
			"Generale",  # 0x40
			"Calcio",  # 0x41
			"Tennis",  # 0x42
			"Motori",  # 0x43
			"Altri",  # 0x44
			"Baseball",  # 0x45
			"Ciclismo",  # 0x46
			"Rugby",  # 0x47
			"Basket",  # 0x48
			"Boxe",  # 0x49
			"Atletica",  # 0x4a
			"Football USA",  # 0x4b
			"Hockey",  # 0x4c
			"Sci",  # 0x4d
			"Equestri",  # 0x4e
			"Golf",  # 0x4f
		),
		# Sport cont..
		5: (
			"Nuoto",  # 0x50
			"Wrestling",  # 0x51
		),
		# Film
		6: (
			"Generale",  # 0x60
			"Drammatico",  # 0x61
			"Commedia",  # 0x62
			"Romantico",  # 0x63
			"Azione",  # 0x64
			"Fantascienza",  # 0x65
			"Western",  # 0x66
			"Comico",  # 0x67
			"Fantastico",  # 0x68
			"Avventura",  # 0x69
			"Poliziesco",  # 0x6a
			"Guerra",  # 0x6b
			"Horror",  # 0x6c
			"Animazione",  # 0x6d
			"Thriller",  # 0x6e
			"Musicale",  # 0x6f
		),
		# Film cont..
		7: (
			"Corto",  # 0x70
			"Cortometraggio",  # 0x71
		),
		# Mondo e Tendenze
		8: (
			"Generale",  # 0x80
			"Natura",  # 0x81
			"Arte e Cultura",  # 0x82
			"Lifestyle",  # 0x83
			"Viaggi",  # 0x84
			"Documentario",  # 0x85
			"Societa",  # 0x86
			"Scienza",  # 0x87
			"Storia",  # 0x88
			"Sport",  # 0x89
			"Pesca",  # 0x8a
			"Popoli",  # 0x8b
			"Cinema",  # 0x8c
			"Musica",  # 0x8d
			"Hobby",  # 0x8e
			"Caccia",  # 0x8f
		),
		# Mondo e Tendenze cont..
		9: (
			"Reportage",  # 0x90
			"Magazine",  # 0x91
			"Magazine Cultura",  # 0x92
			"Magazine Scienza",  # 0x93
			"Politica",  # 0x94
			"Magazine Cinema",  # 0x95
			"Magazine Sport",  # 0x96
			"Attualita",  # 0x97
			"Moda",  # 0x98
			"Economia",  # 0x99
			"Magazine Caccia e Pesca",  # 0x9a
			"Magazine Viaggi",  # 0x9b
			"Magazine Natura",  # 0x9c
			"Magazine Musica",  # 0x9d
			"Religione",  # 0x9e
			"Televendita",  # 0x9f
		),
		# Informazione
		10: (
			"Generale",  # 0xa0
			"Notiziario",  # 0xa1
			"Sport",  # 0xa2
			"Economia",  # 0xa3
		),
		# Ragazzi e Musica
		12: (
			"Generale",  # 0xc0
			"Bambini",  # 0xc1
			"Ragazzi",  # 0xc2
			"Cartoni Animati",  # 0xc3
			"Musica",  # 0xc4
			"Film Animazione",  # 0xc5
			"Film",  # 0xc6
			"Telefilm",  # 0xc7
			"Magazine",  # 0xc8
			"Inutilizzato 0xc9",  # 0xc9
			"Inutilizzato 0xca",  # 0xca
			"Inutilizzato 0xcb",  # 0xcb
			"Inutilizzato 0xcc",  # 0xcc
			"Inutilizzato 0xcd",  # 0xcd
			"Inutilizzato 0xce",  # 0xce
			"Inutilizzato 0xcf",  # 0xcf
		),
		# Ragazzi e Musica cont..
		13: (
			"Inutilizzato 0xd0",  # 0xd0
			"Inutilizzato 0xd1",  # 0xd1
			"Inutilizzato 0xd2",  # 0xd2
			"Inutilizzato 0xd3",  # 0xd3
			"Danza",  # 0xd4
		),
		# Altri Programmi
		14: (
			"Generale",  # 0xe0
			"Educational",  # 0xe1
			"Regionale",  # 0xe2
			"Shopping",  # 0xe3
			"Inutilizzato 0xe4",  # 0xe4
			"Inizio e Fine Trasmissioni",  # 0xe5
			"Eventi Speciali",  # 0xe6
			"Film per Adulti",  # 0xe7
		),
	}


class GenresETSIOpenTV:
	# TODO: "OTV": "ETSI
	maintype = (
		_("General"),  # 0x0
	)

	subtype = {
		0: (
			_("No Category"),  # 0x00
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


def __getGenreStringMainOpenTV(hn, ln, genres):
	if hn < len(genres.maintype):
		return genres.maintype[hn]
	return ""


def __getGenreStringSubOpenTV(hn, ln, genres):
	if hn in genres.subtype:
		if ln < len(genres.subtype[hn]):
			return genres.subtype[hn][ln]
		return _("User defined 0x%02x" % ((hn << 4) | ln))
	return ""


countries = {
	"AUS": (__getGenreStringMain, __getGenreStringMain, GenresAUS()),
	# Use illegal country names for IceTV genre tables so that they won't match real countries
	"AUSIceTV": (__getGenreStringMainIceTV, __getGenreStringSubIceTV, GenresAUSIceTV()),
	"GBROpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresGBROpenTV()),
	"ITAOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresITAOpenTV()),
	"ETSIOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresETSIOpenTV())
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
