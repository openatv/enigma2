from Screen import *
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Header import Header

# hack ... must be made dynamic
from Screens.Setup import Setup
from ServiceScan import ServiceScan
from ScartLoopThrough import ScartLoopThrough
from Components.Button import Button
from Components.Label import Label
from Components.ProgressBar import ProgressBar
from ConfigMenu import *

from TimerEdit import *

from enigma import quitMainloop

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Tools import XMLTools

# some screens
def doGlobal(screen):
	screen["clock"] = Clock()


mdom = xml.dom.minidom.parseString(
        """
	<menu text="Mainmenu" title="the real Mainmenu">
		<item text="Standby debug">quitMainloop()</item>
		<item text="Automatic Scan">self.openDialog(ServiceScan)</item>

		<item text="Blub1">self.openSetup("rc")</item>
		<item text="Blub2">self.openSetup("blasel")</item>

		<item text="TV-Mode">self.setModeTV()</item>
		<item text="Radio-Mode">self.setModeRadio()</item>
		<item text="File-Mode">self.setModeFile()</item>
		<item text="Scart">self.openDialog(ScartLoopThrough)</item>
		<item text="Timer">self.openDialog(TimerEditList)</item>
		<menu text="Setup">
			<menu text="Service Organising">
				<item text="New Bouquets"></item>
				<item text="Add to Bouquets"></item>
				<item text="Edit Bouquets"></item>
			</menu>
			<menu text="Service Searching">
				<item text="Satelliteconfig"></item>
				<item text="Satfinder"></item>
				<item text="Rotor Control"></item>
				<item text="Edit Transponder"></item>
				<item text="Automatic Scan">self.openDialog(ServiceScan)</item>
				<item text="Automatic 'Multisat' Scan"></item>
				<item text="Manual Scan"></item>
			</menu>
			<menu text="System">
				<item text="Time Date"></item>
				<item text="Video Audio"></item>
				<item text="UHF Modulator"></item>
				<item text="Harddisk"></item>
				<item text="Keyboard"></item>
				<item text="OSD">self.openDialog(configOSD)</item>
				<item text="Language"></item>
				<item text="LCD"></item>
			</menu>
			<item text="Common Interface"></item>
			<item text="Parental Control"></item>
			<item text="Expert"></item>
		</menu>
		<item text="Games"></item>
		<item text="Information"></item>
		<menu text="Standby">
			<item text="PowerOff"></item>
			<item text="Restart"></item>
			<item text="Standby"></item>
			<item text="Sleep Timer">self.goSetup()</item>
		</menu>
	</menu>""")

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

class configOSD(Screen):
	#this needs focus handling - so not useable

	def okbuttonClick(self):
		self.close
 
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})

		self["okbutton"] = Button("Save")

		self["txt_alpha"] = Label("Alpha:")
		self["sld_alpha"] = ProgressBar()
		self["sld_alpha"].setValue(50)

		self["txt_brightness"] = Label("Brightness:")
		self["sld_brightness"] = ProgressBar()
		self["sld_brightness"].setValue(50)

		self["txt_gamma"] = Label("Contrast:")
		self["sld_gamma"] = ProgressBar()
		self["sld_gamma"].setValue(50)

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
		self.session.open(setup, dialog)

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

class FixedMenu(Screen):
	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()

	def __init__(self, session, title, list):
		Screen.__init__(self, session)
		
		self["menu"] = MenuList(list)	
							
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
		
		self["title"] = Header(title)


class MainMenu(Menu):
	#add file load functions for the xml-file
	#remove old code (i.e. goScan / goClock...)
	
	def __init__(self, *x):
		Menu.__init__(self, *x)
		self.skinName = "Menu"

	def openDialog(self, dialog):
		self.session.open(dialog)

	def openSetup(self, dialog):
		self.session.open(Setup, dialog)

	def goSetup(self):
		self.session.open(configTest)
	
	def setModeTV(self):
		print "set Mode to TV"
		pass

	def setModeRadio(self):
		print "set Mode to Radio"
		pass

	def setModeFile(self):
		print "set Mode to File"
		pass

	def goScan(self):
		self.session.open(ServiceScan)
	
	def goClock(self):
		self.session.open(clockDisplay, Clock())
