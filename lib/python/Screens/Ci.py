from Screen import *
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Header import Header
from Components.Button import Button
from Components.Label import Label

from Components.HTMLComponent import *
from Components.GUIComponent import *
from Components.config import *

from enigma import eListbox, eListboxPythonConfigContent

class CiEntryList(HTMLComponent, GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonConfigContent()
		self.l.setList(list)
		self.l.setSeperation(100)
		self.list = list

	def toggle(self):
		selection = self.getCurrent()
		selection[1].toggle()
		self.invalidateCurrent()

	def handleKey(self, key):
		#not every element got an .handleKey
		try:
			selection = self.getCurrent()
			selection[1].handleKey(key)
			self.invalidateCurrent()
		except:	
			pass	
			

	def getCurrent(self):
		return self.l.getCurrentSelection()

	def getCurrentIndex(self):
		return self.l.getCurrentSelectionIndex()

	def invalidateCurrent(self):
		self.l.invalidateEntry(self.l.getCurrentSelectionIndex())

	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)

	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

class CiMmi(Screen):
	def addEntry(self, list, entry, index):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			list.append( (entry[1], index) )
		if entry[0] == "PIN":
			x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("INTEGER", (0, ((10**entry[1])-1))))
			list.append( getConfigListEntry(entry[2],x) )

	def okbuttonClick(self):
		print "actual:" + str(self["entries"].getCurrentIndex())

	def keyNumberGlobal(self, number):
		self["entries"].handleKey(config.key[str(number)])

	def keyLeft(self):
		self["entries"].handleKey(config.key["prevElement"])

	def keyRight(self):
		self["entries"].handleKey(config.key["nextElement"])

	def keyCancel(self):
		print "keyCancel"
		self.close()
		
	def __init__(self, session, slotid, title, subtitle, bottom, entries):
		Screen.__init__(self, session)

		self.slotid = slotid
		self["title"] = Label(title)
		self["subtitle"] = Label(subtitle)
		self["bottom"] = Label(bottom)
				
		list = [ ]
		cnt = 0
		for entry in entries:
			self.addEntry(list, entry, cnt)
			cnt = cnt + 1
		self["entries"] = CiEntryList(list)

		self["actions"] = NumberActionMap(["SetupActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.keyCancel,
				#for PIN
				"left": self.keyLeft,
				"right": self.keyRight,
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

#just for testing - we need an cimanager? (or not?)
class CiSelection(Screen):
	def okbuttonClick(self):
		#generate menu / list
		list = [ ]
		list.append( ("TEXT", "CA-Info") )
		list.append( ("TEXT", "Card Status") )
		list.append( ("PIN", 6, "Card Pin") )
		self.session.open(CiMmi, 0, "Wichtiges CI", "Mainmenu", "Footer", list)
		
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
