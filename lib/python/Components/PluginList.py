from HTMLComponent import *
from GUIComponent import *

from MenuList import MenuList

from Tools.Directories import *

from enigma import *

RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

def PluginEntryComponent(picture, name, desc = "Plugin"):
	res = [ None ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 80, 5, 300, 25, 0, RT_HALIGN_LEFT , name))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 80, 26, 300, 17, 1, RT_HALIGN_LEFT , desc))
	png = loadPNG(picture)
	if png == None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/plugin.png"))
	res.append((eListboxPythonMultiContent.TYPE_PIXMAP, 10, 5, 60, 40, png))
	
	return res


class PluginList(HTMLComponent, GUIComponent, MenuList):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(50)