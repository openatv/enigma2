
keyBindings = { }

from keyids import KEYIDS

keyDescriptions = {
		KEYIDS["KEY_RED"]: "red",
		KEYIDS["KEY_BLUE"]: "blue",
		KEYIDS["KEY_GREEN"]: "green",
		KEYIDS["KEY_MENU"]: "menu",
		KEYIDS["KEY_LEFT"]: "left",
		KEYIDS["KEY_RIGHT"]: "right",
		KEYIDS["KEY_VIDEO"]: "video",
		KEYIDS["KEY_INFO"]: "info",
		KEYIDS["KEY_AUDIO"]: "audio",
		KEYIDS["KEY_RADIO"]: "radio"
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
