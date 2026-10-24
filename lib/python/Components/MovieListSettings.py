from os.path import basename, dirname, splitext
from re import search
from time import localtime, strftime, time

from Components.config import ConfigSelection, ConfigSelectionNumber, ConfigText, ConfigYesNo, config
from Components.FileList import KNOWN_EXTENSIONS
from Tools.Conversions import NumberScaler
from Tools.FuzzyDate import FuzzyTime
from Tools.MovieMaintenance import movieMaintenanceState


class MovieListSettings:
	def __init__(self):
		self.standbyCounter = 0
		self.visitStart = 0
		self.previousVisit = 0

	def initConfig(self):
		config.movielist.watchingPercent = ConfigSelectionNumber(0, 30, 1, default=0)
		config.movielist.watchedPercent = ConfigSelectionNumber(50, 100, 1, default=100)
		config.movielist.startFolder = ConfigSelection(default="last", choices=[("last", _("Last folder")), ("home", _("Default movie location")), ("standby", _("Default movie location after standby"))])
		config.movielist.markAdvance = ConfigSelection(default="stay", choices=[("stay", _("Stay on the movie")), ("next", _("Next movie")), ("direction", _("Continue in the last direction"))])
		config.movielist.titleSource = ConfigSelection(default="auto", choices=[("auto", _("Automatic")), ("recording", _("Recording title")), ("filename", _("Filename"))])
		config.movielist.dateMode = ConfigSelection(default="relative", choices=[("relative", _("Relative date")), ("system", _("System date format")), ("datetime", _("System date and time"))])
		config.movielist.rewindWatched = ConfigYesNo(default=False)
		config.movielist.startAtFirstMark = ConfigYesNo(default=False)
		config.movielist.previewMode = ConfigSelection(default="manual", choices=[("off", _("Disabled")), ("manual", _("Manual")), ("auto", _("Automatic"))])
		config.movielist.previewDelay = ConfigSelectionNumber(500, 10000, 500, default=2000)
		config.movielist.previewStart = ConfigSelection(default="resume", choices=[("resume", _("Last playback position")), ("beginning", _("Beginning")), ("firstMark", _("First chapter marker"))])
		config.movielist.previewOffset = ConfigSelectionNumber(0, 60, 1, default=5)
		config.movielist.showBookmarks = ConfigYesNo(default=False)
		config.movielist.rememberQueue = ConfigYesNo(default=False)
		config.movielist.lastPlaylistPath = ConfigText(default="", fixed_size=False)
		config.movielist.directoryInfo = ConfigSelection(default="off", choices=[("off", _("Disabled")), ("count", _("Movie count")), ("size", _("Movie size")), ("both", _("Movie count and size")), ("new", _("New movies")), ("all", _("Movie count, size and new movies"))])
		config.movielist.recordingEofAction = ConfigSelection(default="default", choices=[("default", _("Use normal end-of-movie action")), ("ask", _("Ask to switch to the recording channel")), ("zap", _("Switch to the recording channel"))])
		config.movielist.maintenanceAge = ConfigSelectionNumber(1, 365, 1, default=10)
		config.movielist.showDirectories = ConfigYesNo(default=True)
		config.movielist.directoryOrder = ConfigSelection(default="default", choices=[("default", _("Use selected sorting")), ("first", _("Folders first")), ("mixed", _("Sort folders with movies"))])
		config.movielist.showSymlinks = ConfigYesNo(default=True)
		config.movielist.scanLinkedFolders = ConfigYesNo(default=False)
		config.movielist.recognizeDVD = ConfigYesNo(default=True)
		config.movielist.recognizeBluray = ConfigYesNo(default=True)
		config.movielist.recognizeMovieFolders = ConfigYesNo(default=False)
		config.movielist.fileListCache = ConfigSelection(default="off", choices=[("off", _("Disabled")), ("60", _("1 minute")), ("300", _("5 minutes")), ("900", _("15 minutes"))])
		config.movielist.newRecordings = ConfigSelection(default="off", choices=[("off", _("Disabled")), ("day", _("Last 24 hours")), ("visit", _("Since the previous visit"))])
		config.movielist.lastVisit = ConfigText(default="0", fixed_size=False)
		config.movielist.showFormat = ConfigYesNo(default=False)
		config.movielist.showCutNumber = ConfigYesNo(default=False)
		config.movielist.showRecordingLength = ConfigYesNo(default=False)
		config.movielist.latestRecordings = ConfigYesNo(default=False)
		config.movielist.latestDays = ConfigSelection(default="0", choices=[("0", _("All dates")), ("1", _("Last 24 hours")), ("7", _("Last 7 days")), ("30", _("Last 30 days")), ("90", _("Last 90 days"))])
		config.movielist.latestLimit = ConfigSelection(default="0", choices=[("0", _("Unlimited")), ("25", "25"), ("50", "50"), ("100", "100"), ("500", "500")])
		config.movielist.latestScope = ConfigSelection(default="all", choices=[("all", _("All movie folders")), ("home", _("Default movie location")), ("current", _("Current folder and subfolders"))])
		config.movielist.latestSort = ConfigSelection(default="newest", choices=[("newest", _("Newest recordings first")), ("oldest", _("Oldest recordings first")), ("title", _("Title (A–Z)")), ("titleDesc", _("Title (Z–A)"))])

	def cachedDirectory(self, path):
		value = config.movielist.fileListCache.value
		return movieMaintenanceState.getDirectory(path, int(value) if value != "off" else 0)

	def beginVisit(self, returning=False):
		if not returning or not self.visitStart:
			try:
				self.previousVisit = int(config.movielist.lastVisit.value)
			except ValueError:
				self.previousVisit = 0
			self.visitStart = int(time())
			config.movielist.lastVisit.value = str(self.visitStart)
			config.movielist.lastVisit.save()
			self.updateNewCounts()

	def updateNewCounts(self):
		movieMaintenanceState.newCounts.clear()
		for item in movieMaintenanceState.catalogue.values():
			if self.isNew(item.get("recordedAt"), item.get("progress")):
				folder = dirname(item["path"])
				while folder and folder != dirname(folder):
					movieMaintenanceState.newCounts[folder] = movieMaintenanceState.newCounts.get(folder, 0) + 1
					folder = dirname(folder)

	def isNew(self, recordedAt, progress=None):
		mode = config.movielist.newRecordings.value
		cutoff = time() - 86400 if mode == "day" else self.previousVisit or self.visitStart
		return mode != "off" and bool(cutoff and recordedAt and cutoff < recordedAt <= time()) and self.watchState(progress) == "unwatched"

	def fileInfo(self, path, metadata, running=False):
		parts = []
		if config.movielist.showFormat.value:
			parts.append(metadata.get("mediaStructure") or splitext(path)[1][1:].upper())
		if config.movielist.showCutNumber.value:
			match = search(r"_(\d{3})$", splitext(basename(path))[0])
			if match:
				parts.append(_("Cut %s") % match[1])
		if running and config.movielist.showRecordingLength.value and metadata.get("duration", 0) > 0:
			parts.append(_("%d min recorded") % (metadata["duration"] // 60))
		return " · ".join(x for x in parts if x)

	def latestParameters(self, root):
		scope = config.movielist.latestScope.value
		return {"view": "latest", "since": int(time()) - int(config.movielist.latestDays.value) * 86400 if int(config.movielist.latestDays.value) else 0, "limit": int(config.movielist.latestLimit.value), "root": root if scope == "current" else config.usage.default_path.value if scope == "home" else "", "sort": config.movielist.latestSort.value}

	def watchState(self, progress):
		state = "unwatched"
		if progress is not None and progress > 0:
			if progress >= config.movielist.watchedPercent.value:
				state = "watched"
			elif progress >= config.movielist.watchingPercent.value:
				state = "watching"
		return state

	def watchText(self, progress):
		return {"unwatched": _("Unwatched"), "watching": _("In progress"), "watched": _("Watched")}[self.watchState(progress)]

	def title(self, path, recordingTitle="", metadata=None):
		metadata = metadata or {}
		mode = config.movielist.titleSource.value
		title = basename(path)
		if metadata.get("grouped") or mode == "auto":
			title = metadata.get("title") or recordingTitle or title
		elif mode == "recording":
			title = metadata.get("recordingTitle") or recordingTitle or title
		if not metadata.get("grouped") and config.movielist.hide_extensions.value:
			name, extension = splitext(title)
			if extension.lower() in KNOWN_EXTENSIONS:
				title = name
		if not config.movielist.show_underscores.value:
			title = title.replace("_", " ").strip()
		return title

	def dateText(self, timestamp):
		if not timestamp or timestamp <= 0:
			return ""
		mode = config.movielist.dateMode.value
		if mode == "relative":
			return ", ".join(FuzzyTime(timestamp, inPast=True))
		pattern = config.usage.date.long.value
		if mode == "datetime":
			pattern = f"{pattern} {config.usage.time.short.value}"
		return strftime(pattern, localtime(timestamp))

	def directoryText(self, path):
		mode = config.movielist.directoryInfo.value
		cached = movieMaintenanceState.get(path) if mode != "off" and path.startswith("/") else None
		if cached is None:
			return _("Directory")
		count, size = cached[:2]
		parts = []
		if mode in ("count", "both", "all"):
			parts.append(_("%d movies") % count)
		if mode in ("size", "both", "all"):
			parts.append(NumberScaler().scale(size, style="Iec", maxNumLen=3, decimals=1))
		if mode in ("new", "all"):
			newCount = movieMaintenanceState.newCounts.get(path.rstrip("/"), 0)
			parts.append(_("%d new") % newCount if movieMaintenanceState.catalogueReady else _("New movies: update folder statistics"))
		return " · ".join(parts)

	def useHome(self):
		counter = config.misc.standbyCounter.value
		mode = config.movielist.startFolder.value
		result = mode == "home" or mode == "standby" and counter != self.standbyCounter
		self.standbyCounter = counter
		return result

	def beginning(self, cuts, length=0, chapter=False, margin=0):
		boundaries = sorted((pts, kind) for pts, kind in cuts if kind in (0, 1))
		inside = not boundaries or boundaries[0][1] == 1
		beginning = 0 if inside else boundaries[0][0]
		limit = min(length // 2, (margin * 120 or 1200) * 90000) if length else (margin * 120 or 1200) * 90000
		if chapter:
			for pts, kind in sorted(cuts):
				if kind in (0, 1):
					inside = kind == 0
				elif kind == 2 and inside and beginning <= pts < limit:
					return pts
		return beginning


movieListSettings = MovieListSettings()
