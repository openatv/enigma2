from enigma import eListbox, eListboxPythonStringContent

from Components.GUIComponent import GUIComponent


class MenuList(GUIComponent):
	GUI_WIDGET = eListbox

	def __init__(self, menuList, enableWrapAround=None, content=eListboxPythonStringContent):  # enableWrapAround is deprecated as this is now controllable in the skin and windowstyle.
		GUIComponent.__init__(self)
		self.list = menuList
		self.l = content()
		self.l.setList(self.list)
		self.onSelectionChanged = []

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def enableAutoNavigation(self, enabled):
		if self.instance:
			self.instance.enableAutoNavigation(enabled)

	def selectionEnabled(self, enabled):
		if self.instance:
			self.instance.setSelectionEnable(enabled)

	def getList(self):
		return self.list

	def setList(self, menuList):
		self.list = menuList
		self.l.setList(self.list)

	def updateEntry(self, index, data):
		if self.list and index < len(self.list):
			self.list[index] = data
			self.l.updateEntry(index, data)

	def count(self):
		return len(self.list)

	def selectionChanged(self):
		for callback in self.onSelectionChanged:
			callback()

	def getCurrent(self):
		return self.l.getCurrentSelection()

	current = property(getCurrent)

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setCurrentIndex(self, index):
		if self.instance:
			self.instance.moveSelectionTo(index)

	index = property(getCurrentIndex, setCurrentIndex)

	def getTopIndex(self):
		return self.instance.getTopIndex() if self.instance else -1

	def setTopIndex(self, index):
		if self.instance:
			self.instance.setTopIndex(index)

	def goTop(self):
		if self.instance:
			self.instance.goTop()

	def goPageUp(self):
		if self.instance:
			self.instance.goPageUp()

	def goLineUp(self):
		if self.instance:
			self.instance.goLineUp()

	def goFirst(self):
		if self.instance:
			self.instance.goFirst()

	def goLeft(self):
		if self.instance:
			self.instance.goLeft()

	def goRight(self):
		if self.instance:
			self.instance.goRight()

	def goLast(self):
		if self.instance:
			self.instance.goLast()

	def goLineDown(self):
		if self.instance:
			self.instance.goLineDown()

	def goPageDown(self):
		if self.instance:
			self.instance.goPageDown()

	def goBottom(self):
		if self.instance:
			self.instance.goBottom()

	# Old method names. This methods should be found and removed from all code.
	#
	def getSelectionIndex(self):
		return self.getCurrentIndex()

	def getSelectedIndex(self):
		return self.getCurrentIndex()

	def moveToIndex(self, index):
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
