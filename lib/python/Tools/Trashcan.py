from errno import EINVAL, ENOSYS, ENOTEMPTY, ENOTSUP, EXDEV
from json import dumps, loads
from os import O_RDONLY, close, fsencode, fsync, link, mkdir, name as osName, open as openDescriptor, rename, replace, rmdir, stat, statvfs, unlink, walk
from os.path import basename, dirname, getsize, isabs, isdir, islink, join, lexists, normpath, realpath, relpath
from threading import RLock
from time import time
from uuid import uuid4

from enigma import eBackgroundFileEraser, eLabel, iRecordableService

from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Task import Job, PythonTask, job_manager as jobManager
from Components.VariableText import VariableText
from Tools.Conversions import scaleNumber
from Tools.Directories import fileReadLines

MODULE_NAME = __name__.split(".")[-1]
TRASHCAN = ".Trash"  # This should this be ".Trashcan" to be consistent with the module.


class TrashcanStorage:
	UNSUITABLE = {"autofs", "rootfs", "tmpfs", "ramfs", "jffs2", "ubifs", "squashfs", "proc", "sysfs", "devtmpfs", "overlay"}
	NETWORK = {"nfs", "nfs4", "cifs", "smb3", "ceph", "9p"}

	def mounts(self):
		mounts = []
		for line in fileReadLines("/proc/self/mountinfo", default=[], source=MODULE_NAME):
			fields = line.split()
			try:
				separator = fields.index("-")
				path = fields[4]
				for escaped, value in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
					path = path.replace(escaped, value)
				mounts.append((fields[0], normpath(path), fields[separator + 1], fields[5].split(",")))
			except (IndexError, ValueError):
				continue
		return mounts

	def mount(self, path, mounts):
		# A mounted share can cover its autofs trigger at the very same path.
		return max((x for x in reversed(mounts) if path == x[1] or path.startswith(join(x[1], ""))), key=lambda x: len(x[1]), default=None)

	def usable(self, mount):
		return mount is not None and mount[1] != "/" and mount[2] not in self.UNSUITABLE and "ro" not in mount[3]

	def location(self, path, mounts):
		path = realpath(path)
		mount = self.mount(path, mounts)
		if not self.usable(mount):
			return ""
		movie = join(mount[1], "movie")
		trashcan = join(movie if path == movie or path.startswith(join(movie, "")) else mount[1], TRASHCAN)
		return trashcan if self.mount(trashcan, mounts) == mount else ""

	def validate(self, source, target, checkDirectory=True):
		mounts = self.mounts()
		source = realpath(source)
		target = join(realpath(dirname(target)), basename(target))
		sourceMount = self.mount(source, mounts)
		targetMount = self.mount(target, mounts)
		if not self.usable(sourceMount) or sourceMount != targetMount or stat(source).st_dev != stat(dirname(target)).st_dev:
			raise OSError(EXDEV, _("The trashcan and the movie must be on the same mounted filesystem. No files were copied."))
		if checkDirectory and isdir(source) and (target.startswith(join(source, "")) or any(x[1] == source or x[1].startswith(join(source, "")) for x in mounts)):
			raise ValueError(_("A mount point or a folder containing mounted filesystems cannot be moved to the trashcan."))

	def move(self, source, target):
		# renameat2 avoids overwriting a movie created by another receiver after the preflight.
		if osName == "posix":
			# Load ctypes only for a file operation, not during normal GUI startup.
			from ctypes import CDLL, c_char_p, c_int, c_uint, get_errno
			library = CDLL(None, use_errno=True)
			renameNoReplace = getattr(library, "renameat2", None)
			if renameNoReplace is not None:
				renameNoReplace.argtypes = (c_int, c_char_p, c_int, c_char_p, c_uint)
				renameNoReplace.restype = c_int
				if renameNoReplace(-100, fsencode(source), -100, fsencode(target), 1) == 0:
					return
				error = get_errno()
				if error not in (EINVAL, ENOSYS, ENOTSUP):
					raise OSError(error, _("Unable to move the movie without overwriting existing files."))
			# Older kernels may lack renameat2. Reserve an empty directory exclusively;
			# POSIX rename cannot replace a populated directory. Files use hard links.
			if isdir(source):
				mkdir(target)
				try:
					rename(source, target)
				except OSError:
					rmdir(target)
					raise
				return
			link(source, target)
			try:
				unlink(source)
			except OSError:
				unlink(target)
				raise
		else:
			rename(source, target)  # Windows rename also refuses an existing destination.

	def walk(self, folder, mounts):
		mount = self.mount(realpath(folder), mounts)
		if not self.usable(mount) or islink(folder):
			return
		for root, dirs, files in walk(folder):
			dirs[:] = [x for x in dirs if not islink(join(root, x)) and self.mount(join(root, x), mounts) == mount]
			yield root, dirs, [x for x in files if not islink(join(root, x))]


trashcanStorage = TrashcanStorage()


class TrashcanIndex:
	FILE_NAME = ".trashinfo"
	MAX_SIZE = 4 * 1024 * 1024

	def __init__(self):
		self.lock = RLock()

	def directory(self, path):
		folder = dirname(normpath(path))
		while folder != dirname(folder):
			if basename(folder) == TRASHCAN:
				return folder
			folder = dirname(folder)
		return None

	def isIndexFile(self, path):
		name = basename(path)
		return name == self.FILE_NAME or (name.startswith(f"{self.FILE_NAME}.") and name.endswith(".tmp"))

	def read(self, folder):
		path = join(folder, self.FILE_NAME)
		if islink(path):
			raise ValueError(_("The trash index must not be a symbolic link."))
		try:
			with open(path, encoding="utf-8") as stream:
				text = stream.read(self.MAX_SIZE + 1)
		except FileNotFoundError:
			return {}
		if len(text) > self.MAX_SIZE:
			raise ValueError(_("The trash index is too large."))
		entries = loads(text)
		if not isinstance(entries, dict) or any(not isinstance(x, str) or isabs(x) or normpath(x) != x or ".." in x.replace("\\", "/").split("/") or not isinstance(entries[x], str) or not isabs(entries[x]) or "\0" in x or "\0" in entries[x] for x in entries):
			raise ValueError(_("The trash index is damaged."))
		return entries

	def write(self, folder, entries):
		path = join(folder, self.FILE_NAME)
		temporary = f"{path}.{uuid4().hex}.tmp"
		try:
			if entries:
				text = dumps(entries, ensure_ascii=False)
				if len(text) > self.MAX_SIZE:
					raise ValueError(_("The trash index is too large."))
				with open(temporary, "x", encoding="utf-8") as stream:
					stream.write(text)
					stream.flush()
					fsync(stream.fileno())
				replace(temporary, path)
			elif lexists(path):
				unlink(path)
			if osName == "posix":
				descriptor = openDescriptor(folder, O_RDONLY)
				try:
					try:
						fsync(descriptor)
					except OSError as error:
						if error.errno not in (EINVAL, ENOTSUP):
							raise
				finally:
					close(descriptor)
		finally:
			if lexists(temporary):
				unlink(temporary)

	def get(self, path):
		folder = self.directory(path)
		with self.lock:
			return self.read(folder).get(relpath(path, folder)) if folder else None

	def add(self, path, originalPath):
		folder = self.directory(path)
		if not folder or not isabs(originalPath) or "\0" in originalPath:
			raise ValueError(_("Invalid original movie location."))
		with self.lock:
			entries = self.read(folder)
			entries[relpath(path, folder)] = originalPath
			self.write(folder, entries)

	def discard(self, paths):
		folders = {}
		for path in paths:
			folder = self.directory(path)
			if folder:
				folders.setdefault(folder, set()).add(relpath(path, folder))
		with self.lock:
			for folder, names in folders.items():
				entries = self.read(folder)
				# A failed erase or a new file at the same path must retain its location.
				remaining = {x: entries[x] for x in entries if x not in names or lexists(join(folder, x))}
				if remaining != entries:
					self.write(folder, remaining)


trashcanIndex = TrashcanIndex()


def getTrashcan(path=None):  # Returns trashcan folder without symbolic links.
	try:
		trashcan = trashcanStorage.location(path, trashcanStorage.mounts()) if path else ""
	except OSError as err:
		print(f"[Trashcan] Error {err.errno}: Unable to locate trashcan folder!  ({err.strerror})")
		trashcan = ""
	return trashcan


def createTrashcan(path=None):
	trashcan = getTrashcan(path)
	if trashcan:
		try:
			trashcanStorage.validate(path, join(trashcan, ".probe") if isdir(trashcan) else trashcan, checkDirectory=False)
			if not lexists(trashcan):
				mkdir(trashcan)
			if islink(trashcan) or not isdir(trashcan):
				raise ValueError(_("The trashcan must be a directory on the movie's filesystem."))
		except (OSError, ValueError) as error:
			print(f"[Trashcan] Unable to create trashcan '{trashcan}': {error}")
			trashcan = None
	else:
		trashcan = None
	return trashcan


def createTrashFolder(path=None):
	return createTrashcan(path=path)


def getTrashcanSize(startPath="."):
	trashcanSize = 0
	if startPath:
		for root, dirs, files in walk(startPath):
			for file in files:
				try:
					path = join(root, file)
					trashcanSize += getsize(path)
				except OSError as err:
					print(f"[Trashcan] Error {err.errno}: Unable to get directory size for '{path}'!  ({err.strerror})")
	return trashcanSize


class Trashcan:
	def __init__(self, session):
		self.session = session
		self.realRecordingCount = 0
		session.nav.record_event.append(self.gotRecordEvent)
		self.gotRecordEvent(None, None)

	def __del__(self):
		self.destroy()

	def gotRecordEvent(self, service, event):
		oldRecordingsCount = self.realRecordingCount
		self.realRecordingCount = self.session.nav.getRealRecordingsCount()
		if event == iRecordableService.evEnd and oldRecordingsCount != self.realRecordingCount:
			self.cleanIfIdle()

	def destroy(self):
		if self.session is not None:
			self.session.nav.record_event.remove(self.gotRecordEvent)
		self.session = None

	def cleanIfIdle(self):  # RecordTimer calls this when preparing a recording. That is a nice moment to clean up.
		if self.realRecordingCount:
			print(f"[Trashcan] {self.realRecordingCount} recording(s) are in progress.")
			return
		timeLimit = int(time()) - (config.usage.movielist_trashcan_days.value * 3600 * 24)
		reserveBytes = 1024 * 1024 * 1024 * config.usage.movielist_trashcan_reserve.value
		clean(timeLimit, reserveBytes)


def clean(timeLimit, reserveBytes):
	isCleaning = False
	for job in jobManager.getPendingJobs():
		jobName = str(job.name)
		if jobName.startswith(_("Cleaning Trashcan")):
			isCleaning = True
			break
	if config.usage.movielist_trashcan.value and not isCleaning:
		name = _("Cleaning Trashcan")
		job = Job(name)
		task = CleanTrashTask(job, name)
		task.openFiles(timeLimit, reserveBytes)
		jobManager.AddJob(job)
	elif isCleaning:
		print("[Trashcan] Trashcan cleanup is already running.")
	else:
		print("[Trashcan] Trashcan cleanup is disabled.")


def cleanAll(path=None):
	trashcan = getTrashcan(path)
	if isdir(trashcan) and not islink(trashcan):
		removed = []
		folders = []
		for root, dirs, files in trashcanStorage.walk(trashcan, trashcanStorage.mounts()):
			folders.extend(join(root, x) for x in dirs)
			for file in files:
				path = join(root, file)
				if trashcanIndex.isIndexFile(path):
					continue
				try:
					eBackgroundFileEraser.getInstance().erase(path)
					removed.append(path)
				except Exception as err:
					print(f"[Trashcan] Error: Failed to erase '{path}'!  ({err})")
		for folder in reversed(folders):
			try:
				rmdir(folder)
				removed.append(folder)
			except OSError as error:
				if error.errno != ENOTEMPTY:
					print(f"[Trashcan] Unable to remove directory '{folder}': {error}")
		try:
			trashcanIndex.discard(removed)
		except (OSError, ValueError) as error:
			print(f"[Trashcan] Unable to update original locations: {error}")
	else:
		print(f"[Trashcan] Trashcan '{trashcan}' is not a directory!")


def initTrashcan(session):
	global instance
	instance = Trashcan(session)


class CleanTrashTask(PythonTask):
	def openFiles(self, timeLimit, reserveBytes):
		self.timeLimit = timeLimit
		self.reserveBytes = reserveBytes

	def work(self):
		print("[Trashcan] Probing for trashcan folders.")
		mounts = trashcanStorage.mounts()
		matches = []
		seen = set()
		for mount in mounts:
			network = mount[2] in trashcanStorage.NETWORK or mount[2].startswith("fuse") or mount[1].startswith(("/media/net/", "/media/autofs/"))
			if not trashcanStorage.usable(mount) or network and not config.usage.movielist_trashcan_network_clean.value:
				continue
			for path in (join(mount[1], TRASHCAN), join(mount[1], "movie", TRASHCAN)):
				if trashcanStorage.mount(path, mounts) != mount or islink(path) or not isdir(path):
					continue
				try:
					status = stat(path)
					identity = (status.st_dev, status.st_ino)
					if identity not in seen:
						matches.append(path)
						seen.add(identity)
				except OSError:
					continue
		print("[Trashcan] Found the following trashcans '%s'." % "', '".join(matches))
		for trashcan in matches:
			removed = []
			print(f"[Trashcan] Looking in trashcan '{trashcan}'.")
			try:
				trashcanStatus = statvfs(trashcan)
				freeSpace = trashcanStatus.f_bfree * trashcanStatus.f_bsize
			except OSError as err:
				print(f"[Trashcan] Error {err.errno}: Unable to get status for directory '{trashcan}'!  ({err.strerror})")
				continue  # An unavailable share must not be treated as a full disk.
			bytesToRemove = self.reserveBytes - freeSpace
			candidates = []
			folders = []
			folderTimes = {trashcan: 0}
			size = 0
			for root, dirs, files in trashcanStorage.walk(trashcan, mounts):
				folders.extend(join(root, x) for x in dirs)
				if root != trashcan:
					try:
						folderTimes[root] = max(folderTimes.get(dirname(root), 0), stat(root).st_ctime)
					except OSError:
						dirs[:] = []
						continue
				for file in files:
					try:
						path = join(root, file)
						if trashcanIndex.isIndexFile(path):
							continue
						status = stat(path)
						deletedAt = max(status.st_ctime, folderTimes[root])
						if deletedAt < self.timeLimit:
							eBackgroundFileEraser.getInstance().erase(path)
							removed.append(path)
							bytesToRemove -= status.st_size
						else:
							candidates.append((deletedAt, path, status.st_size))
							size += status.st_size
					except OSError as err:
						print(f"[Trashcan] Error {err.errno}: Unable to get status for '{path}'!  ({err.strerror})")
					except Exception as err:
						print(f"[Trashcan] Error: Failed to erase '{file}'!  ({err})")
			candidates.sort()
			for pathTime, path, pathSize in candidates:
				if bytesToRemove <= 0:
					break
				try:
					eBackgroundFileEraser.getInstance().erase(path)
					removed.append(path)
					bytesToRemove -= pathSize
					size -= pathSize
				except Exception as error:
					print(f"[Trashcan] Failed to erase '{path}': {error}")
			for folder in reversed(folders):
				try:
					rmdir(folder)
					removed.append(folder)
				except OSError as error:
					if error.errno != ENOTEMPTY:
						print(f"[Trashcan] Unable to remove directory '{folder}': {error}")
			print(f"[Trashcan] Trashcan '{trashcan}' is now using {size} bytes.")
			try:
				trashcanIndex.discard(removed)
			except (OSError, ValueError) as error:
				print(f"[Trashcan] Unable to update original locations: {error}")
		if not matches:
			print("[Trashcan] No trashcans found!")


class TrashInfo(VariableText, GUIComponent):
	GUI_WIDGET = eLabel

	def __init__(self, path):
		VariableText.__init__(self)
		GUIComponent.__init__(self)

	def update(self, path):
		self.setText(f"{_('Trashcan')}: {scaleNumber(getTrashcanSize(getTrashcan(path)))}")
