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
import vuplusauthenticity
import os
import socket
import urllib2

default_email_address = "Please input your E-mail address"
config.plugins.vuplusauthenticity = ConfigSubsection()
config.plugins.vuplusauthenticity.sn_a = NoSave(ConfigSelection(default = "MSA", choices = [ ("MSA", _("MSA")), ("MA", _("MA")), ("MB", _("MB")), ("MC", _("MC")), ("MD", _("MD")), ("ME", _("ME")), ("MF", _("MF")), ("MG", _("MG")), ("MH", _("MH"))] ))
config.plugins.vuplusauthenticity.sn_b = NoSave(ConfigInteger(default = 0,  limits = (1, 999999999)))
config.plugins.vuplusauthenticity.sn_b_msa = NoSave(ConfigInteger(default = 0,  limits = (1, 9999999)))
config.plugins.vuplusauthenticity.email = NoSave(ConfigText(default = default_email_address, visible_width = 50, fixed_size = False))

GENUINE_MESSAGES={
		-6 : "UNEXPECTED ERROR(2).",
		-5 : "INVALID SERIAL NUMBER.",
		-4 : " Connect to server failed, \nplease check your network configuration and retry.",
		-3 : "UNEXPECTED ERROR(1).",
		-2 : "DEVICE OPEN ERROR.",
		-1 : "AUTHENTICATION FAILED.",
		0 : "AUTHENTICATION SUCCESS."
}

class VuplusAuthenticity(Screen, ConfigListScreen):
	skin = 	"""
		<screen name="VuplusAuthenticity" position="center,center" size="600,320" title="Return the Love Event (only for genuine box)">
			<ePixmap pixmap="skin_default/buttons/red.png" position="140,15" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="320,15" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="140,15" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="320,15" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="config" zPosition="2" position="10,70" size="580,80" scrollbarMode="showOnDemand" transparent="1" />
			<widget name="text1" position="10,160" size="580,50" font="Regular;32" halign="center" valign="center"/>
			<widget name="text2" position="10,220" size="580,100" font="Regular;18" halign="center" valign="center"/>
		</screen>
		"""
	def __init__(self,session):
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
		self.requestauth_timer = eTimer()
		self.requestauth_timer.callback.append(self.requestauth)

	def checkKernelVer(self):
		KVer = os.uname()[2]
		if float(KVer[:3]) < 3.1:
			self.checkTimer.start(0,True)

	def invalidKVer(self):
		self.session.openWithCallback(self.close, MessageBox, _("For use this plugin, you must update the kernel version to 3.1 or later"), MessageBox.TYPE_ERROR)

	def createSetup(self):
		self.list = []
		self.sn_aEntry = getConfigListEntry(_("1-1. Serial Number (The first two or three letters of SN)"), config.plugins.vuplusauthenticity.sn_a)
		if config.plugins.vuplusauthenticity.sn_a.value == "MSA":
			self.sn_bEntry = getConfigListEntry(_("1-2. Serial Number (The remaining numbers of SN)"), config.plugins.vuplusauthenticity.sn_b_msa)
		else:
			self.sn_bEntry = getConfigListEntry(_("1-2. Serial Number (The remaining numbers of SN)"), config.plugins.vuplusauthenticity.sn_b)
		self.emailEntry = getConfigListEntry(_("2. Contact"), config.plugins.vuplusauthenticity.email)
		self.list.append( self.sn_aEntry )
		self.list.append( self.sn_bEntry )
		self.list.append( self.emailEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def confirmValidSN(self):
		if config.plugins.vuplusauthenticity.sn_a.value == 'MSA':
			sn_length = 7
			sn = str(config.plugins.vuplusauthenticity.sn_b_msa.value)
		else:
			sn_length = 9
			sn = str(config.plugins.vuplusauthenticity.sn_b.value)
		if len(sn) > sn_length or sn == '0':
			return False
		else:
			while(len(sn)<sn_length):
				sn = '0'+sn
			if sn_length == 9:
				if int(sn[:2]) not in range(28) or int(sn[2:4]) not in range(1,53) or int(sn[-5:]) == 0:
					return False
				else:
					return True
			else:
				if int(sn[:2]) not in range(1,53) or int(sn[-5:]) == 0:
					return False
				else:
					return True

	def displayResult(self, ret = -5):
		global GENUINE_MESSAGES
		self["text1"].setText(GENUINE_MESSAGES[ret])
		self["key_green"].text = _("Restart")

	def Start(self):
		self["text1"].setText("WAITING......")
		msg = "Please note that you agree to send software information of the box by applying the event.\nThe collected data will be used in a form that does not personally identify you."
		self.session.openWithCallback(self.userConfirmCallback, MessageBoxGenuine, _(msg), MessageBox.TYPE_YESNO)

	def userConfirmCallback(self,ret):
		if ret:
			self.requestauth_timer.start(0,True)
		else:
			self["text1"].setText("Press green button to start")

	def getModel(self):
		if fileExists("/proc/stb/info/vumodel"):
			vumodel = open("/proc/stb/info/vumodel")
			info=vumodel.read().strip()
			vumodel.close()
			return info
		else:
			return "unknown"

	def requestauth(self):
		if(not self.confirmValidSN()):
			self.displayResult(-5)
			return
		if config.plugins.vuplusauthenticity.sn_a.value == 'MSA':
			sn_length = 7
			sn_b = str(config.plugins.vuplusauthenticity.sn_b_msa.value)
		else:
			sn_length = 9
			sn_b = str(config.plugins.vuplusauthenticity.sn_b.value)
		while(len(sn_b)<sn_length):
			sn_b = '0'+sn_b
		serial_number = config.plugins.vuplusauthenticity.sn_a.value + sn_b
		model =self.getModel()
		email = config.plugins.vuplusauthenticity.email.value
		if len(email) == 0 or email == default_email_address:
			email = "none"
		try:
			ret=vuplusauthenticity.requestauth(serial_number, model, email)
			self.displayResult(ret)
		except :
			self.displayResult(-6)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keyExit(self):
		self.close()

class MessageBoxGenuine(MessageBox):
	skin = """
		<screen name="MessageBoxGenuine" position="center,center" size="600,10" title="Message">
		<widget name="text" position="65,8" size="420,0" font="Regular;22" />
		<widget name="ErrorPixmap" pixmap="Vu_HD/icons/input_error.png" position="5,5" size="53,53" alphatest="blend" />
		<widget name="QuestionPixmap" pixmap="Vu_HD/icons/input_question.png" position="5,5" size="53,53" alphatest="blend" />
		<widget name="InfoPixmap" pixmap="Vu_HD/icons/input_info.png" position="5,5" size="53,53" alphatest="blend" />
		<widget name="list" position="100,100" size="380,375" transparent="1" />
		<applet type="onLayoutFinish">
# this should be factored out into some helper code, but currently demonstrates applets.
from enigma import eSize, ePoint

orgwidth = self.instance.size().width()
orgpos = self.instance.position()
textsize = self[&quot;text&quot;].getSize()

# y size still must be fixed in font stuff...
textsize = (textsize[0] + 50, textsize[1] + 50)
offset = 0
if self.type == self.TYPE_YESNO:
	offset = 60
wsizex = textsize[0] + 60
wsizey = textsize[1] + offset
if (280 &gt; wsizex):
	wsizex = 280
wsize = (wsizex, wsizey)


# resize
self.instance.resize(eSize(*wsize))

# resize label
self[&quot;text&quot;].instance.resize(eSize(*textsize))

# move list
listsize = (wsizex, 50)
self[&quot;list&quot;].instance.move(ePoint(0, textsize[1]))
self[&quot;list&quot;].instance.resize(eSize(*listsize))

# center window
newwidth = wsize[0]
self.instance.move(ePoint(orgpos.x() + (orgwidth - newwidth)/2, orgpos.y()))
		</applet>
	</screen>"""
	def __init__(self, session, text, type = MessageBox.TYPE_YESNO, timeout = -1, close_on_any_key = False, default = True, enable_input = True, msgBoxID = None):
		MessageBox.__init__(self,session, text, type, timeout, close_on_any_key, default, enable_input,msgBoxID)
		if type == MessageBox.TYPE_YESNO:
			self.list = [ (_("Agree"), 0), (_("Exit"), 1) ]
			self["list"].setList(self.list)

def main(session, **kwargs):
	session.open(VuplusAuthenticity)

def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Return the Love Event"), description="Don't lose the chance to get the gift.", where = PluginDescriptor.WHERE_PLUGINMENU, needsRestart = False, fnc=main)]

