from Converter import Converter
from enigma import eListboxPythonStringContent
from Components.Element import cached

class StringList(Converter):
	"""Turns a simple python list into a list which can be used in a listbox."""
	def __init__(self, type):
		Converter.__init__(self, type)
		self.content = None

	def changed(self, what):
		if not self.content:
			self.content = eListboxPythonStringContent()

		if self.source:
			self.content.setList(self.source.list)
		self.downstream_elements.changed(what)

	def selectionChanged(self, index):
		self.source.selectionChanged(index)
		# update all non-master targets
		for x in self.downstream_elements:
			if x is not self.master:
				x.index = index

	@cached
	def getCurrent(self):
		if self.source is None or self.index is None or self.index >= len(self.source.list):
			return None
		return self.source.list[self.index]

	current = property(getCurrent)

	# pass through: getIndex / setIndex to master
	@cached
	def getIndex(self):
		if self.master is None:
			return None
		return self.master.index

	def setIndex(self, index):
		if self.master is not None:
			self.master.index = index

	index = property(getIndex, setIndex)
