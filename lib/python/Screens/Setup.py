from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.config import config				#global config instance
from Components.config import configSelection
from Components.ConfigList import ConfigList
from Components.Label import Label
from Components.Pixmap import Pixmap

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag

from Tools import XMLTools

# FIXME: use resolveFile!
# read the setupmenu
try:
	# first we search in the current path
	setupfile = file('data/setup.xml', 'r')
except:
	# if not found in the current path, we use the global datadir-path
	setupfile = file('/usr/share/enigma2/setup.xml', 'r')
setupdom = xml.dom.minidom.parseString(setupfile.read())
setupfile.close()

class SetupSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="SetupTitle" position="0,0" size="132,16" font="Regular;12" />
		<widget name="SetupEntry" position="0,16" size="132,32" font="Regular;12" />
		<widget name="SetupValue" position="0,48" size="132,16" font="Regular;12" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["SetupTitle"] = Label(_(parent.setup_title))
		self["SetupEntry"] = Label("")
		self["SetupValue"] = Label("")
		self.parent = parent
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)
		
	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()
	
	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)
		self.parent["config"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		self["SetupEntry"].text = self.parent.getCurrentEntry()
		self["SetupValue"].text = self.parent.getCurrentValue()

class Setup(Screen):

	ALLOW_SUSPEND = True

	def __init__(self, session, setup):
		Screen.__init__(self, session)

		xmldata = setupdom.childNodes[0]
		
		entries = xmldata.childNodes

		self.onChangedEntry = [ ]
		list = []
				
		for x in entries:             #walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'setup':
				if x.getAttribute("key") != setup:
					continue
				self.addItems(list, x.childNodes);
				myTitle = x.getAttribute("title").encode("UTF-8")

		#check for list.entries > 0 else self.close
		
		self["config"] = ConfigList(list)

		self.setup_title = myTitle
		self["title"] = Label(_(self.setup_title))

		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()
		
		self["actions"] = NumberActionMap(["SetupActions"], 
			{
				"cancel": self.keyCancel,
				"ok": self.keyOk,
				"left": self.keyLeft,
				"right": self.keyRight,
				"save": self.keySave,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			}, -1)

		self.changedEntry()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].parent.value)

	def createSummary(self):
		return SetupSummary

	def addItems(self, list, childNode):
		for x in childNode:
			if x.nodeType != xml.dom.minidom.Element.nodeType:
				continue
			elif x.tagName == 'item':
				item_text = _(x.getAttribute("text").encode("UTF-8") or "??")
				b = eval(XMLTools.mergeText(x.childNodes));
				print "item " + item_text + " " + b.configPath
				if b == "":
					continue
				#add to configlist
				item = b.controlType(b)
				
				# the first b is the item itself, ignored by the configList.
				# the second one is converted to string.
				list.append( (item_text, item) )

	def handleKey(self, key):
		# ignore keys when not enabled
		if self["config"].getCurrent()[1].parent.enabled:
			self["config"].handleKey(config.key[key])
			print self["config"].getCurrent()
			self.changedEntry()

	def keyOk(self):
		self.handleKey("choseElement")

	def keyLeft(self):
		self.handleKey("prevElement")

	def keyRight(self):
		self.handleKey("nextElement")

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
		
	def keyNumberGlobal(self, number):
		self.handleKey(str(number))

def getSetupTitle(id):
	xmldata = setupdom.childNodes[0].childNodes
	for x in elementsWithTag(xmldata, "setup"):
		if x.getAttribute("key") == id:
			return x.getAttribute("title").encode("UTF-8")
