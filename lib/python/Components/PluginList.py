from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend

from enigma import eListboxPythonMultiContent, gFont, BT_SCALE, BT_KEEP_ASPECT_RATIO
from Tools.LoadPixmap import LoadPixmap
import skin

def PluginEntryComponent(plugin, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/plugin.png"))
	else:
		png = plugin.icon
	nx, ny, nh = skin.parameters.get("PluginBrowserName",(120, 5, 25))
	dx, dy, dh = skin.parameters.get("PluginBrowserDescr",(120, 26, 17))
	ix, iy, iw, ih = skin.parameters.get("PluginBrowserIcon",(10, 5, 100, 40))
	return [
		plugin,
		MultiContentEntryText(pos=(nx, ny), size=(width-nx, nh), font=0, text=plugin.name),
		MultiContentEntryText(pos=(nx, dy), size=(width-dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png = png, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO)
	]

def PluginEntryComponentSelected(plugin, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/plugin.png"))
	else:
		png = plugin.icon
	nx, ny, nh = skin.parameters.get("PluginBrowserName",(120, 5, 25))
	dx, dy, dh = skin.parameters.get("PluginBrowserDescr",(120, 26, 17))
	ix, iy, iw, ih = skin.parameters.get("PluginBrowserIcon",(10, 5, 100, 40))
	return [
		plugin,
		MultiContentEntryText(pos=(nx, ny), size=(width-nx, nh), backcolor_sel = 0xDC143C),
		MultiContentEntryText(pos=(nx, dy), size=(width-dx, dh), backcolor_sel = 0xDC143C),
		MultiContentEntryText(pos=(nx, ny), size=(width-nx, nh), font=0, text=plugin.name),
		MultiContentEntryText(pos=(nx, dy), size=(width-dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png = png, flags = BT_SCALE | BT_KEEP_ASPECT_RATIO)
	]

def PluginCategoryComponent(name, png, width=440):
	x, y, h = skin.parameters.get("PluginBrowserDownloadName",(80, 5, 25))
	ix, iy, iw, ih = skin.parameters.get("PluginBrowserDownloadIcon",(10, 0, 60, 50))
	return [
		name,
		MultiContentEntryText(pos=(x, y), size=(width-x, h), font=0, text=name),
		MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png = png)
	]

def PluginDownloadComponent(plugin, name, version=None, width=440):
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
	x, y, h = skin.parameters.get("PluginBrowserDownloadName",(80, 5, 25))
	dx, dy, dh = skin.parameters.get("PluginBrowserDownloadDescr",(80, 26, 17))
	ix, iy, iw, ih = skin.parameters.get("PluginBrowserDownloadIcon",(10, 0, 60, 50))
	return [
		plugin,
		MultiContentEntryText(pos=(x, y), size=(width-x, h), font=0, text=name),
		MultiContentEntryText(pos=(dx, dy), size=(width-dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png = png)
	]


class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("PluginBrowser0", ("Regular", 20, 50))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		font = skin.fonts.get("PluginBrowser1", ("Regular", 14))
		self.l.setFont(1, gFont(font[0], font[1]))
