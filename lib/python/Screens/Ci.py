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

from enigma import *

#use this class to synchronize all ci to/from user communications
class CiWait(Screen):
	def cancel(self):
		#stop pending requests
		self.Timer.stop()
		self.close()

	def TimerCheck(self):
		#special cases to prevent to fast resets/inits
		if self.lastQuery == 0:
			self.cancel()
		elif self.lastQuery == 1:
			self.cancel()

	def __init__(self, session, slot, query):
		Screen.__init__(self, session)

		self["message"] = Label(_("waiting for CI..."))

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.cancel
			})
			
		self.lastQuery = query

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.TimerCheck)

		if query == 0:									#reset
			self.Timer.start(1000)				#block 1 second
			print "reset"
			eDVBCI_UI.getInstance().setReset(0)
		if query == 1:									#init
			self.Timer.start(1000)				#block 1 second
			print "init"
		if query == 2:									#mmi-open
			print "mmi open"
		if query == 3:									#mmi-answer
			print "mmi answer"
			

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
	def createMenu(self):
		self.list = [ ]
		self.list.append( ("Reset", 0) )
		self.list.append( ("Init", 1) )
		
		self.state = eDVBCI_UI.getInstance().getState(0)
		if self.state == 0:			#no module
			self.list.append( ("no module found", 2) )
		elif self.state == 1:		#module in init
			self.list.append( ("init module", 2) )
		elif self.state == 2:		#module ready
			#get appname		
			appname = eDVBCI_UI.getInstance().getAppName(0)
			self.list.append( (appname, 2) )

		self["entries"] .list = self.list
		self["entries"] .l.setList(self.list)

	def TimerCheck(self):
		state = eDVBCI_UI.getInstance().getState(0)
		if self.state != state:
			print "something happens"
			self.state = state
			self.createMenu()
	
	def okbuttonClick(self):
		if self.state == 2:
			#FIXME: find out the correct slot
			self.session.open(CiWait, 0, self["entries"].getCurrent()[1])

		#generate menu / list
		#list = [ ]
		#list.append( ("TEXT", "CA-Info") )
		#list.append( ("TEXT", "Card Status") )
		#list.append( ("PIN", 6, "Card Pin", 1) )
		#self.session.open(CiMmi, 0, 0, "Wichtiges CI", "Mainmenu", "Footer", list)

	def cancel(self):
		self.Timer.stop()
		self.close()
		
	def __init__(self, session):
		#FIXME support for one ci only
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancel
			})

		self.list = [ ]
		self["entries"] = CiEntryList(list)
		self.createMenu()

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.TimerCheck)
		self.Timer.start(1000)
