from Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import NumberActionMap
from Components.config import config, getConfigListEntry, ConfigNothing, NoSave, ConfigPIN, configfile

from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import PinInput
from Screens.ChannelSelection import service_types_tv
from Tools.BoundFunction import boundFunction
from enigma import eServiceCenter, eTimer, eServiceReference
from operator import itemgetter

class ProtectedScreen:
	def __init__(self):
		if self.isProtected():
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList = self.getPinList(), triesEntry = self.getTriesEntry(), title = self.getPinText(), windowTitle = _("Enter pin code")))

	def getTriesEntry(self):
		return config.ParentalControl.retries.servicepin

	def getPinText(self):
		return _("Please enter the correct pin code")

	def isProtected(self):
		return config.ParentalControl.servicepinactive.value

	def getPinList(self):
		return [ x.value for x in config.ParentalControl.servicepin ]

	def pinEntered(self, result):
		if result is None:
			self.close()
		elif not result:
			self.session.openWithCallback(self.close, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)

class ParentalControlSetup(Screen, ConfigListScreen, ProtectedScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		ProtectedScreen.__init__(self)
		# for the skin: first try ParentalControlSetup, then Setup, this allows individual skinning
		self.skinName = ["ParentalControlSetup", "Setup" ]
		self.setup_title = _("Parental control setup")
		self.onChangedEntry = [ ]

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions"],
		{
		  "cancel": self.keyCancel,
		  "save": self.keySave,
		  "menu": self.closeRecursive,
		}, -2)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self.recursive = False
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def createSetup(self):
		self.changePin = None
		self.reloadLists = None
		self.list = []
		self.list.append(getConfigListEntry(_("Protect services"), config.ParentalControl.servicepinactive))
		if config.ParentalControl.servicepinactive.value:
			self.changePin = getConfigListEntry(_("Change service PIN"), NoSave(ConfigNothing()))
			self.list.append(self.changePin)
			self.list.append(getConfigListEntry(_("Remember service PIN"), config.ParentalControl.storeservicepin))
			self.list.append(getConfigListEntry(_("Protect on epg age"), config.ParentalControl.age))	
			self.reloadLists = getConfigListEntry(_("Reload black-/white lists"), NoSave(ConfigNothing()))
			self.list.append(self.reloadLists)

		self["config"].list = self.list
		self["config"].setList(self.list)

	def keyOK(self):
		if self["config"].l.getCurrentSelection() == self.changePin:
			self.session.open(ParentalControlChangePin, config.ParentalControl.servicepin[0], _("service PIN"))
		elif self["config"].l.getCurrentSelection() == self.reloadLists:
			from Components.ParentalControl import parentalControl
			parentalControl.open()
			self.session.open(MessageBox, _("Lists reloaded!"), MessageBox.TYPE_INFO, timeout=3)
		else:
			ConfigListScreen.keyRight(self)
			self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def ServicePinMessageCallback(self, value):
		if value:
			self.session.openWithCallback(self.cancelCB, ParentalControlChangePin, config.ParentalControl.servicepin[0], _("service PIN"))
		else:
			config.ParentalControl.servicepinactive.value = False
			self.keySave()

	def cancelCB(self, value):
		self.keySave()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def cancelConfirm(self, answer):
		if answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close()

	def keySave(self):
		if config.ParentalControl.servicepinactive.value and config.ParentalControl.servicepin[0].value == "aaaa":
			self.session.openWithCallback(self.ServicePinMessageCallback, MessageBox, _("No valid service PIN found!\nDo you like to change the service PIN now?\nWhen you say 'No' here the service protection stay disabled!"), MessageBox.TYPE_YESNO)
		else:
			for x in self["config"].list:
				x[1].save()
				configfile.save()
			self.close(self.recursive)

	def closeRecursive(self):
		self.recursive = True
		self.keySave()

	def keyNumberGlobal(self, number):
		pass

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

SPECIAL_CHAR = 96
class ParentalControlEditor(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.list = []
		self.servicelist = ParentalControlList(self.list)
		self["servicelist"] = self.servicelist;
		self.currentLetter = chr(SPECIAL_CHAR)
		self.readServiceList()
		self.chooseLetterTimer = eTimer()
		self.chooseLetterTimer.callback.append(self.chooseLetter)
		self.onLayoutFinish.append(self.LayoutFinished)

		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions", "NumberActions"],
		{
			"ok": self.select,
			"cancel": self.cancel,
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

	def LayoutFinished(self):
		self.chooseLetterTimer.start(0, True)

	def cancel(self):
		self.chooseLetter()

	def select(self):
		self.servicelist.toggleSelectedLock()

	def keyNumberGlobal(self, number):
		pass

	def readServiceList(self):
		serviceHandler = eServiceCenter.getInstance()
		refstr = '%s ORDER BY name' % (service_types_tv)
		self.root = eServiceReference(refstr)
		self.servicesList = {}
		list = serviceHandler.list(self.root)
		if list is not None:
			services = list.getContent("CN", True) #(servicecomparestring, name)
			for s in services:
				key = s[1].lower()[0]
				if key < 'a' or key > 'z':
					key = chr(SPECIAL_CHAR)
				#key = str(key)
				if not self.servicesList.has_key(key):
					self.servicesList[key] = []
				self.servicesList[key].append(s)

	def chooseLetter(self):
		mylist = []
		for x in self.servicesList.keys():
			if x == chr(SPECIAL_CHAR):
				x = (_("special characters"), x)
			else:
				x = (x, x)
			mylist.append(x)
		mylist.sort(key=itemgetter(1))
		sel = ord(self.currentLetter) - SPECIAL_CHAR
		self.session.openWithCallback(self.letterChosen, ChoiceBox, title=_("Show services beginning with"), list=mylist, keys = [], selection = sel)

	def letterChosen(self, result):
		from Components.ParentalControl import parentalControl
		if result is not None:
			self.currentLetter = result[1]
			#Replace getProtectionLevel by new getProtectionType
			self.list = [ParentalControlEntryComponent(x[0], x[1], parentalControl.getProtectionType(x[0])) for x in self.servicesList[result[1]]]
			self.servicelist.setList(self.list)
		else:
			parentalControl.save()
			self.close()

class ParentalControlBouquetEditor(Screen):
	#This new class allows adding complete bouquets to black- and whitelists
	#The servicereference that is stored for bouquets is their refstr as listed in bouquets.tv
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "ParentalControlEditor"
		self.list = []
		self.bouquetslist = ParentalControlList(self.list)
		self["servicelist"] = self.bouquetslist;
		self.readBouquetList()
		self.onLayoutFinish.append(self.selectBouquet)

		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions"],
		{
			"ok": self.select,
			"cancel": self.cancel
		}, -1)

	def cancel(self):
		from Components.ParentalControl import parentalControl
		parentalControl.save()
		self.close()

	def select(self):
		self.bouquetslist.toggleSelectedLock()

	def readBouquetList(self):
		serviceHandler = eServiceCenter.getInstance()
		refstr = '1:134:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet'
		bouquetroot = eServiceReference(refstr)
		self.bouquetlist = {}
		list = serviceHandler.list(bouquetroot)
		if list is not None:
			self.bouquetlist = list.getContent("CN", True)

	def selectBouquet(self):
		from Components.ParentalControl import parentalControl
		self.list = [ParentalControlEntryComponent(x[0], x[1], parentalControl.getProtectionType(x[0])) for x in self.bouquetlist]
		self.bouquetslist.setList(self.list)

class ParentalControlChangePin(Screen, ConfigListScreen, ProtectedScreen):
	def __init__(self, session, pin, pinname):
		Screen.__init__(self, session)
		# for the skin: first try ParentalControlChangePin, then Setup, this allows individual skinning
		self.skinName = ["ParentalControlChangePin", "Setup" ]
		self.setup_title = _("Change pin code")
		self.onChangedEntry = [ ]

		self.pin = pin
		self.list = []
		self.pin1 = ConfigPIN(default = 1111, censor = "*")
		self.pin2 = ConfigPIN(default = 1112, censor = "*")
		self.pin1.addEndNotifier(boundFunction(self.valueChanged, 1))
		self.pin2.addEndNotifier(boundFunction(self.valueChanged, 2))
		self.list.append(getConfigListEntry(_("New PIN"), NoSave(self.pin1)))
		self.list.append(getConfigListEntry(_("Reenter new PIN"), NoSave(self.pin2)))
		ConfigListScreen.__init__(self, self.list)
		ProtectedScreen.__init__(self)

		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions", "MenuActions"],
		{
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"save": self.keyOK,
			"menu": self.closeRecursive,
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

	def getPinText(self):
		return _("Please enter the old PIN code")

	def isProtected(self):
		return (self.pin.value != 'aaaa')

	def protectedWithPin(self):
		return self.pin.value

	def keyOK(self):
		if self.pin1.value == self.pin2.value:
			self.pin.value = self.pin1.value
			self.pin.save()
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code has been changed successfully."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("The PIN codes you entered are different."), MessageBox.TYPE_ERROR)

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
