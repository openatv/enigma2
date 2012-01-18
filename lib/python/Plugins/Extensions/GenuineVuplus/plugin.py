from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigText, ConfigInteger,NoSave
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
from Screens.MessageBox import MessageBox
from enigma import eTimer
import genuinevuplus
import os
import socket
import urllib2

default_email_address = "Please input your E-mail address"
config.plugins.genuinevuplus = ConfigSubsection()
config.plugins.genuinevuplus.sn_a = NoSave(ConfigSelection(default = "MA", choices = [ ("MA", _("MA")), ("MB", _("MB")), ("MC", _("MC")), ("MD", _("MD")), ("ME", _("ME")), ("MF", _("MF")), ("MG", _("MG")), ("MH", _("MH"))] ))
config.plugins.genuinevuplus.sn_b = NoSave(ConfigInteger(default = 0,  limits = (1, 999999999)))
config.plugins.genuinevuplus.email = NoSave(ConfigText(default = default_email_address, visible_width = 50, fixed_size = False))

GENUINE_MESSAGES={
		-6 : "The server responded with an error message.",
		-5 : " Connect to server failed, \nplease check your network configuration and retry.",
		-4 : "UNEXPECTED ERROR.",
		-3 : "INVALID SERIAL NUMBER.",
		-2 : "DEVICE OPEN ERROR.",
		-1 : "AUTHENTICATION FAILED.",
		0 : "AUTHENTICATION SUCCESS."
}

class GenuineVuplus(Screen, ConfigListScreen):
	def __init__(self,session):
		if session.desktop.size().width() > 720:
			self.skin = """
			<screen name="GenuineVuplus" position="center,center" size="800,370" title="Genuine Vuplus">
			<ePixmap pixmap="Vu_HD/buttons/red.png" position="250,15" size="25,25" alphatest="on" />
			<ePixmap pixmap="Vu_HD/buttons/green.png" position="435,15" size="25,25" alphatest="on" />
			<widget source="key_red" render="Label" position="265,15" zPosition="1" size="140,25" font="Regular;24" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="450,15" zPosition="1" size="140,25" font="Regular;24" halign="center" valign="center" transparent="1" />
			<widget name="config" zPosition="2" position="80,70" size="640,80" scrollbarMode="showOnDemand" transparent="1" />
			<widget name="text1" position="0,165" size="800,90" font="Regular;32" halign="center" valign="center"/>
			<widget name="text2" position="100,260" size="600,110" font="Regular;24" halign="center" valign="center"/>
			</screen>"""

		else:
			self.skin="""<screen name="GenuineVuplus" position="center,center" size="600,320" title="Genuine Vuplus">
			<ePixmap pixmap="Vu_HD/buttons/red.png" position="170,15" size="25,25" alphatest="on" />
			<ePixmap pixmap="Vu_HD/buttons/green.png" position="355,15" size="25,25" alphatest="on" />
			<widget source="key_red" render="Label" position="185,15" zPosition="1" size="140,25" font="Regular;24" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="370,15" zPosition="1" size="140,25" font="Regular;24" halign="center" valign="center" transparent="1" />
			<widget name="config" zPosition="2" position="10,70" size="580,80" scrollbarMode="showOnDemand" transparent="1" />
			<widget name="text1" position="10,160" size="580,50" font="Regular;32" halign="center" valign="center"/>
			<widget name="text2" position="10,220" size="580,100" font="Regular;18" halign="center" valign="center"/>
			</screen>"""
		Screen.__init__(self,session)
		self.session = session
		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.Start,
			"cancel": self.keyExit,
			"red": self.keyExit,
			"green": self.Start,
		}, -2)
		self.genuine = None
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Start"))
		self["text1"]=Label("Press green button to start")
		self["text2"]=Label("With this plugin you can verify the authenticity of your Vu+.\nFor more information, please visit our website \nhttp://vuplus.com")
		self.createSetup()
		self.onLayoutFinish.append(self.checkKernelVer)
		self.checkTimer = eTimer()
		self.checkTimer.callback.append(self.invalidKVer)
		self.connectToServerTimer = eTimer()
		self.connectToServerTimer.callback.append(self.connectToServer)

	def checkKernelVer(self):
		KVer = os.uname()[2]
		if float(KVer[:3]) < 3.1:
			self.checkTimer.start(0,True)

	def invalidKVer(self):
		self.session.openWithCallback(self.close, MessageBox, _("For use this plugin, you must update the kernel version to 3.1 or later"), MessageBox.TYPE_ERROR)

	def createSetup(self):
		self.list = []
		self.sn_aEntry = getConfigListEntry(_("1-1. Serial Number (The first two letters of SN)"), config.plugins.genuinevuplus.sn_a)
		self.sn_bEntry = getConfigListEntry(_("1-2. Serial Number (The remaining numbers of SN)"), config.plugins.genuinevuplus.sn_b)
		self.emailEntry = getConfigListEntry(_("2. Contact"), config.plugins.genuinevuplus.email)
		self.list.append( self.sn_aEntry )
		self.list.append( self.sn_bEntry )
		self.list.append( self.emailEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def confirmValidSN(self):
		sn = str(config.plugins.genuinevuplus.sn_b.value)
		if len(sn) > 9:
			return False
		elif sn == '0':
			return False
		else:
			while(len(sn)<9):
				sn = '0'+sn
			if int(sn[:2]) not in range(28):
				return False
			elif int(sn[2:4]) not in range(1,53):
				return False
			elif int(sn[-5:]) == 0:
				return False
			else:
				return True

	def displayResult(self, ret = -5):
		global GENUINE_MESSAGES
		self["text1"].setText(GENUINE_MESSAGES[ret])
		self["key_green"].text = _("Restart")

	def Start(self):
		self["text1"].setText("WAITING......")
		if(not self.confirmValidSN()):
			self.displayResult(-3)
		else:
			try:
				ret=genuinevuplus.requestauth()
			except :
				self.displayResult(-4)
			if ret == 0 or ret == -1:
#				self.connectToServer(ret)
				self.genuine = ret
				self.connectToServerTimer.start(0,True)
			elif ret == -2:
				self.displayResult(-2)

	def getModel(self):
		if fileExists("/proc/stb/info/vumodel"):
			vumodel = open("/proc/stb/info/vumodel")
			info=vumodel.read().strip()
			vumodel.close()
			return info
		else:
			return "unknown"

	def connectToServer(self):
		sn_b = str(config.plugins.genuinevuplus.sn_b.value)
		for n in range(9-len(sn_b)):
			sn_b = '0'+sn_b
		serial_number = config.plugins.genuinevuplus.sn_a.value + sn_b

		model =self.getModel()

		email = config.plugins.genuinevuplus.email.value
		if len(email) == 0 or email == default_email_address:
			email = 'none'

		URL = "http://code.vuplus.com/genuine.php?serial=%s&yn=%s&model=%s&email=%s"%(serial_number, self.genuine == 0 and 'y' or self.genuine == -1 and 'n' or 'n' ,model, email)
#		print URL
		response = None
		retry = 0
		while 1:
			try:
				timeout = 10
				socket.setdefaulttimeout(timeout)
				response = urllib2.urlopen(URL)
				break
			except urllib2.URLError, e:
				if hasattr(e, 'reason'):
					print '[Genuine vuplus] Failed to reach a server.'
					print '[Genuine vuplus] Reason : ', e.reason
				elif hasattr(e, 'code'):
					print '[Genuine vuplus] The server could not fullfill the request.'
					print '[Genuine vuplus] Error code: ', e.code
				if retry == 0:
					print "[Genuine vuplus] retry..."
					retry = 1
				else:
					break
			except socket.timeout:
				print "[Genuine vuplus] Socket time out."
				if retry == 0:
					print "[Genuine vuplus] retry..."
					retry = 1
				else:
					break

		if response is not None:
			if response.read() == 'YES':
				self.displayResult(self.genuine)
			else:
				self.displayResult(-6)
		else:
			self.displayResult(-5)

	def keyExit(self):
		self.close()

def main(session, **kwargs):
	session.open(GenuineVuplus)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Genuine Vuplus"), description="Support for verifying the authenticity of your Vu+.", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)]

