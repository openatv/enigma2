from Components.Task import PythonTask, Task, Job, job_manager as JobManager
from Tools.Directories import fileExists
from enigma import eTimer
from os import path
from shutil import rmtree

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
		cmdline = "cp -Rf \"%s\" \"%s\"" % (srcfile,destfile)
		AddFileProcessTask(self, cmdline, srcfile, destfile, name)

class MoveFileJob(Job):
	def __init__(self, srcfile, destfile, name):
		Job.__init__(self, _("Moving files"))
		cmdline = "mv -f \"%s\" \"%s\"" % (srcfile,destfile)
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


def copyFiles(fileList, name):
	for src, dst in fileList:
		JobManager.AddJob(CopyFileJob(src, dst, name))

def moveFiles(fileList, name):
	for src, dst in fileList:
		JobManager.AddJob(MoveFileJob(src, dst, name))

def deleteFiles(fileList, name):
	job = Components.Task.Job(_("Deleting files"))
	task = DeleteFolderTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)
