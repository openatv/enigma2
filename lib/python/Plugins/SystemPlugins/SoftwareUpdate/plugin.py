from Components.ActionMap import ActionMap, NumberActionMap
from Components.GUIComponent import GUIComponent
from Components.Input import Input
from Components.Ipkg import IpkgComponent
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Slider import Slider
from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.ImageWizard import ImageWizard
from Screens.MessageBox import MessageBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from enigma import eTimer, quitMainloop, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eListbox, gFont
from os import popen


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
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "TextEntryActions", "KeyboardInputActions"], 
		{
			"ok": self.go,
			"back": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
			"home": self.keyHome,
			"end": self.keyEnd,
			"deleteForward": self.deleteForward,
			"deleteBackward": self.deleteBackward,
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
	
	def keyHome(self):
		self["text"].home()
	
	def keyEnd(self):
		self["text"].end()
	
	def keyDeleteForward(self):
		self["text"].delete()
	
	def keyDeleteBackward(self):
		self["text"].deleteBackward()
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		self["text"].number(number)

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

class Ipkg2(Screen):
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
			
class UpdatePlugin(Screen):
	skin = """
		<screen position="100,100" size="550,200" title="Software Update..." >
			<widget name="activityslider" position="0,0" size="550,5"  />
			<widget name="slider" position="0,100" size="550,30"  />
			<widget name="package" position="10,30" size="540,20" font="Regular;18"/>
			<widget name="status" position="10,60" size="540,45" font="Regular;18"/>
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = UpdatePlugin.skin
		Screen.__init__(self, session)
		
		self.sliderPackages = { "dreambox-dvb-modules": 1, "enigma2": 2, "tuxbox-image-info": 3 }
		
		self.slider = Slider(0, 4)
		self["slider"] = self.slider
		self.activityslider = Slider(0, 100)
		self["activityslider"] = self.activityslider
		self.status = Label(_("Upgrading Dreambox... Please wait"))
		self["status"] = self.status
		self.package = Label()
		self["package"] = self.package
		
		self.packages = 0
		self.error = 0
		
		self.activity = 0
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doActivityTimer)
		self.activityTimer.start(100, False)
				
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)
		
		self.updating = True
		self.package.setText(_("Package list update"))
		self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
			
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.exit,
			"back": self.exit
		}, -1)
		
	def doActivityTimer(self):
		self.activity += 1
		if self.activity == 100:
			self.activity = 0
		self.activityslider.setValue(self.activity)
		
	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_DOWNLOAD:
			self.status.setText(_("Downloading"))
		elif event == IpkgComponent.EVENT_UPGRADE:
			if self.sliderPackages.has_key(param):
				self.slider.setValue(self.sliderPackages[param])
			self.package.setText(param)
			self.status.setText(_("Upgrading"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_INSTALL:
			self.package.setText(param)
			self.status.setText(_("Installing"))
			self.packages += 1
		elif event == IpkgComponent.EVENT_CONFIGURING:
			self.package.setText(param)
			self.status.setText(_("Configuring"))
		elif event == IpkgComponent.EVENT_MODIFIED:
			self.session.openWithCallback(
				self.modificationCallback,
				MessageBox,
				_("A configuration file (%s) was modified since Installation.\nDo you want to keep your version?") % (param)
			)
		elif event == IpkgComponent.EVENT_ERROR:
			self.error += 1
		elif event == IpkgComponent.EVENT_DONE:
			if self.updating:
				self.updating = False
				self.ipkg.startCmd(IpkgComponent.CMD_UPGRADE, args = {'test_only': False})
			elif self.error == 0:
				self.slider.setValue(4)
				
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				
				self.package.setText("")
				self.status.setText(_("Done - Installed or upgraded %d packages") % self.packages)
			else:
				self.activityTimer.stop()
				self.activityslider.setValue(0)
				error = _("your dreambox might be unusable now. Please consult the manual for further assistance before rebooting your dreambox.")
				if self.packages == 0:
					error = _("No packages were upgraded yet. So you can check your network and try again.")
				if self.updating:
					error = _("Your dreambox isn't connected to the internet properly. Please check it and try again.")
				self.status.setText(_("Error") +  " - " + error)
		#print event, "-", param
		pass

	def modificationCallback(self, res):
		self.ipkg.write(res and "N" or "Y")

	def exit(self):
		if not self.ipkg.isRunning():
			if self.packages != 0 and self.error == 0:
				self.session.openWithCallback(self.exitAnswer, MessageBox, _("Upgrade finished. Do you want to reboot your Dreambox?"))
			else:
				self.close()
			
	def exitAnswer(self, result):
		if result is not None and result:
			quitMainloop(2)
		self.close()

def UpgradeMain(session, **kwargs):
	session.open(UpdatePlugin)

def Plugins(**kwargs):
	return PluginDescriptor(name="Softwareupdate", description=_("Updates your receiver's software"), icon="update.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=UpgradeMain)
