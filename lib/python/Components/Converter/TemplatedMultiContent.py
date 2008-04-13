from Components.Converter.StringList import StringList

class TemplatedMultiContent(StringList):
	"""Turns a python tuple list into a multi-content list which can be used in a listbox renderer."""
	def __init__(self, args):
		StringList.__init__(self, args)
		from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_VALIGN_BOTTOM
		from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest
		l = locals()
		del l["self"] # cleanup locals a bit
		del l["args"]

		self.template = eval(args, {}, l)
		assert "fonts" in self.template
		assert "itemHeight" in self.template
		assert "template" in self.template

	def changed(self, what):
		if not self.content:
			from enigma import eListboxPythonMultiContent
			self.content = eListboxPythonMultiContent()
			self.content.setItemHeight(self.template["itemHeight"])
			self.content.setTemplate(self.template["template"])

			# also setup fonts (also given by source)
			index = 0
			for f in self.template["fonts"]:
				self.content.setFont(index, f)
				index += 1

		if self.source:
			self.content.setList(self.source.list)

		self.downstream_elements.changed(what)
