#
#  sundtek control center
#  coded by giro77
#
#
from Screens.Screen import Screen 
from Screens.Console import Console 
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.ActionMap import ActionMap
from Components.Input import Input
from Components.MenuList import MenuList
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSelection, configfile
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Tools.NumericalTextInput import NumericalTextInput
import os

# for localized texts
from . import _


## configs ################################################################

config.plugins.SundtekControlCenter = ConfigSubsection()
config.plugins.SundtekControlCenter.dvbtransmission = ConfigSelection(default="0", choices = [("0", _("DVB-S/SVB-S2")),("1", _("DVB-C")),("2", _("DVB-T"))])
config.plugins.SundtekControlCenter.autostart = ConfigYesNo(default=False)

config.plugins.SundtekControlCenter.usbnet = ConfigSubsection()
config.plugins.SundtekControlCenter.usbnet.selection = ConfigSelection(default="0", choices = [("0", _("via USB")),("1", _("via Network"))])
config.plugins.SundtekControlCenter.usbnet.networkip = ConfigText(default="0.0.0.0", visible_width = 50, fixed_size = False)

## version string #########################################################

sundtekcontrolcenter_version = "1.0.r2"

###########################################################################

class SundtekControlCenter(Screen, ConfigListScreen):
	skin = """
		<screen title="SundtekControlCenter" position="center,center" size="570,400" name="SundtekControlCenter">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget name="btt_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="btt_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="btt_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="btt_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" /> 
			<widget name="ok" position="10,292" zPosition="1" size="550,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget name="infos" position="10,316" zPosition="1" size="450,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget name="bouquets" position="10,340" zPosition="1" size="450,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget name="netservers" position="10,364" zPosition="1" size="450,40" font="Regular;20" halign="left" valign="center" transparent="1" />
			<widget name="config" position="100,100" size="370,200" scrollbarMode="showOnDemand" zPosition="1"/>
			<ePixmap position="460, 350" size="100,40" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/plugin.png" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, [])
		self.updateSettingList()
		
		self["btt_red"] = Label(_("Back"))
		self["btt_green"] = Label(_("Setup"))
		self["btt_yellow"] = Label(_("Stop Tuner"))
		self["btt_blue"] = Label(_("Start Tuner"))
		self["ok"] = Label(_("OK/ green = activate settings"))
		self["infos"] = Label(_("Info = show tuner informations"))
		self["bouquets"] = Label(_("Bouquet + = install or update driver"))
		self["netservers"] = Label(_("Bouquet - = scan for IPTV server addresses"))
		self["actions"] = ActionMap(["OkCancelActions", "ChannelSelectBaseActions", "ColorActions","ChannelSelectEPGActions"], 
		{
			"ok": self.save,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"yellow": self.tunerstop,
			"blue": self.tunerstart,
			"showEPGList": self.dvbinfo,
			"nextBouquet": self.fetchsundtekdriver,
			"prevBouquet": self.scannetwork,
		},-2)
		
		self.onLayoutFinish.append(self.layoutFinished)
	
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.updateSettingList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.updateSettingList()
		
	def updateSettingList(self):
		list = [] ### creating list
		list.append(getConfigListEntry(_("DVB Transmission Way"), config.plugins.SundtekControlCenter.dvbtransmission))
		list.append(getConfigListEntry(_("USB/Network"), config.plugins.SundtekControlCenter.usbnet.selection))
		
		if config.plugins.SundtekControlCenter.usbnet.selection.value == "1": ## if networking then add ip mask to list
			sublist = [
				getConfigListEntry(_("Network IP"), config.plugins.SundtekControlCenter.usbnet.networkip)
			]
			
			list.extend(sublist)
		
		list.append(getConfigListEntry(_("Autostart"), config.plugins.SundtekControlCenter.autostart))
		
		self["config"].list = list
		self["config"].l.setList(list)
		
	def layoutFinished(self):
		self.setTitle(_("Sundtek Control Center"))
		
	def fetchsundtekdriver(self):
		self.session.openWithCallback(self.disclaimer, MessageBox, _("Sundtek legal notice:\nThis software comes without any warranty, use it at your own risk?"), MessageBox.TYPE_YESNO)

	def disclaimer(self, result): 
		if result:
			self.prompt("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/sundtekinstall.sh")

	def save(self):
		for x in self["config"].list:
			x[1].save()
			
		configfile.save()
		self.setsettings()
		
	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close(False, self.session)

####################################################################

	def setsettings(self):
		if (not os.path.exists("/usr/sundtek")):
			#maybe the driver is not or installed incorrect.
			self.session.openWithCallback(self.installdriverrequest, MessageBox, _("It seems the sundtek driver is not installed or not installed properly. Install the driver now?"), MessageBox.TYPE_YESNO)
			
		else: # driver is installed
			### disable autostart
			if config.plugins.SundtekControlCenter.autostart.value == False:
				self.prompt("/usr/sundtek/sun_dvb.sh noautostart")
				
			if config.plugins.SundtekControlCenter.usbnet.selection.value == "1":
				### save the IP for networking
				f=open("/etc/sundtek.net", "w")
				networkingip=config.plugins.SundtekControlCenter.usbnet.networkip.value+"\n"
				networkingip.lstrip().rstrip()
				f.writelines('REMOTE_IPTV_SERVER='+networkingip)
				f.close()
				
				if config.plugins.SundtekControlCenter.autostart.value == True:
					self.prompt("/usr/sundtek/sun_dvb.sh enable_net")
				
			else:
				if config.plugins.SundtekControlCenter.dvbtransmission.value == "0":
					### dvb-s/ dvb-s2
					if config.plugins.SundtekControlCenter.autostart.value == True:
						### enable autostart
						self.prompt("/usr/sundtek/sun_dvb.sh enable_s2")
						
				elif config.plugins.SundtekControlCenter.dvbtransmission.value == "1":
					### dvb-c
					if config.plugins.SundtekControlCenter.autostart.value == True:
						### enable autostart
						self.prompt("/usr/sundtek/sun_dvb.sh enable_c")
				else:
					### dvb-t
					if config.plugins.SundtekControlCenter.autostart.value == True:
						### enable autostart
						self.prompt("/usr/sundtek/sun_dvb.sh enable_t")
	
	def tunerstart(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.setsettings()
		
		if (os.path.exists("/usr/sundtek/mediasrv")) and (os.path.exists("/usr/sundtek/mediaclient")) and (os.path.exists("/usr/sundtek/sun_dvb.sh")):
			if config.plugins.SundtekControlCenter.dvbtransmission.value == "0":
				### dvb-s/ dvb-s2
				self.prompt("/usr/sundtek/sun_dvb.sh start_s2")
			elif config.plugins.SundtekControlCenter.dvbtransmission.value == "1":
				### dvb-c
				self.prompt("/usr/sundtek/sun_dvb.sh start_c")
			else:
				### dvb-t
				self.prompt("/usr/sundtek/sun_dvb.sh start_t")
			if config.plugins.SundtekControlCenter.usbnet.selection.value == "1":
				### networking
				self.prompt("/usr/sundtek/sun_dvb.sh start_net")
			
	def tunerstop(self):
		self.prompt("/usr/sundtek/sun_dvb.sh stop")
		
	def dvbinfo(self):
		self.prompt("/usr/sundtek/sun_dvb.sh info")
		
	def scannetwork(self):
		if os.path.exists("/usr/sundtek/mediaclient"):
			networkingscan = os.popen("/usr/sundtek/mediaclient --scan-network", "r").read()
			#networkingscan = os.popen("cat /usr/sundtek/scan.txt", "r").read()
			networkingip = networkingscan.split()[20]
			if networkingip == "-":
				self.session.open(MessageBox, _("No IPTV media server found"), MessageBox.TYPE_INFO)
			else:
				self.session.openWithCallback(self.usenetip, MessageBox, networkingscan+_("\n\nUse following address as IPTV media server?\n")+networkingip, MessageBox.TYPE_YESNO)

	def usenetip(self, result): 
		if result:
			config.plugins.SundtekControlCenter.usbnet.selection.value = "1"
			config.plugins.SundtekControlCenter.usbnet.networkip.value = os.popen("/usr/sundtek/mediaclient --scan-network", "r").read().split()[20]
			self.updateSettingList()

	def installdriverrequest(self, result):
		if result:
			self.session.openWithCallback(self.disclaimer, MessageBox, _("Sundtek legal notice:\nThis software comes without any warranty, use it at your own risk?"), MessageBox.TYPE_YESNO)
			
	def prompt(self, com):
		self.session.open(Console,_("comand line: %s") % (com), ["%s" %com])
#
###################################################################

def main(session, **kwargs):
	session.open(SundtekControlCenter)

def SundtekControlCenterStart(menuid):
	if menuid != "scan": 
		return [ ]
	return [(_("Sundtek Control Center"), main, "Sundtek Control Center", 50)]

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	list = [
		PluginDescriptor(name=_("sundtek control center plugin"), description =_("installs the sundtek driver and runs related shellscripts"), where = PluginDescriptor.WHERE_MENU, fnc=SundtekControlCenterStart),
		PluginDescriptor(name=_("sundtek control center plugin"), description =_("installs the sundtek driver and runs related shellscripts"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
		PluginDescriptor(name=_("sundtek control center plugin"), description =_("installs the sundtek driver and runs related shellscripts"), where = PluginDescriptor.WHERE_PLUGINMENU,icon="plugin.png", fnc=main)
		]
	return list
