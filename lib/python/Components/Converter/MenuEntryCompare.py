from Components.Converter.Converter import Converter
from Components.Element import cached

class MenuEntryCompare(Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		self.entry_id = type

	def selChanged(self):
		self.downstream_elements.changed((self.CHANGED_ALL, 0))

	@cached
	def getBool(self):
		id = self.entry_id
		cur = self.source.current
		if cur and len(cur) > 2:
			EntryID = cur[2]
			return EntryID and id and id == EntryID
		return False

	boolean = property(getBool)

	def changed(self, what):
		if what[0] == self.CHANGED_DEFAULT:
			self.source.onSelectionChanged.append(self.selChanged)
		Converter.changed(self, what)
