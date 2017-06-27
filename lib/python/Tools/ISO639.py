import cPickle
import enigma
with open(enigma.eEnv.resolve("${datadir}/enigma2/iso-639-3.pck"), 'rb') as f:
	LanguageCodes = cPickle.load(f)
