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
			if entry[3] == 1:
				# masked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (entry[1], "-")))
			else:				
				# unmasked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (entry[1], "")))			
				
			self.pin = getConfigListEntry(entry[2],x)
			list.append( self.pin )

	def okbuttonClick(self):
		if self.tag == 0:	#ENQ
			print "enq- answer pin:" +  str(self.pin[1].parent.value[0])
			#ci[self.slotid]->getInstance().mmiEnqAnswer(self.pin[1].parent.value[0])
		elif self.tag == 1:	#Menu
			print "answer - actual:" + str(self["entries"].getCurrentIndex())
			#ci[self.slotid]->getInstance().mmiAnswer(self["entries"].getCurrentIndex())
		elif self.tag == 2:	#List
			print "answer on List - send 0"
			#ci[self.slotid]->getInstance().mmiAnswer(0)
		self.close()

	def keyNumberGlobal(self, number):
		self["entries"].handleKey(config.key[str(number)])

	def keyLeft(self):
		self["entries"].handleKey(config.key["prevElement"])

	def keyRight(self):
		self["entries"].handleKey(config.key["nextElement"])

	def keyCancel(self):
		print "keyCancel"
		self.close()
		
		#tag is 0=ENQ 1=Menu 2=List
	def __init__(self, session, slotid, tag, title, subtitle, bottom, entries):
		Screen.__init__(self, session)

		self.slotid = slotid
		self.tag = tag
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

class CiSelection(Screen):
	def okbuttonClick(self):
	
		if self["entries"].getCurrent()[1] == 0:		#reset
			print "ci reset requested"
			pass
		if self["entries"].getCurrent()[1] == 1:		#init
			print "ci init requested"
			pass
		if self["entries"].getCurrent()[1] == 2:		#mmi open
			#ci->getInstance().mmiOpen() and wait for list of elments ???
			#generate menu / list
			list = [ ]
			list.append( ("TEXT", "CA-Info") )
			list.append( ("TEXT", "Card Status") )
			list.append( ("PIN", 6, "Card Pin", 1) )
			self.session.open(CiMmi, 0, 0, "Wichtiges CI", "Mainmenu", "Footer", list)
		
	def __init__(self, session):
		#FIXME support for one ci only
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
			
		list = [ ]
		list.append( ("Reset", 0) )
		list.append( ("Init", 1) )
		#add timer for "app-manager name" ?
		list.append( ("Irdeto Blasel SE", 2) )
		self["entries"] = CiEntryList(list)
