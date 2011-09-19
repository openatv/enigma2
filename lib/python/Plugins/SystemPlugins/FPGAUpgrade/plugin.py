import os

import fpga
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

class UpgradeStatus(Screen):
	skin = 	"""
		<screen position="center,center" size="450,100" title="FPGA Upgrade">
			<widget name="name" position="10,0" size="430,20" font="Regular;18" halign="left" valign="bottom"/>
			<widget name="slider" position="10,25" size="430,30" backgroundColor="white"/>
			<widget name="status" position="10,27" zPosition="1" size="430,30" font="Regular;18" halign="center" valign="center" foregroundColor="black" backgroundColor="white" transparent="1"/>
			<widget source="info" render="Label" position="10,70" zPosition="1" size="430,30" font="Regular;22" halign="center" valign="center" backgroundColor="black" transparent="1"/>
		</screen>
		"""
	def __init__(self, session, parent, timeout = 10):
		Screen.__init__(self,session)
		self.session = session

		self["actions"] = ActionMap(["OkCancelActions"],
                {
			"ok": self.keyExit,
                }, -1)

		self.is_done = 0
		self.exit_count = 0
		self.timeout = timeout
		self.title_str = "FPGA Upgrade"

		#self["name"] = Label(_("Upgrade status"))
		self["name"] = Label(_(" "))
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

	def callbackDoCheckProgress(self):
		self.status = self.parent.FPGA.get_status()

		if self.status > 0:
			self.slider.setValue(self.status)

		if self.status == 100:
			#print "fpga-upgrade done!!"
			self.status_bar.setText(_("Success. Press OK to exit."))
			#self.status_bar.setText(_("%d / 100" % (self.status)))
			self.timer_check_progress.stop()
			self.is_done = 1

			self.timer_exit = eTimer()
			self.timer_exit.callback.append(self.callbackExit)
			self.timer_exit.start(1000)
		elif self.status == -1 or self.status == -2:
			#print "fpga-upgrade error >> errno : [%d]" % (self.status)
			self.status_bar.setText(_("Error[%d]. Press Cancel to exit." % (self.status)))
			self.timer_check_progress.stop()
			self.is_done = 1
		else:
			#print "fpga-upgrade status : %d" % self.status
			self.status_bar.setText(_("%d / 100" % (self.status)))

	def callbackExit(self):
		if self.exit_count == self.timeout:
			self.timer_exit.stop()
			self.keyExit()
		self.exit_count = self.exit_count + 1
		self.instance.setTitle("%s (%d)" % (self.title_str, (self.timeout-self.exit_count)))

	def keyExit(self):
		if self.is_done :
			self.close()
		
class FPGAUpgrade(Screen):
	skin = 	"""
		<screen position="center,center" size="560,440" title="FPGA Upgrade" >
			<ePixmap pixmap="ViX_HD/buttons/red.png" position="0,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="ViX_HD/buttons/green.png" position="140,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="ViX_HD/buttons/yellow.png" position="280,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="ViX_HD/buttons/blue.png" position="420,7" size="140,40" alphatest="blend" />

			<widget source="key_red" render="Label" position="30,3" zPosition="1" size="115,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="170,3" zPosition="1" size="115,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget source="key_yellow" render="Label" position="310,3" zPosition="1" size="115,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget source="key_blue" render="Label" position="450,3" zPosition="1" size="115,40" font="Regular;20" halign="left" valign="center" transparent="1" />

			<widget source="status" render="Label" position="15,45" zPosition="1" size="540,40" font="Regular;18" halign="left" valign="center" transparent="1" />
			<widget name="file_list" position="0,100" size="555,325" scrollbarMode="showOnDemand" />
                </screen>
		"""

	def __init__(self, session): 
		Screen.__init__(self, session)
                self.session = session 

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Upgrade"))
		self["key_yellow"] = StaticText(_(" "))
		self["key_blue"] = StaticText(_("Download"))
		#self["key_blue"] = StaticText(_(" "))
		self["status"] = StaticText(_(" "))
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
		self.FPGA = fpga.Fpga()
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
			self.session.open(UpgradeStatus, self, timeout = 10)			

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

