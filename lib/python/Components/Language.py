# -*- coding: UTF-8 -*-
import gettext
import locale
import os

from Tools.Directories import SCOPE_LANGUAGE, resolveFilename

class Language:
	def __init__(self):
		gettext.install('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), unicode=0, codeset="utf-8")
		self.activeLanguage = 0
		self.catalog = None
		self.lang = {}
		self.langlist = []
		# FIXME make list dynamically
		# name, iso-639 language, iso-3166 country. Please don't mix language&country!
		self.addLanguage("Arabic",      "ar", "AE")
		self.addLanguage("Български",   "bg", "BG")
		self.addLanguage("Català",      "ca", "AD")
		self.addLanguage("Česky",       "cs", "CZ")
		self.addLanguage("Dansk",       "da", "DK")
		self.addLanguage("Deutsch",     "de", "DE")
		self.addLanguage("Ελληνικά",    "el", "GR")
		self.addLanguage("English",     "en", "EN")
		self.addLanguage("Español",     "es", "ES")
		self.addLanguage("Eesti",       "et", "EE")
		self.addLanguage("Persian",     "fa", "IR")
		self.addLanguage("Suomi",       "fi", "FI")
		self.addLanguage("Français",    "fr", "FR")
		self.addLanguage("Frysk",       "fy", "NL")
		self.addLanguage("Hebrew",      "he", "IL")
		self.addLanguage("Hrvatski",    "hr", "HR")
		self.addLanguage("Magyar",      "hu", "HU")
		self.addLanguage("Íslenska",    "is", "IS")
		self.addLanguage("Italiano",    "it", "IT")
		self.addLanguage("Lietuvių",    "lt", "LT")
		self.addLanguage("Latviešu",    "lv", "LV")
		self.addLanguage("Nederlands",  "nl", "NL")
		self.addLanguage("Norsk",       "no", "NO")
		self.addLanguage("Polski",      "pl", "PL")
		self.addLanguage("Português",   "pt", "PT")
		self.addLanguage("Brasileira",  "pt", "BR")
		self.addLanguage("Romanian",    "ro", "RO")
		self.addLanguage("Русский",     "ru", "RU")
		self.addLanguage("Slovensky",   "sk", "SK")
		self.addLanguage("Slovenščina", "sl", "SI")
		self.addLanguage("Srpski",      "sr", "YU")
		self.addLanguage("Svenska",     "sv", "SE")
		self.addLanguage("ภาษาไทย",     "th", "TH")
		self.addLanguage("Türkçe",      "tr", "TR")
		self.addLanguage("Ukrainian",   "uk", "UA")

		self.callbacks = []

	def addLanguage(self, name, lang, country):
		try:
			self.lang[str(lang + "_" + country)] = ((name, lang, country))
			self.langlist.append(str(lang + "_" + country))
		except:
			print "Language " + str(name) + " not found"

	def activateLanguage(self, index):
		try:
			lang = self.lang[index]
			print "Activating language " + lang[0]
			self.catalog = gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[lang[1]])
			self.catalog.install(names=("ngettext", "pgettext"))
			self.activeLanguage = index
			for x in self.callbacks:
				x()
		except:
			print "Selected language does not exist!"
		try:
			locale.setlocale(locale.LC_TIME, (self.getLanguage(), 'UTF-8'))
		except:
			print "Failed to set LC_TIME to " + self.getLanguage() + ". Setting it to 'C'"
			locale.setlocale(locale.LC_TIME, 'C')
		os.environ["LC_TIME"] = self.getLanguage() + '.UTF-8'

	def activateLanguageIndex(self, index):
		if index < len(self.langlist):
			self.activateLanguage(self.langlist[index])

	def getLanguageList(self):
		return [ (x, self.lang[x]) for x in self.langlist ]

	def getActiveLanguage(self):
		return self.activeLanguage

	def getActiveCatalog(self):
		return self.catalog

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

language = Language()
