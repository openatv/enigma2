from Components.Element import cached
from Components.Converter.Converter import Converter


class MenuEntryCompare(Converter):
	def __init__(self, token):
		Converter.__init__(self, token)
		self.entryId = token

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
			result = entryId and self.entryId and self.entryId == entryId
		return result

	boolean = property(getBool)

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))
