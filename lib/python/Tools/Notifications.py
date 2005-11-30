
notifications = [ ]

notificationAdded = [ ]

def AddNotification(screen, *args):
	AddNotificationWithCallback(None, screen, *args)

def AddNotificationWithCallback(fnc, screen, *args):
	notifications.append((fnc, screen) + args)
	for x in notificationAdded:
		x()

