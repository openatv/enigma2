# -*- coding: utf-8 -*-
import errno
import inspect
import os

from enigma import eEnv, getDesktop
from re import compile
from stat import S_IMODE

pathExists = os.path.exists
isMount = os.path.ismount  # Only used in OpenATV /lib/python/Plugins/SystemPlugins/NFIFlash/downloader.py.

SCOPE_TRANSPONDERDATA = 0
SCOPE_SYSETC = 1
SCOPE_FONTS = 2
SCOPE_SKIN = 3
SCOPE_SKIN_IMAGE = 4  # DEBUG: How is this different from SCOPE_SKIN?
SCOPE_USERETC = 5  # DEBUG: Not used in Enigma2.
SCOPE_CONFIG = 6
SCOPE_LANGUAGE = 7
SCOPE_HDD = 8
SCOPE_PLUGINS = 9
SCOPE_MEDIA = 10
SCOPE_PLAYLIST = 11
SCOPE_CURRENT_SKIN = 12
SCOPE_CURRENT_PLUGIN_ABSOLUTE = 13
SCOPE_CURRENT_PLUGIN_RELATIVE = 14
SCOPE_KEYMAPS = 15
SCOPE_METADIR = 16
SCOPE_CURRENT_PLUGIN = 17
SCOPE_TIMESHIFT = 18
SCOPE_ACTIVE_SKIN = 19  # DEBUG: Deprecated scope function - use SCOPE_CURRENT_SKIN instead.
SCOPE_LCDSKIN = 20
SCOPE_CURRENT_LCDSKIN = 21
SCOPE_ACTIVE_LCDSKIN = 21  # DEBUG: Deprecated scope function name - use SCOPE_CURRENT_LCDSKIN instead.
SCOPE_AUTORECORD = 22
SCOPE_DEFAULTDIR = 23
SCOPE_DEFAULTPARTITION = 24
SCOPE_DEFAULTPARTITIONMOUNTDIR = 25
SCOPE_LIBDIR = 26

PATH_CREATE = 0
PATH_DONTCREATE = 1

defaultPaths = {
	SCOPE_TRANSPONDERDATA: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_SYSETC: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_FONTS: (eEnv.resolve("${datadir}/fonts/"), PATH_DONTCREATE),
	SCOPE_SKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_SKIN_IMAGE: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_USERETC: ("", PATH_DONTCREATE),  # User home directory
	SCOPE_CONFIG: (eEnv.resolve("${sysconfdir}/enigma2/"), PATH_CREATE),
	SCOPE_LANGUAGE: (eEnv.resolve("${datadir}/enigma2/po/"), PATH_DONTCREATE),
	SCOPE_HDD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_PLUGINS: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_MEDIA: ("/media/", PATH_DONTCREATE),
	SCOPE_PLAYLIST: (eEnv.resolve("${sysconfdir}/enigma2/playlist/"), PATH_CREATE),
	SCOPE_CURRENT_SKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_CURRENT_PLUGIN_ABSOLUTE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_CURRENT_PLUGIN_RELATIVE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_KEYMAPS: (eEnv.resolve("${datadir}/keymaps/"), PATH_CREATE),
	SCOPE_METADIR: (eEnv.resolve("${datadir}/meta"), PATH_CREATE),
	SCOPE_CURRENT_PLUGIN: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_TIMESHIFT: ("/media/hdd/timeshift/", PATH_DONTCREATE),
	SCOPE_ACTIVE_SKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	SCOPE_CURRENT_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	SCOPE_AUTORECORD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_DEFAULTDIR: (eEnv.resolve("${datadir}/enigma2/defaults/"), PATH_CREATE),
	SCOPE_DEFAULTPARTITION: ("/dev/mtdblock6", PATH_DONTCREATE),
	SCOPE_DEFAULTPARTITIONMOUNTDIR: (eEnv.resolve("${datadir}/enigma2/dealer"), PATH_CREATE),
	SCOPE_LIBDIR: (eEnv.resolve("${libdir}/"), PATH_DONTCREATE)
}

def resolveFilename(scope, base="", path_prefix=None):
	# You can only use the ~/ if we have a prefix directory.
	if base.startswith("~/"):
		assert path_prefix is not None  # Assert only works in debug mode!
		if path_prefix:
			base = os.path.join(path_prefix, base[2:])
		else:
			print "[Directories] Warning: resolveFilename called with base starting with '~/' but 'path_prefix' is None!"
	# Don't further resolve absolute paths.
	if base.startswith("/"):
		return os.path.normpath(base)
	# If an invalid scope is specified log an error and return None.
	if scope not in defaultPaths:
		print "[Directories] Error: Invalid scope=%d provided to resolveFilename!" % scope
		return None
	# Ensure that the defaultPaths directories that should exist do exist.
	path, flag = defaultPaths.get(scope)
	if flag == PATH_CREATE and not pathExists(path):
		try:
			os.makedirs(path)
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Couldn't create directory '%s' (%s)" % (err.errno, path, err.strerror)
			return None
	# Remove any suffix data and restore it at the end.
	suffix = None
	data = base.split(":", 1)
	if len(data) > 1:
		base = data[0]
		suffix = data[1]
	path = base
	# If base is "" then set path to the scope.  Otherwise use the scope to resolve the base filename.
	if base is "":
		path, flags = defaultPaths.get(scope)
		# If the scope is SCOPE_CURRENT_SKIN or SCOPE_ACTIVE_SKIN append the current skin to the scope path.
		if scope in (SCOPE_CURRENT_SKIN, SCOPE_ACTIVE_SKIN):
			# This import must be here as this module finds the config file as part of the config initialisation.
			from Components.config import config
			skin = os.path.dirname(config.skin.primary_skin.value)
			path = os.path.join(path, skin)
		elif scope in (SCOPE_CURRENT_PLUGIN_ABSOLUTE, SCOPE_CURRENT_PLUGIN_RELATIVE):
			callingCode = os.path.normpath(inspect.stack()[1][1])
			plugins = os.path.normpath(defaultPaths[SCOPE_PLUGINS][0])
			path = None
			if comparePath(plugins, callingCode):
				pluginCode = callingCode[len(plugins) + 1:].split(os.sep)
				if len(pluginCode) > 2:
					relative = "%s%s%s" % (pluginCode[0], os.sep, pluginCode[1])
					path = os.path.join(plugins, relative)
	elif scope in (SCOPE_CURRENT_SKIN, SCOPE_ACTIVE_SKIN):
		# This import must be here as this module finds the config file as part of the config initialisation.
		from Components.config import config
		skin = os.path.dirname(config.skin.primary_skin.value)
		resolveList = [
			os.path.join(defaultPaths[SCOPE_CONFIG][0], skin),
			os.path.join(defaultPaths[SCOPE_CONFIG][0], "skin_common"),
			defaultPaths[SCOPE_CONFIG][0],  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			os.path.join(defaultPaths[SCOPE_SKIN][0], skin),
			os.path.join(defaultPaths[SCOPE_SKIN][0], "skin_fallback_%d" % getDesktop(0).size().height()),
			os.path.join(defaultPaths[SCOPE_SKIN][0], "skin_default"),
			defaultPaths[SCOPE_SKIN][0]  # Can we deprecate top level of SCOPE_SKIN directory to allow a clean up?
		]
		for item in resolveList:
			file = os.path.join(item, base)
			if pathExists(file):
				path = file
				break
	elif scope == SCOPE_CURRENT_LCDSKIN:
		# This import must be here as this module finds the config file as part of the config initialisation.
		from Components.config import config
		if hasattr(config.skin, "display_skin"):
			skin = os.path.dirname(config.skin.display_skin.value)
		else:
			skin = ""
		resolveList = [
			os.path.join(defaultPaths[SCOPE_CONFIG][0], "display", skin),
			os.path.join(defaultPaths[SCOPE_CONFIG][0], "display", "skin_common"),
			defaultPaths[SCOPE_CONFIG][0],  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			os.path.join(defaultPaths[SCOPE_LCDSKIN][0], skin),
			os.path.join(defaultPaths[SCOPE_LCDSKIN][0], "skin_fallback_%s" % getDesktop(1).size().height()),
			os.path.join(defaultPaths[SCOPE_LCDSKIN][0], "skin_default"),
			defaultPaths[SCOPE_LCDSKIN][0]  # Can we deprecate top level of SCOPE_LCDSKIN directory to allow a clean up?
		]
		for item in resolveList:
			file = os.path.join(item, base)
			if pathExists(file):
				path = file
				break
	elif scope == SCOPE_FONTS:
		# This import must be here as this module finds the config file as part of the config initialisation.
		from Components.config import config
		skin = os.path.dirname(config.skin.primary_skin.value)
		display = os.path.dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else None
		resolveList = [
			os.path.join(defaultPaths[SCOPE_CONFIG][0], "fonts"),
			os.path.join(defaultPaths[SCOPE_CONFIG][0], skin)
		]
		if display:
			resolveList.append(os.path.join(defaultPaths[SCOPE_CONFIG][0], "display", display))
		resolveList.append(os.path.join(defaultPaths[SCOPE_CONFIG][0], "skin_common"))
		resolveList.append(defaultPaths[SCOPE_CONFIG][0])  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
		resolveList.append(os.path.join(defaultPaths[SCOPE_SKIN][0], skin))
		resolveList.append(os.path.join(defaultPaths[SCOPE_SKIN][0], "skin_default"))
		if display:
			resolveList.append(os.path.join(defaultPaths[SCOPE_LCDSKIN][0], display))
		resolveList.append(os.path.join(defaultPaths[SCOPE_LCDSKIN][0], "skin_default"))
		resolveList.append(defaultPaths[SCOPE_FONTS][0])
		for item in resolveList:
			file = os.path.join(item, base)
			if pathExists(file):
				path = file
				break
	elif scope == SCOPE_CURRENT_PLUGIN:
		file = os.path.join(defaultPaths[SCOPE_PLUGINS][0], base)
		if pathExists(file):
			path = file
	elif scope in (SCOPE_CURRENT_PLUGIN_ABSOLUTE, SCOPE_CURRENT_PLUGIN_RELATIVE):
		callingCode = os.path.normpath(inspect.stack()[1][1])
		plugins = os.path.normpath(defaultPaths[SCOPE_PLUGINS][0])
		path = None
		if comparePath(plugins, callingCode):
			pluginCode = callingCode[len(plugins) + 1:].split(os.sep)
			if len(pluginCode) > 2:
				relative = os.path.join("%s%s%s" % (pluginCode[0], os.sep, pluginCode[1]), base)
				path = os.path.join(plugins, relative)
	else:
		path, flags = defaultPaths.get(scope)
		path = os.path.join(path, base)
	path = os.path.normpath(path)
	# If the path is a directory then ensure that it ends with a "/".
	if os.path.isdir(path) and not path.endswith("/"):
		path += "/"
	if scope == SCOPE_CURRENT_PLUGIN_RELATIVE:
		path = path[len(plugins) + 1:]
	# If a suffix was supplier restore it.
	if suffix is not None:
		path = "%s:%s" % (path, suffix)
	return path

def comparePath(leftPath, rightPath):
	if leftPath.endswith(os.sep):
		leftPath = leftPath[:-1]
	if rightPath.endswith(os.sep):
		rightPath = rightPath[:-1]
	left = leftPath.split(os.sep)
	right = rightPath.split(os.sep)
	for segment in range(len(left)):
		if left[segment] != right[segment]:
			return False
	return True

def bestRecordingLocation(candidates):
	path = ""
	biggest = 0
	for candidate in candidates:
		try:
			# Must have some free space (i.e. not read-only).
			stat = os.statvfs(candidate[1])
			if stat.f_bavail:
				# Free space counts double.
				size = (stat.f_blocks + stat.f_bavail) * stat.f_bsize
				if size > biggest:
					biggest = size
					path = candidate[1]
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Couldn't get free space for '%s' (%s)" % (err.errno, candidate[1], err.strerror)
	return path

def defaultRecordingLocation(candidate=None):
	if candidate and pathExists(candidate):
		return candidate
	# First, try whatever /hdd points to, or /media/hdd.
	try:
		path = os.readlink("/hdd")
	except OSError:
		path = "/media/hdd"
	if not pathExists(path):
		# Find the largest local disk.
		from Components import Harddisk
		mounts = [m for m in Harddisk.getProcMounts() if m[1].startswith("/media/")]
		# Search local devices first, use the larger one
		path = bestRecordingLocation([m for m in mounts if m[0].startswith("/dev/")])
		# If we haven't found a viable candidate yet, try remote mounts.
		if not path:
			path = bestRecordingLocation([m for m in mounts if not m[0].startswith("/dev/")])
	if path:
		# If there's a movie subdir, we'd probably want to use that.
		movie = os.path.join(path, "movie")
		if os.path.isdir(movie):
			path = movie
		if not path.endswith("/"):
			path += "/"  # Bad habits die hard, old code relies on this.
	return path

def createDir(path, makeParents=False):
	try:
		if makeParents:
			os.makedirs(path)
		else:
			os.mkdir(path)
		return 1
	except OSError:
		return 0

def removeDir(path):
	try:
		os.rmdir(path)
		return 1
	except OSError:
		return 0

def fileExists(f, mode="r"):
	if mode == "r":
		acc_mode = os.R_OK
	elif mode == "w":
		acc_mode = os.W_OK
	else:
		acc_mode = os.F_OK
	return os.access(f, acc_mode)

def fileCheck(f, mode="r"):
	return fileExists(f, mode) and f

def fileHas(f, content, mode="r"):
	result = False
	if fileExists(f, mode):
		file = open(f, mode)
		text = file.read()
		file.close()
		if content in text:
			result = True
	return result

def getRecordingFilename(basename, dirname=None):
	# Filter out non-allowed characters.
	non_allowed_characters = "/.\\:*?<>|\""
	basename = basename.replace("\xc2\x86", "").replace("\xc2\x87", "")
	filename = ""
	for c in basename:
		if c in non_allowed_characters or ord(c) < 32:
			c = "_"
		filename += c
	# Max filename length for ext4 is 255 (minus 8 characters for .ts.meta)
	# but must not truncate in the middle of a multi-byte utf8 character!
	# So convert the truncation to unicode and back, ignoring errors, the
	# result will be valid utf8 and so xml parsing will be OK.
	filename = unicode(filename[:247], "utf8", "ignore").encode("utf8", "ignore")
	if dirname is not None:
		if not dirname.startswith("/"):
			dirname = os.path.join(defaultRecordingLocation(), dirname)
	else:
		dirname = defaultRecordingLocation()
	filename = os.path.join(dirname, filename)
	path = filename
	i = 1
	while True:
		if not os.path.isfile(path + ".ts"):
			return path
		path += "_%03d" % i
		i += 1

# This is clearly a hack:
#
def InitFallbackFiles():
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.tv")
	resolveFilename(SCOPE_CONFIG, "bouquets.tv")
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.radio")
	resolveFilename(SCOPE_CONFIG, "bouquets.radio")

# Returns a list of tuples containing pathname and filename matching the given pattern
# Example-pattern: match all txt-files: ".*\.txt$"
#
def crawlDirectory(directory, pattern):
	list = []
	if directory:
		expression = compile(pattern)
		for root, dirs, files in os.walk(directory):
			for file in files:
				if expression.match(file) is not None:
					list.append((root, file))
	return list

def copyfile(src, dst):
	f1 = None
	f2 = None
	status = 0
	try:
		f1 = open(src, "rb")
		if os.path.isdir(dst):
			dst = os.path.join(dst, os.path.basename(src))
		f2 = open(dst, "w+b")
		while True:
			buf = f1.read(16 * 1024)
			if not buf:
				break
			f2.write(buf)
	except (IOError, OSError) as err:
		print "[Directories] Error %d: Copying file '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
		status = -1
	if f1 is not None:
		f1.close()
	if f2 is not None:
		f2.close()
	try:
		st = os.stat(src)
		try:
			os.chmod(dst, S_IMODE(st.st_mode))
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Setting modes from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
		try:
			os.utime(dst, (st.st_atime, st.st_mtime))
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Setting times from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
	except (IOError, OSError) as err:
		print "[Directories] Error %d: Obtaining stats from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
	return status

def copytree(src, dst, symlinks=False):
	names = os.listdir(src)
	if os.path.isdir(dst):
		dst = os.path.join(dst, os.path.basename(src))
		if not os.path.isdir(dst):
			os.mkdir(dst)
	else:
		os.makedirs(dst)
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				copytree(srcname, dstname, symlinks)
			else:
				copyfile(srcname, dstname)
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Copying tree '%s' to '%s'! (%s)" % (err.errno, srcname, dstname, err.strerror)
	try:
		st = os.stat(src)
		try:
			os.chmod(dst, S_IMODE(st.st_mode))
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Setting modes from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
		try:
			os.utime(dst, (st.st_atime, st.st_mtime))
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Setting times from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)
	except (IOError, OSError) as err:
		print "[Directories] Error %d: Obtaining stats from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror)

# Renames files or if source and destination are on different devices moves them in background
# input list of (source, destination)
#
def moveFiles(fileList):
	errorFlag = False
	movedList = []
	try:
		for item in fileList:
			os.rename(item[0], item[1])
			movedList.append(item)
	except (IOError, OSError) as err:
		if err.errno == errno.EXDEV:  # Invalid cross-device link
			print "[Directories] Warning: Cannot rename across devices, trying slower move."
			from Tools.CopyFiles import moveFiles as extMoveFiles  # OpenViX, OpenATV, Beyonwiz
			# from Screens.CopyFiles import moveFiles as extMoveFiles  # OpenPLi
			extMoveFiles(fileList, item[0])
			print "[Directories] Moving files in background."
		else:
			print "[Directories] Error %d: Moving file '%s' to '%s'! (%s)" % (err.errno, item[0], item[1], err.strerror)
			errorFlag = True
	if errorFlag:
		print "[Directories] Reversing renamed files due to error."
		for item in movedList:
			try:
				os.rename(item[1], item[0])
			except (IOError, OSError) as err:
				print "[Directories] Error %d: Renaming '%s' to '%s'! (%s)" % (err.errno, item[1], item[0], err.strerror)
				print "[Directories] Failed to undo move:", item

def getSize(path, pattern=".*"):
	path_size = 0
	if os.path.isdir(path):
		files = crawlDirectory(path, pattern)
		for file in files:
			filepath = os.path.join(file[0], file[1])
			path_size += os.path.getsize(filepath)
	elif os.path.isfile(path):
		path_size = os.path.getsize(path)
	return path_size

def lsof():
	lsof = []
	for pid in os.listdir("/proc"):
		if pid.isdigit():
			try:
				prog = os.readlink(os.path.join("/proc", pid, "exe"))
				dir = os.path.join("/proc", pid, "fd")
				for file in [os.path.join(dir, file) for file in os.listdir(dir)]:
					lsof.append((pid, prog, os.readlink(file)))
			except OSError:
				pass
	return lsof

def getExtension(file):
	filename, extension = os.path.splitext(file)
	return extension

def mediafilesInUse(session):
	from Components.MovieList import KNOWN_EXTENSIONS
	files = [os.path.basename(x[2]) for x in lsof() if getExtension(x[2]) in KNOWN_EXTENSIONS]
	service = session.nav.getCurrentlyPlayingServiceOrGroup()
	filename = service and service.getPath()
	if filename:
		if "://" in filename:  # When path is a stream ignore it.
			filename = None
		else:
			filename = os.path.basename(filename)
	return set([file for file in files if not(filename and file == filename and files.count(filename) < 2)])

# Prepare filenames for use in external shell processing. Filenames may
# contain spaces or other special characters.  This method adjusts the
# filename to be a safe and single entity for passing to a shell.
#
def shellquote(s):
	return "'%s'" % s.replace("'", "'\\''")
