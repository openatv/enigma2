from json import dumps, loads
from os import fsync, unlink
from os.path import dirname, isabs, join, normpath, splitext

from Components.config import config
from Components.FileList import AUDIO_EXTENSIONS, MOVIE_EXTENSIONS
from Tools.Directories import SCOPE_CONFIG, resolveFilename
from Tools.MovieFileOperations import writeMovieText


class MoviePlayQueue:
	LIMIT = 1024

	def __init__(self):
		self.items = []
		self.enabled = None

	def configure(self):
		enabled = config.movielist.rememberQueue.value
		if enabled == self.enabled:
			return
		previous = self.enabled
		self.enabled = enabled
		path = resolveFilename(SCOPE_CONFIG, "moviequeue.json")
		try:
			if enabled:
				if not self.items:
					try:
						with open(path, encoding="utf-8") as stream:
							text = stream.read(1024 * 1024 + 1)
					except FileNotFoundError:
						text = "[]"
					if len(text) > 1024 * 1024:
						raise ValueError("Saved movie queue is too large")
					items = loads(text)
					if not isinstance(items, list) or len(items) > self.LIMIT:
						raise ValueError("Invalid saved movie queue")
					self.items = [{"path": x["path"], "title": x.get("title", "")[:1024]} for x in items if isinstance(x, dict) and isinstance(x.get("path"), str) and isabs(x["path"]) and len(x["path"]) < 4096 and "\0" not in x["path"] and splitext(x["path"])[1].lower() in MOVIE_EXTENSIONS | AUDIO_EXTENSIONS and isinstance(x.get("title", ""), str)]
				self.changed()
			elif previous:
				try:
					unlink(path)
				except FileNotFoundError:
					pass
		except (OSError, ValueError) as error:
			print(f"[MoviePlaylist] Unable to restore movie queue: {error}")

	def changed(self):
		if self.enabled:
			try:
				text = dumps(self.items, ensure_ascii=False)
				if len(text) > 1024 * 1024:
					raise ValueError("Saved movie queue is too large")
				writeMovieText(resolveFilename(SCOPE_CONFIG, "moviequeue.json"), text)
			except (OSError, ValueError) as error:
				print(f"[MoviePlaylist] Unable to save movie queue: {error}")

	def add(self, items):
		known = {item["path"] for item in self.items}
		for item in items:
			if item["path"] not in known and len(self.items) < self.LIMIT:
				self.items.append(dict(item))
				known.add(item["path"])
		self.changed()


def readMoviePlaylist(path):
	if not isabs(path):
		raise ValueError(_("Select an absolute playlist path."))
	with open(path, encoding="utf-8-sig") as stream:
		text = stream.read(1024 * 1024 + 1)
	if len(text) > 1024 * 1024:
		raise ValueError(_("The playlist is too large."))
	items = []
	title = ""
	for line in text.splitlines():
		line = line.strip()
		if line.startswith("#EXTINF:"):
			title = line.partition(",")[2]
		elif line and not line.startswith("#"):
			if "://" in line or "\0" in line:
				raise ValueError(_("Movie playlists support local files and mounted storage only."))
			items.append({"path": normpath(line if isabs(line) else join(dirname(path), line)), "title": title})
			title = ""
			if len(items) > MoviePlayQueue.LIMIT:
				raise ValueError(_("The playlist contains too many movies."))
	return items


def writeMoviePlaylist(path, items):
	if not isabs(path) or not path.lower().endswith((".m3u", ".m3u8")):
		raise ValueError(_("Use an absolute filename ending in .m3u or .m3u8."))
	lines = ["#EXTM3U"]
	for item in items:
		if any(character in item["path"] for character in ("\n", "\r", "\0")):
			raise ValueError(_("A movie filename cannot be represented in M3U format."))
		lines.extend((f"#EXTINF:-1,{item.get('title', '').replace(chr(10), ' ').replace(chr(13), ' ')}", item["path"]))
	# Saving never replaces an existing user playlist.
	created = False
	try:
		with open(path, "x", encoding="utf-8") as stream:
			created = True
			stream.write("\n".join(lines) + "\n")
			stream.flush()
			fsync(stream.fileno())
	except Exception:
		if created:
			unlink(path)
		raise
	return None


moviePlayQueue = MoviePlayQueue()
