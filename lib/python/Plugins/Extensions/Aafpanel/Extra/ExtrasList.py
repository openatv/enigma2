from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Tools.Directories import fileExists, SCOPE_SKIN_IMAGE, SCOPE_CURRENT_SKIN, resolveFilename
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

def SimpleEntry(name, picture):
	res = [(name, picture)]
	#res = []
	picture = resolveFilename(SCOPE_SKIN_IMAGE, 'skin_default/menu/' + picture)
	if name == "---":
		if fileExists(picture):
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 22), size=(470, 4), png=loadPNG(picture)))
	else:
		if fileExists(picture):
			res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 0), size=(48, 48), png=loadPNG(picture)))
		res.append(MultiContentEntryText(pos=(60, 10), size=(420, 38), font=0, text=name))
		
	return res
	
class ExtrasList(MenuList, HTMLComponent, GUIComponent):
	def __init__(self, list, enableWrapAround = False):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont('Regular', 21))
		self.l.setItemHeight(48)
		self.onSelectionChanged = []
		self.enableWrapAround = enableWrapAround
		self.last = 0
		
	GUI_WIDGET = eListbox
	
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		if self.enableWrapAround:
			self.instance.setWrapAround(True)
			
	def selectionChanged(self):
		isDiv = False
		try:
			for element in self.list[self.getSelectionIndex()]:
				if element[0] == "---":
					isDiv = True
					if self.getSelectionIndex() < self.last:
						self.up()
					else:
						self.down()
		except Exception, e:
			pass
	
		self.last = self.getSelectionIndex()
		if not isDiv:
			for f in self.onSelectionChanged:
				f()
