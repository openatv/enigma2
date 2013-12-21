# -*- coding: UTF-8 -*-
import gettext
import locale
import os

from Tools.Directories import SCOPE_LANGUAGE, resolveFilename
from time import time, localtime, strftime

LPATH = resolveFilename(SCOPE_LANGUAGE, "")

class Language:
	def __init__(self):
		gettext.install('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), unicode=0, codeset="utf-8")
		self.activeLanguage = 0
		self.catalog = None
		self.lang = {}
		self.InitLang()
		self.callbacks = []

	def InitLang(self):
		self.langlist = []
		self.ll = os.listdir(LPATH)
		# FIXME make list dynamically
		# name, iso-639 language, iso-3166 country. Please don't mix language&country!
		self.addLanguage("Deutsch", "de", "DE")
		self.addLanguage("Arabic", "ar", "AE")
		self.addLanguage("Български", "bg", "BG")
		self.addLanguage("Bokmål", "nb", "NO")
		self.addLanguage("Català", "ca", "AD")
		self.addLanguage("Česky", "cs", "CZ")
		self.addLanguage("Dansk", "da", "DK")
		self.addLanguage("Ελληνικά", "el", "GR")
		self.addLanguage("English (UK)", "en", "GB")
		self.addLanguage("English (US)", "en", "US")
		self.addLanguage("Español", "es", "ES")
		self.addLanguage("Eesti", "et", "EE")
		self.addLanguage("Persian", "fa", "IR")
		self.addLanguage("Suomi", "fi", "FI")
		self.addLanguage("Français", "fr", "FR")
		self.addLanguage("Frysk", "fy", "NL")
		self.addLanguage("Hebrew", "he", "IL")
		self.addLanguage("Hrvatski", "hr", "HR")
		self.addLanguage("Magyar", "hu", "HU")
		self.addLanguage("Íslenska", "is", "IS")
		self.addLanguage("Italiano", "it", "IT")
		self.addLanguage("Kurdish", "ku", "KU")
		self.addLanguage("Lietuvių", "lt", "LT")
		self.addLanguage("Latviešu", "lv", "LV")
		self.addLanguage("Nederlands", "nl", "NL")
		self.addLanguage("Norsk Bokmål","nb", "NO")
		self.addLanguage("Norsk", "no", "NO")
		self.addLanguage("Polski", "pl", "PL")
		self.addLanguage("Português", "pt", "PT")
		self.addLanguage("Português do Brasil", "pt", "BR")
		self.addLanguage("Romanian", "ro", "RO")
		self.addLanguage("Русский", "ru", "RU")
		self.addLanguage("Slovensky", "sk", "SK")
		self.addLanguage("Slovenščina", "sl", "SI")
		self.addLanguage("Srpski", "sr", "YU")
		self.addLanguage("Svenska", "sv", "SE")
		self.addLanguage("ภาษาไทย", "th", "TH")
		self.addLanguage("Türkçe", "tr", "TR")
		self.addLanguage("Ukrainian", "uk", "UA")

		

	def addLanguage(self, name, lang, country):
		try:
			if lang in self.ll:
				if country == "GB" or country == "BR":
					if (lang + "_" + country) in self.ll:
						self.lang[str(lang + "_" + country)] = ((name, lang, country))
						self.langlist.append(str(lang + "_" + country))
				else:
					self.lang[str(lang + "_" + country)] = ((name, lang, country))
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
				if x:
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
		os.environ["LANGUAGE"] = self.getLanguage() + '.UTF-8'

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

	def delLanguage(self, delLang = None):
		from Components.config import config, configfile
		from shutil import rmtree
		lang = config.osd.language.getValue()
		if delLang:
			print"DELETE", delLang
			if delLang == "en_US":
				print"Default Language can not be deleted !!"
				return
			elif delLang == "en_GB":
				rmtree(LPATH + delLang)
			elif delLang == "pt_BR":
				rmtree(LPATH + delLang)
			else:
				rmtree(LPATH + delLang[:2])
		else:
			ll = os.listdir(LPATH)
			for x in ll:
				print x
				if len(x) > 2:
					if x != lang:
						rmtree(LPATH + x)
				else:
					if x != lang[:2] and x != "en":
						rmtree(LPATH + x)
					elif x == "pt":
						if x != lang:
							rmtree(LPATH + x)
			os.system("touch /etc/enigma2/.removelang")

		self.InitLang()

	def updateLanguageCache(self):
		t = localtime(time())
		createdate = strftime("%d.%m.%Y  %H:%M:%S", t)
		f = open('/usr/lib/enigma2/python/Components/Language_cache.py','w')
		f.write('# -*- coding: UTF-8 -*-\n')
		f.write('# date: ' + createdate + '\n#\n\n')
		f.write('LANG_TEXT = {\n')
		for lang in self.langlist:
			catalog = gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[str(lang)])
			T1 = catalog.gettext("Please use the UP and DOWN keys to select your language. Afterwards press the OK button.")
			T2 = catalog.gettext("Language selection")
			T3 = catalog.gettext("Cancel")
			T4 = catalog.gettext("Save")
			f.write('"' + lang + '"' + ': {\n')
			f.write('\t "T1"' + ': "' + T1 + '",\n')
			f.write('\t "T2"' + ': "' + T2 + '",\n')
			f.write('\t "T3"' + ': "' + T3 + '",\n')
			f.write('\t "T4"' + ': "' + T4 + '",\n')
			f.write('},\n')
		f.write('}\n')
		f.close
		catalog = None
		lang = None

language = Language()
