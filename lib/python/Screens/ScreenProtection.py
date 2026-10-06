from types import MethodType
from Components.config import config
from Screens.InputBox import PinInput
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction


def screenProtectionSections(sections):
	if not config.ParentalControl.setuppinactive.value:
		return set()
	return {section for section in ("main_menu", *sections) if getattr(config.ParentalControl.config_sections, section).value}


def screenProtectionInherited(session, sections):
	# Only reuse authorization inside the current dialog tree, never the service PIN cache.
	scopes = set(getattr(session, "screenProtectionScopes", ()))
	for dialog, shown in session.dialog_stack:
		scopes.update(getattr(dialog, "screenProtectionScopes", ()))
	if session.current_dialog is not None:
		scopes.update(getattr(session.current_dialog, "screenProtectionScopes", ()))
	return bool(sections.intersection(scopes))


def runWithScreenProtectionScopes(session, sections, callback):
	previous = getattr(session, "screenProtectionScopes", ())
	session.screenProtectionScopes = sections
	try:
		return callback()
	finally:
		session.screenProtectionScopes = previous


def runWithScreenProtection(session, sections, callback):
	sections = screenProtectionSections(sections)
	if not sections or screenProtectionInherited(session, sections):
		return callback()

	def pinEntered(result):
		if result:
			runWithScreenProtectionScopes(session, sections, callback)
		elif result is False:
			session.open(MessageBox, _("The PIN code entered is incorrect!"), MessageBox.TYPE_ERROR)

	return session.openWithCallback(pinEntered, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct pin code"), windowTitle=_("Enter pin code"))


class ProtectedScreen:
	protectionSections = None

	def __init__(self):
		if hasattr(self, "screenProtectionReady"):
			return
		self.screenProtectionScopes = set()
		self.screenProtectionCallbacks = []
		self.screenProtectionDenied = False
		sections = screenProtectionSections(self.protectionSections) if self.protectionSections is not None else set()
		self.screenProtectionReady = not self.isProtected() or bool(sections and screenProtectionInherited(self.session, sections))
		if self.screenProtectionReady:
			self.screenProtectionScopes = sections
		else:
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct pin code"), windowTitle=_("Enter pin code")))

	def isProtected(self):
		if self.protectionSections is not None:
			return bool(screenProtectionSections(self.protectionSections))
		return (config.ParentalControl.servicepinactive.value or config.ParentalControl.setuppinactive.value)

	def protectedCallback(self, callback):
		# Constructors/layout callbacks may run before the PIN dialog is displayed.
		def runCallback(screen):
			if screen.screenProtectionReady:
				callback()
			elif not screen.screenProtectionDenied and callback not in screen.screenProtectionCallbacks:
				screen.screenProtectionCallbacks.append(callback)
		# Screen.createGUIScreen distinguishes bound methods from skin applet strings.
		return MethodType(runCallback, self)

	def pinEntered(self, result):
		if result:
			self.screenProtectionReady = True
			if self.protectionSections is not None:
				self.screenProtectionScopes = screenProtectionSections(self.protectionSections)
			callbacks, self.screenProtectionCallbacks = self.screenProtectionCallbacks, []
			for callback in callbacks:
				callback()
		else:
			self.screenProtectionDenied = True
			self.screenProtectionCallbacks = []
			if result is None:
				self.closeProtectedScreen()
			else:
				self.session.openWithCallback(self.closeProtectedScreen, MessageBox, _("The PIN code entered is incorrect!"), MessageBox.TYPE_ERROR)

	def closeProtectedScreen(self, result=None):
		self.close(None)
