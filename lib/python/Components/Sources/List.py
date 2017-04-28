from Source import Source
from Components.Element import cached
from enigma import eListbox

class List(Source, object):
	"""The datasource of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts".

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""
	def __init__(self, list=None, enableWrapAround=None, item_height=25, fonts=None):
		if not list:
			list = []
		if not fonts:
			fonts = []
		Source.__init__(self)
		self.__list = list
		self.onSelectionChanged = []
		self.item_height = item_height
		self.fonts = fonts
		self.disable_callbacks = False
		self.enableWrapAround = enableWrapAround
		self.__style = "default"  # style might be an optional string which can be used to define different visualisations in the skin

	def setList(self, list):
		self.__list = list
		if self.enableWrapAround is not None and self.enableWrapAround != self.wrap_around:
			self.wrap_around = self.enableWrapAround
		self.changed((self.CHANGED_ALL,))

	list = property(lambda self: self.__list, setList)

	def entry_changed(self, index):
		if not self.disable_callbacks:
			self.downstream_elements.entry_changed(index)

	def modifyEntry(self, index, data):
		self.__list[index] = data
		self.entry_changed(index)

	def count(self):
		return len(self.__list)

	# pass through: getWrapAround / setWrapAround to master
	@cached
	def getWrapAround(self):
		if self.master is None:
			return None
		return self.master.wrap_around

	def setWrapAround(self, wrap_around):
		if self.master is not None:
			self.master.wrap_around = wrap_around

	wrap_around = property(getWrapAround, setWrapAround)

	def selectionChanged(self, index):
		if self.disable_callbacks:
			return

		# update all non-master targets
		for x in self.downstream_elements:
			if x is not self.master:
				x.index = index

		for x in self.onSelectionChanged:
			x()

	@cached
	def getCurrent(self):
		return self.master is not None and self.master.current

	current = property(getCurrent)

	def setIndex(self, index):
		if self.master is not None:
			self.master.index = index
			self.selectionChanged(index)

	@cached
	def getIndex(self):
		if self.master is not None:
			return self.master.index
		else:
			return None

	setCurrentIndex = setIndex

	index = property(getIndex, setIndex)

	_operation_fallbacks = {
		eListbox.moveDown: 1,
		eListbox.moveUp: -1,
		eListbox.pageDown: 10,
		eListbox.pageUp: -10,
	}

	def _doMove(self, operation, wrap_around):
		oldPos = self.index
		self.move(operation)
		newPos = self.index
		if oldPos is not None and oldPos == newPos:
			offset = self._operation_fallbacks.get(operation, 0);
			newPos += offset
			listEnd = self.count() - 1
			if 0 <= newPos <= listEnd or not wrap_around:
				self.index = min(newPos, listEnd)
			elif newPos < 0:
				self.index = listEnd
			else:
				self.index = 0

	def selectNext(self):
		self._doMove(eListbox.moveDown, self.wrap_around)

	def selectPrevious(self):
		self._doMove(eListbox.moveUp, self.wrap_around)


	@cached
	def getStyle(self):
		return self.__style

	def setStyle(self, style):
		if self.__style != style:
			self.__style = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	def updateList(self, list):
		"""Changes the list without changing the selection or emitting changed Events"""
		assert len(list) == len(self.__list)
		old_index = self.index
		self.disable_callbacks = True
		self.list = list
		self.index = old_index
		self.disable_callbacks = False

	@cached
	def getSelectionEnabled(self):
		return self.master and self.master.selectionEnabled

	def setSelectionEnabled(self, enabled):
		if self.master is not None:
			self.master.setSelectionEnabled(enabled)

	selectionEnabled = property(getSelectionEnabled, setSelectionEnabled)

	def move(self, direction):
		if self.master is not None:
			self.master.move(direction)

	def pageUp(self):
		self._doMove(eListbox.pageUp, False)

	def pageDown(self):
		self._doMove(eListbox.pageDown, False)

	def up(self):
		self.selectPrevious()

	def down(self):
		self.selectNext()

	def getSelectedIndex(self):
		return self.getIndex()
