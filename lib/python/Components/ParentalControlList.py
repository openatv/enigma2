from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent

from MenuList import MenuList
from Components.ParentalControl import parentalControl
from Tools.Directories import SCOPE_SKIN_IMAGE, resolveFilename

from enigma import LoadPixmap, eListbox, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT

lockPicture = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "lock-fs8.png"))

def ParentalControlEntryComponent(service, name, locked = True):
	res = [ (service, name, locked) ]
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 80, 5, 300, 50, 0, RT_HALIGN_LEFT, name))
	if locked:
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, 32, 32, lockPicture))
	return res

class ParentalControlList(MenuList, HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.list = list
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setItemHeight(32)

	GUI_WIDGET = eListbox
	
	def setList(self, list):
		self.list = list
		self.l.setList(list)
		
	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def toggleSelectedLock(self):
		print "self.l.getCurrentSelection():", self.l.getCurrentSelection()
		print "self.l.getCurrentSelectionIndex():", self.l.getCurrentSelectionIndex()
		self.list[self.l.getCurrentSelectionIndex()] = ParentalControlEntryComponent(self.l.getCurrentSelection()[0][0], self.l.getCurrentSelection()[0][1], not self.l.getCurrentSelection()[0][2]);
		if self.l.getCurrentSelection()[0][2]:
			parentalControl.protectService(self.l.getCurrentSelection()[0][0])
		else:
			parentalControl.unProtectService(self.l.getCurrentSelection()[0][0])	
		self.l.setList(self.list)
