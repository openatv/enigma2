from enigma import eListbox, eListboxPythonStringContent

from Components.GUIComponent import GUIComponent


class MenuList(GUIComponent):
	GUI_WIDGET = eListbox

	def __init__(self, menuList, enableWrapAround=None, content=eListboxPythonStringContent):  # enableWrapAround is deprecated as this is now controllable in the skin and windowstyle.
		GUIComponent.__init__(self)
		self.menuList = menuList
		self.l = content()
		self.l.setList(self.menuList)
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
		return self.menuList

	def setList(self, menuList):
		self.menuList = menuList
		self.l.setList(self.menuList)

	list = property(getList, setList)

	def count(self):
		return len(self.menuList)

	def selectionChanged(self):
		for callback in self.onSelectionChanged:
			callback()

	def getCurrent(self):
		return self.l.getCurrentSelection()

	current = property(getCurrent)

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectionIndex(self):  # This method should be found and removed from all code.
		return self.getCurrentIndex()

	def getSelectedIndex(self):  # This method should be found and removed from all code.
		return self.getCurrentIndex()

	def setCurrentIndex(self, index):
		if self.instance:
			self.instance.moveSelectionTo(index)

	def moveToIndex(self, index):  # This method should be found and removed from all code.
		self.setCurrentIndex(index)

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

	# Old navigation method names.
	#
	def top(self):  # This method should be found and removed from all code.
		self.goTop()

	def pageUp(self):  # This method should be found and removed from all code.
		self.goPageUp()

	def up(self):  # This method should be found and removed from all code.
		self.goLineUp()

	def down(self):  # This method should be found and removed from all code.
		self.goLineDown()

	def pageDown(self):  # This method should be found and removed from all code.
		self.goPageDown()

	def bottom(self):  # This method should be found and removed from all code.
		self.goBottom()
