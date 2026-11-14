from time import localtime

from enigma import eEPGCache, eLabel

from skin import parseBoolean
from Components.VariableText import VariableText
from Components.Renderer.Renderer import Renderer


class SingleEpgList(Renderer, VariableText):
	GUI_WIDGET = eLabel

	def __init__(self):
		self.maxEvents = 4
		self.minEvent = 1
		self.ignoreNA = False
		self.eventFormat = "IBDCTM"
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.epgcache = eEPGCache.getInstance()

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "maxEvents":
				self.maxEvents = int(value)
				attribs.remove((attrib, value))
			if attrib == "minEvent":
				self.minEvent = int(value)
				attribs.remove((attrib, value))
			if attrib == "ignoreNA":
				self.ignoreNA = parseBoolean(attrib, value)
				attribs.remove((attrib, value))
		if self.maxEvents < self.minEvent:
			self.minEvent = 1
		# "M" limits the query to 10 entries (running event included)
		self.eventFormat = "IBDCTM" if self.maxEvents < 10 else "IBDCT"
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def changed(self, what):
		event = self.source.event
		text = []
		if event:
			service = self.source.service
			if self.epgcache:
				events = self.epgcache.lookupEvent([self.eventFormat, (service.toString(), 0, -1, -1)])
				if events:
					eventCount = 0
					for event in events:
						if eventCount > 0 and eventCount >= self.minEvent:
							if event[4]:
								localTime = localtime(event[1])
								text.append(f"{localTime[3]:02d}:{localTime[4]:02d} {event[4]}")
							elif not self.ignoreNA:
								text.append(_("N/A"))

						eventCount += 1
						if eventCount > self.maxEvents:
							break

		self.text = "\n".join(text)
