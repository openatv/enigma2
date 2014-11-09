from MenuList import MenuList
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists
import skin

def ChoiceEntryComponent(key="", text=None):
	if not text: text = ["--"]
	res = [ text ]
	if text[0] == "--":
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 00, 800, 25, 0, RT_HALIGN_LEFT, "-"*200))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, 00, 800, 25, 0, RT_HALIGN_LEFT, text[0]))
		if key:
			if key == "expandable":
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/expandable.png")
			elif key == "expanded":
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/expanded.png")
			elif key == "verticalline":
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/verticalline.png")
			else:
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" % key)
			if fileExists(pngfile):
				png = LoadPixmap(pngfile)
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 0, 35, 25, png))
	return res

class ChoiceList(MenuList):
	def __init__(self, list, selection = 0, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts["ChoiceList"]
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.ItemHeight = font[2]
		self.selection = selection

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		self.moveToIndex(self.selection)
		self.instance.setWrapAround(True)

	def getItemHeight(self):
		return self.ItemHeight
