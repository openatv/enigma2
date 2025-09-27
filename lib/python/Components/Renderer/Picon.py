from os import listdir
from os.path import exists, getsize, isdir, join
from re import sub
from enigma import ePixmap  # , ePicLoad
from Components.config import config
from Components.Harddisk import harddiskmanager
from Components.Renderer.Renderer import Renderer
from ServiceReference import ServiceReference
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import SCOPE_SKINS, SCOPE_GUISKIN, resolveFilename, sanitizeFilename

searchPaths = []
lastPiconPath = None


def initPiconPaths():
	global searchPaths
	searchPaths = []
	for mp in ("/usr/share/enigma2/", "/"):
		onMountpointAdded(mp)
	for part in harddiskmanager.getMountedPartitions():
		mp = join(part.mountpoint, "usr/share/enigma2")
		onMountpointAdded(part.mountpoint)
		onMountpointAdded(mp)


def onMountpointAdded(mountpoint):
	global searchPaths
	try:
		path = join(mountpoint, "picon", "")
		if isdir(path) and path not in searchPaths:
			for fn in listdir(path):
				if fn.endswith(".png"):
					print(f"[Picon] adding path: {path}")
					searchPaths.append(path)
					break
	except Exception as err:
		print(f"[Picon] Failed to investigate {mountpoint}:{str(err)}")


def onMountpointRemoved(mountpoint):
	global searchPaths
	path = join(mountpoint, "picon", "")
	try:
		searchPaths.remove(path)
		print(f"[Picon] removed path: {path}")
	except Exception:
		pass


def onPartitionChange(why, part):
	if why == "add":
		onMountpointAdded(part.mountpoint)
	elif why == "remove":
		onMountpointRemoved(part.mountpoint)


def findPicon(serviceName):
	global lastPiconPath
	if lastPiconPath is not None:
		pngname = f"{lastPiconPath}{serviceName}.png"
		return pngname if exists(pngname) else ""
	else:
		for path in searchPaths:
			if exists(path) and not path.startswith("/media/net"):
				pngname = f"{path}{serviceName}.png"
				if exists(pngname):
					lastPiconPath = path
					return pngname
		return ""


def getPiconName(serviceName):
	fields = GetWithAlternative(serviceName).split(":", 10)[:10]  # Remove the path and name fields, and replace ":" by "_"
	if not fields or len(fields) < 10:
		return ""
	pngname = findPicon("_".join(fields))
	if not pngname and not fields[6].endswith("0000"):
		fields[6] = fields[6][:-4] + "0000"  # Remove "sub-network" from namespace
		pngname = findPicon("_".join(fields))
	if not pngname and fields[0] != "1":
		fields[0] = "1"  # Fallback to 1 for other reftypes
		pngname = findPicon("_".join(fields))
	if not pngname and fields[2] != "1":
		fields[2] = "1"  # Fallback to 1 for services with different service types
		pngname = findPicon("_".join(fields))
	if not pngname:
		if (sName := ServiceReference(serviceName).getServiceName()) and "SID 0x" not in sName and (utf8Name := sanitizeFilename(sName).lower()) and utf8Name != "__":  # avoid lookups on zero length service names
			legacyName = sub("[^a-z0-9]", "", utf8Name.replace("&", "and").replace("+", "plus").replace("*", "star"))  # legacy ascii service name picons
			pngname = findPicon(utf8Name) or legacyName and findPicon(legacyName) or findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", utf8Name).strip()) or legacyName and findPicon(sub(r"(fhd|uhd|hd|sd|4k)$", "", legacyName).strip())
	return pngname


class Picon(Renderer):
	GUI_WIDGET = ePixmap

	def __init__(self):
		Renderer.__init__(self)
		# self.PicLoad = ePicLoad()
		# self.PicLoad.PictureData.get().append(self.updatePicon)
		self.piconsize = (0, 0)
		self.pngname = ""
		self.lastPath = None
		defaultName = "picon_default"
		pngname = findPicon(defaultName)
		self.defaultpngname = None
		if not pngname:
			tmp = resolveFilename(SCOPE_GUISKIN, f"{defaultName}.png")
			if exists(tmp):
				pngname = tmp
			else:
				pngname = resolveFilename(SCOPE_SKINS, f"skin_default/{defaultName}.png")
		self.nopicon = resolveFilename(SCOPE_SKINS, f"skin_default/{defaultName}.png")
		if getsize(pngname):
			self.defaultpngname = pngname
			self.nopicon = pngname

	def addPath(self, value):
		if exists(value):
			global searchPaths
			value = join(value, "")
			if value not in searchPaths:
				searchPaths.append(value)

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.addPath(value)
				attribs.remove((attrib, value))
			elif attrib == "size":
				self.piconsize = value
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	#def updatePicon(self, picInfo=None):
	#	ptr = self.PicLoad.getData()
	#	if ptr is not None:
	#		self.instance.setPixmap(ptr.__deref__())
	#		self.instance.show()

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] == 1 or what[0] == 3:
				pngname = getPiconName(self.source.text)
				if not exists(pngname):  # No picon for service found
					pngname = self.defaultpngname
				if not config.usage.showpicon.value:
					pngname = self.nopicon
				if self.pngname != pngname:
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
#						self.PicLoad.setPara((self.piconsize[0], self.piconsize[1], 0, 0, 1, 1, "#FF000000"))
#						self.PicLoad.startDecode(pngname)
					else:
						self.instance.hide()
					self.pngname = pngname
			elif what[0] == 2:
				self.pngname = ""
				self.instance.hide()


harddiskmanager.on_partition_list_change.append(onPartitionChange)
initPiconPaths()
