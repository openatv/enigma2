from Components.Sources.Source import Source


class Event(Source):
	def __init__(self):
		Source.__init__(self)
		self.myEvent = None
		self.refresh = True
		self.__meta = {}

	def getCurrentEvent(self):
		return self.myEvent

	event = property(getCurrentEvent)

	def newEvent(self, event):
		if not self.myEvent or self.myEvent != event:
			self.myEvent = event
			self.refresh = True
			self.__meta = {}
			if not event:
				self.changed((self.CHANGED_CLEAR,))
			else:
				self.changed((self.CHANGED_ALL,))

	def refreshData(self):  # will be overwritten by plugins
		pass

	def getMeta(self, key=None):
		if key is None:
			return self.__meta if isinstance(self.__meta, dict) else {}
		if self.refresh and self.myEvent:
			self.refresh = False
			self.refreshData()
		return self.__meta.get(key) if isinstance(self.__meta, dict) else None

	def setMeta(self, meta):  # will be called by plugins
		self.refresh = False
		self.__meta = meta if isinstance(meta, dict) else {}
		if self.__meta and self.__meta.get("source_key"):
			self.changed((self.CHANGED_ALL,))
