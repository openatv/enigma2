from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap
from GUIComponent import GUIComponent
from skin import parseFont

def PluginEntryComponent(plugin, width=440):
	global ny, dy, nh, dh
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon

	return [
		plugin,
		MultiContentEntryText(pos=(120, ny), size=(width-120, nh), font=0, text=plugin.name),
		MultiContentEntryText(pos=(120, dy), size=(width-120, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(10, 5), size=(100, 40), png = png)
	]

def PluginCategoryComponent(name, png, width=440):
	global nx, ny, nh, ix, iy, iw, ih
	return [
		name,
		MultiContentEntryText(pos=(nx, ny), size=(width-nx, nh), font=0, text=name),
		MultiContentEntryPixmapAlphaTest(pos=(ix, iy), size=(iw, ih), png = png)
	]

def PluginDownloadComponent(plugin, name, version=None, width=440):
	global nx, ny, nh, dx, dy, dh, ix, iy, iw, ih
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
		MultiContentEntryText(pos=(nx, ny), size=(width-nx, nh), font=0, text=name),
		MultiContentEntryText(pos=(dx, dy), size=(width-dx, dh), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(ix, iy), size=(iw, ih), png = png)
	]

class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		global nx, ny, nh, dx, dy, dh, ix, iy, iw, ih
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		GUIComponent.__init__(self)
		self.itemNameFont = gFont("Regular", 20)
		self.itemDescrFont = gFont("Regular", 14)
		(nx, ny, nh, dx, dy, dh) = (80, 5, 25, 80, 26, 17 )
		(ix, iy, iw, ih) = (10, 0, 60, 50)
		self.l.setItemHeight(50)

	def applySkin(self, desktop, parent):
		def setItemNameFont(value):
			self.itemNameFont = parseFont(value, ((1,1),(1,1)))
		def setItemDescrFont(value):
			self.itemDescrFont = parseFont(value, ((1,1),(1,1)))
		def setNameXYH(value):
			global nx, ny, nh
			(n_x, n_y, n_h) = value.split(',')
			(nx, ny, nh) = (int(n_x),int(n_y),int(n_h))
		def setDescrXYH(value):
			global dx, dy, dh
			(d_x, d_y, d_h) = value.split(',')
			(dx, dy, dh) = (int(d_x),int(d_y),int(d_h))
		def setIconXYWH(value):
			global ix,iy,iw,ih
			(i_x, i_y, i_w, i_h) = value.split(',')
			(ix, iy, iw, ih) = (int(i_x),int(i_y),int(i_w),int(i_h))
		for (attrib, value) in [x for x in self.skinAttributes if x[0] in dir()]:
			eval(attrib + "('" + value + "')")
			self.skinAttributes.remove((attrib, value))
		self.l.setFont(0, self.itemNameFont)
		self.l.setFont(1, self.itemDescrFont)
		return GUIComponent.applySkin(self, desktop, parent)