from Source import Source
from Components.Element import cached

class List(Source, object):
	"""The datasource of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts". 

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""
	def __init__(self, list = [ ], enableWrapAround = False, item_height = 25, fonts = [ ]):
		Source.__init__(self)
		self.__list = list
		self.onSelectionChanged = [ ]
		self.item_height = item_height
		self.fonts = fonts
		self.disable_callbacks = False

	def setList(self, list):
		self.__list = list
		self.changed((self.CHANGED_ALL,))

	list = property(lambda self: self.__list, setList)

	def entry_changed(self, index):
		if not self.disable_callbacks:
			self.downstream_elements.entry_changed(self, index)

	def selectionChanged(self, index):
		if self.disable_callbacks:
			return

		for x in self.onSelectionChanged:
			x()

	@cached
	def getCurrent(self):
		return self.master is not None and self.master.current

	current = property(getCurrent)

	def setIndex(self, index):
		if self.master is not None:
			self.master.index = index

	@cached
	def getIndex(self):
		if self.master is not None:
			return self.master.index
		else:
			return None

	setCurrentIndex = setIndex

	index = property(getIndex, setIndex)

	def updateList(self, list):
		"""Changes the list without changing the selection or emitting changed Events"""
		assert len(list) == len(self.__list)
		print "get old index"
		old_index = self.index
		print "disable callback"
		self.disable_callbacks = True
		print "set list"
		self.list = list
		print "set index"
		self.index = old_index
		print "reenable callbacks"
		self.disable_callbacks = False
		print "done"
