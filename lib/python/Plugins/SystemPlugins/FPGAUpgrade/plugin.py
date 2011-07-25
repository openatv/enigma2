import os

from urllib import urlretrieve
import urllib

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Plugins.Plugin import PluginDescriptor

from Components.PluginComponent import plugins
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.FileList import FileList 
from Tools.Directories import fileExists

class FPGAUpgrade(Screen):
	skin = """
		<screen position="center,center" size="560,440" title="FPGA Upgrade" >
			<ePixmap pixmap="Vu_HD/buttons/red.png" position="0,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="Vu_HD/buttons/green.png" position="140,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="Vu_HD/buttons/yellow.png" position="280,7" size="140,40" alphatest="blend" />
			<ePixmap pixmap="Vu_HD/buttons/blue.png" position="420,7" size="140,40" alphatest="blend" />

			<widget source="key_red" render="Label" position="20,0" zPosition="1" size="115,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="160,0" zPosition="1" size="115,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_yellow" render="Label" position="300,0" zPosition="1" size="115,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_blue" render="Label" position="440,0" zPosition="1" size="115,40" font="Regular;20" halign="center" valign="center" transparent="1" />

			<widget source="status" render="Label" position="15,45" zPosition="1" size="540,40" font="Regular;18" halign="left" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="file_list" position="0,100" size="555,325" scrollbarMode="showOnDemand" />
                </screen>"""

	def __init__(self, session): 
		Screen.__init__(self, session)
                self.session = session 

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Ugrade"))
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

		self.DEVICE_PATH = '/dev/misc/dp'                                                                                       
		self.DOWNLOAD_TAR_PATH = '/tmp/'                                                                             
		self.DOWNLOAD_FILE_NAME = 'TS_PRO.dat'                                                                       
		self.DOWNLOAD_URL = ''
		self.doLoadConf()

		print self.DEVICE_PATH
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

		import fpga
		FPGA = fpga.Fpga()
		path = ''
		try:
			path = self.SOURCELIST.getCurrentDirectory() + self.SOURCELIST.getFilename() 
		except:
			#self.session.open(MessageBox, _("Can't select directory."), MessageBox.TYPE_INFO, timeout = 5)
			return

		self.ERROR_CODE = FPGA.fpga_upgrade(path, self.DEVICE_PATH)
		if self.ERROR_CODE > 0:
			self.ERROR_MSG = FPGA.get_error_msg(self.ERROR_CODE, self.ERROR_MSG)
			self.session.openWithCallback(self.onCallbackHandler, MessageBox, _("Fail to upgrade.\nCause : " + self.ERROR_MSG + "\nDo you want to exit?"), MessageBox.TYPE_YESNO, timeout = 10, default = True)

			print "DEVICE_PATH : ", self.DEVICE_PATH
			print "FILE_PATH : ", path
		else:
			self.session.open(MessageBox, _("Success!!"), MessageBox.TYPE_INFO, timeout = 5)

	def onClickRed(self):
		self.doExit()

	# run upgrade!!
	def onClickGreen(self):
		#self.session.open(MessageBox, _("Upgrade will take about 5 minutes to finish."), MessageBox.TYPE_INFO, timeout = 10)
		self.session.openWithCallback(self.doUpgradeHandler, MessageBox, _("Upgrade will take about 5 minutes to finish.\nDo you want to upgrade?"), MessageBox.TYPE_YESNO, timeout = 10, default = True)

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

