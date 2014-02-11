from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins

import os
from mimetypes import guess_type, add_type

add_type("application/x-debian-package", ".ipk")
add_type("application/ogg", ".ogg")
add_type("audio/x-flac", ".flac")
add_type("application/x-dream-package", ".dmpkg")
add_type("application/x-dream-image", ".nfi")
add_type("video/MP2T", ".ts")
add_type("video/x-dvd-iso", ".iso")
add_type("video/x-matroska", ".mkv")
add_type("audio/x-matroska", ".mka")
add_type("video/mpeg", ".mts")

def getType(file):
	(type, _) = guess_type(file)
	if type is None:
		# Detect some unknown types
		if file[-12:].lower() == "video_ts.ifo":
			return "video/x-dvd"

		p = file.rfind('.')
		if p == -1:
			return None
		ext = file[p+1:].lower()

		if ext == "dat" and file[-11:-6].lower() == "avseq":
			return "video/x-vcd"
	return type

class Scanner:
	def __init__(self, name, mimetypes=None, paths_to_scan=None, description="", openfnc=None):
		if not mimetypes: mimetypes = []
		if not paths_to_scan: paths_to_scan = []
		self.mimetypes = mimetypes
		self.name = name
		self.paths_to_scan = paths_to_scan
		self.description = description
		self.openfnc = openfnc

	def checkFile(self, file):
		return True

	def handleFile(self, res, file):
		if (self.mimetypes is None or file.mimetype in self.mimetypes) and self.checkFile(file):
			res.setdefault(self, []).append(file)

	def __repr__(self):
		return "<Scanner " + self.name + ">"

	def open(self, list, *args, **kwargs):
		if self.openfnc is not None:
			self.openfnc(list, *args, **kwargs)

class ScanPath:
	def __init__(self, path, with_subdirs = False):
		self.path = path
		self.with_subdirs = with_subdirs

	def __repr__(self):
		return self.path + "(" + str(self.with_subdirs) + ")"

	# we will use this in a set(), so we need to implement __hash__ and __cmp__
	def __hash__(self):
		return self.path.__hash__() ^ self.with_subdirs.__hash__()

	def __cmp__(self, other):
		if self.path < other.path:
			return -1
		elif self.path > other.path:
			return +1
		else:
			return self.with_subdirs.__cmp__(other.with_subdirs)

class ScanFile:
	def __init__(self, path, mimetype = None, size = None, autodetect = True):
		self.path = path
		if mimetype is None and autodetect:
			self.mimetype = getType(path)
		else:
			self.mimetype = mimetype
		self.size = size

	def __repr__(self):
		return "<ScanFile " + self.path + " (" + str(self.mimetype) + ", " + str(self.size) + " MB)>"

def execute(option):
	print "execute", option
	if option is None:
		return

	(_, scanner, files, session) = option
	scanner.open(files, session)

def scanDevice(mountpoint):
	scanner = [ ]

	for p in plugins.getPlugins(PluginDescriptor.WHERE_FILESCAN):
		l = p()
		if not isinstance(l, list):
			l = [l]
		scanner += l

	print "scanner:", scanner

	res = { }

	# merge all to-be-scanned paths, with priority to
	# with_subdirs.

	paths_to_scan = set()

	# first merge them all...
	for s in scanner:
		paths_to_scan.update(set(s.paths_to_scan))

	# ...then remove with_subdir=False when same path exists
	# with with_subdirs=True
	for p in paths_to_scan:
		if p.with_subdirs == True and ScanPath(path=p.path) in paths_to_scan:
			paths_to_scan.remove(ScanPath(path=p.path))

	# now scan the paths
	for p in paths_to_scan:
		path = os.path.join(mountpoint, p.path)

		for root, dirs, files in os.walk(path):
			for f in files:
				path = os.path.join(root, f)
				if f.endswith(".wav") and f.startswith("track"):
					sfile = ScanFile(path,"audio/x-cda")
				else:
					sfile = ScanFile(path)
				for s in scanner:
					s.handleFile(res, sfile)

			# if we really don't want to scan subdirs, stop here.
			if not p.with_subdirs:
				del dirs[:]

	# res is a dict with scanner -> [ScanFiles]
	return res

def openList(session, files):
	if not isinstance(files, list):
		files = [ files ]

	scanner = [ ]

	for p in plugins.getPlugins(PluginDescriptor.WHERE_FILESCAN):
		l = p()
		if not isinstance(l, list):
			scanner.append(l)
		else:
			scanner += l

	print "scanner:", scanner

	res = { }

	for file in files:
		for s in scanner:
			s.handleFile(res, file)

	choices = [ (r.description, r, res[r], session) for r in res ]
	Len = len(choices)
	if Len > 1:
		from Screens.ChoiceBox import ChoiceBox

		session.openWithCallback(
			execute,
			ChoiceBox,
			title = "The following viewers were found...",
			list = choices
		)
		return True
	elif Len:
		execute(choices[0])
		return True

	return False

def openFile(session, mimetype, file):
	return openList(session, [ScanFile(file, mimetype)])
