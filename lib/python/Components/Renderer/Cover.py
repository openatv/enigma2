from os.path import basename, dirname, exists, isdir, isfile, join, split, splitext

from enigma import ePicLoad, ePixmap

from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.Sources.CurrentService import CurrentService
from Components.Sources.ServiceEvent import ServiceEvent


class Cover(Renderer):
	GUI_WIDGET = ePixmap
	EXTENSIONS = (".jpg", ".png", ".jpeg")

	def __init__(self):
		Renderer.__init__(self)
		self.nameCache = {}
		self.picname = ""
		self.picload = None

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
					if service.toString().endswith(".."):
						path = config.movielist.last_videodir.value
					folder = join(dirname(path), "folder")
					picname = next((f"{folder}{x}" for x in self.EXTENSIONS if exists(f"{folder}{x}")), "")

				if picname != "":
					self.nameCache[sname] = picname
				if picname == self.picname:
					return
				self.picname = picname
				if picname != "" and exists(picname):
					size = self.instance.size()
					self.picload = ePicLoad()
					self.picload.PictureData.get().append(self.showCoverCallback)
					self.picload.setPara((size.width(), size.height(), 1, 1, False, 1, "#00000000"))
					if self.picload.startDecode(picname) != 0:
						self.picload = None
				else:
					self.instance.hide()

	def showCoverCallback(self, picInfo=None):
		if self.picload:
			ptr = self.picload.getData()
			if ptr is not None:
				self.instance.setPixmap(ptr)
				self.instance.show()
			self.picload = None

	def findCover(self, path):
		p1 = p2 = p3 = ""
		name = splitext(path)[0]
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
			prtdir, directoryName = split(directory)
			p1 = join(directory, directoryName)
			p3 = join(prtdir, directoryName)
		fpath = next((f"{base}{x}" for base in (p1, p2, p3) if base for x in self.EXTENSIONS if exists(f"{base}{x}")), "")
		return (p1, fpath)
