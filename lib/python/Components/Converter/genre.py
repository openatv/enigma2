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
class GenresGBROpenTV:
	maintype=(
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

	subtype={
		# General
		0: (
			_("No Category"),  # 0x00
		),
		# General
		2: (
			_("No Category"),  # 0x20
			_("Adult"),  # 0x21
			_("Unused 0x22"),  # 0x22
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
			_("Game Show"),  # 0x65
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
			_("Unused 0x8d"),  # 0x8d
			_("Unused 0x8e"),  # 0x8e
			_("Unused 0x8f"),  # 0x8f
		),
		# Music cont...
		9: (
			_("Features"),  # 0x90
			_("Unused 0x91"),  # 0x91
			_("Unused 0x92"),  # 0x92
			_("Unused 0x93"),  # 0x93
			_("Unused 0x94"),  # 0x94
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
			_("Unused 0xc3"),  # 0xc3
			_("Comedy"),  # 0xc4
			_("Family"),  # 0xc5
			_("Drama"),  # 0xc6
			_("Unused 0xc7"),  # 0xc7
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
			_("American Football"),  # 0xe1
			_("Athletics"),  # 0xe2
			_("Baseball"),  # 0xe3
			_("Basketball"),  # 0xe4
			_("Boxing"),  # 0xe5
			_("Cricket"),  # 0xe6
			_("Fishing"),  # 0xe7
			_("Football"),  # 0xe8
			_("Golf"),  # 0xe9
			_("Ice Hockey"),  # 0xea
			_("Motor Sport"),  # 0xeb
			_("Racing"),  # 0xec
			_("Rugby"),  # 0xed
			_("Equestrian"),  # 0xee
			_("Winter Sports"),  # 0xef
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
	maintype=(
		_("Generale"),  # 0x0
		_("Generale"),  # 0x1
		_("Intrattenimento"),  # 0x2
		_("Intrattenimento"),  # 0x3
		_("Sport"),  # 0x4
		_("Sport"),  # 0x5
		_("Film"),  # 0x6
		_("Film"),  # 0x7
		_("Mondo e Tendenze"),  # 0x8
		_("Mondo e Tendenze"),  # 0x9
		_("Informazione"),  # 0xa
		_("Informazione"),  # 0xb
		_("Ragazzi e Musica"),  # 0xc
		_("Ragazzi e Musica"),  # 0xd
		_("Altri Programmi"),  # 0xe
		_("Altri Programmi"),  # 0xf
	)

	subtype={
		# Generale
		0: (
			_("Non Definito"),  # 0x00
		),
		# Intrattenimento
		2: (
			_("Generale"),  # 0x20
			_("Fiction"),  # 0x21
			_("Sit Com"),  # 0x22
			_("Show"),  # 0x23
			_("Telefilm"),  # 0x24
			_("Soap Opera"),  # 0x25
			_("Telenovela"),  # 0x26
			_("Fantascienza"),  # 0x27
			_("Animazione"),  # 0x28
			_("Giallo"),  # 0x29
			_("Drammatico"),  # 0x2a
			_("Romantico"),  # 0x2b
			_("Miniserie"),  # 0x2c
			_("Spettacolo"),  # 0x2d
			_("Quiz"),  # 0x2e
			_("Talk Show"),  # 0x2f
		),
		# Intrattenimento cont..
		3: (
			_("Varieta"),  # 0x30
			_("Festival"),  # 0x31
			_("Teatro"),  # 0x32
			_("Gioco"),  # 0x33
		),
		# Sport
		4: (
			_("Generale"),  # 0x40
			_("Calcio"),  # 0x41
			_("Tennis"),  # 0x42
			_("Motori"),  # 0x43
			_("Altri"),  # 0x44
			_("Baseball"),  # 0x45
			_("Ciclismo"),  # 0x46
			_("Rugby"),  # 0x47
			_("Basket"),  # 0x48
			_("Boxe"),  # 0x49
			_("Atletica"),  # 0x4a
			_("Football USA"),  # 0x4b
			_("Hockey"),  # 0x4c
			_("Sci"),  # 0x4d
			_("Equestri"),  # 0x4e
			_("Golf"),  # 0x4f
		),
		# Sport cont..
		5: (
			_("Nuoto"),  # 0x50
			_("Wrestling"),  # 0x51
		),
		# Film
		6: (
			_("Generale"),  # 0x60
			_("Drammatico"),  # 0x61
			_("Commedia"),  # 0x62
			_("Romantico"),  # 0x63
			_("Azione"),  # 0x64
			_("Fantascienza"),  # 0x65
			_("Western"),  # 0x66
			_("Comico"),  # 0x67
			_("Fantastico"),  # 0x68
			_("Avventura"),  # 0x69
			_("Poliziesco"),  # 0x6a
			_("Guerra"),  # 0x6b
			_("Horror"),  # 0x6c
			_("Animazione"),  # 0x6d
			_("Thriller"),  # 0x6e
			_("Musicale"),  # 0x6f
		),
		# Film cont..
		7: (
			_("Corto"),  # 0x70
			_("Cortometraggio"),  # 0x71
		),
		# Mondo e Tendenze
		8: (
			_("Generale"),  # 0x80
			_("Natura"),  # 0x81
			_("Arte e Cultura"),  # 0x82
			_("Lifestyle"),  # 0x83
			_("Viaggi"),  # 0x84
			_("Documentario"),  # 0x85
			_("Societa"),  # 0x86
			_("Scienza"),  # 0x87
			_("Storia"),  # 0x88
			_("Sport"),  # 0x89
			_("Pesca"),  # 0x8a
			_("Popoli"),  # 0x8b
			_("Cinema"),  # 0x8c
			_("Musica"),  # 0x8d
			_("Hobby"),  # 0x8e
			_("Caccia"),  # 0x8f
		),
		# Mondo e Tendenze cont..
		9: (
			_("Reportage"),  # 0x90
			_("Magazine"),  # 0x91
			_("Magazine Cultura"),  # 0x92
			_("Magazine Scienza"),  # 0x93
			_("Politica"),  # 0x94
			_("Magazine Cinema"),  # 0x95
			_("Magazine Sport"),  # 0x96
			_("Attualita"),  # 0x97
			_("Moda"),  # 0x98
			_("Economia"),  # 0x99
			_("Magazine Caccia e Pesca"),  # 0x9a
			_("Magazine Viaggi"),  # 0x9b
			_("Magazine Natura"),  # 0x9c
			_("Magazine Musica"),  # 0x9d
			_("Religione"),  # 0x9e
			_("Televendita"),  # 0x9f
		),
		# Informazione
		10: (
			_("Generale"),  # 0xa0
			_("Notiziario"),  # 0xa1
			_("Sport"),  # 0xa2
			_("Economia"),  # 0xa3
		),
		# Ragazzi e Musica
		12: (
			_("Generale"),  # 0xc0
			_("Bambini"),  # 0xc1
			_("Ragazzi"),  # 0xc2
			_("Cartoni Animati"),  # 0xc3
			_("Musica"),  # 0xc4
			_("Film Animazione"),  # 0xc5
			_("Film"),  # 0xc6
			_("Telefilm"),  # 0xc7
			_("Magazine"),  # 0xc8
			_("Inutilizzato 0xc9"),  # 0xc9
			_("Inutilizzato 0xca"),  # 0xca
			_("Inutilizzato 0xcb"),  # 0xcb
			_("Inutilizzato 0xcc"),  # 0xcc
			_("Inutilizzato 0xcd"),  # 0xcd
			_("Inutilizzato 0xce"),  # 0xce
			_("Inutilizzato 0xcf"),  # 0xcf
		),
		# Ragazzi e Musica cont..
		13: (
			_("Inutilizzato 0xd0"),  # 0xd0
			_("Inutilizzato 0xd1"),  # 0xd1
			_("Inutilizzato 0xd2"),  # 0xd2
			_("Inutilizzato 0xd3"),  # 0xd3
			_("Danza"),  # 0xd4
		),
		# Altri Programmi
		14: (
			_("Generale"),  # 0xe0
			_("Educational"),  # 0xe1
			_("Regionale"),  # 0xe2
			_("Shopping"),  # 0xe3
			_("Inutilizzato 0xe4"),  # 0xe4
			_("Inizio e Fine Trasmissioni"),  # 0xe5
			_("Eventi Speciali"),  # 0xe6
			_("Film per Adulti"),  # 0xe7
		),
	}
class GenresAUSOpenTV:
	# TODO: "OT3": "AUS"
	maintype=(
		_("General"),  # 0x0
	)

	subtype={
		0: (
			_("No Category"),  # 0x00
		),
	}


class GenresNZLOpenTV:
	# TODO: "OT4": "NZL"
	maintype=(
		_("General"),  # 0x0
	)

	subtype={
		0: (
			_("No Category"),  # 0x00
		),
	}


class GenresETSIOpenTV:
	# TODO: "OTV": "ETSI
	maintype=(
		_("General"),  # 0x0
	)

	subtype={
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


countries={
	"AUS": (__getGenreStringMain, __getGenreStringMain, GenresAUS()),
	# Use illegal country names for IceTV genre tables so that they won't match real countries
	"AUSIceTV": (__getGenreStringMainIceTV, __getGenreStringSubIceTV, GenresAUSIceTV()),
	"GBROpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresGBROpenTV()),
	"ITAOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresITAOpenTV()),
	"AUSOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresAUSOpenTV()),
	"NZLOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresNZLOpenTV()),
	"ETSIOpenTV": (__getGenreStringMainOpenTV, __getGenreStringSubOpenTV, GenresETSIOpenTV())
}

defaultGenre=GenresETSI()
defaultCountryInfo=(__getGenreStringMain, __getGenreStringSub, defaultGenre)

# Backwards compatibility - use deprecated

maintype=defaultGenre.maintype
subtype=defaultGenre.subtype


def __remapCountry(country):
	if hasattr(config.plugins, "icetv") and config.plugins.icetv.enable_epg.value:
		if not country:
			country=config.plugins.icetv.member.country.value
		iceTVCountry=f"{country}IceTV"
		if iceTVCountry in countries:
			return iceTVCountry
	return country


def getGenreStringMain(hn, ln, country=None):
	countryInfo=countries.get(__remapCountry(country), defaultCountryInfo)
	return countryInfo[0](hn, ln, countryInfo[2])


def getGenreStringSub(hn, ln, country=None):
	countryInfo=countries.get(__remapCountry(country), defaultCountryInfo)
	return countryInfo[1](hn, ln, countryInfo[2])


def getGenreStringLong(hn, ln, country=None):
	# if hn == 0:
	# 	return _("Undefined content") + " " + str(ln)
	if hn == 15 and "OpenTV" not in str(country) and not (hasattr(config.plugins, "icetv") and config.plugins.icetv.enable_epg.value):
		return f'{_("User defined")} {str(ln)}'
	main=getGenreStringMain(hn, ln, country=country)
	sub=getGenreStringSub(hn, ln, country=country)
	if main and main != sub:
		return f"{main}: {sub}"
	else:
		return main
# 	return _("Reserved") + " " + str(hn) + "," + str(ln)

#
# The End
#
