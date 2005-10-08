from Screen import *
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Header import Header
from Components.Button import Button
from Components.Label import Label
from Components.ProgressBar import ProgressBar

from enigma import quitMainloop

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Screens.Satconfig import NimSelection
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
try:
	# first we search in the current path
	menufile = file('data/menu.xml', 'r')
except:
	# if not found in the current path, we use the global datadir-path
	menufile = file('/usr/share/enigma2/menu.xml', 'r')
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

class Menu(Screen):
	def okbuttonClick(self):
		print "okbuttonClick"
		selection = self["menu"].getCurrent()
		selection[1]()

	def evalText(self, text):
		eval(text)
		
	def nothing(self):																	#dummy
		pass

	def openDialog(self, dialog):				# in every layer needed
		self.session.open(dialog)

	def openSetup(self, dialog):
		self.session.open(Setup, dialog)

	def addMenu(self, destList, node):
		MenuTitle = getValbyAttr(node, "text")
		if MenuTitle != "":																	#check for title
			a = boundFunction(self.session.open, Menu, node, node.childNodes)
			#TODO add check if !empty(node.childNodes)
			destList.append((MenuTitle, a))
		
	def addItem(self, destList, node):
		ItemText = getValbyAttr(node, "text")
		if ItemText != "":																	#check for name
			b = XMLTools.mergeText(node.childNodes)
			if b != "":																				#check for function
				destList.append((ItemText,boundFunction(self.evalText,b)))
			else:
				destList.append((ItemText,self.nothing))				#use dummy as function

	def __init__(self, session, parent, childNode):
		Screen.__init__(self, session)
		
		list = []

		for x in childNode:							#walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
			    continue
			elif x.tagName == 'item':
				self.addItem(list, x)
			elif x.tagName == 'menu':
				self.addMenu(list, x)

		self["menu"] = MenuList(list)	
							
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
		
		a = getValbyAttr(parent, "title")
		if a == "":														#if empty use name
			a = getValbyAttr(parent, "text")
		self["title"] = Header(a)

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
