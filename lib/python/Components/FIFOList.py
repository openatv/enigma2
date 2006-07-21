from Components.MenuList import MenuList

class FIFOList(MenuList):
	def __init__(self, list = [ ], len = 10):
		self.len = len
		self.list = list
		MenuList.__init__(self, self.list)
	
	def addItem(self, item):
		self.list.append(item)
		self.list = self.list[-self.len:]
		self.l.setList(self.list)

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)
