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
		self.addLanguage("Arabic",      "ar", "AE", "ISO-8859-15")
		self.addLanguage("Български",   "bg", "BG", "ISO-8859-15")
		self.addLanguage("Català",      "ca", "AD", "ISO-8859-15")
		self.addLanguage("Česky",       "cs", "CZ", "ISO-8859-15")
		self.addLanguage("Dansk",       "da", "DK", "ISO-8859-15")
		self.addLanguage("Deutsch",     "de", "DE", "ISO-8859-15")
		self.addLanguage("Ελληνικά",    "el", "GR", "ISO-8859-7")
		self.addLanguage("English",     "en", "EN", "ISO-8859-15")
		self.addLanguage("Español",     "es", "ES", "ISO-8859-15")
		self.addLanguage("Eesti",       "et", "EE", "ISO-8859-15")
		self.addLanguage("Persian",     "fa", "IR", "ISO-8859-15")
		self.addLanguage("Suomi",       "fi", "FI", "ISO-8859-15")
		self.addLanguage("Français",    "fr", "FR", "ISO-8859-15")
		self.addLanguage("Frysk",       "fy", "NL", "ISO-8859-15")
		self.addLanguage("Hebrew",      "he", "IL", "ISO-8859-15")
		self.addLanguage("Hrvatski",    "hr", "HR", "ISO-8859-15")
		self.addLanguage("Magyar",      "hu", "HU", "ISO-8859-15")
		self.addLanguage("Íslenska",    "is", "IS", "ISO-8859-15")
		self.addLanguage("Italiano",    "it", "IT", "ISO-8859-15")
		self.addLanguage("Kurdish",     "ku", "KU", "ISO-8859-15")
		self.addLanguage("Lietuvių",    "lt", "LT", "ISO-8859-15")
		self.addLanguage("Latviešu",    "lv", "LV", "ISO-8859-15")
		self.addLanguage("Nederlands",  "nl", "NL", "ISO-8859-15")
		self.addLanguage("Norsk Bokmål","nb", "NO", "ISO-8859-15")
		self.addLanguage("Norsk",       "no", "NO", "ISO-8859-15")
		self.addLanguage("Polski",      "pl", "PL", "ISO-8859-15")
		self.addLanguage("Português",   "pt", "PT", "ISO-8859-15")
		self.addLanguage("Português do Brasil",  "pt", "BR", "ISO-8859-15")
		self.addLanguage("Romanian",    "ro", "RO", "ISO-8859-15")
		self.addLanguage("Русский",     "ru", "RU", "ISO-8859-15")
		self.addLanguage("Slovensky",   "sk", "SK", "ISO-8859-15")
		self.addLanguage("Slovenščina", "sl", "SI", "ISO-8859-15")
		self.addLanguage("Srpski",      "sr", "YU", "ISO-8859-15")
		self.addLanguage("Svenska",     "sv", "SE", "ISO-8859-15")
		self.addLanguage("ภาษาไทย",     "th", "TH", "ISO-8859-15")
		self.addLanguage("Türkçe",      "tr", "TR", "ISO-8859-15")
		self.addLanguage("Ukrainian",   "uk", "UA", "ISO-8859-15")

		self.callbacks = []

	def addLanguage(self, name, lang, country, encoding):
		try:
			self.lang[str(lang + "_" + country)] = ((name, lang, country, encoding))
			self.langlist.append(str(lang + "_" + country))
		except:
			print "Language " + str(name) + " not found"

	def activateLanguage(self, index):
		try:
			lang = self.lang[index]
			print "Activating language " + lang[0]
			self.catalog = gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[index])
			self.catalog.install(names=("ngettext", "pgettext"))
			self.activeLanguage = index
			for x in self.callbacks:
				x()
		except:
			print "Selected language does not exist!"
		# NOTE: we do not use LC_ALL, because LC_ALL will not set any of the categories, when one of the categories fails.
		# We'd rather try to set all available categories, and ignore the others
		for category in [locale.LC_CTYPE, locale.LC_COLLATE, locale.LC_TIME, locale.LC_MONETARY, locale.LC_MESSAGES, locale.LC_NUMERIC]:
			try:
				locale.setlocale(category, (self.getLanguage(), 'UTF-8'))
			except:
				pass
		# HACK: sometimes python 2.7 reverts to the LC_TIME environment value, so make sure it has the correct value
		os.environ["LC_TIME"] = self.getLanguage() + '.UTF-8'
		os.environ["GST_SUBTITLE_ENCODING"] = self.getGStreamerSubtitleEncoding()

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

	def getGStreamerSubtitleEncoding(self):
		try:
			return str(self.lang[self.activeLanguage][3])
		except:
			return 'ISO-8859-15'

	def addCallback(self, callback):
		self.callbacks.append(callback)

language = Language()
