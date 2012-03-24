import os, urllib
from urllib import urlretrieve

from Plugins.Plugin import PluginDescriptor

from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText, ConfigSelection, ConfigYesNo,ConfigText
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Label import Label

from Components.FileList import FileList
from Components.Slider import Slider

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from enigma import ePoint, eConsoleAppContainer, eTimer
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

fwlist = None
fwdata = None
if os.path.exists("/proc/stb/info/vumodel"):
	vumodel = open("/proc/stb/info/vumodel")
	info = vumodel.read().strip()
	vumodel.close()

	if info == "ultimo":
		fwlist= [
			 ("fpga", _("FPGA"))
			,("fp", _("Front Processor"))
			]
		fwdata= {
			 "fpga" : ["http://archive.vuplus.com/download/fpga", "fpga.files", "/dev/fpga_dp;/dev/misc/dp;"]
			,"fp"   : ["http://archive.vuplus.com/download/fp", "fp.files", "/dev/bcm_mu;"]
			}
	elif info == "uno":
		fwlist= [
			("fpga", _("FPGA"))
			]
		fwdata= {
			"fpga" : ["http://archive.vuplus.com/download/fpga", "fpga.files", "/dev/fpga_dp;/dev/misc/dp;"]
			}

import os, fcntl, thread
STATUS_READY 		= 0
STATUS_DONE 		= 1
STATUS_ERROR		= 2
STATUS_PREPARED		= 3
STATUS_PROGRAMMING 	= 4
STATUS_RETRY_UPGRADE 	= 5

class FPUpgradeCore() :
	status = STATUS_READY
	errmsg = ''
	MAX_CALL_COUNT = 120
	def __init__(self, firmwarefile, devicefile):
		self.devicefile = devicefile
		self.firmwarefile = firmwarefile

	def doUpgrade(self):
		firmware,device = None,None
		def closefpga(fp, fd):
			if fd is not None: os.close(fd)
			if fp is not None: fp.close()
		try:
			size = os.path.getsize(self.firmwarefile)
			if size == 0: raise Exception, 'data_size is zero'
			#print '[FPUpgradeCore] data_size :',size

			for xx in range(3):
				self.callcount = 0
				self.status = STATUS_READY

				firmware = open(self.firmwarefile, 'rb')
				device = os.open(self.devicefile, os.O_RDWR)
				#print '[FPUpgradeCore] open >> [ok]'

				rc = fcntl.ioctl(device, 0, size)
				if rc < 0: raise Exception, 'fail to set size : %d'%(rc)
				#print '[FPUpgradeCore] set size >> [ok]'
				self.status = STATUS_PREPARED

				while True:
					data = firmware.read(1024)
					if data == '': break
					os.write(device, data)
				#print '[FPUpgradeCore] write data >> [ok]'

				self.status = STATUS_PROGRAMMING
				rc = fcntl.ioctl(device, 1, 0)
				if rc == 0: break
				if xx == 2: raise Exception, 'fail to upgrade : %d'%(rc)
				self.errmsg = 'fail to upgrade, retry..'
				self.status = STATUS_RETRY_UPGRADE
				closefpga(firmware, device)
			#print '[FPUpgradeCore] upgrade done.'
			if self.callcount < 20: raise Exception, 'wrong fpga file.'
		except Exception, msg:
			self.errmsg = msg
			print '[FPUpgradeCore] ERROR >>',msg
			closefpga(firmware, device)
			return STATUS_ERROR
		return STATUS_DONE

	def upgradeMain(self):
		self.status = STATUS_READY
		self.status = self.doUpgrade()
		if self.status == STATUS_DONE:
			print 'upgrade done.'
		elif self.status == STATUS_ERROR:
			print 'error!!'
		else:	print 'unknown.'

class FPGAUpgradeCore() :
	status = STATUS_READY
	errmsg = ''
	callcount 	= 0
	MAX_CALL_COUNT 	= 1500
	def __init__(self, firmwarefile, devicefile):
		print '[FPGAUpgrade]'
		self.devicefile = devicefile
		self.firmwarefile = firmwarefile

	def doUpgrade(self):
		firmware,device = None,None
		def closefpga(fp, fd):
			if fd is not None: os.close(fd)
			if fp is not None: fp.close()
		try:
			size = os.path.getsize(self.firmwarefile)
			if size == 0: raise Exception, 'data_size is zero'
			#print '[FPGAUpgradeCore] data_size :',size

			firmware = open(self.firmwarefile, 'rb')
			device = os.open(self.devicefile, os.O_RDWR)
			#print '[FPGAUpgradeCore] open >> [ok]'

			rc = fcntl.ioctl(device, 0, size)
			if rc < 0: raise Exception, 'fail to set size : %d'%(rc)
			#print '[FPGAUpgradeCore] set size >> [ok]'

			rc = fcntl.ioctl(device, 2, 5)
			if rc < 0: raise Exception, 'fail to set programming mode : %d'%(rc)
			#print '[FPGAUpgradeCore] programming mode >> [ok]'
			self.status = STATUS_PREPARED

			while True:
				data = firmware.read(1024)
				if data == '': break
				os.write(device, data)
			#print '[FPGAUpgradeCore] write data >> [ok]'

			self.status = STATUS_PROGRAMMING
			rc = fcntl.ioctl(device, 1, 0)
			if rc < 0: raise Exception, 'fail to programming : %d'%(rc)
			#print '[FPGAUpgradeCore] upgrade done.'
			if self.callcount < 20: raise Exception, 'wrong fpga file.'
		except Exception, msg:
			self.errmsg = msg
			print '[FPGAUpgradeCore] ERROR >>',msg
			closefpga(firmware, device)
			return STATUS_ERROR
		closefpga(firmware, device)
		return STATUS_DONE

	def upgradeMain(self):
		self.status = STATUS_READY
		self.status = self.doUpgrade()
		if self.status == STATUS_DONE:
			print '[FPGAUpgrade] upgrade done.'
		elif self.status == STATUS_ERROR:
			print '[FPGAUpgrade] occur error.'
		else:	print '[FPGAUpgrade] occur unknown error.'

class FirmwareUpgradeManager:
	fu = None
	def getInterval(self):
		return 200

	def startUpgrade(self, datafile, device, firmware):
		if firmware == 'fpga':
			self.fu = FPGAUpgradeCore(firmwarefile=datafile, devicefile=device)
		elif firmware == 'fp':
			self.fu = FPUpgradeCore(firmwarefile=datafile, devicefile=device)
		thread.start_new_thread(self.fu.upgradeMain, ())

	def checkError(self):
		if self.fu.status == STATUS_ERROR:
			self.fu.callcount = 0
			return True
		return False

	def getStatus(self):
		if self.fu.status in (STATUS_READY, STATUS_ERROR):
			return 0
		elif self.fu.status == STATUS_PREPARED:
			return 2
		elif self.fu.status == STATUS_PROGRAMMING:
			self.fu.callcount += 1
			ret = (self.fu.callcount * 100) / self.fu.MAX_CALL_COUNT + 2
			if ret >= 100: ret = 99
			#print "callcount : [%d]"%(self.fu.callcount);
			return ret
		elif self.fu.status == STATUS_DONE:
			return 100

	def getErrorMessage(self, errno, errmsg):
		return str(self.fu.errmsg)

class UpgradeStatus(Screen):
	skin = 	"""
		<screen position="center,center" size="450,100" title=" ">
			<widget name="name" position="10,0" size="430,20" font="Regular;18" halign="left" valign="bottom"/>
			<widget name="slider" position="10,25" size="430,30" backgroundColor="white"/>
			<widget name="status" position="10,25" zPosition="1" size="430,30" font="Regular;18" halign="center" valign="center" foregroundColor="black" backgroundColor="black" transparent="1"/>
			<widget source="info" render="Label" position="10,70" zPosition="1" size="430,30" font="Regular;22" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
		</screen>
		"""

	def __init__(self, session, parent, firmware, datafile, device):
		Screen.__init__(self,session)
		self.session = session

		self["actions"] = ActionMap(["OkCancelActions"],
                {
			"ok": self.keyExit,
                }, -1)

		self.firmware = firmware
		self.datafile = datafile
		#print "[FirmwareUpgrade] - [%s][%s][%s]" % (self.datafile, firmware, device)

		self["name"] = Label(" ")
		self["info"] = StaticText(_("Can't cancel during upgrade!!"))

		self["status"] = Label(_("Status : 0%"))

		self.slider = Slider(0, 100)
		self["slider"] = self.slider

		self.callback = None

		self.setTitle(firmware.upper() + " Upgrade Status")

		self.FU = FirmwareUpgradeManager()

		self.old_status   = 0
		self.status_exit  = None
		self.check_status = eTimer()
		self.check_status.callback.append(self.cbCheckStatus)
		self.check_status.start(self.FU.getInterval())

		self.exitTimerCallCount = 0;
		self.upgradeLock = True
		self.FU.startUpgrade(self.datafile, device, firmware)

	def cbCheckStatus(self):
		errmsg = ""
		errno  = self.FU.checkError()
		if errno:
			self.check_status.stop()
			errmsg = self.FU.getErrorMessage(errno, errmsg)
			print "[FirmwareUpgrade] - ERROR : [%d][%s]" % (errno, errmsg)
			self.session.open(MessageBox, _(errmsg), MessageBox.TYPE_INFO, timeout = 10)
			self.cbConfirmExit(False)
			return
		status = self.FU.getStatus()
		if self.old_status > status and status != -1:
			self.session.open(MessageBox, _("Fail to upgrade!! Retry!!"), MessageBox.TYPE_INFO, timeout = 10)
		self.slider.setValue(status)
		self["status"].setText(_("%d / 100" % (status)))
		if status == 100:
			self.check_status.stop()
			self["status"].setText(_("Success. Press OK to exit."))
			self.status_exit = eTimer()
			self.status_exit.callback.append(self.cbTimerExit)
			self.status_exit.start(1000)
			self.upgradeLock = False
		self.old_status = status

	def setCallback(self, cb):
		self.callback = cb

	def cbTimerExit(self):
		if self.exitTimerCallCount < 10: # exit after 10 sec.
			self.exitTimerCallCount = self.exitTimerCallCount + 1
			self.setTitle("%s Upgrade Status (%d)" % (self.firmware.upper(), 10-self.exitTimerCallCount))
			return
		if self.status_exit is not None:
			self.status_exit.stop()
		self.keyExit()

	def cbConfirmExit(self, ret):
		if ret:
			os.system("rm -f %s %s.md5" % (self.datafile, self.datafile))
		self.close()

	def keyExit(self):
		if self.upgradeLock:
			return
		if self.callback is not None:
			self.callback("Reboot now for a successful upgrade.", True)
		self.session.openWithCallback(self.cbConfirmExit, MessageBox, _("Do you want to remove binary data?"), MessageBox.TYPE_YESNO, timeout = 10, default = False)

class Filebrowser(Screen):
	skin = 	"""
		<screen position="center,center" size="500,260" title="File Browser" >
			<ePixmap pixmap="ViX_HD_Common/buttons/blue.png" position="5,7" size="80,40" alphatest="blend" />
			<widget source="key_blue" render="Label" position="40,0" zPosition="1" size="180,40" font="Regular;20" halign="left" valign="center" transparent="1"/>
			<widget name="file_list" position="0,50" size="500,160" scrollbarMode="showOnDemand" />

			<widget source="status" render="Label" position="0,220" zPosition="1" size="500,40" font="Regular;18" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
                </screen>
		"""

	def __init__(self, session, parent, firmware):
		Screen.__init__(self, session)
                self.session = session

		self["key_blue"] = StaticText(_("Download the firmware (latest)"))

		self["status"]    = StaticText(" ")
		self["file_list"] = FileList("/", matchingPattern = "^.*")

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", ],
                {
			"ok":     self.onClickOk,
			"cancel": self.onClickCancel,
			"blue":   self.onClickBlue,
			"up":     self.onClickUp,
			"down":   self.onClickDown,
			"left":   self.onClickLeft,
			"right":  self.onClickRight,
                }, -1)

		self.resetGUI()
		self.firmware = firmware

		self.callback = None
		self.timer_downloading = None

		self.downloadLock = False
		self.setTitle(firmware.upper() + " File Browser")

	def resetGUI(self):
		self["status"].setText("Select to press OK, Exit to press Cancel.")

	def setCallback(self, func):
		self.callback = func

	def onClickOk(self):
		if self.downloadLock:
			return

	        if self["file_list"].canDescent() : # isDir
	        	self["file_list"].descent()
        		return

		# verify data
		self.gbin = self["file_list"].getCurrentDirectory() + self["file_list"].getFilename()
		if not os.path.exists(self.gbin):
			self.session.open(MessageBox, _("Can't found binary file."), MessageBox.TYPE_INFO, timeout = 10)
			return
		if not os.path.exists(self.gbin+".md5"):
			self.session.open(MessageBox, _("Can't found MD5 file."), MessageBox.TYPE_INFO, timeout = 10)
			return
		try:
			def checkExt(ext):
				name_ext = os.path.splitext(self["file_list"].getFilename())
				return len(name_ext)==2 and ext.startswith(name_ext[1])
			self.check_ext = False
			if (self.firmware == "fp" and checkExt(".bin")) or (self.firmware == "fpga" and checkExt(".dat")):
				self.check_ext = True
			if self.check_ext == False:
				self.session.open(MessageBox, _("You chose the incorrect file."), MessageBox.TYPE_INFO)
				return
		except:
			self.session.open(MessageBox, _("You chose the incorrect file."), MessageBox.TYPE_INFO)
			return

		if os.path.exists("/usr/bin/md5sum") == False:
			self.session.open(MessageBox, _("Can't find /usr/bin/md5sum"), MessageBox.TYPE_INFO, timeout = 10)
			return
		md5sum_A = os.popen("md5sum %s | awk \'{print $1}\'"%(self.gbin)).readline().strip()
		md5sum_B = os.popen("cat %s.md5 | awk \'{print $1}\'"%(self.gbin)).readline().strip()
		#print "[FirmwareUpgrade] - Verify : file[%s], md5[%s]"%(md5sum_A,md5sum_B)

		if md5sum_A != md5sum_B:
			self.session.open(MessageBox, _("Fail to verify data file. \nfile[%s]\nmd5[%s]"%(md5sum_A,md5sum_B)), MessageBox.TYPE_INFO, timeout = 10)
			return

		if self.callback is not None:
			self.callback(_(self.gbin))
		self.close()

	def onClickCancel(self):
		self.close()

	# uri : source file url(string)
	# tf  : target file name(string)
	# bd  : target base directory(string)
	# cbfunc(string) : callback function(function)
	def doDownload(self, uri, tf, bd='/tmp', cbfunc=None, errmsg="Fail to download."):
		tar = bd + "/" + tf
		#print "[FirmwareUpgrade] - Download Info : [%s][%s]" % (uri, tar)
		def doHook(blockNumber, blockSize, totalSize) :
			if blockNumber*blockSize > totalSize and cbfunc is not None:
				cbfunc(tar)
		opener = urllib.URLopener()
		try:
			opener.open(uri)
		except:
			#self.session.open(MessageBox, _("File not found in this URL:\n%s"%(uri)), MessageBox.TYPE_INFO, timeout = 10)
			print "[FirmwareUpgrade] - Fail to download. URL :",uri
			self.session.open(MessageBox, _(errmsg), MessageBox.TYPE_INFO, timeout = 10)
			del opener
			return False
		try :
			f, h = urlretrieve(uri, tar, doHook)
		except IOError, msg:
			#self.session.open(MessageBox, _(str(msg)), MessageBox.TYPE_INFO, timeout = 10)
			print "[FirmwareUpgrade] - Fail to download. ERR_MSG :",str(msg)
			self.session.open(MessageBox, _(errmsg), MessageBox.TYPE_INFO, timeout = 10)
			del opener
			return False
		del opener
		return True

	def runDownloading(self) :
		self.timer_downloading.stop()
		machine = str(open("/proc/stb/info/vumodel").read().strip())

		def cbDownloadDone(tar):
			try:
				if os.path.splitext(tar)[1] != ".files":
					self["status"].setText("Downloaded : %s\nSelect to press OK, Exit to press Cancel."%(tar))
			except:
				pass
		# target
		global fwdata
		root_uri  = fwdata[self.firmware][0]
		root_file = fwdata[self.firmware][1]
		if not self.doDownload("%s/%s"%(root_uri, root_file), root_file, cbfunc=cbDownloadDone):
			self.resetGUI()
			self.downloadLock = False
			return

		target_path = ""
		for l in file("/tmp/"+root_file).readlines():
			if l.startswith(machine):
				try:
					target_path = l.split("=")[1].strip()
				except:
					target_path = ""
					pass
		if target_path == "":
			self.session.open(MessageBox, _("Firmware does not exist."), MessageBox.TYPE_INFO)
			self.resetGUI()
			self.downloadLock = False
			return

		self.guri = "%s/vu%s/%s"%(root_uri, machine, target_path)
		self.gbin = os.path.basename(target_path)
		#print "[FirmwareUpgrade] - uri[%s], data[%s], data_path[%s]" % (self.gbin, self.guri, target_path)
		os.system("rm -f /tmp/" + root_file)

		# md5
		if not self.doDownload(self.guri+".md5", self.gbin+".md5", cbfunc=cbDownloadDone, errmsg="Can't download the checksum file."):
			self.resetGUI()
			self.downloadLock = False
			return
		# data
		if not self.doDownload(self.guri, self.gbin, cbfunc=cbDownloadDone, errmsg="Can't download the firmware file."):
			self.resetGUI()
			self.downloadLock = False
			return

		t = ''
		self["file_list"].changeDir("/tmp/")
		self["file_list"].moveToIndex(0)
		while cmp(self["file_list"].getFilename(), self.gbin) != 0 :
			self["file_list"].down()
			if cmp(t, self["file_list"].getFilename()) == 0:
				break
			t = self["file_list"].getFilename()

		del self.timer_downloading
		self.timer_downloading = None
		self.downloadLock = False

	def onClickBlue(self):
		if self.downloadLock:
			return
		self.downloadLock = True
		if not os.path.exists("/proc/stb/info/vumodel"):
			self.session.open(MessageBox, _("Can't found model name."), MessageBox.TYPE_INFO, timeout = 10)
			self.downloadLock = False
			return
		self["status"].setText("Please wait during download.")
		self.timer_downloading = eTimer()
		self.timer_downloading.callback.append(self.runDownloading)
		self.timer_downloading.start(1000)

	def onClickUp(self):
		if self.downloadLock:
			return
		self.resetGUI()
		self["file_list"].up()

	def onClickDown(self):
		if self.downloadLock:
			return
		self.resetGUI()
		self["file_list"].down()

	def onClickLeft(self):
		if self.downloadLock:
			return
		self.resetGUI()
		self["file_list"].pageUp()

	def onClickRight(self):
		if self.downloadLock:
			return
		self.resetGUI()
		self["file_list"].pageDown()

	def keyNone(self):
		None

class FirmwareUpgrade(Screen, ConfigListScreen):
	skin = 	"""
		<screen position="center,center" size="560,175" title="Firmware Upgrade" >
			<ePixmap pixmap="ViX_HD_Common/buttons/red.png" position="125,7" size="80,40" alphatest="blend" />
			<ePixmap pixmap="ViX_HD_Common/buttons/green.png" position="330,7" size="80,40" alphatest="blend" />

			<widget source="key_red" render="Label" position="160,0" zPosition="1" size="155,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="365,0" zPosition="1" size="155,40" font="Regular;20" halign="left" valign="center" transparent="1" />

			<widget name="config" zPosition="2" position="0,50" itemHeight="36" size="540,40" scrollbarMode="showOnDemand" transparent="1" />
			<widget source="status" render="Label" position="0,100" zPosition="1" size="540,75" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
                </screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
                self.session = session

		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok":      self.keyGreen,
			"cancel":  self.keyRed,
			"red":     self.keyRed,
			"green":   self.keyGreen,
			"blue":    self.keyBlue,
		}, -2)

		self.list = []
		self.updateFilePath = ""

		self.finishedExit = False

		self.rebootLock = False
		self.rebootMessage = ""
		self.cbRebootCallCount = 0;

		ConfigListScreen.__init__(self, self.list, session=self.session)
		self["key_red"] = StaticText(_("Close"))

		self.logmode = None
		self.old_blue_clicked = 0
		self.fileopenmode = False
		self.upgrade_auto_run_timer = eTimer()
		self.upgrade_auto_run_timer.callback.append(self.keyGreen)

		global fwlist
		if fwlist is None:
			self["key_green"] = StaticText(" ")
			self["status"] = StaticText(_("This plugin is supported only the Ultimo/Uno."))
		else:
			self["key_green"] = StaticText(_("Upgrade"))
			self["status"] = StaticText(" ")
			self.setupUI()

	def setupUI(self):
		global fwlist
		self.list = []
		self._item_firmware  = ConfigSelection(default=fwlist[0][0],  choices=fwlist)
		self._entry_firmware = getConfigListEntry(_("Firmware"), self._item_firmware)
		self.list.append(self._entry_firmware)
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self.setupStatus()

	def setupStatus(self,message=None,reboot=False):
		self.updateFilePath = ""
		if message is not None:
			self.rebootLock = reboot
			self["status"].setText(message)
			if reboot:
				self.rebootMessage = message
				self.reboot_timer = eTimer()
				self.reboot_timer.callback.append(self.cbReboot)
				self.reboot_timer.start(1000)
			return
		if not self.rebootLock:
			self["status"].setText("Press the Green/OK button")

	def doReboot(self):
		from Screens.Standby import TryQuitMainloop
		self.session.open(TryQuitMainloop, 2)

	def cbReboot(self):
		max_call_count = 20
		self.finishedExit = True
		if self.cbRebootCallCount < max_call_count:
			self.cbRebootCallCount = self.cbRebootCallCount + 1
			#self["status"].setText("%s (%d)"%(self.rebootMessage, max_call_count-self.cbRebootCallCount))
			self["status"].setText("Reboot after %d seconds. Press the OK to reboot now."%(max_call_count-self.cbRebootCallCount))
			return
		self.doReboot()

	# filebrowser window callback function
	def cbSetStatus(self, data=None):
		if data is not None:
			self["status"].setText("Press the Green/OK button, if you want to upgrade to this file:\n%s\n" % (data))
			self.updateFilePath = data
			if self.fileopenmode == False:
				self.upgrade_auto_run_timer.start(1000)

	# upgrade window callback function
	def cbFinishedUpgrade(self,message=None,reboot=False):
		self.setupStatus(message=message,reboot=reboot)

	def cbRunUpgrade(self, ret):
		if ret == False:
			return

		if self.updateFilePath == "":
			self.session.open(MessageBox, _("No selected binary data!!"), MessageBox.TYPE_INFO, timeout = 10)
			return
		device = None
		for d in fwdata[self._item_firmware.value][2].split(';'):
			if os.path.exists(d):
				device = d
		if device is None:
			self.session.open(MessageBox, _("Can't found device file!!"), MessageBox.TYPE_INFO, timeout = 10)
			return
		fbs = self.session.open(UpgradeStatus, self, self._item_firmware.value, self.updateFilePath, device)
		fbs.setCallback(self.cbFinishedUpgrade)

	def doFileOpen(self):
		fbs = self.session.open(Filebrowser, self, self._item_firmware.value)
		fbs.setCallback(self.cbSetStatus)

	def keyLeft(self):
		if self.rebootLock:
			return
		global fwlist
		if fwlist is None:
			return
		ConfigListScreen.keyLeft(self)
		self.setupStatus()

	def keyRight(self):
		global fwlist
		if fwlist is None:
			return
		ConfigListScreen.keyRight(self)
		self.setupStatus()

	def keyGreen(self):
		if self.finishedExit:
			self.doReboot()
			return
		self.upgrade_auto_run_timer.stop()
		if self.rebootLock:
			return
		global fwlist
		if fwlist is None:
			return
		if self.updateFilePath == "":
			#self.session.open(MessageBox, _("No selected binary data!!"), MessageBox.TYPE_INFO)
			self.doFileOpen()
			return
		msg = "You should not be stop during the upgrade.\nDo you want to upgrade?"
		self.session.openWithCallback(self.cbRunUpgrade, MessageBox, _(msg), MessageBox.TYPE_YESNO, timeout = 15, default = True)
		self.fileopenmode = False

	def keyYellow(self):
		if self.rebootLock:
			return
		global fwlist
		if fwlist is None:
			return
		self.fileopenmode = True
		self.doFileOpen()

	def keyRed(self):
		if self.rebootLock:
			return
		self.close()

	def cbLogMode(self):
		if self.old_blue_clicked:
			return
		self.logmode.stop()
		if os.path.exists("/tmp/onlogmode"):
			return
		os.system("touch /tmp/onlogmode")

	def keyBlue(self):
		if self.rebootLock:
			return
		if self.logmode is not None and self.old_blue_clicked == 0:
			return
		if self.old_blue_clicked:
			self.old_blue_clicked = 0
			return
		self.old_blue_clicked = 1
		self.logmode = eTimer()
		self.logmode.callback.append(self.cbLogMode)
		self.logmode.start(1000)

	def keyNone(self):
		None

def main(session, **kwargs):
        session.open(FirmwareUpgrade)

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Firmware Upgrade"), description="Upgrade Firmware..", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)

