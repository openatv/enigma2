import time
import os

try:
	import enigma
	from Components.config import config
except:
	print "Cannot import enigma"

from Directories import resolveFilename, SCOPE_HDD

def getTrashFolder():
	return os.path.join(resolveFilename(SCOPE_HDD), ".Trash")

class Trashcan:
	def __init__(self, session):
		self.session = session
		session.nav.record_event.append(self.gotRecordEvent)
		self.gotRecordEvent(None, None)
	
	def gotRecordEvent(self, service, event):
		print "[Trashcan] gotRecordEvent", service, event
		self.recordings = len(self.session.nav.getRecordings())
		self.cleanIfIdle()
	
	def cleanIfIdle(self):
		if self.recordings:
			print "[Trashcan] Recording in progress", self.recordings
			return
		next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()	
		if (next_rec_time > 0) and ((next_rec_time - time.time()) < 30):
			print "[Trashcan] Recording about to start in", int(next_rec_time - time.time()), "sec."
			return
		try:
			self.clean()
		except Exception, e:
			print "[Trashcan] Weirdness:", e

	def clean(self):
		trash = getTrashFolder()
		if not os.path.isdir(trash):
			print "[Trashcan] No trash.", trash
			return 0
		ctimeLimit = time.time() - (config.usage.movielist_trashcan_days.value * 3600 * 24)
		for root, dirs, files in os.walk(trash, topdown=False):
			for name in files:
				try:
					fn = os.path.join(root, name)
					st = os.stat(fn)
					if st.st_ctime < ctimeLimit:
						print "[Trashcan] Too old:", name, st.st_ctime
						enigma.eBackgroundFileEraser.getInstance().erase(fn)
				except Exception, e:
					print "[Trashcan] Failed to stat %s:"% name, e 
			# Remove empty directories if possible
			for name in dirs:
				try:
					os.rmdir(os.path.join(root, name))
				except:
					pass

		
	
	def destroy(self):
		if self.session is not None:
			self.session.nav.record_event.remove(self.gotRecordEvent)
		self.session = None

	def __del__(self):
		self.destroy()

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
			self.value = 0.001
			self.eBackgroundFileEraser = self
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
	config = s
	enigma = s
	init(s)
	instance.destroy()
	s.destroy()
