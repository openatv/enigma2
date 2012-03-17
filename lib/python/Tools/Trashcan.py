import time
import os
import enigma
from Components.config import config
from Components import Harddisk
from twisted.internet import threads

def getTrashFolder(path):
	# Returns trash folder without symlinks. Path may be file or directory or whatever.
	mountpoint = Harddisk.findMountPoint(os.path.realpath(path))
	movie = os.path.join(mountpoint, 'movie')
	if os.path.isdir(movie):
		mountpoint = movie
	return os.path.join(mountpoint, ".Trash")

def createTrashFolder(path):
	# Create and return trash folder for given file or dir
	trash = getTrashFolder(path)
	if not os.path.isdir(trash):
		print "[Trashcan] create:", trash
		os.mkdir(trash)
	return trash

def enumTrashFolders():
	# Walk through all Trash folders. This may access network
	# drives and similar, so might block for minutes.
	for mount in Harddisk.getProcMounts():
		if mount[1].startswith('/media/'):
			mountpoint = mount[1]
			movie = os.path.join(mountpoint, 'movie')
			if os.path.isdir(movie):
				mountpoint = movie
			result = os.path.join(mountpoint, ".Trash")
			if os.path.isdir(result):
				yield result

class Trashcan:
	def __init__(self, session):
		self.session = session
		session.nav.record_event.append(self.gotRecordEvent)
		self.isCleaning = False
		self.gotRecordEvent(None, None)
	
	def gotRecordEvent(self, service, event):
		self.recordings = len(self.session.nav.getRecordings())
		if (event == enigma.iRecordableService.evEnd):
			self.cleanIfIdle()
	
	def destroy(self):
		if self.session is not None:
			self.session.nav.record_event.remove(self.gotRecordEvent)
		self.session = None

	def __del__(self):
		self.destroy()

	def cleanIfIdle(self):
		# RecordTimer calls this when preparing a recording. That is a
		# nice moment to clean up.
		if self.recordings:
			print "[Trashcan] Recording in progress", self.recordings
			return
		if self.isCleaning:
			print "[Trashcan] Cleanup already running"
			return
		self.isCleaning = True
		ctimeLimit = time.time() - (config.usage.movielist_trashcan_days.value * 3600 * 24)
		reserveBytes = 1024*1024*1024 * int(config.usage.movielist_trashcan_reserve.value)
		threads.deferToThread(clean, ctimeLimit, reserveBytes).addCallbacks(self.cleanReady, self.cleanFail)

	def cleanReady(self, result=None):
		self.isCleaning = False

	def cleanFail(self, failure):
		print "[Trashcan] ERROR in clean:", failure
		self.isCleaning = False

def clean(ctimeLimit, reserveBytes):
	# Remove expired items from trash, and attempt to have
	# reserveBytes of free disk space.
	for trash in enumTrashFolders():
		if not os.path.isdir(trash):
			print "[Trashcan] No trash.", trash
			return 0
		diskstat = os.statvfs(trash)
		free = diskstat.f_bfree * diskstat.f_bsize
		bytesToRemove = reserveBytes - free 
		candidates = []
		print "[Trashcan] bytesToRemove", bytesToRemove, trash
		size = 0
		for root, dirs, files in os.walk(trash, topdown=False):
			for name in files:
				try:
					fn = os.path.join(root, name)
					st = os.stat(fn)
					if st.st_ctime < ctimeLimit:
						print "[Trashcan] Too old:", name, st.st_ctime
						enigma.eBackgroundFileEraser.getInstance().erase(fn)
						bytesToRemove -= st.st_size
					else:
						candidates.append((st.st_ctime, fn, st.st_size))
						size += st.st_size
				except Exception, e:
					print "[Trashcan] Failed to stat %s:"% name, e 
			# Remove empty directories if possible
			for name in dirs:
				try:
					os.rmdir(os.path.join(root, name))
				except:
					pass
		candidates.sort()
		# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
		print "[Trashcan] Bytes to remove:", bytesToRemove
		print "[Trashcan] Size now:", size
		for st_ctime, fn, st_size in candidates:
			if bytesToRemove < 0:
				break
			enigma.eBackgroundFileEraser.getInstance().erase(fn)
			bytesToRemove -= st_size
			size -= st_size
		print "[Trashcan] Size now:", size
 
def cleanAll(trash):
		if not os.path.isdir(trash):
			print "[Trashcan] No trash.", trash
			return 0
		for root, dirs, files in os.walk(trash, topdown=False):
			for name in files:
				fn = os.path.join(root, name)
				try:
					enigma.eBackgroundFileEraser.getInstance().erase(fn)
				except Exception, e:
					print "[Trashcan] Failed to erase %s:"% name, e 
			# Remove empty directories if possible
			for name in dirs:
				try:
					os.rmdir(os.path.join(root, name))
				except:
					pass

def init(session):
	global instance
	instance = Trashcan(session)
