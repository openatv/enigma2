import os
import Components.Task
from twisted.internet import reactor, threads, task

class FailedPostcondition(Components.Task.Condition):
	def __init__(self, exception):
		self.exception = exception
	def getErrorMessage(self, task):
		return str(self.exception)
	def check(self, task):
		return self.exception is None


class CopyFileTask(Components.Task.Task):
	def openFiles(self, fileList):
		self.callback = None
		self.handles = [(open(fn[0], 'rb'), open(fn[1], 'wb')) for fn in fileList]
		self.end = 0
		for src,dst in fileList:
			try:
				self.end += os.stat(src).st_size
			except:
				print "Failed to stat", src
		if not self.end:
			self.end = 1
		print "[CopyFileTask] size:", self.end
	def run(self, callback):
		print "[CopyFileTask] run"
		self.callback = callback
		self.aborted = False
		self.pos = 0
		threads.deferToThread(self.copyHandles).addBoth(self.onComplete)
		self.timer = task.LoopingCall(self.onTimer)
		self.timer.start(5, False)
	def copyHandles(self):
		print "copyHandles: ", len(self.handles)
		try:
			for src, dst in self.handles:
				while 1:
					if self.aborted:
						raise Exception, "Aborted"
					d = src.read(65536)
					if not d:
						# EOF
						break
					dst.write(d)
					self.pos += len(d)
		finally:
			# In any event, close all handles
			for src, dst in self.handles:
				src.close()
				dst.close()
	def abort(self):
		print "[CopyFileTask] abort!"
		self.aborted = True
		if self.callback is None:
			self.finish(aborted = True)
	def onTimer(self):
		self.setProgress(self.pos)
	def onComplete(self, result):
		#callback from reactor, result=None or Failure.
		print "[CopyFileTask] onComplete", result
		self.postconditions.append(FailedPostcondition(result))
		self.timer.stop()
		del self.timer
		if result is None:
			print "[CopyFileTask] done, okay"
		else:
			for s,d in fileList:
				# Remove incomplete data.
				try:
					os.unlink(d)
				except:
					pass
		self.finish()


def copyFiles(fileList, name):
	name = _("Copy") + " " + name
	job = Components.Task.Job(name)
	task = CopyFileTask(job, name)
	task.openFiles(fileList)
	Components.Task.job_manager.AddJob(job)

