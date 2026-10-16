from Components.config import ConfigPIN, ConfigSelection, NoSave, config, configfile
from Screens.MessageBox import MessageBox
from Screens.ScreenProtection import ProtectedScreen, runWithScreenProtection, runWithScreenProtectionScopes, screenProtectionInherited, screenProtectionSections  # noqa F401 - Keep the existing plugin imports working.
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction


class ParentalControlSetup(Setup):
	protectionSections = None  # Always require the PIN when either kind of protection is enabled.

	def __init__(self, session):
		self.changePin = NoSave(ConfigSelection(choices=[("", _("Press OK"))]))
		self.reloadLists = NoSave(ConfigSelection(choices=[("", _("Press OK"))]))
		self._configElements = []
		Setup.__init__(self, session, "ParentalControlSetup")
		self.onClose.append(self._cancelUnsavedSettings)

	def isProtected(self):
		return config.ParentalControl.servicepinactive.value or config.ParentalControl.setuppinactive.value

	def createSetup(self, appendItems=None, prependItems=None):
		Setup.createSetup(self, appendItems=appendItems, prependItems=prependItems)
		# Remember entries that may be hidden later by disabling a protection group.
		for item in self.list:
			if len(item) > 1 and item[1] not in self._configElements:
				self._configElements.append(item[1])

	def keySelect(self):
		currentItem = self.getCurrentItem()
		if currentItem is self.changePin:
			self.session.open(ParentalControlChangePin, config.ParentalControl.servicepin[0], _("service PIN"))
		elif currentItem is self.reloadLists:
			from Components.ParentalControl import parentalControl
			parentalControl.open()
			self.session.open(MessageBox, _("Lists reloaded!"), MessageBox.TYPE_INFO, timeout=3)
		else:
			Setup.keySelect(self)

	def changedEntry(self):
		Setup.changedEntry(self)
		for callback in self.onChangedEntry:
			callback()

	def saveAll(self):
		from Components.ParentalControl import parentalControl
		visibleItems = [x[1] for x in self["config"].list if len(x) > 1]
		for element in self._configElements:
			if element not in visibleItems:
				element.save()
		result = Setup.saveAll(self)
		parentalControl.hideBlacklist()
		return result

	def closeConfigList(self, closeParameters=()):
		if any(x.isChanged() for x in self._configElements):
			self.closeParameters = closeParameters
			self.session.openWithCallback(self.cancelConfirm, MessageBox, self.cancelMsg, default=False, type=MessageBox.TYPE_YESNO)
		else:
			self.close(*closeParameters)

	def _cancelUnsavedSettings(self):
		for element in self._configElements:
			if element.isChanged():
				element.cancel()

	def cancelCB(self, value):  # Retained for callers of the former ConfigList screen.
		self.keySave()

	def keyNumberGlobal(self, number):
		pass


class ParentalControlChangePin(Setup):
	protectionSections = None

	def __init__(self, session, pin, pinname):
		self.pin = pin
		self.pin1 = NoSave(ConfigPIN(default=1111, censor="*"))
		self.pin2 = NoSave(ConfigPIN(default=1112, censor="*"))
		self.pin1.addEndNotifier(boundFunction(self.valueChanged, 1))
		self.pin2.addEndNotifier(boundFunction(self.valueChanged, 2))
		Setup.__init__(self, session, "ParentalControlChangePin")

	def valueChanged(self, pin, value):
		if pin == 1:
			self["config"].setCurrentIndex(1)
		elif pin == 2:
			self.keyOK()

	def getPinText(self):
		return _("Please enter the old PIN code")

	def isProtected(self):
		return self.pin.value != "aaaa"

	def protectedWithPin(self):
		return self.pin.value

	def changedEntry(self):
		Setup.changedEntry(self)
		for callback in self.onChangedEntry:
			callback()

	def keySelect(self):
		self.keyOK()

	def keySave(self):
		self.keyOK()

	def keyOK(self):
		if self.pin1.value == self.pin2.value:
			self.pin.value = self.pin1.value
			self.pin.save()
			configfile.save()
			self.session.openWithCallback(self.close, MessageBox, _("The PIN code has been changed successfully."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("The PIN codes you entered are different."), MessageBox.TYPE_ERROR)
