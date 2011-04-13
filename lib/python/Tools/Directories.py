# -*- coding: utf-8 -*-

from os import path as os_path, mkdir, rmdir, system, walk, stat as os_stat, listdir, readlink, makedirs, error as os_error, symlink, access, F_OK, R_OK, W_OK
from stat import S_IMODE
from re import compile
from enigma import eEnv

try:
	from os import chmod
	have_chmod = True
except:
	have_chmod = False

try:
	from os import utime
	have_utime = True
except:
	have_utime = False

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
SCOPE_PLAYLIST = 11
SCOPE_CURRENT_SKIN = 12
SCOPE_DEFAULTDIR = 13
SCOPE_DEFAULTPARTITION = 14
SCOPE_DEFAULTPARTITIONMOUNTDIR = 15
SCOPE_METADIR = 16
SCOPE_CURRENT_PLUGIN = 17

PATH_CREATE = 0
PATH_DONTCREATE = 1
PATH_FALLBACK = 2
defaultPaths = {
		SCOPE_TRANSPONDERDATA: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
		SCOPE_SYSETC: (eEnv.resolve("${sysconfdir}/"), PATH_DONTCREATE),
		SCOPE_FONTS: (eEnv.resolve("${datadir}/fonts/"), PATH_DONTCREATE),
		SCOPE_CONFIG: (eEnv.resolve("${sysconfdir}/enigma2/"), PATH_CREATE),
		SCOPE_PLUGINS: (eEnv.resolve("${libdir}/enigma2/python/Plugins/"), PATH_CREATE),

		SCOPE_LANGUAGE: (eEnv.resolve("${datadir}/enigma2/po/"), PATH_DONTCREATE),

		SCOPE_SKIN: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
		SCOPE_SKIN_IMAGE: (eEnv.resolve("${datadir}/enigma2/"), PATH_DONTCREATE),
		SCOPE_HDD: ("/hdd/movie/", PATH_DONTCREATE),
		SCOPE_MEDIA: ("/media/", PATH_DONTCREATE),
		SCOPE_PLAYLIST: (eEnv.resolve("${sysconfdir}/enigma2/playlist/"), PATH_CREATE),
		
		SCOPE_USERETC: ("", PATH_DONTCREATE), # user home directory
		
		SCOPE_DEFAULTDIR: (eEnv.resolve("${datadir}/enigma2/defaults/"), PATH_CREATE),
		SCOPE_DEFAULTPARTITION: ("/dev/mtdblock6", PATH_DONTCREATE),
		SCOPE_DEFAULTPARTITIONMOUNTDIR: (eEnv.resolve("${datadir}/enigma2/dealer"), PATH_CREATE),
		SCOPE_METADIR: (eEnv.resolve("${datadir}/meta"), PATH_CREATE),
	}

FILE_COPY = 0 # copy files from fallback dir to the basedir
FILE_MOVE = 1 # move files
PATH_COPY = 2 # copy the complete fallback dir to the basedir
PATH_MOVE = 3 # move the fallback dir to the basedir (can be used for changes in paths)
fallbackPaths = {
		SCOPE_CONFIG: [("/home/root/", FILE_MOVE),
					   (eEnv.resolve("${datadir}/enigma2/defaults/"), FILE_COPY)],
		SCOPE_HDD: [("/hdd/movies", PATH_MOVE)]
	}

def resolveFilename(scope, base = "", path_prefix = None):
	if base[0:2] == "~/":
		# you can only use the ~/ if we have a prefix directory
		assert path_prefix is not None
		base = os_path.join(path_prefix, base[2:])

	# don't resolve absolute paths
	if base[0:1] == '/':
		return base

	if scope == SCOPE_CURRENT_SKIN:
		from Components.config import config
		tmp = defaultPaths[SCOPE_SKIN]
		pos = config.skin.primary_skin.value.rfind('/')
		if pos != -1:
			#if basefile is not available use default skin path as fallback
			tmpfile = tmp[0]+config.skin.primary_skin.value[:pos+1] + base
			if fileExists(tmpfile):
				path = tmp[0]+config.skin.primary_skin.value[:pos+1]
			else:
				path = tmp[0]
		else:
			path = tmp[0]

	elif scope == SCOPE_CURRENT_PLUGIN:
		tmp = defaultPaths[SCOPE_PLUGINS]
		from Components.config import config
		skintmp = defaultPaths[SCOPE_SKIN]
		pos = config.skin.primary_skin.value.rfind('/')
		if pos != -1:
			#if basefile is not available inside current skin path, use the original provided file as fallback
			skintmpfile = skintmp[0]+config.skin.primary_skin.value[:pos+1] + base
			if fileExists(skintmpfile):
				path = skintmp[0]+config.skin.primary_skin.value[:pos+1]
			else:
				path = tmp[0]
		else:
			path = tmp[0]
	else:
		tmp = defaultPaths[scope]
		path = tmp[0]

	flags = tmp[1]

	if flags == PATH_CREATE:
		if not pathExists(path):
			try:
				mkdir(path)
			except OSError:
				print "resolveFilename: Couldn't create %s" % path
				return None

	fallbackPath = fallbackPaths.get(scope)

	if fallbackPath and not fileExists(path + base):
		for x in fallbackPath:
			if x[1] == FILE_COPY:
				if fileExists(x[0] + base):
					system("cp " + x[0] + base + " " + path + base)
					break
			elif x[1] == FILE_MOVE:
				if fileExists(x[0] + base):
					system("mv " + x[0] + base + " " + path + base)
					break
			elif x[1] == PATH_COPY:
				if pathExists(x[0]):
					if not pathExists(defaultPaths[scope][0]):
						mkdir(path)
					system("cp -a " + x[0] + "* " + path)
					break
			elif x[1] == PATH_MOVE:
				if pathExists(x[0]):
					system("mv " + x[0] + " " + path)
					break

	# FIXME: we also have to handle DATADIR etc. here.
	return path + base
	# this is only the BASE - an extension must be added later.

def pathExists(path):
	return os_path.exists(path)

def isMount(path):
	return os_path.ismount(path)

def createDir(path, makeParents = False):
	try:
		if makeParents:
			makedirs(path)
		else:
			mkdir(path)
	except:
		ret = 0
	else:
		ret = 1
	return ret

def removeDir(path):
	try:
		rmdir(path)
	except:
		ret = 0
	else:
		ret = 1
	return ret

def fileExists(f, mode='r'):
	if mode == 'r':
		acc_mode = R_OK
	elif mode == 'w':
		acc_mode = W_OK
	else:
		acc_mode = F_OK
	return access(f, acc_mode)

def getRecordingFilename(basename, dirname = None):
	# filter out non-allowed characters
	non_allowed_characters = "/.\\:*?<>|\""
	filename = ""
	
	basename = basename.replace('\xc2\x86', '').replace('\xc2\x87', '')
	
	for c in basename:
		if c in non_allowed_characters or ord(c) < 32:
			c = "_"
		filename += c

	if dirname is not None:
		filename = ''.join((dirname, filename))

	while len(filename) > 240:
		filename = filename.decode('UTF-8')
		filename = filename[:-1]
		filename = filename.encode('UTF-8')

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
	resolveFilename(SCOPE_CONFIG, "userbouquet.favourites.radio")
	resolveFilename(SCOPE_CONFIG, "bouquets.radio")

# returns a list of tuples containing pathname and filename matching the given pattern
# example-pattern: match all txt-files: ".*\.txt$"
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
	try:
		f1 = open(src, "rb")
		if os_path.isdir(dst):
			dst = os_path.join(dst, os_path.basename(src))
		f2 = open(dst, "w+b")
		while True:
			buf = f1.read(16*1024)
			if not buf:
				break
			f2.write(buf)
		st = os_stat(src)
		mode = S_IMODE(st.st_mode)
		if have_chmod:
			chmod(dst, mode)
		if have_utime:
			utime(dst, (st.st_atime, st.st_mtime))
	except:
		print "copy", src, "to", dst, "failed!"
		return -1
	return 0

def copytree(src, dst, symlinks=False):
	names = listdir(src)
	if os_path.isdir(dst):
		dst = os_path.join(dst, os_path.basename(src))
		if not os_path.isdir(dst):
			mkdir(dst)
	else:
		makedirs(dst)
	for name in names:
		srcname = os_path.join(src, name)
		dstname = os_path.join(dst, name)
		try:
			if symlinks and os_path.islink(srcname):
				linkto = readlink(srcname)
				symlink(linkto, dstname)
			elif os_path.isdir(srcname):
				copytree(srcname, dstname, symlinks)
			else:
				copyfile(srcname, dstname)
		except:
			print "dont copy srcname (no file or link or folder)"
	try:
		st = os_stat(src)
		mode = S_IMODE(st.st_mode)
		if have_chmod:
			chmod(dst, mode)
		if have_utime:
			utime(dst, (st.st_atime, st.st_mtime))
	except:
		print "copy stats for", src, "failed!"

def getSize(path, pattern=".*"):
	path_size = 0
	if os_path.isdir(path):
		files = crawlDirectory(path, pattern)
		for file in files:
			filepath = os_path.join(file[0], file[1])
			path_size += os_path.getsize(filepath)
	elif os_path.isfile(path):
		path_size = os_path.getsize(path)
	return path_size
