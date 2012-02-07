import Components.Task
from Components.config import config
from Components import Harddisk
import time
import os
import enigma

def getTrashFolder(path=None):
	# Returns trash folder without symlinks
	if path is None:
		print 'path is none'
	else:
		mountpoint = Harddisk.findMountPoint(os.path.realpath(path))
		movietrash = os.path.join(mountpoint, 'movie')
		movietrash = os.path.join(movietrash, '.Trash')
		roottrash = os.path.join(mountpoint, '.Trash')
		if os.path.isdir(movietrash):
			   mountpoint = movietrash
		elif os.path.isdir(roottrash):
			   mountpoint = roottrash
		return mountpoint

def createTrashFolder(path=None):
	trash = getTrashFolder(path)
	if not os.path.isdir(trash):
		os.mkdir(trash)
	return trash

class Trashcan:
	def __init__(self, session):
		self.session = session
		session.nav.record_event.append(self.gotRecordEvent)
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
		ctimeLimit = time.time() - (config.usage.movielist_trashcan_days.value * 3600 * 24)
		reserveBytes = 1024*1024*1024 * int(config.usage.movielist_trashcan_reserve.value)
		clean(ctimeLimit, reserveBytes)
	
def clean(ctimeLimit, reserveBytes):
	isCleaning = False
	for job in Components.Task.job_manager.getPendingJobs():
		jobname = str(job.name)
		if jobname.startswith(_("Cleaning Trashes")):
			isCleaning = True
			break

	if config.usage.movielist_trashcan.value and not isCleaning:
		name = _("Cleaning Trashes")
		job = Components.Task.Job(name)
		task = CleanTrashTask(job, name)
		task.openFiles(ctimeLimit, reserveBytes)
		Components.Task.job_manager.AddJob(job)
	elif isCleaning:
		print "[Trashcan] Cleanup already running"
	else:
		print "[Trashcan] Disabled skipping check."
		
def cleanAll(path=None):
	trash = getTrashFolder(path)
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

class CleanTrashTask(Components.Task.PythonTask):
	def openFiles(self, ctimeLimit, reserveBytes):
		self.ctimeLimit = ctimeLimit
		self.reserveBytes = reserveBytes

	def work(self):
		mounts=[]
		matches = []
		print "[Trashcan] probing folders"
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			mounts.append(parts[1])
		f.close()

		for mount in mounts:
			if os.path.isdir(os.path.join(mount,'.Trash')):
				matches.append(os.path.join(mount,'.Trash'))
			elif os.path.isdir(os.path.join(mount,'movie/.Trash')):
				matches.append(os.path.join(mount,'movie/.Trash'))
				
		print "[Trashcan] found following trashcan's:",matches
		if len(matches):
			for trashfolder in matches:
				print "[Trashcan] looking in trashcan",trashfolder
				diskstat = os.statvfs(trashfolder)
				free = diskstat.f_bfree * diskstat.f_bsize
				bytesToRemove = self.reserveBytes - free 
				candidates = []
				print "[Trashcan] " + str(trashfolder) + ": bytesToRemove",bytesToRemove
				size = 0
				for root, dirs, files in os.walk(trashfolder, topdown=False):
					for name in files:
						try:
							fn = os.path.join(root, name)
							st = os.stat(fn)
							if st.st_ctime < self.ctimeLimit:
								print "[Trashcan] " + str(trashfolder) + ": Too old:",name, st.st_ctime
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
				print "[Trashcan] " + str(trashfolder) + ": Bytes to remove:",bytesToRemove
				print "[Trashcan] " + str(trashfolder) + ": Size now:",size
				for st_ctime, fn, st_size in candidates:
					if bytesToRemove < 0:
						break
					enigma.eBackgroundFileEraser.getInstance().erase(fn)
					bytesToRemove -= st_size
					size -= st_size
				print "[Trashcan] " + str(trashfolder) + ": Size now:",size

