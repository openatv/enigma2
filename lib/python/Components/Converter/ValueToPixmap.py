from os.path import join
from Components.Converter.Converter import Converter
from Components.Element import ElementError, cached
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class ValueToPixmap(Converter):
	LANGUAGE_CODE = 0
	PATH = 1

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"LanguageCode": self.LANGUAGE_CODE,
			"Path": self.PATH
		}.get(tokens)
		if self.type is None:
			raise ElementError(f"'{tokens}' is not <LanguageCode|Path> for ValueToPixmap converter")

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == self.type:
			Converter.changed(self, what)

	@cached
	def getPixmap(self):
		pixmap = None
		value = self.source.text if self.source else None
		if value:
			match self.type:
				case self.LANGUAGE_CODE:
					for scope, fileName in ((SCOPE_GUISKIN, f"{value[3:].lower()}.png"), (SCOPE_GUISKIN, f"{value}.png"), (SCOPE_GUISKIN, "missing.png"), (SCOPE_SKINS, "missing.png")):
						pixmap = LoadPixmap(cached=True, path=resolveFilename(scope, join("countries", fileName)))
						if pixmap is not None:
							break
				case self.PATH:
					pixmap = LoadPixmap(value)
		return pixmap

	pixmap = property(getPixmap)
