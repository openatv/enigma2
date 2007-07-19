from Plugins.Plugin import PluginDescriptor
from os import path as os_path, walk as os_walk
from string import lower

def getExtension(file):
	p = file.rfind('.')
	if p == -1:
		ext = ""
	else:
		ext = file[p+1:]

	return lower(ext)

class Scanner:
	def __init__(self, name, extensions = [], paths_to_scan = [], description = "", openfnc = None):
		self.extensions = extensions
		self.name = name
		self.paths_to_scan = paths_to_scan
		self.description = description
		self.openfnc = openfnc

	def checkFile(self, filename):
		return True

	def handleFile(self, res, filename, ext):
		if (self.extensions is None or ext in self.extensions) and self.checkFile(filename):
			res.setdefault(self, []).append(filename)

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

#scanner = [
#		Scanner(extensions = ["jpg", "jpe", "jpeg"], 
#			paths_to_scan = 
#				[
#					ScanPath(path = "DCIM", with_subdirs = True),
#					ScanPath(path = "", with_subdirs = False),
#				],
#			name = "Pictures", 
#			description = "View Photos..."
#		),
#
#		Scanner(extensions = ["mpg", "vob", "ts"], 
#			paths_to_scan =
#				[
#					ScanPath(path = ""),
#					ScanPath(path = "movie", with_subdirs = True),
#				],
#			name = "Movie",
#			description = "View Movies..."
#		),
#
#		Scanner(extensions = ["mp3", "ogg"], 
#			name = "Media",
#			paths_to_scan = 
#				[
#					ScanPath(path = "", with_subdirs = False),
#				],
#			description = "Play music..."
#		),
#
#		Scanner(extensions = ["ipk"], 
#			name = "Packages",
#			paths_to_scan = 
#				[
#					ScanPath(path = ""),
#				],
#			description = "Install software..."
#		),
#	]

def scanDevice(mountpoint):
	from Components.PluginComponent import plugins

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
	for p in set(paths_to_scan):
		if p.with_subdirs == True and ScanPath(path=p.path) in paths_to_scan:
			paths_to_scan.remove(ScanPath(path=p.path))

	# convert to list
	paths_to_scan = list(paths_to_scan)

	# now scan the paths
	for p in paths_to_scan:
		path = os_path.join(mountpoint, p.path)

		for root, dirs, files in os_walk(path):
			for f in files:
				ext = getExtension(f)
				pathname = os_path.join(root, f)
				for s in scanner:
					s.handleFile(res, pathname, ext)

			# if we really don't want to scan subdirs, stop here.
			if not p.with_subdirs:
				del dirs[:]

	# res is a dict with scanner -> [files]
	return res

def execute(option):
	print "execute", option
	if option is None:
		return

	(_, scanner, files, session) = option
	scanner.open(files, session)


def mountpoint_choosen(option):
	if option is None:
		return

	from Screens.ChoiceBox import ChoiceBox

	(description, mountpoint, session) = option
	res = scanDevice(mountpoint)

	list = [ (r.description, r, res[r], session) for r in res ]

	if list == [ ]:
		print "nothing found"
		return

	session.openWithCallback(execute, ChoiceBox, 
		title = "The following files were found...",
		list = list)

def scan(session):
	from Screens.ChoiceBox import ChoiceBox

	from Components.Harddisk import harddiskmanager

	parts = [ (r.description, r.mountpoint, session) for r in harddiskmanager.getMountedPartitions() ]
	session.openWithCallback(mountpoint_choosen, ChoiceBox, title = "Please Select Medium to be Scanned", list = parts)

def main(session, **kwargs):
	scan(session)

def Plugins(**kwargs):
	return PluginDescriptor(name="MediaScanner", description="Scan Files...", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)
