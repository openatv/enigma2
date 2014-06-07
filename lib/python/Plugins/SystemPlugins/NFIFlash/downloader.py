# -*- coding: utf-8 -*-
from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskView import JobView
from Components.About import about
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.Label import Label
from Components.FileList import FileList
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.ScrollLabel import ScrollLabel
from Components.Harddisk import harddiskmanager
from Components.Task import Task, Job, job_manager, Condition
from Tools.Directories import fileExists, isMount, resolveFilename, SCOPE_HDD, SCOPE_MEDIA
from Tools.HardwareInfo import HardwareInfo
from Tools.Downloader import downloadWithProgress
from enigma import eConsoleAppContainer, gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP, eTimer
from os import system, path, access, stat, remove, W_OK, R_OK
from twisted.web import client
from twisted.internet import reactor, defer
from twisted.python import failure
import re

class ImageDownloadJob(Job):
	def __init__(self, url, filename, device=None, mountpoint="/"):
		Job.__init__(self, _("Download .NFI-files for USB-flasher"))
		if device:
			if isMount(mountpoint):
				UmountTask(self, mountpoint)
			MountTask(self, device, mountpoint)
		ImageDownloadTask(self, url, mountpoint+filename)
		ImageDownloadTask(self, url[:-4]+".nfo", mountpoint+filename[:-4]+".nfo")
		#if device:
			#UmountTask(self, mountpoint)

	def retry(self):
		self.tasks[0].args += self.tasks[0].retryargs
		Job.retry(self)

class MountTask(Task):
	def __init__(self, job, device, mountpoint):
		Task.__init__(self, job, ("mount"))
		self.setTool("mount")
		options = "rw,sync"
		self.mountpoint = mountpoint
		self.args += [ device, mountpoint, "-o"+options ]
		self.weighting = 1

	def processOutput(self, data):
		print "[MountTask] output:", data

class UmountTask(Task):
	def __init__(self, job, mountpoint):
		Task.__init__(self, job, ("mount"))
		self.setTool("umount")
		self.args += [mountpoint]
		self.weighting = 1

class DownloaderPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return self.error_message

class ImageDownloadTask(Task):
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
		self.callback = callback
		self.download = downloadWithProgress(self.url,self.path)
		self.download.addProgress(self.download_progress)
		self.download.start().addCallback(self.download_finished).addErrback(self.download_failed)
		print "[ImageDownloadTask] downloading", self.url, "to", self.path

	def abort(self):
		print "[ImageDownloadTask] aborting", self.url
		if self.download:
			self.download.stop()
		self.aborted = True

	def download_progress(self, recvbytes, totalbytes):
		#print "[update_progress] recvbytes=%d, totalbytes=%d" % (recvbytes, totalbytes)
		if ( recvbytes - self.last_recvbytes  ) > 10000: # anti-flicker
			self.progress = int(100*(float(recvbytes)/float(totalbytes)))
			self.name = _("Downloading") + ' ' + "%d of %d kBytes" % (recvbytes/1024, totalbytes/1024)
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

class StickWizardJob(Job):
	def __init__(self, path):
		Job.__init__(self, _("USB stick wizard"))
		self.path = path
		self.device = path
		while self.device[-1:] == "/" or self.device[-1:].isdigit():
			self.device = self.device[:-1]

		box = HardwareInfo().get_device_name()
		url = "http://www.dreamboxupdate.com/download/opendreambox/dreambox-nfiflasher-%s.tar.bz2" % box
		self.downloadfilename = "/tmp/dreambox-nfiflasher-%s.tar.bz2" % box
		self.imagefilename = "/tmp/nfiflash_%s.img" % box
		#UmountTask(self, device)
		PartitionTask(self)
		ImageDownloadTask(self, url, self.downloadfilename)
		UnpackTask(self)
		CopyTask(self)

class PartitionTaskPostcondition(Condition):
	def check(self, task):
		return task.returncode == 0

	def getErrorMessage(self, task):
		return {
			task.ERROR_BLKRRPART: ("Device or resource busy"),
			task.ERROR_UNKNOWN: (task.errormsg)
		}[task.error]

class PartitionTask(Task):
	ERROR_UNKNOWN, ERROR_BLKRRPART = range(2)
	def __init__(self, job):
		Task.__init__(self, job, ("partitioning"))
		self.postconditions.append(PartitionTaskPostcondition())
		self.job = job
		self.setTool("sfdisk")
		self.args += [self.job.device]
		self.weighting = 10
		self.initial_input = "0 - 0x6 *\n;\n;\n;\ny"
		self.errormsg = ""

	def run(self, callback):
		Task.run(self, callback)

	def processOutput(self, data):
		print "[PartitionTask] output:", data
		if data.startswith("BLKRRPART:"):
			self.error = self.ERROR_BLKRRPART
		else:
			self.error = self.ERROR_UNKNOWN
			self.errormsg = data

class UnpackTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, ("Unpacking USB flasher image..."))
		self.job = job
		self.setTool("tar")
		self.args += ["-xjvf", self.job.downloadfilename]
		self.weighting = 80
		self.end = 80
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.progress_increment)

	def run(self, callback):
		Task.run(self, callback)
		self.delayTimer.start(950, False)

	def progress_increment(self):
		self.progress += 1

	def processOutput(self, data):
		print "[UnpackTask] output: \'%s\'" % data
		self.job.imagefilename = data

	def afterRun(self):
		self.delayTimer.callback.remove(self.progress_increment)

class CopyTask(Task):
	def __init__(self, job):
		Task.__init__(self, job, ("Copying USB flasher boot image to stick..."))
		self.job = job
		self.setTool("dd")
		self.args += ["if=%s" % self.job.imagefilename, "of=%s1" % self.job.device]
		self.weighting = 20
		self.end = 20
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.progress_increment)

	def run(self, callback):
		Task.run(self, callback)
		self.delayTimer.start(100, False)

	def progress_increment(self):
		self.progress += 1

	def processOutput(self, data):
		print "[CopyTask] output:", data

	def afterRun(self):
		self.delayTimer.callback.remove(self.progress_increment)

class NFOViewer(Screen):
	skin = """
		<screen name="NFOViewer" position="center,center" size="610,410" title="Changelog" >
			<widget name="changelog" position="10,10" size="590,380" font="Regular;16" />
		</screen>"""

	def __init__(self, session, nfo):
		Screen.__init__(self, session)
		self["changelog"] = ScrollLabel(nfo)

		self["ViewerActions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"green": self.exit,
				"red": self.exit,
				"ok": self.exit,
				"cancel": self.exit,
				"down": self.pageDown,
				"up": self.pageUp
			})
	def pageUp(self):
		self["changelog"].pageUp()

	def pageDown(self):
		self["changelog"].pageDown()

	def exit(self):
		self.close(False)

class feedDownloader:
	def __init__(self, feed_base, box, OE_vers):
		print "[feedDownloader::init] feed_base=%s, box=%s" % (feed_base, box)
		self.feed_base = feed_base
		self.OE_vers = OE_vers
		self.box = box

	def getList(self, callback, errback):
		self.urlbase = "%s/%s/%s/images/" % (self.feed_base, self.OE_vers, self.box)
		print "[getList]", self.urlbase
		self.callback = callback
		self.errback = errback
		client.getPage(self.urlbase).addCallback(self.feed_finished).addErrback(self.feed_failed)

	def feed_failed(self, failure_instance):
		print "[feed_failed]", str(failure_instance)
		self.errback(failure_instance.getErrorMessage())

	def feed_finished(self, feedhtml):
		print "[feed_finished]"
		fileresultmask = re.compile("<a class=[\'\"]nfi[\'\"] href=[\'\"](?P<url>.*?)[\'\"]>(?P<name>.*?.nfi)</a>", re.DOTALL)
		searchresults = fileresultmask.finditer(feedhtml)
		fileresultlist = []
		if searchresults:
			for x in searchresults:
				url = x.group("url")
				if url[0:7] != "http://":
					url = self.urlbase + x.group("url")
				name = x.group("name")
				entry = (name, url)
				fileresultlist.append(entry)
		self.callback(fileresultlist, self.OE_vers)

class DeviceBrowser(Screen, HelpableScreen):
	skin = """
		<screen name="DeviceBrowser" position="center,center" size="520,430" title="Please select target medium" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="message" render="Label" position="5,50" size="510,150" font="Regular;16" />
			<widget name="filelist" position="5,210" size="510,220" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, startdir, message="", showDirectories = True, showFiles = True, showMountpoints = True, matchingPattern = "", useServiceRef = False, inhibitDirs = False, inhibitMounts = False, isTop = False, enableWrapAround = False, additionalExtensions = None):
		Screen.__init__(self, session)

		HelpableScreen.__init__(self)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["message"] = StaticText(message)

		self.filelist = FileList(startdir, showDirectories = showDirectories, showFiles = showFiles, showMountpoints = showMountpoints, matchingPattern = matchingPattern, useServiceRef = useServiceRef, inhibitDirs = inhibitDirs, inhibitMounts = inhibitMounts, isTop = isTop, enableWrapAround = enableWrapAround, additionalExtensions = additionalExtensions)
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.use,
				"red": self.exit,
				"ok": self.ok,
				"cancel": self.exit
			})

		hotplugNotifier.append(self.hotplugCB)
		self.onShown.append(self.updateButton)
		self.onClose.append(self.removeHotplug)

	def hotplugCB(self, dev, action):
		print "[hotplugCB]", dev, action
		self.updateButton()

	def updateButton(self):

		if self["filelist"].getFilename() or self["filelist"].getCurrentDirectory():
			self["key_green"].text = _("Use")
		else:
			self["key_green"].text = ""

	def removeHotplug(self):
		print "[removeHotplug]"
		hotplugNotifier.remove(self.hotplugCB)

	def ok(self):
		if self.filelist.canDescent():
			if self["filelist"].showMountpoints == True and self["filelist"].showDirectories == False:
				self.use()
			else:
				self.filelist.descent()

	def use(self):
		print "[use]", self["filelist"].getCurrentDirectory(), self["filelist"].getFilename()
		if self["filelist"].getCurrentDirectory() is not None:
			if self.filelist.canDescent() and self["filelist"].getFilename() and len(self["filelist"].getFilename()) > len(self["filelist"].getCurrentDirectory()):
				self.filelist.descent()
			self.close(self["filelist"].getCurrentDirectory())
		elif self["filelist"].getFilename():
			self.close(self["filelist"].getFilename())

	def exit(self):
		self.close(False)

(ALLIMAGES, RELEASE, EXPERIMENTAL, STICK_WIZARD, START) = range(5)

class NFIDownload(Screen):
	skin = """
	<screen name="NFIDownload" position="center,center" size="610,410" title="NFIDownload" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#18188b" transparent="1" />
		<ePixmap pixmap="skin_default/border_menu_350.png" position="5,50" zPosition="1" size="350,300" transparent="1" alphatest="on" />
		<widget source="menu" render="Listbox" position="15,60" size="330,290" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (25, [
						MultiContentEntryText(pos = (2, 2), size = (330, 24), flags = RT_HALIGN_LEFT, text = 1), # index 0 is the MenuText,
					], True, "showOnDemand")
					},
				"fonts": [gFont("Regular", 22)],
				"itemHeight": 25
				}
			</convert>
		</widget>
		<widget source="menu" render="Listbox" position="360,50" size="240,300" scrollbarMode="showNever" selectionDisabled="1">
			<convert type="TemplatedMultiContent">
				{"templates":
					{"default": (300, [
						MultiContentEntryText(pos = (2, 2), size = (240, 300), flags = RT_HALIGN_CENTER|RT_VALIGN_CENTER|RT_WRAP, text = 2), # index 2 is the Description,
					], False, "showNever")
					},
				"fonts": [gFont("Regular", 22)],
				"itemHeight": 300
				}
			</convert>
		</widget>
		<widget source="status" render="Label" position="5,360" zPosition="10" size="600,50" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""

	def __init__(self, session, destdir=None):
		Screen.__init__(self, session)
		#self.skin_path = plugin_path
		#self.menu = args

		self.box = HardwareInfo().get_device_name()
		self.feed_base = "http://www.dreamboxupdate.com/opendreambox" #/1.5/%s/images/" % self.box
		self.usbmountpoint = resolveFilename(SCOPE_MEDIA)+"usb/"

		self.menulist = []

		self["menu"] = List(self.menulist)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()

		self["status"] = StaticText(_("Please wait... Loading list..."))

		self["shortcuts"] = ActionMap(["OkCancelActions", "ColorActions", "ShortcutActions", "DirectionActions"],
		{
			"ok": self.keyOk,
			"green": self.keyOk,
			"red": self.keyRed,
			"blue": self.keyBlue,
			"up": self.keyUp,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"down": self.keyDown,
			"cancel": self.close,
		}, -1)
		self.onShown.append(self.go)
		self.feedlists = [[],[],[]]
		self.branch = START
		self.container = eConsoleAppContainer()
		self.container.dataAvail.append(self.tool_avail)
		self.taskstring = ""
		self.image_idx = 0
		self.nfofilename = ""
		self.nfo = ""
		self.target_dir = None

	def tool_avail(self, string):
		print "[tool_avail]" + string
		self.taskstring += string

	def go(self):
		self.onShown.remove(self.go)
		self.umountCallback = self.getMD5
		self.umount()

	def getMD5(self):
		url = "http://www.dreamboxupdate.com/download/opendreambox/dreambox-nfiflasher-%s-md5sums" % self.box
		client.getPage(url).addCallback(self.md5sums_finished).addErrback(self.feed_failed)

	def md5sums_finished(self, data):
		print "[md5sums_finished]", data
		self.stickimage_md5 = data
		self.checkUSBStick()

	def keyRed(self):
		if self.branch == START:
			self.close()
		else:
			self.branch = START
			self["menu"].setList(self.menulist)
		#elif self.branch == ALLIMAGES or self.branch == STICK_WIZARD:

	def keyBlue(self):
		if self.nfo != "":
			self.session.open(NFOViewer, self.nfo)

	def keyOk(self):
		print "[keyOk]", self["menu"].getCurrent()
		current = self["menu"].getCurrent()
		if current:
			if self.branch == START:
				currentEntry = current[0]
				if currentEntry == RELEASE:
					self.image_idx = 0
					self.branch = RELEASE
					self.askDestination()
				elif currentEntry == EXPERIMENTAL:
					self.image_idx = 0
					self.branch = EXPERIMENTAL
					self.askDestination()
				elif currentEntry == ALLIMAGES:
					self.branch = ALLIMAGES
					self.listImages()
				elif currentEntry == STICK_WIZARD:
					self.askStartWizard()
			elif self.branch == ALLIMAGES:
				self.image_idx = self["menu"].getIndex()
				self.askDestination()
		self.updateButtons()

	def keyUp(self):
		self["menu"].selectPrevious()
		self.updateButtons()

	def keyDown(self):
		self["menu"].selectNext()
		self.updateButtons()

	def updateButtons(self):
		current = self["menu"].getCurrent()
		if current:
			if self.branch == START:
				self["key_red"].text = _("Close")
				currentEntry = current[0]
				if currentEntry in (RELEASE, EXPERIMENTAL):
					self.nfo_download(currentEntry, 0)
					self["key_green"].text = _("Download")
				else:
					self.nfofilename = ""
					self.nfo = ""
					self["key_blue"].text = ""
					self["key_green"].text = _("continue")

			elif self.branch == ALLIMAGES:
				self["key_red"].text = _("Back")
				self["key_green"].text = _("Download")
				self.nfo_download(ALLIMAGES, self["menu"].getIndex())

	def listImages(self):
		print "[listImages]"
		imagelist = []
		mask = re.compile("%s/(?P<OE_vers>1\.\d)/%s/images/(?P<branch>.*?)-%s_(?P<version>.*?).nfi" % (self.feed_base, self.box, self.box), re.DOTALL)
		for name, url in self.feedlists[ALLIMAGES]:
			result = mask.match(url)
			if result:
				if result.group("version").startswith("20"):
					version = ( result.group("version")[:4]+'-'+result.group("version")[4:6]+'-'+result.group("version")[6:8] )
				else:
					version = result.group("version")
				description = "\nOpendreambox %s\n%s image\n%s\n" % (result.group("OE_vers"), result.group("branch"), version)
				imagelist.append((url, name, _("Download %s from server" ) % description, None))
		self["menu"].setList(imagelist)

	def getUSBPartitions(self):
		allpartitions = [ (r.description, r.mountpoint) for r in harddiskmanager.getMountedPartitions(onlyhotplug = True)]
		print "[getUSBPartitions]", allpartitions
		usbpartition = []
		for x in allpartitions:
			print x, x[1] == '/', x[0].find("USB"), access(x[1], R_OK)
			if x[1] != '/' and x[0].find("USB") > -1:  # and access(x[1], R_OK) is True:
				usbpartition.append(x)
		return usbpartition

	def askDestination(self):
		usbpartition = self.getUSBPartitions()
		if len(usbpartition) == 1:
			self.target_dir = usbpartition[0][1]
			self.ackDestinationDevice(device_description=usbpartition[0][0])
		else:
			self.openDeviceBrowser()

	def openDeviceBrowser(self):
		self.session.openWithCallback(self.DeviceBrowserClosed, DeviceBrowser, None, showDirectories=True, showMountpoints=True, inhibitMounts=["/autofs/sr0/"])

	def DeviceBrowserClosed(self, path):
		print "[DeviceBrowserClosed]", str(path)
		self.target_dir = path
		if path:
			self.ackDestinationDevice()
		else:
			self.keyRed()

	def ackDestinationDevice(self, device_description=None):
		if device_description == None:
			dev = self.target_dir
		else:
			dev = device_description
		message = _("Do you want to download the image to %s ?") % (dev)
		choices = [(_("Yes"), self.ackedDestination), (_("List of storage devices"),self.openDeviceBrowser), (_("Cancel"),self.keyRed)]
		self.session.openWithCallback(self.ackDestination_query, ChoiceBox, title=message, list=choices)

	def ackDestination_query(self, choice):
		print "[ackDestination_query]", choice
		if isinstance(choice, tuple):
			choice[1]()
		else:
			self.keyRed()

	def ackedDestination(self):
		print "[ackedDestination]", self.branch, self.target_dir
		self.container.setCWD(resolveFilename(SCOPE_MEDIA)+"usb/")
		if self.target_dir[:8] == "/autofs/":
			self.target_dir = "/dev/" + self.target_dir[8:-1]

		if self.branch == STICK_WIZARD:
			job = StickWizardJob(self.target_dir)
			job.afterEvent = "close"
			job_manager.AddJob(job)
			job_manager.failed_jobs = []
			self.session.openWithCallback(self.StickWizardCB, JobView, job, afterEventChangeable = False)

		elif self.branch != STICK_WIZARD:
			url = self.feedlists[self.branch][self.image_idx][1]
			filename = self.feedlists[self.branch][self.image_idx][0]
			print "[getImage] start downloading %s to %s" % (url, filename)
			if self.target_dir.startswith("/dev/"):
				job = ImageDownloadJob(url, filename, self.target_dir, self.usbmountpoint)
			else:
				job = ImageDownloadJob(url, filename, None, self.target_dir)
			job.afterEvent = "close"
			job_manager.AddJob(job)
			job_manager.failed_jobs = []
			self.session.openWithCallback(self.ImageDownloadCB, JobView, job, afterEventChangeable = False)

	def StickWizardCB(self, ret=None):
		print "[StickWizardCB]", ret
#		print job_manager.active_jobs, job_manager.failed_jobs, job_manager.job_classes, job_manager.in_background, job_manager.active_job
		if len(job_manager.failed_jobs) == 0:
			self.session.open(MessageBox, _("The USB stick was prepared to be bootable.\nNow you can download an NFI image file!"), type = MessageBox.TYPE_INFO)
			if len(self.feedlists[ALLIMAGES]) == 0:
				self.getFeed()
			else:
				self.setMenu()
		else:
			self.umountCallback = self.checkUSBStick
			self.umount()

	def ImageDownloadCB(self, ret):
		print "[ImageDownloadCB]", ret
#		print job_manager.active_jobs, job_manager.failed_jobs, job_manager.job_classes, job_manager.in_background, job_manager.active_job
		if len(job_manager.failed_jobs) == 0:
			self.session.openWithCallback(self.askBackupCB, MessageBox, _("The wizard can backup your current settings. Do you want to do a backup now?"), MessageBox.TYPE_YESNO)
		else:
			self.umountCallback = self.keyRed
			self.umount()

	def askBackupCB(self, ret):
		if ret:
			from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen

			class USBBackupScreen(BackupScreen):
				def __init__(self, session, usbmountpoint):
					BackupScreen.__init__(self, session, runBackup = True)
					self.backuppath = usbmountpoint
					self.fullbackupfilename = self.backuppath + "/" + self.backupfile

			self.session.openWithCallback(self.showHint, USBBackupScreen, self.usbmountpoint)
		else:
			self.showHint()

	def showHint(self, ret=None):
		self.session.open(MessageBox, _("To update your receiver firmware, please follow these steps:\n1) Turn off your box with the rear power switch and make sure the bootable USB stick is plugged in.\n2) Turn mains back on and hold the DOWN button on the front panel pressed for 10 seconds.\n3) Wait for bootup and follow instructions of the wizard."), type = MessageBox.TYPE_INFO)
		self.umountCallback = self.keyRed
		self.umount()

	def getFeed(self):
		self.feedDownloader15 = feedDownloader(self.feed_base, self.box, OE_vers="1.5")
		self.feedDownloader16 = feedDownloader(self.feed_base, self.box, OE_vers="1.6")
		self.feedlists = [[],[],[]]
		self.feedDownloader15.getList(self.gotFeed, self.feed_failed)
		self.feedDownloader16.getList(self.gotFeed, self.feed_failed)

	def feed_failed(self, message=""):
		self["status"].text = _("Could not connect to receiver .NFI image feed server:") + "\n" + str(message) + "\n" + _("Please check your network settings!")

	def gotFeed(self, feedlist, OE_vers):
		print "[gotFeed]", OE_vers
		releaselist = []
		experimentallist = []

		for name, url in feedlist:
			if name.find("release") > -1:
				releaselist.append((name, url))
			if name.find("experimental") > -1:
				experimentallist.append((name, url))
			self.feedlists[ALLIMAGES].append((name, url))

		if OE_vers == "1.6":
			self.feedlists[RELEASE] = releaselist + self.feedlists[RELEASE]
			self.feedlists[EXPERIMENTAL] = experimentallist + self.feedlists[RELEASE]
		elif OE_vers == "1.5":
			self.feedlists[RELEASE] = self.feedlists[RELEASE] + releaselist
			self.feedlists[EXPERIMENTAL] = self.feedlists[EXPERIMENTAL] + experimentallist

		self.setMenu()

	def checkUSBStick(self):
		self.target_dir = None
		allpartitions = [ (r.description, r.mountpoint) for r in harddiskmanager.getMountedPartitions(onlyhotplug = True)]
		print "[checkUSBStick] found partitions:", allpartitions
		usbpartition = []
		for x in allpartitions:
			print x, x[1] == '/', x[0].find("USB"), access(x[1], R_OK)
			if x[1] != '/' and x[0].find("USB") > -1:  # and access(x[1], R_OK) is True:
				usbpartition.append(x)

		print usbpartition
		if len(usbpartition) == 1:
			self.target_dir = usbpartition[0][1]
			self.md5_passback = self.getFeed
			self.md5_failback = self.askStartWizard
			self.md5verify(self.stickimage_md5, self.target_dir)
		elif usbpartition == []:
			print "[NFIFlash] needs to create usb flasher stick first!"
			self.askStartWizard()
		else:
			self.askStartWizard()

	def askStartWizard(self):
		self.branch = STICK_WIZARD
		message = _("""This plugin creates a USB stick which can be used to update the firmware of your receiver without the need for a network or WLAN connection.
First, a USB stick needs to be prepared so that it becomes bootable.
In the next step, an NFI image file can be downloaded from the update server and saved on the USB stick.
If you already have a prepared bootable USB stick, please insert it now. Otherwise plug in a USB stick with a minimum size of 64 MB!""")
		self.session.openWithCallback(self.wizardDeviceBrowserClosed, DeviceBrowser, None, message, showDirectories=True, showMountpoints=True, inhibitMounts=["/","/autofs/sr0/","/autofs/sda1/","/media/hdd/","/media/net/",self.usbmountpoint,"/media/dvd/"])

	def wizardDeviceBrowserClosed(self, path):
		print "[wizardDeviceBrowserClosed]", path
		self.target_dir = path
		if path:
			self.md5_passback = self.getFeed
			self.md5_failback = self.wizardQuery
			self.md5verify(self.stickimage_md5, self.target_dir)
		else:
			self.close()

	def wizardQuery(self):
		print "[wizardQuery]"
		description = self.target_dir
		for name, dev in self.getUSBPartitions():
			if dev == self.target_dir:
				description = name
		message = _("You have chosen to create a new .NFI flasher bootable USB stick. This will repartition the USB stick and therefore all data on it will be erased.") + "\n"
		message += _("The following device was found:\n\n%s\n\nDo you want to write the USB flasher to this stick?") % description
		choices = [(_("Yes"), self.ackedDestination), (_("List of storage devices"),self.askStartWizard), (_("Cancel"),self.close)]
		self.session.openWithCallback(self.ackDestination_query, ChoiceBox, title=message, list=choices)

	def setMenu(self):
		self.menulist = []
		try:
			latest_release = "Release %s (Opendreambox 1.5)" % self.feedlists[RELEASE][0][0][-9:-4]
			self.menulist.append((RELEASE, _("Get latest release image"), _("Download %s from server" ) % latest_release, None))
		except IndexError:
			pass

		try:
			dat = self.feedlists[EXPERIMENTAL][0][0][-12:-4]
			latest_experimental = "Experimental %s-%s-%s (Opendreambox 1.6)" % (dat[:4], dat[4:6], dat[6:])
			self.menulist.append((EXPERIMENTAL, _("Get latest experimental image"), _("Download %s from server") % latest_experimental, None))
		except IndexError:
			pass

		self.menulist.append((ALLIMAGES, _("Select an image to be downloaded"), _("Select desired image from feed list" ), None))
		self.menulist.append((STICK_WIZARD, _("USB stick wizard"), _("Prepare another USB stick for image flashing" ), None))
		self["menu"].setList(self.menulist)
		self["status"].text = _("Currently installed image") + ": %s" % (about.getImageVersionString())
		self.branch = START
		self.updateButtons()

	def nfo_download(self, branch, idx):
		nfourl = (self.feedlists[branch][idx][1])[:-4]+".nfo"
		self.nfofilename = (self.feedlists[branch][idx][0])[:-4]+".nfo"
		print "[check_for_NFO]", nfourl
		client.getPage(nfourl).addCallback(self.nfo_finished).addErrback(self.nfo_failed)

	def nfo_failed(self, failure_instance):
		print "[nfo_failed] " + str(failure_instance)
		self["key_blue"].text = ""
		self.nfofilename = ""
		self.nfo = ""

	def nfo_finished(self,nfodata=""):
		print "[nfo_finished] " + str(nfodata)
		self["key_blue"].text = _("Changelog")
		self.nfo = nfodata

	def md5verify(self, md5, path):
		cmd = "md5sum -c -s"
		print "[verify_md5]", md5, path, cmd
		self.container.setCWD(path)
		self.container.appClosed.append(self.md5finished)
		self.container.execute(cmd)
		self.container.write(md5)
		self.container.dataSent.append(self.md5ready)

	def md5ready(self, retval):
		self.container.sendEOF()

	def md5finished(self, retval):
		print "[md5finished]", str(retval)
		self.container.appClosed.remove(self.md5finished)
		self.container.dataSent.remove(self.md5ready)
		if retval==0:
			print "check passed! calling", repr(self.md5_passback)
			self.md5_passback()
		else:
			print "check failed! calling", repr(self.md5_failback)
			self.md5_failback()

	def umount(self):
		cmd = "umount " + self.usbmountpoint
		print "[umount]", cmd
		self.container.setCWD('/')
		self.container.appClosed.append(self.umountFinished)
		self.container.execute(cmd)

	def umountFinished(self, retval):
		print "[umountFinished]", str(retval)
		self.container.appClosed.remove(self.umountFinished)
		self.umountCallback()

def main(session, **kwargs):
	session.open(NFIDownload,resolveFilename(SCOPE_HDD))

def filescan_open(list, session, **kwargs):
	dev = "/dev/" + (list[0].path).rsplit('/',1)[0][7:]
	print "mounting device " + dev + " to /media/usb..."
	usbmountpoint = resolveFilename(SCOPE_MEDIA)+"usb/"
	system("mount %s %s -o rw,sync" % (dev, usbmountpoint))
	session.open(NFIDownload,usbmountpoint)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(mimetypes = ["application/x-dream-image"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "NFI",
			description = (_("Download .NFI-files for USB-flasher")+"..."),
			openfnc = filescan_open, )
