from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap

def PluginEntryComponent(plugin, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon

	return [
		plugin,
		MultiContentEntryText(pos=(120, 5), size=(width-120, 25), font=0, text=plugin.name),
		MultiContentEntryText(pos=(120, 26), size=(width-120, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(100, 40), png = png)
	]

def PluginCategoryComponent(name, png, width=440):
	return [
		name,
		MultiContentEntryText(pos=(80, 5), size=(width-80, 25), font=0, text=name),
		MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(60, 50), png = png)
	]

def PluginDownloadComponent(plugin, name, version=None, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon
	if version:
		if "+git" in version:
			# remove git "hash"
			version = "+".join(version.split("+")[:2])
		elif version.startswith('experimental-'):
			version = version[13:]
		name += "  (" + version + ")"
	return [
		plugin,
		MultiContentEntryText(pos=(80, 5), size=(width-80, 25), font=0, text=name),
		MultiContentEntryText(pos=(80, 26), size=(width-80, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(10, 0), size=(60, 50), png = png)
	]
	

class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)
