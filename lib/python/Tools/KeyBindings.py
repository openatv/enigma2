from keyids import KEYIDS
from Components.config import config
from Components.RcModel import rc_model

keyBindings = {}

keyDescriptions = [{  # id=0 - dmm0 remote directory, DM8000.
	# However, the dmm0 rcpositions.xml file should define
	# an <rc id=0 /> element, but it does not, it only has
	# an <rc id=2 /> element.
	#
	# The rcpositions.xml file defines <button/> elements,
	# but they do not appear to emit codes.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("YELLOW",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EDIT"]: ("EPGSETUP",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("FORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=1 - dmm0 remote directory, other than DM8000.
	# However, the dmm0 rcpositions.xml file should define
	# an <rc id=1 /> element, but it does not, it only has
	# an <rc id=2 /> element.
	#
	# The rcpositions.xml file defines <button/> elements,
	# but they do not appear to emit codes.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EDIT"]: ("EPGSETUP",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("BLUE", "SHIFT"),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("GREEN", "SHIFT"),
	KEYIDS["KEY_PAUSE"]: ("YELLOW", "SHIFT"),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RADIO", "SHIFT"),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("RED", "SHIFT"),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("TV", "SHIFT"),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=2 - Everything else.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_ARCHIVE"]: ("HISTORY",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_AUX"]: ("WIZTV",),
	KEYIDS["KEY_BACK"]: ("RECALL",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CALENDAR"]: ("AUTOTIMER",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_CONTEXT_MENU"]: ("CONTEXT",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EJECTCD"]: ("EJECTCD",),
	KEYIDS["KEY_END"]: ("END",),
	KEYIDS["KEY_ENTER"]: ("ENTER", "kbd"),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_F1"]: ("F1",),
	KEYIDS["KEY_F2"]: ("F2",),
	KEYIDS["KEY_F3"]: ("F3",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_FILE"]: ("LIST",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_HOME"]: ("HOME",),
	KEYIDS["KEY_HOMEPAGE"]: ("HOMEPAGE",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_LIST"]: ("PLAYLIST",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MODE"]: ("VKEY",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_OPTION"]: ("OPTION",),
	KEYIDS["KEY_PAGEDOWN"]: ("PAGEDOWN",),
	KEYIDS["KEY_PAGEUP"]: ("PAGEUP",),
	KEYIDS["KEY_PAUSE"]: ("PAUSE",),
	KEYIDS["KEY_PC"]: ("LAN",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_PVR"]: ("PVR",),
	KEYIDS["KEY_QUESTION"]: ("ABOUT",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SAT"]: ("SAT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SETUP"]: ("SETUP",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_SLOW"]: ("SLOW",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_SWITCHVIDEOMODE"]: ("VMODE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TIME"]: ("TIMESHIFT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("VIDEO",),
	# KEYIDS["KEY_VMODE"]: ("VMODE",),  # This value is deprecated use KEY_SWITCHVIDEOMODE instead.
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",),
	KEYIDS["KEY_ZOOM"]: ("ZOOM",),
	# Discrete power codes
	KEYIDS["KEY_POWER2"]: ("POWER2",),
	KEYIDS["KEY_SUSPEND"]: ("SUSPEND",),
	KEYIDS["KEY_WAKEUP"]: ("WAKEUP",)
}, {  # id=3 - XP1000.
	# The xp1000/rcpositions file defines PLAY and PAUSE
	# at the same location where it should just define
	# PLAYPAUSE there. It has similar overlayed incorrect
	# definitions for play & pause rather than play/pause
	# in remote.html.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PORTAL",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_SWITCHVIDEOMODE"]: ("VMODE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	# KEYIDS["KEY_VMODE"]: ("VMODE",),  # This value is deprecated use KEY_SWITCHVIDEOMODE instead.
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=4 - Formuler F1/F3.
	# The formuler1 rcpositions file seems to define
	# the FF and REW keys as FASTFORWARD and KEY_REWIND,
	# but the remote.xml file issues KEY_PREVIOUSSONG
	# and KEY_NEXTSONG.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BACK"]: ("RECALL",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLAYLIST",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_CONTEXT_MENU"]: ("CONTEXT",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_F1"]: ("F1",),
	KEYIDS["KEY_F2"]: ("F2",),
	KEYIDS["KEY_F3"]: ("F3",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAVORITES",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PAUSE"]: ("PAUSE",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}]

def addKeyBinding(domain, key, context, action, flags):
	keyBindings.setdefault((context, action), []).append((key, domain, flags))

def removeKeyBinding(key, context, action, wild=True):
	if wild and action == "*":
		for ctx, action in keyBindings.keys():
			if ctx == context:
				removeKeyBinding(key, context, action, False)
		return
	contextAction = (context, action)
	if contextAction in keyBindings:
		bind = [x for x in keyBindings[contextAction] if x[0] != key]
		if bind:
			keyBindings[contextAction] = bind
		else:
			del keyBindings[contextAction]

# Returns a list of (key, flags) for a specified action.
#
def queryKeyBinding(context, action):
	if (context, action) in keyBindings:
		return [(x[0], x[2]) for x in keyBindings[(context, action)]]
	else:
		return []

def getKeyDescription(key):
	if rc_model.rcIsDefault():
		idx = config.misc.rcused.value
	else:
		rcType = config.plugins.remotecontroltype.rctype.value
		# rcType = config.misc.inputdevices.rcType.value
		if rcType == 14:  # XP1000
			idx = 3
		elif rcType == 18:  # F1
			idx = 4
		else:
			idx = 2
	return keyDescriptions[idx].get(key)

def getKeyBindingKeys(filterfn=lambda key: True):
	return filter(filterfn, keyBindings)

# Remove all entries of domain "domain".
#
def removeKeyBindings(domain):
	for x in keyBindings:
		keyBindings[x] = filter(lambda e: e[1] != domain, keyBindings[x])
