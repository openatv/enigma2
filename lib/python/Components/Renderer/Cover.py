from os.path import basename, dirname, exists, isdir, isfile, join, split, splitext
from enigma import ePixmap, ePicLoad
from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent


class Cover(Renderer):
	EXTENSIONS = (".jpg", ".png", ".jpeg")
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		self.nameCache = {}
		self.picname = ""

	def changed(self, what):
		if self.instance:
			picname = ""
			sname = ""
			if what[0] != self.CHANGED_CLEAR:
				service = None
				if isinstance(self.source, ServiceEvent):
					service = self.source.getCurrentService()
				elif isinstance(self.source, CurrentService):
					service = self.source.getCurrentServiceReference()
				if service:
					sname = service.getPath()
				else:
					return
				picname = self.nameCache.get(sname, "")
				if picname == "":
					picname = self.findCover(sname)[1]
				if picname == "":
					path = sname
					if service.toString().endswith == "..":
						path = config.movielist.last_videodir.value
					for ext in self.EXTENSIONS:
						p = dirname(path) + "/folder" + ext
						picname = exists(p) and p or ""
						if picname:
							break

				if picname != "":
					self.nameCache[sname] = picname
				if picname == self.picname:
					return
				self.picname = picname
				if picname != "" and exists(picname):
					size = self.instance.size()
					self.picload = ePicLoad()
					self.picload.PictureData.get().append(self.showCoverCallback)
					if self.picload:
						self.picload.setPara((size.width(), size.height(), 1, 1, False, 1, "#00000000"))
						if self.picload.startDecode(picname) != 0:
							del self.picload
				else:
					self.instance.hide()

	def showCoverCallback(self, picInfo=None):
		if self.picload:
			ptr = self.picload.getData()
			if ptr is not None:
				self.instance.setPixmap(ptr)
				self.instance.show()
			del self.picload

	def findCover(self, path):
		fpath = p1 = p2 = p3 = ""
		name, ext = splitext(path)
		ext = ext.lower()
		if isfile(path):
			directory = dirname(path)
			p1 = name
			p2 = join(directory, basename(directory))
		elif isdir(path):
			if path.lower().endswith("/bdmv"):
				directory = path[:-5]
				if directory.lower().endswith("/brd"):
					directory = directory[:-4]
			elif path.lower().endswith("video_ts"):
				directory = path[:-9]
				if directory.lower().endswith("/dvd"):
					directory = directory[:-4]
			else:
				directory = path
				p2 = join(directory, "folder")
			prtdir, directory = split(directory)
			p1 = join(dir, directory)
			p3 = join(prtdir, directory)
		pathes = (p1, p2, p3)
		for p in pathes:
			for ext in self.EXTENSIONS:
				path = p + ext
				if exists(path):
					break
			if exists(path):
				fpath = path
				break

		return (p1, fpath)
