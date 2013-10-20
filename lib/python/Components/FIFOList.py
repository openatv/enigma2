from Components.MenuList import MenuList

class FIFOList(MenuList):
	def __init__(self, list=[]):
		self.list = list
		MenuList.__init__(self, self.list)

	def addItem(self, item):
		self.list.append(item)
		self.l.setList(self.list)
		self.selectionEnabled(True)
		self.down()

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)

	def getCurrentSelection(self):
		return self.list and self.getCurrent() or None
