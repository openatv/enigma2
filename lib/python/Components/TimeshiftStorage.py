"""Owned time shift buffers and bounded, recoverable recording exports.

Filesystem methods in this module run in a worker. The GUI only reads the
registry and the export's progress counters; it never polls a remote file.
"""

from functools import wraps
from json import dump, dumps, load
from os import O_CREAT, O_EXCL, O_RDONLY, O_WRONLY, W_OK, X_OK, access, close, fdopen, fstat, fsync, link, listdir, makedirs, mkdir, open as openFile, rename, replace, rmdir, stat, supports_dir_fd, unlink
from os.path import basename, dirname, join, normpath, realpath
from re import fullmatch
from stat import S_ISDIR, S_ISREG
from threading import Event, Lock, RLock
from time import time
from uuid import uuid4

TS_PACKET_SIZE = 188
EXPORT_PART_SIZE = (((1 << 31) - 1) // TS_PACKET_SIZE) * TS_PACKET_SIZE
MAX_SAVE_INTENTS = 100
MAX_SAVE_INTENT_BYTES = 64 * 1024


def formatTimeshiftMetadata(metadata, tags=None):
	"""Keep a buffer's decoder snapshot independent of later live services."""
	fields = (
		metadata.get("service", ""), metadata.get("name", ""), metadata.get("description", ""),
		str(int(metadata.get("begin", 0))), metadata.get("tags", "") if tags is None else tags,
		"0", "0", metadata.get("serviceData", ""), str(metadata.get("packetSize", TS_PACKET_SIZE)), str(metadata.get("scrambled", 0))
	)
	return "\n".join(" ".join(str(x).splitlines()) for x in fields) + "\n"


def parseTimeshiftMetadata(content):
	lines = [x.removesuffix("\r") for x in content.removesuffix("\n").split("\n")]
	if len(lines) < 4:
		raise ValueError("Incomplete time shift metadata")
	metadata = dict(zip(("service", "name", "description", "begin", "tags"), lines))
	metadata["begin"] = int(metadata["begin"])
	metadata["serviceData"] = lines[7] if len(lines) > 7 else ""
	metadata["packetSize"] = int(lines[8] or 0) if len(lines) > 8 else TS_PACKET_SIZE
	if metadata["packetSize"] <= 0:
		metadata["packetSize"] = TS_PACKET_SIZE
	metadata["scrambled"] = int(lines[9] or 0) if len(lines) > 9 else 0
	return metadata


def _storageMount(descriptor, path):
	"""Reject fallback flash/RAM paths; mutations themselves remain fd-relative."""
	status = fstat(descriptor)
	current = stat(path, follow_symlinks=False)
	if (current.st_dev, current.st_ino) != (status.st_dev, status.st_ino):
		raise OSError(f"Time shift storage directory changed: {path}")
	if status.st_dev == stat("/").st_dev:
		raise OSError(f"Time shift storage is on the root filesystem: {path}")
	with open("/proc/self/mountinfo", encoding="utf-8") as mountsFile:
		mounts = []
		for line in mountsFile:
			fields = line.split()
			separator = fields.index("-")
			mountpoint = fields[4].replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")
			if path == mountpoint or path.startswith(mountpoint.rstrip("/") + "/"):
				mounts.append((len(mountpoint), fields[0], mountpoint, fields[separator + 1], fields[5]))
	if not mounts:
		raise OSError(f"Time shift storage is not mounted: {path}")
	mount = max(mounts)
	if mount[2] == "/" or mount[3] in ("tmpfs", "ramfs", "rootfs", "autofs", "jffs2", "ubifs", "squashfs"):
		raise OSError(f"Time shift storage is unavailable: {path}")
	if stat(mount[2]).st_dev != status.st_dev:
		raise OSError(f"Time shift storage mount changed: {path}")
	# mnt_id was added after kernel 3.2. On older receivers, the pinned fd,
	# directory inode and current mountinfo entry provide the fallback guard.
	with open(f"/proc/self/fdinfo/{descriptor}", encoding="utf-8") as descriptorFile:
		for line in descriptorFile:
			if line.startswith("mnt_id:") and line.split()[1] != mount[1]:
				raise OSError(f"Time shift storage mount was detached: {path}")
	return (mount[1], mount[2], mount[3], status.st_dev)


def _directoryOperation(function):
	@wraps(function)
	def locked(self, *arguments, **options):
		with self._operationLock:
			return function(self, *arguments, **options)
	return locked


class _StorageDirectory:
	"""An owned directory descriptor, never a pathname fallback for mutations."""

	def __init__(self, path, policy=None, parent=None, name=None):
		self._operationLock = RLock()
		if openFile not in supports_dir_fd:
			raise OSError("Time shift storage requires directory descriptor support")
		from os import O_CLOEXEC, O_DIRECTORY, O_NOFOLLOW
		self._fileFlags = O_NOFOLLOW | O_CLOEXEC
		flags = O_RDONLY | O_DIRECTORY | self._fileFlags
		self.path = join(parent.path, name) if parent else realpath(path)
		self._policy = policy or _storageMount
		self._files = {}
		self.fd = openFile(name, flags, dir_fd=parent.fd) if parent else openFile(self.path, flags)
		try:
			status = fstat(self.fd)
			if not S_ISDIR(status.st_mode):
				raise OSError(f"Not a time shift storage directory: {self.path}")
			self.identity = (status.st_dev, status.st_ino)
			self.mount = self._policy(self.fd, self.path)
		except BaseException:
			self.close()
			raise

	@_directoryOperation
	def close(self):
		descriptor = self.fd
		self.fd = None
		if descriptor is not None:
			close(descriptor)

	def __del__(self):
		if getattr(self, "fd", None) is not None:
			try:
				self.close()
			except OSError:
				pass

	@_directoryOperation
	def check(self):
		if self.fd is None or self._policy(self.fd, self.path) != self.mount:
			raise OSError(f"Time shift storage mount changed: {self.path}")

	def _name(self, name):
		if name in ("", ".", "..") or name != basename(name):
			raise ValueError("Expected a single time shift filename")
		return name

	@_directoryOperation
	def list(self):
		self.check()
		return listdir(self.fd)

	@_directoryOperation
	def stat(self, name, remember=True):
		self.check()
		status = stat(self._name(name), dir_fd=self.fd, follow_symlinks=False)
		if not S_ISREG(status.st_mode) and not S_ISDIR(status.st_mode):
			raise OSError(f"Refusing a non-regular time shift path: {join(self.path, name)}")
		identity = (status.st_dev, status.st_ino)
		if status.st_dev != self.identity[0] or name in self._files and self._files[name] != identity:
			raise OSError(f"Time shift file identity changed: {join(self.path, name)}")
		if remember:
			self._files[name] = identity
		return status

	@_directoryOperation
	def exists(self, name):
		try:
			self.stat(name)
			return True
		except FileNotFoundError:
			return False

	@_directoryOperation
	def child(self, name, create=False):
		self.check()
		self._name(name)
		if create:
			mkdir(name, mode=0o700, dir_fd=self.fd)
		status = self.stat(name)
		if not S_ISDIR(status.st_mode):
			raise OSError(f"Not a time shift session directory: {name}")
		child = type(self)(join(self.path, name), self._policy, parent=self, name=name)
		if child.identity != (status.st_dev, status.st_ino):
			child.close()
			raise OSError(f"Time shift session directory changed: {name}")
		return child

	@_directoryOperation
	def open(self, name, mode="rb", buffering=-1, encoding=None):
		self.check()
		self._name(name)
		creating = "x" in mode
		writing = creating or "w" in mode
		if not creating:
			status = self.stat(name)
			if not S_ISREG(status.st_mode):
				raise OSError(f"Not a regular time shift file: {name}")
		flags = (O_WRONLY if writing else O_RDONLY) | self._fileFlags
		if creating:
			flags |= O_CREAT | O_EXCL
		descriptor = openFile(name, flags, 0o600, dir_fd=self.fd)
		try:
			status = fstat(descriptor)
			identity = (status.st_dev, status.st_ino)
			if not S_ISREG(status.st_mode) or status.st_dev != self.identity[0] or not creating and identity != self._files[name]:
				raise OSError(f"Time shift file changed while opening: {name}")
			self._files[name] = identity
			stream = fdopen(descriptor, mode, buffering=buffering, encoding=encoding)
		except BaseException:
			close(descriptor)
			raise
		# Do not truncate until the opened inode has passed the ownership check.
		if "w" in mode:
			stream.truncate(0)
		return stream

	@_directoryOperation
	def unlink(self, name):
		self.stat(name, remember=False)
		if name not in self._files:
			raise OSError(f"Refusing to remove an unowned time shift file: {name}")
		unlink(name, dir_fd=self.fd)
		self._files.pop(name)

	def renameTo(self, name, destination, destinationName, replaceExisting=False):
		first, second = sorted((self, destination), key=id)
		with first._operationLock, second._operationLock:
			self.stat(name)
			destination.check()
			destination._name(destinationName)
			if destination.exists(destinationName) and not replaceExisting:
				raise FileExistsError(join(destination.path, destinationName))
			identity = self._files[name]
			rename(name, destinationName, src_dir_fd=self.fd, dst_dir_fd=destination.fd)
			self._files.pop(name)
			destination._files[destinationName] = identity

	def linkTo(self, name, destination, destinationName):
		first, second = sorted((self, destination), key=id)
		with first._operationLock, second._operationLock:
			self.stat(name)
			destination.check()
			destination._name(destinationName)
			link(name, destinationName, src_dir_fd=self.fd, dst_dir_fd=destination.fd, follow_symlinks=False)
			status = destination.stat(destinationName)
			if (status.st_dev, status.st_ino) != self._files[name]:
				destination.unlink(destinationName)
				raise OSError(f"Time shift source changed while linking: {name}")

	@_directoryOperation
	def removeDirectory(self, name):
		self.stat(name)
		rmdir(name, dir_fd=self.fd)
		self._files.pop(name)

	@_directoryOperation
	def snapshot(self, names):
		for name in names:
			self.exists(name)
		return {"directory": self.identity, "mount": self.mount, "files": {x: self._files[x] for x in names if x in self._files}}

	@_directoryOperation
	def restoreIdentity(self, identity):
		if self.identity != identity["directory"] or self.mount != identity["mount"]:
			raise OSError(f"Time shift storage identity changed: {self.path}")
		self._files.update(identity["files"])


def checkStorageDirectory(path):
	"""Read-only setup check using the same pinned mount policy as exports."""
	directory = _StorageDirectory(path)
	try:
		if not access(".", W_OK | X_OK, dir_fd=directory.fd):
			raise PermissionError(path)
		directory.check()
	finally:
		directory.close()


class TimeshiftSaveJournal:
	"""Small local intents protect sources even when their NAS disappears."""

	def __init__(self, directory):
		self.directory = directory
		self._lock = Lock()
		self._records = None

	def _loadRecords(self):
		if self._records is None:
			records = {}
			makedirs(self.directory, exist_ok=True)
			for name in listdir(self.directory):
				if name.endswith(".json"):
					path = join(self.directory, name)
					if stat(path).st_size > MAX_SAVE_INTENT_BYTES:
						raise OSError(f"Time shift save intent is too large: {path}")
					with open(path, encoding="utf-8") as intentFile:
						intent = load(intentFile)
					records[path] = tuple(x[0] for x in intent["sources"])
			self._records = records

	def create(self, intent):
		content = dumps(intent)
		if len(content.encode("utf-8")) > MAX_SAVE_INTENT_BYTES:
			raise OSError("The time shift save intent is too large")
		with self._lock:
			self._loadRecords()
			if len(self._records) >= MAX_SAVE_INTENTS:
				raise OSError("Too many pending time shift saves; finish or recover earlier saves first")
			path = join(self.directory, f"{uuid4().hex}.json")
			with open(path, "x", encoding="utf-8") as intentFile:
				intentFile.write(content)
				intentFile.flush()
				fsync(intentFile.fileno())
			self._records[path] = tuple(x[0] for x in intent["sources"])
			return path

	def complete(self, path):
		with self._lock:
			self._loadRecords()
			if path not in self._records:
				raise OSError("Unknown time shift save intent")
			try:
				unlink(path)
			except FileNotFoundError:
				pass
			self._records.pop(path)

	def retainedPaths(self):
		with self._lock:
			self._loadRecords()
			paths = set()
			for sources in self._records.values():
				paths.update(sources)
			return paths


def getTimeshiftParts(path, limit=None, allowEmpty=False, statFile=None):
	"""Capture fixed lengths, never chase a file while it grows."""
	statFile = statFile or stat
	parts = []
	remaining = limit
	index = 0
	while remaining is None or remaining > 0:
		partPath = path if index == 0 else f"{path}.{index:03d}"
		if index >= 1000:
			if remaining is not None:
				raise OSError("The time shift source exceeds the supported 1000 parts")
			try:
				statFile(partPath)
			except FileNotFoundError:
				break
			raise OSError("The time shift source has an unsupported physical part")
		try:
			length = statFile(partPath).st_size
		except FileNotFoundError:
			if index == 0 or remaining is not None and remaining > 0:
				raise
			break
		if parts:
			previousPath, previousLength = parts[-1]
			finalLength = statFile(previousPath).st_size
			if finalLength < previousLength:
				raise OSError(f"Time shift source became shorter: {previousPath}")
			if finalLength != previousLength:
				if remaining is not None:
					finalLength = min(finalLength, previousLength + remaining)
					remaining -= finalLength - previousLength
				parts[-1] = (previousPath, finalLength)
		if remaining is not None:
			length = min(length, remaining)
			remaining -= length
		if length or allowEmpty:
			parts.append((partPath, length))
		index += 1
	if not allowEmpty and (not parts or not sum(x[1] for x in parts)):
		raise OSError("The time shift buffer is empty")
	return parts


class TimeshiftBuffer:
	def __init__(self, path, metadata=None):
		self.path = path
		self.metadata = metadata or {}
		self.created = self.metadata.get("begin", time())
		self.active = False
		self.leases = 0
		self.retained = False
		self.autosave = False
		self.deleting = False
		self.deletionParts = None
		self.directory = None
		self.pendingWrites = 0
		self.sidecarsReady = Event()
		self.sidecarsReady.set()


class TimeshiftRegistry:
	def __init__(self, directoryFactory=None):
		self.buffers = {}
		self._lock = Lock()
		self._recovered = set()
		self._directories = {}
		self._directoryFactory = directoryFactory or _StorageDirectory

	def _directory(self, path):
		path = normpath(path)
		if path not in self._directories:
			parentPath = dirname(path)
			parent = self._directories.get(parentPath)
			self._directories[path] = parent.child(basename(path)) if parent else self._directoryFactory(path)
		return self._directories[path]

	def capture(self, entry):
		"""Bind a new native buffer in a worker, before it can become disposable."""
		if entry.directory is None:
			directory = self._directory(dirname(entry.path))
			directory.stat(basename(entry.path))
			entry.directory = directory
		return entry.directory

	def _closeUnusedDirectories(self):
		with self._lock:
			used = {dirname(x.path) for x in self.buffers.values()} | self._recovered
			unused = [self._directories.pop(x) for x in tuple(self._directories) if x not in used]
		for directory in unused:
			directory.close()

	def close(self):
		"""Call in a worker after metadata and cleanup workers have completed."""
		with self._lock:
			if any(x.pendingWrites or x.deleting for x in self.buffers.values()):
				return False
			directories = tuple(self._directories.values())
			self._directories.clear()
		for directory in directories:
			directory.close()
		return True

	def writeMetadata(self, entry, content):
		directory = self.capture(entry)
		name = f"{basename(entry.path)}.meta"
		with directory.open(name, "w" if directory.exists(name) else "x", encoding="utf-8") as metadataFile:
			metadataFile.write(content)

	def writeEvent(self, entry, saveEvent, *arguments):
		directory = self.capture(entry)
		name = f"{basename(entry.path)}.eit"
		with directory.open(name, "wb" if directory.exists(name) else "xb") as eventFile:
			# The native EIT writer reopens this pinned inode, not a NAS pathname.
			return saveEvent(f"/proc/self/fd/{eventFile.fileno()}", *arguments)

	def register(self, identifier, path, metadata):
		with self._lock:
			entry = TimeshiftBuffer(path, metadata)
			entry.active = True
			self.buffers[identifier] = entry
		return entry

	def acquire(self, entry):
		with self._lock:
			if entry.deleting:
				raise OSError("The time shift buffer is being removed")
			entry.leases += 1

	def release(self, entry, failed=False):
		with self._lock:
			entry.leases = max(0, entry.leases - 1)
			entry.retained = entry.retained or failed

	def recover(self, directory, retainedPaths=()):
		"""One scan per storage location, including pre-session legacy buffers."""
		directory = normpath(directory)
		if directory in self._recovered:
			return
		root = self._directory(directory)
		paths = []
		legacyCopies = set()
		legacyCleanup = set()
		directoryNames = {directory: root.list()}
		for name in directoryNames[directory]:
			path = join(directory, name)
			if fullmatch(r"timeshift\.[A-Za-z0-9]{6}", name):
				try:
					status = root.stat(name)
				except FileNotFoundError:
					continue
			else:
				status = None
			if status and S_ISDIR(status.st_mode):
				directoryNames[path] = self._directory(path).list()
				sessionPaths = [join(path, x) for x in directoryNames[path] if fullmatch(r"[0-9]{6}\.ts", x)]
				paths.extend(sessionPaths)
				if not sessionPaths:
					with self._lock:
						unused = self._directories.pop(path) if not any(dirname(x.path) == path for x in self.buffers.values()) else None
					if unused:
						unused.close()
			elif fullmatch(r"pts_livebuffer_[0-9]+", name):
				paths.append(path)
			elif fullmatch(r"timeshift\.[A-Za-z0-9]{6}", name):
				paths.append(path)
			elif fullmatch(r"(?:timeshift\.[A-Za-z0-9]{6}|pts_livebuffer_[0-9]+)(?:\.[0-9]+)?\.copy", name):
				paths.append(path)
				legacyCopies.add(path)
			elif fullmatch(r"(?:timeshift\.[A-Za-z0-9]{6}|pts_livebuffer_[0-9]+)(?:\.(?:[0-9]{3}|eit|meta|ap|sc|cuts))?\.del(?:_again)?", name):
				paths.append(path)
				legacyCleanup.add(path)
		for path in paths:
			with self._lock:
				if any(x.path == path for x in self.buffers.values()):
					continue
			metadata = {}
			storageDirectory = self._directory(dirname(path))
			try:
				with storageDirectory.open(f"{basename(path)}.meta", "r", encoding="utf-8") as source:
					metadata = parseTimeshiftMetadata(source.read())
			except (FileNotFoundError, ValueError, KeyError):
				try:
					metadata["begin"] = storageDirectory.stat(basename(path)).st_mtime
				except FileNotFoundError:
					continue
			entry = TimeshiftBuffer(path, metadata)
			self.capture(entry)
			entry.metadata["cleanupOnly"] = path in legacyCleanup
			entry.retained = path in retainedPaths or path in legacyCopies or any(x.startswith(f"{basename(path)}.save.") and x.endswith(".json") for x in directoryNames[dirname(path)])
			with self._lock:
				if not any(x.path == path for x in self.buffers.values()):
					self.buffers[path] = entry
		self._recovered.add(directory)
		self._closeUnusedDirectories()

	def remove(self, identifier, protected=()):
		with self._lock:
			entry = self.buffers.get(identifier)
			if entry is None or entry.active or entry.leases or entry.retained or entry.path in protected:
				return 0
			if entry.directory is None:
				# No worker ever observed this inode while it was ours. Do not
				# adopt an arbitrary path after a mount switch for deletion.
				entry.retained = True
				return 0
			entry.deleting = True
		directory = entry.directory
		try:
			directory.check()
			if entry.deletionParts is None:
				try:
					entry.deletionParts = getTimeshiftParts(entry.path, allowEmpty=True, statFile=lambda path: directory.stat(basename(path)))
				except FileNotFoundError:
					entry.deletionParts = []
					prefix = f"{basename(entry.path)}."
					for name in directory.list():
						if name.startswith(prefix) and fullmatch(r"[0-9]{3}", name[len(prefix):]) and int(name[len(prefix):]) > 0:
							path = join(dirname(entry.path), name)
							entry.deletionParts.append((path, directory.stat(name).st_size))
			parts = entry.deletionParts
			for suffix in (".meta", ".eit", ".ap", ".sc", ".cuts"):
				directory.exists(f"{basename(entry.path)}{suffix}")
			for path, unusedLength in parts:
				try:
					directory.unlink(basename(path))
				except FileNotFoundError:
					pass
			for suffix in (".meta", ".eit", ".ap", ".sc", ".cuts"):
				try:
					name = f"{basename(entry.path)}{suffix}"
					if directory.exists(name):
						directory.unlink(name)
				except FileNotFoundError:
					pass
		except FileNotFoundError:
			parts = []
		except OSError:
			entry.deleting = False
			raise
		with self._lock:
			self.buffers.pop(identifier, None)
		self._closeUnusedDirectories()
		return sum(x[1] for x in parts)


def removeTimeshiftRecording(source, identity, directoryFactory=None):
	"""Remove only the exact immutable continuation consumed by an export."""
	if not identity or not identity.get("complete") or basename(source) not in identity.get("files", {}):
		raise OSError("Missing time shift continuation ownership information")
	directory = (directoryFactory or _StorageDirectory)(dirname(source))
	try:
		directory.restoreIdentity(identity)
		for name in identity["files"]:
			try:
				directory.unlink(name)
			except FileNotFoundError:
				pass
	finally:
		directory.close()


class TimeshiftExport:
	def __init__(self, sources, destination, metadata=None, immutable=False, partSize=EXPORT_PART_SIZE, merge=False, intentPath=None, directoryFactory=None):
		# sources contains (base path, byte limit), with None only for closed files.
		self.sources = sources
		self.destination = destination
		self.metadata = metadata
		self.immutable = immutable
		self.partSize = partSize
		self.merge = merge
		self.cancelled = Event()
		self.copied = 0
		self.total = 0
		self.intent = intentPath or f"{sources[-1][0]}.save.{uuid4().hex}.json"
		self._localIntent = intentPath is not None
		self._staging = join(dirname(destination), f".pts-save-{uuid4().hex}")
		self._directoryFactory = directoryFactory or _StorageDirectory
		self._directories = {}
		self.sourceIdentities = {}

	def _directory(self, path):
		path = normpath(path)
		if path not in self._directories:
			self._directories[path] = self._directoryFactory(path)
		return self._directories[path]

	def _stat(self, path):
		return self._directory(dirname(path)).stat(basename(path))

	def _exists(self, path):
		return self._directory(dirname(path)).exists(basename(path))

	def _open(self, path, mode="rb", buffering=-1, encoding=None):
		return self._directory(dirname(path)).open(basename(path), mode, buffering=buffering, encoding=encoding)

	def _unlink(self, path):
		self._directory(dirname(path)).unlink(basename(path))

	def _rename(self, source, destination, replaceExisting=False):
		self._directory(dirname(source)).renameTo(basename(source), self._directory(dirname(destination)), basename(destination), replaceExisting=replaceExisting)

	def run(self):
		try:
			for path in [x[0] for x in self.sources] + [self.destination]:
				self._directory(dirname(path))
			return self._run()
		finally:
			for directory in self._directories.values():
				directory.close()

	def _run(self):
		intent = {"version": 1, "sources": self.sources, "destination": self.destination, "metadata": self.metadata, "staging": self._staging, "merge": self.merge, "phase": "copying"}
		if self._localIntent:
			self._writeIntent(intent)
		else:
			with self._open(self.intent, "x", encoding="utf-8") as intentFile:
				dump(intent, intentFile)
				intentFile.flush()
				fsync(intentFile.fileno())
		parts = []
		for path, limit in self.sources:
			sourceParts = getTimeshiftParts(path, limit, statFile=self._stat)
			parts.extend(sourceParts)
			names = [basename(x[0]) for x in sourceParts] + [f"{basename(path)}{x}" for x in (".meta", ".eit", ".ap", ".sc", ".cuts")]
			if path.endswith(".ts"):
				names.append(f"{basename(path)[:-3]}.eit")
			self.sourceIdentities[path] = self._directory(dirname(path)).snapshot(names)
			self.sourceIdentities[path]["complete"] = self.immutable and limit is None
		self.total = sum(x[1] for x in parts)
		if self.total > self.partSize * 1000:
			raise OSError("The recording exceeds the supported 1000 time shift parts")
		self._directories[self._staging] = self._directory(dirname(self.destination)).child(basename(self._staging), create=True)
		outputs = []
		backups = []
		promoted = []
		committed = False
		try:
			# A hard link is safe only when no writer can change any source inode.
			canLink = self.immutable and not self.merge and all(x[1] is None for x in self.sources) and all(x[1] == self.partSize for x in parts[:-1]) and parts[-1][1] <= self.partSize
			if canLink:
				try:
					for index, (path, length) in enumerate(parts):
						self._checkCancelled()
						output = join(self._staging, f"{index:03d}")
						self._directory(dirname(path)).linkTo(basename(path), self._directory(self._staging), basename(output))
						outputs.append(output)
						self.copied += length
				except OSError:
					for output in outputs:
						self._unlink(output)
					outputs = []
					self.copied = 0
			if not outputs:
				outputFile = None
				try:
					for path, length in parts:
						with self._open(path, "rb", buffering=0) as source:
							remaining = length
							while remaining:
								self._checkCancelled()
								if outputFile is None:
									output = join(self._staging, f"{len(outputs):03d}")
									outputFile = self._open(output, "xb")
									outputs.append(output)
									partRemaining = self.partSize
								data = source.read(min(1024 * 1024, remaining, partRemaining))
								if not data:
									raise OSError(f"Time shift source became shorter: {path}")
								outputFile.write(data)
								remaining -= len(data)
								partRemaining -= len(data)
								self.copied += len(data)
								if partRemaining == 0:
									outputFile.flush()
									fsync(outputFile.fileno())
									outputFile.close()
									outputFile = None
					if outputFile:
						outputFile.flush()
						fsync(outputFile.fileno())
				finally:
					if outputFile:
						outputFile.close()
			self._checkCancelled()
			routes = [(x, self.destination if index == 0 else f"{self.destination}.{index:03d}") for index, x in enumerate(outputs)]
			if self.metadata is not None:
				metadataPath = join(self._staging, "metadata")
				with self._open(metadataPath, "x", encoding="utf-8") as metadataFile:
					metadataFile.write(self.metadata)
					metadataFile.flush()
					fsync(metadataFile.fileno())
				routes.append((metadataPath, f"{self.destination}.meta"))
			eitSource = f"{self.sources[-1][0]}.eit"
			if self.merge:
				eitSource = f"{self.sources[-1][0][:-3]}.eit"
			if self._exists(eitSource):
				eitPath = join(self._staging, "eit")
				with self._open(eitSource, "rb") as source, self._open(eitPath, "xb") as eitFile:
					while True:
						data = source.read(65536)
						if not data:
							break
						self._checkCancelled()
						eitFile.write(data)
					eitFile.flush()
					fsync(eitFile.fileno())
				routes.append((eitPath, f"{self.destination[:-3]}.eit"))
			originals = []
			originalParts = 0
			if self.merge:
				originals = [x[0] for x in getTimeshiftParts(self.destination, statFile=self._stat)]
				originalParts = len(originals)
				originals.extend(x[1] for x in routes[len(outputs):] if self._exists(x[1]))
			plannedBackups = [(join(self._staging, f"original-{index:03d}"), x) for index, x in enumerate(originals)]
			intent.update(phase="publishing", parts=len(outputs), sidecars=[basename(x[0]) for x in routes[len(outputs):]], originalParts=originalParts, originalSidecars=[x[len(self.destination):] if x.startswith(self.destination) else ".eit" for x in originals[originalParts:]])
			self._writeIntent(intent)
			for backup, path in plannedBackups:
				self._rename(path, backup)
				backups.append((backup, path))
			# Publish the base transport stream last so a new recording is not
			# advertised before all physical parts and metadata are available.
			for output, path in routes[1:] + routes[:1]:
				self._rename(output, path)
				promoted.append(path)
			committed = True
			intent["phase"] = "committed"
			# Once committed, housekeeping failure must never roll back the
			# new recording after any original part has already been removed.
			try:
				self._writeIntent(intent)
				for backup, unusedPath in backups:
					self._unlink(backup)
				self._directory(dirname(self.destination)).removeDirectory(basename(self._staging))
				if self._localIntent:
					unlink(self.intent)
				else:
					self._unlink(self.intent)
			except OSError as err:
				print(f"[Timeshift] Saved recording; deferred export cleanup: {err}")
			return self.destination
		except BaseException:
			if not committed:
				# Preserve intent and source. Roll back only outputs this job owns.
				for path in promoted:
					try:
						self._unlink(path)
					except OSError:
						pass
				for backup, path in backups:
					if self._exists(backup) and not self._exists(path):
						self._rename(backup, path)
			raise

	def _writeIntent(self, intent):
		path = f"{self.intent}.new"
		content = dumps(intent)
		if len(content.encode("utf-8")) > MAX_SAVE_INTENT_BYTES:
			raise OSError("The time shift save intent is too large")
		intentFile = open(path, "w", encoding="utf-8") if self._localIntent else self._open(path, "x", encoding="utf-8")
		with intentFile:
			intentFile.write(content)
			intentFile.flush()
			fsync(intentFile.fileno())
		# A complete previous intent always survives a failed update.
		if self._localIntent:
			replace(path, self.intent)
		else:
			self._rename(path, self.intent, replaceExisting=True)

	def _checkCancelled(self):
		if self.cancelled.is_set():
			raise InterruptedError("Saving time shift was cancelled; the source has been retained")
