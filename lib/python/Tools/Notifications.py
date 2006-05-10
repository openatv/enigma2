
notifications = [ ]

notificationAdded = [ ]

def AddNotification(screen, *args, **kwargs):
	AddNotificationWithCallback(None, screen, *args, **kwargs)

def AddNotificationWithCallback(fnc, screen, *args, **kwargs):
	notifications.append((fnc, screen, args, kwargs))
	for x in notificationAdded:
		x()
