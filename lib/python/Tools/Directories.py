from errno import ENOENT, EXDEV
from inspect import stack
from os import F_OK, R_OK, W_OK, access, chmod, link, listdir, makedirs, mkdir, readlink, remove, rename, rmdir, sep, stat, statvfs, symlink, utime, walk
from os.path import basename, dirname, exists, getsize, isdir, isfile, islink, join as pathjoin, normpath, splitext
from re import compile
from six import PY2
from stat import S_IMODE
from tempfile import mkstemp
from traceback import print_exc
from xml.etree.cElementTree import ParseError, fromstring, parse

from enigma import eEnv, getDesktop, eGetEnigmaDebugLvl

DEFAULT_MODULE_NAME = __name__.split(".")[-1]

forceDebug = eGetEnigmaDebugLvl() > 4
pathExists = exists

SCOPE_TRANSPONDERDATA = 0
SCOPE_SYSETC = 1
SCOPE_FONTS = 2
SCOPE_SKIN = 3
# SCOPE_SKIN_IMAGE is a deprecated scope function - use SCOPE_CURRENT_SKIN instead.
# SCOPE_SKIN_IMAGE = SCOPE_ACTIVE_SKIN = SCOPE_CURRENT_SKIN
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
# SCOPE_ACTIVE_SKIN is a deprecated scope function - use SCOPE_CURRENT_SKIN instead.
# SCOPE_ACTIVE_SKIN = SCOPE_SKIN_IMAGE = SCOPE_CURRENT_SKIN
SCOPE_ACTIVE_SKIN = 19  # DEBUG: Deprecated scope function - use SCOPE_CURRENT_SKIN instead.
SCOPE_LCDSKIN = 20
SCOPE_CURRENT_LCDSKIN = SCOPE_LCDSKIN
# SCOPE_ACTIVE_LCDSKIN is a deprecated scope function - use SCOPE_CURRENT_LCDSKIN instead.
# SCOPE_ACTIVE_LCDSKIN = SCOPE_CURRENT_LCDSKIN
SCOPE_ACTIVE_LCDSKIN = SCOPE_LCDSKIN # DEBUG: Deprecated scope function name - use SCOPE_CURRENT_LCDSKIN instead.
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
	# SCOPE_CURRENT_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	# SCOPE_ACTIVE_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	SCOPE_AUTORECORD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_DEFAULTDIR: (eEnv.resolve("${datadir}/enigma2/defaults/"), PATH_CREATE),
	SCOPE_DEFAULTPARTITION: ("/dev/mtdblock6", PATH_DONTCREATE),
	SCOPE_DEFAULTPARTITIONMOUNTDIR: (eEnv.resolve("${datadir}/enigma2/dealer"), PATH_CREATE),
	SCOPE_LIBDIR: (eEnv.resolve("${libdir}/"), PATH_DONTCREATE)
}

scopeConfig = defaultPaths[SCOPE_CONFIG][0]
scopeSkin = defaultPaths[SCOPE_SKIN][0]
scopeLcdSkin = defaultPaths[SCOPE_LCDSKIN][0]
scopeFonts = defaultPaths[SCOPE_FONTS][0]
scopePlugins = defaultPaths[SCOPE_PLUGINS][0]


def resolveFilename(scope, base="", path_prefix=None):
	# You can only use the ~/ if we have a prefix directory.
	if str(base).startswith("~%s" % sep):
		assert path_prefix is not None  # Assert only works in debug mode!
		if path_prefix:
			base = pathjoin(path_prefix, base[2:])
		else:
			print("[Directories] Warning: resolveFilename called with base starting with '~%s' but 'path_prefix' is None!" % sep)
	# Don't further resolve absolute paths.
	if str(base).startswith(sep):
		return normpath(base)
	# If an invalid scope is specified log an error and return None.
	if scope not in defaultPaths:
		print("[Directories] Error: Invalid scope=%s provided to resolveFilename!" % scope)
		return None
	# Ensure that the defaultPath directory that should exist for this scope does exist.
	path, flag = defaultPaths[scope]
	if flag == PATH_CREATE and not pathExists(path):
		try:
			makedirs(path)
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Couldn't create directory '%s' (%s)" % (err.errno, path, err.strerror))
			return None
	# Remove any suffix data and restore it at the end.
	suffix = None
	data = base.split(":", 1)
	if len(data) > 1:
		base = data[0]
		suffix = data[1]
	path = base

	def itemExists(resolveList, base):
		baseList = [base]
		if base.endswith(".png"):
			baseList.append("%s%s" % (base[:-3], "svg"))
		elif base.endswith(".svg"):
			baseList.append("%s%s" % (base[:-3], "png"))
		for item in resolveList:
			for base in baseList:
				file = pathjoin(item, base)
				if pathExists(file):
					return file

	# If base is "" then set path to the scope.  Otherwise use the scope to resolve the base filename.
	if base == "":
		path, flags = defaultPaths.get(scope)
		# If the scope is SCOPE_CURRENT_SKIN or SCOPE_ACTIVE_SKIN or SCOPE_SKIN_IMAGE append the current skin to the scope path.
		if scope in (SCOPE_CURRENT_SKIN, SCOPE_ACTIVE_SKIN, SCOPE_SKIN_IMAGE):
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialisation.
			skin = dirname(config.skin.primary_skin.value)
			path = pathjoin(path, skin)
		elif scope in (SCOPE_CURRENT_PLUGIN_ABSOLUTE, SCOPE_CURRENT_PLUGIN_RELATIVE):
			callingCode = normpath(stack()[1][1])
			plugins = normpath(scopePlugins)
			path = None
			if comparePath(plugins, callingCode):
				pluginCode = callingCode[len(plugins) + 1:].split(sep)
				if len(pluginCode) > 2:
					relative = "%s%s%s" % (pluginCode[0], sep, pluginCode[1])
					path = pathjoin(plugins, relative)
	elif scope in (SCOPE_CURRENT_SKIN, SCOPE_ACTIVE_SKIN, SCOPE_SKIN_IMAGE):
		from Components.config import config  # This import must be here as this module finds the config file as part of the config initialisation.
		skin = dirname(config.skin.primary_skin.value)
		resolveList = [
			pathjoin(scopeConfig, skin),
			pathjoin(scopeConfig, "skin_common"),
			scopeConfig,  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			pathjoin(scopeSkin, skin),
			pathjoin(scopeSkin, "skin_fallback_%d" % getDesktop(0).size().height()),
			pathjoin(scopeSkin, "skin_default"),
			scopeSkin  # Can we deprecate top level of SCOPE_SKIN directory to allow a clean up?
		]
		file = itemExists(resolveList, base)
		if file:
			path = file
	elif scope == SCOPE_LCDSKIN:  # in (SCOPE_CURRENT_LCDSKIN, SCOPE_ACTIVE_LCDSKIN):
		from Components.config import config  # This import must be here as this module finds the config file as part of the config initialisation.
		if hasattr(config.skin, "display_skin"):
			skin = dirname(config.skin.display_skin.value)
		else:
			skin = ""
		resolveList = [
			pathjoin(scopeConfig, "display", skin),
			pathjoin(scopeConfig, "display", "skin_common"),
			scopeConfig,  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
			pathjoin(scopeLcdSkin, skin),
			pathjoin(scopeLcdSkin, "skin_fallback_%s" % getDesktop(1).size().height()),
			pathjoin(scopeLcdSkin, "skin_default"),
			scopeLcdSkin  # Can we deprecate top level of SCOPE_LCDSKIN directory to allow a clean up?
		]
		file = itemExists(resolveList, base)
		if file:
			path = file
	elif scope == SCOPE_FONTS:
		# This import must be here as this module finds the config file as part of the config initialisation.
		from Components.config import config
		skin = dirname(config.skin.primary_skin.value)
		display = dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else None
		resolveList = [
			pathjoin(scopeConfig, "fonts"),
			pathjoin(scopeConfig, skin, "fonts"),
			pathjoin(scopeConfig, skin)
		]
		if display:
			resolveList.append(pathjoin(scopeConfig, "display", display, "fonts"))
			resolveList.append(pathjoin(scopeConfig, "display", display))
		resolveList.append(pathjoin(scopeConfig, "skin_common", "fonts"))
		resolveList.append(pathjoin(scopeConfig, "skin_common"))
		resolveList.append(scopeConfig)  # Can we deprecate top level of SCOPE_CONFIG directory to allow a clean up?
		resolveList.append(pathjoin(scopeSkin, skin, "fonts"))
		resolveList.append(pathjoin(scopeSkin, skin))
		resolveList.append(pathjoin(scopeSkin, "skin_default", "fonts"))
		resolveList.append(pathjoin(scopeSkin, "skin_default"))
		if display:
			resolveList.append(pathjoin(scopeLcdSkin, display, "fonts"))
			resolveList.append(pathjoin(scopeLcdSkin, display))
		resolveList.append(pathjoin(scopeLcdSkin, "skin_default", "fonts"))
		resolveList.append(pathjoin(scopeLcdSkin, "skin_default"))
		resolveList.append(scopeFonts)
		for item in resolveList:
			file = pathjoin(item, base)
			if pathExists(file):
				path = file
				break
	elif scope == SCOPE_CURRENT_PLUGIN:
		file = pathjoin(scopePlugins, base)
		if pathExists(file):
			path = file
	elif scope in (SCOPE_CURRENT_PLUGIN_ABSOLUTE, SCOPE_CURRENT_PLUGIN_RELATIVE):
		callingCode = normpath(stack()[1][1])
		plugins = normpath(scopePlugins)
		path = None
		if comparePath(plugins, callingCode):
			pluginCode = callingCode[len(plugins) + 1:].split(sep)
			if len(pluginCode) > 2:
				relative = pathjoin("%s%s%s" % (pluginCode[0], sep, pluginCode[1]), base)
				path = pathjoin(plugins, relative)
	else:
		path, flags = defaultPaths.get(scope)
		path = pathjoin(path, base)
	path = normpath(path)
	# If the path is a directory then ensure that it ends with a "/".
	if isdir(path) and not path.endswith(sep):
		path = "%s%s" % (path, sep)
	if scope == SCOPE_CURRENT_PLUGIN_RELATIVE:
		path = path[len(plugins) + 1:]
	# If a suffix was supplier restore it.
	if suffix is not None:
		path = "%s:%s" % (path, suffix)
	return path


def InitDefaultPaths():
	resolveFilename(SCOPE_CONFIG)


def InitFallbackFiles():
	InitDefaultPaths()


def comparePath(leftPath, rightPath):
	print("[Directories] comparePath DEBUG: left='%s', right='%s'." % (leftPath, rightPath))
	if leftPath.endswith(sep):
		leftPath = leftPath[:-1]
	if rightPath.endswith(sep):
		rightPath = rightPath[:-1]
	left = leftPath.split(sep)
	right = rightPath.split(sep)
	for segment in range(len(left)):
		if left[segment] != right[segment]:
			return False
	return True


def bestRecordingLocation(candidates):
	path = ""
	biggest = 0
	for candidate in candidates:
		try:
			status = statvfs(candidate[1])  # Must have some free space (i.e. not read-only).
			if status.f_bavail:
				size = (status.f_blocks + status.f_bavail) * status.f_bsize  # Free space counts double.
				if size > biggest:
					biggest = size
					path = candidate[1]
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Couldn't get free space for '%s'! (%s)" % (err.errno, candidate[1], err.strerror))
	return path


def defaultRecordingLocation(candidate=None):
	if candidate and pathExists(candidate):
		return candidate
	# First, try whatever /hdd points to, or /media/hdd.
	try:
		path = readlink("/hdd")
	except (IOError, OSError) as err:
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
		movie = pathjoin(path, "movie")
		if isdir(movie):
			path = movie
		if not path.endswith(sep):
			path = "%s%s" % (path, sep)  # Bad habits die hard, old code relies on this.
	return path


def createDir(path, makeParents=False):
	try:
		if makeParents:
			makedirs(path)
		else:
			mkdir(path)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't create directory '%s'! (%s)" % (err.errno, path, err.strerror))
	return 0


def renameDir(oldPath, newPath):
	try:
		rename(oldPath, newPath)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't rename directory '%s' to '%s'! (%s)" % (err.errno, oldPath, newPath, err.strerror))
	return 0


def removeDir(path):
	try:
		rmdir(path)
		return 1
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't remove directory '%s'! (%s)" % (err.errno, path, err.strerror))
	return 0


def fileAccess(file, mode="r"):
	accMode = F_OK
	if "r" in mode:
		accMode |= R_OK
	if "w" in mode:
		accMode |= W_OK
	result = False
	try:
		result = access(file, accMode)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Couldn't determine file '%s' access mode! (%s)" % (err.errno, file, err.strerror))
	return result


def fileCheck(file, mode="r"):
	return fileAccess(file, mode) and file


def fileExists(file, mode="r"):
	return fileAccess(file, mode) and file


def fileContains(file, content, mode="r"):
	result = False
	if fileExists(file, mode):
		fd = open(file, mode)
		text = fd.read()
		fd.close()
		if content in text:
			result = True
	return result


def fileHas(file, content, mode="r"):
	return fileContains(file, content, mode)


def fileReadLine(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	line = None
	try:
		with open(filename, "r") as fd:
			line = fd.read().strip().replace("\0", "")
		msg = "Read"
	except (IOError, OSError) as err:
		if err.errno != ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Error %d: Unable to read a line from file '%s'! (%s)" % (source, err.errno, filename, err.strerror))
		line = default
		msg = "Default"
	if debug or forceDebug:
		print("[%s] Line %d: %s '%s' from file '%s'." % (source, stack()[1][0].f_lineno, msg, line, filename))
	return line


def fileWriteLine(filename, line, source=DEFAULT_MODULE_NAME, debug=False):
	try:
		with open(filename, "w") as fd:
			fd.write(str(line))
		msg = "Wrote"
		result = 1
	except (IOError, OSError) as err:
		print("[%s] Error %d: Unable to write a line to file '%s'! (%s)" % (source, err.errno, filename, err.strerror))
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print("[%s] Line %d: %s '%s' to file '%s'." % (source, stack()[1][0].f_lineno, msg, line, filename))
	return result


def fileReadLines(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	lines = None
	try:
		with open(filename, "r") as fd:
			lines = fd.read().splitlines()
		msg = "Read"
	except (IOError, OSError) as err:
		if err.errno != ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Error %d: Unable to read lines from file '%s'! (%s)" % (source, err.errno, filename, err.strerror))
		lines = default
		msg = "Default"
	if debug or forceDebug:
		length = len(lines) if lines else 0
		print("[%s] Line %d: %s %d lines from file '%s'." % (source, stack()[1][0].f_lineno, msg, length, filename))
	return lines


def fileWriteLines(filename, lines, source=DEFAULT_MODULE_NAME, debug=False):
	try:
		with open(filename, "w") as fd:
			if isinstance(lines, list):
				lines.append("")
				lines = "\n".join(lines)
			fd.write(lines)
		msg = "Wrote"
		result = 1
	except (IOError, OSError) as err:
		print("[%s] Error %d: Unable to write %d lines to file '%s'! (%s)" % (source, err.errno, len(lines), filename, err.strerror))
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print("[%s] Line %d: %s %d lines to file '%s'." % (source, stack()[1][0].f_lineno, msg, len(lines), filename))
	return result


def fileReadXML(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	dom = None
	try:
		with open(filename, "r") as fd:  # This open gets around a possible file handle leak in Python's XML parser.
			try:
				dom = parse(fd).getroot()
				msg = "Read"
			except ParseError as err:
				fd.seek(0)
				content = fd.readlines()
				line, column = err.position
				print("[%s] XML Parse Error: '%s' in '%s'!" % (source, err, filename))
				data = content[line - 1].replace("\t", " ").rstrip()
				print("[%s] XML Parse Error: '%s'" % (source, data))
				print("[%s] XML Parse Error: '%s^%s'" % (source, "-" * column, " " * (len(data) - column - 1)))
			except Exception as err:
				print("[%s] Error: Unable to parse data in '%s' - '%s'!" % (source, filename, err))
	except (IOError, OSError) as err:
		if err.errno == ENOENT:  # ENOENT - No such file or directory.
			print("[%s] Warning: File '%s' does not exist!" % (source, filename))
		else:
			print("[%s] Error %d: Opening file '%s'! (%s)" % (source, err.errno, filename, err.strerror))
	except Exception as err:
		print("[%s] Error: Unexpected error opening/parsing file '%s'! (%s)" % (source, filename, err))
		print_exc()
	if dom is None:
		if default:
			dom = fromstring(default)
			msg = "Default"
		else:
			msg = "Failed to read"
	if debug or forceDebug:
		print("[%s] Line %d: %s from XML file '%s'." % (source, stack()[1][0].f_lineno, msg, filename))
	return dom


def getRecordingFilename(basename, dirname=None):
	# Filter out non-allowed characters.
	non_allowed_characters = "/.\\:*?<>|\""
	basename = basename.replace("\xc2\x86", "").replace("\xc2\x87", "") if PY2 else basename.replace("\x86", "").replace("\x87", "")
	filename = ""
	for c in basename:
		if c in non_allowed_characters or ord(c) < 32:
			c = "_"
		filename += c
	# Max filename length for ext4 is 255 (minus 8 characters for .ts.meta)
	# but must not truncate in the middle of a multi-byte utf8 character!
	# So convert the truncation to unicode and back, ignoring errors, the
	# result will be valid utf8 and so xml parsing will be OK.
	filename = unicode(filename[:247], "utf8", "ignore").encode("utf8", "ignore") if PY2 else filename[:247]
	if dirname is not None:
		if not dirname.startswith("/"):
			dirname = pathjoin(defaultRecordingLocation(), dirname)
	else:
		dirname = defaultRecordingLocation()
	filename = pathjoin(dirname, filename)
	path = filename
	i = 1
	while True:
		if not isfile(path + ".ts"):
			return path
		path = "%s_%03d" % (filename, i)
		i += 1


def hasHardLinks(path):  # Test if the volume containing path supports hard links.
	try:
		level, srcName = mkstemp(prefix="HardLink_", suffix=".test", dir=path, text=False)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Creating temp file!  (%s)" % (err.errno, err.strerror))
		return False
	dstName = "%s.link" % splitext(srcName)[0]
	try:
		link(srcName, dstName)
		result = True
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Creating hard link!  (%s)" % (err.errno, err.strerror))
		result = False
	try:
		remove(srcName)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Removing source file!  (%s)" % (err.errno, err.strerror))
	try:
		remove(dstName)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Removing destination file!  (%s)" % (err.errno, err.strerror))
	return result


# Returns a list of tuples containing pathname and filename matching the given pattern
# Example-pattern: match all txt-files: ".*\.txt$"
#
def crawlDirectory(directory, pattern):
	list = []
	if directory:
		expression = compile(pattern)
		for root, dirs, files in walk(directory):
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
		if isdir(dst):
			dst = pathjoin(dst, basename(src))
		f2 = open(dst, "w+b")
		while True:
			buf = f1.read(16 * 1024)
			if not buf:
				break
			f2.write(buf)
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Copying file '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
		status = -1
	if f1 is not None:
		f1.close()
	if f2 is not None:
		f2.close()
	try:
		st = stat(src)
		try:
			chmod(dst, S_IMODE(st.st_mode))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting modes from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
		try:
			utime(dst, (st.st_atime, st.st_mtime))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting times from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Obtaining stats from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
	return status


def copytree(src, dst, symlinks=False):
	names = listdir(src)
	if isdir(dst):
		dst = pathjoin(dst, basename(src))
		if not isdir(dst):
			mkdir(dst)
	else:
		makedirs(dst)
	for name in names:
		srcname = pathjoin(src, name)
		dstname = pathjoin(dst, name)
		try:
			if symlinks and islink(srcname):
				linkto = readlink(srcname)
				symlink(linkto, dstname)
			elif isdir(srcname):
				copytree(srcname, dstname, symlinks)
			else:
				copyfile(srcname, dstname)
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Copying tree '%s' to '%s'! (%s)" % (err.errno, srcname, dstname, err.strerror))
	try:
		st = stat(src)
		try:
			chmod(dst, S_IMODE(st.st_mode))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting modes from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
		try:
			utime(dst, (st.st_atime, st.st_mtime))
		except (IOError, OSError) as err:
			print("[Directories] Error %d: Setting times from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))
	except (IOError, OSError) as err:
		print("[Directories] Error %d: Obtaining stats from '%s' to '%s'! (%s)" % (err.errno, src, dst, err.strerror))


# Renames files or if source and destination are on different devices moves them in background
# input list of (source, destination)
#
def moveFiles(fileList):
	errorFlag = False
	movedList = []
	try:
		for item in fileList:
			rename(item[0], item[1])
			movedList.append(item)
	except (IOError, OSError) as err:
		if err.errno == EXDEV:  # EXDEV - Invalid cross-device link.
			print("[Directories] Warning: Cannot rename across devices, trying slower move.")
			from Tools.CopyFiles import moveFiles as extMoveFiles  # OpenViX, OpenATV, Beyonwiz
			# from Screens.CopyFiles import moveFiles as extMoveFiles  # OpenPLi
			extMoveFiles(fileList, item[0])
			print("[Directories] Moving files in background.")
		else:
			print("[Directories] Error %d: Moving file '%s' to '%s'! (%s)" % (err.errno, item[0], item[1], err.strerror))
			errorFlag = True
	if errorFlag:
		print("[Directories] Reversing renamed files due to error.")
		for item in movedList:
			try:
				rename(item[1], item[0])
			except (IOError, OSError) as err:
				print("[Directories] Error %d: Renaming '%s' to '%s'! (%s)" % (err.errno, item[1], item[0], err.strerror))
				print("[Directories] Failed to undo move:", item)


def getSize(path, pattern=".*"):
	path_size = 0
	if isdir(path):
		files = crawlDirectory(path, pattern)
		for file in files:
			filepath = pathjoin(file[0], file[1])
			path_size += getsize(filepath)
	elif isfile(path):
		path_size = getsize(path)
	return path_size


def lsof():
	lsof = []
	for pid in listdir("/proc"):
		if pid.isdigit():
			try:
				prog = readlink(pathjoin("/proc", pid, "exe"))
				dir = pathjoin("/proc", pid, "fd")
				for file in [pathjoin(dir, file) for file in listdir(dir)]:
					lsof.append((pid, prog, readlink(file)))
			except (IOError, OSError) as err:
				pass
	return lsof


def getExtension(file):
	filename, extension = splitext(file)
	return extension


def mediafilesInUse(session):
	from Components.MovieList import KNOWN_EXTENSIONS
	files = [basename(x[2]) for x in lsof() if getExtension(x[2]) in KNOWN_EXTENSIONS]
	service = session.nav.getCurrentlyPlayingServiceOrGroup()
	filename = service and service.getPath()
	if filename:
		if "://" in filename:  # When path is a stream ignore it.
			filename = None
		else:
			filename = basename(filename)
	return set([file for file in files if not(filename and file == filename and files.count(filename) < 2)])


# Prepare filenames for use in external shell processing. Filenames may
# contain spaces or other special characters.  This method adjusts the
# filename to be a safe and single entity for passing to a shell.
#
def shellquote(string):
	return "'%s'" % string.replace("'", "'\\''")


def isPluginInstalled(pluginName, pluginFile="plugin", pluginType=None):
	path, flags = defaultPaths.get(SCOPE_PLUGINS)
	for plugintype in ["Extensions", "SystemPlugins"]:
		for extension in ["c", ""]:
			if isfile(pathjoin(path, plugintype, pluginName, "%s.py%s" % (pluginFile, extension))):
				return True
	return False
