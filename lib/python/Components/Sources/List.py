from Components.Element import cached
from Components.Sources.Source import Source


class List(Source):
	"""The datasource of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts".

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""

	# NOTE: The calling arguments enableWraparound, item_height and fonts are not
	# used but remain here so that calling code does not need to be modified.
	# The enableWrapAround function is correctly handles by the C++ code and the 
	# use of the enableWrapAround="1" attribute in the skin. Similarly the 
	# itemHeight and font specifications are handled by the skin.
	#
	def __init__(self, list=[], enableWrapAround=False, item_height=25, fonts=[]):
		Source.__init__(self)
		self.listData = list
		self.onSelectionChanged = []
		self.disableCallbacks = False
		self.listStyle = "default"  # Style might be an optional string which can be used to define different visualizations in the skin.

	def setList(self, listData):
		self.listData = listData
		self.changed((self.CHANGED_ALL,))

	list = property(lambda self: self.listData, setList)

	def updateList(self, listData):
		"""Changes the list without changing the selection or emitting changed Events"""
		maxIndex = len(listData) - 1
		oldIndex = min(self.index, maxIndex)
		self.disableCallbacks = True
		self.setList(listData)
		self.index = oldIndex
		self.disableCallbacks = False

	def entry_changed(self, index):
		if not self.disableCallbacks:
			self.downstream_elements.entry_changed(index)

	def modifyEntry(self, index, data):
		self.listData[index] = data
		self.entry_changed(index)

	def selectionChanged(self, index):
		if self.disableCallbacks:
			return
		for x in self.downstream_elements:  # Update all non-master targets.
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
		return self.listStyle

	def setStyle(self, style):
		if self.listStyle != style:
			self.listStyle = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	def getSelectedIndex(self):
		return self.getIndex()

	def count(self):
		return len(self.listData)

	def selectPrevious(self):  # This is a hack to protect code that was modified to use the previous up/down hack!
		self.up()

	def selectNext(self):  # This is a hack to protect code that was modified to use the previous up/down hack!
		self.down()

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
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.moveUp)
		except AttributeError:
			return

	def down(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.moveDown)
		except AttributeError:
			return

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
