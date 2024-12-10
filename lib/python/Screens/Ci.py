from os import remove
from os.path import exists
from enigma import eTimer, eDVBCI_UI

from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.config import config, ConfigEnableDisable, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_0, ConfigNothing, ConfigPIN, ConfigYesNo, NoSave
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.SystemInfo import BoxInfo
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
import Screens.Standby
from Tools.BoundFunction import boundFunction

forceNotShowCiMessages = False


def setCIBitrate(configElement):
	eDVBCI_UI.getInstance().setClockRate(configElement.slotid, configElement.value)


def setCIEnabled(configElement):
	eDVBCI_UI.getInstance().setEnabled(configElement.slotid, configElement.value)


def setdvbCiDelay(configElement):
	open(BoxInfo.getItem("CommonInterfaceCIDelay"), "w").write(configElement.value)
	configElement.save()


def setRelevantPidsRouting(configElement):
	open(BoxInfo.getItem(f"CI{configElement.slotid}RelevantPidsRoutingSupport"), "w").write("yes" if configElement.value else "no")


def InitCiConfig():
	config.ci = ConfigSubList()
	config.cimisc = ConfigSubsection()
	config.cimisc.cihelperenabled = ConfigEnableDisable(default=True)
	if BoxInfo.getItem("CommonInterface"):
		for slot in range(BoxInfo.getItem("CommonInterface")):
			config.ci.append(ConfigSubsection())
			config.ci[slot].enabled = ConfigYesNo(default=True)
			config.ci[slot].enabled.slotid = slot
			config.ci[slot].enabled.addNotifier(setCIEnabled, initial_call=False)
			config.ci[slot].canDescrambleMultipleServices = ConfigSelection(choices=[("auto", _("Auto")), ("no", _("No")), ("yes", _("Yes"))], default="auto")
			config.ci[slot].use_static_pin = ConfigYesNo(default=True)
			config.ci[slot].static_pin = ConfigPIN(default=0)
			config.ci[slot].show_ci_messages = ConfigYesNo(default=True)
			config.ci[slot].disable_operator_profile = ConfigYesNo(default=False)
			config.ci[slot].alternative_ca_handling = ConfigSelection(choices=[(0, _("off")), (1, _("Close CA device at programm end")), (2, _("Offset CA device index")), (3, _("Offset and close CA device"))], default=0)
			if BoxInfo.getItem(f"CI{slot}SupportsHighBitrates"):
				highBitrateChoices = [
					("normal", _("Normal")),
					("high", _("High")),
				]
				try:
					with open(f"/proc/stb/tsmux/ci{slot}_tsclk_choices") as fd:
						choices = fd.read()
						if "extra_high" in choices:
							highBitrateChoices.append(("extra_high", _("Extra High")))
				except OSError:
					pass
				config.ci[slot].highBitrate = ConfigSelection(default="high", choices=highBitrateChoices)
				config.ci[slot].highBitrate.slotid = slot
				config.ci[slot].highBitrate.addNotifier(setCIBitrate)
			if BoxInfo.getItem(f"CI{slot}RelevantPidsRoutingSupport"):
				config.ci[slot].relevantPidsRouting = ConfigYesNo(default=False)
				config.ci[slot].relevantPidsRouting.slotid = slot
				config.ci[slot].relevantPidsRouting.addNotifier(setRelevantPidsRouting)
		if BoxInfo.getItem("CommonInterfaceCIDelay"):
			config.cimisc.dvbCiDelay = ConfigSelection(default="256", choices=[("16", "16"), ("32", "32"), ("64", "64"), ("128", "128"), ("256", "256")])
			config.cimisc.dvbCiDelay.addNotifier(setdvbCiDelay)
		config.cimisc.bootDelay = ConfigSelection(default=5, choices=[(x, _("%d Seconds") % x) for x in range(16)])


class MMIDialog(Screen):
	def __init__(self, session, slotid, action, handler=eDVBCI_UI.getInstance(), wait_text="", screen_data=None):
		Screen.__init__(self, session)

		print(f"[CI] MMIDialog with action {str(action)}")

		self.mmiclosed = False
		self.tag = None
		self.slotid = slotid

		self.timer = eTimer()
		self.timer.callback.append(self.keyCancel)

		#else the skins fails
		self["title"] = Label("")
		self["subtitle"] = Label("")
		self["bottom"] = Label("")
		self["key_menu"] = StaticText(_("MENU"))
		self["entries"] = ConfigList([])

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
			self.wait_text = _("wait for ci...")
		else:
			self.wait_text = wait_text

		if action == 2:		#start MMI
			handler.startMMI(self.slotid)
			self.showWait()
		elif action == 3:		#mmi already there (called from infobar)
			self.showScreen()

	def addEntry(self, list, entry):
		if entry[0] == "TEXT":		#handle every item (text / pin only?)
			list.append((entry[1], ConfigNothing(), entry[2]))
		if entry[0] == "PIN":
			pinlength = entry[1]
			censor = "*" if entry[3] == 1 else ""
			x = ConfigPIN(0, pinLength=pinlength, censor=censor)
			x.addEndNotifier(self.pinEntered)
			self["subtitle"].setText(entry[2])
			list.append(getConfigListEntry("", x))
			self["bottom"].setText(_("Please press OK when ready"))

	def pinEntered(self, value):
		self.okbuttonClick()

	def okbuttonClick(self):
		self.timer.stop()
		if not self.tag:
			return
		if self.tag == "WAIT":
			print("[CI] do nothing - wait")
		elif self.tag == "MENU":
			print("[CI] answer MENU")
			cur = self["entries"].getCurrent()
			if cur:
				self.handler.answerMenu(self.slotid, cur[2])
			else:
				self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "LIST":
			print("[CI] answer LIST")
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			cur = self["entries"].getCurrent()
			answer = str(cur[1].value)
			length = len(answer)
			while length < cur[1].getLength():
				answer = f"0{answer}"
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
		elif self.tag in ("MENU", "LIST"):
			print("[CI] cancel list")
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			print("[CI] cancel enq")
			self.handler.cancelEnq(self.slotid)
			self.showWait()
		else:
			print("[CI] give cancel action to ci")

	def keyConfigEntry(self, key):
		self.timer.stop()
		try:
			self["entries"].handleKey(key)
			if self.is_pin_list == 4:
				self.okbuttonClick()
		except Exception:
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
		except Exception:
			pass
		List.l.setList(list)

	def showWait(self):
		self.tag = "WAIT"
		self["title"].setText("")
		self["subtitle"].setText("")
		self["bottom"].setText("")
		list = []
		list.append((self.wait_text, ConfigNothing()))
		self.updateList(list)

	def showScreen(self):
		if self.screen_data is not None:
			screen = self.screen_data
			self.screen_data = None
		else:
			screen = self.handler.getMMIScreen(self.slotid)

		list = []

		self.timer.stop()
		if len(screen) > 0 and screen[0][0] == "CLOSE":
			timeout = screen[0][1]
			self.mmiclosed = True
			if timeout > 0:
				self.timer.start(timeout * 1000, True)
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
							answer = f"0{answer}"
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
		self.ci = {}
		self.dlgs = {}
		eDVBCI_UI.getInstance().ciStateChanged.get().append(self.ciStateChanged)

	def setSession(self, session):
		self.session = session

	def ciStateChanged(self, slot):
		if slot in self.ci:
			self.ci[slot](slot)
		else:
			handler = eDVBCI_UI.getInstance()
			if slot in self.dlgs:
				self.dlgs[slot].ciStateChanged()
			elif handler.availableMMI(slot) == 1 and self.session:
				show_ui = False
				if config.ci[slot].show_ci_messages.value:
					show_ui = True
				screen_data = handler.getMMIScreen(slot)
				if config.ci[slot].use_static_pin.value:
					if screen_data is not None and len(screen_data):
						ci_tag = screen_data[0][0]
						if ci_tag == "ENQ" and len(screen_data) >= 2 and screen_data[1][0] == "PIN":
							if str(config.ci[slot].static_pin.value) == "0":
								show_ui = True
							else:
								answer = str(config.ci[slot].static_pin.value)
								length = len(answer)
								while length < config.ci[slot].static_pin.getLength():
									answer = f"0{answer}"
									length += 1
								handler.answerEnq(slot, answer)
								show_ui = False
								self.auto_close = True
						elif ci_tag == "CLOSE" and self.auto_close:
							show_ui = False
							self.auto_close = False
				if show_ui and not forceNotShowCiMessages and not Screens.Standby.inStandby and not config.misc.firstrun.value:
					try:
						self.dlgs[slot] = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, 3, screen_data=screen_data)
					except Exception:
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


class CiSelection(Setup):
	def __init__(self, session):
		self.dlg = None
		self.state = {}
		self.ciplushelper = config.cimisc.cihelperenabled.value and BoxInfo.getItem("CIPlusHelper") and BoxInfo.getItem("CommonInterface")
		Setup.__init__(self, session=session, setup="CiSelection")
		self.skinName = ["Setup"]
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		global forceNotShowCiMessages
		forceNotShowCiMessages = False

	def createSetup(self):  # NOSONAR silence S2638
		self.slot = 0
		items = []
		for slot in range(BoxInfo.getItem("CommonInterface")):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				self.slot += 1
				items = items + self.appendEntries(slot, state)
				CiHandler.registerCIMessageHandler(slot, self.ciStateChanged)
		Setup.createSetup(self, appendItems=items)

	def ciStateChanged(self, slot):
		if self.dlg:
			self.dlg.ciStateChanged()
		else:
			state = eDVBCI_UI.getInstance().getState(slot)
			if self.state[slot] != state:
				self.state[slot] = state
				self.updateState(slot)

	def updateState(self, slot):
		self.createSetup()

	def appendEntries(self, slot, state):
		items = []
		items.append(("**************************",))  # Add the comment line to the config list.

		self.state[slot] = state
		text = _("Slot %d") % (slot + 1)
		if state in (0, 3):
			text = "%s - %s" % (text, state == 0 and _("no module found") or _("module disabled"))
		items.append((text,))

		items.append((_("CI enabled"), config.ci[slot].enabled))
		if self.state[slot] in (0, 3):
			return items
		if not self.ciplushelper:
			items.append((_("Reset"), ConfigNothing(), _("Press OK to reset module"), 0, slot))
			items.append((_("Init"), ConfigNothing(), _("Press OK to init module"), 1, slot))

		if self.state[slot] == 1:  # module in init
			items.append((_("init module"), ConfigNothing(), "", 2, slot))
		elif self.state[slot] == 2:  # module ready
			appname = eDVBCI_UI.getInstance().getAppName(slot)
			items.append((appname, ConfigNothing(), _("Press OK to open module info"), 2, slot))

		items.append(getConfigListEntry(_("Set pin code persistent"), config.ci[slot].use_static_pin))
		items.append((_("Enter persistent PIN code"), ConfigNothing(), _("Press OK to enter PIN code"), 5, slot))
		items.append((_("Reset persistent PIN code"), ConfigNothing(), _("Press OK to reset PIN code"), 6, slot))
		items.append(getConfigListEntry(_("Show CI messages"), config.ci[slot].show_ci_messages))
		items.append(getConfigListEntry(_("Disable operator profiles"), config.ci[slot].disable_operator_profile))
		items.append(getConfigListEntry(_("Descrambling options") + " *", config.ci[slot].alternative_ca_handling))
		items.append(getConfigListEntry(_("Multiple service support"), config.ci[slot].canDescrambleMultipleServices))
		if BoxInfo.getItem(f"CI{slot}SupportsHighBitrates"):
			items.append(getConfigListEntry(_("High bitrate support"), config.ci[slot].highBitrate))
		if BoxInfo.getItem(f"CI{slot}RelevantPidsRoutingSupport"):
			items.append(getConfigListEntry(_("Relevant PIDs Routing"), config.ci[slot].relevantPidsRouting))
		return items

	def dlgClosed(self, slot):
		self.dlg = None

	def keySelect(self):
		current = self["config"].getCurrent()
		if len(current) == 5:
			slot = current[4]
			action = current[3]
			if action == 0:  # reset
				eDVBCI_UI.getInstance().setReset(slot)
				authFile = f"/etc/ciplus/ci_auth_slot_{slot}.bin"
				if exists(authFile):
					remove(authFile)
			elif action == 1:  # init
				eDVBCI_UI.getInstance().setInit(slot)
			elif action == 5:
				self.session.openWithCallback(self.cancelCB, PermanentPinEntry, config.ci[slot].static_pin, _("Smartcard PIN"))
			elif action == 6:
				config.ci[slot].static_pin.value = 0
				config.ci[slot].static_pin.save()
				self.session.openWithCallback(self.cancelCB, MessageBox, _("The saved PIN was cleared."), MessageBox.TYPE_INFO)
			elif action == 2 and self.state[slot] == 2:
				self.dlg = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, action)
			if action in (0, 1, 2, 5, 6, 7):
				return
		Setup.keySelect(self)

	def cancelCB(self, value):
		pass

	def unregisterHandler(self):
		for slot in range(BoxInfo.getItem("CommonInterface")):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				CiHandler.unregisterCIMessageHandler(slot)

	def keySave(self):
		self.unregisterHandler()
		Setup.keySave(self)

	def keyCancel(self):
		self.unregisterHandler()
		self.close()


class PermanentPinEntry(ConfigListScreen, Screen):
	def __init__(self, session, pin, pin_slot):
		Screen.__init__(self, session)
		self.skinName = ["ParentalControlChangePin", "Setup"]
		self.onChangedEntry = []

		self.slot = pin_slot
		self.pin = pin
		self.list = []
		self.pin1 = ConfigPIN(default=0, censor="*")
		self.pin2 = ConfigPIN(default=0, censor="*")
		self.pin1.addEndNotifier(boundFunction(self.valueChanged, 1))
		self.pin2.addEndNotifier(boundFunction(self.valueChanged, 2))
		self.list.append(getConfigListEntry(_("Enter PIN"), NoSave(self.pin1)))
		self.list.append(getConfigListEntry(_("Reenter PIN"), NoSave(self.pin2)))
		ConfigListScreen.__init__(self, self.list, fullUI=True)

		self.setTitle(_("Enter pin code"))

	def valueChanged(self, pin, value):
		if pin == 1:
			self["config"].setCurrentIndex(1)
		elif pin == 2:
			self.keyOK()

	def keySave(self):
		if self.pin1.value == self.pin2.value:
			self.pin.value = self.pin1.value
			self.pin.save()
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code has been saved successfully."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("The PIN codes you entered are different."), MessageBox.TYPE_ERROR)

	def keyCancel(self):
		self.close(None)
