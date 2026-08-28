#!/usr/bin/python
# -*- coding: utf-8 -*-
from mimetypes import guess_type, add_type
from os import walk
from os.path import join
from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins


add_type("audio/dts", ".dts")
add_type("audio/mpeg", ".mp3")
add_type("audio/x-wav", ".wav")
add_type("audio/x-wav", ".wave")
add_type("audio/x-wav", ".wv")
add_type("audio/ogg", ".oga")
add_type("audio/ogg", ".ogg")
add_type("audio/flac", ".flac")
add_type("audio/mp4", ".m4a")
add_type("audio/mpeg", ".mp2")
add_type("audio/mpeg", ".m2a")
add_type("audio/x-ms-wma", ".wma")
add_type("audio/ac3", ".ac3")
add_type("audio/x-matroska", ".mka")
add_type("audio/x-aac", ".aac")
add_type("audio/x-monkeys-audio", ".ape")
add_type("audio/mp4", ".alac")
add_type("audio/amr", ".amr")
add_type("audio/basic", ".au")
add_type("audio/midi", ".mid")
add_type("video/x-dvd-iso", ".iso")
add_type("video/x-dvd-iso", ".img")
add_type("video/x-dvd-iso", ".nrg")
add_type("image/jpeg", ".jpg")
add_type("image/png", ".png")
add_type("image/gif", ".gif")
add_type("image/bmp", ".bmp")
add_type("image/jpeg", ".jpeg")
add_type("image/jpeg", ".jpe")
add_type("image/svg+xml", ".svg")
add_type("video/mpeg", ".mpg")
add_type("video/dvd", ".vob")
add_type("video/mp4", ".m4v")
add_type("video/x-matroska", ".mkv")
add_type("video/avi", ".avi")
add_type("video/divx", ".divx")
add_type("video/x-mpeg", ".dat")
add_type("video/x-flv", ".flv")
add_type("video/mp4", ".mp4")
add_type("video/quicktime", ".mov")
add_type("video/x-ms-wmv", ".wmv")
add_type("video/x-ms-asf", ".asf")
add_type("video/3gpp", ".3gp")
add_type("video/3gpp2", ".3g2")
add_type("video/mpeg", ".mpeg")
add_type("video/mpeg", ".mpe")
add_type("application/vnd.rn-realmedia", ".rm")
add_type("application/vnd.rn-realmedia-vbr", ".rmvb")
add_type("video/ogg", ".ogm")
add_type("video/ogg", ".ogv")
add_type("video/mp2t", ".m2ts")
add_type("video/mts", ".mts")
add_type("video/mp2t", ".ts")
add_type("application/x-debian-package", ".ipk")
add_type("application/x-dream-image", ".nfi")
add_type("video/webm", ".webm")
add_type("video/mpeg", ".pva")
add_type("video/mpeg", ".wtv")


# Guess the mimetype of a file, falling back to a few hardcoded special cases mimetypes doesn't know.
def getType(file):
	(type, _) = guess_type(file, strict=False)
	if type is None:
		# Detect some unknown types
		if file[-12:].lower() == "video_ts.ifo":
			return "video/x-dvd"
		if file == "/media/audiocd/cdplaylist.cdpls":
			return "audio/x-cda"

		p = file.rfind('.')
		if p == -1:
			return None
		ext = file[p + 1:].lower()

		if ext == "ipk":
			return "application/x-debian-package"

		if ext == "dat" and file[-11:-6].lower() == "avseq":
			return "video/x-vcd"
	return type


# Describes one file type handler: which mimetypes/paths it cares about, and what to do when a matching file was found.
class Scanner:
	def __init__(self, name, mimetypes=[], paths_to_scan=[], description="", openfnc=None):
		self.mimetypes = mimetypes
		self.name = name
		self.paths_to_scan = paths_to_scan
		self.description = description
		self.openfnc = openfnc

	# Extra filter hook subclasses can override; base implementation accepts every file.
	def checkFile(self, file):
		return True

	# Add "file" to the result dict (keyed by this scanner) if its mimetype and checkFile() match.
	def handleFile(self, res, file):
		if (self.mimetypes is None or file.mimetype in self.mimetypes) and self.checkFile(file):
			res.setdefault(self, []).append(file)

	def __repr__(self):
		return "<Scanner " + self.name + ">"

	# Invoke the configured openfnc (e.g. to open a screen) with the matched files.
	def open(self, list, *args, **kwargs):
		if self.openfnc is not None:
			self.openfnc(list, *args, **kwargs)


# A directory to look for files in, and whether to recurse into subdirectories.
class ScanPath:
	def __init__(self, path, with_subdirs=False):
		self.path = path
		self.with_subdirs = with_subdirs

	def __repr__(self):
		return self.path + "(" + str(self.with_subdirs) + ")"

	# we will use this in a set(), so we need to implement __hash__ and __cmp__
	def __hash__(self):
		return self.path.__hash__() ^ self.with_subdirs.__hash__()

	def __eq__(self, other):
		return ((self.with_subdirs, self.path) == (other.with_subdirs, other.path))

	def __lt__(self, other):
		return ((self.with_subdirs, self.path) < (other.with_subdirs, other.path))

	def __gt__(self, other):
		return ((self.with_subdirs, self.path) > (other.with_subdirs, other.path))


# A single file found while scanning, with its (auto-detected or explicit) mimetype.
class ScanFile:
	def __init__(self, path, mimetype=None, size=None, autodetect=True):
		self.path = path
		if mimetype is None and autodetect:
			self.mimetype = getType(path)
		else:
			self.mimetype = mimetype
		self.size = size

	def __repr__(self):
		return "<ScanFile " + self.path + " (" + str(self.mimetype) + ", " + str(self.size) + " MB)>"


# openfnc for the built-in Ipkg scanner: open the IPKGInstaller screen with the list of matched .ipk files.
def filescan_open(list, session, **kwargs):
	from Screens.IPKGInstaller import IPKGInstaller  # Prevent Cicle imports
	filelist = [x.path for x in list]
	session.open(IPKGInstaller, filelist)  # List.


# Builds the Scanner that finds .ipk packages, either directly in the scanned root or below an "ipk" subdirectory.
def filescan(**kwargs):
	return Scanner(mimetypes=["application/x-debian-package"], paths_to_scan=[
		ScanPath(path="ipk", with_subdirs=True),
		ScanPath(path="", with_subdirs=False),
	], name="Ipkg", description=_("Install extensions."), openfnc=filescan_open)


# Scanners that always exist, independent of what filescan plugins happen to be installed.
def getBuiltinScanners():
	return [filescan()]


# Callback for the ChoiceBox in openList(): re-opens the scanner the user picked with its matched files.
def execute(option):
	print("[Scanner] execute", option)
	if option is None:
		return

	(_, scanner, files, session) = option
	scanner.open(files, session)


# Walks a freshly mounted device (e.g. USB stick, DVD) and sorts every file it finds into the scanners that want it.
# Returns a dict of {scanner: [ScanFile, ...]}.
def scanDevice(mountpoint):
	# Collect built-in scanners plus every plugin registered for WHERE_FILESCAN.
	scanner = getBuiltinScanners()

	for pluginObj in plugins.getPlugins(PluginDescriptor.WHERE_FILESCAN):
		func = pluginObj()
		if not isinstance(func, list):
			func = [func]
		scanner += func

	print("[Scanner] ", scanner)

	res = {}

	# merge all to-be-scanned paths, with priority to
	# with_subdirs.

	paths_to_scan = set()

	# first merge them all...
	for s in scanner:
		paths_to_scan.update(set(s.paths_to_scan))

	# ...then remove with_subdir=False when same path exists
	# with with_subdirs=True
	for p in paths_to_scan:
		if p.with_subdirs is True and ScanPath(path=p.path) in paths_to_scan:
			paths_to_scan.remove(ScanPath(path=p.path))

	from Components.Harddisk import harddiskmanager
	blockdev = mountpoint.rstrip("/").rsplit('/', 1)[-1]
	error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.getBlockDevInfo(blockdev)

	# now scan the paths
	for p in paths_to_scan:
		path = join(mountpoint, p.path)

		for root, dirs, files in walk(path):
			for f in files:
				path = join(root, f)
				if (is_cdrom and f.endswith(".wav") and f.startswith("track")) or f == "cdplaylist.cdpls":
					sfile = ScanFile(path, "audio/x-cda")
				else:
					sfile = ScanFile(path)
				for s in scanner:
					s.handleFile(res, sfile)

			# if we really don't want to scan subdirs, stop here.
			if not p.with_subdirs:
				del dirs[:]

	# res is a dict with scanner -> [ScanFiles]
	return res


# Given an explicit list of files (e.g. selected in a file browser), find matching scanners and open one.
# If several scanners match, let the user pick via a ChoiceBox; returns False if nothing matched at all.
def openList(session, files):
	if not isinstance(files, list):
		files = [files]

	# Collect built-in scanners plus every plugin registered for WHERE_FILESCAN.
	scanner = getBuiltinScanners()

	for pluginObj in plugins.getPlugins(PluginDescriptor.WHERE_FILESCAN):
		func = pluginObj()
		if not isinstance(func, list):
			scanner.append(func)
		else:
			scanner += func

	print("[Scanner] ", scanner)

	res = {}

	for file in files:
		for item in scanner:
			item.handleFile(res, file)

	choices = [(r.description, r, res[r], session) for r in res]
	Len = len(choices)
	if Len > 1:
		from Screens.ChoiceBox import ChoiceBox

		session.openWithCallback(
			execute,
			ChoiceBox,
			title="The following viewers were found...",
			list=choices
		)
		return True
	elif Len:
		execute(choices[0])
		return True

	return False


# Convenience wrapper around openList() for a single file with a known mimetype.
def openFile(session, mimetype, file):
	return openList(session, [ScanFile(file, mimetype)])
