import Components.Task
from shutil import move, copy2, rmtree

class FailedPostcondition(Components.Task.Condition):
	def __init__(self, exception):
		self.exception = exception
	def getErrorMessage(self, task):
		return str(self.exception)
	def check(self, task):
		return self.exception is None

class CopyFileTask(Components.Task.PythonTask):
	def openFiles(self, fileList):
		self.fileList = fileList

	def work(self):
		print "[CopyFileTask] files ", self.fileList
		errors = []
		for src, dst in self.fileList:
			try:
				copy2(src, dst)
			except Exception, e:
				errors.append(e)
		if errors:
			raise errors[0]

class MoveFileTask(CopyFileTask):
	def work(self):
		print "[MoveFileTask] files ", self.fileList
		errors = []
		for src, dst in self.fileList:
			try:
				move(src, dst)
			except Exception, e:
				errors.append(e)
		if errors:
			raise errors[0]

class DeleteFolderTask(CopyFileTask):
	def work(self):
		print "[DeleteFolderTask] files ", self.fileList
		errors = []
		try:
			rmtree(self.fileList)
		except Exception, e:
			errors.append(e)
		if errors:
			raise errors[0]

def copyFiles(fileList, name):
	name = _("Copy") + " " + name
	job = Components.Task.Job(name)
	task = CopyFileTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)

def moveFiles(fileList, name):
	name = _("Move") + " " + name
	job = Components.Task.Job(name)
	task = MoveFileTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)

def deleteFiles(fileList, name):
	name = _("Delete") + " " + name
	job = Components.Task.Job(name)
	task = DeleteFolderTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)
