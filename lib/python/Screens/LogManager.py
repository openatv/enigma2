from datetime import datetime
from glob import glob
from re import compile
from os import remove, walk, stat, rmdir
from os.path import exists, join, getsize, isdir, basename
from time import time, ctime
from enigma import eTimer, eBackgroundFileEraser, eLabel, gFont, fontRenderClass

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config, configfile
from Components.FileList import FileList, MultiFileSelectList
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.MenuList import MenuList
import Components.Task
from Components.VariableText import VariableText
from Screens.MessageBox import MessageBox
from skin import getSkinFactor
from Tools.TextBoundary import getTextBoundarySize
from Tools.Directories import fileReadLines

MODULE_NAME = __name__.split(".")[-1]


CRASH_LOG_PATTERN = "^.*-enigma\d?-crash\.log$"
DEBUG_LOG_PATTERN = "^.*-enigma\d?-debug\.log$"


def get_size(start_path=None):
	total_size = 0
	if start_path:
		for dirpath, dirnames, filenames in walk(start_path):
			for f in filenames:
				fp = join(dirpath, f)
				total_size += getsize(fp)
		return total_size
	return 0


def AutoLogManager(session=None, **kwargs):
	global debuglogcheckpoller
	debuglogcheckpoller = LogManagerPoller()
	debuglogcheckpoller.start()


class LogManagerPoller:
	"""Automatically Poll LogManager"""

	def __init__(self):
		# Init Timer
		self.TrimTimer = eTimer()
		self.TrashTimer = eTimer()

	def start(self):
		if self.TrimTimerJob not in self.TrimTimer.callback:
			self.TrimTimer.callback.append(self.TrimTimerJob)
		if self.TrashTimerJob not in self.TrashTimer.callback:
			self.TrashTimer.callback.append(self.TrashTimerJob)
		self.TrimTimer.startLongTimer(0)
		self.TrashTimer.startLongTimer(0)

	def stop(self):
		if self.TrimTimerJob in self.TrimTimer.callback:
			self.TrimTimer.callback.remove(self.TrimTimerJob)
		if self.TrashTimerJob in self.TrashTimer.callback:
			self.TrashTimer.callback.remove(self.TrashTimerJob)
		self.TrimTimer.stop()
		self.TrashTimer.stop()

	def TrimTimerJob(self):
		print('[LogManager] Trim Poll Started')
		Components.Task.job_manager.AddJob(self.createTrimJob())

	def TrashTimerJob(self):
		print('[LogManager] Trash Poll Started')
		self.JobTrash()
		# Components.Task.job_manager.AddJob(self.createTrashJob())

	def createTrimJob(self):
		job = Components.Task.Job(_("LogManager"))
		task = Components.Task.PythonTask(job, _("Checking Logs..."))
		task.work = self.JobTrim
		task.weighting = 1
		return job

	def createTrashJob(self):
		job = Components.Task.Job(_("LogManager"))
		task = Components.Task.PythonTask(job, _("Checking Logs..."))
		task.work = self.JobTrash
		task.weighting = 1
		return job

	def openFiles(self, ctimeLimit, allowedBytes):
		ctimeLimit = ctimeLimit
		allowedBytes = allowedBytes

	def JobTrim(self):
		filename = ""
		for filename in glob(config.crash.debug_path.value + '*.log'):
			try:
				if getsize(filename) > (config.crash.debugloglimit.value * 1024 * 1024):
					fh = open(filename, 'rb+')
					fh.seek(-(config.crash.debugloglimit.value * 1024 * 1024), 2)
					data = fh.read()
					fh.seek(0)  # rewind
					fh.write(data)
					fh.truncate()
					fh.close()
			except:
				pass
		self.TrimTimer.startLongTimer(3600)  # once an hour

	def JobTrash(self):
		ctimeLimit = time() - (config.crash.daysloglimit.value * 3600 * 24)
		allowedBytes = 1024 * 1024 * int(config.crash.sizeloglimit.value)

		mounts = fileReadLines("/proc/mounts", source=MODULE_NAME)
		matches = []
		print("[LogManager] probing folders")

		if (datetime.now().hour == 3) or (time() - config.crash.lastfulljobtrashtime.value > 3600 * 24):
			#full JobTrash (in all potential log file dirs) between 03:00 and 04:00 AM / every 24h
			config.crash.lastfulljobtrashtime.setValue(int(time()))
			config.crash.lastfulljobtrashtime.save()
			configfile.save()
			for mount in mounts:
				if isdir(join(mount, 'logs')):
					matches.append(join(mount, 'logs'))
			matches.append('/home/root/logs')
		else:
			#small JobTrash (in selected log file dir only) twice a day
			matches.append(config.crash.debug_path.value)

		print("[LogManager] found following log's: %s" % matches)
		if matches:
			for logsfolder in matches:
				print("[LogManager] looking in: %s" % logsfolder)
				logssize = get_size(logsfolder)
				bytesToRemove = logssize - allowedBytes
				candidates = []
				size = 0
				for root, dirs, files in walk(logsfolder, topdown=False):
					for name in files:
						try:
							fn = join(root, name)
							st = stat(fn)
							#print "Logname: %s" % fn
							#print "Last created: %s" % ctime(st.st_ctime)
							#print "Last modified: %s" % ctime(st.st_mtime)
							if st.st_mtime < ctimeLimit:
								print("[LogManager] %s: Too old: %s" % (str(fn), ctime(st.st_mtime)))
								eBackgroundFileEraser.getInstance().erase(fn)
								bytesToRemove -= st.st_size
							else:
								candidates.append((st.st_mtime, fn, st.st_size))
								size += st.st_size
						except Exception as e:
							print("[LogManager] Failed to stat %s:%s" % (name, str(e)))
					# Remove empty directories if possible
					for name in dirs:
						try:
							rmdir(join(root, name))
						except:
							pass
					candidates.sort()
					# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
					for st_ctime, fn, st_size in candidates:
						print("[LogManager] %s: bytesToRemove %s" % (str(logsfolder), bytesToRemove))
						if bytesToRemove < 0:
							break
						eBackgroundFileEraser.getInstance().erase(fn)
						bytesToRemove -= st_size
						size -= st_size
		now = datetime.now()
		seconds_since_0330am = (now - now.replace(hour=3, minute=30, second=0)).total_seconds()
		if (seconds_since_0330am <= 0):
			seconds_since_0330am += 86400
		if (seconds_since_0330am > 43200):
			self.TrashTimer.startLongTimer(int(86400 - seconds_since_0330am))  # at 03:30 AM
		else:
			self.TrashTimer.startLongTimer(43200)  # twice a day


class LogManager(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.logtype = 'crashlogs'

		self['myactions'] = ActionMap(['ColorActions', 'OkCancelActions', 'DirectionActions'],
			{
				'ok': self.changeSelectionState,
				'cancel': self.close,
				'red': self.changelogtype,
				'green': self.showLog,
				'yellow': self.deletelog,
				"left": self.left,
				"right": self.right,
				"down": self.down,
				"up": self.up
			}, -1)

		self["key_red"] = Button(_("Debug Logs"))
		self["key_green"] = Button(_("View"))
		self["key_yellow"] = Button(_("Delete"))
		self["key_blue"] = Button("")

		self.onChangedEntry = []
		self.sentsingle = ""
		self.selectedFiles = config.logmanager.sentfiles.value
		self.defaultDir = config.crash.debug_path.value
		self.matchingPattern = CRASH_LOG_PATTERN
		self.filelist = MultiFileSelectList(self.selectedFiles, self.defaultDir, showDirectories=False, matchingPattern=self.matchingPattern)
		self["list"] = self.filelist
		self["LogsSize"] = self.logsinfo = LogInfo(config.crash.debug_path.value, LogInfo.USED, update=False)
		self.onLayoutFinish.append(self.layoutFinished)
		if self.selectionChanged not in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		name = str(item[0][0]) if item else ""
		for cb in self.onChangedEntry:
			cb(name, "")

	def layoutFinished(self):
		self["LogsSize"].update(config.crash.debug_path.value)
		idx = 0
		self["list"].moveToIndex(idx)
		self.setTitle(self.defaultDir)

	def up(self):
		self["list"].up()

	def down(self):
		self["list"].down()

	def left(self):
		self["list"].pageUp()

	def right(self):
		self["list"].pageDown()

	def saveSelection(self):
		self.selectedFiles = self["list"].getSelectedList()
		config.logmanager.sentfiles.setValue(self.selectedFiles)
		config.logmanager.sentfiles.save()
		configfile.save()

	def exit(self):
		self.close(None)

	def changeSelectionState(self):
		try:
			self.sel = self["list"].getCurrent()[0]
		except:
			self.sel = None
		if self.sel:
			self["list"].changeSelectionState()
			self.selectedFiles = self["list"].getSelectedList()

	def changelogtype(self):
		self["LogsSize"].update(config.crash.debug_path.value)
		if self.logtype == 'crashlogs':
			self["key_red"].setText(_("Crash Logs"))
			self.logtype = 'debuglogs'
			self.matchingPattern = DEBUG_LOG_PATTERN
		else:
			self["key_red"].setText(_("Debug Logs"))
			self.logtype = 'crashlogs'
			self.matchingPattern = CRASH_LOG_PATTERN
		self["list"].matchingPattern = compile(self.matchingPattern)
		self["list"].changeDir(self.defaultDir)

	def showLog(self):
		try:
			path = self["list"].getPath()
			if path:
				self.session.open(LogManagerViewLog, path)
		except:
			pass

	def deletelog(self):
		try:
			self.sel = self["list"].getCurrent()[0]
		except:
			self.sel = None
		self.selectedFiles = self["list"].getSelectedList()
		if self.selectedFiles:
			message = _("Do you want to delete all selected files:\n(choose 'No' to only delete the currently selected file.)")
			ybox = self.session.openWithCallback(self.doDelete1, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Delete Confirmation"))
		elif self.sel:
			message = _("Are you sure you want to delete this log:\n") + str(self.sel[0])
			ybox = self.session.openWithCallback(self.doDelete3, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Delete Confirmation"))
		else:
			self.session.open(MessageBox, _("You have selected no logs to delete."), MessageBox.TYPE_INFO, timeout=10)

	def doDelete1(self, answer):
		self.selectedFiles = self["list"].getSelectedList()
		self.selectedFiles = ",".join(self.selectedFiles).replace(",", " ")
		self.sel = self["list"].getCurrent()[0]
		if self.sel is not None:
			if answer is True:
				message = _("Are you sure you want to delete all selected logs:\n") + self.selectedFiles
				ybox = self.session.openWithCallback(self.doDelete2, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Delete Confirmation"))
			else:
				message = _("Are you sure you want to delete this log:\n") + str(self.sel[0])
				ybox = self.session.openWithCallback(self.doDelete3, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Delete Confirmation"))

	def doDelete2(self, answer):
		if answer is True:
			self.selectedFiles = self["list"].getSelectedList()
			self["list"].instance.moveSelectionTo(0)
			for f in self.selectedFiles:
				remove(f)
			config.logmanager.sentfiles.setValue("")
			config.logmanager.sentfiles.save()
			configfile.save()
			self["list"].changeDir(self.defaultDir)

	def doDelete3(self, answer):
		if answer is True:
			path = self["list"].getPath()
			if exists(path):
				remove(path)
			self["list"].changeDir(self.defaultDir)
			self["LogsSize"].update(config.crash.debug_path.value)


class LogManagerViewLog(Screen):
	def __init__(self, session, selected):
		Screen.__init__(self, session)
		self.setTitle(basename(selected))
		self.logfile = selected
		self.log = []
		self["list"] = MenuList(self.log)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"up": self["list"].up,
			"down": self["list"].down,
			"right": self["list"].pageDown,
			"left": self["list"].pageUp,
			"moveUp": self["list"].goTop,
			"moveDown": self["list"].goBottom
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		sf = getSkinFactor()
		font = gFont("Console", int(16 * sf))
		if not int(fontRenderClass.getInstance().getLineHeight(font)):
			font = gFont("Regular", int(16 * sf))
		self["list"].instance.setFont(font)
		fontwidth = getTextBoundarySize(self.instance, font, self["list"].instance.size(), _(" ")).width()
		listwidth = int(self["list"].instance.size().width() / fontwidth)
		if exists(self.logfile):
			for line in open(self.logfile).readlines():
				line = line.replace('\t', ' ' * 9)
				if len(line) > listwidth:
					pos = 0
					offset = 0
					readyline = True
					while readyline:
						a = " " * offset + line[pos:pos + listwidth - offset]
						self.log.append(a)
						if len(line[pos + listwidth - offset:]):
							pos += listwidth - offset
							offset = 20
						else:
							readyline = False
				else:
					self.log.append(line)
		else:
			self.log = [_("file can not displayed - file not found")]
		self["list"].setList(self.log)


class LogInfo(VariableText, GUIComponent):
	FREE = 0
	USED = 1
	SIZE = 2

	def __init__(self, path, type, update=True):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.type = type
# 		self.path = config.crash.debug_path.value
		if update:
			self.update(path)

	def update(self, path):
		try:
			total_size = get_size(path)
		except OSError:
			return -1

		if self.type == self.USED:
			try:
				if total_size < 10000000:
					total_size = _("%d kB") % (total_size >> 10)
				elif total_size < 10000000000:
					total_size = _("%d MB") % (total_size >> 20)
				else:
					total_size = _("%d GB") % (total_size >> 30)
				self.setText(_("Space used:") + " " + total_size)
			except:
				# occurs when f_blocks is 0 or a similar error
				self.setText("-?-")

	GUI_WIDGET = eLabel
