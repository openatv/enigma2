from collections import OrderedDict
from json import loads
from os.path import isabs, isfile, splitext
from re import search
from time import monotonic
from twisted.internet import reactor
from twisted.internet.threads import deferToThreadPool
from twisted.python.threadpool import ThreadPool

from enigma import eTimer

from Components.config import ConfigSelection, config
from Tools.MovieFileOperations import movieChangeJournal, readMovieProgress
from Tools.MovieInfoParser import getExtendedMovieDescription


class MovieVirtualFolders:
	@staticmethod
	def group(items, mode="series", separator=":", minimum=2):
		groups = {}
		for item in items:
			name = str(item.get("series") or "").strip()
			title = str(item.get("title") or "")
			if not name:
				match = search(r"(?i)(?<![a-z0-9])(?:s\d{1,2}e\d{1,3}|\d{1,2}x\d{1,3})(?![a-z0-9])", title)
				if match:
					name = title[:match.start()].strip(" ._-:")
				elif mode == "title":
					name = title.partition(separator)[0].strip() if separator else title.strip()
			if name:
				group = groups.setdefault(name.casefold(), {"title": name, "items": []})
				group["items"].append(item)
		return {key: value for key, value in groups.items() if len(value["items"]) >= minimum}


class MovieLibraryRegistry:
	VERSION = 1
	CACHE_SIZE = 256
	BATCH_SIZE = 64

	def __init__(self):
		self.providers = {}
		self.actions = {}
		self.cache = OrderedDict()
		self.pool = None
		self.changeTimer = None
		self.changeBusy = False
		self.changeAgain = False

	def register(self, name, provider, version=1, priority=0):
		if version != self.VERSION or not callable(getattr(provider, "request", None)):
			raise ValueError("Unsupported movie library provider")
		if name in self.providers:
			raise ValueError(f"Movie library provider '{name}' is already registered")
		self.providers[name] = (priority, provider)
		self.cache.clear()
		if "changes" in getattr(provider, "capabilities", ()):
			if self.changeTimer is None:
				self.changeTimer = eTimer()
				self.changeTimer.callback.append(self.synchronizeChanges)
			self.changeTimer.start(1000, True)

	def unregister(self, name, provider):
		if name in self.providers and self.providers[name][1] is provider:
			del self.providers[name]
			self.cache.clear()

	def registerAction(self, name, label, callback, multiple=False):
		if name in self.actions or not callable(callback):
			raise ValueError("Invalid or duplicate movie action")
		self.actions[name] = {"label": label, "callback": callback, "multiple": bool(multiple)}

	def unregisterAction(self, name, callback):
		if self.actions.get(name, {}).get("callback") is callback:
			del self.actions[name]

	def refreshChoices(self):
		choices = [("off", _("Disabled")), ("auto", _("Automatic")), ("e2mdb", "e2MDB")]
		choices.extend((name, getattr(provider, "label", name)) for name, (priority, provider) in sorted(self.providers.items()) if name != "e2mdb")
		setting = getattr(config.movielist, "libraryProvider", None)
		if setting is None:
			config.movielist.libraryProvider = ConfigSelection(default="off", choices=choices)
		else:
			setting.setChoices(choices, default="off")

	def getProvider(self):
		setting = getattr(getattr(config, "movielist", None), "libraryProvider", None)
		name = setting.value if setting is not None else "off"
		if name == "off":
			return None
		if name == "auto":
			return sorted(self.providers, key=lambda key: (-self.providers[key][0], key))[0] if self.providers else None
		return name if name in self.providers else None

	def getPool(self):
		if self.pool is None:
			self.pool = ThreadPool(minthreads=0, maxthreads=2, name="MovieLibrary")
			self.pool.start()
			reactor.addSystemEventTrigger("during", "shutdown", self.pool.stop)
		return self.pool

	def synchronizeChanges(self):
		if self.changeBusy:
			self.changeAgain = True
			return
		providers = [(name, provider) for name, (priority, provider) in sorted(self.providers.items()) if "changes" in getattr(provider, "capabilities", ())]
		if providers:
			self.changeBusy = True
			deferToThreadPool(reactor, self.getPool(), self.sendChanges, providers).addBoth(self.changesDone)

	def sendChanges(self, providers):
		changed = False
		try:
			for name, provider in providers:
				with movieChangeJournal.lock:
					events = []
					for event in movieChangeJournal.recover():
						if name not in event["providers"]:
							continue
						if event.get("state", "done") != "done":
							break
						events.append({key: value for key, value in event.items() if key != "files"})
						if len(events) == 64:
							break
				if events:
					result = provider.request("changes", {"events": events})
					acknowledged = set(result.get("acknowledged", ())) & {event["id"] for event in events}
					if acknowledged:
						movieChangeJournal.acknowledge(acknowledged, name)
						changed = True
					if result.get("errors"):
						print(f"[MovieLibrary] Pending catalogue changes: {result['errors']}")
			with movieChangeJournal.lock:
				pending = bool(movieChangeJournal.read())
			return changed, pending
		except Exception as error:
			print(f"[MovieLibrary] Catalogue synchronization postponed: {error}")
			return changed, True

	def changesDone(self, result):
		self.changeBusy = False
		changed, pending = result if isinstance(result, tuple) else (False, True)
		if changed:
			self.invalidate()
		if self.changeTimer is not None and (pending or self.changeAgain):
			self.changeTimer.start(1000 if self.changeAgain or changed else 60000, True)
		self.changeAgain = False
		return None

	def invalidate(self, paths=()):
		if paths:
			paths = set(paths)
			for key in tuple(self.cache):
				if key[1] in paths:
					del self.cache[key]
		else:
			self.cache.clear()

	def getCached(self, providerName, paths, databaseOnly=False):
		result = {}
		for path in paths:
			key = (providerName, path, databaseOnly)
			cached = self.cache.get(key)
			if cached is not None and cached[0] > monotonic():
				result[path] = cached[1]
				self.cache.move_to_end(key)
		return result

	def cacheDetails(self, providerName, paths, items, databaseOnly=False):
		for path in paths:
			item = items.get(path, {})
			key = (providerName, path, databaseOnly)
			self.cache[key] = (monotonic() + (60 if item else 10), item)
			self.cache.move_to_end(key)
		while len(self.cache) > self.CACHE_SIZE:
			self.cache.popitem(last=False)

	def localDetails(self, paths):
		items = {}
		for path in paths:
			title, description = getExtendedMovieDescription(path)
			if description:
				items[path] = {"path": path, "localDescription": description}
			base = splitext(path)[0]
			poster = next((name for name in (f"{base}.jpg", f"{base}.png", f"{path}.jpg") if isfile(name)), "")
			if poster:
				items.setdefault(path, {}).update(path=path, poster=poster)
			try:
				with open(f"{path}.aml.json", encoding="utf-8") as stream:
					metadata = loads(stream.read(65536))
				if isinstance(metadata, dict) and metadata.get("version") == 1:
					items.setdefault(path, {})["overrides"] = {name: metadata[name] for name in ("title", "description") if isinstance(metadata.get(name), str)}
			except (OSError, ValueError):
				pass
		return items

	def request(self, provider, operation, parameters):
		# Only plain data and provider I/O enter the worker; never Enigma service objects.
		try:
			if provider is None:
				result = {"items": {}} if operation == "details" else {"error": "unavailable"}
			else:
				result = provider.request(operation, parameters)
			if not isinstance(result, dict):
				raise ValueError("Invalid movie library response")
			if operation == "details":
				if parameters.get("databaseOnly"):
					return result
				local = self.localDetails(parameters["paths"])
				items = result.setdefault("items", {})
				for path, item in local.items():
					if item.get("localDescription"):
						items.setdefault(path, {})["localDescription"] = item["localDescription"]
					if not items.get(path, {}).get("poster"):
						items.setdefault(path, {})["poster"] = item.get("poster", "")
					items.setdefault(path, {}).update(item.get("overrides", {}))
				for path in parameters["paths"]:
					item = items.setdefault(path, {})
					item["progress"] = readMovieProgress(path, item.get("duration", 0), parameters.get("resume", {}).get(path))
			elif operation in ("browse", "members"):
				if parameters.get("databaseOnly"):
					if operation == "browse" and not result.get("physical"):
						for item in result.get("items", []):
							for field in ("progress", "season", "episode"):
								item.pop(field, None)
					return result
				items = result.get("items", [])
				local = self.localDetails([item["path"] for item in items if item.get("path")][:self.BATCH_SIZE])
				for item in items:
					values = local.get(item.get("path"), {})
					if not item.get("poster"):
						item["poster"] = values.get("poster", "")
					# A grouped series title must not become the title of its first episode.
					if operation == "members" or item.get("type") != "series":
						item.update(values.get("overrides", {}))
					if operation == "members" or result.get("physical"):
						item["progress"] = readMovieProgress(item["path"], item.get("duration", 0))
					else:
						# Group representatives do not describe every episode or file version.
						for field in ("progress", "season", "episode"):
							item.pop(field, None)
			return result
		except Exception as error:
			print(f"[MovieLibrary] Provider request failed: {error}")
			items = self.localDetails(parameters["paths"]) if operation == "details" and not parameters.get("databaseOnly") else {}
			for item in items.values():
				item.update(item.pop("overrides", {}))
			if operation == "details" and not parameters.get("databaseOnly"):
				for path in parameters["paths"]:
					items.setdefault(path, {})["progress"] = readMovieProgress(path, resume=parameters.get("resume", {}).get(path))
			return {"error": "unavailable", "items": items}


class MovieLibraryClient:
	def __init__(self):
		self.generation = 0
		self.active = False
		self.pending = None
		self.closed = False

	def cancel(self):
		self.generation += 1
		self.pending = None

	def close(self):
		self.cancel()
		self.closed = True

	def request(self, operation, parameters, callback):
		self.cancel()
		if self.closed:
			return
		providerName = movieLibrary.getProvider()
		provider = movieLibrary.providers.get(providerName, (0, None))[1]
		parameters = dict(parameters)
		if operation in ("browse", "members", "seasons"):
			setting = getattr(config.movielist, "hiddenFolders", None)
			parameters["hiddenFolders"] = list(setting.value) if setting is not None else []
		cached = {}
		if operation == "details":
			paths = tuple(dict.fromkeys(path for path in parameters.get("paths", ()) if isinstance(path, str) and isabs(path)))[:movieLibrary.BATCH_SIZE]
			cached = movieLibrary.getCached(providerName, paths, bool(parameters.get("databaseOnly")))
			parameters["paths"] = [path for path in paths if path not in cached]
			if not parameters["paths"]:
				callback({"items": cached})
				return
		self.pending = (self.generation, providerName, provider, operation, parameters, cached, callback)
		self.startRequest()

	def startRequest(self):
		if self.closed or self.active or self.pending is None:
			return
		request = self.pending
		self.pending = None
		self.active = True
		generation, providerName, provider, operation, parameters, cached, callback = request
		deferred = deferToThreadPool(reactor, movieLibrary.getPool(), movieLibrary.request, provider, operation, parameters)
		deferred.addBoth(self.requestDone, request)

	def requestDone(self, result, request):
		self.active = False
		generation, providerName, provider, operation, parameters, cached, callback = request
		if not isinstance(result, dict):
			result = {"error": "unavailable"}
		currentProvider = movieLibrary.providers.get(providerName, (0, None))[1]
		if not self.closed and generation == self.generation and providerName == movieLibrary.getProvider() and provider is currentProvider:
			if operation == "details":
				items = result.setdefault("items", {})
				movieLibrary.cacheDetails(providerName, parameters["paths"], items, bool(parameters.get("databaseOnly")))
				items.update(cached)
			try:
				callback(result)
			finally:
				self.startRequest()
		else:
			self.startRequest()
		return None


movieLibrary = MovieLibraryRegistry()
