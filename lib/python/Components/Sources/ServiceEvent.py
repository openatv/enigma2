from enigma import eServiceCenter

from Components.Element import cached
from Components.Sources.Source import Source


class ServiceEvent(Source):
	def __init__(self):
		Source.__init__(self)
		self.service = None
		self.bouquetName = ""

	@cached
	def getCurrentBouquetName(self):
		return self.bouquetName

	@cached
	def getCurrentService(self):
		return self.service

	@cached
	def getCurrentEvent(self):
		return self.service and self.info and self.info.getEvent(self.service)

	event = property(getCurrentEvent)

	@cached
	def getInfo(self):
		return self.service and eServiceCenter.getInstance().info(self.service)

	info = property(getInfo)

	def newService(self, ref):
		self.service = ref
		if not ref:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))

	def newBouquetName(self, ref):
		self.bouquetName = ref
		if not ref:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))
