from datetime import datetime
from time import localtime, mktime

from enigma import eLabel, eEPGCache

from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class PrimeTime(Renderer, VariableText):
	GUI_WIDGET = eLabel
	EVENT_TOLERANCE = 1200  # 20 minutes tolerance to starting next event.

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.epgCache = eEPGCache.getInstance()

	def changed(self, what):
		text = _("N/A")
		if self.source.event:
			if self.epgCache:
				events = self.epgCache.lookupEvent(["IBDCT", (self.source.service.toString(), 0, -1, -1)])
				if events:
					hour = config.epgselection.graph_primetimehour.value
					minute = config.epgselection.graph_primetimemins.value
					now = localtime()
					primeTime = int(mktime(datetime(now.tm_year, now.tm_mon, now.tm_mday, hour, minute).timetuple()))
					nextEvent = False
					for event in events:
						if event[4]:
							begin = event[1]
							end = event[1] + event[2]
							if begin <= primeTime and end > primeTime or nextEvent:
								if not nextEvent and end <= primeTime + self.EVENT_TOLERANCE:
									nextEvent = True
									continue
								localTime = localtime(begin)
								text = f"{localTime[3]:02d}:{localTime[4]:02d} {event[4]}"
								break
							elif begin > primeTime:  # In this case primeTime is not in the EPG.
								break
						else:
							break
		self.text = text
