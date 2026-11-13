from errno import EINVAL, ENOTEMPTY, ENOTSUP
from json import dumps, loads
from os import O_RDONLY, W_OK, access, close, fsync, mkdir, name as osName, open as openDescriptor, replace, rmdir, stat, statvfs, unlink, walk
from os.path import basename, dirname, getsize, isabs, isdir, islink, join, lexists, normpath, realpath, relpath, split
from threading import RLock
from time import time
from uuid import uuid4

from enigma import eBackgroundFileEraser, eLabel, iRecordableService

from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Harddisk import findMountPoint
from Components.Task import Job, PythonTask, job_manager as jobManager
from Components.VariableText import VariableText
from Tools.Conversions import scaleNumber
from Tools.Directories import fileReadLines

MODULE_NAME = __name__.split(".")[-1]
TRASHCAN = ".Trash"  # This should this be ".Trashcan" to be consistent with the module.


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
	if path:
		path = realpath(path)
	try:
		if path is None or path == "/media/autofs":
			print("[Trashcan] Error: Trashcan path is None or invalid!")
			trashcan = ""
		else:
			trashcan = join(join(findMountPoint(path), "movie") if "/movie" in path else findMountPoint(path), TRASHCAN)
	except OSError as err:
		print(f"[Trashcan] Error {err.errno}: Unable to locate trashcan folder!  ({err.strerror})")
		trashcan = ""
	return trashcan


def createTrashcan(path=None):
	trashcan = getTrashcan(path)
	if trashcan and access(split(trashcan)[0], W_OK):
		if not isdir(trashcan):
			try:
				mkdir(trashcan)
			except OSError as err:
				print(f"[Trashcan] Error {err.errno}: Unable to create trashcan folder '{trashcan}'!  ({err.strerror})")
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
	if isdir(trashcan):
		removed = []
		for root, dirs, files in walk(trashcan, topdown=False):
			for file in files:
				path = join(root, file)
				if trashcanIndex.isIndexFile(path):
					continue
				try:
					eBackgroundFileEraser.getInstance().erase(path)
					removed.append(path)
				except Exception as err:
					print(f"[Trashcan] Error: Failed to erase '{path}'!  ({err})")
			for dir in dirs:  # Remove empty directories if possible.
				path = join(root, dir)
				try:
					rmdir(path)
				except OSError as err:
					if err.errno != ENOTEMPTY:
						print(f"[Trashcan] Error {err.errno}: Unable to remove directory '{path}'!  ({err.strerror})")
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
		lines = []
		lines = fileReadLines("/proc/mounts", default=lines, source=MODULE_NAME)
		mounts = []
		for line in lines:
			parts = line.strip().split()
			if parts[1] == "/media/autofs":
				continue
			if config.usage.movielist_trashcan_network_clean.value and (parts[1].startswith("/media/net") or parts[1].startswith("/media/autofs")):
				mounts.append(parts[1])
			elif not parts[1].startswith("/media/net") and not parts[1].startswith("/media/autofs"):
				mounts.append(parts[1])
		matches = []
		for mount in mounts:
			if isdir(join(mount, TRASHCAN)):
				matches.append(join(mount, TRASHCAN))
			if isdir(join(mount, "movie", TRASHCAN)):
				matches.append(join(mount, "movie", TRASHCAN))
		print("[Trashcan] Found the following trashcans '%s'." % "', '".join(matches))
		for trashcan in matches:
			removed = []
			print(f"[Trashcan] Looking in trashcan '{trashcan}'.")
			trashcanSize = getTrashcanSize(trashcan)
			try:
				trashcanStatus = statvfs(trashcan)
				freeSpace = trashcanStatus.f_bfree * trashcanStatus.f_bsize
			except OSError as err:
				print(f"[Trashcan] Error {err.errno}: Unable to get status for directory '{trashcan}'!  ({err.strerror})")
				freeSpace = 0
			bytesToRemove = self.reserveBytes - freeSpace
			print(f"[Trashcan] Trashcan '{trashcan}' size is {trashcanSize} bytes.")
			candidates = []
			size = 0
			for root, dirs, files in walk(trashcan, topdown=False):
				for file in files:
					try:
						path = join(root, file)
						if trashcanIndex.isIndexFile(path):
							continue
						status = stat(path)
						if status.st_ctime < self.timeLimit:
							eBackgroundFileEraser.getInstance().erase(path)
							removed.append(path)
							bytesToRemove -= status.st_size
						else:
							candidates.append((status.st_ctime, path, status.st_size))
							size += status.st_size
					except OSError as err:
						print(f"[Trashcan] Error {err.errno}: Unable to get status for '{path}'!  ({err.strerror})")
					except Exception as err:
						print(f"[Trashcan] Error: Failed to erase '{file}'!  ({err})")
				for dir in dirs:  # Remove empty directories if possible.
					try:
						path = join(root, dir)
						rmdir(path)
					except OSError as err:
						if err.errno != ENOTEMPTY:
							print(f"[Trashcan] Error {err.errno}: Unable to remove directory '{path}'!  ({err.strerror})")
				candidates.sort()  # Now we have a list of ctime, candidates, size. Sorted by ctime (deletion time).
				for pathTime, path, pathSize in candidates:
					if bytesToRemove < 0:
						break
					try:  # Sometimes the path doesn't exist. This can happen if trashcan is on a network or other code is emptying the trashcan at same time.
						eBackgroundFileEraser.getInstance().erase(path)
						removed.append(path)
					except Exception as err:
						print(f"[Trashcan] Error: Failed to erase '{path}'!  ({err})")  # Should we ignore any deletion errors?
					bytesToRemove -= pathSize
					size -= pathSize
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
