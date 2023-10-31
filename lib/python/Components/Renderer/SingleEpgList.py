from time import localtime
from enigma import eLabel, eEPGCache
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class SingleEpgList(Renderer, VariableText):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.epgcache = eEPGCache.getInstance()

	def changed(self, what):
		event = self.source.event

		if event is None:
			self.text = ""
			return

		service = self.source.service
		text = ""
		evt = None

		if self.epgcache is not None:
			evt = self.epgcache.lookupEvent(["IBDCT", (service.toString(), 0, -1, -1)])

		if evt:
			maxx = 0
			for x in evt:
				if maxx > 0:
					if x[4]:
						t = localtime(x[1])
						text = text + "%02d:%02d %s\n" % (t[3], t[4], x[4])
					else:
						text = text + "n/a\n"

				maxx += 1
				if maxx > 4:
					break

		self.text = text
