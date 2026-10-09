from enigma import eListboxPythonStringContent

from Components.Converter.Converter import Converter
from Components.Element import cached


class StringList(Converter):
	"""Turns a simple python list into a list which can be used in a listbox."""

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.content = None

	def changed(self, what):
		if not self.content:
			self.content = eListboxPythonStringContent()
		if self.source:
			self.content.setList(self.source.list)
		self.downstream_elements.changed(what)

	def entry_changed(self, index):
		if self.content:
			self.content.invalidateEntry(index)

	@cached
	def getCurrent(self):
		current = None
		if self.source is not None and self.index is not None and self.index < len(self.source.list):
			current = self.source.list[self.index]
		return current

	current = property(getCurrent)

	@cached
	def getIndex(self):  # Pass through getIndex / setIndex to master.
		return None if self.master is None else self.master.index

	def selectionChanged(self, index):
		self.source.selectionChanged(index)

	def setIndex(self, index):
		if self.master is not None:
			self.master.index = index

	index = property(getIndex, setIndex)
