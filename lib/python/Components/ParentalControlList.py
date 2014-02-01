from MenuList import MenuList
from Components.ParentalControl import IMG_WHITESERVICE, IMG_WHITEBOUQUET, IMG_BLACKSERVICE, IMG_BLACKBOUQUET
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename

from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT
from Tools.LoadPixmap import LoadPixmap

#Now there is a list of pictures instead of one...
entryPicture = {IMG_BLACKSERVICE: LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lock.png")),
				IMG_BLACKBOUQUET: LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/lockBouquet.png")),
				IMG_WHITESERVICE: LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/unlock.png")),
				IMG_WHITEBOUQUET: LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/unlockBouquet.png"))}


def ParentalControlEntryComponent(service, name, protectionType):
	locked = protectionType[0]
	sImage = protectionType[1]
	res = [
		(service, name, locked),
		(eListboxPythonMultiContent.TYPE_TEXT, 80, 5, 300, 50, 0, RT_HALIGN_LEFT, name)
	]
	#Changed logic: The image is defined by sImage, not by locked anymore
	if sImage != "":
		res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 0, 0, 32, 32, entryPicture[sImage]))
	return res

class ParentalControlList(MenuList):
	def __init__(self, list, enableWrapAround = False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setItemHeight(32)

	def toggleSelectedLock(self):
		from Components.ParentalControl import parentalControl
		print "self.l.getCurrentSelection():", self.l.getCurrentSelection()
		print "self.l.getCurrentSelectionIndex():", self.l.getCurrentSelectionIndex()
		curSel = self.l.getCurrentSelection()
		if curSel[0][2]:
			parentalControl.unProtectService(self.l.getCurrentSelection()[0][0])
		else:
			parentalControl.protectService(self.l.getCurrentSelection()[0][0])
		#Instead of just negating the locked- flag, now I call the getProtectionType every time...
		self.list[self.l.getCurrentSelectionIndex()] = ParentalControlEntryComponent(curSel[0][0], curSel[0][1], parentalControl.getProtectionType(curSel[0][0]))
		self.l.setList(self.list)
