from traceback import print_stack

from Components.International import international


# WARNING:  Old code refers to locales as languages!
#
class Language:
	def __init__(self):
		self.lang = {}
		for package in international.getInstalledPackages():
			locales = international.packageToLocales(package)
			if len(locales):
				language, country = international.splitLocale(locales[0])
				self.lang[locales[0]] = ((international.getLanguageNative(language), language, country, international.getLanguageEncoding(language)))

	def InitLang(self):
		pass

	def activateLanguage(self, language):
		return international.activateLocale(language)

	def getActiveLanguage(self):
		return international.getLocale()

	def addCallback(self, callback):
		if callable(callback):
			international.addCallback(callback)
		elif callback:
			print("[Language] addCallback Error: The callback '%s' is not callable!" % callback)
			print_stack()
		else:
			print("[Language] addCallback Error: The callback is blank or None!")
			print_stack()

	def getLanguage(self):
		return international.getLocale()

	def getLanguageList(self):
		languageList = []
		for language in international.getLanguageList():
			country = international.getLanguageCountryCode(language)
			locale = "%s_%s" % (language, country if country else "??")
			languageList.append((locale, (international.getLanguageNative(language), language, country, international.getLanguageEncoding(language))))
		return languageList

	def getLanguageListSelection(self):
		languageListSelection = []
		for data in self.getLanguageList():
			languageListSelection.append((data[0], data[1][0]))
		return languageListSelection

	def getActiveCatalog(self):
		return international.getActiveCatalog()


language = Language()
