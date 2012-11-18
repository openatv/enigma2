#
# Genre types taken from DVB standards documentation
#
# some broadcaster do define other types so this list
# may grow or be replaced..
#
maintype = [	_("Reserved"),
		_("Movie/Drama"),
		_("News Current Affairs"),
		_("Show Games show"),
		_("Sports"),
		_("Children/Youth"),
		_("Music/Ballet/Dance"),
		_("Arts/Culture"),
		_("Social/Political/Economics"),
		_("Education/Science/..."),
		_("Leisure hobbies"),
		_("Other")]


subtype = {}
# Movie/Drama
subtype[1] = [
					_("movie/drama (general)"),
					_("detective/thriller"),
					_("adventure/western/war"),
					_("science fiction/fantasy/horror"),
					_("comedy"),
					_("soap/melodram/folkloric"),
					_("romance"),
					_("serious/classical/religious/historical movie/drama"),
					_("adult movie/drama")]

# News Current Affairs
subtype[2] = [
					_("news/current affairs (general)"),
					_("news/weather report"),
					_("news magazine"),
					_("documentary"),
					_("discussion/interview/debate")]

# Show Games show
subtype[3] = [
					_("show/game show (general)"),
					_("game show/quiz/contest"),
					_("variety show"),
					_("talk show")]

# Sports
subtype[4] = [
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
					_("martial sports")]

# Children/Youth
subtype[5] = [
					_("childrens's/youth program (general)"),
					_("pre-school children's program"),
					_("entertainment (6-14 year old)"),
					_("entertainment (10-16 year old)"),
					_("information/education/school program"),
					_("cartoon/puppets")]

# Music/Ballet/Dance
subtype[6] = [
					_("music/ballet/dance (general)"),
					_("rock/pop"),
					_("serious music/classic music"),
					_("folk/traditional music"),
					_("jazz"),
					_("musical/opera"),
					_("ballet")]

# Arts/Culture
subtype[7] = [
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
					_("fashion")]

# Social/Political/Economics
subtype[8] = [
					_("social/political issues/economics (general)"),
					_("magazines/reports/documentary"),
					_("economics/social advisory"),
					_("remarkable people")]

# Education/Science/...
subtype[9] = [
					_("education/science/factual topics (general)"),
					_("nature/animals/environment"),
					_("technology/natural science"),
					_("medicine/physiology/psychology"),
					_("foreign countries/expeditions"),
					_("social/spiritual science"),
					_("further education"),
					_("languages")]

# Leisure hobies
subtype[10] = [
					_("leisure hobbies (general)"),
					_("tourism/travel"),
					_("handicraft"),
					_("motoring"),
					_("fitness & health"),
					_("cooking"),
					_("advertisement/shopping"),
					_("gardening")]

# Other
subtype[11] = [
					_("original language"),
					_("black & white"),
					_("unpublished"),
					_("live broadcast")]

def getGenreStringMain(hn, ln):
#	if hn == 0:
#		return _("Undefined content")
	if hn == 15:
		return _("User defined")
	if hn > 0 and hn < len(maintype):
		return maintype[hn]
#	return _("Reserved") + " " + str(hn)
	return ""

def getGenreStringSub(hn, ln):
#	if hn == 0:
#		return _("Undefined content") + " " + str(ln)
	if hn == 15:
		return _("User defined") + " " + str(ln)
	if hn > 0 and hn < len(maintype):
		if ln == 15:
			return _("User defined")
		if ln < len(subtype[hn]):
			return subtype[hn][ln]
#		return _("Reserved") " " + str(ln)
#	return _("Reserved") + " " + str(hn) + "," + str(ln)
	return ""

def getGenreStringLong(hn, ln):
#	if hn == 0:
#		return _("Undefined content") + " " + str(ln)
	if hn == 15:
		return _("User defined") + " " + str(ln)
	if hn > 0 and hn < len(maintype):
		return maintype[hn] + ": " + getGenreStringSub(hn, ln)
#	return _("Reserved") + " " + str(hn) + "," + str(ln)
	return ""

#
# The End
#
