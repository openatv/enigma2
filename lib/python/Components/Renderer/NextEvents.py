from time import localtime

from enigma import eEPGCache, eLabel

from Components.VariableText import VariableText
from Components.Renderer.Renderer import Renderer


class NextEvents(VariableText, Renderer):
	GUI_WIDGET = eLabel

	def __init__(self):
		self.lines = False
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.epgcache = eEPGCache.getInstance()

	def applySkin(self, desktop, parent):
		self.number = 0
		attribs = []
		for (attrib, value) in self.skinAttributes:
			match attrib:
				case "lines":
					self.number = int(value) + 1
					self.lines = True
				case "number":
					self.number = int(value)
				case _:
					attribs.append((attrib, value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ""
		else:
			list = self.epgcache.lookupEvent(["BDT", (self.source.text, 0, -1, 360)])
			text = ""
			if len(list):
				if self.lines:
					i = 1
					for event in list:
						if len(event) == 3 and i == self.number:
							text = text + self.build_eventstr(event)
							break
						elif len(event) == 3 and i > 1 and ((self.number > 0 and i < self.number) or self.number == 0):
							text = text + self.build_eventstr(event)
						i += 1
						if i > 7:
							break
				else:
					i = 1
					for event in list:
						if len(event) == 3 and i == int(self.number):
							text = text + self.build_eventstr(event)
							break
						elif len(event) == 3 and i > 1 and self.number == 0:
							text = text + self.build_eventstr(event)
						i += 1
						if i > 7:
							break
			self.text = text

	def build_eventstr(self, event):
		begin = localtime(event[0])
		end = localtime(event[0] + event[1])
		return ("%02d:%02d - %02d:%02d %s\n" % (begin[3], begin[4], end[3], end[4], event[2]))
