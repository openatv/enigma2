import os

SCOPE_TRANSPONDERDATA = 0
SCOPE_SYSETC = 1
SCOPE_FONTS = 2
SCOPE_SKIN = 3
SCOPE_SKIN_IMAGE = 4
SCOPE_USERETC = 5
SCOPE_CONFIG = 6
SCOPE_LANGUAGE = 7

PATH_CREATE = 0
PATH_DONTCREATE = 1

defaultPaths = {
		SCOPE_TRANSPONDERDATA: ("/etc/", PATH_DONTCREATE),
		SCOPE_SYSETC: ("/etc/", PATH_DONTCREATE),
		SCOPE_FONTS: ("/usr/share/fonts/", PATH_DONTCREATE),
		SCOPE_CONFIG: ("/etc/enigma2/", PATH_CREATE),
					    
		SCOPE_LANGUAGE: ("/enigma2/po/", PATH_CREATE),

		SCOPE_SKIN: ("/usr/share/enigma2/", PATH_DONTCREATE),
		SCOPE_SKIN_IMAGE: ("/usr/share/enigma2/", PATH_DONTCREATE),
		
		SCOPE_USERETC: ("", PATH_DONTCREATE) # user home directory
	}

def resolveFilename(scope, base):
	# in future, we would check for file existence here,
	# so we can provide default/fallbacks.
	
	path = defaultPaths[scope]
	if path[1] == PATH_CREATE:
		if (not os.path.exists(path[0])):
			os.mkdir(path[0])
	
	# FIXME: we also have to handle DATADIR etc. here.
	return path[0] + base

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
			path += "_%03d" % i
		try:
			open(path + ".ts")
			i += 1
		except IOError:
			return path
