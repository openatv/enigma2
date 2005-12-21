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

def PluginEntryComponent(picture, name):
	res = [ None ]
	res.append((80, 10, 200, 50, 0, RT_HALIGN_LEFT , name))
	png = loadPNG(picture)
	if png == None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/countries/missing.png"))
	res.append((10, 5, 60, 40, png))
	
	return res


class PluginList(HTMLComponent, GUIComponent, MenuList):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont("Arial", 20))
		self.l.setFont(1, gFont("Arial", 10))
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(50)