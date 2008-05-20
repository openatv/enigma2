# A Job consists of many "Tasks".
# A task is the run of an external tool, with proper methods for failure handling

from Tools.CList import CList

class Job:
	NOT_STARTED, IN_PROGRESS, FINISHED, FAILED = range(4)
	def __init__(self, name):
		self.tasks = [ ]
		self.workspace = "/tmp"
		self.current_task = 0
		self.callback = None
		self.name = name
		self.finished = False

		self.state_changed = CList()

		self.status = self.NOT_STARTED

	# description is a dict
	def fromDescription(self, description):
		pass

	def createDescription(self):
		return None

	def addTask(self, task):
		task.job = self
		self.tasks.append(task)

	def start(self, callback):
		assert self.callback is None
		self.callback = callback
		self.status = self.IN_PROGRESS
		self.state_changed()
		self.runNext()

	def runNext(self):
		if self.current_task == len(self.tasks):
			self.callback(self, [])
			self.status = self.FINISHED
			self.state_changed()
		else:
			self.tasks[self.current_task].run(self.taskCallback)
			self.state_changed()

	def taskCallback(self, res):
		if len(res):
			print ">>> Error:", res
			self.status = self.FAILED
			self.state_changed()
			self.callback(self, res)
		else:
			self.current_task += 1
			self.runNext()

class Task:
	def __init__(self, job, name):
		self.name = name
		self.immediate_preconditions = [ ]
		self.global_preconditions = [ ]
		self.postconditions = [ ]
		self.returncode = None
		self.initial_input = None
		self.job = None

		self.cmd = None
		self.args = [ ]
		job.addTask(self)

	def setCommandline(self, cmd, args):
		self.cmd = cmd
		self.args = args

	def setTool(self, tool):
		self.cmd = tool
		self.args = [tool]
		self.global_preconditions.append(ToolExistsPrecondition())
		self.postconditions.append(ReturncodePostcondition())

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

	def run(self, callback):
		failed_preconditions = self.checkPreconditions(True) + self.checkPreconditions(False)
		if len(failed_preconditions):
			callback(failed_preconditions)
			return
		self.prepare()

		self.callback = callback
		from enigma import eConsoleAppContainer
		self.container = eConsoleAppContainer()
		self.container.appClosed.get().append(self.processFinished)
		self.container.dataAvail.get().append(self.processOutput)

		assert self.cmd is not None
		assert len(self.args) >= 1

		print "execute:", self.container.execute(self.cmd, self.args), self.cmd, self.args
		if self.initial_input:
			self.writeInput(self.initial_input)

	def prepare(self):
		pass

	def cleanup(self, failed):
		pass

	def processOutput(self, data):
		pass

	def processFinished(self, returncode):
		self.returncode = returncode
		self.finish()

	def finish(self):
		self.afterRun()
		not_met = [ ]
		for postcondition in self.postconditions:
			if not postcondition.check(self):
				not_met.append(postcondition)

		self.callback(not_met)

	def afterRun(self):
		pass

	def writeInput(self, input):
		self.container.write(input)

class JobManager:
	def __init__(self):
		self.active_jobs = [ ]
		self.failed_jobs = [ ]
		self.job_classes = [ ]
		self.active_job = None

	def AddJob(self, job):
		self.active_jobs.append(job)
		self.kick()

	def kick(self):
		if self.active_job is None:
			if len(self.active_jobs):
				self.active_job = self.active_jobs.pop(0)
				self.active_job.start(self.jobDone)

	def jobDone(self, job, problems):
		print "job", job, "completed with", problems
		if problems:
			self.failed_jobs.append(self.active_job)

		self.active_job = None
		self.kick()

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
#		Task.__init__(self, _("Create Partition"))
#		self.device = device
#		self.setTool("/sbin/sfdisk")
#		self.args += ["-f", self.device + "disc"]
#		self.initial_input = "0,\n;\n;\n;\ny\n"
#		self.postconditions.append(PartitionExistsPostcondition(self.device))
#
#class CreateFilesystemTask(Task):
#	def __init__(self, device, partition = 1, largefile = True):
#		Task.__init__(self, _("Create Filesystem"))
#		self.setTool("/sbin/mkfs.ext")
#		if largefile:
#			self.args += ["-T", "largefile"]
#		self.args.append("-m0")
#		self.args.append(device + "part%d" % partition)
#
#class FilesystemMountTask(Task):
#	def __init__(self, device, partition = 1, filesystem = "ext3"):
#		Task.__init__(self, _("Mounting Filesystem"))
#		self.setTool("/bin/mount")
#		if filesystem is not None:
#			self.args += ["-t", filesystem]
#		self.args.append(device + "part%d" % partition)
#
#class DiskspacePrecondition:
#	def __init__(self, diskspace_required):
#		self.diskspace_required = diskspace_required
#
#	def check(self, task):
#		return getFreeDiskspace(task.workspace) >= self.diskspace_required
#
class ToolExistsPrecondition:
	def check(self, task):
		import os
		return os.access(task.cmd, os.X_OK)

class ReturncodePostcondition:
	def check(self, task):
		return task.returncode == 0

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
