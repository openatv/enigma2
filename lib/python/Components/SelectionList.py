from GUIComponent import GUIComponent
from MenuList import MenuList
from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from enigma import eListboxPythonMultiContent, loadPNG, eListbox, gFont, RT_HALIGN_LEFT

selectionpng = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "selectioncross-fs8.png"))

def SelectionEntryComponent(description, value, index, selected):
	res = [ (description, value, index, selected) ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 30, 3, 500, 30, 0, RT_HALIGN_LEFT, description))
	if selected:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, 30, 30, selectionpng))
	return res

class SelectionList(MenuList, GUIComponent):
	def __init__(self, list = []):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.setList(list)
		self.l.setFont(0, gFont("Regular", 20))

	GUI_WIDGET = eListbox
		
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(30)

	def addSelection(self, description, value, index, selected = True):
		self.list.append(SelectionEntryComponent(description, value, index, selected))
		self.setList(self.list)
		
	def toggleSelection(self):
		item = self.list[self.getSelectedIndex()][0]
		self.list[self.getSelectedIndex()] = SelectionEntryComponent(item[0], item[1], item[2], not item[3])
		self.setList(self.list)
		
	def getSelectionsList(self):
		list = []
		for item in self.list:
			if item[0][3]:
				list.append((item[0][0], item[0][1], item[0][2]))
		return list