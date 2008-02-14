from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eListbox, eTimer, gFont
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.GUIComponent import GUIComponent
from Plugins.Plugin import PluginDescriptor

from os import popen

class Upgrade(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="IPKG upgrade..." >
			<widget name="text" position="0,0" size="550,400" font="Regular;15" />
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = Upgrade.skin
		Screen.__init__(self, session)

		self["text"] = ScrollLabel(_("Please press OK!"))
				
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.go,
			"back": self.close,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown
		}, -1)
		
		self.update = True
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.doUpdateDelay)
		
	def go(self):
		if self.update:
			self.session.openWithCallback(self.doUpdate, MessageBox, _("Do you want to update your Dreambox?\nAfter pressing OK, please wait!"))		
		else:
			self.close()
	
	def doUpdateDelay(self):
		lines = popen("ipkg update && ipkg upgrade -force-defaults -force-overwrite", "r").readlines()
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
		lines = popen("ipkg list", "r").readlines()
		packetlist = []
		for x in lines:
			split = x.split(' - ')
			packetlist.append([split[0].strip(), split[1].strip()])
		
		lines = popen("ipkg list_installed", "r").readlines()
		
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
		lines = popen("ipkg update && ipkg upgrade", "r").readlines()
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
	session.open(Upgrade)

def IpkgMain(session, **kwargs):
	session.open(Ipkg)

def Plugins(**kwargs):
	return [PluginDescriptor(name="Old Softwareupdate", description="Updates your receiver's software", icon="update.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=UpgradeMain),
			PluginDescriptor(name="IPKG", description="IPKG frontend", icon="update.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=IpkgMain)]
