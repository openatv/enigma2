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

	def Keycancel(self):
		if self.lastQuery >= 2:
			eDVBCI_UI.getInstance().stopMMI(self.slot)
		self.parent.mmistate = 0
		self.cancel()

	def TimerCheck(self):
		#special cases to prevent to fast resets/inits
		if self.lastQuery == 0:			#reset requested
			self.Keycancel()
		elif self.lastQuery == 1:		#init requested
			self.Keycancel()
		elif self.lastQuery == 4:		#close requested
			self.Keycancel()
		else:
			if eDVBCI_UI.getInstance().getState(self.slot) != 2:	#module removed
				self.Keycancel()
			else:	
				if eDVBCI_UI.getInstance().availableMMI(self.slot) == 1:	#data?
					self.parent.mmistate = 2	#request screen
					self.cancel()

	def __init__(self, session, parent, slot, query):
		Screen.__init__(self, session)

		self["message"] = Label(_("waiting for CI..."))

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.Keycancel
			})
		
		self.parent = parent	
		self.lastQuery = query
		self.slot = slot

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.TimerCheck)
		self.Timer.start(1000)					#check and block 1 second

		if query == 0:									#reset
			#print "reset"
			eDVBCI_UI.getInstance().setReset(slot)
		if query == 1:									#init
			#print "init"
			eDVBCI_UI.getInstance().initialize(slot)
		if query == 2:									#mmi-open
			#print "mmi open"
			eDVBCI_UI.getInstance().startMMI(slot)
		if query == 3:									#mmi-answer
			#print "mmi answer"
			if self.parent.answertype == 0: #ENQ
				eDVBCI_UI.getInstance().answerEnq(slot, self.parent.answertype, self.parent.answer)
			elif self.parent.answertype == 1: #ENQ cancel
				eDVBCI_UI.getInstance().answerEnq(slot, self.parent.answertype, "")
			elif self.parent.answertype == 2: #Menu
				eDVBCI_UI.getInstance().answerMenu(slot, self.parent.answer)
			elif self.parent.answertype == 3: #List
				eDVBCI_UI.getInstance().answerMenu(slot, self.parent.answer)
		if query == 4:									#mmi-close
			#print "mmi close"
			pass
			

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
	def addEntry(self, list, entry):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			list.append( (entry[1], entry[2]) )
		if entry[0] == "PIN":
			if entry[3] == 1:
				# masked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (entry[1], "-")))
			else:				
				# unmasked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (entry[1], "")))			
				
			self.pin = getConfigListEntry(entry[2],x)
			list.append( self.pin )

	def closeMMI(self, cancel):
		if self.tag == "ENQ":
			#print "enq- answer pin:" +  str(self.pin[1].parent.value[0])
			if cancel == 0:
				self.parent.answertype = 0
				self.parent.answer = str(self.pin[1].parent.value[0])
			else:	
				self.parent.answertype = 1
				self.parent.answer = 0
		elif self.tag == "MENU":
			#print "answer - actual:" + str(self["entries"].getCurrent()[1])
			self.parent.answertype = 2
			if cancel == 0:
				self.parent.answer = self["entries"].getCurrent()[1]
			else:	
				self.parent.answer = 0
		elif self.tag == "LIST":
			#print "answer on List"
			self.parent.answertype = 3
			if cancel == 0:
				self.parent.answer = self["entries"].getCurrent()[1]
			else:	
				self.parent.answer = 0

		self.parent.mmistate = 4	#request wait
		self.close()

	def okbuttonClick(self):
		self.closeMMI(0)

	def keyCancel(self):
		print "keyCancel"
		self.closeMMI(1)

	def keyNumberGlobal(self, number):
		self["entries"].handleKey(config.key[str(number)])

	def keyLeft(self):
		self["entries"].handleKey(config.key["prevElement"])

	def keyRight(self):
		self["entries"].handleKey(config.key["nextElement"])

	def __init__(self, session, parent, slotid, appname, entries):
		Screen.__init__(self, session)

		self.parent = parent
		self.slotid = slotid
		self.tag = entries[0][0]
		
		#else the skins fails
		self["title"] = Label("")
		self["subtitle"] = Label("")
		self["bottom"] = Label("")

		list = [ ]
		
		for entry in entries:
			if entry[0] == "TITLE":
				self["title"] = Label(entry[1])
			elif entry[0] == "SUBTITLE":
				self["subtitle"] = Label(entry[1])
			elif entry[0] == "BOTTOM":
				self["bottom"] = Label(entry[1])				
			elif entry[0] == "TEXT":
				self.addEntry(list, entry)
			elif entry[0] == "PIN":
				self.addEntry(list, entry)

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
			#print "something happens"
			self.state = state
			self.createMenu()
	
	def ciWaitAnswer(self):
		#FIXME: handling for correct slot
		#print "ciWaitAnswer with self.mmistate = " + str(self.mmistate)

		if self.mmistate == 0:		
			#print "do nothing"
			pass
		elif self.mmistate == 1:			#wait requested
			#print "wait requested"
			self.session.openWithCallback(self.ciWaitAnswer, CiWait, self, 0, self["entries"].getCurrent()[1])
		elif self.mmistate == 2:			#open screen requested
			#print "open screen requested"
			self.answertype = -1
			self.answer = ""
			appname = eDVBCI_UI.getInstance().getAppName(0)
			list = eDVBCI_UI.getInstance().getMMIScreen(self.slot)
			self.session.openWithCallback(self.ciWaitAnswer, CiMmi, self, self.slot, appname, list)
		elif self.mmistate == 3:			#close mmi requested
			#print "close mmi requested"
			self.session.openWithCallback(self.ciWaitAnswer, CiWait, self, 0, 4)
		elif self.mmistate == 4:			#mmi answer requested
			#print "mmi answer requested"
			self.session.openWithCallback(self.ciWaitAnswer, CiWait, self, 0, 3)
		
	def okbuttonClick(self):
		self.slot = 0
	
		if self.state == 2:
			self.mmistate = 1
			self.ciWaitAnswer()

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
