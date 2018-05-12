### Start Kodi
### check for space and whether installed
### main work done in enigma2.sh, here we do just a touch
### TODO: installation error checking is missing, network state...


from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
import os
#from Components.Ipkg import IpkgComponent
#from Screens.Ipkg import Ipkg
from enigma import quitMainloop
from Plugins.Extensions.StartKodi.installsomething import InstallSomething



class StartKodi2(Screen):

	kodi_name = "kodi-amlogic"
	kodineeds = 200             # TODO: check real needs, more likely to be ~ 300MB
	caninstall = False
	isinstalled = False

	skin = """
		<screen position="center,center" size="500,200" title="Start Kodi">
		<widget name="text" position="30,30" size="360,25" font="Regular;25" />
		<widget name="sd_label" position="30,100" size="310,25" font="Regular;20" />
		<widget name="freespace_label" position="30,125" size="310,25" font="Regular;20" />
		<widget name="installed_label" position="30,150" size="310,25" font="Regular;20" />
		<widget name="sd" position="340,100" size="150,25" font="Regular;20" />
		<widget name="freespace" position="340,125" size="150,25" font="Regular;20" />
		<widget name="installed" position="340,150" size="150,25" font="Regular;20" />
		</screen>"""
	def __init__(self, session, args = 0):
		self.session = session
		Screen.__init__(self, session)

		freembsd = str(self.getFreeSD())
		freemb = str(self.getFreeNand()) 
		isInstalled = str(self.isKodiInstalled())

		self["text"] = Label(_("Please press OK to start Kodi..."))
		self["sd_label"] = Label(_("Kodi/extra partition free space:"))
		self["freespace_label"] = Label(_("System partition free space:"))
		self["installed_label"] = Label(_("Kodi installed:"))

		self["sd"] = Label(freembsd + " MB")
		self["freespace"] = Label(freemb + " MB")
		self["installed"] = Label(isInstalled)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.ok,
			"cancel": self.close,
		})
		self.onShown.append(self.onFirstShown)   ### !!! A must to avoid modal crap 

	def onFirstShown(self):
		self.onShown.remove(self.onFirstShown)   ### avoid perpetual installs
		if (self.isinstalled):
			self["text"] = Label(_("\n   Please press OK to start Kodi..."))
		elif (self.caninstall is False):
			self["text"] = Label(_("\n  WARNING: \n  There is not enough space to install Kodi!"))
		else:
			self.session.openWithCallback(self.doInstallCallback, MessageBox, _("\n Kodi not present. Proceed with install?"))

### wo callback message is shown after install
#			self.session.open(MessageBox,_("\n Kodi not present, installing, please wait..."), MessageBox.TYPE_INFO, timeout = 5)
#			self["text"] = Label(_("\n Kodi not present, installing, please wait..."))
#			os.system("opkg install kodi-amlogic")
#			os.system("touch /etc/.kodistart")
# Try more civilized download
#			self.KodiInstallation = InstallSomething(self.session, self.kodi_name)
#			self.KodiInstallation.__install__()
#			self.isinstalled = True


	def doInstallCallback(self, result):
		if result:
			self.KodiInstallation = InstallSomething(self.session, [self.kodi_name])
			self.KodiInstallation.__install__()
			self.isinstalled = True                 # actually very bad, we did not check for errors
			os.system("touch /etc/.kodistart")      # but enigma2.sh checks for /usr/bin/xbmc 


### TODO: done touch(es) should go here
	def ok(self):
		if (self.isinstalled):
#			self.[text] = Label(_("Starting Kodi..."))
#			self["text"].hide()
#			self["text"].show()
#			StartKodi2.already_shown = False
#			StartKodi2.hide(self)
#			StartKodi2.show(self)
#			StartKodi2.update(self)
			os.system("touch /etc/.kodistart")
			quitMainloop(3)
		else:
			self.close()


### TODO: check portability (busybox vs coreutils)
	def getFreeNand(self):
		os.system('sync ; sync ; sync' )
		sizeread = os.popen("df | grep %s | tr -s ' '" % 'root')
		c = sizeread.read().strip().split(" ")
		sizeread.close()
		free = int(c[3])/1024
		if (free > self.kodineeds):
			self.caninstall = True
		else:
			self.caninstall = False
		return free  
		#hopefully returrn free MBs in NAND/uSD
		#self["lab_flash"].setText("%sB out of %sB" % (c[3], c[1]))
		#self["Used"].setText("Used: %s" % c[2])
		#self["Available"].setText("Available: %s" % c[3])
		#self["Use in %"].setText("Use: %s" % c[4])
		#self["Partition"].setText("Partition: %s" % c[0])

### TODO: check if partition exists check portability (busybox vs coreutils)
	def getFreeSD(self):
#		os.system('sync ; sync ; sync' )
		sizeread = os.popen("df | grep %s | tr -s ' '" % 'uSDextra')
		c = sizeread.read().strip().split(" ")
		sizeread.close()
		if os.path.exists("/media/uSDextra"): 
			free = int(c[3])/1024
		else:
			free = "Not available" 
		return free  


### not very clever...
	def isKodiInstalled(self):
		if os.path.exists("/usr/lib/kodi/kodi.bin"):
			self.isinstalled = True
			return True
		else:
			self.isinstalled = False
			return False


### Not used at the moment
class SysMessage(Screen):
	skin = """
		<screen position="150,200" size="450,200" title="System Message" >
			<widget source="text" position="0,0" size="450,200" font="Regular;20" halign="center" valign="center" render="Label" />
			<ePixmap pixmap="icons/input_error.png" position="5,5" size="53,53" alphatest="on" />
		</screen>"""
	def __init__(self, session, message):
		from Components.Sources.StaticText import StaticText

		Screen.__init__(self, session)

		self["text"] = StaticText(message)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.ok,
		})

	def ok(self):
		self.close()



### MENU service stuff
def main(session, **kwargs):
	session.open(StartKodi2)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Start Kodi"), main, "start_kodi", 44)]
	return []

def Plugins(**kwargs):
	return [
	PluginDescriptor(name = _("Start Kodi"), description = _("Kodi media player"), 	where = PluginDescriptor.WHERE_PLUGINMENU, icon = "kodi.png", needsRestart = False, fnc = main),
	PluginDescriptor(name = _("Start Kodi"), description = _("Play back media files"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = menu)
]
#	PluginDescriptor(name = _("StartKodi"), description = _("Play back media files"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart = False, fnc = menu)



