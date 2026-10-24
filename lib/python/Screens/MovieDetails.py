from os.path import basename

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.MovieInformation import MovieInformation
from Components.MovieListSettings import movieListSettings
from Components.MovieListStyle import movieListStyles
from Components.ScrollLabel import ScrollLabel
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen, ScreenSummary
from Tools.Conversions import NumberScaler
from Tools.MovieFileInfo import MovieFileInfo


class MovieDetails(Screen):
	def __init__(self, session, service, title="", description="", metadata=None, databaseOnly=False):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = movieListStyles.getProviderScreenNames(["MovieDetails"])
		self.setTitle(_("Advance Movie List"))
		self.service = service
		self.path = service.getPath()
		self.initialTitle = title or basename(self.path)
		self.initialDescription = description
		self.metadata = dict(metadata or {})
		self.databaseOnly = databaseOnly
		self.fileInfoStarted = False
		self.fileInformation = None
		self.filePage = False
		self.scrollVisible = False
		self.scrollTimer = eTimer()
		self.scrollTimer.callback.append(self.scrollDetails)
		self["details"] = ScrollLabel()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("File information"))
		self["pageTitle"] = StaticText(_("Movie information"))
		self["MovieSelectionStatus"] = StaticText(_("Movie information"))
		self.movieInformation = MovieInformation(self, posterSize=(390, 585), backdropSize=(1280, 720))
		self.movieInformation.onChanged.append(self.metadataLoaded)
		self.fileInfo = MovieFileInfo(self.fileInfoLoaded)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "MovieSelectionActions", "DirectionActions"], {
			"ok": (self.close, _("Close")),
			"cancel": (self.close, _("Close")),
			"red": (self.close, _("Close")),
			"green": (self.togglePage, _("Switch movie and file information")),
			"showEventInfo": (self.close, _("Close")),
			"up": (lambda: self.scrollPage(-1), _("Scroll up")),
			"down": (lambda: self.scrollPage(1), _("Scroll down")),
			"left": (lambda: self.scrollPage(-1), _("Scroll up")),
			"right": (lambda: self.scrollPage(1), _("Scroll down"))
		})
		self.onLayoutFinish.append(self.load)
		self.onShow.append(self.showDetails)
		self.onHide.append(self.hideDetails)
		self.onClose.append(self.hideDetails)
		self.onClose.append(self.fileInfo.close)

	def createSummary(self):
		return MovieDetailsSummary

	def showDetails(self):
		self.scrollVisible = True
		self.restartScroll()

	def hideDetails(self):
		self.scrollVisible = False
		self.scrollTimer.stop()

	def restartScroll(self, delay=4000):
		self.scrollTimer.stop()
		if self.scrollVisible and self["details"].isNavigationNeeded():
			self.scrollTimer.start(delay, True)

	def scrollPage(self, direction):
		if direction < 0:
			self["details"].pageUp()
		else:
			self["details"].pageDown()
		self.restartScroll(10000)

	def scrollDetails(self):
		details = self["details"]
		if not self.scrollVisible or not details.isNavigationNeeded():
			return
		if details.isAtLastPage():
			details.setPos(0)
			self.restartScroll()
		else:
			details.setPos(details.currentPosition + 1)
			self.scrollTimer.start(5000 if details.isAtLastPage() else 160, True)

	def load(self):
		self.movieInformation.select(self.service, self.initialTitle, self.initialDescription, items={self.path: self.metadata} if self.databaseOnly else None)
		self.metadata.update({x: value for x, value in self.movieInformation.item.items() if value and not self.metadata.get(x)})
		self.updateText()

	def metadataLoaded(self):
		self.metadata.update(self.movieInformation.item)
		if not self.filePage:
			self.updateText()

	def fileInfoLoaded(self, information):
		self.fileInformation = information
		if self.filePage:
			self.updateText()

	def togglePage(self):
		self.filePage = not self.filePage
		if self.filePage and not self.fileInfoStarted:
			self.fileInfoStarted = True
			self.fileInfo.start(self.path)
		self["key_green"].text = _("Movie information") if self.filePage else _("File information")
		self["pageTitle"].text = _("File information") if self.filePage else _("Movie information")
		self["MovieSelectionStatus"].text = self["pageTitle"].text
		self.updateText()

	def displayValue(self, value):
		if isinstance(value, dict):
			name = value.get("name") or value.get("actor") or value.get("title") or ""
			role = value.get("character") or value.get("job") or value.get("role") or ""
			return f"{name} ({role})" if name and role else str(name)
		if isinstance(value, (list, tuple)):
			return ", ".join(filter(None, (self.displayValue(x) for x in value)))
		return str(value) if value is not None else ""

	def updateText(self):
		if self.filePage:
			lines = self.fileDetails()
		else:
			lines = [self.metadata.get("description") or self.initialDescription or _("No description available."), ""]
			for field, label in (("tagline", _("Tagline")), ("originalTitle", _("Original title")), ("series", _("Series")), ("released", _("Release date")), ("countries", _("Countries")), ("ageRating", _("Age rating")), ("runtime", _("Runtime")), ("votes", _("Votes")), ("cast", _("Cast")), ("crew", _("Crew"))):
				if field == "series" and self.metadata.get("type") != "series":
					continue
				value = self.displayValue(self.metadata.get(field))
				if value and value != "0":
					lines.append(f"{label}: {value}")
			if self.metadata.get("recordedAt"):
				lines.append(f"{_('Recorded')}: {movieListSettings.dateText(self.metadata['recordedAt'])}")
		self["details"].setText("\n".join(lines))
		self.restartScroll()

	def fileDetails(self):
		lines = [f"{_('File name')}: {basename(self.path)}", f"{_('Path')}: {self.path}", ""]
		information = self.fileInformation
		if self.metadata.get("fileSize") and (not information or not information.get("format", {}).get("size")):
			lines.append(f"{_('Size')}: {NumberScaler().scale(self.metadata['fileSize'], style='Iec', maxNumLen=3, decimals=2)}")
		if information is None:
			lines.append(_("Reading media information..."))
		elif information.get("error"):
			lines.append(_("Media information is currently unavailable.") if information["error"] != "timeout" else _("Reading media information timed out."))
		else:
			fileFormat = information.get("format", {})
			for field, label in (("format_long_name", _("Container")), ("size", _("Size")), ("duration", _("Duration")), ("bit_rate", _("Bitrate"))):
				value = fileFormat.get(field)
				if value is not None:
					try:
						if field in ("size", "bit_rate"):
							value = NumberScaler().scale(int(value), style="Iec" if field == "size" else "Si", suffix="B" if field == "size" else "bit/s", maxNumLen=3, decimals=2)
						elif field == "duration":
							seconds = int(float(value))
							value = f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
					except (ValueError, TypeError, OverflowError):
						continue
					lines.append(f"{label}: {value}")
			for stream in information.get("streams", []):
				kind = {"video": _("Video"), "audio": _("Audio"), "subtitle": _("Subtitle")}.get(stream.get("codec_type"))
				if kind is None:
					continue
				lines.extend(("", f"{kind} #{stream.get('index', '')}"))
				if stream.get("width") and stream.get("height"):
					lines.append(f"{_('Resolution')}: {stream['width']} × {stream['height']}")
				for field, label in (("codec_long_name", _("Codec")), ("profile", _("Profile")), ("display_aspect_ratio", _("Aspect ratio")), ("avg_frame_rate", _("Frame rate")), ("pix_fmt", _("Pixel format")), ("color_transfer", _("Transfer characteristics")), ("color_space", _("Color space")), ("sample_rate", _("Sample rate")), ("channels", _("Audio channels")), ("channel_layout", _("Channel layout")), ("bit_rate", _("Bitrate"))):
					value = stream.get(field)
					if value not in (None, "", "0/0"):
						try:
							if field == "bit_rate":
								value = NumberScaler().scale(int(value), style="Si", suffix="bit/s", maxNumLen=3, decimals=2)
							elif field == "sample_rate":
								value = f"{value} Hz"
							elif field == "avg_frame_rate":
								numerator, separator, denominator = str(value).partition("/")
								value = f"{float(numerator) / float(denominator) if separator else float(numerator):g} fps"
						except (ValueError, TypeError, OverflowError, ZeroDivisionError):
							continue
						lines.append(f"{label}: {value}")
				tags = stream.get("tags", {})
				for field, label in (("language", _("Track language")), ("title", _("Title"))):
					if tags.get(field):
						lines.append(f"{label}: {tags[field]}")
				flags = stream.get("disposition", {})
				for field, label in (("default", _("Default")), ("forced", _("Forced")), ("hearing_impaired", _("Hearing impaired")), ("visual_impaired", _("Audio description"))):
					if flags.get(field):
						lines.append(label)
		return lines


class MovieDetailsSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent)
		self["name"] = StaticText(parent.initialTitle)
		self["progress"] = Progress()
		self.onShow.append(self.connect)
		self.onHide.append(self.disconnect)

	def connect(self):
		self.parent.movieInformation.onChanged.append(self.updateInformation)
		self.updateInformation()

	def disconnect(self):
		if self.updateInformation in self.parent.movieInformation.onChanged:
			self.parent.movieInformation.onChanged.remove(self.updateInformation)

	def updateInformation(self):
		self["name"].text = self.parent["MovieTitle"].text or self.parent.initialTitle
		self["progress"].value = min(100, self.parent.movieInformation.item.get("progress") or 0)
