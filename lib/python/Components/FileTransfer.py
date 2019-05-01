# -*- coding: utf-8 -*-
from Components.Task import Task, Job, job_manager, AbortedPostcondition, ReturncodePostcondition
from Tools.Directories import fileExists, shellquote
from Components.MovieList import MOVIE_EXTENSIONS
from enigma import eTimer
import os

ALL_MOVIE_EXTENSIONS = MOVIE_EXTENSIONS.union((".ts",))

class FileTransferJob(Job):
	def __init__(self, src_file, dst_file, src_isDir, do_copy, title):
		Job.__init__(self, title)
		FileTransferTask(self, src_file, dst_file, src_isDir, do_copy)

class FileTransferTask(Task):
	def __init__(self, job, src_file, dst_file, src_isDir, do_copy):
		Task.__init__(self, job, "")
		nice = "ionice -c 3"
		self.src_isDir = src_isDir
		self.src_file = src_file
		self.dst_isDir = False
		self.dst_file = dst_file + "/" + os.path.basename(src_file)
		src_file_append = ""
		if not src_isDir:
			root, ext = os.path.splitext(src_file)
			if ext in ALL_MOVIE_EXTENSIONS:
				src_file = root
				src_file_append = ".*"
		cmd = "mv"
		if do_copy:
			cmd = "cp -pr"
		cmdline = '%s %s %s%s %s' % (nice, cmd, shellquote(src_file), src_file_append, shellquote(dst_file))
		if self.dst_file.endswith("/"):
			self.dst_isDir = True
		self.setCmdline(cmdline)
		self.end = 100
		self.progressTimer = eTimer()
		self.progressTimer.callback.append(self.progressUpdate)

	def progressUpdate(self):
		if not fileExists(self.dst_file, 'r'):
			return
		if self.dst_isDir:
			dst_dir_size = self.dst_file
			if self.src_isDir and self.src_file.endswith("/"):
				mv_dir = self.src_file[:-1].rsplit("/", 1)
				if len(mv_dir) == 2:
					dst_dir_size = self.dst_file + mv_dir[1]
			dst_size = float(self.dirSize(dst_dir_size))
		else:
			dst_size = float(os.path.getsize(self.dst_file))
		progress = dst_size / self.src_size * 100.0
		self.setProgress(progress)
		self.progressTimer.start(self.updateTime, True)

	def prepare(self):
		if fileExists(self.src_file, 'r'):
			if self.src_isDir:
				self.src_size = float(self.dirSize(self.src_file))
			else:
				self.src_size = float(os.path.getsize(self.src_file))
			self.updateTime = max(1000, int(self.src_size * 0.000001 * 0.5)) # based on 20Mb/s transfer rate
			self.progressTimer.start(self.updateTime, True)

	def afterRun(self):
		self.progressTimer.stop()
		self.setProgress(100)

	def dirSize(self, folder):
		total_size = os.path.getsize(folder)
		for item in os.listdir(folder):
			itempath = os.path.join(folder, item)
			if os.path.isfile(itempath):
				total_size += os.path.getsize(itempath)
			elif os.path.isdir(itempath):
				total_size += self.dirSize(itempath)
		return total_size

	def finish(self, aborted=False):
		self.afterRun()
		not_met = []
		if aborted:
			from Tools import Notifications
			from Screens.MessageBox import MessageBox
			Notifications.AddNotification(MessageBox, _("File transfer was cancelled by user"), type=MessageBox.TYPE_INFO)
		else:
			for postcondition in self.postconditions:
				if not postcondition.check(self):
					not_met.append(postcondition)
		self.cleanup(not_met)
		self.callback(self, not_met)
