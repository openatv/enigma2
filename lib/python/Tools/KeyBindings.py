
keyBindings = { }

from keyids import KEYIDS

keyDescriptions = {
		KEYIDS["BTN_0"]: ("fp_up", 630, 320),
		KEYIDS["BTN_1"]: ("fp_down", 565, 320),
		KEYIDS["KEY_OK"]: ("ok", 598, 320),
		KEYIDS["KEY_UP"]: ("up", 598, 290),
		KEYIDS["KEY_DOWN"]: ("down", 598, 345),
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
		KEYIDS["KEY_TEXT"]: ("text", 610, 425),
		KEYIDS["KEY_NEXT"]: ("next", 635, 203),
		KEYIDS["KEY_PREVIOUS"]: ("prev", 559, 203),
		KEYIDS["KEY_PREVIOUSSONG"]: ("sh_blue", 640, 390),
		KEYIDS["KEY_PLAYPAUSE"]: ("sh_yellow", 610, 390),
		KEYIDS["KEY_PLAY"]: ("sh_green", 585, 390),
		KEYIDS["KEY_NEXTSONG"]: ("sh_red", 555, 390),
		KEYIDS["KEY_CHANNELUP"]: ("ch_up", 645, 245),
		KEYIDS["KEY_CHANNELDOWN"]: ("ch_down", 630, 270),
		KEYIDS["KEY_0"]: ("0", 598, 203),
		KEYIDS["KEY_1"]: ("1", 559, 134),
		KEYIDS["KEY_3"]: ("3", 635, 134),
		KEYIDS["KEY_8"]: ("8", 598, 180),
		KEYIDS["KEY_EXIT"]: ("exit", 598, 255),
		KEYIDS["KEY_STOP"]: ("sh_tv", 560, 425),
		KEYIDS["KEY_RECORD"]: ("sh_radio", 585, 425)
	}

def addKeyBinding(domain, key, context, action, flags):
	keyBindings.setdefault((context, action), []).append((key, domain, flags))

# returns a list of (key, flags) for a specified action
def queryKeyBinding(context, action):
	if (context, action) in keyBindings:
		return [(x[0], x[2]) for x in keyBindings[(context, action)]]
	else:
		return [ ]

def getKeyDescription(key):
	if key in keyDescriptions:
		return keyDescriptions.get(key, [ ])

def removeKeyBindings(domain):
	# remove all entries of domain 'domain'
	for x in keyBindings:
		keyBindings[x] = filter(lambda e: e[1] != domain, keyBindings[x])
