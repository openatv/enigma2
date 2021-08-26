import cPickle
import enigma

# The data file contains dictionary that encompasses a mixture of ISO-639-3,
# ISO639-2 and ISO-639-1 keys and the corresponding language names. For
# example, English will have {'en': ('English',), 'eng': ('English',)}


with open(enigma.eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	LanguageCodes = cPickle.load(f)
	LanguageCodes["aus"] = ("Audio Description",)  # hack to deal with Australian broadcasters AD tracks
