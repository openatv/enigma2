import gettext

from Tools.Directories import SCOPE_LANGUAGE, resolveFilename

import language_cache

class Language:
	def __init__(self):
		gettext.install('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), unicode=0, codeset="utf-8")
		self.activeLanguage = 0
		self.lang = {}
		self.langlist = []
		# FIXME make list dynamically
		# name, iso-639 language, iso-3166 country. Please don't mix language&country!
		# also, see "precalcLanguageList" below on how to re-create the language cache after you added a language
		self.addLanguage(_("English"), "en", "EN")
		self.addLanguage(_("German"), "de", "DE")
		self.addLanguage(_("Arabic"), "ar", "AE")
		self.addLanguage(_("Catalan"), "ca", "AD")
		self.addLanguage(_("Croatian"), "hr", "HR")
		self.addLanguage(_("Czech"), "cs", "CZ")
		self.addLanguage(_("Danish"), "da", "DK")
		self.addLanguage(_("Dutch"), "nl", "NL")
		self.addLanguage(_("Estonian"), "et", "EE")
		self.addLanguage(_("Finnish"), "fi", "FI")
		self.addLanguage(_("French"), "fr", "FR")
		self.addLanguage(_("Greek"), "el", "GR")
		self.addLanguage(_("Hungarian"), "hu", "HU")
		self.addLanguage(_("Lithuanian"), "lt", "LT")
		self.addLanguage(_("Latvian"), "lv", "LV")
		self.addLanguage(_("Icelandic"), "is", "IS")
		self.addLanguage(_("Italian"), "it", "IT")
		self.addLanguage(_("Norwegian"), "no", "NO")
		self.addLanguage(_("Polish"), "pl", "PL")
		self.addLanguage(_("Portuguese"), "pt", "PT")
		self.addLanguage(_("Russian"), "ru", "RU")
		self.addLanguage(_("Serbian"), "sr", "YU")
		self.addLanguage(_("Slovakian"), "sk", "SK")
		self.addLanguage(_("Slovenian"), "sl", "SI")
		self.addLanguage(_("Spanish"), "es", "ES")
		self.addLanguage(_("Swedish"), "sv", "SE")
		self.addLanguage(_("Turkish"), "tr", "TR")
		self.addLanguage(_("Ukrainian"), "uk", "UA")
		self.addLanguage(_("Frisian"), "fy", "x-FY") # there is no separate country for frisian

		self.callbacks = []

	def addLanguage(self, name, lang, country):
		try:
			self.lang[str(lang + "_" + country)] = ((_(name), lang, country))
			self.langlist.append(str(lang + "_" + country))
		except:
			print "Language " + str(name) + " not found"

	def activateLanguage(self, index):
		try:
			lang = self.lang[index]
			print "Activating language " + lang[0]
			gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[lang[1]]).install()
			self.activeLanguage = index
			for x in self.callbacks:
				x()
		except:
			print "Selected language does not exist!"

	def activateLanguageIndex(self, index):
		if index < len(self.langlist):
			self.activateLanguage(self.langlist[index])

	def getLanguageList(self):
		return [ (x, self.lang[x]) for x in self.langlist ]

	def getActiveLanguage(self):
		return self.activeLanguage
	
	def getActiveLanguageIndex(self):
		idx = 0
		for x in self.langlist:
			if x == self.activeLanguage:
				return idx
			idx += 1
		return None			

	def getLanguage(self):
		try:
			return str(self.lang[self.activeLanguage][1]) + "_" + str(self.lang[self.activeLanguage][2])
		except:
			return ''

	def addCallback(self, callback):
		self.callbacks.append(callback)

	def precalcLanguageList(self):
		# excuse me for those T1, T2 hacks please. The goal was to keep the language_cache.py as small as possible, *and* 
		# don't duplicate these strings.
		T1 = _("Please use the UP and DOWN keys to select your language. Afterwards press the OK button.")
		T2 = _("Language selection")
		l = open("language_cache.py", "w")
		print >>l, "# -*- coding: UTF-8 -*-"
		print >>l, "LANG_TEXT = {"
		for language in self.langlist:
			self.activateLanguage(language)
			print >>l, '"%s": {' % language
			for name, lang, country in self.lang.values():
				print >>l, '\t"%s_%s": "%s",' % (lang, country, _(name))

			print >>l, '\t"T1": "%s",' % (_(T1))
			print >>l, '\t"T2": "%s",' % (_(T2))
			print >>l, '},'
		print >>l, "}"

language = Language()
