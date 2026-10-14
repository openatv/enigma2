from enigma import eListboxPythonMultiContent

from Components.Converter.StringList import StringList


class StaticMultiList(StringList):
	"""Turns a python list in 'multi list format' into a list which can be used in a listbox."""

	def changed(self, what):
		if not self.content:
			self.content = eListboxPythonMultiContent()
			if self.source:
				# Setup the required item height and fonts, as given by the source.
				self.content.setItemHeight(self.source.item_height)
				for index, font in enumerate(self.source.fonts):
					self.content.setFont(index, font)
		if self.source:
			self.content.setList(self.source.list)
		print(f"[StaticMultiList] downstream_elements: {self.downstream_elements}")
		self.downstream_elements.changed(what)
