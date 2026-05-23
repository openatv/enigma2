from enigma import eServiceCenter

from Components.Element import cached
from Components.Sources.Source import Source


class ServiceEvent(Source):
	def __init__(self):
		Source.__init__(self)
		self.service = None
		self._event = None
		self.bouquetName = ""
		self.__meta = {}
		self.refresh = True

	@cached
	def getCurrentBouquetName(self):
		return self.bouquetName

	@cached
	def getCurrentService(self):
		return self.service

	@cached
	def getCurrentEvent(self):
		if self._event is not None:
			return self._event
		else:
			return self.service and self.info and self.info.getEvent(self.service)

	event = property(getCurrentEvent)

	@cached
	def getInfo(self):
		return self.service and eServiceCenter.getInstance().info(self.service)

	info = property(getInfo)

	def newService(self, ref, event=None):
		self.service = ref
		self._event = event
		self.__meta = {}
		if not ref:
			self.refresh = False
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.refresh = True
			self.changed((self.CHANGED_ALL,))

	def newBouquetName(self, ref):
		self.bouquetName = ref
		self.__meta = {}
		if not ref:
			self.refresh = False
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.refresh = True
			self.changed((self.CHANGED_ALL,))

	def refreshData(self):  # will be overwritten by plugins
		pass

	def getMeta(self, key=None):
		if key is None:
			return self.__meta if isinstance(self.__meta, dict) else {}
		if self.refresh:
			self.refresh = False
			self.refreshData()
		return self.__meta.get(key) if isinstance(self.__meta, dict) else None

	def setMeta(self, meta):  # will be called by plugins
		self.refresh = False
		self.__meta = meta if isinstance(meta, dict) else {}
		if self.__meta and self.__meta.get("source_key"):
			self.changed((self.CHANGED_ALL,))
