from Plugins.Plugin import PluginDescriptor

from Components.ActionMap import ActionMap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.Sources.List import List
from enigma import eTimer
from Components.Pixmap import Pixmap
from socket import gethostbyname, gaierror
import socket
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from Plugins.Extensions.RemoteIPTVClient.RemoteTunerServer import *
from boxbranding import getMachineBrand, getMachineName
from os import system as os_system

def DoesHostExist(host, port):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(1)
		s.connect((host, port))
		s.close()
	except:
		print "[RemoteTunerScanner] Can not connect to %s on %d port" % (host, port)
		return False
	      
	return True

class RemoteTunerScanner(Screen):
	skin = """
		<screen name="RemoteTunerScanner" position="center,center" size="700,560" title="RemoteTunerScanner" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_blue" render="Label"  position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="list" render="Listbox" position="10,50" size="680,150" zPosition="2" scrollbarMode="showOnDemand" transparent="1">
				<convert type="TemplatedMultiContent">
				    {"template": [
				    MultiContentEntryText(pos = (70, 0), size = (620, 60), font=0, text = 0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER),
				    MultiContentEntryPixmapAlphaBlend(pos = (6, 6), size = (50, 50), png = 1),
				    ],
				    "fonts": [gFont("Regular", 24),gFont("Regular", 20)],
				    "itemHeight": 60
				    }
				</convert>
			</widget>
		</screen>"""
  
	def __init__(self, session):
		Screen.__init__(self, session)
		self.list = []
		self["list"] = List(self.list)
		self["key_red"] = Label(_("Close"))
		self["key_green"] = Label(_("Connect"))
		self["key_yellow"] = Label(_("Refresh"))
		self["key_blue"] = Label(_("Manual"))
		
		statusTxt =  _("Here is a list of detected %s IPTV servers. You can choose one to connect Your %s %s to retrive channel list and watch them by network, without SAT, CABLE or TERRESTRIAL signal") % (getMachineBrand(), getMachineBrand(), getMachineName())
		self["text"] = Label(statusTxt)
		
		self.updateList()
		self.stopService()
		
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			'ok': self.save,
			'back': self.close,
			'red': self.Exit,
			'yellow': self.Yellow,
			'green': self.Green,
			'blue': self.Blue
		}, -1)

	def detectServers(self):
		print "[RemoteTunerScanner] detectServers"
		self.list = []
		
		hostnames_to_check = ["xpeedlx3", "atemio6200", "beyonwizt2", "beyonwizt3", "beyonwizt4"] # List of hostnames for detection, not sure if it good way, but I guess not many people are changing their hostnames
		
		png = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/RemoteIPTVClient/icons/found.png")
		
		for x in hostnames_to_check:
			try:
				if DoesHostExist(x,21):
					host = gethostbyname(x)
					print "[RemoteTunerScanner] Host " + x + " can be connected by port 21 so We can retrive channel list"
					res = ("Remote server: " + x + " (" + host +")", png, host)
					self.list.append(res)
				
			except gaierror:
				print "[RemoteTunerScanner] Oops, hostname does not exist in this LAN, seems it still exist as hostname in your router"
				
		self.Timer.stop() #stopTimer
		
		if len(self.list) < 1:
			png = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/RemoteIPTVClient/icons/searching.png")
			statusTxt =  _("IPTV server are not found...Try to use manual setup")
			res = (statusTxt, png, "searching")
			self.list.append(res)
		
		self["list"].list = self.list

	def save(self):
		print "[RemoteTunerScanner] save"
		self.run()
	    
	def run(self):
		print "[RemoteTunerScanner] run"
		mysel = self["list"].getCurrent()
		if mysel:
			if mysel[2] != 'searching':
				user = "root" 
				password ="beyonwiz" # any will work
				iptable = []
				ip = mysel[2].strip().split(".")
				for x in ip:
					x=int(x)
					iptable.append(x)
				self.session.openWithCallback(self.Red, RemoteTunerServerEditor, iptable, user, password, 21, False)
			else:
				print "[RemoteTunerScanner] Still searching for the IP servers or did not find any"
	
	def stopService(self):
		self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
	        self.session.nav.stopService()
		os_system('/usr/bin/showiframe /usr/share/enigma2/black.mvi')
		
	def updateList(self):
		print "[RemoteTunerScanner] updateList"
		self.searchinglist = []
		
		png = LoadPixmap("/usr/lib/enigma2/python/Plugins/Extensions/RemoteIPTVClient/icons/searching.png")
		statusTxt =  _("Searching for %s IPTV servers...") % (getMachineBrand())
		res = (statusTxt, png, "searching") 
		
		self.searchinglist.append(res)
		
		self["list"].list = self.searchinglist
		
		self.Timer = eTimer()
		self.Timer.callback.append(self.detectServers)
		self.Timer.start(1000, False)

	def Exit(self):
		print "[RemoteTunerScanner] Exit from Plugin"
		self.session.nav.playService(self.oldref)
		self.close()
			
	def Red(self, ret = False):
		if ret:
			print "[RemoteTunerScanner] Red"
			self.session.nav.playService(self.oldref)
			self.close()

	def Green(self):
		print "[RemoteTunerScanner] Green"
		self.run()
   
	def Yellow(self):
		print "[RemoteTunerScanner] Yellow"
		self.updateList()

	def Blue(self):
		print "[RemoteTunerScanner] Blue"
		self.session.open(RemoteTunerServerEditor)

def main(session, **kwargs):
	session.open(RemoteTunerScanner)

def Plugins(**kwargs):
	l = []
	#l.append(PluginDescriptor(name=_("Remote IPTV Client"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=False, fnc=main))
	#l.append(PluginDescriptor(name=_("Remote IPTV Client"), where=PluginDescriptor.WHERE_PLUGINMENU, needsRestart=False, fnc=main))
	return l
