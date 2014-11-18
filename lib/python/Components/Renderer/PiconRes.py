import os, re, unicodedata
from Renderer import Renderer
from enigma import ePixmap
from Tools.Alternatives import GetWithAlternative
from Tools.Directories import pathExists, SCOPE_SKIN_IMAGE, SCOPE_ACTIVE_SKIN, resolveFilename
from Components.Harddisk import harddiskmanager
from Components.config import config
from ServiceReference import ServiceReference


searchPaths = []
lastPiconPath = None

def initPiconPaths():
	global searchPaths
	searchPaths = []
	for mp in ('/usr/share/enigma2/', '/'):
		onMountpointAdded(mp)
	for part in harddiskmanager.getMountedPartitions():
		onMountpointAdded(part.mountpoint)

def onMountpointAdded(mountpoint):
	global searchPaths
	try:
		path = os.path.join(mountpoint, 'picon') + '/'
		if os.path.isdir(path) and path not in searchPaths:
			for fn in os.listdir(path):
				if fn.endswith('.png'):
					print "[Picon] adding path:", path
					searchPaths.append(path)
					break
	except Exception, ex:
		print "[Picon] Failed to investigate %s:" % mountpoint, ex

def onMountpointRemoved(mountpoint):
	global searchPaths
	path = os.path.join(mountpoint, 'picon') + '/'
	try:
		searchPaths.remove(path)
		print "[Picon] removed path:", path
	except:
		pass

def onPartitionChange(why, part):
	if why == 'add':
		onMountpointAdded(part.mountpoint)
	elif why == 'remove':
		onMountpointRemoved(part.mountpoint)

def findPicon(serviceName):
	global lastPiconPath
	if lastPiconPath is not None:
		pngname = lastPiconPath + serviceName + ".png"
		if pathExists(pngname):
			return pngname
		else:
			return ""
	else:
		global searchPaths
		pngname = ""
		for path in searchPaths:
			if pathExists(path) and not path.startswith('/media/net'):
				pngname = path + serviceName + ".png"
				if pathExists(pngname):
					lastPiconPath = path
					break
			elif pathExists(path):
				pngname = path + serviceName + ".png"
				if pathExists(pngname):
					lastPiconPath = path
					break
		if pathExists(pngname):
			return pngname
		else:
			return ""

def getPiconName(serviceName):
	#remove the path and name fields, and replace ':' by '_'
	sname = '_'.join(GetWithAlternative(serviceName).split(':', 10)[:10])
	pngname = findPicon(sname)
	if not pngname:
		fields = sname.split('_', 3)
		if len(fields) > 2 and fields[2] != '2': #fallback to 1 for tv services with nonstandard servicetypes
			fields[2] = '1'
		if len(fields) > 0 and fields[0] == '4097': #fallback to 1 for IPTV streams
			fields[0] = '1'
		pngname = findPicon('_'.join(fields))
	if not pngname: # picon by channel name
		name = ServiceReference(serviceName).getServiceName()
		name = unicodedata.normalize('NFKD', unicode(name, 'utf_8')).encode('ASCII', 'ignore')
		name = re.sub('[^a-z0-9]', '', name.replace('&', 'and').replace('+', 'plus').replace('*', 'star').lower())
		if name:
			pngname = findPicon(name)
	return pngname

def resizePicon(pngname):
	try:
		from PIL import Image
		im = Image.open(pngname)
		im.resize((220,132)).save("/tmp/picon.png")
		pngname = "/tmp/picon.png"
	except:
		print"[PiconRes] error resizePicon"
		pass
	return pngname

class PiconRes(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = ""
		self.lastPath = None
		pngname = findPicon("picon_default")
		self.defaultpngname = None
		if not pngname:
			tmp = resolveFilename(SCOPE_ACTIVE_SKIN, "picon_default.png")
			if pathExists(tmp):
				pngname = tmp
			else:
				pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
		self.nopicon = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
		if os.path.getsize(pngname):
			self.defaultpngname = pngname
			self.nopicon = pngname

	def addPath(self, value):
		if pathExists(value):
			global searchPaths
			if not value.endswith('/'):
				value += '/'
			if value not in searchPaths:
				searchPaths.append(value)

	def applySkin(self, desktop, parent):
		attribs = self.skinAttributes[:]
		for (attrib, value) in self.skinAttributes:
			if attrib == "path":
				self.addPath(value)
				attribs.remove((attrib,value))
		self.skinAttributes = attribs
		return Renderer.applySkin(self, desktop, parent)

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] != self.CHANGED_CLEAR:
				pngname = getPiconName(self.source.text)
			if not pngname: # no picon for service found
				pngname = self.defaultpngname
			if not config.usage.showpicon.getValue():
				pngname = self.nopicon
			if self.pngname != pngname:
				if pngname:
					self.instance.setScale(1)
					self.instance.setPixmapFromFile(resizePicon(pngname))
					self.instance.show()
				else:
					self.instance.hide()
				self.pngname = pngname

harddiskmanager.on_partition_list_change.append(onPartitionChange)
initPiconPaths()
