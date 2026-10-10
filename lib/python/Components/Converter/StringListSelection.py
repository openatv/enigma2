from Components.Converter.Converter import Converter
from Components.Element import cached


class StringListSelection(Converter):
	"""Extracts the first element of the current string list element for displaying it on LCD."""

	def __init__(self, tokens):
		Converter.__init__(self, tokens)

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)

	@cached
	def getText(self):
		current = self.source.current
		return current[0] if current else None

	text = property(getText)

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))
