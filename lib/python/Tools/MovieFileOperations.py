from datetime import datetime, timezone
from errno import EEXIST, EINVAL, ENOTSUP, EXDEV
from json import dumps, loads
from os import O_RDONLY, close, fsync, link, listdir, name as osName, open as openDescriptor, replace, stat, unlink
from os.path import basename, dirname, isabs, isdir, isfile, islink, join, lexists, normpath, splitext
from re import fullmatch
from shutil import copystat
from struct import Struct
from threading import RLock
from time import time
from uuid import uuid4

from Components.Task import Job, PythonTask
from Tools.Directories import SCOPE_CONFIG, resolveFilename
from Tools.EITFile import EITFile


class MovieFileBundle:
	FULL_SUFFIXES = (".meta", ".cuts", ".ap", ".sc", ".aml.json", ".aml.trash.json")
	BASE_SUFFIXES = (".eit", ".srt", ".ass", ".ssa", ".vtt", ".sub", ".idx", ".txt", ".info", ".nfo", ".jpg", ".jpeg", ".png")
	CUTS = Struct(">QI")

	def __init__(self, path, directoryNames=None, allowShared=False):
		self.path = normpath(path)
		if not isfile(self.path) or islink(self.path):
			raise ValueError(_("File operations require a regular movie file."))
		self.base = splitext(self.path)[0]
		if lexists(join(dirname(self.path), "dir.lock")):
			raise ValueError(_("This directory is locked for movie file changes."))
		candidates = {f"{self.path}{suffix}" for suffix in self.FULL_SUFFIXES + self.BASE_SUFFIXES}
		candidates.update(f"{self.base}{suffix}" for suffix in self.BASE_SUFFIXES)
		if directoryNames is None:
			directoryNames = listdir(dirname(self.path))
		if self.path.lower().endswith(".ts"):
			prefix = f"{basename(self.path)}."
			candidates.update(join(dirname(self.path), name) for name in directoryNames if name.startswith(prefix) and len(name[len(prefix):]) == 3 and name[len(prefix):].isdigit())
		for prefix in (f"{basename(self.path)}.", f"{basename(self.base)}."):
			candidates.update(join(dirname(self.path), name) for name in directoryNames if name.startswith(prefix) and fullmatch(r"(?:[a-zA-Z]{2,3}(?:[-_][a-zA-Z]{2,4})?(?:\.(?:forced|sdh|cc))?|forced|sdh|cc)\.(?:srt|ass|ssa|vtt|sub|idx)", name[len(prefix):]))
		self.files = sorted(path for path in candidates if isfile(path) and path != self.path) + [self.path]
		# A shared basename can belong to two media variants; do not take its companions away.
		shared = [path for path in self.files if not path.startswith(self.path)]
		if shared and not allowShared:
			for extension in (".ts", ".mkv", ".mp4", ".avi", ".mov", ".m2ts", ".iso"):
				other = f"{self.base}{extension}"
				if other != self.path and isfile(other):
					raise ValueError(_("Companion files are shared by multiple media files. Rename or move the variants separately after resolving their companion files."))
		if any(islink(path) for path in self.files):
			raise ValueError(_("A movie companion file is a symbolic link."))
		self.snapshot = {path: self.signature(path) for path in self.files}
		if time() - stat(self.path).st_mtime < 5:
			raise ValueError(_("The movie file is still being written. Try again later."))

	def signature(self, path):
		status = stat(path)
		return status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns

	def checkUnchanged(self):
		if any(self.signature(path) != signature for path, signature in self.snapshot.items()):
			raise ValueError(_("The recording changed while the operation was running."))

	def destinations(self, target):
		target = normpath(target)
		if target == self.path:
			raise ValueError(_("Source and destination are identical."))
		targetBase = splitext(target)[0]
		pairs = [(path, f"{target}{path[len(self.path):]}" if path.startswith(self.path) else f"{targetBase}{path[len(self.base):]}") for path in self.files]
		if len({destination for path, destination in pairs}) != len(pairs):
			raise ValueError(_("Ambiguous companion file names."))
		if any(lexists(destination) for path, destination in pairs):
			raise FileExistsError(_("A destination file already exists. No files were overwritten."))
		return pairs


def syncMovieDirectory(path):
	if osName == "posix":
		descriptor = openDescriptor(dirname(path), O_RDONLY)
		try:
			try:
				fsync(descriptor)
			except OSError as error:
				if error.errno not in (EINVAL, ENOTSUP):
					raise
		finally:
			close(descriptor)


def writeMovieText(path, text):
	temporary = f"{path}.{uuid4().hex}.tmp"
	try:
		with open(temporary, "x", encoding="utf-8") as stream:
			stream.write(text)
			stream.flush()
			fsync(stream.fileno())
		if isfile(path):
			copystat(path, temporary)
		replace(temporary, path)
		syncMovieDirectory(path)
	finally:
		if lexists(temporary):
			unlink(temporary)


class MovieCutList:
	@staticmethod
	def update(path, action="status", position=None):
		cutsPath = f"{path}.cuts"
		try:
			with open(cutsPath, "rb") as stream:
				data = stream.read(4 * 1024 * 1024 + 1)
		except FileNotFoundError:
			data = b""
		if len(data) > 4 * 1024 * 1024 or len(data) % MovieFileBundle.CUTS.size:
			raise ValueError(_("The cut list is damaged; it was left unchanged."))
		entries = list(MovieFileBundle.CUTS.iter_unpack(data))
		lastPosition = next((x[0] for x in reversed(entries) if x[1] == 3), None)
		length = next((x[0] for x in reversed(entries) if x[1] == 5), None)
		if action == "clearMarkers":
			entries = [x for x in entries if x[1] != 2]
			position = lastPosition
		elif action in ("status", "restoreResume"):
			if action == "restoreResume":
				position = next((x[0] for x in reversed(entries) if x[1] == 4), None)
				if position is None:
					raise ValueError(_("No saved playback position is available."))
			elif position is not None and position <= 0:
				raise ValueError(_("The movie duration is unknown."))
			entries = [x for x in entries if x[1] != 3]
			if lastPosition is not None and lastPosition != position:
				entries = [x for x in entries if x[1] != 4] + [(lastPosition, 4)]
			if position is not None:
				entries.append((position, 3))
		else:
			raise ValueError("Unknown cut list operation")
		temporary = f"{cutsPath}.{uuid4().hex}.tmp"
		try:
			with open(temporary, "xb") as stream:
				stream.write(b"".join(MovieFileBundle.CUTS.pack(*x) for x in sorted(entries)))
				stream.flush()
				fsync(stream.fileno())
			if isfile(cutsPath):
				copystat(cutsPath, temporary)
			replace(temporary, cutsPath)
			syncMovieDirectory(cutsPath)
		finally:
			if lexists(temporary):
				unlink(temporary)
		return {"position": position, "length": length}


def writeMovieStatus(path, position=None):
	return MovieCutList.update(path, position=position)


def createMovieEit(path, metadata):
	eitPath = f"{splitext(path)[0]}.eit"
	if lexists(eitPath):
		return False
	title = metadata.get("title") or splitext(basename(path))[0]
	description = metadata.get("description") or metadata.get("localDescription") or ""
	if not description:
		raise ValueError(_("No movie description is available to create an EIT file."))
	duration = int(metadata.get("duration") or int(metadata.get("runtime") or 0) * 60)
	start = datetime.fromtimestamp(metadata.get("recordedAt") or 0, timezone.utc)
	event = EITFile(eitPath, "und", 0, start, duration, title, metadata.get("tagline") or "", description)
	created = False
	try:
		with open(eitPath, "xb") as stream:
			created = True
			stream.write(event.Data.b)
			stream.flush()
			fsync(stream.fileno())
		syncMovieDirectory(eitPath)
	except FileExistsError:
		return False
	except OSError:
		if created:
			unlink(eitPath)
		raise
	return True


def readMovieProgress(path, duration=0, resume=None):
	position = None
	length = None
	try:
		with open(f"{path}.cuts", "rb") as stream:
			data = stream.read(65536)
		if len(data) % MovieFileBundle.CUTS.size == 0:
			for value, kind in MovieFileBundle.CUTS.iter_unpack(data):
				if kind == 3:
					position = value
				elif kind == 5:
					length = value
	except OSError:
		pass
	if resume:
		position = resume[1] if position is None else position
		length = length or resume[2]
	length = length or duration * 90000
	return None if position is None else min(100, 100 * position // length) if length else 0


class MovieChangeJournal:
	LIMIT = 2048

	def __init__(self):
		self.lock = RLock()
		self.active = set()

	def read(self):
		try:
			with open(resolveFilename(SCOPE_CONFIG, "moviechanges.json"), encoding="utf-8") as stream:
				return loads(stream.read())
		except FileNotFoundError:
			return []

	def append(self, event):
		with self.lock:
			events = self.read()
			if len(events) >= self.LIMIT:
				raise ValueError(_("Too many pending movie database changes. Reconnect the database first."))
			events.append(event)
			writeMovieText(resolveFilename(SCOPE_CONFIG, "moviechanges.json"), dumps(events, ensure_ascii=False))
			self.active.add(event["id"])

	def finish(self, identifier, success):
		with self.lock:
			try:
				events = self.read()
				for event in events:
					if event["id"] == identifier:
						event["state"] = "done" if success else "pending"
				writeMovieText(resolveFilename(SCOPE_CONFIG, "moviechanges.json"), dumps(events, ensure_ascii=False))
			finally:
				self.active.discard(identifier)

	def recover(self):
		with self.lock:
			events = self.read()
			pending = []
			changed = False
			for event in events:
				if event.get("state", "done") == "done" or event["id"] in self.active:
					pending.append(event)
					continue
				action = event["action"]
				changed = True
				applied = False
				unapplied = False
				if action in ("copy", "move", "rename", "trash", "restore"):
					applied = all(isfile(target) and stat(target).st_size == size for source, target, size in event.get("files", [])) and bool(event.get("files"))
					unapplied = all(isfile(source) and stat(source).st_size == size and not lexists(target) and isdir(dirname(target)) for source, target, size in event.get("files", []))
					if applied and isfile(event["path"]):
						event["action"] = "copy"  # A completed destination is safe even after an interrupted source cleanup.
				elif action == "delete":
					applied = all(not lexists(source) and isdir(dirname(source)) for source, target, size in event.get("files", []))
					unapplied = isfile(event["path"])
				elif action == "metadata":
					try:
						with open(f"{event['path']}.meta", encoding="utf-8", errors="replace") as stream:
							lines = stream.read().splitlines()
					except FileNotFoundError:
						lines = []
					applied = lines[1:3] == [event["title"], event["description"]]
					unapplied = not applied and isfile(event["path"])
					if applied:
						# Complete a metadata edit interrupted between its two atomic file writes.
						writeMovieText(f"{event['path']}.aml.json", dumps({"version": 1, "title": event["title"], "description": event["description"]}, ensure_ascii=False))
				elif action == "status":
					applied = True  # A projection cannot change the authoritative cut list or resume data.
				if applied:
					event["state"] = "done"
				if applied or not unapplied:
					pending.append(event)
			if changed:
				writeMovieText(resolveFilename(SCOPE_CONFIG, "moviechanges.json"), dumps(pending, ensure_ascii=False))
			return pending

	def acknowledge(self, identifiers, provider):
		with self.lock:
			events = self.read()
			for event in events:
				if event["id"] in identifiers and provider in event["providers"]:
					event["providers"].remove(provider)
			writeMovieText(resolveFilename(SCOPE_CONFIG, "moviechanges.json"), dumps([event for event in events if event["providers"]], ensure_ascii=False))


class MovieFileJob(Job):
	def __init__(self, name, operations, guard, providers=()):
		Job.__init__(self, name)
		self.results = []
		self.cancelled = False
		self.directoryNames = {}
		for operation in operations:
			MovieFileTask(self, operation, guard, tuple(providers))


class MovieFileTask(PythonTask):
	def __init__(self, job, operation, guard, providers):
		PythonTask.__init__(self, job, basename(operation["path"]))
		self.operation = dict(operation)
		self.guard = guard
		self.providers = providers
		self.guardError = ""
		self.byteTotal = 1
		self.byteDone = 0

	def prepare(self):
		# Enigma recording/playback state must only be read on the GUI thread.
		self.guardError = _("Operation cancelled.") if self.job.cancelled else self.guard(self.operation["path"])

	def abort(self):
		self.job.cancelled = True
		PythonTask.abort(self)

	def copyFile(self, source, target):
		created = False
		try:
			with open(source, "rb") as inputFile, open(target, "xb") as outputFile:
				created = True
				while True:
					if self.aborted:
						raise InterruptedError(_("Operation cancelled."))
					data = inputFile.read(1024 * 1024)
					if not data:
						break
					outputFile.write(data)
					self.byteDone += len(data)
					self.pos = self.end * self.byteDone // self.byteTotal
				outputFile.flush()
				fsync(outputFile.fileno())
			copystat(source, target)
		except Exception:
			if created:
				unlink(target)
			raise

	def transfer(self, bundle, target, move):
		pairs = bundle.destinations(target)
		self.byteTotal = max(1, sum(signature[2] for signature in bundle.snapshot.values()))
		self.byteDone = 0
		created = []
		try:
			for source, destination in pairs:
				if self.aborted:
					raise InterruptedError(_("Operation cancelled."))
				if move:
					try:
						link(source, destination)
						self.byteDone += bundle.snapshot[source][2]
						self.pos = self.end * self.byteDone // self.byteTotal
					except OSError as error:
						if error.errno == EEXIST:
							raise
						# Cross-filesystem moves and filesystems without hard links use a verified copy.
						if error.errno == EXDEV or not lexists(destination):
							self.copyFile(source, destination)
						else:
							raise
				else:
					self.copyFile(source, destination)
				created.append(destination)
			bundle.checkUnchanged()
			syncMovieDirectory(target)
		except Exception:
			for destination in reversed(created):
				unlink(destination)
			raise
		if move:
			# Only remove sources after every companion and the movie have reached the destination.
			for source, destination in pairs:
				try:
					unlink(source)
				except OSError:
					raise OSError(_("The complete movie is at the destination, but some source files could not be removed."))
			syncMovieDirectory(bundle.path)

	def work(self):
		result = dict(self.operation)
		event = None
		try:
			if self.aborted:
				raise InterruptedError(_("Operation cancelled."))
			if self.guardError:
				raise ValueError(self.guardError)
			folder = dirname(self.operation["path"])
			if folder not in self.job.directoryNames:
				self.job.directoryNames[folder] = listdir(folder)
			action = self.operation["action"]
			if action == "metadata":
				for field in ("title", "description"):
					self.operation[field] = self.operation[field].replace("\r", " ").replace("\n", " ")
			bundle = MovieFileBundle(self.operation["path"], self.job.directoryNames[folder], allowShared=action in ("status", "metadata", "markers", "eit"))
			if action == "trash":
				bundle.destinations(self.operation["target"])
				writeMovieText(f"{bundle.path}.aml.trash.json", dumps({"version": 1, "originalPath": bundle.path}, ensure_ascii=False))
				bundle = MovieFileBundle(bundle.path, self.job.directoryNames[folder])
			elif action == "restore":
				try:
					with open(f"{bundle.path}.aml.trash.json", encoding="utf-8") as stream:
						metadata = loads(stream.read(65536))
					target = metadata.get("originalPath") if metadata.get("version") == 1 else None
					if not isinstance(target, str) or not isabs(target):
						raise ValueError("Invalid original path")
				except (OSError, ValueError, AttributeError):
					raise ValueError(_("The original location is unknown. Use Move to select a destination."))
				self.operation["target"] = target
				result["target"] = target
			if self.providers and action not in ("eit", "markers"):
				pairs = bundle.destinations(self.operation["target"]) if "target" in self.operation else [(path, "") for path in bundle.files]
				event = dict(self.operation, id=uuid4().hex, providers=list(self.providers), timestamp=int(time()), state="pending", files=[(source, target, bundle.snapshot[source][2]) for source, target in pairs])
				movieChangeJournal.append(event)  # Persist intent before touching recording data.
			if action in ("copy", "move", "rename", "trash", "restore"):
				self.transfer(bundle, self.operation["target"], action != "copy")
			elif action == "delete":
				bundle.checkUnchanged()
				for path in bundle.files:
					unlink(path)
				syncMovieDirectory(bundle.path)
			elif action == "status":
				result.update(writeMovieStatus(bundle.path, self.operation.get("position")))
			elif action == "markers":
				result.update(MovieCutList.update(bundle.path, self.operation["mode"]))
			elif action == "eit":
				result["created"] = createMovieEit(bundle.path, self.operation["metadata"])
			elif action == "metadata":
				metaPath = f"{bundle.path}.meta"
				try:
					with open(metaPath, encoding="utf-8", errors="replace") as stream:
						lines = stream.read().splitlines()
				except FileNotFoundError:
					lines = [self.operation.get("service", ""), "", "", str(int(time())), ""]
				lines.extend("" for index in range(max(0, 5 - len(lines))))
				lines[1:3] = [self.operation["title"].replace("\n", " "), self.operation["description"].replace("\n", " ")]
				writeMovieText(metaPath, "\n".join(lines) + "\n")
				writeMovieText(f"{bundle.path}.aml.json", dumps({"version": 1, "title": lines[1], "description": lines[2]}, ensure_ascii=False))
			else:
				raise ValueError("Unknown movie file operation")
			result["success"] = True
		except (OSError, ValueError) as error:
			result.update(success=False, error=str(error))
		finally:
			if event is not None:
				try:
					movieChangeJournal.finish(event["id"], bool(result.get("success")))
				except (OSError, ValueError) as error:
					result["warning"] = str(error)
		self.job.results.append(result)
		self.pos = self.end
		return None


movieChangeJournal = MovieChangeJournal()
