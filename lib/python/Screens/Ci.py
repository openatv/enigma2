from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Label import Label

from Components.config import config, ConfigNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_0, ConfigNothing, ConfigPIN
from Components.ConfigList import ConfigList, ConfigListScreen

from Components.SystemInfo import SystemInfo

from enigma import eTimer, eDVBCI_UI, eDVBCIInterfaces

MAX_NUM_CI = 4

def setCIBitrate(configElement):
	if configElement.value == "no":
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateNormal)
	else:
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateHigh)

def InitCiConfig():
	config.ci = ConfigSubList()
	for slot in range(MAX_NUM_CI):
		config.ci.append(ConfigSubsection())
		config.ci[slot].canDescrambleMultipleServices = ConfigSelection(choices = [("auto", _("Auto")), ("no", _("No")), ("yes", _("Yes"))], default = "no")
		if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
			config.ci[slot].canHandleHighBitrates = ConfigSelection(choices = [("no", _("No")), ("yes", _("Yes"))], default = "yes")
			config.ci[slot].canHandleHighBitrates.slotid = slot
			config.ci[slot].canHandleHighBitrates.addNotifier(setCIBitrate)

class MMIDialog(Screen):
	def __init__(self, session, slotid, action, handler = eDVBCI_UI.getInstance(), wait_text = _("wait for ci...") ):
		Screen.__init__(self, session)

		print "MMIDialog with action" + str(action)

		self.mmiclosed = False
		self.tag = None
		self.slotid = slotid

		self.timer = eTimer()
		self.timer.callback.append(self.keyCancel)

		#else the skins fails
		self["title"] = Label("")
		self["subtitle"] = Label("")
		self["bottom"] = Label("")
		self["entries"] = ConfigList([ ])

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

		self.handler = handler
		self.wait_text = wait_text

		if action == 2:		#start MMI
			handler.startMMI(self.slotid)
			self.showWait()
		elif action == 3:		#mmi already there (called from infobar)
			self.showScreen()

	def addEntry(self, list, entry):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			list.append( (entry[1], ConfigNothing(), entry[2]) )
		if entry[0] == "PIN":
			pinlength = entry[1]
			pin = config.cipin.pin1.value
			if len(str(config.cipin.pin1.value)) == 3:
				pin = "0" + str(config.cipin.pin1.value)
				pinlength = 4
			if entry[3] == 1:
				# masked pins:
				x = ConfigPIN(int(pin), len = pinlength, censor = "*")
			else:
				# unmasked pins:
				x = ConfigPIN(int(pin), len = pinlength)
			x.addEndNotifier(self.pinEntered)
			self["subtitle"].setText(entry[2])
			list.append( getConfigListEntry("", x) )
			self["bottom"].setText(_("please press OK when ready"))
			if config.cipin.pin1autook.value:
				self.okbuttonClick()

	def pinEntered(self, value):
		self.okbuttonClick()

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
				self.handler.answerMenu(self.slotid, cur[2])
			else:
				self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "LIST":
			print "answer LIST"
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			pin = config.cipin.pin1.value
			if len(str(config.cipin.pin1.value)) == 3:
				pin = "0" + str(config.cipin.pin1.value)
			cur = self["entries"].getCurrent()
			try:
				answer = str(cur[1].value)
			except:
				answer = str(pin)

			length = len(answer)
			
			try:
				pinlen = cur[1].getLength()
			except:
				pinlen = len(str(pin))
			while length < pinlen:
				answer = '0'+answer
				length+=1
			self.handler.answerEnq(self.slotid, answer)
			self.showWait()

	def closeMmi(self):
		self.timer.stop()
		self.close(self.slotid)

	def keyCancel(self):
		self.timer.stop()
		if not self.tag or self.mmiclosed:
			self.closeMmi()
		elif self.tag == "WAIT":
			self.handler.stopMMI(self.slotid)
			self.closeMmi()
		elif self.tag in ( "MENU", "LIST" ):
			print "cancel list"
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			print "cancel enq"
			self.handler.cancelEnq(self.slotid)
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
		self.keyConfigEntry(KEY_0 + number)

	def keyLeft(self):
		self.timer.stop()
		self.keyConfigEntry(KEY_LEFT)

	def keyRight(self):
		self.timer.stop()
		self.keyConfigEntry(KEY_RIGHT)

	def updateList(self, list):
		List = self["entries"]
		try:
			List.instance.moveSelectionTo(0)
		except:
			pass
		List.l.setList(list)

	def showWait(self):
		self.tag = "WAIT"
		self["title"].setText("")
		self["subtitle"].setText("")
		self["bottom"].setText("")
		list = [(self.wait_text, ConfigNothing())]
		self.updateList(list)

	def showScreen(self):
		screen = self.handler.getMMIScreen(self.slotid)

		list = [ ]

		self.timer.stop()
		if len(screen) > 0 and screen[0][0] == "CLOSE":
			timeout = screen[0][1]
			self.mmiclosed = True
			if timeout > 0:
				self.timer.start(timeout*1000, True)
			else:
				self.keyCancel()
		else:
			self.mmiclosed = False
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
		do_close = False
		if self.action == 0:			#reset
			do_close = True
		if self.action == 1:			#init
			do_close = True

		#module still there ?
		if self.handler.getState(self.slotid) != 2:
			do_close = True

		#mmi session still active ?
		if self.handler.getMMIState(self.slotid) != 1:
			do_close = True

		if do_close:
			self.closeMmi()
		elif self.action > 1 and self.handler.availableMMI(self.slotid) == 1:
			self.showScreen()

		#FIXME: check for mmi-session closed

class CiMessageHandler:
	def __init__(self):
		self.session = None
		self.ci = { }
		self.dlgs = { }
		eDVBCI_UI.getInstance().ciStateChanged.get().append(self.ciStateChanged)
		SystemInfo["CommonInterface"] = eDVBCIInterfaces.getInstance().getNumOfSlots() > 0
		try:
			file = open("/proc/stb/tsmux/ci0_tsclk", "r")
			file.close()
			SystemInfo["CommonInterfaceSupportsHighBitrates"] = True
		except:
			SystemInfo["CommonInterfaceSupportsHighBitrates"] = False

	def setSession(self, session):
		self.session = session

	def ciStateChanged(self, slot):
		if slot in self.ci:
			self.ci[slot](slot)
		else:
			if slot in self.dlgs:
				self.dlgs[slot].ciStateChanged()
			elif eDVBCI_UI.getInstance().availableMMI(slot) == 1:
				if self.session and not config.usage.hide_ci_messages.value:
					try:
						self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, 3)
					except:
						pass

	def dlgClosed(self, slot):
		if slot in self.dlgs:
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
		self.setTitle(_("Common Interface"))
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

		menuList = ConfigList(self.list)
		menuList.list = self.list
		menuList.l.setList(self.list)
		self["entries"] = menuList
		self["entries"].onSelectionChanged.append(self.selectionChanged)
		self["text"] = Label(_("Slot %d")% 1)

	def selectionChanged(self):
		cur_idx = self["entries"].getCurrentIndex()
		self["text"].setText(_("Slot %d")%((cur_idx / 5)+1))

	def keyConfigEntry(self, key):
		try:
			self["entries"].handleKey(key)
			self["entries"].getCurrent()[1].save()
		except:
			pass

	def keyLeft(self):
		self.keyConfigEntry(KEY_LEFT)

	def keyRight(self):
		self.keyConfigEntry(KEY_RIGHT)

	def appendEntries(self, slot, state):
		self.state[slot] = state
		self.list.append( (_("Reset"), ConfigNothing(), 0, slot) )
		self.list.append( (_("Init"), ConfigNothing(), 1, slot) )

		if self.state[slot] == 0:			#no module
			self.list.append( (_("no module found"), ConfigNothing(), 2, slot) )
		elif self.state[slot] == 1:		#module in init
			self.list.append( (_("init module"), ConfigNothing(), 2, slot) )
		elif self.state[slot] == 2:		#module ready
			#get appname
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			self.list.append( (appname, ConfigNothing(), 2, slot) )

		self.list.append(getConfigListEntry(_("Multiple service support"), config.ci[slot].canDescrambleMultipleServices))
		if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
			self.list.append(getConfigListEntry(_("High bitrate support"), config.ci[slot].canHandleHighBitrates))

	def updateState(self, slot):
		state = eDVBCI_UI.getInstance().getState(slot)
		self.state[slot] = state

		slotidx=0
		while len(self.list[slotidx]) < 3 or self.list[slotidx][3] != slot:
			slotidx += 1

		slotidx += 1 # do not change Reset
		slotidx += 1 # do not change Init

		if state == 0:			#no module
			self.list[slotidx] = (_("no module found"), ConfigNothing(), 2, slot)
		elif state == 1:		#module in init
			self.list[slotidx] = (_("init module"), ConfigNothing(), 2, slot)
		elif state == 2:		#module ready
			#get appname
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			self.list[slotidx] = (appname, ConfigNothing(), 2, slot)

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
			action = cur[2]
			slot = cur[3]
			if action == 0:		#reset
				eDVBCI_UI.getInstance().setReset(slot)
			elif action == 1:		#init
				eDVBCI_UI.getInstance().setInit(slot)
			elif self.state[slot] == 2:
				self.dlg = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, action)

	def cancel(self):
		for slot in range(MAX_NUM_CI):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				CiHandler.unregisterCIMessageHandler(slot)
		self.close()

config.cipin = ConfigSubsection()
config.cipin.pin1 = ConfigPIN(1234, len = 4)
config.cipin.pin1autook = ConfigYesNo(default=False)

class CiDefaultPinSetup(ConfigListScreen, Screen):
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.skinName = ["Setup"]
			
		list = []
		list.append(getConfigListEntry(_('Default PIN for CI'), config.cipin.pin1))
		list.append(getConfigListEntry(_('Enable auto PIN'), config.cipin.pin1autook))

		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("Save"))
			
		ConfigListScreen.__init__(self, list)
		self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], 
		{
			'red' : self.dontSaveAndExit,  
			'green': self.saveAndExit, 
			'cancel': self.dontSaveAndExit
		}, -1)

	def saveAndExit(self):
		for x in self['config'].list:
			x[1].save()

		config.cipin.save()
		self.close()

	def dontSaveAndExit(self):
		for x in self['config'].list:
		    x[1].cancel()
		self.close()
		