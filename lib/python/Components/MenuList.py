from enigma import eListbox, eListboxPythonStringContent

from Components.GUIComponent import GUIComponent


class MenuList(GUIComponent):
	def __init__(self, menuList, enableWrapAround=True, content=eListboxPythonStringContent):
		GUIComponent.__init__(self)
		self.menuList = menuList
		self.enableWrapAround = enableWrapAround
		self.l = content()
		self.l.setList(self.menuList)
		self.onSelectionChanged = []

	def getCurrent(self):
		return self.l.getCurrentSelection()

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		if self.enableWrapAround:
			self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for module in self.onSelectionChanged:
			module()

	def getSelectionIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectedIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setList(self, menuList):
		self.menuList = menuList
		self.l.setList(self.menuList)

	def moveToIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def count(self):
		return len(self.menuList)

	def top(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)

	def pageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def up(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def down(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def pageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def bottom(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)
