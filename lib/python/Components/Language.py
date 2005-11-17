import gettext
import os

class Language:
	def __init__(self):
		gettext.install('enigma2', '/enigma2/po')
		self.lang = []
		# FIXME make list dynamically
		self.addLanguage(_("English"), "en")
		self.addLanguage(_("German"), "de")

	def addLanguage(self, name, lang):
		try:
			self.lang.append((_(name), gettext.translation('enigma2', '/enigma2/po', languages=[lang])))
		except:
			print "Language " + str(name) + " not found"

	def activateLanguage(self, index):
		try:
			print "Activating language " + str(self.lang[index][0])
			self.lang[index][1].install()
		except:
			print "Selected language does not exist!"
		
	def getLanguageList(self):
		list = []
		for x in self.lang:
			list.append(x[0])
		return list

language = Language()
