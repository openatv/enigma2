from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT

from MenuList import MenuList
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap


selectiononpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_on.png"))
selectionoffpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock_off.png"))

def SelectionEntryComponent(description, value, index, selected):
	res = [
		(description, value, index, selected),
		(eListboxPythonMultiContent.TYPE_TEXT, 25, 3, 780, 30, 0, RT_HALIGN_LEFT, description)
	]
	if selected:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 2, 25, 24, selectiononpng))
	else:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 2, 25, 24, selectionoffpng))
	return res

class SelectionList(MenuList):
	def __init__(self, list = None, enableWrapAround = False):
		MenuList.__init__(self, list or [], enableWrapAround, content = eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setItemHeight(30)

	def addSelection(self, description, value, index, selected = True):
		self.list.append(SelectionEntryComponent(description, value, index, selected))
		self.setList(self.list)

	def toggleSelection(self):
		if len(self.list) > 0:
			idx = self.getSelectedIndex()
			item = self.list[idx][0]
			self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
			self.setList(self.list)

	def getSelectionsList(self):
		return [ (item[0][0], item[0][1], item[0][2]) for item in self.list if item[0][3] ]

	def toggleAllSelection(self):
		for idx,item in enumerate(self.list):
			item = self.list[idx][0]
			self.list[idx] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
		self.setList(self.list)

