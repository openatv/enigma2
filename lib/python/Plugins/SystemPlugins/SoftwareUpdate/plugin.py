from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ScrollLabel import ScrollLabel
from Components.GUIComponent import *
from Components.MenuList import MenuList
from Components.Input import Input
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Screens.ImageWizard import ImageWizard

import os

class UpdatePluginMenu(Screen):
	skin = """
		<screen position="200,100" size="300,250" title="Update..." >
			<widget name="menu" position="10,10" size="290,175" scrollbarMode="showOnDemand" />
		</screen>"""
		
	def __init__(self, session, args = 0):
		self.skin = UpdatePluginMenu.skin
		Screen.__init__(self, session)
		
		self.menu = args
		
		list = []
		if self.menu == 0:
			list.append((_("Image-Upgrade"), "image"))
			list.append((_("Online-Upgrade"), "upgrade"))
			list.append((_("Advanced"), "advanced"))
		elif self.menu == 1:
			list.append((_("Choose source"), "source"))
			list.append((_("Packet management"), "ipkg"))
			list.append((_("Settings"), "setup"))
		
		self["menu"] = MenuList(list)
				
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"], 
		{
			"ok": self.go,
			"back": self.close,
		}, -1)
		
	def go(self):
		if self.menu == 0:
			if (self["menu"].l.getCurrentSelection()[1] == "image"):
				self.session.open(ImageWizard)
			if (self["menu"].l.getCurrentSelection()[1] == "upgrade"):
				self.session.openWithCallback(self.runUpgrade, MessageBox, _("Do you want to update your Dreambox?\nAfter pressing OK, please wait!"))
			if (self["menu"].l.getCurrentSelection()[1] == "advanced"):
				self.session.open(UpdatePluginMenu, 1)
		if self.menu == 1:
			if (self["menu"].l.getCurrentSelection()[1] == "source"):
				self.session.open(IPKGSource)
			elif (self["menu"].l.getCurrentSelection()[1] == "ipkg"):
				self.session.open(Ipkg)
			elif (self["menu"].l.getCurrentSelection()[1] == "setup"):
				self.session.open(MessageBox, _("Function not yet implemented"), MessageBox.TYPE_ERROR)
	
	def runUpgrade(self, result):
		if result:
			self.session.open(Console, title = "Upgrade running...", cmdlist = ["ipkg update", "ipkg upgrade -force-defaults -force-overwrite"], finishedCallback = self.runFinished)

	def runFinished(self):
		self.session.openWithCallback(self.reboot, MessageBox, _("Upgrade finished. Do you want to reboot your Dreambox?"), MessageBox.TYPE_YESNO)
		
	def reboot(self, result):
		if result is None:
			return
		if result:
			quitMainloop(3)

class IPKGSource(Screen):
	skin = """
		<screen position="100,100" size="550,60" title="IPKG source" >
			<widget name="text" position="0,0" size="550,25" font="Regular;20" />
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = IPKGSource.skin
		Screen.__init__(self, session)
		
		fp = file('/etc/ipkg/official-feed.conf', 'r')
		sources = fp.readlines()
		fp.close()
		
		self["text"] = Input(sources[0], maxSize=False, type=Input.TEXT)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions"], 
		{
			"ok": self.go,
			"back": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
	def go(self):
		fp = file('/etc/ipkg/official-feed.conf', 'w')
		fp.write(self["text"].getText())
		fp.close()
		self.close()
		
	def keyLeft(self):
		self["text"].left()
	
	def keyRight(self):
		self["text"].right()
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		self["text"].number(number)

RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

def PacketEntryComponent(packet):
	res = [ packet ]
	
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0,250, 30, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, packet[0]))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 250, 0, 200, 30, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, packet[1]))
	res.append((eListboxPythonMultiContent.TYPE_TEXT, 450, 0, 100, 30, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, packet[2]))
	return res

class PacketList(GUIComponent):
	def __init__(self, list):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setList(list)
		self.l.setFont(0, gFont("Regular", 20))
		self.l.setFont(1, gFont("Regular", 18))
	
	def getCurrent(self):
		return self.l.getCurrentSelection()
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(30)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

	def invalidate(self):
		self.l.invalidate()

class Ipkg(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="IPKG upgrade..." >
			<widget name="list" position="0,0" size="550,400" scrollbarMode="showOnDemand" />
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = Ipkg.skin
		Screen.__init__(self, session)
	
		list = []
		self.list = list
		self.fillPacketList()

		self["list"] = PacketList(self.list)
				
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.close,
			"back": self.close
		}, -1)
		

	def fillPacketList(self):
		lines = os.popen("ipkg list", "r").readlines()
		packetlist = []
		for x in lines:
			split = x.split(' - ')
			packetlist.append([split[0].strip(), split[1].strip()])
		
		lines = os.popen("ipkg list_installed", "r").readlines()
		
		installedlist = {}
		for x in lines:
			split = x.split(' - ')
			installedlist[split[0].strip()] = split[1].strip()
		
		for x in packetlist:
			status = ""
			if installedlist.has_key(x[0]):
				if installedlist[x[0]] == x[1]:
					status = "installed"
				else:
					status = "upgradable"
			self.list.append(PacketEntryComponent([x[0], x[1], status]))
		
	def go(self):
		if self.update:
			self.session.openWithCallback(self.doUpdate, MessageBox, _("Do you want to update your Dreambox?\nAfter pressing OK, please wait!"))		
		else:
			self.close()
	
	def doUpdateDelay(self):
		lines = os.popen("ipkg update && ipkg upgrade", "r").readlines()
		string = ""
		for x in lines:
			string += x
		self["text"].setText(_("Updating finished. Here is the result:") + "\n\n" + string)
		self.update = False
			
	
	def doUpdate(self, val = False):
		if val == True:
			self["text"].setText(_("Updating... Please wait... This can take some minutes..."))
			self.delayTimer.start(0, 1)
		else:
			self.close()

def UpgradeMain(session, **kwargs):
	session.open(UpdatePluginMenu)

def Plugins(**kwargs):
	return PluginDescriptor(name="Softwareupdate", description="Updates your receiver's software", icon="update.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=UpgradeMain)
