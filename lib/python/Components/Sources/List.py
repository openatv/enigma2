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
	def __init__(self, list=None, enableWrapAround=None, item_height=0, fonts=None, templateName=None, indexNames=None):
		Source.__init__(self)
		self.listData = list or []
		self.listTemplate = templateName or "Default"  # Style might be an optional string which can be used to define different visualizations in the skin.
		self.listStyle = "default"  # Style might be an optional string which can be used to define different visualizations in the skin.
		self.listIndexNames = indexNames or {}
		self.onSelectionChanged = []
		self.onListUpdated = []
		self.disableCallbacks = False
		self.__current = None  # current element set from connected GUI element
		self.__index = 0  # current index set from connected GUI element
		self.connectedGuiElement = None  # manuallyconnected GUI element

	def enableAutoNavigation(self, enabled):
		try:
			instance = self.master.master.instance
			instance.enableAutoNavigation(enabled)
		except AttributeError:
			pass

	def getList(self):
		return self.listData

	def setList(self, listData):
		self.listData = listData
		self.changed((self.CHANGED_ALL,))
		self.listUpdated()

	list = property(getList, setList)

	def count(self):
		return len(self.listData)

	def updateList(self, listData):
		"""Changes the list without changing the selection or emitting changed Events"""
		maxIndex = len(listData) - 1
		oldIndex = min(self.index, maxIndex)
		self.disableCallbacks = True
		self.setList(listData)
		self.index = oldIndex
		self.disableCallbacks = False

	def updateEntry(self, index, data):
		self.listData[index] = data
		self.entryChanged(index)

	def selectionEnabled(self, enabled):
		try:
			instance = self.master.master.instance
			instance.setSelectionEnable(enabled)
		except AttributeError:
			pass

	# this is for manually set which is the GUI element connected with the list
	# For use in case of addons where there is no source so to rely on the master
	def setConnectedGuiElement(self, guiElement):
		self.connectedGuiElement = guiElement
		index = guiElement.instance.getCurrentIndex()
		self.__current = self.listData[index]
		self.__index = index
		self.changed((self.CHANGED_ALL,))

	def selectionChanged(self, index):
		if not self.disableCallbacks:
			for element in self.downstream_elements:  # Update all non-master targets.
				if element is not self.master:
					element.index = index
			for callback in self.onSelectionChanged:
				callback()

	def entryChanged(self, index):  # Only used in CutListEditor.
		if not self.disableCallbacks:
			self.downstream_elements.entry_changed(index)

	@cached
	def getCurrent(self):
		return self.master.current if self.master and hasattr(self.master, "current") else self.__current

	current = property(getCurrent)

	@cached
	def getCurrentIndex(self):
		return self.master.index if self.master is not None and hasattr(self.master, "index") else self.__index

	def setCurrentIndex(self, index):
		if self.master is not None:
			if hasattr(self.master, "index"):
				self.master.index = index
			else:
				self.__index = index
			self.selectionChanged(index)
		if self.connectedGuiElement is not None:
			self.connectedGuiElement.moveSelection(index)

	index = property(getCurrentIndex, setCurrentIndex)

	def getTopIndex(self):
		try:
			instance = self.master.master.instance
			result = instance.getTopIndex()
		except AttributeError:
			result = -1
		return result

	def setTopIndex(self, index):
		try:
			instance = self.master.master.instance
			instance.setTopIndex(index)
		except AttributeError:
			pass

	@cached
	def getTemplate(self):
		return self.listTemplate

	def setTemplate(self, template):
		if self.listTemplate != template:
			self.listTemplate = template
			self.changed((self.CHANGED_SPECIFIC, "template"))

	template = property(getTemplate, setTemplate)

	@cached
	def getMode(self):
		return self.listStyle

	def setMode(self, mode):
		self.setStyle(mode)

	mode = property(getMode, setMode)

	@cached
	def getStyle(self):
		return self.listStyle

	def setStyle(self, style):
		if self.listStyle != style:
			self.listStyle = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	@cached
	def getIndexNames(self):
		return self.listIndexNames

	indexNames = property(getIndexNames)

	def setVisible(self, visble):
		if visble:
			self.show()
		else:
			self.hide()

	def getVisible(self):
		try:
			instance = self.master.master.instance
			result = instance.isVisible()
		except AttributeError:
			result = False
		return result

	visible = property(getVisible, setVisible)

	def show(self):
		try:
			instance = self.master.master.instance
			instance.show()
		except AttributeError:
			pass

	def hide(self):
		try:
			instance = self.master.master.instance
			instance.hide()
		except AttributeError:
			pass

	def goTop(self):
		try:
			instance = self.master.master.instance
			instance.goTop()
		except AttributeError:
			pass

	def goPageUp(self):
		try:
			instance = self.master.master.instance
			instance.goPageUp()
		except AttributeError:
			pass

	def goLineUp(self):
		try:
			instance = self.master.master.instance
			instance.goLineUp()
		except AttributeError:
			pass

	def goFirst(self):
		try:
			instance = self.master.master.instance
			instance.goFirst()
		except AttributeError:
			pass

	def goLeft(self):
		try:
			instance = self.master.master.instance
			instance.goLeft()
		except AttributeError:
			pass

	def goRight(self):
		try:
			instance = self.master.master.instance
			instance.goRight()
		except AttributeError:
			pass

	def goLast(self):
		try:
			instance = self.master.master.instance
			instance.goLast()
		except AttributeError:
			pass

	def goLineDown(self):
		try:
			instance = self.master.master.instance
			instance.goLineDown()
		except AttributeError:
			pass

	def goPageDown(self):
		try:
			instance = self.master.master.instance
			instance.goPageDown()
		except AttributeError:
			pass

	def goBottom(self):
		try:
			instance = self.master.master.instance
			instance.goBottom()
		except AttributeError:
			pass

	def listUpdated(self):
		for method in self.onListUpdated:
			method()

	# These hacks protect code that was modified to use the previous up/down hack!   These methods should be found and removed from all code.
	#
	def selectPrevious(self):
		self.goLineUp()

	def selectNext(self):
		self.goLineDown()

	# Old method names. These methods should be found and removed from all code.
	#
	def entry_changed(self, index):
		self.entryChanged(index)

	def modifyEntry(self, index, data):  # This is only used by CutListEditor.
		self.updateEntry(index, data)

	def getSelectedIndex(self):
		return self.getCurrentIndex()

	def getIndex(self):
		return self.getCurrentIndex()

	def setIndex(self, index):
		self.setCurrentIndex(index)

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
