import os, fcntl, thread

from enigma import eTimer

from urllib import urlretrieve
import urllib

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Plugins.Plugin import PluginDescriptor

from Tools.Directories import fileExists

from Components.Label import Label
from Components.Slider import Slider
from Components.Pixmap import Pixmap
from Components.FileList import FileList
from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText

STATUS_READY 		= 0
STATUS_DONE 		= 1
STATUS_ERROR		= 2
STATUS_PREPARED		= 3
STATUS_PROGRAMMING 	= 4

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
			if self.callcount < 100: raise Exception, 'wrong fpga file.'
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

class FPGAUpgradeManager:
	fu = None
	def get_interval(self):
		return 200

	def fpga_upgrade(self, datafile, device):
		self.fu = FPGAUpgradeCore(firmwarefile=datafile, devicefile=device)
		thread.start_new_thread(self.fu.upgradeMain, ())

	def checkError(self):
		if self.fu.status == STATUS_ERROR:
			self.fu.callcount = 0
			return True
		return False

	def get_status(self):
		if self.fu.status == STATUS_READY:
			return 0
		elif self.fu.status == STATUS_ERROR:
			return -1
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

	def get_error_msg(self, errno, errmsg):
		return str(self.fu.errmsg)

class UpgradeStatus(Screen):
	skin = 	"""
		<screen position="center,center" size="450,100" title="FPGA Upgrade">
			<widget name="name" position="10,0" size="430,20" font="Regular;18" halign="left" valign="bottom"/>
			<widget name="slider" position="10,25" size="430,30" backgroundColor="white"/>
			<widget name="status" position="10,27" zPosition="1" size="430,30" font="Regular;18" halign="center" valign="center" foregroundColor="black" backgroundColor="white" transparent="1"/>
			<widget source="info" render="Label" position="10,70" zPosition="1" size="430,30" font="Regular;22" halign="center" valign="center" backgroundColor="black" transparent="1"/>
		</screen>
		"""
	def __init__(self, session, parent, timeout = 20):
		Screen.__init__(self,session)
		self.session = session

		self["actions"] = ActionMap(["OkCancelActions"],
                {
			"ok": self.keyExit,
                }, -2)

		self.is_done = 0
		self.exit_count = 0
		self.timeout = 20
		self.title_str = "FPGA Upgrade"

		#self["name"] = Label(_("Upgrade status"))
		self["name"] = Label(" ")
		self["info"] = StaticText(_("Can't cancel during upgrade!!"))

		self["status"] = Label(_("Status : 0%"))
		self.status_bar = self["status"]

		self.slider = Slider(0, 100)
		self["slider"] = self.slider

		self.parent = parent
		self.timer_check_progress = eTimer()
		self.timer_check_progress.callback.append(self.callbackDoCheckProgress)
		interval = self.parent.FPGA.get_interval()
		self.timer_check_progress.start(interval)
		self.need_restart = False

	def callbackDoCheckProgress(self):
		self.status = self.parent.FPGA.get_status()

		if self.status > 0:
			self.slider.setValue(self.status)

		if self.status == 100:
			#print "fpga-upgrade done!!"
			self.status_bar.setText(_("Succeed"))
			#self.status_bar.setText(_("%d / 100" % (self.status)))
			self.timer_check_progress.stop()
			self.is_done = 1
			self.timer_exit = eTimer()
			self.timer_exit.callback.append(self.callbackExit)
			self.timer_exit.start(1000)

		elif self.status < 0:#elif self.status == -1 or self.status == -2:
			#print "fpga-upgrade error >> errno : [%d]" % (self.status)
			ERROR_MSG = ''
			ERROR_CODE = int(self.status) * -1
			ERROR_MSG = self.parent.FPGA.get_error_msg(ERROR_CODE, ERROR_MSG)
			self.status_bar.setText("Fail to update!!")
			self["info"].setText(_("Error[%d] : %s.\nPress OK to exit." % (self.status, ERROR_MSG)))
			self.timer_check_progress.stop()
			self.is_done = 1

		else:
			#print "fpga-upgrade status : %d" % self.status
			self.status_bar.setText(_("%d / 100" % (self.status)))

	def callbackExit(self):
		self.need_restart = True
		if self.exit_count == self.timeout:
			self.timer_exit.stop()
			self.keyExit()
		self.exit_count = self.exit_count + 1
		#self.instance.setTitle("%s (%d)" % (self.title_str, (self.timeout-self.exit_count)))
		self["info"].setText("Reboot after %d seconds.\nPress the OK to reboot now." %(self.timeout-self.exit_count))

	def keyExit(self):
		if self.need_restart:
			from Screens.Standby import TryQuitMainloop
			self.session.open(TryQuitMainloop, 2)
		if self.is_done :
			self.close()

class FPGAUpgrade(Screen):
	skin = 	"""
		<screen position="center,center" size="560,440" title="FPGA Upgrade" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="status" render="Label" position="15,45" zPosition="1" size="540,40" font="Regular;18" halign="left" valign="center" transparent="1" />
			<widget name="file_list" position="0,100" size="555,325" scrollbarMode="showOnDemand" />
                </screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("FPGA Upgrade"))

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Upgrade"))
		self["key_yellow"] = StaticText(" ")
		self["key_blue"] = StaticText(_("Download"))

		self["status"] = StaticText(" ")
		self["file_list"] = FileList("/", matchingPattern = "^.*")

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", ],
                {
                        "red": self.onClickRed,
			"green": self.onClickGreen,
			"blue": self.onClickBlue,
			"back": self.onClickRed,
			"ok": self.onClickOk,
			"up": self.onClickUp,
			"down": self.onClickDown,
			"left": self.onClickLeft,
			"right": self.onClickRight,
                }, -1)
		self.onLayoutFinish.append(self.doLayoutFinish)

                self.ERROR_MSG = ''
                self.ERROR_CODE = 0
                self.SOURCELIST = self["file_list"]
                self.STATUS_BAR = self["status"]
                self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))

		self.DEVICE_LIST = '/dev/fpga_dp;/dev/dp;/dev/misc/dp;'
		self.DOWNLOAD_TAR_PATH = '/tmp/'
		self.DOWNLOAD_FILE_NAME = 'TS_PRO.dat'
		self.DOWNLOAD_URL = ''
		self.doLoadConf()
		self.FPGA = FPGAUpgradeManager()
		print self.DEVICE_LIST
		print self.DOWNLOAD_TAR_PATH
		print self.DOWNLOAD_FILE_NAME
		print self.DOWNLOAD_URL

	def doLayoutFinish(self):
		return

	def doExit(self):
		if fileExists(self.DOWNLOAD_TAR_PATH + self.DOWNLOAD_FILE_NAME):
			os.remove(self.DOWNLOAD_TAR_PATH + self.DOWNLOAD_FILE_NAME)
		self.close()

	def doLoadConf(self):
		if fileExists("/proc/stb/info/vumodel"):
                        model = open("/proc/stb/info/vumodel").read().strip()
			download_uri_header = open('/usr/lib/enigma2/python/Plugins/SystemPlugins/FPGAUpgrade/fpga.conf').readline().strip()
			self.DOWNLOAD_URL = str(download_uri_header) + "vu" + str(model) + "/" + self.DOWNLOAD_FILE_NAME

	def doHook(self, blockNumber, blockSize, totalSize) :
		if blockNumber*blockSize > totalSize :
			self.STATUS_BAR.setText(_("Downloaded " + self.DOWNLOAD_TAR_PATH + self.DOWNLOAD_FILE_NAME))
		else :
			self.STATUS_BAR.setText(_("Downloading..."))

	def onCallbackHandler(self, confirmed):
		if confirmed:
			self.doExit()

	def doUpgradeHandler(self, confirmed):
		if confirmed == False:
			return

		path = ''
		try:
			path = self.SOURCELIST.getCurrentDirectory() + self.SOURCELIST.getFilename()
		except:
			#self.session.open(MessageBox, _("Can't select directory."), MessageBox.TYPE_INFO, timeout = 5)
			return

		device = ""
		device_list = self.DEVICE_LIST.split(";")

		for d in device_list:
			if os.path.exists(d):
				device = d
				break

		if device == None or len(device) == 0:
			message = "Fail to upgrade.\nCause : Can't found device.\nDo you want to exit?"
			self.session.openWithCallback(self.onCallbackHandler, MessageBox, _(message), MessageBox.TYPE_YESNO, timeout = 10, default = True)
			print "DEVICE_LIST : ", device_list

		print "DEVICE : ", device
		self.ERROR_CODE = self.FPGA.fpga_upgrade(path, device)
		if self.ERROR_CODE > 0:
			self.ERROR_MSG = self.FPGA.get_error_msg(self.ERROR_CODE, self.ERROR_MSG)
			message = "Fail to upgrade.\nCause : " + self.ERROR_MSG + "\nDo you want to exit?"
			self.session.openWithCallback(self.onCallbackHandler, MessageBox, _(message), MessageBox.TYPE_YESNO, timeout = 10, default = True)
			print "DEVICE : ", device
			print "FILE : ", path
		else:
			#self.session.open(MessageBox, _("Success!!"), MessageBox.TYPE_INFO, timeout = 5)
			self.session.open(UpgradeStatus, self, timeout = 20)

	def onClickRed(self):
		self.doExit()

	# run upgrade!!
	def onClickGreen(self):
		#self.session.open(MessageBox, _("Upgrade will take about 5 minutes to finish."), MessageBox.TYPE_INFO, timeout = 10)
		message = "Upgrade will take about 5 minutes to finish.\nDo you want to upgrade?"
		self.session.openWithCallback(self.doUpgradeHandler, MessageBox, _(message), MessageBox.TYPE_YESNO, timeout = 10, default = True)

	def onClickBlue(self):
		fname = ''
		header = ''
		test_opener = urllib.URLopener()
		try:
			test_opener.open(self.DOWNLOAD_URL)
		except:
			self.session.open(MessageBox, _('File not found'), MessageBox.TYPE_INFO, timeout = 5)
			del test_opener
			return
		try :
			fname, header = urlretrieve(self.DOWNLOAD_URL, self.DOWNLOAD_TAR_PATH + self.DOWNLOAD_FILE_NAME, self.doHook)
		except IOError, msg:
			self.session.open(MessageBox, _(str(msg)), MessageBox.TYPE_INFO, timeout = 5)
			del test_opener
			return
		del test_opener

		before_name = ''
		self.SOURCELIST.changeDir(self.DOWNLOAD_TAR_PATH)
		self.SOURCELIST.moveToIndex(0)
		while cmp(self.SOURCELIST.getFilename(), self.DOWNLOAD_FILE_NAME) != 0 :
			self.SOURCELIST.down()
			if cmp(before_name, self.SOURCELIST.getFilename()) == 0:
				break
			before_name = self.SOURCELIST.getFilename()

	def onClickOk(self):
	        if self.SOURCELIST.canDescent() : # isDir
	        	self.SOURCELIST.descent()
			if self.SOURCELIST.getCurrentDirectory():
				self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))
        	else:
			self.onClickGreen()

	def onClickUp(self):
		self.SOURCELIST.up()
		self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))

	def onClickDown(self):
		self.SOURCELIST.down()
		self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))

	def onClickLeft(self):
		self.SOURCELIST.pageUp()
		self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))

	def onClickRight(self):
		self.SOURCELIST.pageDown()
		self.STATUS_BAR.setText(_(self.SOURCELIST.getCurrentDirectory()))

def main(session, **kwargs):
        session.open(FPGAUpgrade)

def Plugins(**kwargs):
	return PluginDescriptor(name=_("FPGA Upgrade"), description="Upgrade FPGA..", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)

