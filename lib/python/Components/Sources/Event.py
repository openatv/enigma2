from Components.Sources.Source import Source


class Event(Source):
	def __init__(self):
		Source.__init__(self)
		self.myEvent = None

	def getCurrentEvent(self):
		return self.myEvent

	event = property(getCurrentEvent)

	def newEvent(self, event):
		if not self.myEvent or self.myEvent != event:
			self.myEvent = event
			if not event:
				self.changed((self.CHANGED_CLEAR,))
			else:
				self.changed((self.CHANGED_ALL,))
