from MenuList import MenuList
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename
from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont, getDesktop
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists
import skin

def ChoiceEntryComponent(key="", text=None):
	screenwidth = getDesktop(0).size().width()
	font = skin.fonts["ChoiceList"]
	top = 0
	if screenwidth:
		if screenwidth == 1920:
			left = 100
			height = 50
		else:
			left = 50
			height = 25
		width = screenwidth
	else:
		left = 50
		width = 720
		height = 25
	if font:
		if font[2] > height:
			height = font[2]
		top = int((height - font[2]) / 2)
	if not text: text = ["--"]
	res = [ text ]
	if text[0] == "--":
		res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, width, height, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, "-"*200))
	else:
		res.append((eListboxPythonMultiContent.TYPE_TEXT, left, top, width, height, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, text[0]))
		if key:
			if screenwidth and screenwidth == 1920:
				left = 10
				width = 48
				size = 48
			else:
				left = 5;
				width = 35
				size = 25
			top = int((height - size) / 2)
			if key == "expandable":
				height = size
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/expandable.png")
			elif key == "expanded":
				height = size + top
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/expanded.png")
			elif key == "verticalline":
				top = 0
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "icons/verticalline.png")
			else:
				height = size
				pngfile = resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/key_%s.png" % key)
			if fileExists(pngfile):
				png = LoadPixmap(pngfile)
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, left, top, width, height, png))
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
