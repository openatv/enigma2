from enigma import eTimer
from Screens.MessageBox import MessageBox

notifications = []

notificationAdded = []

# notifications which are currently on screen (and might be closed by similiar notifications)
current_notifications = []


def __AddNotification(fnc, screen, id, *args, **kwargs):
	if ".MessageBox'>" in repr(screen):
		kwargs["simple"] = True
	notifications.append((fnc, screen, args, kwargs, id))
	for x in notificationAdded:
		x()


def AddNotification(screen, *args, **kwargs):
	AddNotificationWithCallback(None, screen, *args, **kwargs)


def AddNotificationWithCallback(fnc, screen, *args, **kwargs):
	__AddNotification(fnc, screen, None, *args, **kwargs)


def AddNotificationParentalControl(fnc, screen, *args, **kwargs):
	RemovePopup("Parental control")
	__AddNotification(fnc, screen, "Parental control", *args, **kwargs)


def AddNotificationWithID(id, screen, *args, **kwargs):
	__AddNotification(None, screen, id, *args, **kwargs)


def AddNotificationWithIDCallback(fnc, id, screen, *args, **kwargs):
	__AddNotification(fnc, screen, id, *args, **kwargs)

# Entry to only have one pending item with an id.
# Only use this if you don't mind losing the callback for skipped calls.
#


def AddNotificationWithUniqueIDCallback(fnc, id, screen, *args, **kwargs):
	for x in notifications:
		if x[4] and x[4] == id:    # Already there...
			return
	__AddNotification(fnc, screen, id, *args, **kwargs)

# we don't support notifications with callback and ID as this
# would require manually calling the callback on cancelled popups.


def RemovePopup(id):
	# remove similiar notifications
	for x in notifications:
		if x[4] and x[4] == id:
			print("[Notifications] RemovePopup id = %s" % id)
			notifications.remove(x)

	for x in current_notifications:
		if x[0] == id:
			print("[Notifications] found in current notifications")
			x[1].close()


def AddPopup(text, type, timeout, id=None):
	if id is not None:
		RemovePopup(id)
	print("[Notifications] AddPopup id = %s" % id)
	AddNotificationWithID(id, MessageBox, text=text, type=type, timeout=timeout, close_on_any_key=True)


def AddPopupWithCallback(fnc, text, type, timeout, id=None):
	if id is not None:
		RemovePopup(id)
	print("[Notifications] AddPopupWithCallback id = %s" % id)
	AddNotificationWithIDCallback(fnc, id, MessageBox, text=text, type=type, timeout=timeout, close_on_any_key=False)


def showError(text, timeout=5):
	notificationCenter.session.showError(text, timeout)


def showInfo(text, timeout=5):
	notificationCenter.session.showInfo(text, timeout)


def showWarning(text, timeout=5):
	notificationCenter.session.showWarning(text, timeout)


def AddModalNotification(text, timeout=-1, list=None, default=True, typeIcon=None, windowTitle=None, callback=None):
	notificationCenter.addModalNotification(text, timeout, list, default, typeIcon, windowTitle, callback)


class NotificationCenter:

	def __init__(self):
		self.modalDialog = None
		self.modalQueue = []
		self.modalCallback = None
		self.nextModalTimer = None

	def setup(self, session):
		self.session = session
		self.modalDialog = session.instantiateDialog(MessageBox, "", enableInput=False, skinName="MessageBoxModal")
		self.modalDialog.setAnimationMode(0)
		self.modalDialog.hide()
		self.nextModalTimer = eTimer()
		self.nextModalTimer.callback.append(self.showNextModal)

	def addModalNotification(self, text, timeout=-1, list=None, default=True, typeIcon=None, windowTitle=None, callback=None):
		if not self.modalDialog:
			print("[NotificationCenter] addModalNotification: not yet set up, notification dropped.")
			return
		if typeIcon is None:
			typeIcon = MessageBox.TYPE_YESNO
		self.modalQueue.append((text, timeout, list, default, typeIcon, windowTitle, callback))
		if not self.modalDialog.shown and not (self.nextModalTimer and self.nextModalTimer.isActive()):
			self.showNextModal()

	def showNextModal(self):
		if not self.modalQueue or not self.modalDialog:
			return
		text, timeout, list_, default, typeIcon, windowTitle, callback = self.modalQueue.pop(0)
		self.modalCallback = callback
		dialog = self.modalDialog
		dialog.text = text
		dialog["text"].setText(text)
		dialog.typeIcon = typeIcon
		dialog.type = typeIcon
		dialog.picon = (typeIcon != MessageBox.TYPE_NOICON)
		if typeIcon == MessageBox.TYPE_YESNO:
			dialog.list = [(_("Yes"), True), (_("No"), False)] if list_ is None else list_
			dialog["list"].setList(dialog.list)
			dialog.startIndex = 0 if default else 1
			dialog["list"].show()
		else:
			dialog["list"].hide()
			dialog.list = None
		dialog.timeout = timeout
		dialog.msgBoxID = None
		dialog.enableInput = True
		dialog.createActionMap(-20)
		dialog["actions"].execBegin()
		dialog.closeOnAnyKey = False
		dialog.timeoutDefault = True if default else False
		dialog.windowTitle = windowTitle or _("Message")
		dialog.baseTitle = dialog.windowTitle
		dialog.activeTitle = dialog.windowTitle
		dialog.reloadLayout()
		dialog.close = self.onModalAnswer
		dialog.show()

	def onModalAnswer(self, *retval):
		dialog = self.modalDialog
		if dialog.enableInput:
			dialog["actions"].execEnd()
		dialog.hide()
		callback = self.modalCallback
		self.modalCallback = None
		if callback and callable(callback):
			callback(*retval)
		if self.modalQueue:
			self.nextModalTimer.start(500, True)


notificationCenter = NotificationCenter()
