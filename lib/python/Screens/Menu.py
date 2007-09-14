from Screen import Screen
from Components.Sources.List import List
from Components.ActionMap import ActionMap
from Components.Header import Header
from Components.Label import Label
from Components.config import configfile
from Components.Sources.Clock import Clock
from Components.PluginComponent import plugins

from Tools.Directories import resolveFilename, SCOPE_SKIN

import xml.dom.minidom

from Screens.Setup import Setup, getSetupTitle

from Tools import XMLTools

#		<item text="TV-Mode">self.setModeTV()</item>
#		<item text="Radio-Mode">self.setModeRadio()</item>
#		<item text="File-Mode">self.setModeFile()</item>
#			<item text="Sleep Timer"></item>


# read the menu
menufile = file(resolveFilename(SCOPE_SKIN, 'menu.xml'), 'r')
mdom = xml.dom.minidom.parseString(menufile.read())
menufile.close()

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
		<widget name="MenuTitle" position="6,4" size="120,21" font="Regular;18" />
		<widget name="MenuEntry" position="6,25" size="120,21" font="Regular;16" />
		<widget source="CurrentTime" render="Label" position="56,46" size="82,18" font="Regular;16" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["MenuTitle"] = Label(parent.menu_title)
		self["MenuEntry"] = Label("")
		self["CurrentTime"] = Clock()
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

	ALLOW_SUSPEND = True

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

	def nothing(self): #dummy
		pass

	def openDialog(self, *dialog):				# in every layer needed
		self.session.openWithCallback(self.menuClosed, *dialog)

	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def addMenu(self, destList, node):
		MenuTitle = _(node.getAttribute("text").encode("UTF-8") or "??")
		entryID = node.getAttribute("entryID") or "undefined"
		x = node.getAttribute("flushConfigOnClose")
		if x:
			a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node, node.childNodes)
		else:
			a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node, node.childNodes)
		#TODO add check if !empty(node.childNodes)
		destList.append((MenuTitle, a, entryID))

	def menuClosedWithConfigFlush(self, *res):
		configfile.save()
		self.menuClosed(*res)

	def menuClosed(self, *res):
		if len(res) and res[0]:
			self.close(True)

	def addItem(self, destList, node):
		item_text = node.getAttribute("text").encode("UTF-8")
		entryID = node.getAttribute("entryID") or "undefined"
		for x in node.childNodes:
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'screen':
				module = x.getAttribute("module") or None
				screen = x.getAttribute("screen") or None

				if screen is None:
					screen = module

				print module, screen
				if module:
					module = "Screens." + module
				else:
					module = ""

				# check for arguments. they will be appended to the
				# openDialog call
				args = XMLTools.mergeText(x.childNodes)
				screen += ", " + args

				destList.append((_(item_text or "??"), boundFunction(self.runScreen, (module, screen)), entryID))
				return
			elif x.tagName == 'code':
				destList.append((_(item_text or "??"), boundFunction(self.execText, XMLTools.mergeText(x.childNodes)), entryID))
				return
			elif x.tagName == 'setup':
				id = x.getAttribute("id")
				if item_text == "":
					item_text = _(getSetupTitle(id)) + "..."
				else:
					item_text = _(item_text)
				destList.append((item_text, boundFunction(self.openSetup, id), entryID))
				return
		destList.append((item_text, self.nothing, entryID))


	def __init__(self, session, parent, childNode):
		Screen.__init__(self, session)
		
		list = []
		
		menuID = None
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
				menuID = x.getAttribute("val")
				count = 0

			if menuID is not None:
				# menuupdater?
				if menuupdater.updatedMenuAvailable(menuID):
					for x in menuupdater.getUpdatedMenu(menuID):
						if x[1] == count:
							list.append((x[0], boundFunction(self.runScreen, (x[2], x[3] + ", "))))
							count += 1

		if menuID is not None:
			# plugins
			for l in plugins.getPluginsForMenu(menuID):
				list.append((l[0], boundFunction(l[1], self.session)))

		# for the skin: first try a menu_<menuID>, then Menu
		self.skinName = [ ]
		if menuID is not None:
			self.skinName.append("menu_" + menuID)
		self.skinName.append("Menu")

		self["menu"] = List(list)

		self["actions"] = ActionMap(["OkCancelActions", "MenuActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive
			})
		
		a = parent.getAttribute("title").encode("UTF-8") or None
		if a is None:
			a = _(parent.getAttribute("text").encode("UTF-8"))
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
		self.skinName = "Menu"
		Menu.__init__(self, *x)
