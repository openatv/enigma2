from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_0, ConfigNothing, ConfigPIN, ConfigText, ConfigYesNo, NoSave
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.SystemInfo import SystemInfo
from enigma import eTimer, eDVBCI_UI, eDVBCIInterfaces
import Screens.Standby

from boxbranding import getBoxType

MAX_NUM_CI = 4

forceNotShowCiMessages = False

def setCIBitrate(configElement):
	if configElement.value == "no":
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateNormal)
	else:
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateHigh)

def setdvbCiDelay(configElement):
	open(SystemInfo["CommonInterfaceCIDelay"], "w").write(configElement.value)
	configElement.save()

def InitCiConfig():
	config.ci = ConfigSubList()
	config.cimisc = ConfigSubsection()
	for slot in range(MAX_NUM_CI):
		config.ci.append(ConfigSubsection())
		config.ci[slot].canDescrambleMultipleServices = ConfigSelection(choices = [("auto", _("Auto")), ("no", _("No")), ("yes", _("Yes"))], default = "auto")
		config.ci[slot].use_static_pin = ConfigYesNo(default = True)
		config.ci[slot].static_pin = ConfigPIN(default = 0)
		config.ci[slot].show_ci_messages = ConfigYesNo(default = True)
		if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
			config.ci[slot].canHandleHighBitrates = ConfigSelection(choices = [("no", _("No")), ("yes", _("Yes"))], default = "yes")
			config.ci[slot].canHandleHighBitrates.slotid = slot
			config.ci[slot].canHandleHighBitrates.addNotifier(setCIBitrate)
		if SystemInfo["CommonInterfaceCIDelay"]:
			config.cimisc.dvbCiDelay = ConfigSelection(default = "256", choices = [ ("16", _("16")), ("32", _("32")), ("64", _("64")), ("128", _("128")), ("256", _("256"))] )
			config.cimisc.dvbCiDelay.addNotifier(setdvbCiDelay)

class MMIDialog(Screen):
	def __init__(self, session, slotid, action, handler=eDVBCI_UI.getInstance(), wait_text="", screen_data=None):
		Screen.__init__(self, session)

		print "[CI] with action" + str(action)

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

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.keyCancel,
				"menu": self.forceExit,
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
		self.screen_data = screen_data

		self.is_pin_list = -1
		self.handler = handler
		if wait_text == "":
			self.wait_text = _("Wait for ci...")
		else:
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
			if entry[3] == 1:
				# masked pins:
				x = ConfigPIN(0, len = pinlength, censor = "*")
			else:
				# unmasked pins:
				x = ConfigPIN(0, len = pinlength)
			x.addEndNotifier(self.pinEntered)
			self["subtitle"].setText(entry[2])
			list.append( getConfigListEntry("", x) )
			self["bottom"].setText(_("Please press OK when ready"))

	def pinEntered(self, value):
		self.okbuttonClick()

	def okbuttonClick(self):
		self.timer.stop()
		if not self.tag:
			return
		if self.tag == "WAIT":
			print "[CI] do nothing - wait"
		elif self.tag == "MENU":
			print "[CI] answer MENU"
			cur = self["entries"].getCurrent()
			if cur:
				self.handler.answerMenu(self.slotid, cur[2])
			else:
				self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "LIST":
			print "[CI] answer LIST"
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			cur = self["entries"].getCurrent()
			answer = str(cur[1].value)
			length = len(answer)
			while length < cur[1].getLength():
				answer = '0' + answer
				length += 1
			self.answer = answer
			if config.ci[self.slotid].use_static_pin.value:
				self.session.openWithCallback(self.save_PIN_CB, MessageBox, _("Would you save the entered PIN %s persistent?") % self.answer, MessageBox.TYPE_YESNO)
			else:
				self.save_PIN_CB(False)

	def save_PIN_CB(self, ret=None):
		if ret:
			config.ci[self.slotid].static_pin.value = self.answer
			config.ci[self.slotid].static_pin.save()
		self.handler.answerEnq(self.slotid, self.answer)
		self.showWait()

	def closeMmi(self):
		self.timer.stop()
		self.close(self.slotid)

	def forceExit(self):
		self.timer.stop()
		if self.tag == "WAIT":
			self.handler.stopMMI(self.slotid)
			global forceNotShowCiMessages
			forceNotShowCiMessages = True
			self.close(self.slotid)

	def keyCancel(self):
		self.timer.stop()
		if not self.tag or self.mmiclosed:
			self.closeMmi()
		elif self.tag == "WAIT":
			self.handler.stopMMI(self.slotid)
			self.closeMmi()
		elif self.tag in ( "MENU", "LIST" ):
			print "[CI] cancel list"
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			print "[CI] cancel enq"
			self.handler.cancelEnq(self.slotid)
			self.showWait()
		else:
			print "[CI] give cancel action to ci"

	def keyConfigEntry(self, key):
		self.timer.stop()
		try:
			self["entries"].handleKey(key)
			if self.is_pin_list == 4:
				self.okbuttonClick()
		except:
			pass

	def keyNumberGlobal(self, number):
		self.timer.stop()
		if self.is_pin_list > -1:
			self.is_pin_list += 1
		self.keyConfigEntry(KEY_0 + number)

	def keyLeft(self):
		self.timer.stop()
		if self.is_pin_list > 0:
			self.is_pin_list += -1
		self.keyConfigEntry(KEY_LEFT)

	def keyRight(self):
		self.timer.stop()
		if self.is_pin_list > -1 and self.is_pin_list < 4:
			self.is_pin_list += 1
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
		if self.screen_data is not None:
			screen = self.screen_data
			self.screen_data = None
		else:
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
					if config.ci[self.slotid].use_static_pin.value and str(config.ci[self.slotid].static_pin.value) != "0":
						answer = str(config.ci[self.slotid].static_pin.value)
						length = len(answer)
						while length < config.ci[self.slotid].static_pin.getLength():
							answer = '0' + answer
							length += 1
						self.handler.answerEnq(self.slotid, answer)
						self.showWait()
						break
					else:
						self.is_pin_list = 0
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
		self.auto_close = False
		self.ci = { }
		self.dlgs = { }
		eDVBCI_UI.getInstance().ciStateChanged.get().append(self.ciStateChanged)
		if getBoxType() in ('vuzero'):
			SystemInfo["CommonInterface"] = False
		else:
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
			handler = eDVBCI_UI.getInstance()
			if slot in self.dlgs:
				self.dlgs[slot].ciStateChanged()
			elif handler.availableMMI(slot) == 1:
				if self.session:
					show_ui = False
					if config.ci[slot].show_ci_messages.value:
						show_ui = True
					screen_data = handler.getMMIScreen(slot)
					if config.ci[slot].use_static_pin.value:
						if screen_data is not None and len(screen_data):
							ci_tag = screen_data[0][0]
							if ci_tag == 'ENQ' and len(screen_data) >= 2 and screen_data[1][0] == 'PIN':
								if str(config.ci[slot].static_pin.value) == "0":
									show_ui = True
								else:
									answer = str(config.ci[slot].static_pin.value)
									length = len(answer)
									while length < config.ci[slot].static_pin.getLength():
										answer = '0' + answer
										length += 1
									handler.answerEnq(slot, answer)
									show_ui = False
									self.auto_close = True
							elif ci_tag == 'CLOSE' and self.auto_close:
								show_ui = False
								self.auto_close = False
					if show_ui and not forceNotShowCiMessages and not Screens.Standby.inStandby:
						self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, 3, screen_data = screen_data)

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
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Common interface")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

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
		self["text"] = Label(_("Slot %d")%(1))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		global forceNotShowCiMessages
		forceNotShowCiMessages = False
		self.setTitle(_("Common interface"))

	def selectionChanged(self):
		cur_idx = self["entries"].getCurrentIndex()
		self["text"].setText(_("Slot %d")%((cur_idx / len(self.list))+1))

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
		self.list.append((_("Reset"), ConfigNothing(), 0, slot))
		self.list.append((_("Init"), ConfigNothing(), 1, slot))

		if self.state[slot] == 0: #no module
			self.list.append((_("No module found"), ConfigNothing(), 2, slot))
		elif self.state[slot] == 1: #module in init
			self.list.append((_("Init module"), ConfigNothing(), 2, slot))
		elif self.state[slot] == 2: #module ready
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			self.list.append((appname, ConfigNothing(), 2, slot))
		self.list.append(getConfigListEntry(_("Set pin code persistent"), config.ci[slot].use_static_pin))
		self.list.append((_("Enter persistent PIN code"), ConfigNothing(), 5, slot))
		self.list.append((_("Reset persistent PIN code"), ConfigNothing(), 6, slot))
		self.list.append(getConfigListEntry(_("Show CI messages"), config.ci[slot].show_ci_messages))
		self.list.append(getConfigListEntry(_("Multiple service support"), config.ci[slot].canDescrambleMultipleServices))
		if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
			self.list.append(getConfigListEntry(_("High bitrate support"), config.ci[slot].canHandleHighBitrates))
		if SystemInfo["CommonInterfaceCIDelay"]:
			self.list.append(getConfigListEntry(_("DVB CI delay"), config.cimisc.dvbCiDelay))

	def updateState(self, slot):
		state = eDVBCI_UI.getInstance().getState(slot)
		self.state[slot] = state

		slotidx=0
		while len(self.list[slotidx]) < 3 or self.list[slotidx][3] != slot:
			slotidx += 1

		slotidx += 1 #do not change Reset
		slotidx += 1 #do not change Init

		if state == 0: #no module
			self.list[slotidx] = (_("No module found"), ConfigNothing(), 2, slot)
		elif state == 1: #module in init
			self.list[slotidx] = (_("Init module"), ConfigNothing(), 2, slot)
		elif state == 2: #module ready
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
				self.state[slot] = state
				self.updateState(slot)

	def dlgClosed(self, slot):
		self.dlg = None

	def okbuttonClick(self):
		cur = self["entries"].getCurrent()
		if cur and len(cur) > 2:
			action = cur[2]
			slot = cur[3]
			if action == 0: #reset
				eDVBCI_UI.getInstance().setReset(slot)
			elif action == 1: #init
				eDVBCI_UI.getInstance().setInit(slot)
			elif action == 5:
				self.session.openWithCallback(self.cancelCB, PermanentPinEntry, config.ci[slot].static_pin, _("Smartcard PIN"))
			elif action == 6:
				config.ci[slot].static_pin.value = 0
				config.ci[slot].static_pin.save()
				self.session.openWithCallback(self.cancelCB, MessageBox, _("The saved PIN was cleared."), MessageBox.TYPE_INFO)
			elif self.state[slot] == 2:
				self.dlg = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, action)

	def cancelCB(self, value):
		pass

	def cancel(self):
		for slot in range(MAX_NUM_CI):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				CiHandler.unregisterCIMessageHandler(slot)
		self.close()

class PermanentPinEntry(Screen, ConfigListScreen):
	def __init__(self, session, pin, pin_slot):
		Screen.__init__(self, session)
		self.skinName = ["ParentalControlChangePin", "Setup" ]
		self.setup_title = _("Enter pin code")
		self.onChangedEntry = [ ]

		self.slot = pin_slot
		self.pin = pin
		self.list = []
		self.pin1 = ConfigPIN(default = 0, censor = "*")
		self.pin2 = ConfigPIN(default = 0, censor = "*")
		self.pin1.addEndNotifier(boundFunction(self.valueChanged, 1))
		self.pin2.addEndNotifier(boundFunction(self.valueChanged, 2))
		self.list.append(getConfigListEntry(_("Enter PIN"), NoSave(self.pin1)))
		self.list.append(getConfigListEntry(_("Re-enter PIN"), NoSave(self.pin2)))
		ConfigListScreen.__init__(self, self.list)

		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions"],
		{
			"cancel": self.cancel,
			"red": self.cancel,
			"save": self.keyOK,
		}, -1)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def valueChanged(self, pin, value):
		if pin == 1:
			self["config"].setCurrentIndex(1)
		elif pin == 2:
			self.keyOK()

	def keyOK(self):
		if self.pin1.value == self.pin2.value:
			self.pin.value = self.pin1.value
			self.pin.save()
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code has been saved successfully."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("The PIN codes you entered are different."), MessageBox.TYPE_ERROR)

	def cancel(self):
		self.close(None)

	def keyNumberGlobal(self, number):
		ConfigListScreen.keyNumberGlobal(self, number)

	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
