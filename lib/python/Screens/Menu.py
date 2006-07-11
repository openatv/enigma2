from Screen import *
from Components.Sources.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Header import Header
from Components.Button import Button
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Components.config import configfile
from Components.Clock import Clock

from Tools.Directories import resolveFilename, SCOPE_SKIN

from enigma import quitMainloop

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Screens.Setup import *

from Tools import XMLTools

# some screens
def doGlobal(screen):
	screen["clock"] = Clock()


#		<item text="TV-Mode">self.setModeTV()</item>
#		<item text="Radio-Mode">self.setModeRadio()</item>
#		<item text="File-Mode">self.setModeFile()</item>
#		<item text="Scart">self.openDialog(ScartLoopThrough)</item>
#			<item text="Sleep Timer"></item>


# read the menu
menufile = file(resolveFilename(SCOPE_SKIN, 'menu.xml'), 'r')
mdom = xml.dom.minidom.parseString(menufile.read())
menufile.close()


def getValbyAttr(x, attr):
	for p in range(x.attributes.length):
		a = x.attributes.item(p)
		attrib = str(a.name)
		value = str(a.value)
		if attrib == attr:
			return value
			
	return ""

class boundFunction:
	def __init__(self, fnc, *args):
		self.fnc = fnc
		self.args = args
	def __call__(self):
		self.fnc(*self.args)
		
class MenuUpdater:
	def __init__(self):
		self.updatedMenuItems = {}
	
	def addMenuItem(self, id, pos, text, module, screen):
		if not self.updatedMenuAvailable(id):
			self.updatedMenuItems[id] = []
		self.updatedMenuItems[id].append([text, pos, module, screen])
	
	def delMenuItem(self, id, pos, text, module, screen):
		self.updatedMenuItems[id].remove([text, pos, module, screen])
	
	def updatedMenuAvailable(self, id):
		return self.updatedMenuItems.has_key(id)
	
	def getUpdatedMenu(self, id):
		return self.updatedMenuItems[id]
	
menuupdater = MenuUpdater()

class MenuSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="MenuTitle" position="0,4" size="132,21" font="Regular;18" />
		<widget name="MenuEntry" position="0,25" size="132,21" font="Regular;16" />
		<widget name="Clock" position="50,46" size="82,18" font="Regular;16" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["MenuTitle"] = Label(parent.menu_title)
		self["MenuEntry"] = Label("")
		self["Clock"] = Clock()
		self.parent = parent
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)
	
	def addWatcher(self):
		self.parent["menu"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()
	
	def removeWatcher(self):
		self.parent["menu"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["MenuEntry"].setText(self.parent["menu"].getCurrent()[0])

class Menu(Screen):
	def okbuttonClick(self):
		print "okbuttonClick"
		selection = self["menu"].getCurrent()
		selection[1]()

	def execText(self, text):
		exec text

	def runScreen(self, arg):
		# arg[0] is the module (as string)
		# arg[1] is Screen inside this module 
		#        plus possible arguments, as 
		#        string (as we want to reference 
		#        stuff which is just imported)
		# FIXME. somehow
		if arg[0] != "":
			exec "from " + arg[0] + " import *"
			
		self.openDialog(*eval(arg[1]))

	def nothing(self):																	#dummy
		pass

	def openDialog(self, *dialog):				# in every layer needed
		self.session.open(*dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		MenuTitle = _(getValbyAttr(node, "text"))
		if MenuTitle != "":																	#check for title
			x = getValbyAttr(node, "flushConfigOnClose")
			if x == "1":
				a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node, node.childNodes)
			else:
				a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node, node.childNodes)
			#TODO add check if !empty(node.childNodes)
			destList.append((MenuTitle, a))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		if len(res) and res[0]:
			self.close(True)

	def addItem(self, destList, node):
		ItemText = _(getValbyAttr(node, "text"))
		if ItemText != "":																	#check for name
			for x in node.childNodes:
				if x.nodeType != xml.dom.minidom.Element.nodeType:
					continue
				elif x.tagName == 'screen':
					module = getValbyAttr(x, "module")
					screen = getValbyAttr(x, "screen")

					if len(screen) == 0:
						screen = module

					if module != "":
						module = "Screens." + module
					
					# check for arguments. they will be appended to the 
					# openDialog call
					args = XMLTools.mergeText(x.childNodes)
					screen += ", " + args
					
					destList.append((ItemText, boundFunction(self.runScreen, (module, screen))))
					return
				elif x.tagName == 'code':
					destList.append((ItemText, boundFunction(self.execText, XMLTools.mergeText(x.childNodes))))
					return
				elif x.tagName == 'setup':
					id = getValbyAttr(x, "id")
					destList.append((ItemText, boundFunction(self.openSetup, id)))
					return
			
			destList.append((ItemText,self.nothing))


	def __init__(self, session, parent, childNode):
		Screen.__init__(self, session)
		
		list = []
		menuID = ""

		menuID = -1
		for x in childNode:						#walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
			    continue
			elif x.tagName == 'item':
				self.addItem(list, x)
				count += 1
			elif x.tagName == 'menu':
				self.addMenu(list, x)
				count += 1
			elif x.tagName == "id":
				menuID = getValbyAttr(x, "val")
				count = 0
			if menuID != -1:
				if menuupdater.updatedMenuAvailable(menuID):
					for x in menuupdater.getUpdatedMenu(menuID):
						if x[1] == count:
							list.append((x[0], boundFunction(self.runScreen, (x[2], x[3] + ", "))))
							count += 1


		self["menu"] = MenuList(list)	
							
		self["actions"] = ActionMap(["OkCancelActions", "MenuActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive
			})
		
		a = getValbyAttr(parent, "title")
		if a == "":														#if empty use name
			a = _(getValbyAttr(parent, "text"))
		self["title"] = Header(a)
		self.menu_title = a

	def closeNonRecursive(self):
		self.close(False)

	def closeRecursive(self):
		self.close(True)

	def createSummary(self):
		return MenuSummary

class MainMenu(Menu):
	#add file load functions for the xml-file
	
	def __init__(self, *x):
		Menu.__init__(self, *x)
		self.skinName = "Menu"

	def openDialog(self, dialog):
		self.session.open(dialog)

	def openSetup(self, dialog):
		self.session.open(Setup, dialog)

	def setModeTV(self):
		print "set Mode to TV"
		pass

	def setModeRadio(self):
		print "set Mode to Radio"
		pass

	def setModeFile(self):
		print "set Mode to File"
		pass
