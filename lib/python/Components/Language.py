import gettext
import os

from Tools.Directories import *

class Language:
	def __init__(self):
		gettext.install('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), unicode=0, codeset="utf-8")
		self.activeLanguage = 0
		self.lang = {}
		self.langlist = []
		# FIXME make list dynamically
		# name, iso-639 language, iso-3166 country. Please don't mix language&country!
		self.addLanguage(_("English"), "en", "EN")
		self.addLanguage(_("German"), "de", "DE")
		self.addLanguage(_("Arabic"), "ar", "AE")
		self.addLanguage(_("Catalan"), "ca", "AD")
		self.addLanguage(_("Danish"), "da", "DK")
		self.addLanguage(_("Dutch"), "nl", "NL")
		self.addLanguage(_("Finnish"), "fi", "FI")
		self.addLanguage(_("French"), "fr", "FR")
		self.addLanguage(_("Icelandic"), "is", "IS")
		self.addLanguage(_("Italian"), "it", "IT")
		self.addLanguage(_("Norwegian"), "no", "NO")
		self.addLanguage(_("Spanish"), "es", "ES")
		self.addLanguage(_("Swedish"), "sv", "SE")
		self.addLanguage(_("Turkish"), "tr", "TR")
		
		self.callbacks = []

	def addLanguage(self, name, lang, country):
		try:
			self.lang[str(lang + "_" + country)] = ((_(name), gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[lang]), lang, country))
			self.langlist.append(str(lang + "_" + country))
		except:
			print "Language " + str(name) + " not found"

	def activateLanguage(self, index):
		try:
			print "Activating language " + str(self.lang[index][0])
			self.lang[index][1].install()
			self.activeLanguage = index
			for x in self.callbacks:
				x()
		except:
			print "Selected language does not exist!"

	def getLanguageList(self):
		list = []
		for x in self.langlist:
			list.append((x, self.lang[x]))
		return list

	def getActiveLanguage(self):
		return self.activeLanguage

	def getLanguage(self):
		try:
			return str(self.lang[self.activeLanguage][2]) + "_" + str(self.lang[self.activeLanguage][3])
		except:
			return ''

	def addCallback(self, callback):
		self.callbacks.append(callback)

language = Language()
