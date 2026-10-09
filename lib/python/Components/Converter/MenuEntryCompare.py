from Components.Converter.Converter import Converter
from Components.Element import cached


class MenuEntryCompare(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.entry_id = tokens

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)

	@cached
	def getBool(self):
		result = False
		current = self.source.current
		if current and len(current) > 2:
			entryId = current[2]
			result = entryId and self.entry_id and self.entry_id == entryId
		return result

	boolean = property(getBool)

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))
