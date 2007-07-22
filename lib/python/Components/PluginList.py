from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent

from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import loadPNG, eListboxPythonMultiContent, eListbox, gFont

def PluginEntryComponent(plugin):
	res = [ plugin ]
	
	res.append(MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=plugin.name))
	res.append(MultiContentEntryText(pos=(120, 26), size=(320, 17), font=1, text=plugin.description))

	if plugin.icon is None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "plugin.png"))
	else:
		png = plugin.icon
	res.append(MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(100, 40), png = png))
	
	return res

def PluginCategoryComponent(name, png):
	res = [ name ]
	
	res.append(MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=name))
	res.append(MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(100, 50), png = png))
	
	return res

def PluginDownloadComponent(plugin, name):
	res = [ plugin ]
	
	res.append(MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=name))
	res.append(MultiContentEntryText(pos=(120, 26), size=(320, 17), font=1, text=plugin.description))

	if plugin.icon is None:
		png = loadPNG(resolveFilename(SCOPE_SKIN_IMAGE, "plugin.png"))
	else:
		png = plugin.icon
	res.append(MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(100, 50), png = png))
	
	return res

class PluginList(MenuList, HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
