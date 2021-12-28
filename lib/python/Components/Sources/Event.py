from Components.Sources.Source import Source


class Event(Source):
	def __init__(self):
		Source.__init__(self)
		self.evt = None

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
