# Genre types taken from DVB standards documentation.
#
# Some broadcaster do define other types so this list may grow or be replaced.
#
class Genres:
	levelOneETSI = {
		0x0: _("Undefined"),
		0x1: _("Movie/Drama"),
		0x2: _("News/Current affairs"),
		0x3: _("Show/Game show"),
		0x4: _("Sports"),
		0x5: _("Children's/Youth programs"),
		0x6: _("Music/Ballet/Dance"),
		0x7: _("Arts/Culture (without music)"),
		0x8: _("Social/Political issues/Economics"),
		0x9: _("Education/Science/Factual topics"),
		0xA: _("Leisure hobbies"),
		0xB: _("Special characteristics"),
		0xC: _("Adult"),
		0xD: _("Reserved"),
		0xE: _("Reserved"),
		0xF: _("User defined")
	}
	levelTwoETSI = {
		0x00: "",
		#
		0x10: _("Movie/Drama"),
		0x11: _("Detective/Thriller"),
		0x12: _("Adventure/Western/War"),
		0x13: _("Science fiction/Fantasy/Horror"),
		0x14: _("Comedy"),
		0x15: _("Soap/Melodrama/Folkloric"),
		0x16: _("Romance"),
		0x17: _("Serious/Classical/Religious/Historical/Drama"),
		0x18: _("Adult movie/Drama"),
		#
		0x20: _("News/Current affairs"),
		0x21: _("News/Weather report"),
		0x22: _("News magazine"),
		0x23: _("Documentary"),
		0x24: _("Discussion/Interview/Debate"),
		#
		0x30: _("Show/Game show"),
		0x31: _("Game show/Quiz/Contest"),
		0x32: _("Variety show"),
		0x33: _("Talk show"),
		#
		0x40: _("Sports"),
		0x41: _("Special events (Olympic games, World cup, etc.)"),
		0x42: _("Sports magazines"),
		0x43: _("Football/Soccer"),
		0x44: _("Tennis/Squash"),
		0x45: _("Team sports (excluding Football)"),
		0x46: _("Athletics"),
		0x47: _("Motor sport"),
		0x48: _("Water sport"),
		0x49: _("Winter sport"),
		0x4A: _("Equestrian"),
		0x4B: _("Martial sports"),
		#
		0x50: _("Children's/Youth programs"),
		0x51: _("Pre-school children's programs"),
		0x52: _("Entertainment programs for 6 to 14"),
		0x53: _("Entertainment programs for 10 to 16"),
		0x54: _("Informational/Educational/School programs"),
		0x55: _("Cartoons/Puppets"),
		#
		0x60: _("Music/Ballet/Dance"),
		0x61: _("Rock/Pop"),
		0x62: _("Serious music/Classic music"),
		0x63: _("Folk/Traditional music"),
		0x64: _("Jazz"),
		0x65: _("Musical/Opera"),
		0x66: _("Ballet"),
		#
		0x70: _("Arts/Culture (without music)"),
		0x71: _("Performing arts"),
		0x72: _("Fine arts"),
		0x73: _("Religion"),
		0x74: _("Popular culture/Traditional arts"),
		0x75: _("Literature"),
		0x76: _("Film/Cinema"),
		0x77: _("Experimental film/video"),
		0x78: _("Broadcasting/Press"),
		0x79: _("New media"),
		0x7A: _("Arts/Culture magazines"),
		0x7B: _("Fashion"),
		#
		0x80: _("Social/Political issues/Economics"),
		0x81: _("Magazines/Reports/Documentary"),
		0x82: _("Economics/Social advisory"),
		0x83: _("Remarkable people"),
		#
		0x90: _("Education/Science/Factual topics"),
		0x91: _("Nature/Animals/Environment"),
		0x92: _("Technology/Natural sciences"),
		0x93: _("Medicine/Physiology/Psychology"),
		0x94: _("Foreign countries/Expeditions"),
		0x95: _("Social/Spiritual sciences"),
		0x96: _("Further education"),
		0x97: _("Languages"),
		#
		0xA0: _("Leisure hobbies"),
		0xA1: _("Tourism/Travel"),
		0xA2: _("Handicraft"),
		0xA3: _("Motoring"),
		0xA4: _("Fitness and Health"),
		0xA5: _("Cooking"),
		0xA6: _("Advertisement/Shopping"),
		0xA7: _("Gardening"),
		#
		0xB0: _("Original language"),
		0xB1: _("Black & White"),
		0xB2: _("Unpublished"),
		0xB3: _("Live broadcast"),
		0xB4: _("Plano-stereoscopic"),
		0xB5: _("Local or Regional"),
		#
		0xC0: _("Adult")
	}
	levelOneAUS = {
		0x0: _("Undefined"),
		0x1: _("Movie"),
		0x2: _("News"),
		0x3: _("Entertainment"),
		0x4: _("Sport"),
		0x5: _("Children's"),
		0x6: _("Music"),
		0x7: _("Arts/Culture"),
		0x8: _("Current affairs"),
		0x9: _("Education/Information"),
		0xA: _("Infotainment"),
		0xB: _("Special"),
		0xC: _("Comedy"),
		0xD: _("Drama"),
		0xE: _("Documentary"),
		0xF: _("User defined")
	}
	levelTwoAUS = {
		0x00: "",
		#
		0x10: _("Movie/Drama"),
		0x11: _("Detective/Thriller"),
		0x12: _("Adventure/Western/War"),
		0x13: _("Science fiction/Fantasy/Horror"),
		0x14: _("Comedy"),
		0x15: _("Soap/Melodrama/Folkloric"),
		0x16: _("Romance"),
		0x17: _("Serious/Classical/Religious/Historical/Drama"),
		0x18: _("Adult movie/Drama"),
		#
		0x20: _("News"),
		0x21: _("News/Weather report"),
		0x22: _("News magazine"),
		0x23: _("Documentary"),
		0x24: _("Discussion/Interview/Debate"),
		#
		0x30: _("Entertainment"),
		0x31: _("Game show/Quiz/Contest"),
		0x32: _("Variety show"),
		0x33: _("Talk show"),
		#
		0x40: _("Sports"),
		0x41: _("Special events (Olympic games, World cup, etc.)"),
		0x42: _("Sports magazines"),
		0x43: _("Football/Soccer"),
		0x44: _("Tennis/Squash"),
		0x45: _("Team sports (excluding Football)"),
		0x46: _("Athletics"),
		0x47: _("Motor sport"),
		0x48: _("Water sport"),
		0x49: _("Winter sport"),
		0x4A: _("Equestrian"),
		0x4B: _("Martial sports"),
		#
		0x50: _("Children's"),
		0x51: _("Pre-school children's programs"),
		0x52: _("Entertainment programs for 6 to 14"),
		0x53: _("Entertainment programs for 10 to 16"),
		0x54: _("Informational/Educational/School programs"),
		0x55: _("Cartoons/Puppets"),
		#
		0x60: _("Music"),
		0x61: _("Rock/Pop"),
		0x62: _("Serious music/Classic music"),
		0x63: _("Folk/Traditional music"),
		0x64: _("Jazz"),
		0x65: _("Musical/Opera"),
		0x66: _("Ballet"),
		#
		0x70: _("Arts/Culture"),
		0x71: _("Performing arts"),
		0x72: _("Fine arts"),
		0x73: _("Religion"),
		0x74: _("Popular culture/Traditional arts"),
		0x75: _("Literature"),
		0x76: _("Film/Cinema"),
		0x77: _("Experimental film/video"),
		0x78: _("Broadcasting/Press"),
		0x79: _("New media"),
		0x7A: _("Arts/Culture magazines"),
		#
		0x80: _("Current affairs"),
		0x81: _("Magazines/Reports/Documentary"),
		0x82: _("Economics/Social advisory"),
		0x83: _("Remarkable people"),
		#
		0x90: _("Education/Information"),
		0x91: _("Nature/Animals/Environment"),
		0x92: _("Technology/Natural sciences"),
		0x93: _("Medicine/Physiology/Psychology"),
		0x94: _("Foreign countries/Expeditions"),
		0x95: _("Social/Spiritual sciences"),
		0x96: _("Further education"),
		0x97: _("Languages"),
		#
		0xA0: _("Infotainment"),
		0xA1: _("Tourism/Travel"),
		0xA2: _("Handicraft"),
		0xA3: _("Motoring"),
		0xA4: _("Fitness and Health"),
		0xA5: _("Cooking"),
		0xA6: _("Advertisement/Shopping"),
		0xA7: _("Gardening"),
		#
		0xB0: _("Special"),
		0xB1: _("Black & White"),
		0xB2: _("Unpublished"),
		0xB3: _("Live broadcast"),
		0xB4: _("Plano-stereoscopic"),
		0xB5: _("Local or Regional"),
		#
		0xC0: _("Comedy"),
		#
		0xD0: _("Drama"),
		#
		0xE0: _("Documentary")
	}
	levelOneAUSIceTV ={
		0x0: _("Miscellaneous"),
		0x1: _("Movie/Drama"),
		0x2: _("News/Current affairs"),
		0x3: _("Show/Game show"),
		0x4: _("Sports"),
		0x5: _("Children/Youth"),
		0x6: _("Music/Ballet/Dance"),
		0x7: _("Arts/Culture"),
		0x8: _("Social/Political/Economics"),
		0x9: _("Education/Science/Factual"),
		0xA: _("Leisure hobbies"),
		0xB: _("Special"),
		0xC: _("Comedy"),
		0xD: _("Drama"),
		0xE: _("Documentary"),
		0xF: _("Real life")
	}
	levelTwoAUSIceTV = {
		0x00: _(""),  # _("Miscellaneous"),
		0x01: _("Cult"),
		0x02: _("Youth"),  # 0x02 remapped from 0x01.
		0x03: _("Wrestling"),  # 0x03 remapped from 0x01.
		0x04: _("Violence"),  # 0x04 remapped from 0x01.
		0x05: _("Short film"),  # 0x05 remapped from 0x01.
		0x06: _("Sailing"),  # 0x06 remapped from 0x01.
		0x07: _("Renovation"),  # 0x07 remapped from 0x01.
		0x08: _("Mini series"),  # 0x08 remapped from 0x01.
		0x09: _("MMA"),  # 0x09 remapped from 0x01.
		0x0A: _("Horse racing"),  # 0x0A remapped from 0x01.
		0x0B: _("Finance"),  # 0x0B remapped from 0x01.
		0x0C: _("Film-noir"),  # 0x0C remapped from 0x01.
		0x0D: _("Family"),  # 0x0D remapped from 0x01.
		0x0E: _("Cycling"),  # 0x0E remapped from 0x01.
		#
		0x10: _("Movie"),  # _("Movie/Drama"),
		0x11: _("Crime"),
		0x12: _("Adventure"),
		0x13: _("Science fiction"),
		0x14: _("Comedy"),
		0x15: _("Soap opera"),
		0x16: _("Romance"),
		0x17: _("Historical"),
		0x18: _("Adult"),
		0x19: _("Drama"),  # 0x19 remapped from 0x10.
		0x1A: _("Thriller"),  # 0x1A remapped from 0x11.
		0x1B: _("Mystery"),  # 0x1B remapped from 0x11.
		0x1C: _("Murder"),  # 0x1C remapped from 0x11.
		0x1D: _("Western"),  # 0x1D remapped from 0x12.
		0x1E: _("War"),  # 0x1E remapped from 0x12.
		0x1F: _("Action"),  # 0x1F remapped from 0x12.
		#
		0x20: _("News"),  # _("News/Current affairs"),
		0x21: _("Weather"),
		0x23: _("Documentary"),
		#
		0x30: _("Entertainment"),  # _("Show/Game show"),
		0x31: _("Game show"),
		0x32: _("Variety"),
		0x33: _("Talk show"),
		#
		0x40: _("Sport"),  # _("Sports"),
		0x41: _("Olympics"),
		0x42: _("Golf"),  # 0x42 remapped from 0x40.
		0x43: _("Soccer"),
		0x44: _("Tennis"),
		0x45: _("Football"),
		0x46: _("Athletics"),
		0x47: _("Motor sport"),
		0x48: _("Swimming"),
		0x49: _("Winter sports"),
		0x4A: _("Boxing"),  # 0x4A remapped from 0x40.
		0x4B: _("Rugby league"),  # 0x4B remapped from 0x45.
		0x4C: _("Rugby"),  # 0x4C remapped from 0x45.
		0x4D: _("Netball"),  # 0x4D remapped from 0x45.
		0x4E: _("Hockey"),  # 0x4E remapped from 0x45.
		0x4F: _("Cricket"),  # 0x4F remapped from 0x45.
		#
		0x50: _("Children"),  # _("Children/Youth"),
		0x51: _("Cartoon"),  # 0x51 remapped from 0x55.
		0x55: _("Animation"),
		#
		0x60: _("Music"),  # _("Music/Ballet/Dance"),
		0x61: _("Musical"),  # 0x61 remapped from 0x60.
		0x62: _("Dance"),  # 0x62 remapped from 0x60.
		#
		0x70: _("Arts/Culture"),
		0x73: _("Religion"),
		#
		0x80: _("Society & Culture"),  # _("Social/Political/Economics"),
		0x81: _("Current affairs"),
		0x82: _("Parliament"),  # 0x82 remapped from 0x80.
		0x83: _("Biography"),
		0x84: _("Business & Finance"),  # 0x84 remapped from 0x80.
		#
		0x90: _("Education"),  # _("Education/Science/Factual"),
		0x91: _("Nature"),
		0x92: _("Science & Tech"),
		0x93: _("Medical"),
		0x94: _("Science"),  # 0x94 remapped from 0x90.
		#
		0xA0: _("Infotainment"),  # _("Leisure hobbies"),
		0xA1: _("Travel"),
		0xA2: _("Lifestyle"),  # 0xA2 remapped from 0xA0.
		0xA3: _("Fishing"),  # 0xA3 remapped from 0xA0.
		0xA4: _("Food/Wine"),  # 0xA4 remapped from 0xA5.
		0xA5: _("Cooking"),
		0xA6: _("Shopping"),
		0xA7: _("Gardening"),
		#
		0xB0: _("Special"),
		0xB3: _("Live"),
		#
		0xC0: _("Comedy"),
		#
		0xD0: _("Drama"),
		#
		0xE0: _("Documentary"),
		#
		0xF0: _("Real life"),
		0xF1: _("Horror"),  # 0xF1 remapped from 0x13.
		0xF2: _("Fantasy"),  # 0xF2 remapped from 0x13.
		0xF3: _("Sitcom"),  # 0xF3 remapped from 0x14.
		0xF4: _("Basketball"),  # 0xF4 remapped from 0x45.
		0xF5: _("Baseball"),  # 0xF5 remapped from 0x45.
		0xF6: _("American football"),  # 0xF6 remapped from 0x45.
		0xF7: _("AFL"),  # 0xF7 remapped from 0x45.
		0xF8: _("Rowing")  # 0xF8 remapped from 0x48.
	}
	levelOneGBROpenTV = {  # The GBR entries are not translated as they are location specific.
		0x0: "General",
		0x1: "General",
		0x2: "General",
		0x3: "General",
		0x4: "Children",
		0x5: "Children",
		0x6: "Entertainment",
		0x7: "Entertainment",
		0x8: "Music",
		0x9: "Music",
		0xA: "News/Documentary",
		0xB: "News/Documentary",
		0xC: "Movie",
		0xD: "Movie",
		0xE: "Sports",
		0xF: "Sports"
	}
	levelTwoGBROpenTV = {
		0x00: "No category",  # "General",
		#
		0x20: "No category",  # "General",
		0x21: "Adult",
		0x23: "Shopping",
		#
		0x40: "General",  # "Children",
		0x41: "Cartoons",
		0x42: "Comedy",
		0x43: "Drama",
		0x44: "Educational",
		0x45: "Under 5",
		0x46: "Factual",
		0x47: "Magazine",
		#
		0x60: "General",  # "Entertainment",
		0x61: "Action",
		0x62: "Comedy",
		0x63: "Detective",
		0x64: "Drama",
		0x65: "Game show",
		0x66: "Science fiction",
		0x67: "Soap",
		0x68: "Animation",
		0x69: "Chat show",
		0x6A: "Cooking",
		0x6B: "Factual",
		0x6C: "Fashion",
		0x6D: "Home and Garden",
		0x6E: "Travel",
		0x6F: "Technology",
		#
		0x70: "Arts",  # "Entertainment",
		0x71: "Lifestyle",
		0x72: "Home",
		0x73: "Magazine",
		0x74: "Medical",
		0x75: "Review",
		0x76: "Antiques",
		0x77: "Motors",
		0x78: "Art/Literature",
		0x79: "Ballet",
		0x7A: "Opera",
		#
		0x80: "General",  # "Music",
		0x81: "Classical",
		0x82: "Folk and Country",
		0x83: "National music",
		0x84: "Jazz",
		0x85: "Opera",
		0x86: "Rock/Pop",
		0x87: "Alternative",
		0x88: "Events",
		0x89: "Club/Dance",
		0x8A: "Hip Hop",
		0x8B: "Soul/Rhythm and Blues",
		0x8C: "Dance",
		#
		0x90: "Features",  # "Music",
		0x95: "Lifestyle",
		0x96: "News and Weather",
		0x97: "Easy listening",
		0x98: "Discussion",
		0x99: "Entertainment",
		0x9A: "Religious",
		#
		0xA0: "General",  # "News/Documentary",
		0xA1: "Business",
		0xA2: "World cultures",
		0xA3: "Adventure",
		0xA4: "Biography",
		0xA5: "Educational",
		0xA6: "Feature",
		0xA7: "Politics",
		0xA8: "News",
		0xA9: "Nature",
		0xAA: "Religious",
		0xAB: "Science",
		0xAC: "Showbiz",
		0xAD: "War",
		0xAE: "Historical",
		0xAF: "Ancient",
		#
		0xB0: "Transport",  # "News/Documentary",
		0xB1: "Docudrama",
		0xB2: "World Affairs",
		0xB3: "Events",
		0xB4: "Entertainment",
		#
		0xC0: "General",  # "Movie",
		0xC1: "Action",
		0xC2: "Animation",
		0xC4: "Comedy",
		0xC5: "Family",
		0xC6: "Drama",
		0xC8: "Science fiction",
		0xC9: "Thriller",
		0xCA: "Horror",
		0xCB: "Romance",
		0xCC: "Musical",
		0xCD: "Mystery",
		0xCE: "Western",
		0xCF: "Factual",
		#
		0xD0: "Fantasy",  # "Movie",
		0xD1: "Erotic",
		0xD2: "Adventure",
		0xD3: "War",
		#
		0xE0: "General",  # "Sports",
		0xE1: "American football",
		0xE2: "Athletics",
		0xE3: "Baseball",
		0xE4: "Basketball",
		0xE5: "Boxing",
		0xE6: "Cricket",
		0xE7: "Fishing",
		0xE8: "Football",
		0xE9: "Golf",
		0xEA: "Ice hockey",
		0xEB: "Motor sport",
		0xEC: "Racing",
		0xED: "Rugby",
		0xEE: "Equestrian",
		0xEF: "Winter sports",
		#
		0xF0: "Snooker/Pool",  # "Sports",
		0xF1: "Tennis",
		0xF2: "Wrestling",
		0xF3: "Darts",
		0xF4: "Water sports",
		0xF5: "Extreme"
	}
	levelOneITAOpenTV = {  # The ITA entries are not translated as they are location specific.
		0x0: "Generale",
		0x1: "Generale",
		0x2: "Intrattenimento",
		0x3: "Intrattenimento",
		0x4: "Sport",
		0x5: "Sport",
		0x6: "Film",
		0x7: "Film",
		0x8: "Mondo e Tendenze",
		0x9: "Mondo e Tendenze",
		0xA: "Informazione",
		0xB: "Informazione",
		0xC: "Ragazzi e Musica",
		0xD: "Ragazzi e Musica",
		0xE: "Altri Programmi",
		0xF: "Altri Programmi"
	}
	levelTwoITAOpenTV = {
		0x00: "Non definito",  # "Generale",
		#
		0x20: "Generale",  # "Intrattenimento",
		0x21: "Fiction",
		0x22: "Sit com",
		0x23: "Show",
		0x24: "Telefilm",
		0x25: "Soap opera",
		0x26: "Telenovela",
		0x27: "Fantascienza",
		0x28: "Animazione",
		0x29: "Giallo",
		0x2A: "Drammatico",
		0x2B: "Romantico",
		0x2C: "Miniserie",
		0x2D: "Spettacolo",
		0x2E: "Quiz",
		0x2F: "Talk show",
		#
		0x30: "Varieta",  # "Intrattenimento",
		0x31: "Festival",
		0x32: "Teatro",
		0x33: "Gioco",
		#
		0x40: "Generale",  # "Sport",
		0x41: "Calcio",
		0x42: "Tennis",
		0x43: "Motori",
		0x44: "Altri",
		0x45: "Baseball",
		0x46: "Ciclismo",
		0x47: "Rugby",
		0x48: "Basket",
		0x49: "Boxe",
		0x4A: "Atletica",
		0x4B: "Football USA",
		0x4C: "Hockey",
		0x4D: "Sci",
		0x4E: "Equestri",
		0x4F: "Golf",
		#
		0x50: "Nuoto",  # "Sport",
		0x51: "Wrestling",
		#
		0x60: "Generale",  # "Film",
		0x61: "Drammatico",
		0x62: "Commedia",
		0x63: "Romantico",
		0x64: "Azione",
		0x65: "Fantascienza",
		0x66: "Western",
		0x67: "Comico",
		0x68: "Fantastico",
		0x69: "Avventura",
		0x6A: "Poliziesco",
		0x6B: "Guerra",
		0x6C: "Horror",
		0x6D: "Animazione",
		0x6E: "Thriller",
		0x6F: "Musicale",
		#
		0x70: "Corto",  # "Film",
		0x71: "Cortometraggio",
		#
		0x80: "Generale",  # "Mondo e Tendenze",
		0x81: "Natura",
		0x82: "Arte e Cultura",
		0x83: "Lifestyle",
		0x84: "Viaggi",
		0x85: "Documentario",
		0x86: "Societa",
		0x87: "Scienza",
		0x88: "Storia",
		0x89: "Sport",
		0x8A: "Pesca",
		0x8B: "Popoli",
		0x8C: "Cinema",
		0x8D: "Musica",
		0x8E: "Hobby",
		0x8F: "Caccia",
		#
		0x90: "Reportage",  # "Mondo e Tendenze",
		0x91: "Magazine",
		0x92: "Magazine cultura",
		0x93: "Magazine scienza",
		0x94: "Politica",
		0x95: "Magazine cinema",
		0x96: "Magazine sport",
		0x97: "Attualita",
		0x98: "Moda",
		0x99: "Economia",
		0x9A: "Magazine caccia e pesca",
		0x9B: "Magazine viaggi",
		0x9C: "Magazine natura",
		0x9D: "Magazine musica",
		0x9E: "Religione",
		0x9F: "Televendita",
		#
		0xA0: "Generale",  # "Informazione",
		0xA1: "Notiziario",
		0xA2: "Sport",
		0xA3: "Economia",
		#
		0xC0: "Generale",  # "Ragazzi e Musica",
		0xC1: "Bambini",
		0xC2: "Ragazzi",
		0xC3: "Cartoni animati",
		0xC4: "Musica",
		0xC5: "Film animazione",
		0xC6: "Film",
		0xC7: "Telefilm",
		0xC8: "Magazine",
		#
		0xD4: "Danza",    # "Ragazzi e Musica",
		#
		0xE0: "Generale",  # "Altri Programmi",
		0xE1: "Educational",
		0xE2: "Regionale",
		0xE3: "Shopping",
		0xE5: "Inizio e fine trasmissioni",
		0xE6: "Eventi speciali",
		0xE7: "Film per adulti"
	}

	def __init__(self):
		self.countryGenres = {
			"AUS": (self.levelOneAUS, self.levelTwoAUS),  # Australian sub-genres are effectively the same as the genre.
			# Use illegal country name for IceTV genre tables so that they won't match real countries.
			"IT1": (self.levelOneAUSIceTV, self.levelTwoAUSIceTV),
			# Use illegal country name for OpenTV genre tables so that they won't match real countries.
			"OT1": (self.levelOneGBROpenTV, self.levelTwoGBROpenTV),
			"OT2": (self.levelOneITAOpenTV, self.levelTwoITAOpenTV)
		}

	def getGenreLevelOneText(self, highNibble, lowNibble, country=None):
		if 0x0 <= highNibble <= 0xF and 0x0 <= lowNibble <= 0xF:
			levelOne, levelTwo = self.countryGenres.get(country, (self.levelOneETSI, self.levelTwoETSI))
			genreText = levelOne.get(highNibble, f"{_("Undefined")} 0x{highNibble:X}{lowNibble:X}")
		else:
			genreText = ""
		return genreText

	def getGenreLevelTwoText(self, highNibble, lowNibble, country=None):
		if 0x0 <= highNibble <= 0xF and 0x0 <= lowNibble <= 0xF:
			levelOne, levelTwo = self.countryGenres.get(country, (self.levelOneETSI, self.levelTwoETSI))
			genre = highNibble * 16 + lowNibble
			genreText = levelTwo.get(genre)
			if genreText is None:
				# genreText = levelOne.get(highNibble, f"{_("Undefined")} 0x{highNibble:X}{lowNibble:X}")
				genreText = f"{_("Undefined")} 0x{highNibble:X}{lowNibble:X}"
		else:
			genreText = ""
		return genreText


genres = Genres()
