# -*- coding: utf-8 -*-
from Components.MenuList import MenuList
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.Label import Label
from Components.FileList import FileList
from Components.MultiContent import MultiContentEntryText
from Tools.Directories import fileExists
from Tools.HardwareInfo import HardwareInfo
from enigma import eConsoleAppContainer, eListbox, gFont, eListboxPythonMultiContent, \
	RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP, eRect, eTimer
from os import system, remove
import re
import urllib
from Tools.Downloader import downloadWithProgress
from twisted.web import client
from twisted.internet import reactor, defer
from twisted.python import failure
from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier

class UserRequestedCancel(Exception):
	pass

class Feedlist(MenuList):
	def __init__(self, list=[], enableWrapAround = False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 16))
		self.l.setItemHeight(22)

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)

	def getNFIname(self):
		l = self.l.getCurrentSelection()
		return l and l[0][0]

	def getNFIurl(self):
		l = self.l.getCurrentSelection()
		return l and l[0][1]

	def getNFOname(self):
		l = self.l.getCurrentSelection()
		return l and l[0][0][:-3]+"nfo"

	def getNFOurl(self):
		l = self.l.getCurrentSelection()
		return l and l[0][1][:-3]+"nfo"

	def isValid(self):
		l = self.l.getCurrentSelection()
		if l[0] == 0:
			return False
		else:
			return True

	def moveSelection(self,idx=0):
		if self.instance is not None:
			self.instance.moveSelectionTo(idx)

class NFIDownload(Screen):
	LIST_SOURCE = 1
	LIST_DEST = 2
	skin = """
		<screen name="NFIDownload" position="90,95" size="560,420" title="Image download utility">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" zPosition="0" size="140,40" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;19" valign="center" halign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;19" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;19" valign="center" halign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;19" valign="center" halign="center" backgroundColor="#18188b" transparent="1" />
			
			<widget source="label_top" render="Label" position="10,44" size="240,20" font="Regular;16" />
			<widget name="feedlist" position="10,66" size="250,222" scrollbarMode="showOnDemand" />
			<widget name="destlist" position="0,66" size="260,222" scrollbarMode="showOnDemand" />

			<widget source="label_bottom" render="Label" position="10,312" size="240,18" font="Regular;16"/>
			<widget source="path_bottom" render="Label" position="10,330" size="250,42" font="Regular;18" />
			
			<widget source="infolabel" render="Label" position="270,44" size="280,284" font="Regular;16" />
			<widget source="job_progressbar" render="Progress" position="10,374" size="540,26" borderWidth="1" backgroundColor="#254f7497" />
			<widget source="job_progresslabel" render="Label" position="130,378" zPosition="2" font="Regular;18" halign="center" transparent="1" size="300,22" foregroundColor="#000000" />
			<widget source="statusbar" render="Label" position="10,404" size="540,16" font="Regular;16" foregroundColor="#cccccc" />
		</screen>"""

	def __init__(self, session, destdir="/tmp/"):
		self.skin = NFIDownload.skin
		Screen.__init__(self, session)
		
		self["job_progressbar"] = Progress()
		self["job_progresslabel"] = StaticText()
		
		self["infolabel"] = StaticText()
		self["statusbar"] = StaticText()
		self["label_top"] = StaticText()
		self["label_bottom"] = StaticText()
		self["path_bottom"] = StaticText()
		
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()

		self["key_red"] = StaticText()

		self["feedlist"] = Feedlist([0,(eListboxPythonMultiContent.TYPE_TEXT, 0, 0,250, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, "feed not available")])
		self["destlist"] = FileList(destdir, showDirectories = True, showFiles = False)
		self["destlist"].hide()

		self.download_container = eConsoleAppContainer()
		self.nfo = ""
		self.nfofile = ""
		self.feedhtml = ""
		self.focus = None
		self.download = None
		self.box = HardwareInfo().get_device_name()
		self.feed_base = "http://www.dreamboxupdate.com/opendreambox/1.5/%s/images/" % self.box
		self.nfi_filter = "" # "release" # only show NFIs containing this string, or all if ""
		self.wizard_mode = False

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "EPGSelectActions"],
		{
			"cancel": self.closeCB,
			"red": self.closeCB,
			"green": self.nfi_download,
			"yellow": self.switchList,
			"blue": self.askCreateUSBstick,
			"prevBouquet": self.switchList,
			"nextBouquet": self.switchList,
			"ok": self.ok,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"upRepeated": self.up,
			"downRepeated": self.down,
			"down": self.down
		}, -1)

		self.feed_download()

	def downloading(self, state=True):
		if state is True:	
			self["key_red"].text = _("Cancel")
			self["key_green"].text = ""
			self["key_yellow"].text = ""
			self["key_blue"].text = ""
		else:
			self.download = None
			self["key_red"].text = _("Exit")
			if self["feedlist"].isValid():
				self["key_green"].text = (_("Download"))
				if self.focus is self.LIST_SOURCE:
					self["key_yellow"].text = (_("Change dir."))
				else:
					self["key_yellow"].text = (_("Select image"))
			self["key_blue"].text = (_("USB stick wizard"))

	def switchList(self,to_where=None):
		if self.download or not self["feedlist"].isValid():
			return

		self["job_progressbar"].value = 0
		self["job_progresslabel"].text = ""

		if to_where is None:
			if self.focus is self.LIST_SOURCE:
				to_where = self.LIST_DEST
			if self.focus is self.LIST_DEST:
				to_where = self.LIST_SOURCE

		if to_where is self.LIST_DEST:
			self.focus = self.LIST_DEST
			self["statusbar"].text = _("Please select target directory or medium")
			self["label_top"].text = _("choose destination directory")+":"
			self["feedlist"].hide()
			self["destlist"].show()
			self["label_bottom"].text = _("Selected source image")+":"
			self["path_bottom"].text = str(self["feedlist"].getNFIname())
			self["key_yellow"].text = (_("Select image"))

		elif to_where is self.LIST_SOURCE:
			self.focus = self.LIST_SOURCE
			self["statusbar"].text = _("Please choose .NFI image file from feed server to download")
			self["label_top"].text = _("select image from server")+":"
			self["feedlist"].show()
			self["destlist"].hide()
			self["label_bottom"].text = _("Destination directory")+":"
			self["path_bottom"].text = str(self["destlist"].getCurrentDirectory())
			self["key_yellow"].text = (_("Change dir."))

	def up(self):
		if self.download:
			return
		if self.focus is self.LIST_SOURCE:
			self["feedlist"].up()
			self.nfo_download()
		if self.focus is self.LIST_DEST:
			self["destlist"].up()

	def down(self):
		if self.download:
			return
		if self.focus is self.LIST_SOURCE:
			self["feedlist"].down()
			self.nfo_download()
		if self.focus is self.LIST_DEST:
			self["destlist"].down()

	def left(self):
		if self.download:
			return
		if self.focus is self.LIST_SOURCE:
			self["feedlist"].pageUp()
			self.nfo_download()
		if self.focus is self.LIST_DEST:
			self["destlist"].pageUp()

	def right(self):
		if self.download:
			return
		if self.focus is self.LIST_SOURCE:
			self["feedlist"].pageDown()
			self.nfo_download()
		if self.focus is self.LIST_DEST:
			self["destlist"].pageDown()

	def ok(self):
		if self.download:
			return
		if self.focus is self.LIST_DEST:
			if self["destlist"].canDescent():
				self["destlist"].descent()

	def feed_download(self):
		self.downloading(True)
		self.download = self.feed_download
		client.getPage(self.feed_base).addCallback(self.feed_finished).addErrback(self.feed_failed)

	def feed_failed(self, failure_instance):
		print "[feed_failed] " + str(failure_instance)
		self["infolabel"].text = _("Could not connect to Dreambox .NFI Image Feed Server:") + "\n" + failure_instance.getErrorMessage() + "\n\n" + _("Please check your network settings!")
		self.downloading(False)

	def feed_finished(self, feedhtml):
		print "[feed_finished] " + str(feedhtml)
		self.downloading(False)
		fileresultmask = re.compile("<a href=[\'\"](?P<url>.*?)[\'\"]>(?P<name>.*?.nfi)</a>", re.DOTALL)
		searchresults = fileresultmask.finditer(feedhtml)
		fileresultlist = []
		if searchresults:
			for x in searchresults:
				url = x.group("url")
				if url[0:7] != "http://":
					url = self.feed_base + x.group("url")
				name = x.group("name")
				if name.find(self.nfi_filter) > -1:
					entry = [[name, url],(eListboxPythonMultiContent.TYPE_TEXT, 0, 0,250, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, name)]
					print "adding to feedlist: " + str(entry)
					fileresultlist.append(entry)
				else:
					print "NOT adding to feedlist: " + name
			self["feedlist"].l.setList(fileresultlist)
			self["feedlist"].moveSelection(0)

		if len(fileresultlist) > 0:
			self.switchList(self.LIST_SOURCE)
			self.nfo_download()
		else:
			self["infolabel"].text = _("Cannot parse feed directory")

	def nfo_download(self):
		print "[check_for_NFO]"
		if self["feedlist"].isValid():
			print "nfiname: " + self["feedlist"].getNFIname()
			self["job_progressbar"].value = 0
			self["job_progresslabel"].text = ""
			if self["feedlist"].getNFIurl() is None:
				self["key_green"].text = ""
				return
			self["key_green"].text = _("Download")
			nfourl = self["feedlist"].getNFOurl()
			print "downloading " + nfourl
			self.download = self.nfo_download
			self.downloading(True)
			client.getPage(nfourl).addCallback(self.nfo_finished).addErrback(self.nfo_failed)
			self["statusbar"].text = ("Downloading image description...")

	def nfo_failed(self, failure_instance):
		print "[nfo_failed] " + str(failure_instance)
		self["infolabel"].text = _("No details for this image file") + "\n" + self["feedlist"].getNFIname()
		self["statusbar"].text = ""
		self.nfofilename = ""
		self.nfo = ""
		self.downloading(False)

	def nfo_finished(self,nfodata=""):
		print "[nfo_finished] " + str(nfodata)
		self.downloading(False)
		self.nfo = nfodata
		if self.nfo != "":
			self.nfofilename = self["destlist"].getCurrentDirectory() + '/' + self["feedlist"].getNFOname()
			self["infolabel"].text = self.nfo
		else:	
			self.nfofilename = ""
			self["infolabel"].text = _("No details for this image file")
		self["statusbar"].text = ""

	def nfi_download(self):
		if self["destlist"].getCurrentDirectory() is None:
			self.switchList(self.LIST_TARGET)
		if self["feedlist"].isValid():
			url = self["feedlist"].getNFIurl()
			self.nfilocal = self["destlist"].getCurrentDirectory()+'/'+self["feedlist"].getNFIname()
			print "[nfi_download] downloading %s to %s" % (url, self.nfilocal)
			self.download = downloadWithProgress(url,self.nfilocal)
			self.download.addProgress(self.nfi_progress)
			self["job_progressbar"].range = 1000
			self.download.start().addCallback(self.nfi_finished).addErrback(self.nfi_failed)
			self.downloading(True)

	def nfi_progress(self, recvbytes, totalbytes):
		#print "[update_progress] recvbytes=%d, totalbytes=%d" % (recvbytes, totalbytes)
		self["job_progressbar"].value = int(1000*recvbytes/float(totalbytes))
		self["job_progresslabel"].text = "%d of %d kBytes (%.2f%%)" % (recvbytes/1024, totalbytes/1024, 100*recvbytes/float(totalbytes))

	def nfi_failed(self, failure_instance=None, error_message=""):
		if error_message == "" and failure_instance is not None:
			error_message = failure_instance.getErrorMessage()
		print "[nfi_failed] " + error_message
		if fileExists(self["destlist"].getCurrentDirectory()+'/'+self["feedlist"].getNFIname()):
			message = "%s %s\n%s" % (_(".NFI Download failed:"), error_message, _("Remove the incomplete .NFI file?"))
			self.session.openWithCallback(self.nfi_remove, MessageBox, message, MessageBox.TYPE_YESNO)
		else:
			message = "%s %s" % (_(".NFI Download failed:"),error_message)
			self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)
			self.downloading(False)

	def nfi_finished(self, string=""):
		print "[nfi_finished] " + str(string)
		if self.nfo != "":
			self.nfofilename = self["destlist"].getCurrentDirectory() + '/' + self["feedlist"].getNFOname()
			nfofd = open(self.nfofilename, "w")
			if nfofd:
				nfofd.write(self.nfo)
				nfofd.close()
			else:
				print "couldn't save nfo file " + self.nfofilename

			pos = self.nfo.find("MD5:")
			if pos > 0 and len(self.nfo) >= pos+5+32:
				self["statusbar"].text = ("Please wait for md5 signature verification...")
				cmd = "md5sum -c -"
				md5 = self.nfo[pos+5:pos+5+32] + "  " + self.nfilocal
				print cmd, md5
				self.download_container.setCWD(self["destlist"].getCurrentDirectory())
				self.download_container.appClosed.append(self.md5finished)
				self.download_container.execute(cmd)
				self.download_container.write(md5)
				self.download_container.dataSent.append(self.md5ready)
			else:
				self["statusbar"].text = "Download completed."
				self.downloading(False)
		else:
			self["statusbar"].text = "Download completed."
			self.downloading(False)
			if self.wizard_mode:
				self.configBackup()

	def md5ready(self, retval):
		self.download_container.sendEOF()

	def md5finished(self, retval):
		print "[md5finished]: " + str(retval)
		self.download_container.appClosed.remove(self.md5finished)
		if retval==0:
			self.downloading(False)
			if self.wizard_mode:
				self.configBackup()
			else:
				self["statusbar"].text = _(".NFI file passed md5sum signature check. You can safely flash this image!")
				self.switchList(self.LIST_SOURCE)
		else:
			self.session.openWithCallback(self.nfi_remove, MessageBox, (_("The md5sum validation failed, the file may be downloaded incompletely or be corrupted!") + "\n" + _("Remove the broken .NFI file?")), MessageBox.TYPE_YESNO)

	def nfi_remove(self, answer):
		self.downloading(False)
		if answer == True:
			nfifilename =  self["destlist"].getCurrentDirectory()+'/'+self["feedlist"].getNFIname()
			if fileExists(self.nfofilename):
				remove(self.nfofilename)
			if fileExists(nfifilename):
				remove(nfifilename)
		self.switchList(self.LIST_SOURCE)

	def askCreateUSBstick(self):
		self.downloading()
		self.imagefilename = "/tmp/nfiflash_" + self.box + ".img"
		message = _("You have chosen to create a new .NFI flasher bootable USB stick. This will repartition the USB stick and therefore all data on it will be erased.")
		self.session.openWithCallback(self.flasherdownload_query, MessageBox, (message + '\n' + _("First we need to download the latest boot environment for the USB flasher.")), MessageBox.TYPE_YESNO)

	def flasherdownload_query(self, answer):
		if answer is False:
			self.downloading(False)
			self.switchList(self.LIST_SOURCE)
			return
		#url = self.feed_base + "/nfiflasher_" + self.box + ".tar.bz2"
		url = "http://www.dreamboxupdate.com/download/opendreambox/dreambox-nfiflasher-%s.tar.bz2" % self.box
		localfile = "/tmp/nfiflasher_image.tar.bz2"
		print "[flasherdownload_query] downloading %s to %s" % (url, localfile)
		self["statusbar"].text = ("Downloading %s..." % url)
		self.download = downloadWithProgress(url,localfile)
		self.download.addProgress(self.nfi_progress)
		self["job_progressbar"].range = 1000
		self.download.start().addCallback(self.flasherdownload_finished).addErrback(self.flasherdownload_failed)

	def flasherdownload_failed(self, failure_instance=None, error_message=""):
		if error_message == "" and failure_instance is not None:
			error_message = failure_instance.getErrorMessage()
		print "[flasherdownload_failed] " + error_message
		message = "%s %s" % (_("Download of USB flasher boot image failed: "),error_message)
		self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)
		self.remove_img(True)

	def flasherdownload_finished(self, string=""):
		print "[flasherdownload_finished] " + str(string)	
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.umount_finished)
		self.container.dataAvail.append(self.tool_avail)
		self.taskstring = ""
		umountdevs = ""
		from os import listdir
		for device in listdir("/dev"):
			if device[:2] == "sd" and device[-1:].isdigit():
				umountdevs += "/dev/"+device
		self.cmd = "umount " + umountdevs
		print "executing " + self.cmd
		self.container.execute(self.cmd)

	def tool_avail(self, string):
		print "[tool_avail]" + string
		self.taskstring += string

	def umount_finished(self, retval):
		self.container.appClosed.remove(self.umount_finished)
		self.container.appClosed.append(self.dmesg_cleared)
		self.taskstring = ""
		self.cmd = "dmesg -c"
		print "executing " + self.cmd
		self.container.execute(self.cmd)

	def dmesg_cleared(self, answer):
		self.container.appClosed.remove(self.dmesg_cleared)
		self.msgbox = self.session.open(MessageBox, _("Please disconnect all USB devices from your Dreambox and (re-)attach the target USB stick (minimum size is 64 MB) now!"), MessageBox.TYPE_INFO)
		hotplugNotifier.append(self.hotplugCB)

	def hotplugCB(self, dev, action):
		print "[hotplugCB]", dev, action
		if dev.startswith("sd") and action == "add":
			self.msgbox.close()
			hotplugNotifier.remove(self.hotplugCB)
			self.container.appClosed.append(self.dmesg_scanned)
			self.taskstring = ""
			self.cmd = "dmesg"
			print "executing " + self.cmd
			self.container.execute(self.cmd)

	def dmesg_scanned(self, retval):
		self.container.appClosed.remove(self.dmesg_scanned)
		dmesg_lines = self.taskstring.splitlines()
		self.devicetext = None
		self.stickdevice = None
		for i, line in enumerate(dmesg_lines):
			if line.find("usb-storage: waiting for device") != -1 and len(dmesg_lines) > i+3:
				self.devicetext = dmesg_lines[i+1].lstrip()+"\n"+dmesg_lines[i+3]
			elif line.find("/dev/scsi/host") != -1:
				self.stickdevice = line.split(":",1)[0].lstrip()

		if retval != 0 or self.devicetext is None or self.stickdevice is None:
			self.session.openWithCallback(self.remove_img, MessageBox, _("No useable USB stick found"), MessageBox.TYPE_ERROR)
		else:
			self.session.openWithCallback(self.fdisk_query, MessageBox, (_("The following device was found:\n\n%s\n\nDo you want to write the USB flasher to this stick?") % self.devicetext), MessageBox.TYPE_YESNO)

	def fdisk_query(self, answer):
		if answer == True and self.stickdevice:
			self["statusbar"].text = ("Partitioning USB stick...")
			self["job_progressbar"].range = 1000
			self["job_progressbar"].value = 100
			self["job_progresslabel"].text = "5.00%"
			self.taskstring = ""
			self.container.appClosed.append(self.fdisk_finished)
			self.container.execute("fdisk " + self.stickdevice + "/disc")
			self.container.write("d\nn\np\n1\n\n\nt\n6\nw\n")
			self.delayTimer = eTimer()
			self.delayTimer.callback.append(self.progress_increment)
			self.delayTimer.start(105, False)
		else:
			self.remove_img(True)

	def fdisk_finished(self, retval):
		self.container.appClosed.remove(self.fdisk_finished)
		self.delayTimer.stop()
		if retval == 0:
			if fileExists(self.imagefilename):
				self.tar_finished(0)
				self["job_progressbar"].value = 700
			else:
				self["statusbar"].text = ("Decompressing USB stick flasher boot image...")
				self.taskstring = ""
				self.container.appClosed.append(self.tar_finished)
				self.container.setCWD("/tmp")
				self.cmd = "tar -xjvf nfiflasher_image.tar.bz2"
				self.container.execute(self.cmd)
				print "executing " + self.cmd
				self.delayTimer = eTimer()
				self.delayTimer.callback.append(self.progress_increment)
				self.delayTimer.start(105, False)
		else:
                        print "fdisk failed: " + str(retval)
			self.session.openWithCallback(self.remove_img, MessageBox, ("fdisk " + _("failed") + ":\n" + str(self.taskstring)), MessageBox.TYPE_ERROR)

	def progress_increment(self):
		newval = int(self["job_progressbar"].value) + 1
		if newval < 950:
			self["job_progressbar"].value = newval
			self["job_progresslabel"].text = "%.2f%%" % (newval/10.0)

	def tar_finished(self, retval):
		self.delayTimer.stop()
		if len(self.container.appClosed) > 0:
			self.container.appClosed.remove(self.tar_finished)
		if retval == 0:
			self.imagefilename = "/tmp/nfiflash_" + self.box + ".img"
			self["statusbar"].text = ("Copying USB flasher boot image to stick...")
			self.taskstring = ""
			self.container.appClosed.append(self.dd_finished)
			self.cmd = "dd if=%s of=%s" % (self.imagefilename,self.stickdevice+"/part1")
			self.container.execute(self.cmd)
			print "executing " + self.cmd
			self.delayTimer = eTimer()
			self.delayTimer.callback.append(self.progress_increment)
			self.delayTimer.start(105, False)
		else:
			self.session.openWithCallback(self.remove_img, MessageBox, (self.cmd + " " + _("failed") + ":\n" + str(self.taskstring)), MessageBox.TYPE_ERROR)

	def dd_finished(self, retval):
		self.delayTimer.stop()
		self.container.appClosed.remove(self.dd_finished)
		self.downloading(False)
		if retval == 0:
			self["job_progressbar"].value = 950
			self["job_progresslabel"].text = "95.00%"
			self["statusbar"].text = ("Remounting stick partition...")
			self.taskstring = ""
			self.container.appClosed.append(self.mount_finished)
			self.cmd = "mount %s /mnt/usb -o rw,sync" % (self.stickdevice+"/part1")
			self.container.execute(self.cmd)
			print "executing " + self.cmd
		else:
			self.session.openWithCallback(self.remove_img, MessageBox, (self.cmd + " " + _("failed") + ":\n" + str(self.taskstring)), MessageBox.TYPE_ERROR)

	def mount_finished(self, retval):
		self.container.dataAvail.remove(self.tool_avail)
		self.container.appClosed.remove(self.mount_finished)
		if retval == 0:
			self["job_progressbar"].value = 1000
			self["job_progresslabel"].text = "100.00%"
			self["statusbar"].text = (".NFI Flasher bootable USB stick successfully created.")
			self.session.openWithCallback(self.flasherFinishedCB, MessageBox, _("The USB stick is now bootable. Do you want to download the latest image from the feed server and save it on the stick?"), type = MessageBox.TYPE_YESNO)
			self["destlist"].changeDir("/mnt/usb")
		else:
			self.session.openWithCallback(self.flasherFinishedCB, MessageBox, (self.cmd + " " + _("failed") + ":\n" + str(self.taskstring)), MessageBox.TYPE_ERROR)
			self.remove_img(True)

	def remove_img(self, answer):
		if fileExists("/tmp/nfiflasher_image.tar.bz2"):
			remove("/tmp/nfiflasher_image.tar.bz2")
		if fileExists(self.imagefilename):
			remove(self.imagefilename)
		self.downloading(False)
		self.switchList(self.LIST_SOURCE)

	def flasherFinishedCB(self, answer):
		if answer == True:
			self.wizard_mode = True
			self["feedlist"].moveSelection(0)
			self["path_bottom"].text = str(self["destlist"].getCurrentDirectory())
			self.nfo_download()
			self.nfi_download()

	def configBackup(self):
		self.session.openWithCallback(self.runBackup, MessageBox, _("The wizard can backup your current settings. Do you want to do a backup now?"))

	def runBackup(self, result=None):
		from Tools.Directories import createDir, isMount, pathExists
		from time import localtime
		from datetime import date
		from Screens.Console import Console
		if result:
			if isMount("/mnt/usb/"):
				if (pathExists("/mnt/usb/backup") == False):
					createDir("/mnt/usb/backup", True)
				d = localtime()
				dt = date(d.tm_year, d.tm_mon, d.tm_mday)
				self.backup_file = "backup/" + str(dt) + "_settings_backup.tar.gz"
				self.session.open(Console, title = "Backup running", cmdlist = ["tar -czvf " + "/mnt/usb/" + self.backup_file + " /etc/enigma2/ /etc/network/interfaces /etc/wpa_supplicant.conf"], finishedCallback = self.backup_finished, closeOnSuccess = True)
		else:
			self.backup_file = None
			self.backup_finished(skipped=True)

	def backup_finished(self, skipped=False):
		if not skipped:
			wizardfd = open("/mnt/usb/wizard.nfo", "w")
			if wizardfd:
				wizardfd.write("image: "+self["feedlist"].getNFIname()+'\n')
				wizardfd.write("configuration: "+self.backup_file+'\n')
				wizardfd.close()
		self.session.open(MessageBox, _("To update your Dreambox firmware, please follow these steps:\n1) Turn off your box with the rear power switch and plug in the bootable USB stick.\n2) Turn mains back on and hold the DOWN button on the front panel pressed for 10 seconds.\n3) Wait for bootup and follow instructions of the wizard."), type = MessageBox.TYPE_INFO)

	def closeCB(self):
		if self.download:
			self.download.stop()
			#self.nfi_failed(None, "Cancelled by user request")
			self.downloading(False)
		else:
			self.close()

def main(session, **kwargs):
	session.open(NFIDownload,"/home/root")

def filescan_open(list, session, **kwargs):
	dev = "/dev/" + (list[0].path).rsplit('/',1)[0][7:]
	print "mounting device " + dev + " to /mnt/usb..."
	system("mount "+dev+" /mnt/usb/ -o rw,sync")
	session.open(NFIDownload,"/mnt/usb/")

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(mimetypes = ["application/x-dream-image"], 
			paths_to_scan = 
				[
					ScanPath(path = "", with_subdirs = False),
				], 
			name = "NFI", 
			description = (_("Download .NFI-Files for USB-Flasher")+"..."),
			openfnc = filescan_open, )
