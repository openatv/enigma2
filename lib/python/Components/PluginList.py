from enigma import BT_HALIGN_CENTER, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_CENTER, eListboxPythonMultiContent, gFont

from skin import fonts, parameters
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


INSTALLEDPNG = LoadPixmap(cached=False, path=resolveFilename(SCOPE_GUISKIN, "icons/installed.png"))
INSTALLABLE = LoadPixmap(cached=False, path=resolveFilename(SCOPE_GUISKIN, "icons/installable.png"))
UPGRADEABLE = LoadPixmap(cached=False, path=resolveFilename(SCOPE_GUISKIN, "icons/upgradeable.png"))
PLUGINPNG = LoadPixmap(cached=False, path=resolveFilename(SCOPE_GUISKIN, "icons/plugin.png"))


def PluginEntryComponent(plugin, width=440):
	png = plugin.icon or PLUGINPNG
	nx, ny, nh = parameters.get("PluginBrowserName", (120, 5, 25))
	dx, dy, dh = parameters.get("PluginBrowserDescr", (120, 26, 17))
	ix, iy, iw, ih = parameters.get("PluginBrowserIcon", (10, 5, 100, 40))
	return [
		plugin,
		MultiContentEntryText(pos=(nx, ny), size=(width - nx, nh), font=0, text=plugin.name),
		MultiContentEntryText(pos=(nx, dy), size=(width - dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(ix, iy), size=(iw, ih), png=png, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER)
	]


def PluginEntryComponentSelected(plugin, width=440):
	png = plugin.icon or PLUGINPNG
	nx, ny, nh = parameters.get("PluginBrowserName", (120, 5, 25))
	dx, dy, dh = parameters.get("PluginBrowserDescr", (120, 26, 17))
	ix, iy, iw, ih = parameters.get("PluginBrowserIcon", (10, 5, 100, 40))
	return [
		plugin,
		MultiContentEntryText(pos=(nx, ny), size=(width - nx, nh), backcolor_sel=0xDC143C),
		MultiContentEntryText(pos=(nx, dy), size=(width - dx, dh), backcolor_sel=0xDC143C),
		MultiContentEntryText(pos=(nx, ny), size=(width - nx, nh), font=0, text=plugin.name),
		MultiContentEntryText(pos=(nx, dy), size=(width - dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(ix, iy), size=(iw, ih), png=png, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER)
	]


def PluginCategoryComponent(name, png, width=440):
	x, y, h = parameters.get("PluginBrowserDownloadName", (80, 5, 25))
	ix, iy, iw, ih = parameters.get("PluginBrowserDownloadIcon", (10, 0, 60, 50))
	return [
		name,
		MultiContentEntryText(pos=(x, y), size=(width - x, h), font=0, text=name),
		MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png=png)
	]


def PluginDownloadComponent(plugin, name, version=None, width=440, installstatus=None, updatestatus=None):
	png = plugin.icon or PLUGINPNG
	if version:
		if "+git" in version:  # Remove git "hash".
			version = "+".join(version.split("+")[:2])
		elif version.startswith("experimental-"):
			version = version[13:]
		name += "  (" + version + ")"
	x, y, h = parameters.get("PluginBrowserDownloadName", (80, 5, 25))
	dx, dy, dh = parameters.get("PluginBrowserDownloadDescr", (80, 26, 17))
	ix, iy, iw, ih = parameters.get("PluginBrowserDownloadIcon", (10, 0, 60, 50))
	if installstatus:
		ipng = INSTALLABLE if installstatus == "0" else INSTALLEDPNG
		if updatestatus and updatestatus != "0":
			ipng = UPGRADEABLE
		offset = iw
		return [
			plugin,
			MultiContentEntryText(pos=(x + offset, y), size=(width - x, h), font=0, text=name),
			MultiContentEntryText(pos=(dx + offset, dy), size=(width - dx, dh), font=1, text=plugin.description),
			MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png=png),
			MultiContentEntryPixmapAlphaBlend(pos=(ix + offset, iy), size=(iw, ih), png=ipng, flags=BT_SCALE | BT_KEEP_ASPECT_RATIO | BT_HALIGN_CENTER | BT_VALIGN_CENTER)
		]
	else:
		return [
			plugin,
			MultiContentEntryText(pos=(x, y), size=(width - x, h), font=0, text=name),
			MultiContentEntryText(pos=(dx, dy), size=(width - dx, dh), font=1, text=plugin.description),
			MultiContentEntryPixmapAlphaBlend(pos=(ix, iy), size=(iw, ih), png=png)
		]


class PluginList(MenuList):
	def __init__(self, pluginList, enableWrapAround=True):
		MenuList.__init__(self, pluginList, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("PluginBrowser0", ("Regular", 20, 50))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		font = fonts.get("PluginBrowser1", ("Regular", 14))
		self.l.setFont(1, gFont(font[0], font[1]))
