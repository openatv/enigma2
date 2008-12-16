from Source import Source

class Progress(Source):
	def __init__(self, value = 0, range = 100):
		Source.__init__(self)
		self.__value = value
		self.range = range

	def getValue(self):
		return self.__value

	def setValue(self, value):
		self.__value = value
		self.changed((self.CHANGED_ALL,))
		
	def setRange(self, range = 100):
		self.range = range
		self.changed((self.CHANGED_ALL,))

	def getRange(self):
		return self.range

	value = property(getValue, setValue)
