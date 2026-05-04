from datetime import datetime
from glob import glob
from os import SEEK_END, remove, replace, rmdir, stat, walk
from os.path import basename, exists, getsize, isdir, join
from re import compile
from time import ctime, time
from enigma import eBackgroundFileEraser, eLabel, eTimer, fontRenderClass, gFont
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config, configfile
from Components.FileList import MultiFileSelectList
from Components.GUIComponent import GUIComponent
from Components.MenuList import MenuList
import Components.Task
from Components.VariableText import VariableText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from skin import getSkinFactor
from Tools.Directories import fileReadLines
from Tools.TextBoundary import getTextBoundarySize

MODULE_NAME = __name__.split(".")[-1]


CRASH_LOG_PATTERN = r"^.*-enigma\d?-crash\.log$"
DEBUG_LOG_PATTERN = r"^.*-enigma\d?-debug\.log$"


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
		self.trim_timer = eTimer()
		self.trash_timer = eTimer()

	def start(self):
		if self.trim_timer_job not in self.trim_timer.callback:
			self.trim_timer.callback.append(self.trim_timer_job)
		if self.trash_timer_job not in self.trash_timer.callback:
			self.trash_timer.callback.append(self.trash_timer_job)
		self.trim_timer.startLongTimer(0)
		self.trash_timer.startLongTimer(0)

	def stop(self):
		if self.trim_timer_job in self.trim_timer.callback:
			self.trim_timer.callback.remove(self.trim_timer_job)
		if self.trash_timer_job in self.trash_timer.callback:
			self.trash_timer.callback.remove(self.trash_timer_job)
		self.trim_timer.stop()
		self.trash_timer.stop()

	def trim_timer_job(self):
		print('[LogManager] Trim Poll Started')
		Components.Task.job_manager.AddJob(self.create_trim_job())

	def trash_timer_job(self):
		print('[LogManager] Trash Poll Started')
		self.job_trash()
		# Components.Task.job_manager.AddJob(self.createTrashJob())

	def create_trim_job(self):
		job = Components.Task.Job(_("LogManager"))
		task = Components.Task.PythonTask(job, _("Checking Logs..."))
		task.work = self.job_trim
		task.weighting = 1
		return job

	def create_trash_job(self):
		job = Components.Task.Job(_("LogManager"))
		task = Components.Task.PythonTask(job, _("Checking Logs..."))
		task.work = self.job_trash
		task.weighting = 1
		return job

	def openFiles(self, ctimeLimit, allowedBytes):
		ctimeLimit = ctimeLimit
		allowedBytes = allowedBytes

	def job_trim(self):
		filename = ""
		limit = config.crash.debugloglimit.value * 1024 * 1024
		for filename in glob(config.crash.debug_path.value + '*.log'):
			try:
				size = getsize(filename)
				if size <= limit:
					continue

				with open(filename, 'rb') as fh:
					fh.seek(0, SEEK_END)
					size = fh.tell()
					if size <= limit:
						continue
					fh.seek(-limit, SEEK_END)
					data = fh.read()

				nl = data.find(b'\n')
				if nl != -1:
					data = data[nl + 1:]
				tmp_filename = filename + '.tmp'

				with open(tmp_filename, 'wb') as out:
					out.write(data)
				replace(tmp_filename, filename)

			except OSError:
				pass
		self.trim_timer.startLongTimer(3600)  # once an hour

	def job_trash(self):
		ctime_limit = time() - (config.crash.daysloglimit.value * 3600 * 24)
		allowed_bytes = 1024 * 1024 * int(config.crash.sizeloglimit.value)

		mounts = fileReadLines("/proc/mounts", source=MODULE_NAME)
		matches = []
		print("[LogManager] probing folders")

		if (datetime.now().hour == 3) or (time() - config.crash.lastfulljobtrashtime.value > 3600 * 24):
			# full JobTrash (in all potential log file dirs) between 03:00 and 04:00 AM / every 24h
			config.crash.lastfulljobtrashtime.setValue(int(time()))
			config.crash.lastfulljobtrashtime.save()
			configfile.save()
			for mount in mounts:
				if isdir(join(mount, 'logs')):
					matches.append(join(mount, 'logs'))
			matches.append('/home/root/logs')
		else:
			# small JobTrash (in selected log file dir only) twice a day
			matches.append(config.crash.debug_path.value)

		print("[LogManager] found following log's: %s" % matches)
		if matches:
			for logsfolder in matches:
				print("[LogManager] looking in: %s" % logsfolder)
				logssize = get_size(logsfolder)
				bytes_to_remove = logssize - allowed_bytes
				candidates = []
				size = 0
				for root, dirs, files in walk(logsfolder, topdown=False):
					for name in files:
						try:
							fn = join(root, name)
							st = stat(fn)
							# print "Logname: %s" % fn
							# print "Last created: %s" % ctime(st.st_ctime)
							# print "Last modified: %s" % ctime(st.st_mtime)
							if st.st_mtime < ctime_limit:
								print("[LogManager] %s: Too old: %s" % (str(fn), ctime(st.st_mtime)))
								eBackgroundFileEraser.getInstance().erase(fn)
								bytes_to_remove -= st.st_size
							else:
								candidates.append((st.st_mtime, fn, st.st_size))
								size += st.st_size
						except Exception as e:
							print("[LogManager] Failed to stat %s:%s" % (name, str(e)))
					# Remove empty directories if possible
					for name in dirs:
						try:
							rmdir(join(root, name))
						except OSError:
							pass
					candidates.sort()
					# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
					for st_ctime, fn, st_size in candidates:
						print("[LogManager] %s: bytesToRemove %s" % (str(logsfolder), bytes_to_remove))
						if bytes_to_remove < 0:
							break
						eBackgroundFileEraser.getInstance().erase(fn)
						bytes_to_remove -= st_size
						size -= st_size
		now = datetime.now()
		seconds_since_0330am = (now - now.replace(hour=3, minute=30, second=0)).total_seconds()
		if (seconds_since_0330am <= 0):
			seconds_since_0330am += 86400
		if (seconds_since_0330am > 43200):
			self.trash_timer.startLongTimer(int(86400 - seconds_since_0330am))  # at 03:30 AM
		else:
			self.trash_timer.startLongTimer(43200)  # twice a day


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
		self.selected_files = config.logmanager.sentfiles.value
		self.default_dir = config.crash.debug_path.value
		self.matching_pattern = CRASH_LOG_PATTERN
		self.filelist = MultiFileSelectList(self.selected_files, self.default_dir, showDirectories=False, matchingPattern=self.matching_pattern)
		self["list"] = self.filelist
		self["LogsSize"] = self.logsinfo = LogInfo(self.default_dir, LogInfo.USED, update=False)
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
		self.setTitle(self.default_dir)

	def up(self):
		self["list"].up()

	def down(self):
		self["list"].down()

	def left(self):
		self["list"].pageUp()

	def right(self):
		self["list"].pageDown()

	def saveSelection(self):
		self.selected_files = self["list"].getSelectedList()
		config.logmanager.sentfiles.setValue(self.selected_files)
		config.logmanager.sentfiles.save()
		configfile.save()

	def exit(self):
		self.close(None)

	def changeSelectionState(self):
		try:
			self.sel = self["list"].getCurrent()[0]
		except Exception:
			self.sel = None
		if self.sel:
			self["list"].changeSelectionState()
			self.selected_files = self["list"].getSelectedList()

	def changelogtype(self):
		self["LogsSize"].update(config.crash.debug_path.value)
		if self.logtype == 'crashlogs':
			self["key_red"].setText(_("Crash Logs"))
			self.logtype = 'debuglogs'
			self.matching_pattern = DEBUG_LOG_PATTERN
		else:
			self["key_red"].setText(_("Debug Logs"))
			self.logtype = 'crashlogs'
			self.matching_pattern = CRASH_LOG_PATTERN
		self["list"].matchingPattern = compile(self.matching_pattern)
		self["list"].changeDir(self.default_dir)

	def showLog(self):
		try:
			path = self["list"].getPath()
			if path:
				self.session.open(LogManagerViewLog, path)
		except Exception:
			pass

	def deletelog(self):
		try:
			self.sel = self["list"].getCurrent()[0]
		except Exception:
			self.sel = None
		self.selected_files = self["list"].getSelectedList()
		if self.selected_files:
			message = _("Do you want to delete all selected files:\n(choose 'No' to only delete the currently selected file.)")
			self.session.openWithCallback(self.doDelete1, MessageBox, message, MessageBox.TYPE_YESNO, windowTitle=_("Delete Confirmation"))
		elif self.sel:
			message = _("Are you sure you want to delete this log:\n") + str(self.sel[0])
			self.session.openWithCallback(self.doDelete3, MessageBox, message, MessageBox.TYPE_YESNO, windowTitle=_("Delete Confirmation"))
		else:
			self.session.open(MessageBox, _("You have selected no logs to delete."), MessageBox.TYPE_INFO, timeout=10)

	def doDelete1(self, answer):
		self.selected_files = self["list"].getSelectedList()
		self.selected_files = ",".join(self.selected_files).replace(",", " ")
		self.sel = self["list"].getCurrent()[0]
		if self.sel is not None:
			if answer is True:
				message = _("Are you sure you want to delete all selected logs:\n") + self.selected_files
				self.session.openWithCallback(self.doDelete2, MessageBox, message, MessageBox.TYPE_YESNO, windowTitle=_("Delete Confirmation"))
			else:
				message = _("Are you sure you want to delete this log:\n") + str(self.sel[0])
				self.session.openWithCallback(self.doDelete3, MessageBox, message, MessageBox.TYPE_YESNO, windowTitle=_("Delete Confirmation"))

	def doDelete2(self, answer):
		if answer is True:
			self.selected_files = self["list"].getSelectedList()
			self["list"].instance.moveSelectionTo(0)
			for f in self.selected_files:
				remove(f)
			config.logmanager.sentfiles.setValue("")
			config.logmanager.sentfiles.save()
			configfile.save()
			self["list"].changeDir(self.default_dir)

	def doDelete3(self, answer):
		if answer is True:
			path = self["list"].getPath()
			if exists(path):
				remove(path)
			self["list"].changeDir(self.default_dir)
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
		fontwidth = getTextBoundarySize(self.instance, font, self["list"].instance.size(), " ").width()
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
			except Exception:
				# occurs when f_blocks is 0 or a similar error
				self.setText("-?-")

	GUI_WIDGET = eLabel
