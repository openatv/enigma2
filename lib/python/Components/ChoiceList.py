from HTMLComponent import *
from GUIComponent import *
from MenuList import MenuList
from Tools.Directories import SCOPE_SKIN_IMAGE, resolveFilename
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, eListbox, gFont, loadPNG

def ChoiceEntryComponent(key, text):
	res = [ text ]
	if text[0] == "--":
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 00, 800, 25, 0, RT_HALIGN_LEFT, "-"*200))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 32, 00, 800, 25, 0, RT_HALIGN_LEFT, text[0]))
	
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "key_" + key + "-fs8.png"))
		if png is not None:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, 30, 20, png))
	
	return res

class ChoiceList(MenuList, HTMLComponent, GUIComponent):
	def __init__(self, list, selection = 0):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setItemHeight(25)
		self.selection = selection

	GUI_WIDGET = eListbox
		
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		self.moveToIndex(self.selection)
