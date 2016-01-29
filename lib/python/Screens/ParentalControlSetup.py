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
		if self.isProtected() and config.ParentalControl.servicepin[0].value:
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct pin code"), windowTitle=_("Enter pin code")))

	def isProtected(self):
		return (config.ParentalControl.servicepinactive.value or config.ParentalControl.setuppinactive.value)

	def pinEntered(self, result):
		if result is None:
			self.closeProtectedScreen()
		elif not result:
			self.session.openWithCallback(self.closeProtectedScreen, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR, timeout=3)

	def closeProtectedScreen(self, result=None):
		self.close(None)

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
		self.createSetup(initial=True)

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

	def isProtected(self):
		return (not config.ParentalControl.setuppinactive.value and config.ParentalControl.servicepinactive.value) or\
			(not config.ParentalControl.setuppinactive.value and config.ParentalControl.config_sections.configuration.value) or\
			(not config.ParentalControl.config_sections.configuration.value and config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value)

	def createSetup(self, initial=False):
		self.reloadLists = None
		self.list = []
		if config.ParentalControl.servicepin[0].value or config.ParentalControl.servicepinactive.value or config.ParentalControl.setuppinactive.value or not initial:
			self.changePin = getConfigListEntry(_("Change PIN"), NoSave(ConfigNothing()))
			self.list.append(self.changePin)
			self.list.append(getConfigListEntry(_("Protect services"), config.ParentalControl.servicepinactive))
			if config.ParentalControl.servicepinactive.value:
				self.list.append(getConfigListEntry(_("Remember service PIN"), config.ParentalControl.storeservicepin))
				if config.ParentalControl.storeservicepin.value != "never":
					self.list.append(getConfigListEntry(_("Hide parentel locked services"), config.ParentalControl.hideBlacklist))
				self.list.append(getConfigListEntry(_("Protect on epg age"), config.ParentalControl.age))
				self.reloadLists = getConfigListEntry(_("Reload blacklists"), NoSave(ConfigNothing()))
				self.list.append(self.reloadLists)
			self.list.append(getConfigListEntry(_("Protect Screens"), config.ParentalControl.setuppinactive))
			if config.ParentalControl.setuppinactive.value:
				self.list.append(getConfigListEntry(_("Protect main menu"), config.ParentalControl.config_sections.main_menu))
				self.list.append(getConfigListEntry(_("Protect timer menu"), config.ParentalControl.config_sections.timer_menu))
				self.list.append(getConfigListEntry(_("Protect plugin browser"), config.ParentalControl.config_sections.plugin_browser))
				self.list.append(getConfigListEntry(_("Protect configuration"), config.ParentalControl.config_sections.configuration))
				self.list.append(getConfigListEntry(_("Protect standby menu"), config.ParentalControl.config_sections.standby_menu))
				self.list.append(getConfigListEntry(_("Protect software update screen"), config.ParentalControl.config_sections.software_update))
				self.list.append(getConfigListEntry(_("Protect manufacturer reset screen"), config.ParentalControl.config_sections.manufacturer_reset))
				self.list.append(getConfigListEntry(_("Protect movie list"), config.ParentalControl.config_sections.movie_list))
				self.list.append(getConfigListEntry(_("Protect context menus"), config.ParentalControl.config_sections.context_menus))
		else:
			self.changePin = getConfigListEntry(_("Enable parental protection"), NoSave(ConfigNothing()))
			self.list.append(self.changePin)
		self["config"].list = self.list
		self["config"].setList(self.list)

	def keyOK(self):
		if self["config"].l.getCurrentSelection() == self.changePin:
			if config.ParentalControl.servicepin[0].value:
				self.session.openWithCallback(self.oldPinEntered, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the old PIN code"), windowTitle=_("Enter pin code"))
			else:
				self.oldPinEntered(True)
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
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].save()
			configfile.save()
			from Components.ParentalControl import parentalControl
			parentalControl.hideBlacklist()
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

	def oldPinEntered(self, answer):
		if answer:
			self.session.openWithCallback(self.newPinEntered, PinInput, title=_("Please enter the new PIN code"), windowTitle=_("Enter pin code"))
		elif answer == False:
			self.session.open(MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR, timeout=3)

	def newPinEntered(self, answer):
		if answer is not None:
			self.session.openWithCallback(boundFunction(self.confirmNewPinEntered, answer), PinInput, title=_("Please re-enter the new PIN code"), windowTitle=_("Enter pin code"))

	def confirmNewPinEntered(self, answer1, answer2):
		if answer2 is not None:
			if answer1 == answer2:
				self.session.open(MessageBox, _("The PIN code has been changed successfully."), MessageBox.TYPE_INFO, timeout=3)
				config.ParentalControl.servicepin[0].value = answer1
				config.ParentalControl.servicepin[0].save()
				self.createSetup()
			else:
				self.session.open(MessageBox, _("The PIN codes you entered are different."), MessageBox.TYPE_ERROR, timeout=3)
