from functools import partial
from hashlib import sha256
from os.path import basename, isdir, isfile, normpath, splitext
from uuid import uuid4

from enigma import eServiceReference, eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.MovieLibrary import MovieLibraryClient, MovieVirtualFolders, movieLibrary
from Components.MovieList import MovieList, MovieListServiceInfo
from Components.MovieListSettings import movieListSettings
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.MovieMaintenance import movieMaintenanceState


class MovieFolderView:
	def __init__(self, screen):
		self.screen = screen
		self.groups = {}
		self.bookmarks = {}
		self.rootRows = []
		self.active = None
		self.root = None
		self.cached = False
		self.rootMetadata = {}
		self.rootCached = False

	def load(self):
		root = self.screen.current_ref.getPath()
		if root != self.root:
			self.active = None
		self.root = root
		self.groups = {}
		self.bookmarks = {}
		rows = self.screen.list.list
		self.rootCached = self.screen.list.cached
		self.rootMetadata = dict(self.screen.list.movieMetadata)
		groupedPaths = set()
		virtualRows = []
		if config.movielist.latestRecordings.value:
			service = eServiceReference(eServiceReference.idFile, eServiceReference.mustDescent, "aml://latest/")
			virtualRows.append((service, MovieListServiceInfo({"title": _("Latest recordings")}), 0, None))
		if config.movielist.showBookmarks.value:
			for target in dict.fromkeys(config.movielist.videodirs.value):
				if target.startswith("/") and normpath(target) != normpath(root):
					path = f"aml://bookmark/{sha256(target.encode('utf-8')).hexdigest()}/"
					self.bookmarks[path] = target
					service = eServiceReference(eServiceReference.idFile, eServiceReference.mustDescent, path)
					item = {"title": basename(normpath(target)) or target, "description": _("Bookmark: %s") % target}
					virtualRows.append((service, MovieListServiceInfo(item), 0, None))
		mode = config.movielist.virtualGrouping.value
		if root in config.movielist.ungroupedFolders.value:
			mode = "off"
		if mode != "off":
			items = []
			byPath = {}
			for row in rows:
				service, info = row[:2]
				if info is not None and self.screen.movieActions.isMediaItem(row):
					path = service.getPath()
					item = dict(self.screen.list.movieMetadata.get(path, {}))
					item.update(path=path, title=item.get("title") or info.getName(service))
					items.append(item)
					byPath[path] = row
			for key, group in MovieVirtualFolders.group(items, mode, config.movielist.groupSeparator.value, config.movielist.groupMinimum.value).items():
				path = f"aml://series/{sha256(key.encode('utf-8')).hexdigest()}/"
				members = [byPath[x["path"]] for x in group["items"]]
				self.groups[path] = {"title": group["title"], "rows": members, "cached": self.rootCached}
				groupedPaths.update(x[0].getPath() for x in members)
				virtualRows.append(self.folderRow(path, group["title"], len(members), max(x[2] for x in members)))
		for identifier, collection in config.movielist.collections.value.items():
			path = f"aml://collection/{identifier}/"
			members = []
			for item in collection.get("items", []):
				if not isinstance(item, dict) or not str(item.get("path", "")).startswith("/") or "/.Trash/" in item["path"]:
					continue
				service = eServiceReference(eServiceReference.idDVB if splitext(item["path"])[1].lower() == ".ts" else 4097, 0, item["path"])
				members.append((service, MovieListServiceInfo(item), item.get("recordedAt") or 0, None))
			title = collection.get("title") or identifier
			self.groups[path] = {"title": title, "rows": members, "cached": True, "collection": identifier}
			virtualRows.append(self.folderRow(path, title, len(members), max((x[2] for x in members), default=0)))
		remaining = [x for x in rows if x[0].getPath() not in groupedPaths]
		parents = [x for x in remaining if x[1] is None]
		remaining = [x for x in remaining if x[1] is not None]
		sortType = self.screen.list.sort_type
		reverse = sortType in (MovieList.SORT_RECORDED, MovieList.SORT_ALPHANUMERIC_REVERSE, MovieList.SORT_ALPHANUMERIC_FLAT_REVERSE)
		dateSort = sortType in (MovieList.SORT_RECORDED, MovieList.SORT_RECORDED_REVERSE)
		key = (lambda row: row[2]) if dateSort else (lambda row: row[1].getName(row[0]).casefold())
		if config.movielist.groupFoldersFirst.value:
			self.rootRows = parents + sorted(virtualRows, key=key, reverse=reverse) + remaining
		else:
			self.rootRows = parents + sorted(virtualRows + remaining, key=key, reverse=reverse) if virtualRows else parents + remaining
		if self.active not in self.groups:
			self.active = None
		self.show()

	def folderRow(self, path, title, count, recordedAt=0):
		service = eServiceReference(eServiceReference.idFile, eServiceReference.mustDescent, path)
		item = {"title": _("%(title)s (%(count)d)") % {"title": title, "count": count}, "description": _("Virtual folder — movie files stay in their original locations."), "recordedAt": recordedAt}
		return service, MovieListServiceInfo(item), recordedAt, None

	def show(self):
		movieList = self.screen.list
		if self.active:
			group = self.groups[self.active]
			self.cached = group["cached"]
			parent = self.folderRow("aml://up/", "..", 0)
			rows = [(parent[0], None, 0, None)] + group["rows"]
			self.screen.setTitle(group["title"])
		else:
			self.cached = self.rootCached
			rows = self.rootRows
		movieList.list = rows
		movieList.markedPaths.intersection_update(x[0].getPath() for x in rows)
		if self.cached:
			movieList.movieMetadata = {x[0].getPath(): x[1].item for x in rows if x[1] is not None}
			# The player's live resume cache avoids reading sidecars on sleeping storage.
			from Screens import InfoBarGenerics
			for service, info, begin, data in rows:
				resume = InfoBarGenerics.resumePointCache.get(service.toString())
				if resume and info is not None:
					length = resume[2] or info.item.get("duration", 0) * 90000
					info.item["progress"] = min(100, 100 * resume[1] // length) if length else 0
		else:
			movieList.movieMetadata = dict(self.rootMetadata)
		movieList.l.setList(rows)
		self.screen.movieActions.updateMarks()

	def openItem(self, service):
		path = service.getPath() if service else ""
		if path == "aml://latest/":
			self.openLatest()
			return True
		if path == "aml://up/":
			return self.back()
		if path in self.bookmarks:
			target = self.bookmarks[path]
			if isdir(target):
				self.screen.gotFilename(target)
			else:
				self.screen.session.open(MessageBox, _("The bookmarked folder is not available."), type=MessageBox.TYPE_INFO)
			return True
		if path in self.groups:
			self.active = path
			self.show()
			self.screen.list.moveToIndex(0)
			self.screen.updateMovieInformation()
			return True
		return False

	def back(self):
		if self.active:
			path = self.active
			self.active = None
			self.show()
			self.screen.list.moveToIndex(next((index for index, row in enumerate(self.rootRows) if row[0].getPath() == path), 0))
			self.screen.setTitle(_("Advance Movie List"))
			self.screen.updateMovieInformation()
			return True
		return False

	def collections(self):
		choices = [(_("Create virtual collection"), "new")]
		if config.movielist.latestRecordings.value:
			choices.insert(0, (_("Latest recordings"), "latest"))
		choices.extend((x.get("title") or key, key) for key, x in config.movielist.collections.value.items())
		self.screen.session.openWithCallback(self.collectionSelected, ChoiceBox, title=_("Virtual collections"), list=choices)

	def collectionSelected(self, choice):
		if not choice:
			return
		if choice[1] == "latest":
			self.openLatest()
			return
		if choice[1] == "new":
			self.screen.session.openWithCallback(self.createCollection, VirtualKeyBoard, title=_("Collection name"))
		else:
			identifier = choice[1]
			choices = [(_("Open collection"), "open"), (_("Add selected movies"), "add"), (_("Remove selected movies from collection"), "remove"), (_("Rename collection"), "rename"), (_("Delete collection (keep movie files)"), "delete")]
			self.screen.session.openWithCallback(partial(self.changeCollection, identifier), ChoiceBox, title=choice[0], list=choices)

	def openLatest(self):
		view = self.screen.libraryView
		view.history.clear()
		view.parameters = {"view": "latest", "page": 1, "returnToFolders": not self.screen.libraryActive}
		if self.screen.libraryActive:
			view.load()
		else:
			self.screen.setMovieView(True)

	def createCollection(self, title):
		if title and title.strip():
			identifier = uuid4().hex
			config.movielist.collections.value[identifier] = {"title": title.strip(), "items": []}
			self.changeCollection(identifier, ("", "add"))

	def changeCollection(self, identifier, choice):
		if not choice or identifier not in config.movielist.collections.value:
			return
		collection = config.movielist.collections.value[identifier]
		if choice[1] == "open":
			if self.screen.libraryActive:
				view = self.screen.libraryView
				view.history.append(dict(view.parameters))
				view.parameters = {"collection": identifier, "page": 1}
				view.load()
			else:
				self.active = f"aml://collection/{identifier}/"
				self.screen.reloadList()
			return
		if choice[1] == "rename":
			self.screen.session.openWithCallback(partial(self.renameCollection, identifier), VirtualKeyBoard, title=_("Collection name"), text=collection["title"])
			return
		if choice[1] == "delete":
			del config.movielist.collections.value[identifier]
		else:
			items = {x["path"]: x for x in collection.get("items", [])}
			for service, info, begin, data in self.screen.movieActions.selectedItems():
				path = service.getPath()
				if choice[1] == "remove":
					items.pop(path, None)
				else:
					item = dict(self.screen.list.movieMetadata.get(path, {}), path=path)
					item.setdefault("title", info.getName(service))
					item.setdefault("recordedAt", begin)
					# Persist a bounded display snapshot, without provider-private payloads.
					items[path] = self.collectionSnapshot(item)
			collection["items"] = list(items.values())
		config.movielist.collections.save()
		self.screen.reloadList()

	@staticmethod
	def collectionSnapshot(item):
		fields = ("path", "title", "recordingTitle", "description", "type", "series", "season", "episode", "year", "rating", "recordedAt", "duration", "fileSize", "poster", "preview", "backdrop")
		return {key: value[:8192] if isinstance(value, str) else value for key in fields if isinstance(value := item.get(key), (str, int, float))}

	@staticmethod
	def updateCollections(results):
		changed = False
		for result in results:
			if not result.get("success") or result.get("action") not in ("move", "rename", "trash", "restore", "delete", "metadata"):
				continue
			for collection in config.movielist.collections.value.values():
				items = []
				for item in collection.get("items", []):
					if item.get("path") == result["path"]:
						changed = True
						if result["action"] == "delete":
							continue
						if result.get("target"):
							item["path"] = result["target"]
						if result["action"] == "metadata":
							item.update(title=result["title"], description=result["description"])
					items.append(item)
				collection["items"] = items
		if changed:
			config.movielist.collections.save()

	def renameCollection(self, identifier, title):
		if title and title.strip() and identifier in config.movielist.collections.value:
			config.movielist.collections.value[identifier]["title"] = title.strip()
			config.movielist.collections.save()
			self.screen.reloadList()

	def toggleGrouping(self):
		folders = set(config.movielist.ungroupedFolders.value)
		folders.symmetric_difference_update((self.screen.current_ref.getPath(),))
		config.movielist.ungroupedFolders.value = sorted(folders)
		config.movielist.ungroupedFolders.save()
		self.screen.reloadList()


class MovieLibraryView:
	def __init__(self, screen):
		self.screen = screen
		self.session = screen.session
		self.list = screen.list
		self.movieInformation = screen.movieInformation
		self.movieActions = screen.movieActions
		self.client = MovieLibraryClient()
		self.filterClient = MovieLibraryClient()
		self.filterCursors = {1: ""}
		self.parameters = {"page": 1, "type": "all", "query": ""}
		self.history = []
		self.libraryItems = {}
		self.hasMore = False
		self.busy = False
		self.physical = False
		self.refreshTimer = eTimer()
		self.refreshTimer.callback.append(self.load)
		screen["libraryActions"] = HelpableActionMap(screen, ["OkCancelActions", "ColorActions", "MoviePlayerActions", "MovieSelectionActions", "InfobarActions", "MovielistSeekActions"], {
			"ok": (self.openItem, _("Open selected movie or series")),
			"cancel": (self.back, _("Back")),
			"red": (screen.abort, _("Exit Movie Selection")),
			"green": (self.nextPage, _("Next page")),
			"yellow": (self.search, _("Search")),
			"blue": (self.filter, _("Filter")),
			"channelUp": (self.previousPage, _("Previous page")),
			"channelDown": (self.nextPage, _("Next page")),
			"contextMenu": (screen.doContext, _("Menu")),
			"showEventInfo": (screen.showEventInformation, _("Show movie information")),
			"showMovies": (screen.selectMovieView, _("View")),
			"playpauseService": (self.preview, _("Preview")),
			"leavePlayer": (screen.playbackStop, _("Stop"))
		}, prio=-1)
		screen.onClose.append(self.close)

	def close(self):
		self.client.close()
		self.filterClient.close()
		self.refreshTimer.stop()
		self.screen = None

	def updateButtons(self):
		for button, text in (("red", _("Exit")), ("green", _("Next page") if self.hasMore else ""), ("yellow", _("Search")), ("blue", _("Filter"))):
			self.screen[f"key_{button}"].text = text

	def load(self):
		if self.screen is None or not self.screen.libraryActive:
			return
		self.refreshTimer.stop()
		self.busy = True
		self.filterClient.cancel()
		self.screen["status"].text = _("Loading movie library...")
		if self.parameters.get("view") == "resume":
			# The player owns this live cache; do not maintain a second resume database.
			from Screens import InfoBarGenerics
			items = []
			for reference, resume in sorted(InfoBarGenerics.resumePointCache.items(), key=lambda item: item[1][0], reverse=True):
				service = eServiceReference(reference)
				path = service.getPath()
				if path.startswith("/") and "/.Trash/" not in path and not any(path.startswith(f"{folder.rstrip('/')}/") for folder in config.movielist.hiddenFolders.value) and resume[1] and (not resume[2] or resume[1] < resume[2]):
					items.append((path, list(resume)))
			offset = (self.parameters["page"] - 1) * 48
			pageItems = dict(items[offset:offset + 48])
			self.client.request("details", {"paths": list(pageItems), "databaseOnly": True}, partial(self.resumeLoaded, pageItems, offset + 48 < len(items)))
			return
		parameters = dict(self.parameters, databaseOnly=True)
		parameters["sort"] = self.movieActions.librarySort or (config.movielist.libraryEpisodeSort.value if parameters.get("id") else config.movielist.librarySort.value)
		if parameters.get("view") == "latest":
			parameters.update(movieListSettings.latestParameters(config.movielist.last_videodir.value))
			parameters["sort"] = self.movieActions.librarySort or parameters["sort"]
			if movieLibrary.getProvider() is None:
				if not movieMaintenanceState.catalogueReady:
					self.loaded({"items": [], "physical": True})
					self.screen["status"].text = _("Preparing latest recordings. Progress is shown in Tasks.")
					self.movieActions.scanCatalogue()
					return
				root = parameters["root"].rstrip("/")
				hidden = config.movielist.hiddenFolders.value
				items = [x for x in movieMaintenanceState.catalogue.values() if (not root or x["path"].startswith(f"{root}/")) and (x.get("recordedAt") or 0) >= parameters["since"] and not any(x["path"].startswith(f"{folder.rstrip('/')}/") for folder in hidden)]
				query = str(parameters.get("query") or "").casefold()
				if query:
					items = [x for x in items if query in f"{x.get('title', '')} {x.get('description', '')}".casefold()]
				items.sort(key=lambda item: (-(item.get("recordedAt") or 0), item["path"]))
				if parameters["limit"]:
					items = items[:parameters["limit"]]
				order = parameters["sort"]
				items.sort(key=lambda item: ((item.get("recordedAt") or 0) if order in ("newest", "oldest") else item.get("title", "").casefold(), item["path"]), reverse=order in ("newest", "titleDesc"))
				offset = (parameters["page"] - 1) * 48
				self.loaded({"items": items[offset:offset + 48], "physical": True, "hasMore": offset + 48 < len(items)})
				return
		if parameters.get("collection"):
			items = [item for item in config.movielist.collections.value.get(parameters["collection"], {}).get("items", []) if "/.Trash/" not in item["path"]]
			sortOrder = parameters["sort"]
			field = {"newest": "recordedAt", "oldest": "recordedAt", "year": "year", "rating": "rating"}.get(sortOrder)
			def sortKey(item):
				if field:
					try:
						value = float(item.get(field) or 0)
					except (TypeError, ValueError):
						value = 0
				else:
					value = str(item.get("title", "")).casefold()
				return value, item["path"]
			items = sorted(items, key=sortKey, reverse=sortOrder in ("titleDesc", "newest", "year", "rating"))
			offset = (parameters["page"] - 1) * 48
			pageItems = {item["path"]: item for item in items[offset:offset + 48] if "/.Trash/" not in item["path"]}
			self.client.request("details", {"paths": list(pageItems), "databaseOnly": True}, partial(self.collectionLoaded, pageItems, offset + 48 < len(items)))
			return
		if not parameters.get("id") and not parameters.get("view") and config.movielist.libraryGrouping.value == "files":
			parameters["view"] = "files"
		self.client.request("members" if parameters.get("id") else "browse", parameters, self.loaded)

	def collectionLoaded(self, pageItems, hasMore, result):
		items = [dict(item, **{key: value for key, value in result.get("items", {}).get(path, {}).items() if value is not None and value != ""}) for path, item in pageItems.items()]
		self.loaded({"items": items, "hasMore": hasMore, "physical": True, "error": result.get("error")})

	def resumeLoaded(self, pageItems, hasMore, result):
		items = []
		for path, resume in pageItems.items():
			item = dict(result.get("items", {}).get(path, {}), path=path)
			item.setdefault("title", basename(path))
			item["progress"] = min(100, 100 * resume[1] // resume[2]) if resume[2] else 0
			if movieListSettings.watchState(item.get("progress")) != "watched":
				items.append(item)
		self.loaded({"items": items, "hasMore": hasMore, "physical": True})

	def loaded(self, result):
		if self.screen is None or not self.screen.libraryActive:
			return
		self.busy = False
		current = self.list.getCurrent()
		currentPath = current.getPath() if current is not None else ""
		self.libraryItems = {}
		self.physical = bool(self.parameters.get("id") or result.get("physical"))
		self.screen.physical = self.physical
		# The player updates this live cache; cached browsing must never open .cuts files.
		from Screens import InfoBarGenerics
		resumeByPath = {eServiceReference(reference).getPath(): resume for reference, resume in InfoBarGenerics.resumePointCache.items()}
		rows = []
		for item in result.get("items", []):
			item = dict(item)
			item["grouped"] = not self.physical
			path = item.get("path")
			if not path:
				continue
			serviceType = eServiceReference.idDVB if splitext(path)[1].lower() == ".ts" else 4097
			service = eServiceReference(serviceType, 0, path)
			service.setName(item.get("title") or basename(path))
			if self.physical and (resume := resumeByPath.get(path)):
				length = resume[2] or (item.get("duration") or 0) * 90000
				item["progress"] = min(100, 100 * resume[1] // length) if length else 0
			rows.append((service, MovieListServiceInfo(item), item.get("recordedAt", 0), None))
			self.libraryItems[path] = item
		self.list.markedPaths.intersection_update(self.libraryItems)
		self.screen["MovieSelectionStatus"].text = _("%d movies selected") % len(self.list.markedPaths) if self.list.markedPaths else ""
		self.list.list = rows
		self.list.movieMetadata = dict(self.libraryItems)
		self.list.moviePosters.clear()
		self.list.moviePreviews.clear()
		self.list.setStyleMode("episodes" if self.physical and self.libraryItems and all(x.get("type") == "series" for x in self.libraryItems.values()) else "default")
		self.list.l.setBuildFunc(self.list.buildMovieListEntry)
		self.list.l.setList(rows)
		self.hasMore = bool(result.get("hasMore"))
		self.screen["key_green"].text = _("Next page") if self.hasMore else ""
		if result.get("error"):
			self.screen["status"].text = _("Movie database unavailable. Select files and folders from View in the menu.")
		elif not rows:
			self.screen["status"].text = _("No movies found. Select files and folders from View to see unscanned recordings.")
		else:
			self.screen["status"].text = _("Page %(page)d · %(count)d entries") % {"page": self.parameters["page"], "count": len(rows)}
		if result.get("indexing"):
			self.screen["status"].text += " · " + _("Updating library index...")
			self.refreshTimer.start(1000, True)
		self.list.moveToIndex(next((index for index, row in enumerate(rows) if row[0].getPath() == currentPath), 0))
		self.selectionChanged()

	def selectionChanged(self):
		if self.screen is None or not self.screen.libraryActive:
			return
		selection = self.getCurrentSelection()
		service = selection[0] if selection else None
		self.screen["Service"].newService(None)
		item = self.libraryItems.get(service.getPath(), {}) if service is not None else {}
		self.movieInformation.select(service, item.get("title", ""), item.get("description", ""), items=self.libraryItems)

	def preview(self):
		if self.physical and self.movieActions.isMediaItem(self.getCurrentSelection()):
			self.screen.preview()

	def nextPage(self):
		if not self.busy and self.hasMore:
			self.parameters["page"] += 1
			self.load()

	def previousPage(self):
		if not self.busy and self.parameters["page"] > 1:
			self.parameters["page"] -= 1
			self.load()

	def back(self):
		if self.history:
			self.parameters = self.history.pop()
			self.load()
		elif self.parameters.get("returnToFolders"):
			self.screen.setMovieView(False)
		else:
			self.screen.abort()

	def openItem(self):
		selection = self.getCurrentSelection()
		if selection is None or self.busy:
			return
		service = selection[0]
		item = self.libraryItems.get(service.getPath(), {})
		if not self.physical:
			provider = movieLibrary.providers.get(movieLibrary.getProvider(), (0, None))[1]
			if item.get("type") == "series" and "seasons" in getattr(provider, "capabilities", ()):
				self.busy = True
				self.client.request("seasons", {"id": item.get("group") or item.get("id")}, partial(self.seasonsLoaded, item))
				return
			self.history.append(dict(self.parameters))
			self.parameters = {"id": item.get("group") or item.get("id"), "page": 1}
			self.load()
		elif not isfile(service.getPath()):
			self.session.open(MessageBox, _("This movie is currently unavailable. Check its storage device or network mount."), type=MessageBox.TYPE_INFO)
		else:
			self.playServices([service])

	def seasonsLoaded(self, item, result):
		self.busy = False
		if result.get("error"):
			self.screen.showActionFeedback(_("Movie database unavailable"))
			return
		choices = [(_("All episodes"), None)] + [(_("Season %d") % season if season >= 0 else _("Season unknown"), season) for season in result.get("seasons", [])]
		self.session.openWithCallback(partial(self.seasonSelected, item), ChoiceBox, title=item.get("title", ""), list=choices)

	def seasonSelected(self, item, choice):
		if choice:
			self.history.append(dict(self.parameters))
			self.parameters = {"id": item.get("group") or item.get("id"), "page": 1, "season": choice[1]}
			self.load()

	def search(self):
		self.session.openWithCallback(self.searchEntered, VirtualKeyBoard, title=_("Search movie library"), text=self.parameters.get("query", ""))

	def searchEntered(self, query):
		if query is not None:
			self.history.clear()
			latest = {x: self.parameters[x] for x in ("view", "returnToFolders") if x in self.parameters} if self.parameters.get("view") == "latest" else {}
			self.parameters = dict(latest, page=1, type="all", query=query)
			self.load()

	def filter(self):
		choices = [(_("All media"), "all"), (_("Movies"), "movie"), (_("Series"), "series"), (_("Continue watching"), "resume"), (_("Latest recordings"), "latest"), (_("Unassigned / pending recordings"), "pending"), (_("Year"), "year"), (_("Genre"), "genre"), (_("Actor"), "cast"), (_("Clear filters"), "clear")]
		if movieLibrary.getProvider() is None:
			choices = [(_("Latest recordings"), "latest"), (_("Clear filters"), "clear")]
		self.session.openWithCallback(self.filterSelected, ChoiceBox, title=_("Movie library"), list=choices)

	def filterSelected(self, choice):
		if choice:
			if choice[1] in ("year", "genre", "cast"):
				provider = movieLibrary.providers.get(movieLibrary.getProvider(), (0, None))[1]
				if "filters" in getattr(provider, "capabilities", ()):
					self.filterCursors = {1: ""}
					self.loadFilters(choice[1], choice[0])
				else:
					self.session.openWithCallback(partial(self.filterEntered, choice[1]), VirtualKeyBoard, title=choice[0], text=self.parameters.get(choice[1], ""))
				return
			self.history.clear()
			returnToFolders = self.parameters.get("returnToFolders", False)
			if choice[1] == "clear":
				self.parameters = {"page": 1} if movieLibrary.getProvider() is not None else {"page": 1, "view": "latest"}
			elif choice[1] in ("latest", "pending", "resume"):
				self.parameters = {"page": 1, "view": choice[1]}
			else:
				self.parameters = {"page": 1, "type": choice[1], "query": self.parameters.get("query", "")}
			self.parameters["returnToFolders"] = returnToFolders
			self.load()

	def loadFilters(self, field, title, page=1):
		self.filterClient.request("filters", dict(self.parameters, field=field, filterPage=page, filterAfter=self.filterCursors.get(page, "")), partial(self.filtersLoaded, field, title, page))

	def filtersLoaded(self, field, title, page, result):
		if self.screen is None or not self.screen.libraryActive or self.session.current_dialog is not self.screen:
			return
		if result.get("error"):
			self.screen.showActionFeedback(_("Movie database unavailable"))
			return
		values = [x for x in result.get("values", []) if isinstance(x, str) and x]
		choices = [(_("All"), "")] + [(x, x) for x in values]
		if page > 1:
			choices.append((_("Previous page"), page - 1))
		if result.get("hasMore") and values:
			self.filterCursors[page + 1] = values[-1]
			choices.append((_("Next page"), page + 1))
		if result.get("indexing"):
			choices.append((_("Updating library index...") + " " + _("Refresh"), page))
		selection = next((index for index, choice in enumerate(choices) if choice[1] == self.parameters.get(field, "")), 0)
		self.session.openWithCallback(partial(self.filterValueSelected, field, title), ChoiceBox, title=title, list=choices, selection=selection)

	def filterValueSelected(self, field, title, choice):
		if choice is not None:
			if isinstance(choice[1], int):
				self.loadFilters(field, title, choice[1])
			else:
				self.parameters["exactFilters"] = True
				self.filterEntered(field, choice[1])

	def filterEntered(self, field, value):
		if value is not None:
			self.history.clear()
			self.parameters.pop("id", None)
			self.parameters.pop("season", None)
			self.parameters.pop("view", None)
			self.parameters.update(page=1)
			self.parameters[field] = value.strip()
			self.load()

	def getMenu(self):
		choices = [(_("View") + "...", self.screen.selectMovieView), (_("Temporary layout and sorting"), self.movieActions.temporaryView), (_("Virtual collections"), self.screen.folderView.collections), (_("Play queue / playlists"), self.movieActions.queueMenu), (_("Hidden folders"), self.movieActions.hiddenFolders), (_("Settings") + "...", self.screen.configure), (_("Refresh library"), self.load)]
		choices.append((_("Movie maintenance"), self.movieActions.maintenance))
		if movieLibrary.getProvider() is None and self.parameters.get("view") == "latest":
			choices.append((_("Update movie folder snapshot"), self.movieActions.scanCatalogue))
		if not self.physical and self.getCurrentSelection() is not None:
			choices.append((_("Open selected movie or series"), self.openItem))
		if self.physical and self.getCurrentSelection() is not None:
			choices.extend([(_("Mark / unmark movie"), self.movieActions.toggleMark), (_("Select all movies on this page"), self.movieActions.markAll), (_("Clear movie selection"), self.movieActions.clearMarks), (_("Edit movie"), self.movieActions.renameMenu), (_("Move"), partial(self.movieActions.transfer, "move")), (_("Copy"), partial(self.movieActions.transfer, "copy")), (_("Delete"), self.movieActions.delete), (_("Mark as watched"), partial(self.movieActions.setWatched, True)), (_("Mark as unwatched"), partial(self.movieActions.setWatched, False))])
			selected = tuple(item[0] for item in self.movieActions.selectedItems())
			choices.extend([(_("Play selected movies"), self.movieActions.playSelected), (_("Chapter markers and playback position"), self.movieActions.markers)])
			if config.movielist.eitMode.value != "off":
				choices.append((_("Create missing EIT files"), self.movieActions.createEit))
			choices.extend((action["label"], partial(action["callback"], self.session, selected)) for name, action in sorted(movieLibrary.actions.items()) if action["multiple"] or len(selected) == 1)
			choices.extend((plugin.description, partial(plugin, self.session, self.getCurrentSelection()[0])) for plugin in plugins.getPlugins(PluginDescriptor.WHERE_MOVIELIST))
		return choices

	def playServices(self, services, index=0):
		self.screen.playServices(services, index)

	def getCurrentSelection(self):
		return self.list.l.getCurrentSelection()
