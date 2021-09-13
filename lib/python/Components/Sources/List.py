from Components.Element import cached
from Components.Sources.Source import Source


class List(Source):
	"""The datasource of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts".

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""

	def __init__(self, list=[], enableWrapAround=False, item_height=25, fonts=[]):
		Source.__init__(self)
		self.__list = list
		self.enableWrapAround = enableWrapAround
		self.item_height = item_height
		self.fonts = fonts
		self.onSelectionChanged = []
		self.disable_callbacks = False
		self.__style = "default"  # Style might be an optional string which can be used to define different visualisations in the skin.

	def setList(self, list):
		self.__list = list
		self.changed((self.CHANGED_ALL,))

	list = property(lambda self: self.__list, setList)

	def updateList(self, list):
		"""Changes the list without changing the selection or emitting changed Events"""
		maxIndex = len(list) - 1
		oldIndex = min(self.index, maxIndex)
		self.disable_callbacks = True
		self.list = list
		self.index = oldIndex
		self.disable_callbacks = False

	def entry_changed(self, index):
		if not self.disable_callbacks:
			self.downstream_elements.entry_changed(index)

	def modifyEntry(self, index, data):
		self.__list[index] = data
		self.entry_changed(index)

	def selectionChanged(self, index):
		if self.disable_callbacks:
			return
		# Update all non-master targets.
		for x in self.downstream_elements:
			if x is not self.master:
				x.index = index
		for x in self.onSelectionChanged:
			x()

	@cached
	def getCurrent(self):
		return self.master is not None and self.master.current

	current = property(getCurrent)

	@cached
	def getIndex(self):
		return self.master.index if self.master is not None else 0  # None - The 0 is a hack to avoid badly written code from crashing!

	def setIndex(self, index):
		if self.master is not None:
			self.master.index = index
			self.selectionChanged(index)

	index = property(getIndex, setIndex)

	setCurrentIndex = setIndex

	@cached
	def getStyle(self):
		return self.__style

	def setStyle(self, style):
		if self.__style != style:
			self.__style = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	def getSelectedIndex(self):
		return self.getIndex()

	def count(self):
		return len(self.__list)

	def selectPrevious(self):
		if self.getIndex() - 1 < 0:
			if self.enableWrapAround:
				self.index = self.count() - 1
		else:
			self.index -= 1
		self.setIndex(self.index)

	def selectNext(self):
		if self.getIndex() + 1 >= self.count():
			if self.enableWrapAround:
				self.index = 0
		else:
			self.index += 1
		self.setIndex(self.index)

	def top(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.moveTop)
		except AttributeError:
			return

	def pageUp(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.pageUp)
		except AttributeError:
			return

	def up(self):
		self.selectPrevious()

	def down(self):
		self.selectNext()

	def pageDown(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.pageDown)
		except AttributeError:
			return

	def bottom(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.moveEnd)
		except AttributeError:
			return
