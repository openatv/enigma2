# -*- coding: utf-8 -*-
import os

SCOPE_TRANSPONDERDATA = 0
SCOPE_SYSETC = 1
SCOPE_FONTS = 2
SCOPE_SKIN = 3
SCOPE_SKIN_IMAGE = 4
SCOPE_USERETC = 5
SCOPE_CONFIG = 6
SCOPE_LANGUAGE = 7
SCOPE_HDD = 8
SCOPE_PLUGINS = 9
SCOPE_MEDIA = 10

PATH_CREATE = 0
PATH_DONTCREATE = 1
PATH_FALLBACK = 2
defaultPaths = {
		SCOPE_TRANSPONDERDATA: ("/etc/", PATH_DONTCREATE),
		SCOPE_SYSETC: ("/etc/", PATH_DONTCREATE),
		SCOPE_FONTS: ("/usr/share/fonts/", PATH_DONTCREATE),
		SCOPE_CONFIG: ("/etc/enigma2/", PATH_CREATE),
		SCOPE_PLUGINS: ("/usr/lib/enigma2/python/Plugins/", PATH_CREATE),
					    
		SCOPE_LANGUAGE: ("/usr/share/enigma2/po/", PATH_CREATE),

		SCOPE_SKIN: ("/usr/share/enigma2/", PATH_DONTCREATE),
		SCOPE_SKIN_IMAGE: ("/usr/share/enigma2/", PATH_DONTCREATE),
		SCOPE_HDD: ("/hdd/movie/", PATH_DONTCREATE),
		SCOPE_MEDIA: ("/media/", PATH_DONTCREATE),
		
		SCOPE_USERETC: ("", PATH_DONTCREATE) # user home directory
	}
	
FILE_COPY = 0 # copy files from fallback dir to the basedir
FILE_MOVE = 1 # move files
PATH_COPY = 2 # copy the complete fallback dir to the basedir
PATH_MOVE = 3 # move the fallback dir to the basedir (can be used for changes in paths)
fallbackPaths = {
		SCOPE_CONFIG: [("/home/root/", FILE_MOVE),
					   ("/usr/share/enigma2/defaults/", FILE_COPY)],
		SCOPE_HDD: [("/hdd/movies", PATH_MOVE)]
	}

def resolveFilename(scope, base = "", path_prefix = None):
	if base[0:2] == "~/":
		# you can only use the ~/ if we have a prefix directory
		assert path_prefix is not None
		base = os.path.join(path_prefix, base[2:])

	# don't resolve absolute paths
	if base[0:1] == '/':
		return base

	path = defaultPaths[scope]

	if path[1] == PATH_CREATE:
		if (not pathExists(defaultPaths[scope][0])):
			os.mkdir(path[0])
			
	#if len(base) > 0 and base[0] == '/':
		#path = ("", None)
	
	if not fileExists(path[0] + base):
		#try:
		if fallbackPaths.has_key(scope):
			for x in fallbackPaths[scope]:
				if x[1] == FILE_COPY:
					if fileExists(x[0] + base):
						os.system("cp " + x[0] + base + " " + path[0] + base)
						break
				elif x[1] == FILE_MOVE:
					if fileExists(x[0] + base):
						os.system("mv " + x[0] + base + " " + path[0] + base)
						break
				elif x[1] == PATH_COPY:
					if pathExists(x[0]):
						if not pathExists(defaultPaths[scope][0]):
							os.mkdir(path[0])
						os.system("cp -a " + x[0] + "* " + path[0])
						break
				elif x[1] == PATH_MOVE:
					if pathExists(x[0]):
						os.system("mv " + x[0] + " " + path[0])
						break

	
	# FIXME: we also have to handle DATADIR etc. here.
	return path[0] + base

	# this is only the BASE - an extension must be added later.
	
def pathExists(path):
	return os.path.exists(path)

def fileExists(f):
	try:
		file = open(f)
	except IOError:
		exists = 0
	else:
		exists = 1
	return exists

def getRecordingFilename(basename):
		# filter out non-allowed characters
	non_allowed_characters = "/.\\:*?<>|\""
	filename = ""
	
	basename = basename.replace('\xc2\x86', '').replace('\xc2\x87', '')
	
	for c in basename:
		if c in non_allowed_characters:
			c = "_"
		filename += c
	
	i = 0
	while True:
		path = resolveFilename(SCOPE_HDD, filename)
		if i > 0:
			path += "_%03d" % i
		try:
			open(path + ".ts")
			i += 1
		except IOError:
			return path

# this is clearly a hack:
def InitFallbackFiles():
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.tv")
	resolveFilename(SCOPE_CONFIG, "bouquets.tv")
