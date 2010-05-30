import time
import os

try:
	import enigma
	from Components.config import config
except:
	print "Cannot import enigma"

from Directories import resolveFilename, SCOPE_HDD

def getTrashFolder():
	# Returns trash folder without symlinks
	return os.path.realpath(os.path.join(resolveFilename(SCOPE_HDD), ".Trash"))

def createTrashFolder():
	trash = getTrashFolder()
	if not os.path.isdir(trash):
		os.mkdir(trash)
	return trash

class Trashcan:
	def __init__(self, session):
		self.session = session
		session.nav.record_event.append(self.gotRecordEvent)
		self.gotRecordEvent(None, None)
	
	def gotRecordEvent(self, service, event):
		print "[Trashcan] gotRecordEvent", service, event
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
		try:
			ctimeLimit = time.time() - (config.usage.movielist_trashcan_days.value * 3600 * 24)
			reserveBytes = 1024*1024*1024 * int(config.usage.movielist_trashcan_reserve.value) 
			clean(ctimeLimit, reserveBytes)
		except Exception, e:
			print "[Trashcan] Weirdness:", e

def clean(ctimeLimit, reserveBytes):
		# Remove expired items from trash, and attempt to have
		# reserveBytes of free disk space. 
		trash = getTrashFolder()
		if not os.path.isdir(trash):
			print "[Trashcan] No trash.", trash
			return 0
		diskstat = os.statvfs(trash)
		free = diskstat.f_bfree * diskstat.f_bsize
		bytesToRemove = reserveBytes - free 
		candidates = []
		print "[Trashcan] bytesToRemove", bytesToRemove
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
		 
		
def cleanAll():
		trash = getTrashFolder()
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

# Unit test
# (can be run outside enigma. Can be moved somewhere else later on)
if __name__ == '__main__':
	class Fake:
		def __init__(self):
			self.record_event = []
			self.nav = self
			self.RecordTimer = self
			self.usage = self
			self.movielist_trashcan_days = self
			self.movielist_trashcan_reserve = self
			self.value = 1
			self.eBackgroundFileEraser = self
			self.iRecordableService = self
			self.evEnd = None
		def getInstance(self):
			# eBackgroundFileEraser
			return self
		def erase(self, fn):
			print "ERASE", fn 
		def getNextRecordingTime(self):
			# RecordTimer
			return time.time() + 500
		def getRecordings(self):
			return []
		def destroy(self):
			if self.record_event:
				raise Exception, "record_event not empty" + str(self.record_event)
	
	s = Fake()
	createTrashFolder()
	config = s
	enigma = s
	init(s)
	diskstat = os.statvfs('/hdd/movie')
	free = diskstat.f_bfree * diskstat.f_bsize
	# Clean up one MB
	clean(1264606758, free + 1000000)
	cleanAll()
	instance.destroy()
	s.destroy()
