from Components.Task import PythonTask, Task, Job, job_manager as JobManager, Condition
from Tools.Directories import fileExists
from enigma import eTimer
from os import path
from shutil import rmtree, copy2, move

class DeleteFolderTask(PythonTask):
	def openFiles(self, fileList):
		self.fileList = fileList

	def work(self):
		print "[DeleteFolderTask] files ", self.fileList
		errors = []
		try:
			rmtree(self.fileList)
		except Exception, e:
			errors.append(e)
		if errors:
			raise errors[0]

class CopyFileJob(Job):
	def __init__(self, srcfile, destfile, name):
		Job.__init__(self, _("Copying files"))
		cmdline = 'cp -Rf "%s" "%s"' % (srcfile,destfile)
		AddFileProcessTask(self, cmdline, srcfile, destfile, name)

class MoveFileJob(Job):
	def __init__(self, srcfile, destfile, name):
		Job.__init__(self, _("Moving files"))
		cmdline = 'mv -f "%s" "%s"' % (srcfile,destfile)
		AddFileProcessTask(self, cmdline, srcfile, destfile, name)

class AddFileProcessTask(Task):
	def __init__(self, job, cmdline, srcfile, destfile, name):
		Task.__init__(self, job, name)
		self.setCmdline(cmdline)
		self.srcfile = srcfile
		self.destfile = destfile

		self.ProgressTimer = eTimer()
		self.ProgressTimer.callback.append(self.ProgressUpdate)

	def ProgressUpdate(self):
		if self.srcsize <= 0 or not fileExists(self.destfile, 'r'):
			return

		self.setProgress(int((path.getsize(self.destfile)/float(self.srcsize))*100))
		self.ProgressTimer.start(5000, True)

	def prepare(self):
		if fileExists(self.srcfile, 'r'):
			self.srcsize = path.getsize(self.srcfile)
			self.ProgressTimer.start(5000, True)

	def afterRun(self):
		self.setProgress(100)
		self.ProgressTimer.stop()


class DownloadProcessTask(Job):
	def __init__(self, url, filename, file):
		Job.__init__(self, _("%s") % file)
		DownloadTask(self, url, filename)

class DownloaderPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return self.error_message

class DownloadTask(Task):
	def __init__(self, job, url, path):
		Task.__init__(self, job, _("Downloading"))
		self.postconditions.append(DownloaderPostcondition())
		self.job = job
		self.url = url
		self.path = path
		self.error_message = ""
		self.last_recvbytes = 0
		self.error_message = None
		self.download = None
		self.aborted = False

	def run(self, callback):
		from Tools.Downloader import downloadWithProgress
		self.callback = callback
		self.download = downloadWithProgress(self.url,self.path)
		self.download.addProgress(self.download_progress)
		self.download.start().addCallback(self.download_finished).addErrback(self.download_failed)
		print "[DownloadTask] downloading", self.url, "to", self.path

	def abort(self):
		print "[DownloadTask] aborting", self.url
		if self.download:
			self.download.stop()
		self.aborted = True

	def download_progress(self, recvbytes, totalbytes):
		if ( recvbytes - self.last_recvbytes  ) > 100000: # anti-flicker
			self.progress = int(100*(float(recvbytes)/float(totalbytes)))
			if (((float(totalbytes)/1024)/1024)/1024) >= 1:
				self.name = _("Downloading") + ' ' + _("%s of %s GB") % (str(round((((float(recvbytes)/1024)/1024)/1024),2)), str(round((((float(totalbytes)/1024)/1024)/1024),2)))
			elif ((float(totalbytes)/1024)/1024) >= 1:
				self.name = _("Downloading") + ' ' + _("%s of %s MB") % (str(round(((float(recvbytes)/1024)/1024),2)), str(round(((float(totalbytes)/1024)/1024),2)))
			elif (totalbytes/1024) >= 1:
				self.name = _("Downloading") + ' ' + _("%d of %d KB") % (recvbytes/1024, totalbytes/1024)
			else:
				self.name = _("Downloading") + ' ' + _("%d of %d Bytes") % (recvbytes, totalbytes)
			self.last_recvbytes = recvbytes

	def download_failed(self, failure_instance=None, error_message=""):
		self.error_message = error_message
		if error_message == "" and failure_instance is not None:
			self.error_message = failure_instance.getErrorMessage()
		Task.processFinished(self, 1)

	def download_finished(self, string=""):
		if self.aborted:
			self.finish(aborted = True)
		else:
			Task.processFinished(self, 0)

def copyFiles(fileList, name):
	for src, dst in fileList:
		if path.isdir(src) or int(path.getsize(src))/1000/1000 > 100:
			JobManager.AddJob(CopyFileJob(src, dst, name))
		else:
			copy2(src, dst)

def moveFiles(fileList, name):
	for src, dst in fileList:
		if path.isdir(src) or int(path.getsize(src))/1000/1000 > 100:
			JobManager.AddJob(MoveFileJob(src, dst, name))
		else:
			move(src, dst)

def deleteFiles(fileList, name):
	job = Job(_("Deleting files"))
	task = DeleteFolderTask(job, name)
	task.openFiles(fileList)
	JobManager.AddJob(job)

def downloadFile(url, file_name, sel):
	JobManager.AddJob(DownloadProcessTask(url, file_name, sel))
