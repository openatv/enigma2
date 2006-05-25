
keyBindings = { }

from keyids import KEYIDS

keyDescriptions = {
		KEYIDS["BTN_0"]: ("fp_up", 630, 320),
		KEYIDS["BTN_1"]: ("fp_down", 565, 320),
		KEYIDS["KEY_UP"]: ("up", 630, 320),
		KEYIDS["KEY_DOWN"]: ("down", 565, 320),
		KEYIDS["KEY_POWER"]: ("power", 615, 80),
		KEYIDS["KEY_RED"]: ("red", 555, 390),
		KEYIDS["KEY_BLUE"]: ("blue", 640, 390),
		KEYIDS["KEY_GREEN"]: ("green", 585, 390),
		KEYIDS["KEY_YELLOW"]: ("yellow", 610, 390),
		KEYIDS["KEY_MENU"]: ("menu", 645, 290),
		KEYIDS["KEY_LEFT"]: ("left", 565, 320),
		KEYIDS["KEY_RIGHT"]: ("right", 630, 320),
		KEYIDS["KEY_VIDEO"]: ("video", 645, 355),
		KEYIDS["KEY_INFO"]: ("info", 550, 290),
		KEYIDS["KEY_AUDIO"]: ("audio", 555, 355),
		KEYIDS["KEY_TV"]: ("tv", 560, 425),
		KEYIDS["KEY_RADIO"]: ("radio", 585, 425),
		KEYIDS["KEY_NEXT"]: ("next", 635, 203),
		KEYIDS["KEY_PREVIOUS"]: ("prev", 559, 203)
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
		return keyDescriptions.get(key, [ ])
