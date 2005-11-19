
keyBindings = { }

from keyids import KEYIDS

keyDescriptions = {
		KEYIDS["KEY_RED"]: "red",
		KEYIDS["KEY_BLUE"]: "blue",
		KEYIDS["KEY_MENU"]: "menu",
		KEYIDS["KEY_VIDEO"]: "video"
	}

def addKeyBinding(key, context, action):
	if (context, action) in keyBindings:
		keyBindings[(context, action)].append(key)
	else:
		keyBindings[(context, action)] = [key]

def queryKeyBinding(context, action):
	if (context, action) in keyBindings:
		return keyBindings[(context, action)]
	else:
		return [ ]

def getKeyDescription(key):
	if key in keyDescriptions:
		return keyDescriptions[key]
	return "key_%0x" % key
