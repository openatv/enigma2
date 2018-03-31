from Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Console import Console
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_0, ConfigNothing, ConfigPIN, ConfigText, ConfigYesNo, NoSave
from Components.ConfigList import ConfigList
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from os import path as os_path, remove, unlink, rename, chmod, access, X_OK
from enigma import eTimer, eDVBCI_UI, eDVBCIInterfaces
from Tools.BoundFunction import boundFunction
from boxbranding import getBrandOEM, getBoxType
import time

MAX_NUM_CI = 4
relevantPidsRoutingChoices = None

def setCIBitrate(configElement):
	if configElement.value == "no":
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateNormal)
	else:
		eDVBCI_UI.getInstance().setClockRate(configElement.slotid, eDVBCI_UI.rateHigh)

def setdvbCiDelay(configElement):
	f = open("/proc/stb/tsmux/rmx_delay", "w")
	f.write(configElement.value)
	f.close()

def setRelevantPidsRouting(configElement):
	fileName = "/proc/stb/tsmux/ci%d_relevant_pids_routing" % (configElement.slotid)
	if fileExists(fileName, 'r'):
		f = open(fileName, "w")
		f.write(configElement.value)
		f.close()

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
			if getBrandOEM() in ('dags', 'blackbox'):
				config.ci[slot].canHandleHighBitrates = ConfigSelection(choices = [("no", _("No")), ("yes", _("Yes"))], default = "yes")
			else: 
				config.ci[slot].canHandleHighBitrates = ConfigSelection(choices = [("no", _("No")), ("yes", _("Yes"))], default = "no")
			config.ci[slot].canHandleHighBitrates.slotid = slot
			config.ci[slot].canHandleHighBitrates.addNotifier(setCIBitrate)
		if SystemInfo["RelevantPidsRoutingSupport"]:
			global relevantPidsRoutingChoices
			if not relevantPidsRoutingChoices:
				relevantPidsRoutingChoices = [("no", _("No")), ("yes", _("Yes"))]
				default = "no"
				fileName = "/proc/stb/tsmux/ci%d_relevant_pids_routing_choices"
			if fileExists(fileName, 'r'):
				relevantPidsRoutingChoices = []
				fd = open(fileName, 'r')
				data = fd.read()
				data = data.split()
				for x in data:
					relevantPidsRoutingChoices.append((x, _(x)))
				if default not in data:
					default = data[0]
			config.ci[slot].relevantPidsRouting = ConfigSelection(choices = relevantPidsRoutingChoices, default = default)
			config.ci[slot].relevantPidsRouting.slotid = slot
			config.ci[slot].relevantPidsRouting.addNotifier(setRelevantPidsRouting)
	if SystemInfo["CommonInterfaceCIDelay"]:
		config.cimisc.dvbCiDelay = ConfigSelection(default = "256", choices = [ ("16", _("16")), ("32", _("32")), ("64", _("64")), ("128", _("128")), ("256", _("256"))] )
		config.cimisc.dvbCiDelay.addNotifier(setdvbCiDelay)
	if getBrandOEM() in ('entwopia', 'tripledot', 'dreambox'):
		if SystemInfo["HaveCISSL"]:
			config.cimisc.civersion = ConfigSelection(default = "ciplus1", choices = [("auto", _("Auto")), ("ciplus1", _("CI Plus 1.2")), ("ciplus2", _("CI Plus 1.3")), ("legacy", _("CI Legacy"))])
		else:
			config.cimisc.civersion = ConfigSelection(default = "legacy", choices = [("legacy", _("CI Legacy"))])
	else:
		config.cimisc.civersion = ConfigSelection(default = "auto", choices = [("auto", _("Auto")), ("ciplus1", _("CI Plus 1.2")), ("ciplus2", _("CI Plus 1.3")), ("legacy", _("CI Legacy"))])

class CISetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Setup" ]
		self.setup_title = _("CI settings")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label()

		self.onChangedEntry = [ ]

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		from Components.ActionMap import ActionMap
		self["actions"] = ActionMap(["SetupActions", "MenuActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def createSetup(self):
		level = config.usage.setup_level.index

		self.list = [ ]

		if level >= 1:
			if SystemInfo["CommonInterfaceCIDelay"]:
				self.list.append(getConfigListEntry(_("DVB CI Delay"), config.cimisc.dvbCiDelay, _("Choose dvb wait delay for ci response.")))
			if SystemInfo["HaveCISSL"]:
				self.list.append(getConfigListEntry(_("CI Operation Mode"), config.cimisc.civersion, _("Choose the CI protocol operation mode for standard ci or ciplus.")))
			else:
				self.list.append(getConfigListEntry(_("CI Operation Mode"), config.cimisc.civersion, _("Your Hardware can detect ci mode self or work only in legacy mode.")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def confirm(self, confirmed):
		self.keySave()

	def apply(self):
		self.keySave()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

class MMIDialog(Screen):
	def __init__(self, session, slotid, action, handler = eDVBCI_UI.getInstance(), wait_text = "wait for ci...", screen_data = None ):
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
		self.wait_text = _(wait_text)
		self.screen_data = screen_data

		self.is_pin_list = -1

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
			self["subtitle"].setText(entry[2])
			list.append( getConfigListEntry("", x) )
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
				self.handler.answerMenu(self.slotid, cur[2])
			else:
				self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "LIST":
			print "answer LIST"
			self.handler.answerMenu(self.slotid, 0)
			self.showWait()
		elif self.tag == "ENQ":
			cur = self["entries"].getCurrent()
			answer = str(cur[1].value)
			length = len(answer)
			while length < cur[1].getLength():
				answer = '0'+answer
				length+=1
			self.answer = answer
			if config.ci[self.slotid].use_static_pin.value:
				self.session.openWithCallback(self.save_PIN_CB, MessageBox, _("Would you save the entered PIN %s persistent?") % self.answer, MessageBox.TYPE_YESNO)
			else:
				self.save_PIN_CB(False)

	def save_PIN_CB(self, ret = None):
		if ret:
			config.ci[self.slotid].static_pin.value = self.answer
			config.ci[self.slotid].static_pin.save()
		self.handler.answerEnq(self.slotid, self.answer)
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
		list = [ ]
		list.append( (self.wait_text, ConfigNothing()) )
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
							length+=1
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
		self.ci = { }
		self.dlgs = { }
		self.auto_close = False
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
		try:
			file = open("/proc/stb/tsmux/rmx_delay", "r")
			file.close()
			SystemInfo["CommonInterfaceCIDelay"] = True
		except:
			SystemInfo["CommonInterfaceCIDelay"] = False
		try:
			file = open("/proc/stb/tsmux/ci0_relevant_pids_routing", "r")
			file.close()
			SystemInfo["RelevantPidsRoutingSupport"] = True
		except:
			SystemInfo["RelevantPidsRoutingSupport"] = False

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
					if config.ci[slot].show_ci_messages.value and config.misc.firstrun.value == 0:
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
										length+=1
									handler.answerEnq(slot, answer)
									show_ui = False
									self.auto_close = True
							elif ci_tag == 'CLOSE' and self.auto_close:
								show_ui = False
								self.auto_close = False
					if show_ui:
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
		self.slots = []
		self.HighBitrateEntry = {}
		self.RelevantPidsRoutingEntry = {}
		self.entryData = []

		self.list = [ ]
		self["entries"] = ConfigList(self.list)
		self["entries"].list = self.list
		self["entries"].l.setList(self.list)
		self["text"] = Label(_("Slot %d")%(1))
		self.onLayoutFinish.append(self.initialUpdate)

	def initialUpdate(self):
		for slot in range(MAX_NUM_CI):
			state = eDVBCI_UI.getInstance().getState(slot)
			if state != -1:
				self.slots.append(slot)
				self.state[slot] = state
				self.createEntries(slot)
				CiHandler.registerCIMessageHandler(slot, self.ciStateChanged)

		self.updateEntries()

	def selectionChanged(self):
		entryData = self.entryData[self["entries"].getCurrentIndex()]
		self["text"].setText(_("Slot %d")%(entryData[1] + 1))

	def keyConfigEntry(self, key):
		current = self["entries"].getCurrent()
		try:
			self["entries"].handleKey(key)
			current[1].save()
		except:
			pass

	def keyLeft(self):
		self.keyConfigEntry(KEY_LEFT)

	def keyRight(self):
		self.keyConfigEntry(KEY_RIGHT)

	def createEntries(self, slot):
		if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
			self.HighBitrateEntry[slot] = getConfigListEntry(_("High bitrate support"), config.ci[slot].canHandleHighBitrates)
		if SystemInfo["RelevantPidsRoutingSupport"]:
			self.RelevantPidsRoutingEntry[slot] = getConfigListEntry(_("Relevant PIDs Routing"), config.ci[slot].relevantPidsRouting)

	def addToList(self, data, action, slotid):
		self.list.append(data)
		self.entryData.append((action, slotid))

	def updateEntries(self):
		self.list = []
		self.entryData = []
		for slot in self.slots:
			self.addToList((_("Reset"), ConfigNothing()), 0, slot)
			self.addToList((_("Init"), ConfigNothing()), 1, slot)

			if self.state[slot] == 0:                       #no module
				self.addToList((_("no module found"), ConfigNothing()), 2, slot)
			elif self.state[slot] == 1:             #module in init
				self.addToList((_("init module"), ConfigNothing()), 2, slot)
			elif self.state[slot] == 2:             #module ready
				#get appname
				appname = eDVBCI_UI.getInstance().getAppName(slot)
				self.addToList((appname, ConfigNothing()), 2, slot)

			self.addToList(getConfigListEntry(_("Set pin code persistent"), config.ci[slot].use_static_pin), -1, slot)
			self.addToList(( _("Enter persistent PIN code"), ConfigNothing()), 5, slot)
			self.addToList(( _("Reset persistent PIN code"), ConfigNothing()), 6, slot)
			self.addToList(getConfigListEntry(_("Show CI messages"), config.ci[slot].show_ci_messages), -1, slot)
			self.addToList(getConfigListEntry(_("Multiple service support"), config.ci[slot].canDescrambleMultipleServices), -1, slot)

			if SystemInfo["CommonInterfaceSupportsHighBitrates"]:
				self.addToList(self.HighBitrateEntry[slot], -1, slot)
			if SystemInfo["RelevantPidsRoutingSupport"]:
				self.addToList(self.RelevantPidsRoutingEntry[slot], -1, slot)

		self["entries"].list = self.list
		self["entries"].l.setList(self.list)
		if self.selectionChanged not in self["entries"].onSelectionChanged:
			self["entries"].onSelectionChanged.append(self.selectionChanged)

	def ciStateChanged(self, slot):
		if self.dlg:
			self.dlg.ciStateChanged()
		else:
			state = eDVBCI_UI.getInstance().getState(slot)
			if self.state[slot] != state:
				#print "something happens"
				self.state[slot] = state
				self.updateEntries()

	def dlgClosed(self, slot):
		self.dlg = None

	def okbuttonClick(self):
		cur = self["entries"].getCurrent()
		if cur:
			idx = self["entries"].getCurrentIndex()
			entryData = self.entryData[idx]
			action = entryData[0]
			slot = entryData[1]
			if action == 0:		#reset
				eDVBCI_UI.getInstance().setReset(slot)
			elif action == 1:		#init
				eDVBCI_UI.getInstance().setInit(slot)
			elif action == 5:
				self.session.openWithCallback(self.cancelCB, PermanentPinEntry, config.ci[slot].static_pin, _("Smartcard PIN"))
			elif action == 6:
				config.ci[slot].static_pin.value = 0
				config.ci[slot].static_pin.save()
				self.session.openWithCallback(self.cancelCB, MessageBox, _("The saved PIN was cleared."), MessageBox.TYPE_INFO)
			elif action == 2 and self.state[slot] == 2:
				self.dlg = self.session.openWithCallback(self.dlgClosed, MMIDialog, slot, action)

	def cancelCB(self,value):
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
		self.list.append(getConfigListEntry(_("Reenter PIN"), NoSave(self.pin2)))
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

	# for summary:
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

class CIHelper(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("CIHelper Setup"))
		self.skinName = "CIHelper"
		self.onChangedEntry = [ ]
		self['ci0'] = Label(_("CIHelper for SLOT CI0"))
		self['ci0active'] = Pixmap()
		self['ci0inactive'] = Pixmap()
		self['ci1'] = Label(_("CIHelper for SLOT CI1"))
		self['ci1active'] = Pixmap()
		self['ci1inactive'] = Pixmap()

		self['autostart'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['status'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label()
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label()
		self.Console = Console()
		self.my_cihelper_active = False
		self.my_cihelper_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'SetupActions'], {'ok': self.setupcihelper, 'back': self.close, 'menu': self.setupcihelper, 'green': self.CIHelperStartStop, 'yellow': self.CIHelperset})
		self.onLayoutFinish.append(self.updateService)

	def CIHelperStartStop(self):
		if not self.my_cihelper_run:
			self.Console.ePopen('/etc/init.d/cihelper.sh start', self.StartStopCallback)
		elif self.my_cihelper_run:
			self.Console.ePopen('/etc/init.d/cihelper.sh stop', self.StartStopCallback)

	def StartStopCallback(self, result = None, retval = None, extra_args = None):
		time.sleep(5)
		self.updateService()

	def CIHelperset(self):
		if fileExists('/etc/rcS.d/S50cihelper.sh') or fileExists('/etc/rc4.d/S50cihelper.sh'):
			self.Console.ePopen('update-rc.d -f cihelper.sh remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f -s cihelper.sh start 50 S .', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		cihelper_process = str(p.named('cihelper')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self.my_cihelper_active = False
		self.my_cihelper_run = False
		if fileExists('/etc/rcS.d/S50cihelper.sh') or fileExists('/etc/rc4.d/S50cihelper.sh'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_cihelper_active = True
			autostartstatus_summary = self['autostart'].text + ' ' + self['labactive'].text
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
			autostartstatus_summary = self['autostart'].text + ' ' + self['labdisabled'].text
		if cihelper_process:
			self.my_cihelper_run = True
		if self.my_cihelper_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary= self['status'].text + ' ' + self['labstop'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary= self['status'].text + ' ' + self['labstop'].text

		if fileExists('/etc/cihelper.conf'):
			f = open('/etc/cihelper.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('ENABLE_CI0='):
					if line[11:] == 'no':
						self['ci0active'].hide()
						self['ci0inactive'].show()
					else:
						self['ci0active'].show()
						self['ci0inactive'].hide()
				elif fileExists('/dev/ci1'):
					if line.startswith('ENABLE_CI1='):
						if line[11:] == 'no':
							self['ci1active'].hide()
							self['ci1inactive'].show()
						else:
							self['ci1active'].show()
							self['ci1inactive'].hide()
				else:
					self['ci1active'].hide()
					self['ci1inactive'].hide()
					self['ci1'].hide()
				f.close()
		title = _("CIHelper Setup")

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

	def setupcihelper(self):
		self.session.openWithCallback(self.updateService, CIHelperSetup)

class CIHelperSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("CIHelper Setup"))
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.selectionChanged)
		Screen.setTitle(self, _("CIHelper Setup"))
		self['key_red'] = Label(_("Save"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'red': self.saveCIHelper, 'back': self.close})
		self.updateList()
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(item[0])
			desc = str(item[1].value)
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, ret=None):
		self.list = []
		self.cihelper_ci0 = NoSave(ConfigYesNo(default='True'))
		if fileExists('/dev/ci1'):
			self.cihelper_ci1 = NoSave(ConfigYesNo(default='True'))
		else:
			self.cihelper_ci1 = ConfigNothing()

		if fileExists('/etc/cihelper.conf'):
			f = open('/etc/cihelper.conf', 'r')
			for line in f.readlines():
				line = line.strip()
				if line.startswith('ENABLE_CI0='):
					if line[11:] == 'no':
						self.cihelper_ci0.value = False
					else:
						self.cihelper_ci0.value = True
					cihelper_ci0x = getConfigListEntry(_("Enable CIHelper for SLOT CI0") + ":", self.cihelper_ci0)
					self.list.append(cihelper_ci0x)
				elif line.startswith('ENABLE_CI1='):
					if line[11:] == 'no':
						self.cihelper_ci1.value = False
					else:
						self.cihelper_ci1.value = True
					if fileExists('/dev/ci1'):
						cihelper_ci1x = getConfigListEntry(_("Enable CIHelper for SLOT CI1") + ":", self.cihelper_ci1)
						self.list.append(cihelper_ci1x)
			f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)

	def saveCIHelper(self):
		if fileExists('/etc/cihelper.conf'):
			inme = open('/etc/cihelper.conf', 'r')
			out = open('/etc/cihelper.conf.tmp', 'w')
			for line in inme.readlines():
				line = line.replace('\n', '')
				if line.startswith('ENABLE_CI0='):
					if not self.cihelper_ci0.value:
						line = 'ENABLE_CI0=no'
					else:
						line = 'ENABLE_CI0=yes'
				elif line.startswith('ENABLE_CI1='):
					if not self.cihelper_ci1.value:
						line = 'ENABLE_CI1=no'
					else:
						line = 'ENABLE_CI1=yes'
				out.write((line + '\n'))
			out.close()
			inme.close()
		else:
			open('/tmp/CIHelper.log', "a").write(_("Sorry CIHelper Config is Missing") + '\n')
			self.session.open(MessageBox, _("Sorry CIHelper Config is Missing"), MessageBox.TYPE_INFO)
			self.close()
		if fileExists('/etc/cihelper.conf.tmp'):
			rename('/etc/cihelper.conf.tmp', '/etc/cihelper.conf')
		self.myStop()

	def myStop(self):
		self.close()

