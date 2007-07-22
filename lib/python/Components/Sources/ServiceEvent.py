from Components.VariableText import VariableText
from Components.Element import cached
from Components.GUIComponent import GUIComponent
from enigma import eEPGCache, eServiceReference as Ref, eLabel
from Source import Source

class ServiceEvent(VariableText, GUIComponent, Source, object):
	def __init__(self):
		Source.__init__(self)
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.cur_ref = None

	GUI_WIDGET = eLabel

#TODO Add a timer to get every minute the actual event..
#but this just make sense when the Servicelist do the same thing..
	@cached
	def getCurrentEvent(self):
		epg = eEPGCache.getInstance()
		return epg and self.cur_ref and epg.startTimeQuery(self.cur_ref) != -1 and epg.getNextTimeEntry() or None

	event = property(getCurrentEvent)

	def newService(self, ref):
		if not self.cur_ref or self.cur_ref != ref:
			self.cur_ref = ref
			if not ref or (ref.flags & Ref.flagDirectory) == Ref.flagDirectory or ref.flags & Ref.isMarker:
				self.changed((self.CHANGED_CLEAR,))
			else:
				self.changed((self.CHANGED_ALL,))
