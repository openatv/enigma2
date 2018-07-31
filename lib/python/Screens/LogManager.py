from Screens.Screen import Screen
from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.FileList import FileList
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel
from Components.config import config, configfile
from Components.FileList import MultiFileSelectList
from Screens.MessageBox import MessageBox
from os import path, remove, walk, stat, rmdir
from time import time, ctime
from datetime import datetime
from enigma import eTimer, eBackgroundFileEraser, eLabel, getDesktop, gFont, fontRenderClass
from Tools.TextBoundary import getTextBoundarySize
from glob import glob

import Components.Task

# Import smtplib for the actual sending function
import smtplib, base64

# Here are the email package modules we'll need
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate

_session = None

def get_size(start_path=None):
	total_size = 0
	if start_path:
		for dirpath, dirnames, filenames in walk(start_path):
			for f in filenames:
				fp = path.join(dirpath, f)
				total_size += path.getsize(fp)
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
		print '[LogManager] Trim Poll Started'
		Components.Task.job_manager.AddJob(self.createTrimJob())

	def TrashTimerJob(self):
		print '[LogManager] Trash Poll Started'
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
				if path.getsize(filename) > (config.crash.debugloglimit.value * 1024 * 1024):
					fh = open(filename, 'rb+')
					fh.seek(-(config.crash.debugloglimit.value * 1024 * 1024), 2)
					data = fh.read()
					fh.seek(0) # rewind
					fh.write(data)
					fh.truncate()
					fh.close()
			except:
				pass
		self.TrimTimer.startLongTimer(3600) #once an hour

	def JobTrash(self):
		ctimeLimit = time() - (config.crash.daysloglimit.value * 3600 * 24)
		allowedBytes = 1024*1024 * int(config.crash.sizeloglimit.value)

		mounts = []
		matches = []
		print "[LogManager] probing folders"
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			mounts.append(parts[1])
		f.close()

		if (datetime.now().hour == 3) or (time() - config.crash.lastfulljobtrashtime.value > 3600 * 24):
			#full JobTrash (in all potential log file dirs) between 03:00 and 04:00 AM / every 24h
			config.crash.lastfulljobtrashtime.setValue(int(time()))
			config.crash.lastfulljobtrashtime.save()
			configfile.save()
			for mount in mounts:
				if path.isdir(path.join(mount,'logs')):
					matches.append(path.join(mount,'logs'))
			matches.append('/home/root/logs')
		else:
			#small JobTrash (in selected log file dir only) twice a day
			matches.append(config.crash.debug_path.value)

		print "[LogManager] found following log's:", matches
		if len(matches):
			for logsfolder in matches:
				print "[LogManager] looking in:", logsfolder
				logssize = get_size(logsfolder)
				bytesToRemove = logssize - allowedBytes
				candidates = []
				size = 0
				for root, dirs, files in walk(logsfolder, topdown=False):
					for name in files:
						try:
							fn = path.join(root, name)
							st = stat(fn)
							#print "Logname: %s" % fn
							#print "Last created: %s" % ctime(st.st_ctime)
							#print "Last modified: %s" % ctime(st.st_mtime)
							if st.st_mtime < ctimeLimit:
								print "[LogManager] " + str(fn) + ": Too old:", ctime(st.st_mtime)
								eBackgroundFileEraser.getInstance().erase(fn)
								bytesToRemove -= st.st_size
							else:
								candidates.append((st.st_mtime, fn, st.st_size))
								size += st.st_size
						except Exception, e:
							print "[LogManager] Failed to stat %s:"% name, e
					# Remove empty directories if possible
					for name in dirs:
						try:
							rmdir(path.join(root, name))
						except:
							pass
					candidates.sort()
					# Now we have a list of ctime, candidates, size. Sorted by ctime (=deletion time)
					for st_ctime, fn, st_size in candidates:
						print "[LogManager] " + str(logsfolder) + ": bytesToRemove", bytesToRemove
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
			self.TrashTimer.startLongTimer(int(86400-seconds_since_0330am)) #at 03:30 AM
		else:
			self.TrashTimer.startLongTimer(43200) #twice a day

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
				'blue': self.sendlog,
				"left": self.left,
				"right": self.right,
				"down": self.down,
				"up": self.up
			}, -1)

		self["key_red"] = Button(_("Debug Logs"))
		self["key_green"] = Button(_("View"))
		self["key_yellow"] = Button(_("Delete"))
		self["key_blue"] = Button(_("Send"))

		self.onChangedEntry = [ ]
		self.sentsingle = ""
		self.selectedFiles = config.logmanager.sentfiles.value
		self.previouslySent = config.logmanager.sentfiles.value
		self.defaultDir = config.crash.debug_path.value
		self.matchingPattern = 'enigma2_crash_'
		self.filelist = MultiFileSelectList(self.selectedFiles, self.defaultDir, showDirectories = False, matchingPattern = self.matchingPattern )
		self["list"] = self.filelist
		self["LogsSize"] = self.logsinfo = LogInfo(config.crash.debug_path.value, LogInfo.USED, update=False)
		self.onLayoutFinish.append(self.layoutFinished)
		if not self.selectionChanged in self["list"].onSelectionChanged:
			self["list"].onSelectionChanged.append(self.selectionChanged)

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["list"].getCurrent()
		desc = ""
		if item:
			name = str(item[0][0])
		else:
			name = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def layoutFinished(self):
		self["LogsSize"].update(config.crash.debug_path.value)
		idx = 0
		self["list"].moveToIndex(idx)
		self.setWindowTitle()

	def setWindowTitle(self):
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
		self.previouslySent = self["list"].getSelectedList()
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
		import re
		if self.logtype == 'crashlogs':
			self["key_red"].setText(_("Crash Logs"))
			self.logtype = 'debuglogs'
			self.matchingPattern = 'Enigma2'
		else:
			self["key_red"].setText(_("Debug Logs"))
			self.logtype = 'crashlogs'
			self.matchingPattern = 'enigma2_crash_'
		self["list"].matchingPattern = re.compile(self.matchingPattern)
		self["list"].changeDir(self.defaultDir)

	def showLog(self):
		try:
			self.sel = self["list"].getCurrent()[0]
		except:
			self.sel = None
		if self.sel:
			self.session.open(LogManagerViewLog, self.sel[0])

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
			self.session.open(MessageBox, _("You have selected no logs to delete."), MessageBox.TYPE_INFO, timeout = 10)

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
			self.sel = self["list"].getCurrent()[0]
			self["list"].instance.moveSelectionTo(0)
			if path.exists(self.defaultDir + self.sel[0]):
				remove(self.defaultDir + self.sel[0])
			self["list"].changeDir(self.defaultDir)
			self["LogsSize"].update(config.crash.debug_path.value)

	def sendlog(self, addtionalinfo = None):
		try:
			self.sel = self["list"].getCurrent()[0]
		except:
			self.sel = None
		if self.sel:
			self.sel = str(self.sel[0])
			self.selectedFiles = self["list"].getSelectedList()
			self.resend = False
			for send in self.previouslySent:
				if send in self.selectedFiles:
					self.selectedFiles.remove(send)
				if send == (self.defaultDir + self.sel):
					self.resend = True
			if self.selectedFiles:
				message = _("Do you want to send all selected files:\n(choose 'No' to only send the currently selected file.)")
				ybox = self.session.openWithCallback(self.sendlog1, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Send Confirmation"))
			elif self.sel and not self.resend:
				self.sendallfiles = False
				message = _("Are you sure you want to send this log:\n") + self.sel
				ybox = self.session.openWithCallback(self.sendlog2, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Send Confirmation"))
			elif self.sel and self.resend:
				self.sendallfiles = False
				message = _("You have already sent this log, are you sure you want to resend this log:\n") + self.sel
				ybox = self.session.openWithCallback(self.sendlog2, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Send Confirmation"))
		else:
			self.session.open(MessageBox, _("You have selected no logs to send."), MessageBox.TYPE_INFO, timeout = 10)

	def sendlog1(self, answer):
		if answer:
			self.sendallfiles = True
			message = _("Do you want to add any additional information ?")
			ybox = self.session.openWithCallback(self.sendlog3, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Additional Info"))
		else:
			self.sendallfiles = False
			message = _("Are you sure you want to send this log:\n") + str(self.sel[0])
			ybox = self.session.openWithCallback(self.sendlog2, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Send Confirmation"))

	def sendlog2(self, answer):
		if answer:
			self.sendallfiles = False
			message = _("Do you want to add any additional information ?")
			ybox = self.session.openWithCallback(self.sendlog3, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Additional Info"))

	def sendlog3(self, answer):
		if answer:
			message = _("Do you want to attach a text file to explain the log ?\n(choose 'No' to type message using virtual keyboard.)")
			ybox = self.session.openWithCallback(self.sendlog4, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Attach a file"))
		else:
			self.doSendlog()

	def sendlog4(self, answer):
		if answer:
			self.session.openWithCallback(self.doSendlog, LogManagerFb)
		else:
			from Screens.VirtualKeyBoard import VirtualKeyBoard
			self.session.openWithCallback(self.doSendlog, VirtualKeyBoard, title = 'Additonal Info')

	def doSendlog(self, additonalinfo = None):
		ref = str(time())
		# Create the container (outer) email message.
		msg = MIMEMultipart()
		if config.logmanager.user.value != '' and config.logmanager.useremail.value != '':
			fromlogman = config.logmanager.user.value + '  <' + config.logmanager.useremail.value + '>'
			tocrashlogs = 'crashlogs@dummy.org'
			msg['From'] = fromlogman
			msg['To'] = tocrashlogs
			msg['Cc'] = fromlogman
			msg['Date'] = formatdate(localtime=True)
			msg['Subject'] = 'Ref: ' + ref
			if additonalinfo != "":
				msg.attach(MIMEText(additonalinfo, 'plain'))
			else:
				msg.attach(MIMEText(config.logmanager.additionalinfo.value, 'plain'))
			if self.sendallfiles:
				self.selectedFiles = self["list"].getSelectedList()
				for send in self.previouslySent:
					if send in self.selectedFiles:
						self.selectedFiles.remove(send)
				self.sel = ",".join(self.selectedFiles).replace(",", " ")
				self["list"].instance.moveSelectionTo(0)
				for f in self.selectedFiles:
					self.previouslySent.append(f)
					fp = open(f, 'rb')
					data = MIMEText(fp.read())
					fp.close()
					msg.attach(data)
					self.saveSelection()
					sentfiles = self.sel
			else:
				self.sel = self["list"].getCurrent()[0]
				self.sel = str(self.sel[0])
				sentfiles = self.sel
				fp = open((self.defaultDir + self.sel), 'rb')
				data = MIMEText(fp.read())
				fp.close()
				msg.attach(data)
				self.sentsingle = self.defaultDir + self.sel
				self.changeSelectionState()
				self.saveSelection()

			# Send the email via our own SMTP server.
			wos_user = 'crashlogs@dummy.org'
			wos_pwd = base64.b64decode('NDJJWnojMEpldUxX')

			try:
				print "connecting to server: mail.dummy.org"
				#socket.setdefaulttimeout(30)
				s = smtplib.SMTP("mail.dummy.org",26)
				s.login(wos_user, wos_pwd)
				if config.logmanager.usersendcopy.value:
					s.sendmail(fromlogman, [tocrashlogs, fromlogman], msg.as_string())
					s.quit()
					self.session.open(MessageBox, sentfiles + ' ' + _('has been sent to the SVN team team.\nplease quote') + ' ' + str(ref) + ' ' + _('when asking question about this log\n\nA copy has been sent to yourself.'), MessageBox.TYPE_INFO)
				else:
					s.sendmail(fromlogman, tocrashlogs, msg.as_string())
					s.quit()
					self.session.open(MessageBox, sentfiles + ' ' + _('has been sent to the SVN team team.\nplease quote') + ' ' + str(ref) + ' ' + _('when asking question about this log'), MessageBox.TYPE_INFO)
			except Exception,e:
				self.session.open(MessageBox, _("Error:\n%s" % e), MessageBox.TYPE_INFO, timeout = 10)
		else:
			self.session.open(MessageBox, _('You have not setup your user info in the setup screen\nPress MENU, and enter your info, then try again'), MessageBox.TYPE_INFO, timeout = 10)

	def myclose(self):
		self.close()

class LogManagerViewLog(Screen):
	def __init__(self, session, selected):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(selected)
		self.logfile = config.crash.debug_path.value + selected
		self.log=[]
		self["list"] = MenuList(self.log)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
		{
			"cancel": self.cancel,
			"ok": self.cancel,
			"up": self["list"].up,
			"down": self["list"].down,
			"right": self["list"].pageDown,
			"left": self["list"].pageUp,
			"moveUp": self.gotoFirstPage,
			"moveDown": self.gotoLastPage
		}, -2)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		screenwidth = getDesktop(0).size().width()
		if screenwidth and screenwidth < 1920:
			f = 1
		elif screenwidth and screenwidth < 3840:
			f = 1.5
		else:
			f = 3
		font = gFont("Console", int(16*f))
		if not int(fontRenderClass.getInstance().getLineHeight(font)):
			font = gFont("Regular", int(16*f))
		self["list"].instance.setFont(font)
		fontwidth = getTextBoundarySize(self.instance, font, self["list"].instance.size(), _(" ")).width()
		listwidth = int(self["list"].instance.size().width() / fontwidth) - 2
		if path.exists(self.logfile):
			for line in file(self.logfile ).readlines():
				line = line.replace('\t',' '*9)
				if len(line) > listwidth:
					pos = 0
					offset = 0
					readyline = True
					while readyline:
						a = " " * offset + line[pos:pos+listwidth-offset]
						self.log.append(a)
						if len(line[pos+listwidth-offset:]):
							pos += listwidth-offset
							offset = 19
						else:
							readyline = False
				else:
					self.log.append(line)
		else:
			self.log = [_("file can not displayed - file not found")]
		self["list"].setList(self.log)

	def gotoFirstPage(self):
		self["list"].moveToIndex(0)

	def gotoLastPage(self):
		self["list"].moveToIndex(len(self.log)-1)

	def cancel(self):
		self.close()

class LogManagerFb(Screen):
	def __init__(self, session, logpath=None):
		if logpath is None:
			if path.isdir(config.logmanager.path.value):
				logpath = config.logmanager.path.value
			else:
				logpath = "/"

		self.session = session
		Screen.__init__(self, session)

		self["list"] = FileList(logpath, matchingPattern = "^.*")
		self["red"] = Label(_("delete"))
		self["green"] = Label(_("move"))
		self["yellow"] = Label(_("copy"))
		self["blue"] = Label(_("rename"))


		self["actions"] = ActionMap(["ChannelSelectBaseActions","WizardActions", "DirectionActions", "MenuActions", "NumberActions", "ColorActions"],
			{
			 "ok": self.ok,
			 "back": self.exit,
			 "up": self.goUp,
			 "down": self.goDown,
			 "left": self.goLeft,
			 "right": self.goRight,
			 "0": self.doRefresh,
			 }, -1)
		self.onLayoutFinish.append(self.mainlist)

	def exit(self):
		config.logmanager.additionalinfo.setValue("")
		if self["list"].getCurrentDirectory():
			config.logmanager.path.setValue(self["list"].getCurrentDirectory())
			config.logmanager.path.save()
		self.close()

	def ok(self):
		if self.SOURCELIST.canDescent(): # isDir
			self.SOURCELIST.descent()
			if self.SOURCELIST.getCurrentDirectory(): #??? when is it none
				self.setTitle(self.SOURCELIST.getCurrentDirectory())
		else:
			self.onFileAction()

	def goLeft(self):
		self.SOURCELIST.pageUp()

	def goRight(self):
		self.SOURCELIST.pageDown()

	def goUp(self):
		self.SOURCELIST.up()

	def goDown(self):
		self.SOURCELIST.down()

	def doRefresh(self):
		self.SOURCELIST.refresh()

	def mainlist(self):
		self["list"].selectionEnabled(1)
		self.SOURCELIST = self["list"]
		self.setTitle(self.SOURCELIST.getCurrentDirectory())

	def onFileAction(self):
		config.logmanager.additionalinfo.setValue(file(self.SOURCELIST.getCurrentDirectory()+self.SOURCELIST.getFilename()).read())
		if self["list"].getCurrentDirectory():
			config.logmanager.path.setValue(self["list"].getCurrentDirectory())
			config.logmanager.path.save()
		self.close()

class LogInfo(VariableText, GUIComponent):
	FREE = 0
	USED = 1
	SIZE = 2

	def __init__(self, path, type, update = True):
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
					total_size = "%d kB" % (total_size >> 10)
				elif total_size < 10000000000:
					total_size = "%d MB" % (total_size >> 20)
				else:
					total_size = "%d GB" % (total_size >> 30)
				self.setText(_("Space used:") + " " + total_size)
			except:
				# occurs when f_blocks is 0 or a similar error
				self.setText("-?-")

	GUI_WIDGET = eLabel
