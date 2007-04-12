from enigma import eListboxPythonMultiContent
from Components.Converter.StringList import StringList

class StaticMultiList(StringList):
	"""Turns a python list in 'multi list format' into a list which can be used in a listbox."""
	def changed(self, what):
		if not self.content:
			self.content = eListboxPythonMultiContent()

			if self.source:
				# setup the required item height, as given by the source.
				self.content.setItemHeight(self.source.item_height)
			
				# also setup fonts (also given by source)
				index = 0
				for f in self.source.fonts:
					self.content.setFont(index, f)
					index += 1

		if self.source:
			self.content.setList(self.source.list)

		print "downstream_elements:", self.downstream_elements
		self.downstream_elements.changed(what)
