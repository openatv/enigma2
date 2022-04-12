from enigma import BT_KEEP_ASPECT_RATIO, BT_SCALE, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont

from skin import fonts, parameters
from Components.MenuList import MenuList
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

icons = None


def SelectionEntryComponent(description, value, index, selected):
	dx, dy, dw, dh = parameters.get("SelectionListDescr", (25, 3, 650, 30))
	res = [
		(description, value, index, selected),
		(eListboxPythonMultiContent.TYPE_TEXT, dx, dy, dw, dh, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, description)
	]
	global icons
	icon = icons[0] if selected else icons[1]
# 	Do we really we need SelectionListLockOff
#	ix, iy, iw, ih = parameters.get("SelectionListLock" if selected else "SelectionListLockOff", (0, 2, 25, 24))
	ix, iy, iw, ih = parameters.get("SelectionListLock", (0, 2, 25, 24))
	res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, ix, iy, iw, ih, icon, None, None, BT_SCALE | BT_KEEP_ASPECT_RATIO))
	return res


class SelectionList(MenuList):
	def __init__(self, list=None, enableWrapAround=False):
		MenuList.__init__(self, list or [], enableWrapAround=enableWrapAround, content=eListboxPythonMultiContent)
		font = fonts.get("SelectionList", ("Regular", 20, 30))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		global icons
		icons = [
			LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/lock_on.png")),
			LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/lock_off.png"))
		]

	def addSelection(self, description, value, index, selected=True):
		self.list.append(SelectionEntryComponent(description, value, index, selected))
		self.setList(self.list)

	def toggleSelection(self):
		if len(self.list):
			index = self.getSelectedIndex()
			item = self.list[index][0]
			self.list[index] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
			self.setList(self.list)

	def getSelectionsList(self):
		return [(item[0][0], item[0][1], item[0][2]) for item in self.list if item[0][3]]

	def toggleAllSelection(self):
		for index, item in enumerate(self.list):
			item = self.list[index][0]
			self.list[index] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
		self.setList(self.list)

	def removeSelection(self, selection):
		for item in self.list:
			if item[0] == selection:
				self.list.pop(self.list.index(item))
				self.setList(self.list)
				return

	def toggleItemSelection(self, selection):
		for index, item in enumerate(self.list):
			if item[0] == selection:
				selection = self.list[index][0]
				self.list[index] = SelectionEntryComponent(selection[0], selection[1], selection[2], not selection[3])
				self.setList(self.list)
				return

	def sort(self, sortType=False, flag=False):
		# Sorting by sortType:
		# 	0 - description
		# 	1 - value
		# 	2 - index
		# 	3 - selected
		self.list.sort(key=lambda x: x[0][sortType], reverse=flag)
		self.setList(self.list)
