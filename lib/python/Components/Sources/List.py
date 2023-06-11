from Components.Element import cached
from Components.Sources.Source import Source


class List(Source):
	"""The data source of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts".

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""

	# NOTE: The calling arguments enableWraparound, item_height and fonts are not
	# used but remain here so that calling code does not need to be modified.
	# The enableWrapAround function is correctly handled by the C++ code and the
	# use of the enableWrapAround="1" attribute in the skin. Similarly the
	# itemHeight and font specifications are handled by the skin.
	#
	def __init__(self, list=None, enableWrapAround=None, item_height=0, fonts=None):
		Source.__init__(self)
		self.listData = list or []
		self.listStyle = "default"  # Style might be an optional string which can be used to define different visualizations in the skin.
		self.onSelectionChanged = []
		self.disableCallbacks = False

	def enableAutoNavigation(self, enabled):
		try:
			instance = self.master.master.instance
			instance.enableAutoNavigation(enabled)
		except AttributeError:
			return

	def getList(self):
		return self.listData

	def setList(self, listData):
		self.listData = listData
		self.changed((self.CHANGED_ALL,))

	list = property(getList, setList)

	def updateList(self, listData):
		"""Changes the list without changing the selection or emitting changed Events"""
		maxIndex = len(listData) - 1
		oldIndex = min(self.index, maxIndex)
		self.disableCallbacks = True
		self.setList(listData)
		self.index = oldIndex
		self.disableCallbacks = False

	def count(self):
		return len(self.listData)

	def selectionChanged(self, index):
		if self.disableCallbacks:
			return
		for element in self.downstream_elements:  # Update all non-master targets.
			if element is not self.master:
				element.index = index
		for callback in self.onSelectionChanged:
			callback()

	def entryChanged(self, index):
		if not self.disableCallbacks:
			self.downstream_elements.entry_changed(index)

	def modifyEntry(self, index, data):
		self.listData[index] = data
		self.entryChanged(index)

	@cached
	def getCurrent(self):
		return self.master is not None and self.master.current

	current = property(getCurrent)

	@cached
	def getCurrentIndex(self):
		return self.master.index if self.master is not None else 0  # None - The 0 is a hack to avoid badly written code from crashing!

	def setCurrentIndex(self, index):
		if self.master is not None:
			self.master.index = index
			self.selectionChanged(index)

	def setIndex(self, index):  # This method should be found and removed from all code.
		return self.setCurrentIndex(index)

	index = property(getCurrentIndex, setCurrentIndex)

	def getTopIndex(self):
		try:
			instance = self.master.master.instance
			return instance.getTopIndex()
		except AttributeError:
			return -1

	def setTopIndex(self, index):
		try:
			instance = self.master.master.instance
			instance.setTopIndex(index)
		except AttributeError:
			return

	@cached
	def getStyle(self):
		return self.listStyle

	def setStyle(self, style):
		if self.listStyle != style:
			self.listStyle = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	def show(self):
		try:
			instance = self.master.master.instance
			instance.show()
		except AttributeError:
			return

	def hide(self):
		try:
			instance = self.master.master.instance
			instance.hide()
		except AttributeError:
			return

	def setVisible(self, visble):
		if visble:
			self.show()
		else:
			self.hide()

	def getVisible(self):
		try:
			instance = self.master.master.instance
			return instance.isVisible()
		except AttributeError:
			return False

	visible = property(getVisible, setVisible)

	def goTop(self):
		try:
			instance = self.master.master.instance
			instance.goTop()
		except AttributeError:
			return

	def goPageUp(self):
		try:
			instance = self.master.master.instance
			instance.goPageUp()
		except AttributeError:
			return

	def goLineUp(self):
		try:
			instance = self.master.master.instance
			instance.goLineUp()
		except AttributeError:
			return

	def goFirst(self):
		try:
			instance = self.master.master.instance
			instance.goFirst()
		except AttributeError:
			return

	def goLeft(self):
		try:
			instance = self.master.master.instance
			instance.goLeft()
		except AttributeError:
			return

	def goRight(self):
		try:
			instance = self.master.master.instance
			instance.goRight()
		except AttributeError:
			return

	def goLast(self):
		try:
			instance = self.master.master.instance
			instance.goLast()
		except AttributeError:
			return

	def goLineDown(self):
		try:
			instance = self.master.master.instance
			instance.goLineDown()
		except AttributeError:
			return

	def goPageDown(self):
		try:
			instance = self.master.master.instance
			instance.goPageDown()
		except AttributeError:
			return

	def goBottom(self):
		try:
			instance = self.master.master.instance
			instance.goBottom()
		except AttributeError:
			return

	# These hacks protect code that was modified to use the previous up/down hack!   This methods should be found and removed from all code.
	#
	def selectPrevious(self):
		self.goLineUp()

	def selectNext(self):
		self.goLineDown()

	# Old method names. This methods should be found and removed from all code.
	#
	def getSelectedIndex(self):
		return self.getCurrentIndex()

	def getIndex(self):
		return self.getCurrentIndex()

	def top(self):
		self.goTop()

	def pageUp(self):
		self.goPageUp()

	def up(self):
		self.goLineUp()

	def down(self):
		self.goLineDown()

	def pageDown(self):
		self.goPageDown()

	def bottom(self):
		self.goBottom()
