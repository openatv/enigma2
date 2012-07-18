
maintype = [	"Reserved",
			"Movie/Drama",
			"News Current Affairs",
			"Show Games show",
			"Sports",
			"Children/Youth",
			"Music/Ballet/Dance",
			"Arts/Culture",
			"Social/Political/Economics",
     			"Education/Science/...",
			"Leisure hobies",
			"Other",
			"Reserved",
			"Reserved",
			"Reserved",
			"Reserved"]

	

subtype = {}
subtype["Movie/Drama"] = [
					"movie/drama (general)",
					"detective/thriller",
					"adventure/western/war",
					"science fiction/fantasy/horror",
					"comedy",
					"soap/melodram/folkloric",
					"romance",
					"serious/classical/religious/historical movie/drama",
					"adult movie/drama"]

subtype["News Current Affairs"] = [
					"news/current affairs (general)",
					"news/weather report",
					"news magazine",
					"documentary",
					"discussion/interview/debate"]

subtype["Show Games show"] = [
					"show/game show (general)",
					"game show/quiz/contest",
					"variety show",
					"talk show"]

subtype["Sports"] = [
					"sports (general)",
					"special events",
					"sports magazine",
					"football/soccer",
					"tennis/squash",
					"team sports",
					"athletics",
					"motor sport",
					"water sport",
					"winter sport",
					"equestrian",
					"martial sports"]

subtype["Children/Youth"] = [
					"childrens's/youth program (general)",
					"pre-school children's program",
					"entertainment (6-14 year old)",
					"entertainment (10-16 year old)",
					"information/education/school program",
					"cartoon/puppets"]

subtype["Music/Ballet/Dance "] = [
					"music/ballet/dance (general)",
					"rock/pop",
					"serious music/classic music",
					"folk/traditional music",
					"jazz",
					"musical/opera",
					"ballet"]

subtype["Arts/Culture"] = [
					"arts/culture (without music, general)",
					"performing arts",
					"fine arts",
					"religion",
					"popular culture/traditional arts",
					"literature",
					"film/cinema",
					"experimental film/video",
					"broadcasting/press",
					"new media",
					"arts/culture magazine",
					"fashion"]

subtype["Social/Political/Economics"] = [
					"social/political issues/economics (general)",
					"magazines/reports/documentary",
					"economics/social advisory",
					"remarkable people"]

subtype["Education/Science/..."] = [
					"education/science/factual topics (general)",
					"nature/animals/environment",
					"technology/natural science",
					"medicine/physiology/psychology",
					"foreign countries/expeditions",
					"social/spiritual science",
					"further education",
					"languages"]

subtype["Leisure hobies"] = [
					"leisure hobbies (general)",
					"tourism/travel",
					"handicraft",
					"motoring",
					"fitness & health",
					"cooking",
					"advertisement/shopping",
					"gardening"]

subtype["Other"] = [
					"original language",
					"black & white",
					"unpublished",
					"live broadcast"]

def getGenreStringLong(hn, ln):
        maingenre = maintype[hn]
	if maingenre == "Reserved":
		return "Reserved"
	if ln == 15:
		return maingenre + ": User defined"
        sublen = len(subtype[maingenre])
	if ln >= sublen:
		return maingenre + " : Reserved"
	subgenre = subtype[maingenre][ln]
	return maingenre + ": " + subgenre

def getGenreStringMain(hn, ln):
        return maintype[hn]

def getGenreStringSub(hn, ln):
        maingenre = maintype[hn]
	if maingenre == "Reserved":
		return "Reserved"
	if ln == 15:
		return "User defined"
        sublen = len(subtype[maingenre])
	if ln >= sublen:
		return "Reserved"
	subgenre = subtype[maingenre][ln]
	return subgenre

