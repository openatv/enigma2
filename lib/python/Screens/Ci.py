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
from Components.ConfigList import ConfigList

from enigma import eTimer, eDVBCI_UI, eListboxPythonStringContent, eListboxPythonConfigContent

TYPE_MENU = 0
TYPE_CONFIG = 1

class CiMmi(Screen):
	def __init__(self, session, slotid, action):
		Screen.__init__(self, session)

		print "ciMMI with action" + str(action)

		self.slotid = slotid

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.TimerCheck)
		self.Timer.start(1000)

		#else the skins fails
		self["title"] = Label("")
		self["subtitle"] = Label("")
		self["bottom"] = Label("")
		self["entries"] = ConfigList([ ])
		self.listtype = TYPE_CONFIG

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

		self.action = action

		if action == 0:			#reset
			eDVBCI_UI.getInstance().setReset(self.slotid)
			self.showWait()
		elif action == 1:		#init
			eDVBCI_UI.getInstance().setInit(self.slotid)
		elif action == 2:		#start MMI
			eDVBCI_UI.getInstance().startMMI(self.slotid)
			self.showWait()
		elif action == 3:		#mmi already there (called from infobar)
			self.showScreen()

	def addEntry(self, list, entry):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			list.append( (entry[1], entry[2]) )
		if entry[0] == "PIN":
			self.pinlength = entry[1]
			if entry[3] == 1:
				# masked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (self.pinlength, "*")))
			else:				
				# unmasked pins:
				x = configElement_nonSave("", configSequence, [1234], configsequencearg.get("PINCODE", (self.pinlength, "")))
			self["subtitle"].setText(entry[2])
			self.pin = getConfigListEntry("",x)
			list.append( self.pin )
			self["bottom"].setText(_("please press OK when ready"))

	def okbuttonClick(self):
		print "ok"
		if self.tag == "WAIT":
			print "do nothing - wait"
		elif self.tag == "MENU":
			print "answer MENU"
			cur = self["entries"].getCurrent()
			if cur:
				eDVBCI_UI.getInstance().answerMenu(self.slotid, cur[1])
			else:
				eDVBCI_UI.getInstance().answerMenu(self.slotid, 0)
			self.showWait()	
		elif self.tag == "LIST":
			print "answer LIST"
			eDVBCI_UI.getInstance().answerMenu(self.slotid, 0)
			self.showWait()	
		elif self.tag == "ENQ":
			answer = str(self.pin[1].parent.value[0])
			length = len(answer)
			while length < self.pinlength:
				answer = '0'+answer
				length+=1
			eDVBCI_UI.getInstance().answerEnq(self.slotid, answer)
			self.showWait()

	def closeMmi(self):
		self.Timer.stop()
		self.close()

	def keyCancel(self):
		print "keyCancel"
		if self.tag == "WAIT":
			eDVBCI_UI.getInstance().stopMMI(self.slotid)
			self.closeMmi()
		elif self.tag in [ "MENU", "LIST" ]:
			print "cancel list"
			eDVBCI_UI.getInstance().answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			print "cancel enq"
			eDVBCI_UI.getInstance().cancelEnq(self.slotid)
			self.showWait()
		else:
			print "give cancel action to ci"	

	def keyConfigEntry(self, key):
		try:
			self["entries"].handleKey(key)
		except AttributeError:
			pass

	def keyNumberGlobal(self, number):
		self.keyConfigEntry(config.key[str(number)])

	def keyLeft(self):
		self.keyConfigEntry(config.key["prevElement"])

	def keyRight(self):
		self.keyConfigEntry(config.key["nextElement"])

	def updateList(self, list):
		List = self["entries"]
		try:
			List.instance.moveSelectionTo(0)
		except:
			List.l.setList(list)
			return

		if self.tag == "ENQ":
			type = TYPE_CONFIG
		else:
			type = TYPE_MENU

		if type != self.listtype:
			if type == TYPE_CONFIG:
				List.l = eListboxPythonConfigContent()
			else:
				List.l = eListboxPythonStringContent()
			List.instance.setContent(List.l)
			self.listtype = type

		List.l.setList(list)

	def showWait(self):
		self.tag = "WAIT"
		self["title"].setText("")
		self["subtitle"].setText("")
		self["bottom"].setText("")
		list = [ ]
		list.append( ("wait for ci...", 0) )
		self.updateList(list)

	def showScreen(self):
		screen = eDVBCI_UI.getInstance().getMMIScreen(self.slotid)
	
		list = [ ]

		self.tag = screen[0][0]

		for entry in screen:
			if entry[0] == "PIN":
				self.addEntry(list, entry)
			else:
				if entry[0] == "TITLE":
					self["title"].setText(entry[1])
				elif entry[0] == "SUBTITLE":
					self["subtitle"].setText(entry[1])
				elif entry[0] == "BOTTOM":
					self["bottom"].setText(entry[1])
				elif entry[0] == "TEXT":
					self.addEntry(list, entry)
		self.updateList(list)

	def TimerCheck(self):
		if self.action == 0:			#reset
			self.closeMmi()
		if self.action == 1:			#init
			self.closeMmi()

		#module still there ?			
		if eDVBCI_UI.getInstance().getState(self.slotid) != 2:
			self.closeMmi()

		#mmi session still active ?			
		if eDVBCI_UI.getInstance().getMMIState(self.slotid) != 1:
			self.closeMmi()

		if eDVBCI_UI.getInstance().availableMMI(self.slotid) == 1:
			self.showScreen()

		#FIXME: check for mmi-session closed	

class CiSelection(Screen):
	def createMenu(self):
		self.list = [ ]
		self.list.append( (_("Reset"), 0) )
		self.list.append( (_("Init"), 1) )
		
		self.state = eDVBCI_UI.getInstance().getState(0)
		if self.state == 0:			#no module
			self.list.append( (_("no module found"), 2) )
		elif self.state == 1:		#module in init
			self.list.append( (_("init module"), 2) )
		elif self.state == 2:		#module ready
			#get appname		
			appname = eDVBCI_UI.getInstance().getAppName(0)
			self.list.append( (appname, 2) )

		self["entries"].list = self.list
		self["entries"].l.setList(self.list)

	def TimerCheck(self):
		state = eDVBCI_UI.getInstance().getState(0)
		if self.state != state:
			#print "something happens"
			self.state = state
			self.createMenu()
	
	def okbuttonClick(self):
		self.slot = 0
	
		if self.state == 2:
			self.session.open(CiMmi, 0, self["entries"].getCurrent()[1])

		#generate menu / list
		#list = [ ]
		#list.append( ("TEXT", "CA-Info") )
		#list.append( ("TEXT", "Card Status") )
		#list.append( ("PIN", 6, "Card Pin", 1) )
		#self.session.open(CiMmi, 0, 0, "Wichtiges CI", "Mainmenu", "Footer", list)

	def cancel(self):
		self.Timer.stop()
		self.close()

	def mmiAvail(self, slot):
		print "mmi avail slot", slot

	def __init__(self, session):
		#FIXME support for one ci only
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancel
			})

		self.list = [ ]
		self["entries"] = MenuList(list)
		self.createMenu()

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.TimerCheck)
		self.Timer.start(1000)

		eDVBCI_UI.getInstance().mmiAvail.get().append(self.mmiAvail)
