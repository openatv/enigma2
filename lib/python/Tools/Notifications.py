
notifications = [ ]

notificationAdded = [ ]

# notifications which are currently on screen (and might be closed by similiar notifications)
current_notifications = [ ]

def __AddNotification(fnc, screen, id, *args, **kwargs):
	if ".MessageBox'>" in `screen`:
		kwargs["simple"] = True
	notifications.append((fnc, screen, args, kwargs, id))
	for x in notificationAdded:
		x()

def AddNotification(screen, *args, **kwargs):
	AddNotificationWithCallback(None, screen, *args, **kwargs)

def AddNotificationWithCallback(fnc, screen, *args, **kwargs):
	__AddNotification(fnc, screen, None, *args, **kwargs)

def AddNotificationWithID(id, screen, *args, **kwargs):
	__AddNotification(None, screen, id, *args, **kwargs)

# we don't support notifications with callback and ID as this
# would require manually calling the callback on cancelled popups.

def RemovePopup(id):
	# remove similiar notifications
	print "RemovePopup, id =", id
	for x in notifications:
		if x[4] and x[4] == id:
			print "(found in notifications)"
			notifications.remove(x)

	for x in current_notifications:
		if x[0] == id:
			print "(found in current notifications)"
			x[1].close()

from Screens.MessageBox import MessageBox

def AddPopup(text, type, timeout, id = None):
	if id is not None:
		RemovePopup(id)
	print "AddPopup, id =", id
	AddNotificationWithID(id, MessageBox, text = text, type = type, timeout = timeout, close_on_any_key = True)
