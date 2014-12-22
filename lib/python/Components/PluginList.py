from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend

from enigma import eListboxPythonMultiContent, gFont, getDesktop
from Tools.LoadPixmap import LoadPixmap

def PluginEntryComponent(plugin, width=540):
	screenwidth = getDesktop(0).size().width()
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/plugin.png"))
	else:
		png = plugin.icon
	
	if screenwidth and screenwidth == 1920:
		return [
		plugin,
		MultiContentEntryText(pos=(180, 1), size=(width-120, 35), font=2, text=plugin.name),
		MultiContentEntryText(pos=(180, 38), size=(width-120, 25), font=3, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 5), size=(150, 60), png = png)
		]
	else:
		return [
		plugin,
		MultiContentEntryText(pos=(120, 5), size=(width-120, 25), font=0, text=plugin.name),
		MultiContentEntryText(pos=(120, 26), size=(width-120, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 5), size=(100, 40), png = png)
		]
	
def PluginCategoryComponent(name, png, width=440):
	screenwidth = getDesktop(0).size().width()
	if screenwidth and screenwidth == 1920:
		return [
		name,
		MultiContentEntryText(pos=(110, 15), size=(width-80, 35), font=2, text=name),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 0), size=(90, 75), png = png)
		]
	else:
		return [
		name,
		MultiContentEntryText(pos=(80, 5), size=(width-80, 25), font=0, text=name),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 0), size=(60, 50), png = png)
		]

def PluginDownloadComponent(plugin, name, version=None, width=440):
	screenwidth = getDesktop(0).size().width()
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/plugin.png"))
	else:
		png = plugin.icon
	if version:
		if "+git" in version:
			# remove git "hash"
			version = "+".join(version.split("+")[:2])
		elif version.startswith('experimental-'):
			version = version[13:]
		name += "  (" + version + ")"
	if screenwidth and screenwidth == 1920:
		return [
		plugin,
		MultiContentEntryText(pos=(110, 1), size=(width-80, 35), font=2, text=name),
		MultiContentEntryText(pos=(110, 38), size=(width-80, 25), font=3, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 0), size=(90, 75), png = png)
		]
	else:
		return [
		plugin,
		MultiContentEntryText(pos=(80, 5), size=(width-80, 25), font=0, text=name),
		MultiContentEntryText(pos=(80, 26), size=(width-80, 17), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(10, 0), size=(60, 50), png = png)
		]


class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setFont(2, gFont("Regular", 32))
		self.l.setFont(3, gFont("Regular", 24))
		self.l.setItemHeight(50)
