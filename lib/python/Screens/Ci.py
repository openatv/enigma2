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
MAX_NUM_CI = 4

def InitCiConfig():
	config.ci = [ ]
	for slot in range(MAX_NUM_CI):
		config.ci.append(ConfigSubsection())
		config.ci[slot].canDescrambleMultipleServices = configElement("config.ci%d.canDescrambleMultipleServices"%(slot), configSelection, 0, (("auto", _("Auto")), ("no", _("No")), ("yes", _("Yes"))))

class CiMmi(Screen):
	def __init__(self, session, slotid, action):
		Screen.__init__(self, session)

		print "ciMMI with action" + str(action)

		self.tag = None
		self.slotid = slotid

		self.timer = eTimer()
		self.timer.timeout.get().append(self.keyCancel)

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

		if action == 2:		#start MMI
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
		self.timer.stop()
		if not self.tag:
			return
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
		self.timer.stop()
		self.close(self.slotid)

	def keyCancel(self):
		self.timer.stop()
		if not self.tag:
			return
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
		self.timer.stop()
		try:
			self["entries"].handleKey(key)
		except:
			pass

	def keyNumberGlobal(self, number):
		self.timer.stop()
		self.keyConfigEntry(config.key[str(number)])

	def keyLeft(self):
		self.timer.stop()
		self.keyConfigEntry(config.key["prevElement"])

	def keyRight(self):
		self.timer.stop()
		self.keyConfigEntry(config.key["nextElement"])

	def updateList(self, list):
		List = self["entries"]
		try:
			List.instance.moveSelectionTo(0)
		except:
			List.l.setList(list)
			return

		if self.tag and self.tag == "ENQ":
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

		self.timer.stop()
		if len(screen) > 0 and screen[0][0] == "CLOSE":
			timeout = screen[0][1]
			if timeout > 0:
				self.timer.start(timeout*1000, True)
			else:
				self.keyCancel()
		else:
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

	def ciStateChanged(self):
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

		if self.action > 1 and eDVBCI_UI.getInstance().availableMMI(self.slotid) == 1:
			self.showScreen()

		#FIXME: check for mmi-session closed	

class CiMessageHandler:
	def __init__(self):
		self.session = None
		self.ci = { }
		self.dlgs = { }
		eDVBCI_UI.getInstance().ciStateChanged.get().append(self.ciStateChanged)

	def setSession(self, session):
		self.session = session

	def ciStateChanged(self, slot):
		if slot in self.ci:
			self.ci[slot](slot)
		else:
			if slot in self.dlgs:
				self.dlgs[slot].ciStateChanged()
			elif eDVBCI_UI.getInstance().availableMMI(slot) == 1:
				if self.session:
					self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, CiMmi, slot, 3)
				else:
					print "no session"

	def dlgClosed(self, slot):
		del self.dlgs[slot]

	def registerCIMessageHandler(self, slot, func):
		self.unregisterCIMessageHandler(slot)
		self.ci[slot] = func

	def unregisterCIMessageHandler(self, slot):
		if slot in self.ci:
			del self.ci[slot]

CiHandler = CiMessageHandler()

class CiSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions", "CiSelectionActions"],
			{
				"left": self.keyLeft,
				"right": self.keyLeft,
				"ok": self.okbuttonClick,
				"cancel": self.cancel
			},-1)

		self.dlg = None
		self.state = { }
		self.list = [ ]

		for slot in range(MAX_NUM_CI):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				self.appendEntries(slot, state)
				CiHandler.registerCIMessageHandler(slot, self.ciStateChanged)

		menuList = ConfigList(list)
		menuList.list = self.list
		menuList.l.setList(self.list)
		self["entries"] = menuList

	def keyConfigEntry(self, key):
		try:
			self["entries"].handleKey(key)
			self["entries"].getCurrent()[1].save()
		except:
			pass

	def keyLeft(self):
		self.keyConfigEntry(config.key["prevElement"])

	def keyRight(self):
		self.keyConfigEntry(config.key["nextElement"])

	def appendEntries(self, slot, state):
		self.state[slot] = state
		self.list.append( (_("Reset"), 0, slot) )
		self.list.append( (_("Init"), 1, slot) )

		if self.state[slot] == 0:			#no module
			self.list.append( (_("no module found"), 2, slot) )
		elif self.state[slot] == 1:		#module in init
			self.list.append( (_("init module"), 2, slot) )
		elif self.state[slot] == 2:		#module ready
			#get appname
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			self.list.append( (appname, 2, slot) )

		self.list.append(getConfigListEntry(_("Multiple service support"), config.ci[slot].canDescrambleMultipleServices))

	def updateState(self, slot):
		state = eDVBCI_UI.getInstance().getState(slot)
		self.state[slot] = state

		slotidx=0
		while self.list[slotidx][2] != slot:
			slotidx += 1

		slotidx += 1 # do not change Reset
		slotidx += 1 # do not change Init

		if state == 0:			#no module
			self.list[slotidx] = (_("no module found"), 2, slot)
		elif state == 1:		#module in init
			self.list[slotidx] = (_("init module"), 2, slot)
		elif state == 2:		#module ready
			#get appname
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			self.list[slotidx] = (appname, 2, slot)

		lst = self["entries"]
		lst.list = self.list
		lst.l.setList(self.list)

	def ciStateChanged(self, slot):
		if self.dlg:
			self.dlg.ciStateChanged()
		else:
			state = eDVBCI_UI.getInstance().getState(slot)
			if self.state[slot] != state:
				#print "something happens"
				self.state[slot] = state
				self.updateState(slot)

	def dlgClosed(self, slot):
		self.dlg = None

	def okbuttonClick(self):
		cur = self["entries"].getCurrent()
		if cur and len(cur) > 2:
			action = cur[1]
			slot = cur[2]
			if action == 0:		#reset
				eDVBCI_UI.getInstance().setReset(slot)
			elif action == 1:		#init
				eDVBCI_UI.getInstance().setInit(slot)
			elif self.state[slot] == 2:
				self.dlg = self.session.openWithCallback(self.dlgClosed, CiMmi, slot, action)

	def cancel(self):
		CiHandler.unregisterCIMessageHandler(0)
		self.close()
