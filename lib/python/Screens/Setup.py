from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config				#global config instance
from Components.config import configBoolean
from Components.ConfigList import ConfigList
from Components.Label import Label

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Tools import XMLTools

# read the setupmenu
try:
	# first we search in the current path
	setupfile = file('data/setup.xml', 'r')
except:
	# if not found in the current path, we use the global datadir-path
	setupfile = file('/usr/share/enigma2/setup.xml', 'r')
setupdom = xml.dom.minidom.parseString(setupfile.read())
setupfile.close()

def getValbyAttr(x, attr):
	for p in range(x.attributes.length):
		a = x.attributes.item(p)
		attrib = str(a.name)
		value = str(a.value)
		if attrib == attr:
			return value
	
	return ""

class Setup(Screen):

	def addItems(self, list, childNode):
		for x in childNode:
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'item':
				ItemText = getValbyAttr(x, "text")
				b = eval(XMLTools.mergeText(x.childNodes));
				print "item " + ItemText + " " + b.configPath
				if b == "":
					continue
				#add to configlist
				item = b.controlType(b)
				
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				list.append( (ItemText, item) )

	def keyOk(self):
		self["config"].handleKey(0)
	def keyLeft(self):
		self["config"].handleKey(1)
	def keyRight(self):
		self["config"].handleKey(2)

	def keySave(self):
		print "save requested"
		for x in self["config"].list:
			x[1].save()
		self.close()

	def keyCancel(self):
		print "cancel requested"
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def __init__(self, session, setup):
		Screen.__init__(self, session)

		print "request setup for " + setup
		
		xmldata = setupdom.childNodes[0]
		
		entries = xmldata.childNodes

		list = []
				
		for x in entries:             #walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'setup':
				ItemText = getValbyAttr(x, "key")
				if ItemText != setup:
					continue
				self.addItems(list, x.childNodes);
		
		#check for list.entries > 0 else self.close
		
		self["config"] = ConfigList(list)

		self["ok"] = Label("OK")
		self["cancel"] = Label("Cancel")

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.keyCancel,
				"ok": self.keyOk,
				"left": self.keyLeft,
				"right": self.keyRight,
				"save": self.keySave
			}, 1)
