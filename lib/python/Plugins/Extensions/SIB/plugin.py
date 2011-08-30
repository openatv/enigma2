from Screens.Screen import Screen
from Screens.InfoBarGenerics import InfoBarPlugins
from Screens.InfoBar import InfoBar
from Screens.MessageBox import MessageBox
from Screens.EpgSelection import EPGSelection
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Tools.Directories import fileExists
if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/MerlinEPG/plugin.pyo") or fileExists("/usr/lib/enigma2/python/Plugins/Extensions/MerlinEPG/plugin.pyc"):
	from Plugins.Extensions.MerlinEPG.plugin import Merlin_PGII
	MerlinEPGaviable = True
else:
	MerlinEPGaviable = False
from enigma import eTimer, ePoint


GP2test = False

SIBbase__init__ = None
SIB_StartOnlyOneTime = False
VZ_MODE = "-1"


config.plugins.SecondInfoBar  = ConfigSubsection()
config.plugins.SecondInfoBar.TimeOut = ConfigInteger(default = 6, limits = (0, 30))
config.plugins.SecondInfoBar.Mode = ConfigSelection(default="sib", choices = [
				("nothing", _("Not enabled")),
				("sib", _("Show Second-InfoBar")),
				("onlysib", _("Show ONLY Second-InfoBar")),
				("epglist", _("Show EPG-List")),
				("subsrv", _("Show Subservices"))
				])
config.plugins.SecondInfoBar.GP2pass = ConfigYesNo(default = True)
config.plugins.SecondInfoBar.HideNormalIB = ConfigYesNo(default = False)



def Plugins(**kwargs):
	return [PluginDescriptor(name="SecondInfoBar", where=PluginDescriptor.WHERE_MENU, fnc=SIBsetup),
			PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = SIBautostart)]



def SIBsetup(menuid):
	return [ ]
	
def openSIBsetup(session, **kwargs):
	session.open(SIBsetupScreen)



class SIBsetupScreen(ConfigListScreen, Screen):
	skin = """
		<screen name="SIBsetupScreen" position="center,center" size="600,340" title="Second-InfoBar setup">
			<eLabel font="Regular;20" foregroundColor="#00ff4A3C" halign="center" position="20,308" size="120,26" text="Cancel"/>
			<eLabel font="Regular;20" foregroundColor="#0056C856" halign="center" position="165,308" size="120,26" text="Save"/>
			<widget name="config" position="5,5" scrollbarMode="showOnDemand" size="590,300"/>
		</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.MustRestart = (config.plugins.SecondInfoBar.Mode.value == "onlysib")
		list = []
		list.append(getConfigListEntry(_("Second-InfoBar working mode"), config.plugins.SecondInfoBar.Mode))
		list.append(getConfigListEntry(_("Second-InfoBar Timeout (in Sec. , 0 = wait for OK)"), config.plugins.SecondInfoBar.TimeOut))
		list.append(getConfigListEntry(_("Hide Infobar if Second-InfoBar shown"), config.plugins.SecondInfoBar.HideNormalIB))
		ConfigListScreen.__init__(self, list)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
									{
									"red": self.exit, 
									"green": self.save,
									"cancel": self.exit
									}, -1)

	def exit(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def save(self):
		for x in self["config"].list:
			x[1].save()
		if (self.MustRestart ^ (config.plugins.SecondInfoBar.Mode.value == "onlysib")):
			self.session.open(MessageBox, _("GUI needs a restart to apply the new settings !!!"), MessageBox.TYPE_INFO)
		self.close()



def SIBautostart(reason, **kwargs):
	global SIBbase__init__
	if "session" in kwargs:
		if SIBbase__init__ is None:
			SIBbase__init__ = InfoBarPlugins.__init__
		InfoBarPlugins.__init__ = InfoBarPlugins__init__
		InfoBarPlugins.switch = switch
		InfoBarPlugins.swOff = swOff



def InfoBarPlugins__init__(self):
	global SIB_StartOnlyOneTime
	global VZ_MODE
	if not SIB_StartOnlyOneTime: 
		SIB_StartOnlyOneTime = True
		if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/plugin.pyo") or fileExists("/usr/lib/enigma2/python/Plugins/Extensions/VirtualZap/plugin.pyc"):
			try:
				VZ_MODE = config.plugins.virtualzap.mode.value
			except:
				VZ_MODE = "-1"
		else:
			VZ_MODE = "-1"
		if VZ_MODE == "1":
			self["SIBActions"] = ActionMap(["SIBwithVZActions"],{"ok_but": self.switch,"exit_but": self.swOff}, -1)
		else:
			self["SIBActions"] = ActionMap(["SIBActions"],{"ok_but": self.switch,"exit_but": self.swOff}, -1)
		self.SIBtimer = eTimer()
		self.SIBtimer.callback.append(self.swOff)
		self.SIBdialog = self.session.instantiateDialog(SecondInfoBar)
		if config.plugins.SecondInfoBar.Mode.value == "onlysib":
			self.onHide.append(lambda: self.SIBdialog.hide())
			self.onShow.append(lambda: self.SIBdialog.show())
		def CheckSIBtimer():
			if self.SIBtimer.isActive():
				self.SIBtimer.stop()
		self.SIBdialog.onHide.append(CheckSIBtimer)
	else:
		InfoBarPlugins.__init__ = InfoBarPlugins.__init__
		InfoBarPlugins.switch = None
		InfoBarPlugins.swOff = None
	SIBbase__init__(self)



def switch(self):
	if isinstance(self,InfoBar):
		if config.plugins.SecondInfoBar.Mode.value == "sib":
			if not self.shown and not self.SIBdialog.shown:
				self.toggleShow()
			elif self.shown and not self.SIBdialog.shown:
				if config.plugins.SecondInfoBar.HideNormalIB.value:
					self.hide()
				self.SIBdialog.show()
				SIBidx = config.plugins.SecondInfoBar.TimeOut.value
				if (SIBidx > 0):
					self.SIBtimer.start(SIBidx*1000, True)
			elif not self.shown and self.SIBdialog.shown:
				self.SIBdialog.hide()
			elif self.shown and self.SIBdialog.shown:
				self.hide()
				self.SIBdialog.hide()
			else:
				self.toggleShow()
		elif config.plugins.SecondInfoBar.Mode.value == "epglist":
			if self.shown:
				if MerlinEPGaviable:
					self.session.open(Merlin_PGII, self.servicelist)
				else:
					self.session.open(EPGSelection, self.session.nav.getCurrentlyPlayingServiceReference())
			else:
				self.toggleShow()
		elif config.plugins.SecondInfoBar.Mode.value == "subsrv":
			if self.shown:
				service = self.session.nav.getCurrentService()
				subservices = service and service.subServices()
				if subservices.getNumberOfSubservices()>0:
					self.subserviceSelection()
				else:
					self.toggleShow()
			else:
				self.toggleShow()
		else:
			self.toggleShow()



def swOff(self):
	if isinstance(self,InfoBar):
		if not(self.shown or self.SIBdialog.shown) and (VZ_MODE == "2"):
			self.newHide()
		else:
			self.hide()
			self.SIBdialog.hide()



class SecondInfoBar(Screen):
	skin = """
		<screen flags="wfNoBorder" name="SecondInfoBar" position="center,350" size="720,200" title="Second Infobar">
			<eLabel text="Your skin do not support SecondInfoBar !!!" position="0,0" size="720,200" font="Regular;22" halign="center" valign="center"/>
		</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SecondInfoBar.skin

	def __onShow(self):
		if GP2test and config.plugins.SecondInfoBar.GP2pass.value:
			GPpos = BPInfoBarutils.INFOBAR_POSITION
			GPoffset_x = Cbpconfig.getInstance().getParaInt("infobar_offset_x")
			GPoffset_y = Cbpconfig.getInstance().getParaInt("infobar_offset_y")
			px = GPpos.x()
			py = GPpos.y()
			self.instance.move(ePoint(px+GPoffset_x, py+GPoffset_y))








