from Components.Converter.Converter import Converter
from Components.Element import cached, ElementError
from Tools.Directories import fileExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class ValueToPixmap(Converter, object):
	LANGUAGE_CODE = 0
	PATH = 1
	
	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "LanguageCode":
			self.type = self.LANGUAGE_CODE
		elif type == "Path":
			self.type = self.PATH
		else:
			raise ElementError("'%s' is not <LanguageCode|Path> for ValueToPixmap converter" % type)

	@cached
	def getPixmap(self):
		if self.source:
			val = self.source.text
			if val in (None, ""):
				return None
		if self.type == self.PATH:
			return LoadPixmap(val)
		if self.type == self.LANGUAGE_CODE:
			png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "countries/" + val[3:].lower() + ".png"))
			if png == None:
				png = LoadPixmap(cached=True, path=resolveFilename(SCOPE_SKIN_IMAGE, "countries/missing.png"))
			return png
		return None			
	
	pixmap = property(getPixmap)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == self.type:
			Converter.changed(self, what)

