from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap

def PluginEntryComponent(plugin):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon

	return [
		plugin,
		MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=plugin.name),
		MultiContentEntryText(pos=(120, 26), size=(320, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(100, 40), png = png)
	]

def PluginCategoryComponent(name, png):
	return [
		name,
		MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=name),
		MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(100, 50), png = png)
	]

def PluginDownloadComponent(plugin, name):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon

	return [
		plugin,
		MultiContentEntryText(pos=(120, 5), size=(320, 25), font=0, text=name),
		MultiContentEntryText(pos=(120, 26), size=(320, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(100, 50), png = png)
	]
	

class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)
