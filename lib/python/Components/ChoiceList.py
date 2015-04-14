from MenuList import MenuList
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont, getDesktop
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists
import skin
from os import path

def ChoiceEntryComponent(key="", text=None):
	screenwidth = getDesktop(0).size().width()
	if not text: text = ["--"]
	res = [ text ]
	if text[0] == "--":
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 00, 1200, 38, 0, RT_HALIGN_LEFT, "-"*300))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 00, 800, 25, 0, RT_HALIGN_LEFT, "-"*200))
	else:
		if screenwidth and screenwidth == 1920:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 68, 5, 1200, 38, 0, RT_HALIGN_LEFT, text[0]))
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
				if screenwidth and screenwidth == 1920:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 14, 4, 45, 45, png))
				else:
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, 9, 0, 30, 30, png))
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
