from Components.VariableText import VariableText
from Components.GUIComponent import GUIComponent
from enigma import eLabel
from Source import Source

class Event(VariableText, GUIComponent, Source, object):
	def __init__(self):
		Source.__init__(self)
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.evt = None

	GUI_WIDGET = eLabel

	def getCurrentEvent(self):
		return self.evt

	event = property(getCurrentEvent)

	def newEvent(self, event):
		if not self.evt or self.evt != event:
			self.evt = event
			if not event:
				self.changed((self.CHANGED_CLEAR,))
			else:
				self.changed((self.CHANGED_ALL,))
