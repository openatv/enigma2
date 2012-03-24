from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry, ConfigSubsection, ConfigSelection
from Components.ActionMap import ActionMap
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from enigma import eTimer

config.plugins.remotecontrolcode = ConfigSubsection()
if fileExists("/proc/stb/info/vumodel"):
	vumodel = open("/proc/stb/info/vumodel")
	info=vumodel.read().strip()
	vumodel.close()
	if info == "uno" or info == "ultimo":
		config.plugins.remotecontrolcode.systemcode = ConfigSelection(default = "2", choices =
			[ ("1", "1 "), ("2", "2 "), ("3", "3 "), ("4", "4 ") ] )
	elif info == "solo" or info == "duo":
		config.plugins.remotecontrolcode.systemcode = ConfigSelection(default = "1", choices =
			[ ("1", "1 "), ("2", "2 "), ("3", "3 "), ("4", "4 ") ] )

def isRemoteCodeSupported():
	if fileExists("/proc/stb/fp/remote_code"):
		return True
	return False

SystemInfo["RemoteCode"] = isRemoteCodeSupported()

class RemoteControlCodeInit:
	def __init__(self):
		self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))

	def setSystemCode(self, type = 2):
		if not fileExists("/proc/stb/fp/remote_code"):
			return -1
		print "<RemoteControlCode> Write Remote Control Code : %d" % type
		f = open("/proc/stb/fp/remote_code", "w")
		f.write("%d" % type)
		f.close()
		return 0

	def getModel(self):
		if fileExists("/proc/stb/info/vumodel"):
			vumodel = open("/proc/stb/info/vumodel")
			info=vumodel.read().strip()
			vumodel.close()
			if info in ["uno", "ultimo"]:
				return True
			else:
				return False
		else:
			return False

class RemoteControlCode(Screen,ConfigListScreen,RemoteControlCodeInit):
	skin = """
			<screen name="RemoteControlCode" position="center,center" size="560,300" title="Remote Control System Code Setting" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" zPosition="2" position="5,50" size="550,200" scrollbarMode="showOnDemand" transparent="1" />
			</screen>"""

	def __init__(self,session):
		Screen.__init__(self,session)
		self.session = session
		Screen.setTitle(self, _("Remote Control Code"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)
		self.codestartup = config.plugins.remotecontrolcode.systemcode.value
		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self.createSetup()
		self.onLayoutFinish.append(self.checkModel)
		self.checkModelTimer = eTimer()
		self.checkModelTimer.callback.append(self.invalidmodel)

	def checkModel(self):
		if not self.getModel():
			self.checkModelTimer.start(1000,True)

	def invalidmodel(self):
			self.session.openWithCallback(self.close, MessageBox, _("This Plugin only support for UNO/ULTIMO"), MessageBox.TYPE_ERROR)

	def createSetup(self):
		self.list = []
		self.rcsctype = getConfigListEntry(_("Remote Control System Code"), config.plugins.remotecontrolcode.systemcode)
		self.list.append( self.rcsctype )
		self.list.append(getConfigListEntry(_("Text support"), config.misc.remotecontrol_text_support))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keySave(self):
		config.misc.remotecontrol_text_support.save()
		configfile.save()
		if self.codestartup != config.plugins.remotecontrolcode.systemcode.value:
			print "<RemoteControlCode> Selected System Code : ",config.plugins.remotecontrolcode.systemcode.value
			ret = self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))
			if ret == -1:
				self.restoreCode()
				self.session.openWithCallback(self.close, MessageBox, _("FILE NOT EXIST : /proc/stb/fp/remote_code"), MessageBox.TYPE_ERROR)
			else:
				self.session.openWithCallback(self.MessageBoxConfirmCodeCallback, MessageBoxConfirmCode, _("Please change your remote mode") + '\n' + _("Press and hold '2' & '7' until red LED is solid, then press 'Help', then press '000") + config.plugins.remotecontrolcode.systemcode.value + "'\n" + _("Then choose 'Keep' within seconds"), MessageBox.TYPE_YESNO, timeout = 60, default = False)
		else:
			self.close()

	def restoreCode(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def MessageBoxConfirmCodeCallback(self,ret):
		if ret:
			ConfigListScreen.keySave(self)
		else:
			self.restoreCode()
			self.setSystemCode(int(config.plugins.remotecontrolcode.systemcode.value))

class MessageBoxConfirmCode(MessageBox):
	def __init__(self, session, text, type = MessageBox.TYPE_YESNO, timeout = -1, close_on_any_key = False, default = True, enable_input = True, msgBoxID = None):
		MessageBox.__init__(self,session,text,type,timeout,close_on_any_key,default,enable_input,msgBoxID)
		self.skinName = "MessageBox"
		if type == MessageBox.TYPE_YESNO:
			self.list = [ (_("Keep"), 0), (_("Restore"), 1) ]
			self["list"].setList(self.list)

	def timerTick(self):
		if self.execing:
			self.timeout -= 1
			self["text"].setText(self.text + " in %d seconds." %self.timeout)
			if self.timeout == 0:
				self.timer.stop()
				self.timerRunning = False
				self.timeoutCallback()

	def move(self, direction):
		if self.close_on_any_key:
			self.close(True)
		self["list"].instance.moveSelection(direction)
		if self.list:
			self["selectedChoice"].setText(self["list"].getCurrent()[0])
#		self.stopTimer()

	def timeoutCallback(self):
		self.close(False)

remotecontrolcodeinit = RemoteControlCodeInit()

def Plugins(**kwargs):
	return []
