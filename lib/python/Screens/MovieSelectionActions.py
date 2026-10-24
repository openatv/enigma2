from functools import partial
from os.path import basename, dirname, join, normpath, splitext
from re import sub
from time import time
from twisted.internet import reactor
from twisted.internet.threads import deferToThreadPool

from enigma import eServiceReference, iServiceInformation

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigText, ConfigYesNo, config, getConfigListEntry
from Components.FileList import AUDIO_EXTENSIONS, DVD_EXTENSIONS, MOVIE_EXTENSIONS
from Components.MovieLibrary import MovieLibraryClient, movieLibrary
from Components.MovieListSettings import movieListSettings
from Components.Task import job_manager
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.LocationBox import MovieLocationBox
from Screens.MessageBox import MessageBox
from Screens.MovieLibrary import MovieFolderView
from Screens.Setup import Setup
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.MovieFileOperations import MovieFileJob
from Tools.MovieMaintenance import MovieCatalogueJob, MovieMaintenanceJob, MovieOrphanJob, movieMaintenanceState
from Tools.MoviePlaylist import moviePlayQueue, readMoviePlaylist, writeMoviePlaylist
from Tools.Notifications import AddNotification
from Tools.Trashcan import TRASHCAN, createTrashcan


def movieOperationGuard(session, path):
	playing = session.nav.getCurrentlyPlayingServiceReference()
	if playing is not None and normpath(playing.getPath()) == normpath(path):
		return _("Stop playback or preview before changing this movie.")
	base = splitext(normpath(path))[0]
	for timer in session.nav.RecordTimer.timer_list:
		if timer.isRunning() and not timer.justplay and normpath(getattr(timer, "Filename", "") or "") in (base, normpath(path)):
			return _("The movie is currently being recorded.")
	return ""


def updateMovieResumePoints(results):
	MovieFolderView.updateCollections(results)
	# InfoBarGenerics imports MovieSelection; resolve its live cache only after startup.
	from Screens import InfoBarGenerics
	changed = False
	for result in results:
		if not result.get("success"):
			continue
		oldReference = result.get("reference")
		if not oldReference:
			continue
		action = result["action"]
		if action in ("move", "rename", "trash", "restore", "copy"):
			entry = InfoBarGenerics.resumePointCache.get(oldReference)
			if entry is not None:
				newReference = eServiceReference(oldReference)
				newReference.setPath(result["target"])
				InfoBarGenerics.resumePointCache[newReference.toString()] = list(entry)
				if action != "copy":
					del InfoBarGenerics.resumePointCache[oldReference]
				changed = True
		elif action in ("status", "markers") and result.get("position") is not None:
			previous = InfoBarGenerics.resumePointCache.get(oldReference)
			length = result.get("length") or (previous[2] if previous else None)
			if action == "status" and result.get("position"):
				length = length or result["position"]
			InfoBarGenerics.resumePointCache[oldReference] = [int(time()), result["position"], length]
			changed = True
		elif action in ("delete", "status", "markers"):
			if oldReference in InfoBarGenerics.resumePointCache:
				del InfoBarGenerics.resumePointCache[oldReference]
				changed = True
	if changed:
		InfoBarGenerics.saveResumePoints()


class MovieMetadataEditor(Setup):
	def __init__(self, session, title, description):
		self.movieTitle = ConfigText(default=title, fixed_size=False)
		self.movieDescription = ConfigText(default=description, fixed_size=False)
		Setup.__init__(self, session, setup="")
		self.setTitle(_("Edit recording information"))

	def createSetup(self):
		self["config"].list = [getConfigListEntry(_("Title"), self.movieTitle), getConfigListEntry(_("Description"), self.movieDescription)]

	def keySave(self):
		if self.movieTitle.value.strip():
			self.close((self.movieTitle.value.strip(), self.movieDescription.value))
		else:
			self.session.open(MessageBox, _("Enter a movie title."), type=MessageBox.TYPE_ERROR)


class MovieMaintenanceReview(Setup):
	def __init__(self, session, candidates):
		self.candidates = [(candidate, ConfigYesNo(default=False)) for candidate in candidates]
		Setup.__init__(self, session, setup="")
		self.setTitle(_("Select maintenance candidates"))
		self["key_green"].setText(_("Continue"))

	def createSetup(self):
		self["config"].list = [getConfigListEntry(basename(candidate["path"]), selected, candidate["path"]) for candidate, selected in self.candidates]

	def keySave(self):
		self.close([candidate for candidate, selected in self.candidates if selected.value])


class MoviePlayerFileActions:
	def __init__(self, screen):
		self.screen = screen
		self.pending = False
		screen.onClose.append(self.close)

	def close(self):
		self.screen = None

	def delete(self, answer):
		if self.pending or self.screen is None:
			return
		service = self.screen.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service is None or not service.getPath().startswith("/"):
			self.screen.is_closing = False
			self.screen.session.open(MessageBox, _("This service is not a local movie file."), type=MessageBox.TYPE_ERROR)
			return
		operation = {"action": "delete", "path": service.getPath(), "reference": service.toString()}
		trash = config.usage.movielist_trashcan.value and TRASHCAN not in normpath(service.getPath()).split("/")
		if trash:
			destination = createTrashcan(service.getPath())
			if not destination:
				self.screen.is_closing = False
				self.screen.session.open(MessageBox, _("Cannot create the trashcan."), type=MessageBox.TYPE_ERROR)
				return
			operation.update(action="trash", target=join(destination, basename(service.getPath())))
		returnToList = answer.startswith("deleteandmovielist")
		if answer.endswith("confirmed") or trash and not config.usage.movielistTrashcanConfirm.value:
			self.confirmed(operation, returnToList, True)
		else:
			message = (_("Move '%s' and its companion files to the trashcan?") if trash else _("Permanently delete '%s' and its companion files?")) % basename(service.getPath())
			self.screen.session.openWithCallback(partial(self.confirmed, operation, returnToList), MessageBox, message, type=MessageBox.TYPE_YESNO, default=False)

	def confirmed(self, operation, returnToList, confirmed):
		if self.screen is None:
			return
		if not confirmed:
			self.screen.is_closing = False
			return
		self.pending = True
		session = self.screen.session
		current = session.nav.getCurrentlyPlayingServiceOrGroup()
		if current is None or current.toString() != operation["reference"]:
			self.pending = False
			self.screen.is_closing = False
			self.screen.session.open(MessageBox, _("Playback changed. Select the movie again before deleting it."), type=MessageBox.TYPE_INFO)
			return
		session.nav.stopService()
		providers = [name for name, (priority, provider) in movieLibrary.providers.items() if "changes" in getattr(provider, "capabilities", ())]
		job = MovieFileJob(_("Movie file operations"), [operation], partial(movieOperationGuard, session), providers)
		job_manager.AddJob(job, onSuccess=partial(self.finished, returnToList))

	def finished(self, returnToList, job):
		self.pending = False
		paths = movieMaintenanceState.applyChanges(job.results)
		movieListSettings.updateNewCounts()
		updateMovieResumePoints(job.results)
		if paths:
			movieLibrary.invalidate(paths)
		movieLibrary.synchronizeChanges()
		result = job.results[0]
		if self.screen is not None:
			if result.get("success"):
				if returnToList and self.screen.fromMovieSelection:
					self.screen.movielistAgain()
				else:
					self.screen.close()
			else:
				self.screen.is_closing = False
		if not result.get("success") or result.get("warning"):
			AddNotification(MessageBox, result.get("error") or result.get("warning"), type=MessageBox.TYPE_ERROR)


class MovieSelectionActions:
	def __init__(self, screen):
		self.screen = screen
		self.client = MovieLibraryClient()
		self.seriesPending = []
		self.seriesProposals = []
		self.seriesSkipped = 0
		self.eitPending = []
		self.eitOperations = []
		self.eitAttempted = set()
		self.screenStyle = None
		self.widgetStyle = None
		self.sortType = None
		self.librarySort = None
		self.markDirection = "down"
		moviePlayQueue.configure()
		screen["temporaryMovieActions"] = HelpableActionMap(screen, ["MovieSelectionActions"], {
			"temporaryMovieView": (self.temporaryView, _("Select view and sorting for this movie list"))
		}, prio=-2)
		screen["MovieSelectionStatus"] = StaticText()
		screen.onClose.append(self.close)

	def close(self):
		self.client.close()
		self.screen = None

	def selectedItems(self):
		if self.screen is None:
			return []
		if not getattr(self.screen, "physical", True):
			return []
		movieList = self.screen.list
		if movieList.markedPaths:
			return [item for item in movieList.list if self.isMediaItem(item) and item[0].getPath() in movieList.markedPaths]
		item = self.screen.getCurrentSelection()
		return [item] if self.isMediaItem(item) else []

	def isMediaItem(self, item):
		return item is not None and not item[0].flags & eServiceReference.mustDescent and splitext(item[0].getPath())[1].lower() in MOVIE_EXTENSIONS | AUDIO_EXTENSIONS | DVD_EXTENSIONS

	def updateMarks(self):
		count = len(self.screen.list.markedPaths)
		selectionStatus = self.screen["MovieSelectionStatus"]
		selectionStatus.text = _("%d movies selected") % count if count else ""
		self.screen.list.l.invalidate()
		if not selectionStatus.downstream_elements:
			self.screen.showActionFeedback(selectionStatus.text)

	def hideFolder(self):
		item = self.screen.getCurrentSelection()
		if item is not None and item[1] is not None and item[0].flags & eServiceReference.mustDescent:
			path = normpath(item[0].getPath())
			if path != "/":
				if len(config.movielist.hiddenFolders.value) >= 256:
					self.screen.session.open(MessageBox, _("Up to 256 folders can be hidden."), type=MessageBox.TYPE_INFO)
					return
				config.movielist.hiddenFolders.value = sorted(set(config.movielist.hiddenFolders.value) | {path})
				config.movielist.hiddenFolders.save()
				self.screen.reloadList()

	def hiddenFolders(self):
		choices = [(path, path) for path in config.movielist.hiddenFolders.value]
		self.screen.session.openWithCallback(self.unhideFolder, ChoiceBox, title=_("Select a folder to show again. This does not change database scan paths."), list=choices or [(_("No hidden folders"), None)])

	def unhideFolder(self, choice):
		if choice and choice[1] is not None:
			config.movielist.hiddenFolders.value = [path for path in config.movielist.hiddenFolders.value if path != choice[1]]
			config.movielist.hiddenFolders.save()
			self.screen.reloadList()

	def toggleMark(self):
		item = self.screen.getCurrentSelection()
		if self.isMediaItem(item):
			path = item[0].getPath()
			marks = self.screen.list.markedPaths
			if path in marks:
				marks.remove(path)
			else:
				marks.add(path)
			self.screen.list.invalidateMoviePaths((path,))
			self.updateMarks()
			mode = config.movielist.markAdvance.value
			if mode != "stay":
				movieList = self.screen.list
				start = movieList.getCurrentIndex()
				direction = self.markDirection if mode == "direction" else "down"
				for attempt in range(len(movieList.list)):
					previous = movieList.getCurrentIndex()
					# MovieList already handles one-entry movement in lists and grids.
					movieList.moveUp() if direction == "up" else movieList.moveDown()
					index = movieList.getCurrentIndex()
					if self.isMediaItem(self.screen.getCurrentSelection()):
						break
					if index in (start, previous):
						movieList.moveToIndex(start)
						break

	def markAll(self):
		self.screen.list.markedPaths = {item[0].getPath() for item in self.screen.list.list if self.isMediaItem(item)}
		self.screen.list.invalidateMoviePaths(self.screen.list.markedPaths)
		self.updateMarks()

	def clearMarks(self):
		paths = self.screen.list.markedPaths
		self.screen.list.markedPaths = set()
		self.screen.list.invalidateMoviePaths(paths)
		self.updateMarks()

	def operations(self, action):
		return [{"action": action, "path": item[0].getPath(), "reference": item[0].toString()} for item in self.selectedItems()]

	def temporaryView(self):
		choices = [(_("Files or database"), self.screen.selectMovieView), (_("Screen layout"), partial(self.temporaryStyle, "screenStyle")), (_("List or grid style"), partial(self.temporaryStyle, "widgetStyle")), (_("Sort by"), self.temporarySort), (_("Use configured defaults"), self.resetTemporaryView)]
		self.screen.session.openWithCallback(lambda choice: choice[1]() if choice else None, ChoiceBox, title=_("View for this movie list only"), list=choices)

	def temporaryStyle(self, name):
		setting = getattr(config.movielist, name)
		choices = [(setting.description[x], x) for x in setting.choices]
		self.screen.session.openWithCallback(partial(self.temporaryStyleSelected, name), ChoiceBox, title=_("View for this movie list only"), list=choices)

	def temporaryStyleSelected(self, name, choice):
		if choice:
			setattr(self, name, choice[1])
			self.screen.setMovieView(self.screen.libraryActive, force=True)

	def temporarySort(self):
		if self.screen.libraryActive:
			setting = config.movielist.libraryEpisodeSort if self.screen.libraryView.parameters.get("id") else config.movielist.librarySort
			choices = [(setting.description[x], x) for x in setting.choices]
			self.screen.session.openWithCallback(self.librarySortSelected, ChoiceBox, title=_("Sort this movie list"), list=choices)
			return
		# MovieSelection imports these actions; obtain its existing sort choices after startup.
		from Screens.MovieSelection import l_moviesort
		choices = [(x[1], x[0]) for x in l_moviesort]
		self.screen.session.openWithCallback(self.temporarySortSelected, ChoiceBox, title=_("Sort this movie list"), list=choices)

	def temporarySortSelected(self, choice):
		if choice:
			self.sortType = int(choice[1])
			self.screen.reloadList()

	def librarySortSelected(self, choice):
		if choice:
			self.librarySort = choice[1]
			self.screen.libraryView.parameters["page"] = 1
			self.screen.reloadList()

	def resetTemporaryView(self):
		self.screenStyle = self.widgetStyle = self.sortType = self.librarySort = None
		self.screen.setMovieView(self.screen.libraryActive, force=True)

	def playSelected(self):
		services = [x[0] for x in self.selectedItems()]
		if services:
			if any(splitext(x.getPath())[1].lower() in DVD_EXTENSIONS for x in services):
				self.screen.session.open(MessageBox, _("Open DVD images individually with the DVD player."), type=MessageBox.TYPE_INFO)
			else:
				self.screen.playServices(services)

	def markers(self):
		choices = [(_("Remove chapter markers (keep cuts and resume position)"), "clearMarkers"), (_("Restore previous playback position"), "restoreResume")]
		self.screen.session.openWithCallback(self.markersSelected, ChoiceBox, title=_("Chapter markers and playback position"), list=choices)

	def markersSelected(self, choice):
		if choice:
			operations = [dict(x, mode=choice[1]) for x in self.operations("markers")]
			if operations:
				self.screen.session.openWithCallback(lambda confirmed: self.run(operations) if confirmed else None, MessageBox, _("Apply '%(action)s' to %(count)d selected movies?") % {"action": choice[0], "count": len(operations)}, type=MessageBox.TYPE_YESNO, default=False)

	def createEit(self):
		self.eitPending = []
		self.eitOperations = []
		for service, info, *data in self.selectedItems():
			metadata = dict(self.screen.list.movieMetadata.get(service.getPath(), {}))
			if info is not None:
				metadata.setdefault("title", info.getName(service))
				event = info.getEvent(service)
				if not metadata.get("description"):
					metadata["description"] = event.getExtendedDescription() if event else info.getInfoString(service, iServiceInformation.sDescription)
				metadata.setdefault("duration", max(0, info.getLength(service)))
				metadata.setdefault("recordedAt", max(0, info.getInfo(service, iServiceInformation.sTimeCreate)))
			self.eitPending.append({"action": "eit", "path": service.getPath(), "reference": service.toString(), "metadata": metadata})
		self.loadEitBatch()

	def loadEitBatch(self):
		if self.screen is None:
			return
		if self.eitPending:
			batch = self.eitPending[:64]
			del self.eitPending[:64]
			self.client.request("details", {"paths": [x["path"] for x in batch]}, partial(self.eitLoaded, batch))
		else:
			self.run(self.eitOperations)

	def eitLoaded(self, batch, result):
		for operation in batch:
			operation["metadata"].update({x: value for x, value in result.get("items", {}).get(operation["path"], {}).items() if value})
		self.eitOperations.extend(batch)
		self.loadEitBatch()

	def createSelectedEit(self, path, metadata):
		if path in self.eitAttempted or not (metadata.get("description") or metadata.get("localDescription")):
			return
		self.eitAttempted.add(path)
		operation = {"action": "eit", "path": path, "metadata": dict(metadata)}
		job = MovieFileJob(_("Create missing EIT file"), [operation], partial(movieOperationGuard, self.screen.session))
		job_manager.AddJob(job)

	def transfer(self, action):
		operations = self.operations(action)
		if operations:
			self.screen.selectMovieLocation(_("Select destination for %d movies") % len(operations), partial(self.transferDestination, operations))

	def transferDestination(self, operations, destination):
		if destination:
			for operation in operations:
				operation["target"] = join(destination, basename(operation["path"]))
			self.run(operations)

	def delete(self):
		operations = self.operations("delete")
		if not operations:
			return
		trash = config.usage.movielist_trashcan.value and all(TRASHCAN not in normpath(operation["path"]).split("/") for operation in operations)
		if trash:
			for operation in operations:
				destination = createTrashcan(operation["path"])
				if not destination:
					self.screen.session.open(MessageBox, _("Cannot create the trashcan."), type=MessageBox.TYPE_ERROR)
					return
				operation.update(action="trash", target=join(destination, basename(operation["path"])))
		message = (_("Move %d selected movies and their companion files to the trashcan?") if trash else _("Permanently delete %d selected movies and their companion files?")) % len(operations)
		self.screen.session.openWithCallback(lambda confirmed: self.run(operations) if confirmed else None, MessageBox, message, type=MessageBox.TYPE_YESNO, default=False)

	def setWatched(self, watched):
		operations = self.operations("status")
		items = self.selectedItems()
		for operation, item in zip(operations, items):
			if watched:
				length = item[1].getLength(item[0]) if item[1] is not None else 0
				if length <= 0:
					length = self.screen.list.movieMetadata.get(operation["path"], {}).get("duration", 0)
				operation["position"] = max(0, length) * 90000
		self.run(operations)

	def restore(self):
		self.run(self.operations("restore"))

	def edit(self):
		items = self.selectedItems()
		if len(items) != 1:
			self.screen.session.open(MessageBox, _("Select one movie to edit its information."), type=MessageBox.TYPE_INFO)
			return
		service, info = items[0][:2]
		title = info.getName(service) if info is not None else basename(service.getPath())
		description = info.getInfoString(service, iServiceInformation.sDescription) if info is not None else ""
		operation = dict(self.operations("metadata")[0], service=service.toString())
		self.screen.session.openWithCallback(partial(self.edited, operation), MovieMetadataEditor, title, description)

	def edited(self, operation, values):
		if values:
			operation.update(title=values[0], description=values[1])
			self.run([operation])

	def rename(self):
		operations = self.operations("rename")
		if len(operations) != 1:
			self.screen.session.open(MessageBox, _("Select one movie to rename its file."), type=MessageBox.TYPE_INFO)
			return
		self.screen.session.openWithCallback(partial(self.renamed, operations[0]), VirtualKeyBoard, title=_("New movie filename (without extension)"), text=splitext(basename(operations[0]["path"]))[0])

	def renamed(self, operation, name):
		if name is None:
			return
		if not name.strip() or name in (".", "..") or any(character in name for character in ("/", "\\", "\0", "\n", "\r")):
			self.screen.session.open(MessageBox, _("Invalid filename."), type=MessageBox.TYPE_ERROR)
			return
		operation["target"] = join(dirname(operation["path"]), f"{name.strip()}{splitext(operation['path'])[1]}")
		self.run([operation])

	def run(self, operations):
		if not operations or self.screen is None:
			return
		providers = [name for name, (priority, provider) in movieLibrary.providers.items() if "changes" in getattr(provider, "capabilities", ())]
		job = MovieFileJob(_("Movie file operations"), operations, partial(movieOperationGuard, self.screen.session), providers)
		job_manager.AddJob(job, onSuccess=self.finished)
		self.screen.showActionFeedback(_("Processing %d movies in the background") % len(operations))

	def finished(self, job):
		paths = movieMaintenanceState.applyChanges(job.results)
		movieListSettings.updateNewCounts()
		updateMovieResumePoints(job.results)
		if paths:
			movieLibrary.invalidate(paths)
		movieLibrary.synchronizeChanges()
		failures = [f"{basename(result['path'])}: {result.get('error') or result.get('warning')}" for result in job.results if not result.get("success") or result.get("warning")]
		if self.screen is not None:
			self.clearMarks()
			self.screen.reloadList()
			self.screen.showActionFeedback(_("Completed: %(done)d of %(total)d movies") % {"done": sum(bool(result.get("success")) for result in job.results), "total": len(job.results)})
		if failures:
			AddNotification(MessageBox, "\n".join(failures), type=MessageBox.TYPE_ERROR)

	def maintenance(self):
		choices = [(_("Update folder movie counts and sizes"), "statistics"), (_("Find orphaned movie companion files"), "orphans"), (_("Find old watched movies"), "watched")]
		choices.insert(0, (_("Update movie folder snapshot / latest recordings"), "catalogue"))
		if movieMaintenanceState.scan is not None:
			choices.insert(0, (_("Review last maintenance scan"), "review"))
		self.screen.session.openWithCallback(self.maintenanceSelected, ChoiceBox, title=_("Movie maintenance"), list=choices)

	def maintenanceSelected(self, choice):
		if not choice or self.screen is None:
			return
		if choice[1] == "review":
			self.reviewMaintenance()
		elif choice[1] == "catalogue":
			self.scanCatalogue()
		elif movieMaintenanceState.running:
			self.screen.session.open(MessageBox, _("A movie maintenance scan is already running. Its progress is shown in Tasks."), type=MessageBox.TYPE_INFO)
		else:
			root = config.movielist.last_videodir.value if self.screen.libraryActive else self.screen.current_ref.getPath()
			self.screen.session.openWithCallback(partial(self.startMaintenance, choice[1]), MovieLocationBox, _("Select the movie folder to scan, including subfolders"), root)

	def scanCatalogue(self):
		if self.screen is None or movieMaintenanceState.catalogueRunning:
			return
		# Resolve the player's live cache after startup to avoid circular imports.
		from Screens import InfoBarGenerics
		resumes = {eServiceReference(x).getPath(): list(InfoBarGenerics.resumePointCache[x]) for x in InfoBarGenerics.resumePointCache}
		roots = list(dict.fromkeys([config.usage.default_path.value, config.movielist.last_videodir.value] + list(config.movielist.videodirs.value)))
		job = MovieCatalogueJob(roots, config.movielist.hiddenFolders.value, config.movielist.scanLinkedFolders.value, resumes)
		movieMaintenanceState.catalogueRunning = True
		job_manager.AddJob(job, onSuccess=self.catalogueScanned, onFail=self.catalogueFailed)
		self.screen.showActionFeedback(_("Updating movie folder snapshot in Tasks"))

	def catalogueFailed(self, job, task, problems):
		movieMaintenanceState.catalogueRunning = False
		return job_manager.notifyFailed(job, task, problems)

	def catalogueScanned(self, job):
		movieMaintenanceState.catalogueRunning = False
		if job.revision != movieMaintenanceState.catalogueRevision:
			if self.screen is not None:
				self.scanCatalogue()
			return  # A completed file operation must not be overwritten by an older scan.
		movieMaintenanceState.catalogueReady = True
		movieMaintenanceState.catalogue = job.items
		movieListSettings.updateNewCounts()
		for root in job.roots:
			movieMaintenanceState.update(root, {x: job.statistics[x] for x in job.statistics if x == normpath(root) or x.startswith(join(normpath(root), ""))})
		if self.screen is not None:
			self.screen.reloadList()

	def startMaintenance(self, mode, root):
		if not root or self.screen is None:
			return
		# Copy the live resume cache on the GUI thread; the worker only receives plain data.
		from Screens import InfoBarGenerics
		resumes = {eServiceReference(reference).getPath(): list(value) for reference, value in InfoBarGenerics.resumePointCache.items()}
		job = MovieMaintenanceJob(root, mode, resumes, config.movielist.watchedPercent.value, config.movielist.maintenanceAge.value)
		movieMaintenanceState.running = True
		job_manager.AddJob(job, onSuccess=self.maintenanceScanned, onFail=self.maintenanceFailed)
		self.screen.showActionFeedback(_("Scanning movie folders in the background"))

	def maintenanceFailed(self, job, task, problems):
		movieMaintenanceState.running = False
		return job_manager.notifyFailed(job, task, problems)

	def maintenanceScanned(self, job):
		movieMaintenanceState.running = False
		movieMaintenanceState.update(job.root, job.statistics)
		movieMaintenanceState.scan = {"mode": job.mode, "candidates": job.candidates} if job.mode != "statistics" else None
		if self.screen is not None:
			self.screen.reloadList()
		message = _("Folder movie counts and sizes updated.") if job.mode == "statistics" else _("Maintenance scan finished: %d candidates. Review them from Movie maintenance in the context menu.") % len(job.candidates)
		AddNotification(MessageBox, message, type=MessageBox.TYPE_INFO, timeout=10)

	def reviewMaintenance(self):
		job = movieMaintenanceState.scan
		if job is not None:
			if job["candidates"]:
				self.screen.session.openWithCallback(partial(self.maintenanceReviewed, job), MovieMaintenanceReview, job["candidates"])
			else:
				self.screen.session.open(MessageBox, _("No maintenance candidates found."), type=MessageBox.TYPE_INFO)

	def maintenanceReviewed(self, job, candidates):
		if candidates and self.screen is not None:
			message = _("Permanently delete %d selected orphaned companion files?") if job["mode"] == "orphans" else _("Move %d selected watched movies and their companion files to the trashcan?")
			self.screen.session.openWithCallback(partial(self.maintenanceConfirmed, job, candidates), MessageBox, message % len(candidates), type=MessageBox.TYPE_YESNO, default=False)

	def maintenanceConfirmed(self, job, candidates, answer):
		if not answer or self.screen is None:
			return
		movieMaintenanceState.scan = None
		if job["mode"] == "orphans":
			operation = MovieOrphanJob(candidates, partial(movieOperationGuard, self.screen.session))
			job_manager.AddJob(operation, onSuccess=self.orphansFinished)
		else:
			operations = []
			for candidate in candidates:
				path = candidate["path"]
				destination = createTrashcan(path)
				if not destination:
					self.screen.session.open(MessageBox, _("Cannot create the trashcan."), type=MessageBox.TYPE_ERROR)
					return
				service = eServiceReference(eServiceReference.idDVB if splitext(path)[1].lower() == ".ts" else 4097, 0, path)
				operations.append(dict(candidate, action="trash", target=join(destination, basename(path)), reference=service.toString()))
			self.run(operations)

	def orphansFinished(self, job):
		failures = [f"{basename(result['path'])}: {result.get('error', '')}" for result in job.results if not result["success"]]
		message = "\n".join(failures) if failures else _("Orphaned companion files removed.")
		AddNotification(MessageBox, message, type=MessageBox.TYPE_ERROR if failures else MessageBox.TYPE_INFO)

	def renameMenu(self):
		choices = [(_("Edit title and description"), self.edit), (_("Rename movie file and companion files"), self.rename)]
		if movieLibrary.getProvider() is not None:
			choices.append((_("Preview series filenames from the movie database"), self.renameSeries))
		self.screen.session.openWithCallback(lambda choice: choice[1]() if choice else None, ChoiceBox, title=_("Edit movie"), list=choices)

	def renameSeries(self):
		self.seriesPending = self.operations("rename")
		self.seriesProposals = []
		self.seriesSkipped = 0
		self.loadSeriesBatch()

	def loadSeriesBatch(self):
		if self.screen is None:
			return
		if self.seriesPending:
			batch = self.seriesPending[:64]
			del self.seriesPending[:64]
			self.screen.showActionFeedback(_("Preparing series filenames..."))
			self.client.request("details", {"paths": [operation["path"] for operation in batch]}, partial(self.seriesLoaded, batch))
		else:
			proposals = self.seriesProposals
			if not proposals:
				self.screen.session.open(MessageBox, _("No unambiguous series filenames are available. A series name, season and episode are required."), type=MessageBox.TYPE_INFO)
				return
			preview = "\n".join(f"{basename(operation['path'])}\n→ {basename(operation['target'])}" for operation in proposals[:20])
			preview += "\n\n" + _("Rename %(count)d movies with their companion files? %(skipped)d unchanged or incomplete entries were skipped.") % {"count": len(proposals), "skipped": self.seriesSkipped}
			if len(proposals) > 20:
				preview += "\n" + _("The preview shows the first 20 filenames.")
			self.screen.session.openWithCallback(lambda confirmed: self.run(proposals) if confirmed else None, MessageBox, preview, type=MessageBox.TYPE_YESNO, default=False)

	def seriesLoaded(self, batch, result):
		for operation in batch:
			item = result.get("items", {}).get(operation["path"], {})
			try:
				season, episode = int(item["season"]), int(item["episode"])
				series = str(item.get("series") or "").strip()
				if not series or season < 0 or episode < 1 or item.get("pending"):
					raise ValueError("Incomplete series metadata")
				name = f"{series} - S{season:02d}E{episode:02d}"
				title = str(item.get("title") or "").strip()
				if title and title.casefold() != series.casefold():
					name += f" - {title}"
				name = sub(r'[\x00-\x1f/\\:*?"<>|]', "_", name).strip(" .")
				# Leave space for the extension and full-name companion suffixes on common filesystems.
				name = name.encode("utf-8")[:220].decode("utf-8", "ignore")
				operation["target"] = join(dirname(operation["path"]), f"{name}{splitext(operation['path'])[1]}")
				if operation["target"] == operation["path"]:
					raise ValueError("Already named")
				self.seriesProposals.append(operation)
			except (KeyError, TypeError, ValueError):
				self.seriesSkipped += 1
		self.loadSeriesBatch()

	def queueMenu(self):
		choices = [(_("Add selected movies to the play queue"), self.queueAdd), (_("Edit play queue (%d movies)") % len(moviePlayQueue.items), self.queueEdit), (_("Play queue"), self.queuePlay), (_("Load M3U playlist"), partial(self.queueFile, False)), (_("Save queue as M3U playlist"), partial(self.queueFile, True)), (_("Clear play queue"), self.queueClear)]
		self.screen.session.openWithCallback(lambda choice: choice[1]() if choice else None, ChoiceBox, title=_("Movie play queue"), list=choices)

	def queueAdd(self):
		items = []
		for service, info, *data in self.selectedItems():
			path = service.getPath()
			if splitext(path)[1].lower() in DVD_EXTENSIONS:
				self.screen.session.open(MessageBox, _("Open DVD images individually with the DVD player. Play queues support video and audio files."), type=MessageBox.TYPE_INFO)
				return
			title = self.screen.list.movieMetadata.get(path, {}).get("title") or (info.getName(service) if info is not None else basename(path))
			items.append({"path": path, "title": title})
		moviePlayQueue.add(items)
		self.screen.showActionFeedback(_("Play queue: %d movies (maximum 1024)") % len(moviePlayQueue.items))

	def queueClear(self):
		moviePlayQueue.items.clear()
		moviePlayQueue.changed()
		self.screen.showActionFeedback(_("Play queue cleared"))

	def queueEdit(self):
		choices = [(f"{index + 1}. {item.get('title') or basename(item['path'])}", index) for index, item in enumerate(moviePlayQueue.items)]
		self.screen.session.openWithCallback(self.queueSelected, ChoiceBox, title=_("Edit play queue"), list=choices or [(_("The play queue is empty"), None)])

	def queueSelected(self, choice):
		if choice and choice[1] is not None:
			index = choice[1]
			choices = [(_("Remove from queue"), "remove"), (_("Move up"), "up"), (_("Move down"), "down"), (_("Play from here"), "play")]
			self.screen.session.openWithCallback(partial(self.queueChanged, index), ChoiceBox, title=choice[0], list=choices)

	def queueChanged(self, index, choice):
		if choice and index < len(moviePlayQueue.items):
			if choice[1] == "play":
				self.queuePlay(index)
				return
			item = moviePlayQueue.items.pop(index)
			if choice[1] != "remove":
				moviePlayQueue.items.insert(max(0, index - 1) if choice[1] == "up" else index + 1, item)
			moviePlayQueue.changed()
			self.queueEdit()

	def queuePlay(self, index=0):
		services = []
		for item in moviePlayQueue.items:
			service = eServiceReference(eServiceReference.idDVB if splitext(item["path"])[1].lower() == ".ts" else 4097, 0, item["path"])
			service.setName(item.get("title", ""))
			services.append(service)
		if services:
			self.screen.playServices(services, index)

	def queueFile(self, saving):
		path = config.movielist.lastPlaylistPath.value or join(config.movielist.last_videodir.value, "playlist.m3u8")
		self.screen.session.openWithCallback(partial(self.queueFilename, saving), VirtualKeyBoard, title=_("Playlist filename (.m3u or .m3u8)"), text=path)

	def queueFilename(self, saving, path):
		if path:
			arguments = (path, [dict(item) for item in moviePlayQueue.items]) if saving else (path,)
			deferToThreadPool(reactor, movieLibrary.getPool(), writeMoviePlaylist if saving else readMoviePlaylist, *arguments).addBoth(self.queueFileDone, saving, path)

	def queueFileDone(self, result, saving, path=None):
		if self.screen is not None:
			if result is None or isinstance(result, list):
				if not saving:
					if any(splitext(item["path"])[1].lower() not in MOVIE_EXTENSIONS | AUDIO_EXTENSIONS for item in result):
						self.screen.session.open(MessageBox, _("This playlist contains unsupported files. Play queues support video and audio files; open DVD images individually."), type=MessageBox.TYPE_INFO)
						return None
					moviePlayQueue.items.clear()
					moviePlayQueue.add(result)
				if path:
					config.movielist.lastPlaylistPath.value = path
					config.movielist.lastPlaylistPath.save()
				self.screen.showActionFeedback(_("Playlist saved") if saving else _("Playlist loaded"))
			else:
				self.screen.session.open(MessageBox, result.getErrorMessage(), type=MessageBox.TYPE_ERROR)
		return None
