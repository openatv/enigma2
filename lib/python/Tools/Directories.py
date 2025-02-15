from errno import ENOENT, EXDEV
from os import F_OK, R_OK, W_OK, access, chmod, link, listdir, makedirs, mkdir, readlink, remove, rename, rmdir, sep, stat, statvfs, symlink, utime, walk
from os.path import basename, dirname, exists, getsize, isdir, isfile, islink, join, normpath, splitext
from re import compile
from shutil import copy2
from stat import S_IMODE
from sys import _getframe as getframe
from tempfile import mkstemp
from traceback import print_exc
from unicodedata import normalize
from xml.etree.ElementTree import Element, ParseError, fromstring, parse

from enigma import eEnv, getDesktop, eGetEnigmaDebugLvl

DEFAULT_MODULE_NAME = __name__.split(".")[-1]

forceDebug = eGetEnigmaDebugLvl() > 4
pathExists = exists  # This is needed for old plugins.

SCOPE_HOME = 0  # DEBUG: Not currently used in Enigma2.
SCOPE_LANGUAGE = 1
SCOPE_KEYMAPS = 2
SCOPE_METADIR = 3
SCOPE_SKINS = 4
SCOPE_GUISKIN = 5
SCOPE_LCDSKIN = 6
SCOPE_FONTS = 7
SCOPE_PLUGINS = 8
SCOPE_PLUGIN = 9
SCOPE_PLUGIN_ABSOLUTE = 10
SCOPE_PLUGIN_RELATIVE = 11
SCOPE_SYSETC = 12
SCOPE_TRANSPONDERDATA = 13
SCOPE_CONFIG = 14
SCOPE_PLAYLIST = 15
SCOPE_MEDIA = 16
SCOPE_HDD = 17
SCOPE_TIMESHIFT = 18
SCOPE_DEFAULTDIR = 19
SCOPE_LIBDIR = 20
SCOPE_HARDWARE = 21

# Deprecated scopes:
SCOPE_ACTIVE_LCDSKIN = SCOPE_LCDSKIN
SCOPE_ACTIVE_SKIN = SCOPE_GUISKIN
SCOPE_CURRENT_LCDSKIN = SCOPE_LCDSKIN
SCOPE_CURRENT_PLUGIN = SCOPE_PLUGIN
SCOPE_CURRENT_SKIN = SCOPE_GUISKIN
SCOPE_SKIN = SCOPE_SKINS
SCOPE_SKIN_IMAGE = SCOPE_SKINS
SCOPE_USERETC = SCOPE_HOME

PATH_CREATE = 0
PATH_DONTCREATE = 1

# ${sysconfdir} = /etc/enigma2
# ${libdir} = /usr/lib
# ${datadir} = /usr/share
#
defaultPaths = {
	SCOPE_HOME: ("", PATH_DONTCREATE),  # User home directory.
	SCOPE_LANGUAGE: (eEnv.resolve("${datadir}/enigma2/po/"), PATH_DONTCREATE),
	SCOPE_KEYMAPS: (eEnv.resolve("${datadir}/keymaps/"), PATH_CREATE),
	SCOPE_METADIR: (eEnv.resolve("${datadir}/meta/"), PATH_CREATE),
	SCOPE_SKINS: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_GUISKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
	SCOPE_LCDSKIN: (eEnv.resolve("${datadir}/enigma2/display/"), PATH_DONTCREATE),
	SCOPE_FONTS: (eEnv.resolve("${datadir}/fonts/"), PATH_DONTCREATE),
	SCOPE_PLUGINS: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_PLUGIN: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),
	SCOPE_PLUGIN_ABSOLUTE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_PLUGIN_RELATIVE: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_DONTCREATE),
	SCOPE_SYSETC: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_TRANSPONDERDATA: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
	SCOPE_CONFIG: (eEnv.resolve("${sysconfdir}/enigma2/"), PATH_CREATE),
	SCOPE_PLAYLIST: (eEnv.resolve("${sysconfdir}/enigma2/playlist/"), PATH_CREATE),
	SCOPE_MEDIA: ("/media/", PATH_DONTCREATE),
	SCOPE_HDD: ("/media/hdd/movie/", PATH_DONTCREATE),
	SCOPE_TIMESHIFT: ("/media/hdd/timeshift/", PATH_DONTCREATE),
	SCOPE_DEFAULTDIR: (eEnv.resolve("${datadir}/enigma2/defaults/"), PATH_CREATE),
	SCOPE_LIBDIR: (eEnv.resolve("${libdir}/"), PATH_DONTCREATE),
	SCOPE_HARDWARE: (eEnv.resolve("${datadir}/enigma2/hardware/"), PATH_CREATE)
}

scopeConfig = defaultPaths[SCOPE_CONFIG][0]
scopeGUISkin = defaultPaths[SCOPE_GUISKIN][0]
scopeLCDSkin = defaultPaths[SCOPE_LCDSKIN][0]
scopeFonts = defaultPaths[SCOPE_FONTS][0]
scopePlugins = defaultPaths[SCOPE_PLUGINS][0]


def InitDefaultPaths():
	resolveFilename(SCOPE_CONFIG)


skinResolveList = []
lcdskinResolveList = []
fontsResolveList = []


def clearResolveLists():
	global skinResolveList, lcdskinResolveList, fontsResolveList
	skinResolveList = []
	lcdskinResolveList = []
	fontsResolveList = []


def resolveFilename(scope, base="", path_prefix=None):
	def addIfExists(paths):
		return [path for path in paths if isdir(path)]

	def checkPaths(resolveList, base):
		# Disable png / svg interchange code for now.  SVG files are very CPU intensive.
		# baseList = [base]
		# if base.endswith(".png"):
		# 	baseList.append(f"{base[:-3]}svg")
		# elif base.endswith(".svg"):
		# 	baseList.append(f"{base[:-3]}png")
		path = base
		for item in resolveList:
			# for base in baseList:
			file = join(item, base)
			if exists(file):
				path = file
				break
		return path

	if str(base).startswith(f"~{sep}"):  # You can only use the ~/ if we have a prefix directory.
		if path_prefix:
			base = join(path_prefix, base[2:])
		else:
			print(f"[Directories] Warning: resolveFilename called with base starting with '~{sep}' but 'path_prefix' is None!")
	if str(base).startswith(sep):  # Don't further resolve absolute paths.
		return normpath(base)
	if scope not in defaultPaths:  # If an invalid scope is specified log an error and return None.
		print(f"[Directories] Error: Invalid scope={scope} provided to resolveFilename!")
		return None
	path, flag = defaultPaths[scope]  # Ensure that the defaultPath directory that should exist for this scope does exist.
	if flag == PATH_CREATE and not exists(path):
		try:
			makedirs(path)
		except OSError as err:
			print(f"[Directories] Error {err.errno}: Couldn't create directory '{path}'!  ({err.strerror})")
			return None
	suffix = None  # Remove any suffix data and restore it at the end.
	data = base.split(":", 1)
	if len(data) > 1:
		base = data[0]
		suffix = data[1]
	path = base
	if base == "":  # If base is "" then set path to the scope.  Otherwise use the scope to resolve the base filename.
		path, flags = defaultPaths.get(scope)
		if scope == SCOPE_GUISKIN:  # If the scope is SCOPE_GUISKIN append the current skin to the scope path.
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
			skin = dirname(config.skin.primary_skin.value)
			path = join(path, skin)
		elif scope in (SCOPE_PLUGIN_ABSOLUTE, SCOPE_PLUGIN_RELATIVE):
			callingCode = normpath(getframe(1).f_code.co_filename)
			plugins = normpath(scopePlugins)
			path = None
			if comparePaths(plugins, callingCode):
				pluginCode = callingCode[len(plugins) + 1:].split(sep)
				if len(pluginCode) > 2:
					path = join(plugins, pluginCode[0], pluginCode[1])
	elif scope == SCOPE_GUISKIN:
		global skinResolveList
		if not skinResolveList:
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
			skin = dirname(config.skin.primary_skin.value)
			skinResolveList = addIfExists([
				join(scopeConfig, skin),
				join(scopeConfig, "skin_common"),
				join(scopeGUISkin, skin),
				join(scopeGUISkin, f"skin_fallback_{getDesktop(0).size().height()}"),
				join(scopeGUISkin, "skin_default"),
				scopeGUISkin  # Deprecate top level of SCOPE_GUISKIN directory to allow a clean up.
			])
		if base.endswith(".xml"):  # If the base filename ends with ".xml" then add scopeConfig to the resolveList for support of old skins.
			resolveList = skinResolveList[:]
			resolveList.insert(2, scopeConfig)
			path = checkPaths(resolveList, base)
		else:
			path = checkPaths(skinResolveList, base)
	elif scope == SCOPE_LCDSKIN:
		global lcdskinResolveList
		if not lcdskinResolveList:
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
			skin = dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else ""
			lcdskinResolveList = addIfExists([
				join(scopeConfig, "display", skin),
				join(scopeConfig, "display", "skin_common"),
				join(scopeLCDSkin, skin),
				join(scopeLCDSkin, f"skin_fallback_{getDesktop(1).size().height()}"),
				join(scopeLCDSkin, "skin_default"),
				scopeLCDSkin  # Deprecate top level of SCOPE_LCDSKIN directory to allow a clean up.
			])
		path = checkPaths(lcdskinResolveList, base)
	elif scope == SCOPE_FONTS:
		global fontsResolveList
		if not fontsResolveList:
			from Components.config import config  # This import must be here as this module finds the config file as part of the config initialization.
			skin = dirname(config.skin.primary_skin.value)
			display = dirname(config.skin.display_skin.value) if hasattr(config.skin, "display_skin") else None
			resolveList = [
				join(scopeConfig, "fonts"),
				join(scopeConfig, skin, "fonts"),
				join(scopeConfig, skin)
			]
			if display:
				resolveList.append(join(scopeConfig, "display", display, "fonts"))
				resolveList.append(join(scopeConfig, "display", display))
			resolveList.append(join(scopeConfig, "skin_common", "fonts"))
			resolveList.append(join(scopeConfig, "skin_common"))
			resolveList.append(join(scopeGUISkin, skin, "fonts"))
			resolveList.append(join(scopeGUISkin, skin))
			resolveList.append(join(scopeGUISkin, "skin_default", "fonts"))
			resolveList.append(join(scopeGUISkin, "skin_default"))
			if display:
				resolveList.append(join(scopeLCDSkin, display, "fonts"))
				resolveList.append(join(scopeLCDSkin, display))
			resolveList.append(join(scopeLCDSkin, "skin_default", "fonts"))
			resolveList.append(join(scopeLCDSkin, "skin_default"))
			resolveList.append(scopeFonts)
			fontsResolveList = addIfExists(resolveList)
		path = checkPaths(fontsResolveList, base)
	elif scope == SCOPE_PLUGIN:
		file = join(scopePlugins, base)
		if exists(file):
			path = file
	elif scope in (SCOPE_PLUGIN_ABSOLUTE, SCOPE_PLUGIN_RELATIVE):
		callingCode = normpath(getframe(1).f_code.co_filename)
		plugins = normpath(scopePlugins)
		path = None
		if comparePaths(plugins, callingCode):
			pluginCode = callingCode[len(plugins) + 1:].split(sep)
			if len(pluginCode) > 2:
				path = join(plugins, pluginCode[0], pluginCode[1], base)
	else:
		path, flags = defaultPaths.get(scope)
		path = join(path, base)
	path = normpath(path)
	if isdir(path) and not path.endswith(sep):  # If the path is a directory then ensure that it ends with a "/".
		path = join(path, "")
	if scope == SCOPE_PLUGIN_RELATIVE:
		path = path[len(plugins) + 1:]
	if suffix is not None:  # If a suffix was supplier restore it.
		path = f"{path}:{suffix}"
	return path


def fileReadLine(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	line = None
	try:
		with open(filename) as fd:
			line = fd.read().strip().replace("\0", "")
		msg = "Read"
	except OSError as err:
		if err.errno != ENOENT:  # No such file or directory.
			print(f"[{source}] Error {err.errno}: Unable to read a line from file '{filename}'!  ({err.strerror})")
		line = default
		msg = "Default"
	if debug or forceDebug:
		print(f"[{source}] Line {getframe(1).f_lineno}: {msg} '{line}' from file '{filename}'.")
	return line


def fileWriteLine(filename, line, source=DEFAULT_MODULE_NAME, debug=False):
	try:
		with open(filename, "w") as fd:
			fd.write(str(line))
		msg = "Wrote"
		result = 1
	except OSError as err:
		print(f"[{source}] Error {err.errno}: Unable to write a line to file '{filename}'!  ({err.strerror})")
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print(f"[{source}] Line {getframe(1).f_lineno}: {msg} '{line}' to file '{filename}'.")
	return result


def fileUpdateLine(filename, conditionValue, replacementValue, create=False, source=DEFAULT_MODULE_NAME, debug=False):
	line = fileReadLine(filename, default="", source=source, debug=debug)
	create = False if conditionValue and not line.startswith(conditionValue) else create
	return fileWriteLine(filename, replacementValue, source=source, debug=debug) if create or (conditionValue and line.startswith(conditionValue)) else 0


def fileReadLines(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	lines = None
	try:
		with open(filename) as fd:
			lines = fd.read().splitlines()
		msg = "Read"
	except OSError as err:
		if err.errno != ENOENT:  # No such file or directory.
			print(f"[{source}] Error {err.errno}: Unable to read lines from file '{filename}'!  ({err.strerror})")
		lines = default
		msg = "Default"
	if debug or forceDebug:
		length = len(lines) if lines else 0
		print(f"[{source}] Line {getframe(1).f_lineno}: {msg} {length} lines from file '{filename}'.")
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
	except OSError as err:
		print(f"[{source}] Error {err.errno}: Unable to write {len(lines)} lines to file '{filename}'!  ({err.strerror})")
		msg = "Failed to write"
		result = 0
	if debug or forceDebug:
		print(f"[{source}] Line {getframe(1).f_lineno}: {msg} {len(lines)} lines to file '{filename}'.")
	return result


def fileReadXML(filename, default=None, source=DEFAULT_MODULE_NAME, debug=False):
	dom = None
	try:
		with open(filename) as fd:  # This open gets around a possible file handle leak in Python's XML parser.
			try:
				dom = parse(fd).getroot()
				msg = "Read"
			except ParseError as err:
				fd.seek(0)
				content = fd.readlines()
				line, column = err.position
				print(f"[{source}] XML Parse Error: '{err}' in '{filename}'!")
				data = content[line - 1].replace("\t", " ").rstrip()
				print(f"[{source}] XML Parse Error: '{data}'")
				print(f"[{source}] XML Parse Error: '{'-' * column}^{' ' * (len(data) - column - 1)}'")
			except Exception as err:
				print(f"[{source}] Error: Unable to parse data in '{filename}' - '{err}'!")
	except OSError as err:
		if err.errno == ENOENT:  # No such file or directory.
			print(f"[{source}] Warning: File '{filename}' does not exist!")
		else:
			print("[%s] Error %d: Opening file '%s'!  (%s)" % (source, err.errno, filename, err.strerror))
	except Exception as err:
		print(f"[{source}] Error: Unexpected error opening/parsing file '{filename}'!  ({err})")
		print_exc()
	if dom is None:
		if default and isinstance(default, str):
			dom = fromstring(default)
			msg = "Default (XML)"
		elif default and isinstance(default, Element):
			dom = default
			msg = "Default (DOM)"
		else:
			msg = "Failed to read"
	if debug or forceDebug:
		print(f"[{source}] Line {getframe(1).f_lineno}: {msg} from XML file '{filename}'.")
	return dom


def defaultRecordingLocation(candidate=None):
	if candidate and exists(candidate):
		return candidate
	try:
		path = readlink("/hdd")  # First, try whatever /hdd points to, or /media/hdd.
	except OSError as err:
		path = "/media/hdd"
	if not exists(path):  # Find the largest local disk.
		from Components import Harddisk
		mounts = [mount for mount in Harddisk.getProcMounts() if mount[1].startswith("/media/")]
		path = bestRecordingLocation([mount for mount in mounts if mount[0].startswith("/dev/")])  # Search local devices first, use the larger one.
		if not path:  # If we haven't found a viable candidate yet, try remote mounts.
			path = bestRecordingLocation([mount for mount in mounts if not mount[0].startswith("/dev/")])
	if path:
		movie = join(path, "movie", "")  # If there's a movie subdir, we'd probably want to use that (directories need to end in sep).
		if isdir(movie):
			path = movie
	return path


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
		except OSError as err:
			print(f"[Directories] Error {err.errno}: Couldn't get free space for '{candidate[1]}'!  ({err.strerror})")
	return path


def getRecordingFilename(basename, dirname=None):
	nonAllowedCharacters = "/.\\:*?<>|\""  # Filter out non-allowed characters.
	basename = basename.replace("\x86", "").replace("\x87", "")
	filename = ""
	for character in basename:
		if character in nonAllowedCharacters or ord(character) < 32:
			character = "_"
		filename += character
	# Max filename length for ext4 is 255 (minus 12 characters for .stream.meta)
	# but must not truncate in the middle of a multi-byte UTF8 character!
	# So convert the truncation to Unicode and back, ignoring errors, the
	# result will be valid UTF8 and so XML parsing will be OK.
	filename = filename[:243]
	if dirname is None:
		dirname = defaultRecordingLocation()
	else:
		if not dirname.startswith(sep):
			dirname = join(defaultRecordingLocation(), dirname)
	filename = join(dirname, filename)
	next = 0
	path = filename
	while isfile(f"{path}.ts"):
		next += 1
		path = "%s_%03d" % (filename, next)
	return path


def copyFile(src, dst):
	try:
		copy2(src, dst)
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Copying file '{src}' to '{dst}'!  ({err.strerror})")
		return -1
	return 0
	# if isdir(dst):
	# 	dst = join(dst, basename(src))
	# try:
	# 	with open(src, "rb") as fd1:
	# 		with open(dst, "w+b") as fd2:
	# 			while True:
	# 				buf = fd1.read(16 * 1024)
	# 				if not buf:
	# 					break
	# 				fd2.write(buf)
	# 	try:
	# 		status = stat(src)
	# 		try:
	# 			chmod(dst, S_IMODE(status.st_mode))
	# 		except OSError as err:
	# 			print("[Directories] Error %d: Setting modes from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 		try:
	# 			utime(dst, (status.st_atime, status.st_mtime))
	# 		except OSError as err:
	# 			print("[Directories] Error %d: Setting times from '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 	except OSError as err:
	# 		print("[Directories] Error %d: Obtaining status from '%s'!  (%s)" % (err.errno, src, err.strerror))
	# except OSError as err:
	# 	print("[Directories] Error %d: Copying file '%s' to '%s'!  (%s)" % (err.errno, src, dst, err.strerror))
	# 	return -1
	# return 0


def copyfile(src, dst):
	return copyFile(src, dst)


def copyTree(src, dst, symlinks=False):
	names = listdir(src)
	if isdir(dst):
		dst = join(dst, basename(src))
		if not isdir(dst):
			mkdir(dst)
	else:
		makedirs(dst)
	for name in names:
		srcName = join(src, name)
		dstName = join(dst, name)
		try:
			if symlinks and islink(srcName):
				linkTo = readlink(srcName)
				symlink(linkTo, dstName)
			elif isdir(srcName):
				copytree(srcName, dstName, symlinks)
			else:
				copyfile(srcName, dstName)
		except OSError as err:
			print(f"[Directories] Error {err.errno}: Copying tree '{srcName}' to '{dstName}'!  ({err.strerror})")
	try:
		status = stat(src)
		try:
			chmod(dst, S_IMODE(status.st_mode))
		except OSError as err:
			print(f"[Directories] Error {err.errno}: Setting modes from '{src}' to '{dst}'!  ({err.strerror})")
		try:
			utime(dst, (status.st_atime, status.st_mtime))
		except OSError as err:
			print(f"[Directories] Error {err.errno}: Setting times from '{src}' to '{dst}'!  ({err.strerror})")
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Obtaining stats from '{src}' to '{dst}'!  ({err.strerror})")


def copytree(src, dst, symlinks=False):
	return copyTree(src, dst, symlinks=symlinks)


# Renames files or if source and destination are on different devices moves them in the background.
# The input is a list of (source, destination).
#
def moveFiles(fileList):
	errorFlag = False
	movedList = []
	try:
		for item in fileList:
			rename(item[0], item[1])
			movedList.append(item)
	except OSError as err:
		if err.errno == EXDEV:  # Invalid cross-device link.
			print("[Directories] Warning: Cannot rename across devices, trying slower move.")
			from Tools.CopyFiles import moveFiles as extMoveFiles  # OpenViX, OpenATV, Beyonwiz
			# from Screens.CopyFiles import moveFiles as extMoveFiles  # OpenPLi / OV
			extMoveFiles(fileList, item[0])
			print("[Directories] Moving files in background.")
		else:
			print(f"[Directories] Error {err.errno}: Moving file '{item[0]}' to '{item[1]}'!  ({err.strerror})")
			errorFlag = True
	if errorFlag:
		print("[Directories] Reversing renamed files due to error.")
		for item in movedList:
			try:
				rename(item[1], item[0])
			except OSError as err:
				print(f"[Directories] Error {err.errno}: Renaming '{item[1]}' to '{item[0]}'!  ({err.strerror})")
				print(f"[Directories] Note: Failed to undo move of '{item[0]}' to '{item[1]}'!")


def comparePaths(leftPath, rightPath):
	print(f"[Directories] comparePaths DEBUG: left='{leftPath}', right='{rightPath}'.")
	if leftPath.endswith(sep):
		leftPath = leftPath[:-1]
	left = leftPath.split(sep)
	right = rightPath.split(sep)
	for index, segment in enumerate(left):
		if left[index] != right[index]:
			return False
	return True


# Returns a list of tuples containing pathname and filename matching the given pattern.
# Example-pattern: match all txt-files: ".*\.txt$"
#
def crawlDirectory(directory, pattern):
	fileList = []
	if directory:
		expression = compile(pattern)
		for root, dirs, files in walk(directory):
			for file in files:
				if expression.match(file) is not None:
					fileList.append((root, file))
	return fileList


def createDir(path, makeParents=False):
	try:
		if makeParents:
			makedirs(path)
		else:
			mkdir(path)
		return 1
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Couldn't create directory '{path}'!  ({err.strerror})")
	return 0


def renameDir(oldPath, newPath):
	try:
		rename(oldPath, newPath)
		return 1
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Couldn't rename directory '{oldPath}' to '{newPath}'!  ({err.strerror})")
	return 0


def removeDir(path):
	try:
		rmdir(path)
		return 1
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Couldn't remove directory '{path}'!  ({err.strerror})")
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
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Couldn't determine file '{file}' access mode!  ({err.strerror})")
	return result


def fileCheck(file, mode="r"):
	return fileAccess(file, mode) and file


def fileExists(file, mode="r"):
	return fileAccess(file, mode) and file


def fileContains(file, content, mode="r"):
	result = False
	if fileExists(file, mode):
		with open(file, mode) as fd:
			text = fd.read()
		if content in text:
			result = True
	return result


def fileHas(file, content, mode="r"):
	return fileContains(file, content, mode)


def hasHardLinks(path):  # Test if the volume containing path supports hard links.
	try:
		fd, srcName = mkstemp(prefix="HardLink_", suffix=".test", dir=path, text=False)
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Creating temp file!  ({err.strerror})")
		return False
	dstName = f"{splitext(srcName)[0]}.link"
	try:
		link(srcName, dstName)
		result = True
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Creating hard link!  ({err.strerror})")
		result = False
	try:
		remove(srcName)
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Removing source file!  ({err.strerror})")
	try:
		remove(dstName)
	except OSError as err:
		print(f"[Directories] Error {err.errno}: Removing destination file!  ({err.strerror})")
	return result


def getSize(path, pattern=".*"):
	pathSize = 0
	if isdir(path):
		for file in crawlDirectory(path, pattern):
			pathSize += getsize(join(file[0], file[1]))
	elif isfile(path):
		pathSize = getsize(path)
	return pathSize


# Prepare filenames for use in external shell processing. Filenames may
# contain spaces or other special characters.  This method adjusts the
# filename to be a safe and single entity for passing to a shell.
#
def shellQuote(string):
	return "'%s'" % string.replace("'", "'\\''")


def shellquote(string):
	return shellQuote(string)


def lsof():  # List of open files.
	lsof = []
	for pid in listdir("/proc"):
		if pid.isdigit():
			try:
				program = readlink(join("/proc", pid, "exe"))
				directory = join("/proc", pid, "fd")
				for file in [join(directory, x) for x in listdir(directory)]:
					lsof.append((pid, program, readlink(file)))
			except OSError as err:
				pass
	return lsof


def getExtension(file):
	filename, extension = splitext(file)
	return extension


def mediaFilesInUse(session):
	from Components.MovieList import KNOWN_EXTENSIONS
	files = [basename(x[2]) for x in lsof() if getExtension(x[2]) in KNOWN_EXTENSIONS]
	service = session.nav.getCurrentlyPlayingServiceOrGroup()
	filename = service and service.getPath()
	if filename:
		filename = None if "://" in filename else basename(filename)  # When path is a stream ignore it.
	return set([file for file in files if not (filename and file == filename and files.count(filename) < 2)])


def isPluginInstalled(pluginName, pluginFile="plugin", pluginType=None):
	types = ["Extensions", "SystemPlugins"]
	if pluginType:
		types = [pluginType]
	for type in types:
		for extension in ["c", ""]:
			if isfile(join(scopePlugins, type, pluginName, f"{pluginFile}.py{extension}")):
				return True
	return False


def sanitizeFilename(filename, maxlen=255):  # 255 is max length in ext4 (and most other file systems)
	"""Return a fairly safe version of the filename.

	We don't limit ourselves to ascii, because we want to keep municipality
	names, etc, but we do want to get rid of anything potentially harmful,
	and make sure we do not exceed filename length limits.
	Hence a less safe blacklist, rather than a whitelist.
	"""
	blacklist = ("\\", "/", ":", "*", "?", "\"", "<", ">", "|", "\0")
	reserved = (
		"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
		"COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
		"LPT6", "LPT7", "LPT8", "LPT9",
	)  # Reserved words on Windows
	# Remove any blacklisted chars. Remove all characters below code point 32. Normalize. Strip.
	filename = normalize("NFKD", "".join(c for c in filename if c not in blacklist and ord(c) > 31)).strip()
	if all([x == "." for x in filename]) or filename in reserved:  # if filename is a string of dots
		filename = f"__{filename}"
	# Most Unix file systems typically allow filenames of up to 255 bytes.
	# However, the actual number of characters allowed can vary due to the
	# representation of Unicode characters. Therefore length checks must
	# be done in bytes, not Unicode.
	#
	# Also we cannot leave the byte truncate in the middle of a multi-byte
	# UTF8 character! So, convert to bytes, truncate then get back to Unicode,
	# ignoring errors along the way, the result will be valid Unicode.
	# Prioritize maintaining the complete extension if possible.
	# Any truncation of root or ext will be done at the end of the string
	root, ext = splitext(filename.encode(encoding="UTF-8", errors="ignore"))
	if len(ext) > maxlen - (1 if root else 0):  # leave at least one char for root if root
		ext = ext[:maxlen - (1 if root else 0)]
	# convert back to Unicode, ignoring any incomplete UTF8 multi-byte chars
	filename = root[:maxlen - len(ext)].decode(encoding="UTF-8", errors="ignore") + ext.decode(encoding="UTF-8", errors="ignore")
	filename = filename.rstrip(". ")  # Windows does not allow these at end
	if not filename:
		filename = "__"
	return filename
