from collections import OrderedDict
from os import listdir, lstat, scandir, stat, unlink
from os.path import basename, dirname, isabs, isfile, islink, join, lexists, normpath, realpath, splitext
from stat import S_ISREG
from time import monotonic, time

from Components.FileList import KNOWN_EXTENSIONS, MOVIE_EXTENSIONS
from Components.Task import Job, PythonTask
from Tools.MovieFileOperations import readMovieProgress
from Tools.Trashcan import TRASHCAN


class MovieMaintenanceState:
	def __init__(self):
		self.items = {}
		self.scan = None
		self.running = False
		self.directories = OrderedDict()
		self.directorySettings = {}
		self.catalogue = {}
		self.catalogueReady = False
		self.catalogueRunning = False
		self.catalogueRevision = 0
		self.newCounts = {}

	def update(self, root, items):
		root = normpath(root)
		self.items = {path: value for path, value in self.items.items() if path != root and not path.startswith(join(root, ""))}
		self.items.update(items)
		while len(self.items) > 4096:
			self.items.pop(next(iter(self.items)))

	def invalidate(self, paths=()):
		self.catalogueRevision += 1
		if not paths:
			self.items.clear()
			self.directories.clear()
		else:
			paths = {normpath(x) for x in paths if x}
			for folder in tuple(self.items):
				if any(x == folder or x.startswith(join(folder, "")) or folder.startswith(join(x, "")) for x in paths):
					del self.items[folder]
			for folder in tuple(self.directories):
				if any(dirname(x) == folder or x == folder or folder.startswith(join(x, "")) for x in paths):
					del self.directories[folder]
		self.directorySettings = {x: self.directorySettings[x] for x in self.directorySettings if x in self.directories}

	def getDirectory(self, path, lifetime):
		cached = self.directories.get(normpath(path))
		if lifetime and cached is not None and monotonic() - cached[0] < lifetime:
			self.directories.move_to_end(normpath(path))
			return cached[1]
		return None

	def cacheDirectory(self, path, rows):
		self.directories[normpath(path)] = (monotonic(), rows)
		self.directories.move_to_end(normpath(path))
		while len(self.directories) > 32 or sum(len(x[1]) for x in self.directories.values()) > 10000:
			self.directories.popitem(last=False)
		self.directorySettings = {x: self.directorySettings[x] for x in self.directorySettings if x in self.directories}

	def applyChanges(self, results):
		paths = set()
		for result in results:
			path = result["path"]
			paths.add(path)  # Failed operations may also have partially changed companions.
			if result.get("target"):
				paths.add(result["target"])
			if not result.get("success"):
				continue
			item = self.catalogue.get(path)
			if item is not None:
				action = result.get("action")
				if action in ("delete", "trash", "move", "rename", "restore"):
					self.catalogue.pop(path, None)
				if action in ("copy", "move", "rename", "restore"):
					self.catalogue[result["target"]] = dict(item, path=result["target"])
				elif action in ("status", "markers"):
					length = result.get("length") or item.get("duration", 0) * 90000
					position = result.get("position")
					item["progress"] = min(100, 100 * position // length) if position is not None and length else None
				elif action == "metadata":
					item.update(title=result["title"], description=result["description"])
		if paths:
			self.invalidate(paths)
		return paths

	def get(self, path):
		return self.items.get(normpath(path))


class MovieStructure:
	@staticmethod
	def detect(path, dvd=True, bluray=True, movie=False):
		if dvd:
			for candidate in (path, join(path, "VIDEO_TS"), join(path, "DVD", "VIDEO_TS")):
				if isfile(join(candidate, "VIDEO_TS.IFO")):
					return {"mediaStructure": "DVD", "playPath": candidate}
		if bluray:
			for candidate in (path, join(path, "BDMV"), join(path, "BRD", "BDMV")):
				if isfile(join(candidate, "index.bdmv")):
					return {"mediaStructure": "Blu-ray", "playPath": dirname(candidate)}
		if movie:
			for extension in sorted(MOVIE_EXTENSIONS):
				candidate = join(path, f"{basename(normpath(path))}{extension}")
				if isfile(candidate):
					return {"mediaStructure": _("Movie"), "playPath": candidate}
		return {}


class MovieCatalogueJob(Job):
	def __init__(self, roots, hidden, followLinks, resumes):
		Job.__init__(self, _("Update movie folder snapshot"))
		self.roots = roots
		self.hidden = {normpath(x) for x in hidden}
		self.followLinks = followLinks
		self.resumes = resumes
		self.items = {}
		self.statistics = {}
		self.revision = movieMaintenanceState.catalogueRevision
		MovieCatalogueScan(self)


class MovieCatalogueScan(PythonTask):
	def __init__(self, job):
		PythonTask.__init__(self, job, _("Read movie folders"))
		self.visited = set()
		self.entries = 0

	def work(self):
		for root in sorted(self.job.roots, key=lambda path: (len(path), path)):
			if isabs(root) and normpath(root) != "/":
				try:
					self.walk(normpath(root), 0)
				except FileNotFoundError:
					continue  # Disconnected bookmarks must not discard available roots.
		self.pos = self.end

	def walk(self, folder, depth):
		if self.aborted:
			raise InterruptedError(_("Operation cancelled."))
		if depth > 64 or self.entries > 100000 or len(self.job.items) > 20000:
			raise ValueError(_("Too many entries. Scan a smaller movie folder."))
		if any(folder == x or folder.startswith(join(x, "")) for x in self.job.hidden) or not self.job.followLinks and islink(folder):
			return 0, 0
		status = stat(folder)
		identity = (status.st_dev, status.st_ino)
		if identity in self.visited or lexists(join(folder, "dir.lock")) or lexists(join(folder, ".noscan")):
			return 0, 0
		self.visited.add(identity)
		count = size = 0
		with scandir(folder) as entries:
			for entry in entries:
				self.entries += 1
				if self.aborted or self.entries > 100000:
					raise InterruptedError(_("Scan cancelled or folder limit reached."))
				if entry.name.startswith(".") or entry.name == TRASHCAN or entry.is_symlink() and not self.job.followLinks:
					continue
				try:
					if entry.is_dir():
						childCount, childSize = self.walk(entry.path, depth + 1)
						count += childCount
						size += childSize
					elif splitext(entry.name)[1].lower() in MOVIE_EXTENSIONS and entry.is_file():
						status = entry.stat()
						item = {"path": entry.path, "title": entry.name, "recordedAt": int(status.st_mtime), "fileSize": status.st_size}
						try:
							with open(f"{entry.path}.meta", encoding="utf-8", errors="replace") as stream:
								lines = stream.read(16384).splitlines()
							if len(lines) >= 4:
								item.update(title=lines[1][:512] or entry.name, description=lines[2][:4096], recordedAt=int(lines[3]), serviceReference=lines[0])
						except (OSError, ValueError):
							pass
						item["progress"] = readMovieProgress(entry.path, resume=self.job.resumes.get(entry.path))
						self.job.items[entry.path] = item
						if len(self.job.items) > 20000:
							raise ValueError(_("Too many movies. Scan a smaller movie folder."))
						count += 1
						size += status.st_size
					self.pos = min(self.end - 1, self.entries * self.end // 100000)
				except FileNotFoundError:
					pass  # A recording or a link can disappear while scanning.
		self.job.statistics[folder] = (count, size)
		return count, size


class MovieMaintenanceJob(Job):
	def __init__(self, root, mode, resumes, watchedPercent, age):
		Job.__init__(self, _("Movie maintenance"))
		self.root = normpath(root)
		self.mode = mode
		self.candidates = []
		self.statistics = {}
		MovieMaintenanceScan(self, resumes, watchedPercent, age)


class MovieMaintenanceScan(PythonTask):
	LIMIT = 100000
	CANDIDATE_LIMIT = 2000

	def __init__(self, job, resumes, watchedPercent, age):
		PythonTask.__init__(self, job, _("Scan movie folders"))
		self.resumes = resumes
		self.watchedPercent = watchedPercent
		self.cutoff = time() - age * 86400
		self.visited = 0

	@staticmethod
	def signature(path):
		status = lstat(path)
		return status.st_dev, status.st_ino, status.st_size, status.st_mtime_ns

	@staticmethod
	def orphanBase(path, names, mediaBases=None):
		stem, suffix = splitext(basename(path))
		if suffix.lower() not in (".ap", ".sc", ".cuts", ".meta", ".eit"):
			return None
		base, extension = splitext(stem)
		if extension.lower() not in KNOWN_EXTENSIONS:
			base = stem
		if mediaBases is None:
			mediaBases = {splitext(name)[0] for name in names if splitext(name)[1].lower() in KNOWN_EXTENSIONS}
		# Keep companions whenever another media variant may own them.
		if stem in names or base in mediaBases:
			return None
		return join(dirname(path), stem)

	def work(self):
		root = self.job.root
		if not isabs(root) or root == "/" or islink(root) or TRASHCAN in root.split("/"):
			raise ValueError(_("Select a movie folder outside the trashcan."))
		self.rootDevice = stat(root).st_dev
		self.walk(root, 0)
		self.pos = self.end

	def walk(self, folder, depth):
		if self.aborted:
			raise InterruptedError(_("Operation cancelled."))
		if depth > 64 or self.visited > self.LIMIT:
			raise ValueError(_("Too many entries. Scan a smaller movie folder."))
		if lexists(join(folder, "dir.lock")):
			return 0, 0
		with scandir(folder) as iterator:
			entries = []
			for entry in iterator:
				self.visited += 1
				if self.aborted or self.visited > self.LIMIT:
					raise InterruptedError(_("Scan cancelled or folder limit reached."))
				entries.append(entry)
		names = {entry.name for entry in entries}
		mediaBases = {splitext(name)[0] for name in names if splitext(name)[1].lower() in KNOWN_EXTENSIONS} if self.job.mode == "orphans" else set()
		count = size = 0
		for entry in entries:
			if self.aborted:
				raise InterruptedError(_("Operation cancelled."))
			if entry.is_symlink() or entry.name.startswith(".") or entry.name == TRASHCAN:
				continue
			status = entry.stat(follow_symlinks=False)
			if status.st_dev != self.rootDevice:
				continue
			if entry.is_dir(follow_symlinks=False):
				childCount, childSize = self.walk(entry.path, depth + 1)
				count += childCount
				size += childSize
			elif entry.is_file(follow_symlinks=False):
				if splitext(entry.name)[1].lower() in MOVIE_EXTENSIONS:
					count += 1
					size += status.st_size
					if self.job.mode == "watched":
						self.watched(entry.path, status)
				elif self.job.mode == "orphans" and time() - status.st_mtime > 60:
					base = self.orphanBase(entry.path, names, mediaBases)
					if base:
						self.job.candidates.append({"path": entry.path, "base": base, "signature": self.signature(entry.path), "parent": realpath(folder)})
			if len(self.job.candidates) > self.CANDIDATE_LIMIT:
				raise ValueError(_("Too many candidates. Scan a smaller movie folder."))
			self.pos = min(self.end - 1, self.visited * self.end // self.LIMIT)
		self.job.statistics[folder] = (count, size)
		return count, size

	def watched(self, path, status):
		resume = self.resumes.get(path)
		cuts = f"{path}.cuts"
		cutSignature = self.signature(cuts) if lexists(cuts) and not islink(cuts) else None
		lastUsed = max(status.st_mtime, cutSignature[3] / 1000000000 if cutSignature else 0, resume[0] if resume else 0)
		if lastUsed >= self.cutoff:
			return
		progress = readMovieProgress(path, resume=resume)
		if progress is not None and progress >= self.watchedPercent:
			self.job.candidates.append({"path": path, "expected": {path: self.signature(path), cuts: cutSignature}})


class MovieOrphanJob(Job):
	def __init__(self, candidates, guard):
		Job.__init__(self, _("Remove orphaned movie companion files"))
		self.results = []
		self.cancelled = False
		for candidate in candidates:
			MovieOrphanTask(self, candidate, guard)


class MovieOrphanTask(PythonTask):
	def __init__(self, job, candidate, guard):
		PythonTask.__init__(self, job, basename(candidate["path"]))
		self.candidate = candidate
		self.guard = guard

	def prepare(self):
		self.guardError = _("Operation cancelled.") if self.job.cancelled else self.guard(self.candidate["base"])

	def abort(self):
		self.job.cancelled = True
		PythonTask.abort(self)

	def work(self):
		path = self.candidate["path"]
		result = {"path": path, "success": False}
		try:
			if self.aborted or self.guardError:
				raise ValueError(self.guardError or _("Operation cancelled."))
			parent = dirname(path)
			if realpath(parent) != self.candidate["parent"] or lexists(join(parent, "dir.lock")) or not S_ISREG(lstat(path).st_mode):
				raise ValueError(_("The movie folder or companion file changed."))
			if MovieMaintenanceScan.signature(path) != self.candidate["signature"] or not MovieMaintenanceScan.orphanBase(path, set(listdir(parent))):
				raise ValueError(_("The companion file changed or belongs to a movie again."))
			unlink(path)
			result["success"] = True
		except (OSError, ValueError) as error:
			result["error"] = str(error)
		self.job.results.append(result)
		self.pos = self.end


movieMaintenanceState = MovieMaintenanceState()
