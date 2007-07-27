from Components.VariableText import VariableText
from Components.GUIComponent import GUIComponent
from enigma import eEPGCache, eServiceReference as Ref, eLabel
from Source import Source

class Event(VariableText, GUIComponent, Source, object):
	def __init__(self, timer=None):
		Source.__init__(self)
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.event = None

	GUI_WIDGET = eLabel

	def getCurrentEvent(self):
		return self.event

	event = property(getCurrentEvent)

	def newEvent(self, event):
		if not self.event or self.event != event:
			self.event = event
			if not event:
				self.changed((self.CHANGED_CLEAR,))
			else:
				self.changed((self.CHANGED_ALL,))
