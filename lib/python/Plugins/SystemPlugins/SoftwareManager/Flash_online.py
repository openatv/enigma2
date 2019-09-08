from Components.config import config
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.Task import Task, Job, job_manager, Condition
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Components.ProgressBar import ProgressBar
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Components.Console import Console
from Tools.BoundFunction import boundFunction
from Tools.Multiboot import GetImagelist, GetCurrentImage, GetCurrentImageMode, GetCurrentKern, GetCurrentRoot, GetBoxName
from enigma import eTimer, fbClass
import os, urllib2, shutil, math, time, zipfile, shutil


from boxbranding import getImageDistro, getMachineBuild, getMachineBrand, getMachineName

feedserver = 'images.mynonpublic.com'
feedurl = 'http://%s/%s' %(feedserver, getImageDistro())
imagecat = [3.0,4.0,4.1,4.2,5.0,5.1,5.2,5.3,6.0,6.1,6.2,6.3]

def checkimagefiles(files):
	return len([x for x in files if 'kernel' in x and '.bin' in x or x in ('zImage', 'uImage', 'root_cfe_auto.bin', 'root_cfe_auto.jffs2', 'oe_kernel.bin', 'oe_rootfs.bin', 'e2jffs2.img', 'rootfs.tar.bz2', 'rootfs.ubi','rootfs.bin')]) >= 2

class FlashOnline(Screen):
	skin = """
	<screen name="SelectImage" position="center,center" size="550,400">
		<widget name="list" position="fill" scrollbarMode="showOnDemand"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.selection = 0
		self.imagesList = {}
		self.setIndex = 0
		self.expanded = []
		Screen.setTitle(self, _("Flash On the Fly"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["description"] = StaticText()
		self["list"] = ChoiceList(list=[ChoiceEntryComponent('',((_("Retrieving image list - Please wait...")), "Waiter"))])

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": boundFunction(self.close, None),
			"red": boundFunction(self.close, None),
			"green": self.keyOk,
			"yellow": self.keyDelete,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.getImagesList)
		self.delay.start(0, True)

	def getImagesList(self):

		def getImages(path, files):
			for file in [x for x in files if os.path.splitext(x)[1] == ".zip" and box in x]:
				try:
					if checkimagefiles([x.split(os.sep)[-1] for x in zipfile.ZipFile(file).namelist()]):
						imagetyp = _("Downloaded Images")
						if 'backup' in file.split(os.sep)[-1]:
							imagetyp = _("Fullbackup Images")
						if imagetyp not in self.imagesList:
							self.imagesList[imagetyp] = {}
						self.imagesList[imagetyp][file] = {'link': file, 'name': file.split(os.sep)[-1]}
				except:
					pass

		if not self.imagesList:
			box = GetBoxName()
			try:
				import socket
				socket.getaddrinfo(feedserver, None)

				for version in reversed(sorted(imagecat)):
					newversion = _("Image Version %s") %version
					the_page =""
					url = '%s/%s/index.php?open=%s' % (feedurl,version,box)
					try:
						req = urllib2.Request(url)
						response = urllib2.urlopen(req)
					except urllib2.URLError as e:
						print "URL ERROR: %s\n%s" % (e,url)
						continue

					try:
						the_page = response.read()
					except urllib2.HTTPError as e:
						print "HTTP download ERROR: %s" % e.code
						continue

					lines = the_page.split('\n')
					tt = len(box)
					countimage = []
					for line in lines:
						if line.find("<a href='%s/" % box) > -1:
							t = line.find("<a href='%s/" % box)
							if line[t+tt+10:t+tt+tt+39].endswith(".zip"):
								countimage.append(line[t+tt+10:t+tt+tt+39])
					if len(countimage) >= 1:
						self.imagesList[newversion] = {}
						for image in countimage:
							self.imagesList[newversion][image] = {}
							self.imagesList[newversion][image]["name"] = image
							self.imagesList[newversion][image]["link"] = '%s/%s/%s/%s' % (feedurl,version,box,image)

			except socket.error as e:
				print "FEEDSERVER ERROR: %s" %e

			for media in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
				if not(SystemInfo['HasMMC'] and "/mmc" in media) and os.path.isdir(media):
					getImages(media, [os.path.join(media, x) for x in os.listdir(media) if os.path.splitext(x)[1] == ".zip" and box in x])
					if "images" in os.listdir(media):
						media = os.path.join(media, "images")
						if os.path.isdir(media) and not os.path.islink(media) and not os.path.ismount(media):
							getImages(media, [os.path.join(media, x) for x in os.listdir(media) if os.path.splitext(x)[1] == ".zip" and box in x])
							for dir in [dir for dir in [os.path.join(media, dir) for dir in os.listdir(media)] if os.path.isdir(dir) and os.path.splitext(dir)[1] == ".unzipped"]:
								shutil.rmtree(dir)

		list = []
		for catagorie in reversed(sorted(self.imagesList.keys())):
			if catagorie in self.expanded:
				list.append(ChoiceEntryComponent('expanded',((str(catagorie)), "Expander")))
				for image in reversed(sorted(self.imagesList[catagorie].keys(), key=lambda x: x.split(os.sep)[-1])):
					list.append(ChoiceEntryComponent('verticalline',((str(self.imagesList[catagorie][image]['name'])), str(self.imagesList[catagorie][image]['link']))))
			else:
				for image in self.imagesList[catagorie].keys():
					list.append(ChoiceEntryComponent('expandable',((str(catagorie)), "Expander")))
					break
		if list:
			self["list"].setList(list)
			if self.setIndex:
				self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				if self["list"].l.getCurrentSelection()[0][1] == "Expander":
					self.setIndex -= 1
					if self.setIndex:
						self["list"].moveToIndex(self.setIndex if self.setIndex < len(list) else len(list) - 1)
				self.setIndex = 0
			self.selectionChanged()
		else:
			self.session.openWithCallback(self.close, MessageBox, _("Cannot find images - please try later"), type=MessageBox.TYPE_ERROR, timeout=3)


	def keyOk(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if currentSelected[0][1] == "Expander":
			if currentSelected[0][0] in self.expanded:
				self.expanded.remove(currentSelected[0][0])
			else:
				self.expanded.append(currentSelected[0][0])
			self.getImagesList()
		elif currentSelected[0][1] != "Waiter":
			self.session.openWithCallback(self.getImagesList, FlashImage, currentSelected[0][0], currentSelected[0][1])

	def keyDelete(self):
		currentSelected= self["list"].l.getCurrentSelection()[0][1]
		if not("://" in currentSelected or currentSelected in ["Expander", "Waiter"]):
			try:
				os.remove(currentSelected)
				currentSelected = ".".join([currentSelected[:-4], "unzipped"])
				if os.path.isdir(currentSelected):
					shutil.rmtree(currentSelected)
				self.setIndex = self["list"].getSelectedIndex()
				self.imagesList = {}
				self.getImagesList()
			except:
				self.session.open(MessageBox, _("Cannot delete downloaded image"), MessageBox.TYPE_ERROR, timeout=3)

	def selectionChanged(self):
		currentSelected = self["list"].l.getCurrentSelection()
		if "://" in currentSelected[0][1] or currentSelected[0][1] in ["Expander", "Waiter"]:
			self["key_yellow"].setText("")
		else:
			self["key_yellow"].setText(_("Delete image"))
		if currentSelected[0][1] == "Waiter":
			self["key_green"].setText("")
		else:
			if currentSelected[0][1] == "Expander":
				self["key_green"].setText(_("Collapse") if currentSelected[0][0] in self.expanded else _("Expand"))
				self["description"].setText("")
			else:
				self["key_green"].setText(_("Flash Image"))
				self["description"].setText(currentSelected[0][1])

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.selectionChanged()

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.selectionChanged()

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.selectionChanged()

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.selectionChanged()
		
class FlashImage(Screen):
	skin = """<screen position="center,center" size="640,150" flags="wfNoBorder" backgroundColor="#54242424">
		<widget name="header" position="5,10" size="e-10,50" font="Regular;40" backgroundColor="#54242424"/>
		<widget name="info" position="5,60" size="e-10,130" font="Regular;24" backgroundColor="#54242424"/>
		<widget name="progress" position="5,e-39" size="e-10,24" backgroundColor="#54242424"/>
	</screen>"""

	def __init__(self, session,  imagename, source):
		Screen.__init__(self, session)
		self.containerbackup = None
		self.containerofgwrite = None
		self.getImageList = None
		self.saveImageList = None
		self.downloader = None
		self.source = source
		self.imagename = imagename

		self["header"] = Label(_("Backup settings"))
		self["info"] = Label(_("Save settings and EPG data"))
		self["summary_header"] = StaticText(self["header"].getText())
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self["progress"].setValue(0)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"cancel": self.abort,
			"red": self.abort,
			"ok": self.ok,
			"green": self.ok,
		}, -1)

		self.delay = eTimer()
		self.delay.callback.append(self.confirmation)
		self.delay.start(0, True)
		self.hide()

	def confirmation(self):
		self.message = _("Do you want to flash image\n%s") % self.imagename
		if SystemInfo["canMultiBoot"]:
			self.getImageList = GetImagelist(self.getImagelistCallback)
		else:
			self.checkMedia(True)

	def getImagelistCallback(self, imagedict):
		self.saveImageList = imagedict
		self.getImageList = None
		choices = []
		currentimageslot = GetCurrentImage()
		for x in range(1, SystemInfo["canMultiBoot"][1] + 1):
			choices.append(((_("slot%s - %s (current image)") if x == currentimageslot else _("slot%s - %s")) % (x, imagedict[x]['imagename']), (x,True)))
		choices.append((_("No, do not flash an image"), False))
		self.session.openWithCallback(self.checkMedia, MessageBox, self.message, list=choices, default=currentimageslot, simple=True)

	def backupQuestionCB(self, retval = True):
		if retval:
			self.checkMedia('backup')
		else:
			self.checkMedia('no_backup')

	def checkMedia(self, retval):
		if retval:
			if not 'backup' in str(retval):
				if SystemInfo["canMultiBoot"]:
					self.multibootslot = retval[0]
				self.session.openWithCallback(self.backupQuestionCB, MessageBox, _('Backup Settings') + '?', default=True, timeout=10)
				return

			def findmedia(path):
				def avail(path):
					if not '/mmc' in path and os.path.isdir(path) and os.access(path, os.W_OK):
						try:
							statvfs = os.statvfs(path)
							return (statvfs.f_bavail * statvfs.f_frsize) / (1 << 20)
						except:
							pass

				def checkIfDevice(path, diskstats):
					st_dev = os.stat(path).st_dev
					return (os.major(st_dev), os.minor(st_dev)) in diskstats

				diskstats = [(int(x[0]), int(x[1])) for x in [x.split()[0:3] for x in open('/proc/diskstats').readlines()] if x[2].startswith("sd")]
				if os.path.isdir(path) and checkIfDevice(path, diskstats) and avail(path) > 500:
					return (path, True)
				mounts = []
				devices = []
				for path in ['/media/%s' % x for x in os.listdir('/media')] + (['/media/net/%s' % x for x in os.listdir('/media/net')] if os.path.isdir('/media/net') else []):
					if checkIfDevice(path, diskstats):
						devices.append((path, avail(path)))
					else:
						mounts.append((path, avail(path)))
				devices.sort(key=lambda x: x[1], reverse=True)
				mounts.sort(key=lambda x: x[1], reverse=True)
				return ((devices[0][1] > 500 and (devices[0][0], True)) if devices else mounts and mounts[0][1] > 500 and (mounts[0][0], False)) or (None, None)

			self.destination, isDevice = findmedia("/media/hdd" or "/media/usb")

			if self.destination:

				destination = os.path.join(self.destination, 'images')
				self.zippedimage = "://" in self.source and os.path.join(destination, self.imagename) or self.source
				self.unzippedimage = os.path.join(destination, '%s.unzipped' % self.imagename[:-4])

				try:
					if os.path.isfile(destination):
						os.remove(destination)
					if not os.path.isdir(destination):
						os.mkdir(destination)
					if isDevice or 'no_backup' == retval:
						self.startBackupsettings(retval)
					else:
						self.session.openWithCallback(self.startBackupsettings, MessageBox, _("Can only find a network drive to store the backup this means after the flash the autorestore will not work. Alternatively you can mount the network drive after the flash and perform a manufacturer reset to autorestore"), simple=True)
				except:
					self.session.openWithCallback(self.abort, MessageBox, _("Unable to create the required directories on the media (e.g. USB stick or Harddisk) - Please verify media and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
			else:
				self.session.openWithCallback(self.abort, MessageBox, _("Could not find suitable media - Please remove some downloaded images or insert a media (e.g. USB stick) with sufficient free space and try again!"), type=MessageBox.TYPE_ERROR, simple=True)
		else:
			self.abort()

	def startBackupsettings(self, retval):
		if retval:
			if 'backup' == retval or True == retval:
				from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen
				self.session.openWithCallback(self.flashPostAction,BackupScreen, runBackup = True)
			else:
				self.flashPostAction()
		else:
			self.abort()

	def flashPostAction(self, retval = True):
		if retval:
			self.recordcheck = False
			title =_("Please select what to do after flashing the image:\n(In addition, if it exists, a local script will be executed as well at /media/hdd/images/config/myrestore.sh)")
			choices = ((_("Upgrade (Backup, Flash & Restore All)"), "restoresettingsandallplugins"),
			(_("Clean (Just flash and start clean)"), "wizard"),
			(_("Backup, flash and restore settings and no plugins"), "restoresettingsnoplugin"),
			(_("Backup, flash and restore settings and selected plugins (ask user)"), "restoresettings"),
			(_("Do not flash image"), "abort"))
			self.session.openWithCallback(self.postFlashActionCallback, ChoiceBox,title=title,list=choices,selection=self.SelectPrevPostFlashAction())
		else:
			self.abort()

	def SelectPrevPostFlashAction(self):
		index = 0
		Settings = False
		AllPlugins = False
		noPlugins = False
		if os.path.exists('/media/hdd/images/config/settings'):
			Settings = True
		if os.path.exists('/media/hdd/images/config/plugins'):
			AllPlugins = True
		if os.path.exists('/media/hdd/images/config/noplugins'):
			noPlugins = True

		if Settings and noPlugins:
			index = 2
		elif Settings and not AllPlugins and not noPlugins:
			index = 3
		elif Settings and AllPlugins:
			index = 0
		else:
			index = 1
		return index

	def recordWarning(self, answer):
		if answer:
			self.postFlashActionCallback(self.answer)
		else:
			self.abort()

	def postFlashActionCallback(self, answer):
		restoreSettings   = False
		restoreAllPlugins = False
		restoreSettingsnoPlugin = False
		if answer is not None:
			if answer[1] != "abort" and not self.recordcheck:
				self.recordcheck = True
				rec = self.session.nav.RecordTimer.isRecording()
				next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
				if rec or (next_rec_time > 0 and (next_rec_time - time.time()) < 360):
					self.answer = answer
					self.session.openWithCallback(self.recordWarning, MessageBox, _("Recording(s) are in progress or coming up in few seconds!") + '\n' + _("Really reflash your %s %s and reboot now?") % (getMachineBrand(), getMachineName()), default=False)
					return
			if answer[1] == "restoresettings":
				restoreSettings   = True
			if answer[1] == "restoresettingsnoplugin":
				restoreSettings = True
				restoreSettingsnoPlugin = True
			if answer[1] == "restoresettingsandallplugins":
				restoreSettings   = True
				restoreAllPlugins = True
			if restoreSettings:
				self.SaveEPG()
			if answer[1] != "abort":
				if restoreSettings:
					try:
						if not os.path.exists('/media/hdd/images/config'):
							os.makedirs('/media/hdd/images/config')
						open('/media/hdd/images/config/settings','w').close()
					except:
						print "postFlashActionCallback: failed to create /media/hdd/images/config/settings"
				else:
					if os.path.exists('/media/hdd/images/config/settings'):
						os.unlink('/media/hdd/images/config/settings')
				if restoreAllPlugins:
					try:
						if not os.path.exists('/media/hdd/images/config'):
							os.makedirs('/media/hdd/images/config')
						open('/media/hdd/images/config/plugins','w').close()
					except:
						print "postFlashActionCallback: failed to create /media/hdd/images/config/plugins"
				else:
					if os.path.exists('/media/hdd/images/config/plugins'):
						os.unlink('/media/hdd/images/config/plugins')
				if restoreSettingsnoPlugin:
					try:
						if not os.path.exists('/media/hdd/images/config'):
							os.makedirs('/media/hdd/images/config')
						open('/media/hdd/images/config/noplugins','w').close()
					except:
						print "postFlashActionCallback: failed to create /media/hdd/images/config/noplugins"
				else:
					if os.path.exists('/media/hdd/images/config/noplugins'):
						os.unlink('/media/hdd/images/config/noplugins')
				if restoreSettings or restoreAllPlugins or restoreSettingsnoPlugin:
					if config.plugins.softwaremanager.restoremode.value is not None:
						try:
							if not os.path.exists('/media/hdd/images/config'):
								os.makedirs('/media/hdd/images/config')
							if config.plugins.softwaremanager.restoremode.value == "slow":
								if not os.path.exists('/media/hdd/images/config/slow'):
									open('/media/hdd/images/config/slow','w').close()
								if os.path.exists('/media/hdd/images/config/fast'):
									os.unlink('/media/hdd/images/config/fast')
								if os.path.exists('/media/hdd/images/config/turbo'):
									os.unlink('/media/hdd/images/config/turbo')
							elif config.plugins.softwaremanager.restoremode.value == "fast":
								if not os.path.exists('/media/hdd/images/config/fast'):
									open('/media/hdd/images/config/fast','w').close()
								if os.path.exists('/media/hdd/images/config/slow'):
									os.unlink('/media/hdd/images/config/slow')
								if os.path.exists('/media/hdd/images/config/turbo'):
									os.unlink('/media/hdd/images/config/turbo')
							elif config.plugins.softwaremanager.restoremode.value == "turbo":
								if not os.path.exists('/media/hdd/images/config/turbo'):
									open('/media/hdd/images/config/turbo','w').close()
								if os.path.exists('/media/hdd/images/config/slow'):
									os.unlink('/media/hdd/images/config/slow')
								if os.path.exists('/media/hdd/images/config/fast'):
									os.unlink('/media/hdd/images/config/fast')
						except:
							print "postFlashActionCallback: failed to create restore mode flagfile"
				self.startDownload()
			else:
				self.abort()
		else:
			self.abort()

	def SaveEPG(self):
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.save()

	def startDownload(self, reply=True):
		self.show()
		if reply:
			if "://" in self.source:
				from Tools.Downloader import downloadWithProgress
				self["header"].setText(_("Downloading Image"))
				self["info"].setText(self.imagename)
				self["summary_header"].setText(self["header"].getText())
				self.downloader = downloadWithProgress(self.source, self.zippedimage)
				self.downloader.addProgress(self.downloadProgress)
				self.downloader.addEnd(self.downloadEnd)
				self.downloader.addError(self.downloadError)
				self.downloader.start()
			else:
				self.unzip()
		else:
			self.abort()

	def downloadProgress(self, current, total):
		self["progress"].setValue(int(100 * current / total))

	def downloadError(self, reason, status):
		self.downloader.stop()
		self.session.openWithCallback(self.abort, MessageBox, _("Error during downloading image\n%s\n%s") % (self.imagename, reason), type=MessageBox.TYPE_ERROR, simple=True)

	def downloadEnd(self):
		self.downloader.stop()
		self.unzip()

	def unzip(self):
		self["header"].setText(_("Unzipping Image"))
		self["summary_header"].setText(self["header"].getText())
		self["info"].setText("%s\n%s"% (self.imagename, _("Please wait")))
		self["progress"].hide()
		self.delay.callback.remove(self.confirmation)
		self.delay.callback.append(self.doUnzip)
		self.delay.start(0, True)

	def doUnzip(self):
		try:
			zipfile.ZipFile(self.zippedimage, 'r').extractall(self.unzippedimage)
			self.flashimage()
		except:
			self.session.openWithCallback(self.abort, MessageBox, _("Error during unzipping image\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def flashimage(self):
		self["header"].setText(_("Flashing Image"))
		self["summary_header"].setText(self["header"].getText())
		def findimagefiles(path):
			for path, subdirs, files in os.walk(path):
				if not subdirs and files:
					return checkimagefiles(files) and path
		imagefiles = findimagefiles(self.unzippedimage)
		if imagefiles:
			self.getImageList = self.saveImageList
			self.MTDKERNEL = GetCurrentKern()
			self.MTDROOTFS = GetCurrentRoot()
			if SystemInfo["canMultiBoot"]:
				if "sd" in self.getImageList[self.multibootslot]['part']:
					self.MTDKERNEL = "%s%s" %(SystemInfo["canMultiBoot"][2], int(self.getImageList[self.multibootslot]['part'][3])-1)
					self.MTDROOTFS = "%s" %(self.getImageList[self.multibootslot]['part'])
			if SystemInfo["canMultiBoot"]:
				if getMachineBuild() in ("gbmv200","cc1","sf8008","ustym4kpro","beyonwizv2","viper4k"): # issue detect kernel device and rootfs on sda
					print "[FlashImage] detect Kernel:",self.MTDKERNEL
					print "[FlashImage] detect rootfs:",self.MTDROOTFS
					command = "/usr/bin/ofgwrite -r%s -k%s %s" % (self.MTDROOTFS, self.MTDKERNEL, imagefiles)
				else:
					command = "/usr/bin/ofgwrite -r -k -m%s %s" % (self.multibootslot, imagefiles)
			elif getMachineBuild() in ("u5pvr","u5","u51","u52","u53","u532","u533","u54","u56"): # issue detect kernel device
				print "[FlashImage] detect Kernel:",self.MTDKERNEL
				print "[FlashImage] detect rootfs:",self.MTDROOTFS
				command = "/usr/bin/ofgwrite -r%s -k%s %s" % (self.MTDROOTFS, self.MTDKERNEL, imagefiles)
			else:
				command = "/usr/bin/ofgwrite -r -k %s" % imagefiles
			self.containerofgwrite = Console()
			self.containerofgwrite.ePopen(command, self.FlashimageDone)
			fbClass.getInstance().lock()
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Image to install is invalid\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def FlashimageDone(self, data, retval, extra_args):
		fbClass.getInstance().unlock()
		self.containerofgwrite = None
		if retval == 0:
			self["header"].setText(_("Flashing image successful"))
			self["summary_header"].setText(self["header"].getText())
			self["info"].setText(_("%s\nPress ok to close") % self.imagename)
		else:
			self.session.openWithCallback(self.abort, MessageBox, _("Flashing image was not successful\n%s") % self.imagename, type=MessageBox.TYPE_ERROR, simple=True)

	def abort(self, reply=None):
		if self.getImageList:
			return 0
		if self.downloader:
			self.downloader.stop()
		self.close()

	def ok(self):
		fbClass.getInstance().unlock()
		if self["header"].text == _("Flashing image successful"):
			self.close()
		else:
			return 0
