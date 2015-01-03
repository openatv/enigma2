from MenuList import MenuList
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from enigma import RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont
from Tools.LoadPixmap import LoadPixmap
import skin

def row_delta_y():
	font = skin.fonts["ChoiceList"]
	return (int(font[2]) - int(font[1]))/2

def ChoiceEntryComponent(key = None, text = ["--"]):
	y = row_delta_y()
	res = [ text ]
	if text[0] == "--":
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, y, 800, 25, 0, RT_HALIGN_LEFT, "-"*200))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 45, y, 800, 25, 0, RT_HALIGN_LEFT, text[0]))
		if key:
			if key == "expandable":
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/expandable.png"))
			elif key == "expanded":
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/expanded.png"))
			elif key == "verticalline":
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/verticalline.png"))
			elif key == "bullet":
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/bullet.png"))
			else:
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/buttons/key_%s.png" % key))
			if png:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, y, 35, 25, png))
	return res

class ChoiceList(MenuList):
	def __init__(self, list, selection = 0, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts["ChoiceList"]
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])
		self.selection = selection

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		self.moveToIndex(self.selection)
		self.instance.setWrapAround(True)
