from HTMLComponent import *
from GUIComponent import *

from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import RT_HALIGN_LEFT, MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import *

def PluginEntryComponent(plugin):
	res = [ plugin ]
	
	res.append(MultiContentEntryText(pos=(80, 5), size=(300, 25), font=0, text=plugin.name))
	res.append(MultiContentEntryText(pos=(80, 26), size=(300, 17), font=1, text=plugin.description))

	if plugin.icon is None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/plugin.png"))
	else:
		png = plugin.icon
	res.append(MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(60, 40), png = png))
	
	return res

def PluginCategoryComponent(name, png):
	res = [ name ]
	
	res.append(MultiContentEntryText(pos=(80, 5), size=(300, 25), font=0, text=name))
	res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 0), size=(60, 50), png = png))
	
	return res

def PluginDownloadComponent(plugin, name):
	res = [ plugin ]
	
	res.append(MultiContentEntryText(pos=(80, 5), size=(300, 25), font=0, text=name))
	res.append(MultiContentEntryText(pos=(80, 26), size=(300, 17), font=1, text=plugin.description))

	if plugin.icon is None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "/plugin.png"))
	else:
		png = plugin.icon
	res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 0), size=(60, 50), png = png))
	
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
