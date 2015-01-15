from MenuList import MenuList

from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from enigma import eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap
from GUIComponent import GUIComponent
from skin import parseFont

#
# SKIN pars:
# ============================
# PluginBrowser:
# setName("y, height")
# setDescr("y, height")
# setPluginIcon("x,y,width,height")
#
# PluginDownloadBrowser:
# setName("y, height")
# setDescr("y,height")
# setIcon("x,y,width,height")
#
# common:
# setNameFont
# setDescrFont

def PluginEntryComponent(plugin, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon
	pos = 2 * p.plicon[0] + p.plicon[2]
	return [
		plugin,
		MultiContentEntryText(pos=(pos, p.name[0]), size=(width - pos, p.name[1]), font=0, text=plugin.name),
		MultiContentEntryText(pos=(pos, p.descr[0]), size=(width - pos, p.descr[1]), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(p.plicon[0], p.plicon[1]), size=(p.plicon[2], p.plicon[3]), png = png)
	]

def PluginCategoryComponent(name, png, width=440):
	pos = 2* p.icon[0] + p.icon[2]
	return [
		name,
		MultiContentEntryText(pos=(pos, p.name[0]), size=(width-pos, p.name[1]), font=0, text=name),
		MultiContentEntryPixmapAlphaTest(pos=(p.icon[0], p.icon[1]), size=(p.icon[2], p.icon[3]), png = png)
	]

def PluginDownloadComponent(plugin, name, version=None, width=440):
	if plugin.icon is None:
		png = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png = plugin.icon
	pos = 2 * p.icon[0] + p.icon[2]
	if version:
		if "+git" in version:
			# remove git "hash"
			version = "+".join(version.split("+")[:2])
		elif version.startswith('experimental-'):
			version = version[13:]
		name += "  (" + version + ")"
	return [
		plugin,
		MultiContentEntryText(pos=(pos, p.name[0]), size=(width-pos, p.name[1]), font=0, text=name),
		MultiContentEntryText(pos=(pos, p.descr[0]), size=(width-pos, p.descr[1]), font=1, text=plugin.description),
		MultiContentEntryPixmapAlphaTest(pos=(p.icon[0], p.icon[1]), size=(p.icon[2], p.icon[3]), png = png)
	]

class PluginList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.itemNameFont = gFont("Regular", 20)
		self.itemDescrFont = gFont("Regular", 14)
		self.l.setItemHeight(50)

	def applySkin(self, desktop, parent):
		def setNameFont(value):
			self.itemNameFont = parseFont(value, ((1,1),(1,1)))
		def setDescrFont(value):
			self.itemDescrFont = parseFont(value, ((1,1),(1,1)))
		def setName(value):
			p.name = map(int, value.split(','))
		def setDescr(value):
			p.descr = map(int, value.split(','))
		def setIcon(value):
			p.icon = map(int, value.split(','))
		def setPluginIcon(value):
			p.plicon = map(int, value.split(','))
		for (attrib, value) in list(self.skinAttributes):
			try:
				locals().get(attrib)(value)
				self.skinAttributes.remove((attrib, value))
			except:
				pass
		self.l.setFont(0, self.itemNameFont)
		self.l.setFont(1, self.itemDescrFont)
		return GUIComponent.applySkin(self, desktop, parent)

class skinParameters():
	def __init__(self):
		self.name  =  5, 25
		self.descr =  26, 17
		self.icon  =  10, 0, 60, 50
		self.plicon = 10, 5, 100, 40
	def name(self):
		return self.name
	def descr(self):
		return self.descr
	def icon(self):
		return self.icon
	def plicon(self):
		return self.plicon
p = skinParameters()
