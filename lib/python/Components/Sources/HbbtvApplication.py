from Source import Source
from Components.Element import cached

class HbbtvApplication(Source):
	def __init__(self):
		Source.__init__(self)
		self._available = False
		self._appname = ""

	def setApplicationName(self, name):
		self._appname = name
		self._available = False
		if name is not None and name != "":
			self._available = True
		self.changed((self.CHANGED_ALL,))

	@cached
	def getBoolean(self):
		return self._available
	boolean = property(getBoolean)

	@cached
	def getName(self):
		return self._appname
	name = property(getName) 
