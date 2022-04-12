from Components.Element import cached
from Components.Sources.Source import Source


class HbbtvApplication(Source):
	def __init__(self):
		Source.__init__(self)
		self.appAvailable = False
		self.appName = ""
		self.appUseAit = True

	def setApplicationName(self, name):
		self.appName = name
		self.appAvailable = False
		if name:
			self.appAvailable = True
		self.changed((self.CHANGED_ALL,))

	def getUseAit(self):
		return self.appUseAit

	@cached
	def getBoolean(self):
		return self.appAvailable

	boolean = property(getBoolean)

	@cached
	def getName(self):
		return self.appName

	name = property(getName)
