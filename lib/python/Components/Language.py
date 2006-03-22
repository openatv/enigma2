import gettext
import os

from Tools.Directories import *

class Language:
	def __init__(self):
		gettext.install('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), unicode=0, codeset="utf-8")
		self.activeLanguage = 0
		self.lang = []
		# FIXME make list dynamically
		# name, iso-639 language, iso-3166 country. Please don't mix language&country!
		self.addLanguage(_("English"), "en", "EN")
		self.addLanguage(_("German"), "de", "DE")
		self.addLanguage(_("Arabic"), "ar", "AE")
		self.addLanguage(_("Dutch"), "nl", "NL")
		self.addLanguage(_("Spanish"), "es", "ES")
		self.addLanguage(_("Icelandic"), "is", "IS")
		
		self.callbacks = []

	def addLanguage(self, name, lang, country):
		try:
			self.lang.append((_(name), gettext.translation('enigma2', resolveFilename(SCOPE_LANGUAGE, ""), languages=[lang]), lang, country))
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
		for x in self.lang:
			list.append(x[0])
		return list
	
	def getLanguage(self):
		return str(self.lang[self.activeLanguage][2]) + "_" + str(self.lang[self.activeLanguage][3])
	
	def addCallback(self, callback):
		self.callbacks.append(callback)
		
language = Language()
