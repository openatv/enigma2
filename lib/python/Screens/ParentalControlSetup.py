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
			self.list.append(getConfigListEntry(_("Hide parentel locked services"), config.ParentalControl.hideBlacklist))
			self.reloadLists = getConfigListEntry(_("Reload blacklists"), NoSave(ConfigNothing()))
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
