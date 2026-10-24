from collections import OrderedDict
from os.path import basename
from time import localtime, strftime

from enigma import ePicLoad, eServiceReference, eTimer, iServiceInformation

from Components.config import config
from Components.MovieLibrary import MovieLibraryClient, movieLibrary
from Components.Converter.MovieInfo import MovieInfo
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Source import Source
from Components.Sources.StaticText import StaticText


class MovieArtwork(Source):
	def __init__(self):
		Source.__init__(self)
		self.pixmap = None

	def setPixmap(self, pixmap):
		self.pixmap = pixmap
		self.changed((self.CHANGED_ALL,))


class MovieArtworkLoader:
	CACHE_BYTES = 12 * 1024 * 1024

	def __init__(self):
		self.cache = OrderedDict()
		self.cacheBytes = 0
		self.queue = []
		self.active = None
		self.closed = False
		self.generation = 0
		self.decoder = ePicLoad()
		self.decoder.PictureData.get().append(self.decoded)

	def cancel(self):
		self.generation += 1
		self.queue.clear()

	def close(self):
		self.closed = True
		self.cancel()
		self.cache.clear()
		self.cacheBytes = 0
		# Keep the decoder alive until its native worker has finished.
		if self.active is None:
			self.decoder.PictureData.get().remove(self.decoded)

	def load(self, path, size, callback):
		if self.closed:
			return
		key = (path, size)
		if key in self.cache:
			self.cache.move_to_end(key)
			callback(self.cache[key])
		elif path:
			self.queue.append((self.generation, key, callback))
			self.startNext()

	def startNext(self):
		while self.queue and self.active is None and not self.closed:
			self.active = self.queue.pop(0)
			generation, (path, size), callback = self.active
			self.decoder.setPara((*size, 1, 1, False, 1, "#00000000"))
			if self.decoder.startDecode(path) != 0:
				self.active = None
				callback(None)

	def decoded(self, information=None):
		pixmap = self.decoder.getData()
		request = self.active
		self.active = None
		if self.closed:
			self.decoder.PictureData.get().remove(self.decoded)
			return
		if request is not None:
			generation, key, callback = request
			if generation == self.generation:
				if pixmap is not None and key not in self.cache:
					self.cache[key] = pixmap
					self.cacheBytes += key[1][0] * key[1][1] * 4
					while self.cacheBytes > self.CACHE_BYTES:
						oldKey, oldPixmap = self.cache.popitem(last=False)
						self.cacheBytes -= oldKey[1][0] * oldKey[1][1] * 4
				callback(pixmap)
		self.startNext()


class MovieInformation:
	def __init__(self, screen, movieList=None, posterSize=(300, 450), backdropSize=(640, 360)):
		self.screen = screen
		self.movieList = movieList
		self.posterSize = posterSize
		self.backdropSize = backdropSize
		self.client = MovieLibraryClient()
		self.artwork = MovieArtworkLoader()
		self.timer = eTimer()
		self.timer.callback.append(self.load)
		self.path = ""
		self.item = {}
		self.onChanged = []
		self.serviceSource = ServiceEvent()
		self.description = MovieInfo("FullDescription")
		self.description.connect(self.serviceSource)
		self.channel = MovieInfo("RecordServiceName")
		self.channel.connect(self.serviceSource)
		for name in ("MovieTitle", "MovieDescription", "MovieDetails", "MovieLibraryStatus"):
			screen[name] = StaticText()
		for name in ("MoviePoster", "MovieBackdrop"):
			screen[name] = MovieArtwork()
		screen.onClose.append(self.close)

	def close(self):
		self.timer.stop()
		self.client.close()
		self.artwork.close()
		self.description.disconnectAll()
		self.channel.disconnectAll()
		self.screen = None
		self.movieList = None
		self.onChanged.clear()

	def select(self, serviceRef, title="", description="", items=None):
		if self.screen is None:
			return
		self.timer.stop()
		self.client.cancel()
		self.artwork.cancel()
		self.path = serviceRef.getPath() if serviceRef is not None and not serviceRef.flags & eServiceReference.mustDescent else ""
		self.item = {}
		self.localDetails = ""
		self.providedItems = items
		self.serviceSource.newService(serviceRef if self.path and items is None else None)
		if self.path and items is None:
			fullDescription = self.description.text
			if fullDescription and fullDescription != self.path:
				description = fullDescription
			info = self.serviceSource.info
			if info is not None:
				self.item["fileSize"] = info.getInfoObject(serviceRef, iServiceInformation.sFileSize)
				recordedAt = info.getInfo(serviceRef, iServiceInformation.sTimeCreate)
				if recordedAt > 0:
					self.item["recordedAt"] = recordedAt
					self.localDetails = strftime("%d.%m.%Y %H:%M", localtime(recordedAt))
			self.localDetails = " · ".join(x for x in (self.channel.text, self.localDetails) if x)
		self.item.update({"title": title or basename(self.path), "description": description})
		self.screen["MovieTitle"].text = title or basename(self.path)
		self.screen["MovieDescription"].text = description or (_("No description available.") if self.path else "")
		self.screen["MovieDetails"].text = self.localDetails
		self.screen["MovieLibraryStatus"].text = ""
		self.screen["MoviePoster"].setPixmap(None)
		self.screen["MovieBackdrop"].setPixmap(None)
		if serviceRef is not None:
			self.timer.start(180, True)

	def load(self):
		if self.providedItems is not None:
			self.loaded({"items": self.providedItems})
			return
		styled = self.movieList is not None and self.movieList.listStyle is not None
		artworkVisible = self.screen["MoviePoster"].downstream_elements or self.screen["MovieBackdrop"].downstream_elements
		if self.item.get("description") and not styled and not artworkVisible and not self.onChanged and movieLibrary.getProvider() is None and config.movielist.eitMode.value != "automatic":
			return
		paths = [self.path] if self.path else []
		if styled:
			index = self.movieList.getCurrentIndex()
			start = max(0, index - 24)
			paths.extend(item[0].getPath() for item in self.movieList.list[start:start + 48] if not item[0].flags & eServiceReference.mustDescent)
		if paths:
			# InfoBarGenerics imports MovieSelection; snapshot its live cache after startup.
			from Screens import InfoBarGenerics
			services = [item[0] for item in self.movieList.list if item[0].getPath() in paths] if self.movieList is not None else []
			resume = {service.getPath(): InfoBarGenerics.resumePointCache[service.toString()] for service in services if service.toString() in InfoBarGenerics.resumePointCache}
			self.client.request("details", {"paths": paths, "resume": resume}, self.loaded)

	def loaded(self, result):
		items = result.get("items", {})
		description = self.item.get("description")
		self.item.update(items.get(self.path, {}))
		if not self.item.get("description"):
			self.item["description"] = description or self.item.get("localDescription", "")
		if self.item.get("title"):
			self.screen["MovieTitle"].text = self.item["title"]
		if self.item.get("description"):
			self.screen["MovieDescription"].text = self.item["description"]
		genres = self.item.get("genres", [])
		if isinstance(genres, (list, tuple)):
			genres = ", ".join(str(genre) for genre in genres)
		details = [self.item.get("year")]
		if self.item.get("type") == "series" and self.item.get("season") is not None and self.item.get("episode"):
			details.append(_("Season %(season)s · Episode %(episode)s") % self.item)
		if self.item.get("rating"):
			details.append(_("Rating: %s") % self.item["rating"])
		details.append(genres)
		self.screen["MovieDetails"].text = " · ".join(str(value) for value in details if value) or self.localDetails
		self.screen["MovieLibraryStatus"].text = _("Movie database unavailable") if result.get("error") else ""
		if self.screen["MoviePoster"].downstream_elements:
			self.artwork.load(self.item.get("poster"), self.posterSize, self.posterLoaded)
		if self.screen["MovieBackdrop"].downstream_elements:
			self.artwork.load(self.item.get("backdrop"), self.backdropSize, self.backdropLoaded)
		if self.movieList is not None:
			self.movieList.setMovieMetadata(items)
			if self.movieList.listStyle is not None and "Poster" in self.movieList.listStyle.fields:
				for path, item in items.items():
					if item.get("poster"):
						self.artwork.load(item["poster"], (160, 240), lambda pixmap, path=path: self.movieList.setMoviePoster(path, pixmap))
		for callback in self.onChanged:
			callback()
		if self.path and self.providedItems is None and hasattr(self.screen, "movieActions") and config.movielist.eitMode.value == "automatic":
			self.screen.movieActions.createSelectedEit(self.path, self.item)

	def posterLoaded(self, pixmap):
		self.screen["MoviePoster"].setPixmap(pixmap)

	def backdropLoaded(self, pixmap):
		self.screen["MovieBackdrop"].setPixmap(pixmap)
