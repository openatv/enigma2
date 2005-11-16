import os

SCOPE_TRANSPONDERDATA = 0
SCOPE_SYSETC = 1
SCOPE_FONTS = 2
SCOPE_SKIN = 3
SCOPE_SKIN_IMAGE = 4
SCOPE_USERETC = 5

defaultPaths = {
		SCOPE_TRANSPONDERDATA: "/etc/",
		SCOPE_SYSETC: "/etc/",
		SCOPE_FONTS: "/usr/share/fonts/",

		SCOPE_SKIN: "/usr/share/tuxbox/enigma2/",
		SCOPE_SKIN_IMAGE: "/usr/share/tuxbox/enigma2/",
		
		SCOPE_USERETC: "" # user home directory
	}

def resolveFilename(scope, base):
	# in future, we would check for file existence here,
	# so we can provide default/fallbacks.
	
	# FIXME: we also have to handle DATADIR etc. here.
	return defaultPaths[scope] + base

	# this is only the BASE - an extension must be added later.
def getRecordingFilename(basename):
	
		# filter out non-allowed characters
	non_allowed_characters = "/.\\"
	
	filename = ""
	for c in basename:
		if c in non_allowed_characters:
			c = "_"
		filename += c
	
	i = 0
	while True:
		path = "/hdd/movies/" + filename
		if i > 0:
			path += str(i)
		try:
			open(path + ".ts")
			i += 1
		except IOError:
			return path
