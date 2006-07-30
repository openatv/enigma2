from Source import Source
from Tools.Event import Event

class MenuList(Source, object):
	def __init__(self, list = [ ], enableWrapAround = False):
		Source.__init__(self)
		self.__list = list
		self.onSelectionChanged = [ ]
	
	def setList(self, list):
		self.__list = list
		self.changed((self.CHANGED_ALL,))
	
	list = property(lambda self: self.__list, setList)

	def entry_changed(self, index):
		self.downstream_elements.entry_changed(self, index)

	def selectionChanged(self, index):
		for x in self.onSelectionChanged:
			x()

	def getCurrent(self):
		return self.master and self.master.current

	current = property(getCurrent)

	def setIndex(self, index):
		if self.master is not None:
			self.master = index
	
	def getIndex(self, index):
		if self.master is not None:
			return self.master.index
		else:
			return -1

	setCurrentIndex = setIndex
	
	index = property(getIndex, setIndex)
