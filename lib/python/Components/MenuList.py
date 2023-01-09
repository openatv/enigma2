from enigma import eListbox, eListboxPythonStringContent

from Components.GUIComponent import GUIComponent


class MenuList(GUIComponent):
	GUI_WIDGET = eListbox

	def __init__(self, list, enableWrapAround=None, content=eListboxPythonStringContent):  # enableWrapAround is deprecated as this is now controllable in the skin and windowstyle.
		GUIComponent.__init__(self)
		self.list = list
		self.l = content()
		self.l.setList(self.list)
		self.onSelectionChanged = []

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for callback in self.onSelectionChanged:
			callback()

	def getList(self):
		return self.list

	def setList(self, list):
		self.list = list
		self.l.setList(self.list)

	def selectionEnabled(self, enabled):
		if self.instance:
			self.instance.setSelectionEnable(enabled)

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectionIndex(self):
		return self.getCurrentIndex()

	def getSelectedIndex(self):
		return self.getCurrentIndex()

	def count(self):
		return len(self.list)

	def setCurrentIndex(self, index):
		if self.instance:
			self.instance.moveSelectionTo(index)

	def moveToIndex(self, index):
		self.setCurrentIndex(index)

	def goTop(self):
		if self.instance:
			self.instance.goTop()

	def goPageUp(self):
		if self.instance:
			self.instance.goPageUp()

	def goLineUp(self):
		if self.instance:
			self.instance.goLineUp()

	def goLineDown(self):
		if self.instance:
			self.instance.goLineDown()

	def goPageDown(self):
		if self.instance:
			self.instance.goPageDown()

	def goBottom(self):
		if self.instance:
			self.instance.goBottom()

	def getTopIndex(self):
		return self.instance.getTopIndex() if self.instance else -1

	def setTopIndex(self, index):
		if self.instance:
			self.instance.setTopIndex(index)

	# Old navigation method names.
	#
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
