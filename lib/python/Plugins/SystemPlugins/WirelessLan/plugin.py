from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.GUIComponent import *
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText


from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Network import Network

from Plugins.Plugin import PluginDescriptor

from Wlan import Wlan, WlanList, wpaSupplicant

plugin_path = "/usr/lib/enigma2/python/Plugins/SystemPlugins/WirelessLan"

class WlanSelection(Screen):
	skin = """
	<screen position="70,138" size="610,300" title="Choose a Wireless Network" >
		<widget name="list" position="10,10" size="580,200" scrollbarMode="showOnDemand" />
		
		<widget name="cancel" position="10,255" size="140,40" pixmap="~/key-red.png" zPosition="1" transparent="1" alphatest="on" />
		<widget name="select" position="160,255" size="140,40" pixmap="~/key-green.png" zPosition="1" transparent="1" alphatest="on" />
		<widget name="rescan" position="310,255" size="140,40" pixmap="~/key-yellow.png" zPosition="1" transparent="1" alphatest="on" />
		<widget name="skip" position="460,255" size="140,40" pixmap="~/key-blue.png" zPosition="1" transparent="1" alphatest="on" />
		
		<widget name="canceltext" position="10,255" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />		
		<widget name="selecttext" position="160,255" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="#FFFFFF" />
		<widget name="rescantext" position="310,255" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="#FFFFFF" />
		<widget name="skiptext" position="460,255" size="140,40" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" foregroundColor="#FFFFFF" />
	</screen>
	"""
	def __init__(self, session, args = None):
	
		self.skin = WlanSelection.skin
		self.session = session
		Screen.__init__(self, session)
		
		self.list = []
				
		self["list"] = WlanList(self.session)
		self.skin_path = plugin_path
		
		self["cancel"] = Pixmap()
		self["select"] = Pixmap()
		self["rescan"] = Pixmap()
		self["skip"] = Pixmap()
		
		
		self["canceltext"] = Label(_("Cancel"))
		self["selecttext"] = Label(_("Select"))
		self["rescantext"] = Label(_("Rescan"))
		self["skiptext"] = Label(_("Skip"))
			
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "EPGSelectActions"],
		{
			"ok": self.select,
			"back": self.exit,
#			"up": self.up,
#			"down": self.down,
		}, -1)
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
		 	"red": self.exit,
			"green": self.select,
			"yellow": self.rescan,
			"blue": self.skip,
		})
	
	def select(self):
		cur = self["list"].getCurrent()
		if cur:
			ret = (self.session, cur)
		else:
			ret = (self.session, None)
		self.close(ret)
	
	def rescan(self):
		self["list"].reload()
	
	def skip(self):
		self.close( (self.session, None) )
	
	def exit(self):
		self.close( (None ,) )

class WlanConfiguration(ConfigListScreen, Screen):
	skin = """
		<screen position="76,138" size="600,300" title="Wireless Network Configuration" >
			<widget name="interface" position="10,10" size="580,30" font="Regular;24" valign="center" />
			<widget name="config" position="10,60" size="580,150" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="100,260" size="400,30" font="Regular;23" valign="center" halign="center" />	
		</screen>
	"""
	
	def __init__(self, session, essid = None, encrypted = False, iface = "wlan0"):
		
		Screen.__init__(self, session)		
		self.skin = WlanConfiguration.skin
		
		self.iface = iface
		self.list = []
		self.ws = wpaSupplicant()
		
		self["introduction"] = Label(_("Press OK to activate the settings."))
		self["interface"] = Label(_("Interface: ")+self.iface)
		
		if essid is None:
			self.ws.loadConfig()
		
		else:
			config.plugins.wlan.essid.value = essid
			config.plugins.wlan.encryption.enabled.value = True
			
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
		}, -2)
		
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
	
	def createSetup(self):

		self.list = [ ]
						
		self.list.append(getConfigListEntry(_("Network SSID"), config.plugins.wlan.essid))
		self.list.append(getConfigListEntry(_("Encryption"), config.plugins.wlan.encryption.enabled))
		
		if config.plugins.wlan.encryption.enabled.value:
			self.list.append(getConfigListEntry(_("Encryption Type"), config.plugins.wlan.encryption.type))
			self.list.append(getConfigListEntry(_("Encryption Key"), config.plugins.wlan.encryption.psk))
		
		self["config"].list = self.list
		self["config"].l.setList(self.list)
	
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def ok(self):
		self.ws.writeConfig()
		self.ws.restart(self.iface)
		self.close()

	def cancel(self):
		self.close()

def EntryChosen(parms):
	if parms[0]:
		session = parms[0]
		if parms[1] is not None:
			val = parms[1]
			essid = val[0]
			encrypted = val[2]
			iface = val[3]
			session.open(WlanConfiguration, essid, encrypted, iface)
		else:
			session.open(WlanConfiguration)

def WlanSelectionMain(session, iface):
	session.openWithCallback(EntryChosen, WlanSelection)

def WlanConfigurationMain(session, **kwargs):
	session.open(WlanConfiguration)

def callFunction(iface):
	w = Wlan()

	if iface in w.getWirelessInterfaces():
		return WlanSelectionMain	
	else:
		return None

def configStrings(iface):
	return "#Custom Configstring for "+iface
	
def Plugins(**kwargs):
	return PluginDescriptor(name=_("Wireless LAN"), description=_("Connect to a Wireless Network"), where = PluginDescriptor.WHERE_NETWORKSETUP, fnc={"ifaceSupported": callFunction, "configStrings": configStrings, "menuEntryName": lambda x: _("Wlan Configuartion Utility")})
	