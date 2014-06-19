# A Job consists of many "Tasks".
# A task is the run of an external tool, with proper methods for failure handling

from Tools.CList import CList

class Job(object):
	NOT_STARTED, IN_PROGRESS, FINISHED, FAILED = range(4)
	def __init__(self, name):
		self.tasks = [ ]
		self.resident_tasks = [ ]
		self.workspace = "/tmp"
		self.current_task = 0
		self.callback = None
		self.name = name
		self.finished = False
		self.end = 100
		self.__progress = 0
		self.weightScale = 1
		self.afterEvent = None
		self.state_changed = CList()
		self.status = self.NOT_STARTED
		self.onSuccess = None

	# description is a dict
	def fromDescription(self, description):
		pass

	def createDescription(self):
		return None

	def getProgress(self):
		if self.current_task == len(self.tasks):
			return self.end
		t = self.tasks[self.current_task]
		jobprogress = t.weighting * t.progress / float(t.end) + sum([task.weighting for task in self.tasks[:self.current_task]])
		return int(jobprogress*self.weightScale)

	progress = property(getProgress)

	def getStatustext(self):
		return { self.NOT_STARTED: _("Waiting"), self.IN_PROGRESS: _("In progress"), self.FINISHED: _("Finished"), self.FAILED: _("Failed") }[self.status]

	def task_progress_changed_CB(self):
		self.state_changed()

	def addTask(self, task):
		task.job = self
		task.task_progress_changed = self.task_progress_changed_CB
		self.tasks.append(task)

	def start(self, callback):
		assert self.callback is None
		self.callback = callback
		self.restart()

	def restart(self):
		self.status = self.IN_PROGRESS
		self.state_changed()
		self.runNext()
		sumTaskWeightings = sum([t.weighting for t in self.tasks]) or 1
		self.weightScale = self.end / float(sumTaskWeightings)

	def runNext(self):
		if self.current_task == len(self.tasks):
			if len(self.resident_tasks) == 0:
				self.status = self.FINISHED
				self.state_changed()
				self.callback(self, None, [])
				self.callback = None
			else:
				print "still waiting for %d resident task(s) %s to finish" % (len(self.resident_tasks), str(self.resident_tasks))
		else:
			self.tasks[self.current_task].run(self.taskCallback)
			self.state_changed()

	def taskCallback(self, task, res, stay_resident = False):
		cb_idx = self.tasks.index(task)
		if stay_resident:
			if cb_idx not in self.resident_tasks:
				self.resident_tasks.append(self.current_task)
				print "task going resident:", task
			else:
				print "task keeps staying resident:", task
				return
		if len(res):
			print ">>> Error:", res
			self.status = self.FAILED
			self.state_changed()
			self.callback(self, task, res)
		if cb_idx != self.current_task:
			if cb_idx in self.resident_tasks:
				print "resident task finished:", task
				self.resident_tasks.remove(cb_idx)
		if res == []:
			self.state_changed()
			self.current_task += 1
			self.runNext()

	def retry(self):
		assert self.status == self.FAILED
		self.restart()

	def abort(self):
		if self.current_task < len(self.tasks):
			self.tasks[self.current_task].abort()
		for i in self.resident_tasks:
			self.tasks[i].abort()

	def cancel(self):
		self.abort()

	def __str__(self):
		return "Components.Task.Job name=%s #tasks=%s" % (self.name, len(self.tasks))

class Task(object):
	def __init__(self, job, name):
		self.name = name
		self.immediate_preconditions = [ ]
		self.global_preconditions = [ ]
		self.postconditions = [ ]
		self.returncode = None
		self.initial_input = None
		self.job = None
		self.end = 100
		self.weighting = 100
		self.__progress = 0
		self.cmd = None
		self.cwd = "/tmp"
		self.args = [ ]
		self.cmdline = None
		self.task_progress_changed = None
		self.output_line = ""
		job.addTask(self)
		self.container = None

	def setCommandline(self, cmd, args):
		self.cmd = cmd
		self.args = args

	def setTool(self, tool):
		self.cmd = tool
		self.args = [tool]
		self.global_preconditions.append(ToolExistsPrecondition())
		self.postconditions.append(ReturncodePostcondition())

	def setCmdline(self, cmdline):
		self.cmdline = cmdline

	def checkPreconditions(self, immediate = False):
		not_met = [ ]
		if immediate:
			preconditions = self.immediate_preconditions
		else:
			preconditions = self.global_preconditions
		for precondition in preconditions:
			if not precondition.check(self):
				not_met.append(precondition)
		return not_met

	def _run(self):
		if (self.cmd is None) and (self.cmdline is None):
			self.finish()
			return
		from enigma import eConsoleAppContainer
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.processFinished)
		self.container.stdoutAvail.append(self.processStdout)
		self.container.stderrAvail.append(self.processStderr)
		if self.cwd is not None:
			self.container.setCWD(self.cwd)
		if not self.cmd and self.cmdline:
			print "execute:", self.container.execute(self.cmdline), self.cmdline
		else:
			assert self.cmd is not None
			assert len(self.args) >= 1
			print "execute:", self.container.execute(self.cmd, *self.args), ' '.join(self.args)
		if self.initial_input:
			self.writeInput(self.initial_input)

	def run(self, callback):
		failed_preconditions = self.checkPreconditions(True) + self.checkPreconditions(False)
		if failed_preconditions:
			print "[Task] preconditions failed"
			callback(self, failed_preconditions)
			return
		self.callback = callback
		try:
			self.prepare()
			self._run()
		except Exception, ex:
			print "[Task] exception:", ex
			self.postconditions = [FailedPostcondition(ex)]
			self.finish()

	def prepare(self):
		pass

	def cleanup(self, failed):
		pass

	def processStdout(self, data):
		self.processOutput(data)

	def processStderr(self, data):
		self.processOutput(data)

	def processOutput(self, data):
		self.output_line += data
		while True:
			i = self.output_line.find('\n')
			if i == -1:
				break
			self.processOutputLine(self.output_line[:i+1])
			self.output_line = self.output_line[i+1:]

	def processOutputLine(self, line):
		print "[Task %s]" % self.name, line[:-1]
		pass

	def processFinished(self, returncode):
		self.returncode = returncode
		self.finish()

	def abort(self):
		if self.container:
			self.container.kill()
		self.finish(aborted = True)

	def finish(self, aborted = False):
		self.afterRun()
		not_met = [ ]
		if aborted:
			not_met.append(AbortedPostcondition())
		else:
			for postcondition in self.postconditions:
				if not postcondition.check(self):
					not_met.append(postcondition)
		self.cleanup(not_met)
		self.callback(self, not_met)

	def afterRun(self):
		pass

	def writeInput(self, input):
		self.container.write(input)

	def getProgress(self):
		return self.__progress

	def setProgress(self, progress):
		if progress > self.end:
			progress = self.end
		if progress < 0:
			progress = 0
		self.__progress = progress
		if self.task_progress_changed:
			self.task_progress_changed()

	progress = property(getProgress, setProgress)

	def __str__(self):
		return "Components.Task.Task name=%s" % (self.name)

class LoggingTask(Task):
	def __init__(self, job, name):
		Task.__init__(self, job, name)
		self.log = []
	def processOutput(self, data):
		print "[%s]" % self.name, data,
		self.log.append(data)


class PythonTask(Task):
	def _run(self):
		from twisted.internet import threads
		from enigma import eTimer
		self.aborted = False
		self.pos = 0
		threads.deferToThread(self.work).addBoth(self.onComplete)
		self.timer = eTimer()
		self.timer.callback.append(self.onTimer)
		self.timer.start(5)
	def work(self):
		raise NotImplemented, "work"
	def abort(self):
		self.aborted = True
		if self.callback is None:
			self.finish(aborted = True)
	def onTimer(self):
		self.setProgress(self.pos)
	def onComplete(self, result):
		self.postconditions.append(FailedPostcondition(result))
		self.timer.stop()
		del self.timer
		self.finish()

class ConditionTask(Task):
	"""
	Reactor-driven pthread_condition.
	Wait for something to happen. Call trigger when something occurs that
	is likely to make check() return true. Raise exception in check() to
	signal error.
	Default is to call trigger() once per second, override prepare/cleanup
	to do something else (like waiting for hotplug)...
	"""
	def __init__(self, job, name, timeoutCount=None):
		Task.__init__(self, job, name)
		self.timeoutCount = timeoutCount
	def _run(self):
		self.triggerCount = 0
	def prepare(self):
		from enigma import eTimer
		self.timer = eTimer()
		self.timer.callback.append(self.trigger)
		self.timer.start(1000)
	def cleanup(self, failed):
		if hasattr(self, 'timer'):
			self.timer.stop()
			del self.timer
	def check(self):
		# override to return True only when condition triggers
		return True
	def trigger(self):
		self.triggerCount += 1
		try:
			if (self.timeoutCount is not None) and (self.triggerCount > self.timeoutCount):
				raise Exception, "Timeout elapsed, sorry"
			res = self.check()
		except Exception, e:
			self.postconditions.append(FailedPostcondition(e))
			res = True
		if res:
			self.finish()

# The jobmanager will execute multiple jobs, each after another.
# later, it will also support suspending jobs (and continuing them after reboot etc)
# It also supports a notification when some error occurred, and possibly a retry.
class JobManager:
	def __init__(self):
		self.active_jobs = [ ]
		self.failed_jobs = [ ]
		self.job_classes = [ ]
		self.in_background = False
		self.visible = False
		self.active_job = None

	# Set onSuccess to popupTaskView to get a visible notification.
	# onFail defaults to notifyFailed which tells the user that it went south.
	def AddJob(self, job, onSuccess=None, onFail=None):
		job.onSuccess = onSuccess
		if onFail is None:
			job.onFail = self.notifyFailed
		else:
			job.onFail = onFail
		self.active_jobs.append(job)
		self.kick()

	def kick(self):
		if self.active_job is None:
			if self.active_jobs:
				self.active_job = self.active_jobs.pop(0)
				self.active_job.start(self.jobDone)

	def notifyFailed(self, job, task, problems):
		from Tools import Notifications
		from Screens.MessageBox import MessageBox
		if problems[0].RECOVERABLE:
			Notifications.AddNotificationWithCallback(self.errorCB, MessageBox, _("Error: %s\nRetry?") % (problems[0].getErrorMessage(task)))
			return True
		else:
			Notifications.AddNotification(MessageBox, job.name + "\n" + _("Error") + (': %s') % (problems[0].getErrorMessage(task)), type = MessageBox.TYPE_ERROR )
			return False

	def jobDone(self, job, task, problems):
		print "job", job, "completed with", problems, "in", task
		if problems:
			if not job.onFail(job, task, problems):
				self.errorCB(False)
		else:
			self.active_job = None
			if job.onSuccess:
				job.onSuccess(job)
			self.kick()

	# Set job.onSuccess to this function if you want to pop up the jobview when the job is done/
	def popupTaskView(self, job):
		if not self.visible:
			from Tools import Notifications
			from Screens.TaskView import JobView
			self.visible = True
			Notifications.AddNotification(JobView, job)

	def errorCB(self, answer):
		if answer:
			print "retrying job"
			self.active_job.retry()
		else:
			print "not retrying job."
			self.failed_jobs.append(self.active_job)
			self.active_job = None
			self.kick()

	def getPendingJobs(self):
		list = [ ]
		if self.active_job:
			list.append(self.active_job)
		list += self.active_jobs
		return list

# some examples:
#class PartitionExistsPostcondition:
#	def __init__(self, device):
#		self.device = device
#
#	def check(self, task):
#		import os
#		return os.access(self.device + "part1", os.F_OK)
#
#class CreatePartitionTask(Task):
#	def __init__(self, device):
#		Task.__init__(self, "Creating partition")
#		self.device = device
#		self.setTool("/sbin/sfdisk")
#		self.args += ["-f", self.device + "disc"]
#		self.initial_input = "0,\n;\n;\n;\ny\n"
#		self.postconditions.append(PartitionExistsPostcondition(self.device))
#
#class CreateFilesystemTask(Task):
#	def __init__(self, device, partition = 1, largefile = True):
#		Task.__init__(self, "Creating filesystem")
#		self.setTool("/sbin/mkfs.ext")
#		if largefile:
#			self.args += ["-T", "largefile"]
#		self.args.append("-m0")
#		self.args.append(device + "part%d" % partition)
#
#class FilesystemMountTask(Task):
#	def __init__(self, device, partition = 1, filesystem = "ext3"):
#		Task.__init__(self, "Mounting filesystem")
#		self.setTool("/bin/mount")
#		if filesystem is not None:
#			self.args += ["-t", filesystem]
#		self.args.append(device + "part%d" % partition)

class Condition:
	RECOVERABLE = False

	def getErrorMessage(self, task):
		return _("An unknown error occurred!") + " (%s @ task %s)" % (self.__class__.__name__, task.__class__.__name__)

class WorkspaceExistsPrecondition(Condition):
	def check(self, task):
		return os.access(task.job.workspace, os.W_OK)

class DiskspacePrecondition(Condition):
	def __init__(self, diskspace_required):
		self.diskspace_required = diskspace_required
		self.diskspace_available = 0

	def check(self, task):
		import os
		try:
			s = os.statvfs(task.job.workspace)
			self.diskspace_available = s.f_bsize * s.f_bavail
			return self.diskspace_available >= self.diskspace_required
		except OSError:
			return False

	def getErrorMessage(self, task):
		return _("Not enough disk space. Please free up some disk space and try again. (%d MB required, %d MB available)") % (self.diskspace_required / 1024 / 1024, self.diskspace_available / 1024 / 1024)

class ToolExistsPrecondition(Condition):
	def check(self, task):
		import os
		if task.cmd[0]=='/':
			self.realpath = task.cmd
			print "[Task.py][ToolExistsPrecondition] WARNING: usage of absolute paths for tasks should be avoided!"
			return os.access(self.realpath, os.X_OK)
		else:
			self.realpath = task.cmd
			path = os.environ.get('PATH', '').split(os.pathsep)
			path.append(task.cwd + '/')
			absolutes = filter(lambda file: os.access(file, os.X_OK), map(lambda directory, file = task.cmd: os.path.join(directory, file), path))
			if absolutes:
				self.realpath = absolutes[0]
				return True
		return False

	def getErrorMessage(self, task):
		return _("A required tool (%s) was not found.") % (self.realpath)

class AbortedPostcondition(Condition):
	def getErrorMessage(self, task):
		return "Cancelled upon user request"

class ReturncodePostcondition(Condition):
	def check(self, task):
		return task.returncode == 0
	def getErrorMessage(self, task):
		if hasattr(task, 'log') and task.log:
			log = ''.join(task.log).strip()
			log = log.split('\n')[-3:]
			log = '\n'.join(log)
			return log
		else:
			return _("Error code") + ": %s" % task.returncode

class FailedPostcondition(Condition):
	def __init__(self, exception):
		self.exception = exception
	def getErrorMessage(self, task):
		if isinstance(self.exception, int):
			if hasattr(task, 'log'):
				log = ''.join(task.log).strip()
				log = log.split('\n')[-4:]
				log = '\n'.join(log)
				return log
			else:
				return _("Error code") + " %s" % self.exception
		return str(self.exception)
	def check(self, task):
		return (self.exception is None) or (self.exception == 0)

#class HDDInitJob(Job):
#	def __init__(self, device):
#		Job.__init__(self, _("Initialize Harddisk"))
#		self.device = device
#		self.fromDescription(self.createDescription())
#
#	def fromDescription(self, description):
#		self.device = description["device"]
#		self.addTask(CreatePartitionTask(self.device))
#		self.addTask(CreateFilesystemTask(self.device))
#		self.addTask(FilesystemMountTask(self.device))
#
#	def createDescription(self):
#		return {"device": self.device}

job_manager = JobManager()
