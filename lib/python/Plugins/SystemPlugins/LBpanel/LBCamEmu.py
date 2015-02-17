# LBPanel -- Linux-Box Panel.                             
# Copyright (C) www.linux-box.es
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of   
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU gv; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 
# Author: lucifer
#         iqas
#
# Internet: www.linux-box.es
# Based on original source by epanel for openpli 

from Plugins.Plugin import PluginDescriptor
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigSelection, ConfigSubsection, ConfigYesNo,   config, configfile
from Components.ConfigList import ConfigListScreen
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap, NumberActionMap
from Screens.ChoiceBox import ChoiceBox
from Components.config import config, configfile, getConfigListEntry
from Components.ConfigList import ConfigList, ConfigListScreen
from Screens.PluginBrowser import PluginBrowser
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.Sources.List import List
from Tools.LoadPixmap import LoadPixmap
from Plugins.Plugin import PluginDescriptor
from Screens.Console import Console
from Screens.Screen import Screen
from Components.Label import Label
from enigma import eTimer, RT_HALIGN_LEFT, eListboxPythonMultiContent, gFont, getDesktop, eSize, ePoint
from Components.Language import language
from Components.Sources.StaticText import StaticText
from Tools.Directories import fileExists
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ
import os
import sys
import gettext
import LBtools

sys.path.append('/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/libs/CCcamInfo') 
sys.path.append('/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/libs/OscamInfo')
sys.path.append('/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/libs/GboxSuite')

import gboxsuite
import cccaminfo
import oscaminfo

address = "http://gisclub.tv/gi/softcam/SoftCam.Key"
pluginpath = "/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/"
ownbiss = "own.biss"

lang = language.getLanguage()
environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("messages", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "SystemPlugins/LBpanel/locale"))

def _(txt):
	t = gettext.dgettext("messages", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t
####################################################################
config.plugins.lbpanel.activeserver = ConfigText(default = "NotSelected")
config.plugins.lbpanel.activeconf = ConfigText(default = "NotSelected")
config.plugins.lbpanel.activeemu = ConfigText(default = "NotSelected")
####################################################################
config.plugins.lbpanel.serveredit = ConfigText(default="xxx.xxx.xxx.xxx", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.port = ConfigText(default="00000", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.login = ConfigText(default="login", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.passw = ConfigText(default="******", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.timeout = ConfigText(default="000", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.keepalive = ConfigText(default="no", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.incoming = ConfigText(default="00000", visible_width = 200, fixed_size = False)
config.plugins.lbpanel.debug = ConfigText(default="00000", visible_width = 200, fixed_size = False)
######################################################################################
config.plugins.lbpanel.addbiss = ConfigSelection(default = "No", choices = [
		("0", _("No")),
		("1", _("Yes")),
		])
config.plugins.lbpanel.path = ConfigSelection(default = "/usr/keys/", choices = [
		("/usr/keys/", "/usr/keys/"),
		("/etc/keys/", "/etc/keys/"),
		("/var/tuxbox/config/", "/var/tuxbox/config/"),
		("/var/tuxbox/config/oscam-stable/", "/var/tuxbox/config/oscam-stable/"),
		])
config.plugins.lbpanel.keyname = ConfigSelection(default = "SoftCam.Key", choices = [
		("SoftCam.Key", "SoftCam.Key"),
		("oscam.keys", "oscam.keys"),
		("oscam.biss", "oscam.biss"),
		])
		
# Start init emu
print ("Init/restart SoftCam %s restart" % config.plugins.lbpanel.activeemu.value)
os.system("/usr/CamEmu/%s restart &" % config.plugins.lbpanel.activeemu.value )
######################################################################################
class emuSel2(Screen):
	skin = """
<screen name="emuSel2" position="0,0" size="1280,720" title="lb_title" zPosition="2">
  <widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
    <convert type="TemplatedMultiContent">
		{"template": [
			MultiContentEntryText(pos = (70, 2), size = (630, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
			MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
			MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (37, 23), png = 2), # index 4 is the pixmap
				],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 50
	}
	</convert>
 </widget>
<eLabel text="INFO" position="1115,650" size="100,30" zPosition="5" font="Regular;20" valign="center" halign="center" backgroundColor="white" foregroundColor="black" transparent="0" />
     
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="PARAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="REINICIAR" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="INICIAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="INSTALAR" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="800,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

  	skin = skin.replace("lb_title", _("LBpanel CamEmu"))
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel CamEmu Activa: %s") % config.plugins.lbpanel.activeemu.value)
		self.session = session
		self.list = []
		self.indexpos = None
		self["menu"] = List(self.list)
		self.selemulist()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "CCcamInfoActions"],
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"green": self.start,
				"red": self.stop,
				"yellow": self.restart,
				"blue": self.install,
				"info": self.extrainfo,
			},-1)
		self.list = [ ]
		self["text"] = ScrollLabel("")
		self.listecm()
		self.Timer = eTimer()
		self.Timer.callback.append(self.listecm)
		self.Timer.start(1000*4, False)
		
	def listecm(self):
		list = ""
		if fileExists("/tmp/ecm.info"):
			try:
				ecmfiles = open("/tmp/ecm.info", "r")
				for line in ecmfiles:
					if line.find("caid:") > -1 or line.find("provider:") > -1 or line.find("provid:") > -1 or line.find("pid:") > -1 or line.find("hops:") > -1  or line.find("system:") > -1 or line.find("address:") > -1 or line.find("using:") > -1 or line.find("ecm time:") > -1:
						line = line.replace(' ',"").replace(":",": ")
					if line.find("caid:") > -1 or line.find("pid:") > -1 or line.find("reader:") > -1 or line.find("from:") > -1 or line.find("hops:") > -1  or line.find("system:") > -1 or line.find("Service:") > -1 or line.find("CAID:") > -1 or line.find("Provider:") > -1:
						line = line.strip('\n') + "  "
					if line.find("Signature") > -1:
						line = ""
					if line.find("=") > -1:
						line = line.lstrip('=').replace('======', "").replace('\n', "").rstrip() + ', '
					if line.find("ecmtime:") > -1:
						line = line.replace("ecmtime:", "ecm time:")
					if line.find("response time:") > -1:
						line = line.replace("response time:", "ecm time:").replace("decoded by", "by")
					if not line.startswith('\n'):
						list += line
				self["text"].setText(list)
				ecmfiles.close()
			except:
				pass
		
	def selemulist(self):
		self.list = []
		typeemu = ' '
		
		if not os.path.exists("/usr/CamEmu"):
			os.makedirs("/usr/CamEmu")
			
		camdlist = os.listdir("/usr/CamEmu/")
		for line in camdlist:
			if line.find(".None") == -1:
				if line.split(".")[0] == 'camemu':
					typeemu = 'camemu'
					print "EMU: %s - %s" % (line, config.plugins.lbpanel.activeemu.value)
    					if line == config.plugins.lbpanel.activeemu.value : 
					#self.emuversion('camemu'):
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/%s" % 'ico_crypt_on.png'))
					else:
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/%s" % 'ico_crypt_off.png'))
				elif line.split(".")[0] == 'cardserver':
					typeemu = 'cardserver'
					if self.emuversion(line) == self.emuversion('cardserver'):
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/%s" % 'cardact.png'))
					else:
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/%s" % 'cardmini.png'))
				try:
					if line.find('camemu.') > -1 or line.find('cardserver.') > -1:
						#line = self.line.replace("camemu.", "")
						self.list.append((line, self.emuversion(line), softpng, typeemu))
				except:
					pass
		self.list.sort()
		self["menu"].setList(self.list)
		if self.indexpos != None:
			self["menu"].setIndex(self.indexpos)
		
	def emuversion(self, what):
		emuname = " "
		nameemu = []
		if fileExists("/usr/CamEmu/%s" % what.split("\n")[0]):
			try:
				for line in open("/usr/CamEmu/%s" % what.split("\n")[0]):
					if line.find("echo") > -1:
						nameemu.append(line)
				emuname =  "%s" % nameemu[1].split('"')[1]
			except:
				emuname = " "
		return emuname
		
	def start(self):
		emutype = self["menu"].getCurrent()[3]
		os.system("/usr/CamEmu/%s stop" % config.plugins.lbpanel.activeemu.value)
		emuexec = self["menu"].getCurrent()[0]
		emuexec = emuexec[7:]
		print "Add execute permision to %s" % (emuexec)
		if fileExists("/usr/bin/%s" % emuexec):
			os.chmod("/usr/bin/%s" % emuexec, 0777)
		config.plugins.lbpanel.activeemu.value = self["menu"].getCurrent()[0]
		self.indexpos = self["menu"].getIndex()
		config.plugins.lbpanel.activeemu.save()
		os.system("/usr/CamEmu/%s start" % config.plugins.lbpanel.activeemu.value)
		self.mbox = self.session.open(MessageBox, _("Please wait, starting %s") % self["menu"].getCurrent()[0], MessageBox.TYPE_INFO, timeout = 4 )
		self.setTitle(_("Select SoftCam or CardServer: - %s") % config.plugins.lbpanel.activeemu.value)
		self.selemulist()
		
	def stop(self):
		emutype = self["menu"].getCurrent()[3]
		os.system("/usr/CamEmu/%s stop" % config.plugins.lbpanel.activeemu.value)
		self.mbox = self.session.open(MessageBox, _("Please wait, stoping softcam or cardserver"), MessageBox.TYPE_INFO, timeout = 4 )
		config.plugins.lbpanel.activeemu.value = "NotSelected"
		config.plugins.lbpanel.activeemu.save()
		self.setTitle(_("Select SoftCam or CardServer: - %s") % config.plugins.lbpanel.activeemu.value)
		self.indexpos = self["menu"].getIndex()
		self.selemulist()
		
	def restart(self):
		emutype = self["menu"].getCurrent()[3]
		#if self.emuversion(emutype) != " ":
		os.system("/usr/CamEmu/%s restart" % config.plugins.lbpanel.activeemu.value)
		self.mbox = self.session.open(MessageBox,_("Please wait, restarting %s")% self.emuversion(emutype), MessageBox.TYPE_INFO, timeout = 4 )
		self.indexpos = self["menu"].getIndex()
		
	def install(self):
		self.session.openWithCallback(self.selemulist,installCam)

	def extrainfo(self):
		self.session.open(ECMinfo)
		
	def ok(self):
		self.start()
		
	def cancel(self):
		self.close()
		
#####################################################################################################
class installCam(Screen):
	skin = """
<screen name="installCam" position="0,0" size="1280,720" title="lb_title">
    <widget source="menu" render="Listbox" position="592,191" size="628,350" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1">
	<convert type="TemplatedMultiContent">
		{"template": [
			MultiContentEntryText(pos = (70, 2), size = (630, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
			MultiContentEntryText(pos = (80, 29), size = (630, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
			MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (50, 40), png = 2), # index 4 is the pixmap
				],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 50
	}
	</convert>
	</widget>
   <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="INSTALAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="INSTALADOS" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""
	  
	skin = skin.replace("lb_title", _("LBpanel - LinuxBox Feeds Download"))  
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.list = []
		self["menu"] = List(self.list)
		self.feedlist()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"green": self.setup,
				"red": self.cancel,
				"blue": self.install,
			},-1)
		self.list = [ ]
				
	def feedlist(self):
		self.list = []
		os.system("opkg update")
		camdlist = os.popen("opkg list | grep lbcam")
		softpng = LoadPixmap(cached = True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/emumini.png"))
		for line in camdlist.readlines():
			try:
				self.list.append(("%s %s" % (line.split(' - ')[0], line.split(' - ')[1]), line.split(' - ')[-1], softpng))
			except:
				pass
		camdlist.close()
		self["menu"].setList(self.list)
		
	def ok(self):
		self.setup()

	def install(self):
		self.session.open(installCam2)
		
	def setup(self):
		os.system("opkg install -force-overwrite %s" % self["menu"].getCurrent()[0])
		os.popen("chmod 777 /usr/CamEmu/camemu.*")	
		self.mbox = self.session.open(MessageBox, _("%s is installed" % self["menu"].getCurrent()[0]), MessageBox.TYPE_INFO, timeout = 4 )
		
	def cancel(self):
		self.close()
#################################################
class installCam2(Screen):
	skin = """

<screen name="installCam2" position="0,0" size="1280,720" title="lb_title">
    <widget source="menu" render="Listbox" position="592,191" size="628,350" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1">
	<convert type="TemplatedMultiContent">
		{"template": [
			MultiContentEntryText(pos = (70, 2), size = (630, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
			MultiContentEntryText(pos = (80, 29), size = (630, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
			MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (50, 40), png = 2), # index 4 is the pixmap
				],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 50
	}
	</convert>
	</widget>
   <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="BORRAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""
	  
	skin = skin.replace("lb_title", _("LBpanel - LinuxBox Feeds installed"))  
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.list = []
		self["menu"] = List(self.list)
		self.feedlist()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"green": self.setup,
				"red": self.cancel,
			},-1)
		self.list = [ ]
				
	def feedlist(self):
		self.list = []
		camdlist = os.popen("opkg list-installed | grep lbcam")
		softpng = LoadPixmap(cached = True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/emumini1.png"))
		for line in camdlist.readlines():
			try:
				self.list.append(("%s %s" % (line.split(' - ')[0], line.split(' - ')[1]), line.split(' - ')[-1], softpng))
			except:
				pass
		camdlist.close()
		self["menu"].setList(self.list)
		
	def ok(self):
		self.setup()
		
	def setup(self):
		os.system("opkg remove %s" % self["menu"].getCurrent()[0])
		self.mbox = self.session.open(MessageBox, _("%s is remove" % self["menu"].getCurrent()[0]), MessageBox.TYPE_INFO, timeout = 4 )
		

	def cancel(self):
		self.close()
#################################################
class ECMinfo(Screen):
	skin = """
<screen name="ECMinfo" position="0,0" size="1280,720" title="Ecminfo">
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
<eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
      	<widget name="text" position="610,191" size="600,500" foregroundColor="#ffffff" backgroundColor="#6e6e6e" transparent="1" font="Console;15" />
</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("CamEmu Extra Info"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"ok": self.exit,
			})
		self["key_red"] = StaticText(_("Close"))
		self["text"] = ScrollLabel("")
		self.meminfoall()
		
	def exit(self):
		self.close()
		
	def meminfoall(self):
		list = " "
		try:
			os.system("uptime>/tmp/mem && echo>>/tmp/mem && /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/extrainfo>>/tmp/mem")
			meminfo = open("/tmp/mem", "r")
			for line in meminfo:
				list += line
			self["text"].setText(list)
			meminfo.close()
			os.system("rm /tmp/mem")
		except:
			list = " "
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], { "cancel": self.close, "up": self["text"].pageUp, "left": self["text"].pageUp, "down": self["text"].pageDown, "right": self["text"].pageDown,}, -1)
#################################################
class CamEmuPanel(Screen):
	skin = """
<screen name="CamEmuPanel" position="0,0" size="1280,720" >
<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="white" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" size="628,350">
      <convert type="TemplatedMultiContent">
    {"template": [ MultiContentEntryText(pos = (30, 5), size = (460, 50), flags = RT_HALIGN_LEFT, text = 0) ],
    "fonts": [gFont("Regular", 30)],
    "itemHeight": 60
    }
   </convert>
    </widget>
    
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="REINICIAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - SoftEmus"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "CCcamInfoActions"],

		{
			"ok": self.keyOK,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.Restart,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reboot"))
		self.list = []
		self["menu"] = List(self.list)
		self.mList()
		
	def mList(self):
		self.list = []
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/softcam.png"))
		treepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/soft.png"))
		fivepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/serviceman.png"))
		dospng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/cccam.png"))
		trespng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/oscam.png"))
		cuatropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/mbox.png"))
		cincopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/acj.png"))
		seispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/mgcami.png"))
		sietepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/mgcamedi.png"))
		self.list.append((_("Softcam"),"com_one", _("Softcam Init, Stop and Restart"), onepng))
		#self.list.append((_("Softcam control"),"com_five", _("Testin Softcam status"), fivepng))
		#self.list.append((_("Descarga SoftCam.Key"),"com_tree", _("Descarga Softcam.key de internet"), treepng))
		self.list.append((_("CCcam Info"),"com_dos", _("Plugin CCcam Info"), dospng))
		self.list.append((_("Oscam Info"),"com_tres", _("Plugin Status emu Oscam"), trespng))
		self.list.append((_("Gbox Suite"),"com_cuatro", _("Plugin Status emu Gbox-Mbox"), cuatropng))
		self.list.append((_("Mbox scripts"),"com_cinco", _("ACJ Mbox Script"), cincopng))
		self.list.append((_("Mgcamd Info"),"com_seis", _("Mgcamd status information"), seispng))
		self.list.append((_("Mgcamd Editor"),"com_siete", _("Newcamd Line Editor"), sietepng))
		self["menu"].setList(self.list)

	def exit(self):
		self.close()

	def keyOK(self, returnValue = None):
		if returnValue == None:
			returnValue = self["menu"].getCurrent()[1]
			if returnValue is "com_one":
				self.session.openWithCallback(self.mList,emuSel2)
			#elif returnValue is "com_tree":
				#self.session.open(SoftcamUpd)
			elif returnValue is "com_two":
				self.session.open(wicconfsw)
			elif returnValue is "com_five":
				self.session.open(ServiceMan)
			elif returnValue is "com_dos":
				self.session.open(cccaminfo.CCcamInfoMain)
			elif returnValue is "com_tres":
				self.session.open(oscaminfo.OscamInfoMenu)
			elif returnValue is "com_cuatro":
				self.session.open(gboxsuite.GboxSuiteMainMenu)
			elif returnValue is "com_cinco":
				self.session.open(MboxMan)
			elif returnValue is "com_seis":
				self.session.open(NCLSwp2)
			elif returnValue is "com_siete":
				self.session.open(NCLEdit)
			else:
				print "\n[LBpanel] cancel\n"
				self.close(None)

	def Restart(self):
		if fileExists("/usr/CamEmu/camemu"):
			os.system("/usr/CamEmu/camemu stop")
		if fileExists("/etc/init.d/cardserver"):
			os.system("/etc/init.d/cardserver stop")
			os.system("/etc/init.d/cardserver start")
		if fileExists("/usr/CamEmu/camemu"):
			os.system("/usr/CamEmu/camemu start")
		if fileExists("/usr/CamEmu/camemu") or fileExists("/etc/init.d/cardserver"):
			self.mbox = self.session.open(MessageBox, _("Restarting ..."), MessageBox.TYPE_INFO, timeout = 4 )
###############################################################################################
class SoftcamUpd(ConfigListScreen, Screen):
	skin = """
<screen name="SoftcamUpd" position="center,160" size="750,370" title="lb_title">
		<widget position="15,10" size="720,300" name="config" scrollbarMode="showOnDemand" />
		<ePixmap position="10,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
		<widget source="key_red" render="Label" position="10,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
		<ePixmap position="175,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
		<widget source="key_green" render="Label" position="175,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
		<ePixmap position="340,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/yellow.png" alphatest="blend" />
		<widget source="key_yellow" render="Label" position="340,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
		<ePixmap position="505,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/blue.png" alphatest="blend" />
		<widget source="key_blue" render="Label" position="505,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
</screen>"""
	skin = skin.replace("lb_title", _("LBpanel Sofcam Key Updater"))
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.list = []
		self.list.append(getConfigListEntry(_("Path to save keyfile"), config.plugins.lbpanel.path))
		self.list.append(getConfigListEntry(_("Name of keyfile"), config.plugins.lbpanel.keyname))
		self.list.append(getConfigListEntry(_("Add own biss in keyfile"), config.plugins.lbpanel.addbiss))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Download"))
		self["key_blue"] = StaticText(_("Changelog"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "EPGSelectActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.downkey,
			"blue": self.keyBlue,
			"ok": self.save
		}, -2)
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close(False)
	
	def save(self):
		config.plugins.lbpanel.addbiss.save()
		config.plugins.lbpanel.path.save()
		config.plugins.lbpanel.keyname.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )
		
	def keyBlue (self):
		self.session.open(ChangelogScreen)
		
	def downkey(self):
		try:
			os.system("wget -P /tmp %s" % ( address))
			if config.plugins.lbpanel.addbiss.value == "1":
				if fileExists("%s%s" % (pluginpath,ownbiss)):
					os.system("cp %s%s /tmp/%s" % (pluginpath, ownbiss, ownbiss))
					os.system("cat /tmp/%s /tmp/SoftCam.Key > /tmp/keyfile.tmp" % (ownbiss))
					os.system("rm /tmp/SoftCam.Key")
			else:
				os.system("mv /tmp/SoftCam.Key /tmp/keyfile.tmp")
			if fileExists("%s%s" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value)):
				if config.plugins.lbpanel.keyname.value == "SoftCam.Key":
					os.system("cp %s%s %s%s.old" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value, config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value[:-4]))
				else:
					os.system("cp %s%s %s%s.old" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value, config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value[:-5]))
				os.system("rm %s%s" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value))
			os.system("cp /tmp/keyfile.tmp %s%s" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value))
			os.chmod(("%s%s" % (config.plugins.lbpanel.path.value, config.plugins.lbpanel.keyname.value)), 0644)
			os.system("rm /tmp/keyfile.tmp")
			os.system("rm /tmp/%s" % (ownbiss))
			self.mbox = self.session.open(MessageBox,(_("%s downloaded Successfull" % config.plugins.lbpanel.keyname.value)), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			os.system("cp /usr/keys/SoftCam.old /usr/keys/SoftCam.Key")
			self.mbox = self.session.open(MessageBox,(_("%s downloaded UnSuccessfull" % config.plugins.lbpanel.keyname.value)), MessageBox.TYPE_INFO, timeout = 4 )
######################################################################################
class ChangelogScreen(Screen):
	skin = """
<screen name="ChangelogScreen" position="center,160" size="750,370" title="Changelog">
	<ePixmap position="20,358" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
	<widget source="key_red" render="Label" position="20,328" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget name="text" position="15,10" size="720,300" font="Console;20" />
</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("Changelog"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			})
		self["key_red"] = StaticText(_("Close"))
		self["text"] = ScrollLabel("")
		self.meminfoall()
		
	def exit(self):
		self.close()
		
	def meminfoall(self):
		list = " "
		os.system("wget -P /tmp/ %s.txt" % (address[:-4]))
		try:
			meminfo = open("/tmp/SoftCam.txt", "r")
			for line in meminfo:
				list += line
			self["text"].setText(list)
			meminfo.close()
			os.system("rm /tmp/SoftCam.txt")
		except:
			try:
				self.mbox = self.session.open(MessageBox,(_("%s") % (address)), MessageBox.TYPE_INFO, timeout = 4)
			except:
				pass
			list = " "
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], 
		{ "cancel": self.close,
		"up": self["text"].pageUp,
		"left": self["text"].pageUp,
		"down": self["text"].pageDown,
		"right": self["text"].pageDown,
		}, -1)
######################################################################################
class wicconfsw(Screen):
	skin = """
<screen name="wicconfsw" position="center,160" size="750,370" title="Oscam.conf Switcher">
  <ePixmap position="20,358" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
  <widget source="key_red" render="Label" position="20,328" zPosition="2" size="170,30" font="Regular; 19" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
  <ePixmap position="190,358" zPosition="1" size="250,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
  <widget source="key_green" render="Label" position="190,328" zPosition="2" size="250,30" font="Regular; 19" halign="center" valign="center" backgroundColor="background" foregroundColor="white" transparent="1" />
  <widget source="list" render="Listbox" position="15,10" size="720,150" scrollbarMode="showOnDemand">
   <convert type="TemplatedMultiContent">
   {"template": [
    MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
    MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
    MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (50, 40), png = 2), # index 4 is the pixmap
    ],
   "fonts": [gFont("Regular", 23),gFont("Regular", 16)],
   "itemHeight": 50
  }
    </convert>
      </widget>
  <widget name="text" position="50,180" size="650,155" font="Console;22" halign="center" noWrap="1" backgroundColor="background" foregroundColor="foreground" />
  <eLabel position="50,168" size="650,2" backgroundColor="grey" zPosition="3" />
</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = wicconfsw.skin
		self.setTitle(_("LBpanel oscam.conf Switcher: - %s") % config.plugins.lbpanel.activeconf.value)
		self.session = session
		self.list = []
		self["list"] = List(self.list)
		self.mList()
		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions"],
		{	
			"ok": self.run,
			"red": self.close,
			"green": self.restartsoft,
			"cancel": self.close
		}, -1)
		self["readServ"] = StaticText()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Restart Softcam"))
		self["text"] = ScrollLabel("")
		self.listecm()
		self.Timer = eTimer()
		self.Timer.callback.append(self.listecm)
		self.Timer.start(1000*4, False)
		
	def listecm(self):
		list = ""
		try:
			ecmfiles = open("/tmp/ecm.info", "r")
			for line in ecmfiles:
				if line.find("caid:") > -1 or line.find("provider:") > -1 or line.find("provid:") > -1 or line.find("pid:") > -1 or line.find("hops:") > -1  or line.find("system:") > -1 or line.find("address:") > -1 or line.find("using:") > -1 or line.find("ecm time:") > -1:
					line = line.replace(' ',"").replace(":",": ")
				if line.find("caid:") > -1 or line.find("pid:") > -1 or line.find("reader:") > -1 or line.find("from:") > -1 or line.find("hops:") > -1  or line.find("system:") > -1 or line.find("Service:") > -1 or line.find("CAID:") > -1 or line.find("Provider:") > -1:
					line = line.strip('\n') + "  "
				if line.find("Signature") > -1:
					line = ""
				if line.find("=") > -1:
					line = line.lstrip('=').replace('======', "").replace('\n', "").rstrip() + ', '
				if line.find("ecmtime:") > -1:
					line = line.replace("ecmtime:", "ecm time:")
				if line.find("response time:") > -1:
					line = line.replace("response time:", "ecm time:").replace("decoded by", "by")
				if not line.startswith('\n'):
					list += line
			self["text"].setText(list)
			ecmfiles.close()
		except:
			pass
		
	def mList(self):
		servinactpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/serv.png"))
		servactpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/servact.png"))
		self.list = []
		list = os.listdir("/var/tuxbox/config")
		for line in list:
			if line.find(".wc") > -1:
				if line[:-3] == config.plugins.lbpanel.activeconf.value:
					self.list.append((line[:-3],self.Adress(line), servactpng))
				else:
					self.list.append((line[:-3],self.Adress(line), servinactpng))
		self.list.sort()
		self["list"].setList(self.list)
		
	def run(self):
		config.plugins.lbpanel.activeconf.value = self["list"].getCurrent()[0]
		config.plugins.lbpanel.activeconf.save()
		self.setTitle(_("oscam.conf Switcher: - %s") % config.plugins.lbpanel.activeconf.value)
		if  fileExists("/var/tuxbox/config/oscam.conf"):
			os.system("cp -f /var/tuxbox/config/oscam.conf /var/tuxbox/config/previous.wc")
			os.chmod("/var/tuxbox/config/previous.wc", 0644)
		os.system("cp /var/tuxbox/config/%s.wc /var/tuxbox/config/oscam.conf" %  self["list"].getCurrent()[0])
		os.chmod("/var/tuxbox/config/oscam.conf", 0644)
		self.session.open(MessageBox, _("%s oscam.conf" % self["list"].getCurrent()[0]), type = MessageBox.TYPE_INFO, timeout = 4 )
		self.mList()

	def restartsoft(self):
		if fileExists("/etc/init.d/softcam"):
			os.system("/etc/init.d/softcam stop")
			os.system("/etc/init.d/softcam start")
			self.session.open(MessageBox, _("Softcam Restarted"), type = MessageBox.TYPE_INFO, timeout = 4 )
		
	def Adress (self, nameserv):
		cardline = ""
		iscard = 0
		if fileExists("/var/tuxbox/config/%s" % (nameserv)):
			for line in open("/var/tuxbox/config/%s" % (nameserv)):
				if line.find("device")> -1:
					cardline += "card: %s " % line.split()[-1]
				if line.find("account")> -1 and not line.find("[account]")> -1 and iscard < 1:
					cardline += "account: %s" % line.split()[-1].split("@")[-1].split(":")[0]
					iscard = iscard + 1
			return cardline
		else:
			return ""
####################################################################################
class NCLSwp2(Screen):
	skin = """
<screen name="NCLSwp2" position="0,0" size="1280,720" title="Mgcamd Info">
    
	<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
<eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
      	<widget name="text" position="610,191" size="600,500" foregroundColor="#ffffff" backgroundColor="#6e6e6e" transparent="1" font="Console;15" />
</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel Mgcamd Info"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"ok": self.exit,
			})
		self["key_red"] = StaticText(_("Close"))
		self["text"] = ScrollLabel("")
		self.meminfoall()
		
	def exit(self):
		self.close()
		
	def meminfoall(self):
		list = " "
		try:
			os.system("uptime>/tmp/mem && echo>>/tmp/mem && /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/mgcamdinfo>>/tmp/mem")
			meminfo = open("/tmp/mem", "r")
			for line in meminfo:
				list += line
			self["text"].setText(list)
			meminfo.close()
			os.system("rm /tmp/mem")
		except:
			list = " "
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], { "cancel": self.close, "up": self["text"].pageUp, "left": self["text"].pageUp, "down": self["text"].pageDown, "right": self["text"].pageDown,}, -1)
####################################################################################
class NCLEdit(Screen):
	skin = """
<screen name="NCLEdit" position="0,0" size="1280,720" title="newcamd.list editor">
  	<widget source="menu" render="Listbox" position="592,300" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" scrollbarMode="showNever" backgroundColorSelected="#fd6502" transparent="1">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (10, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (20, 29), size = (580, 25), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
		
			],
	"fonts": [gFont("Regular", 20),gFont("Regular", 20)],
	"itemHeight": 80
	}
			</convert>
		</widget>
		
		
	<eLabel position="625,210" size="290,25" font="Regular; 19" backgroundColor="#6e6e6e" transparent="1" text="CWS_CONNECT_TIMEOUT = " zPosition="1" />
	<eLabel position="625,240" size="200,25" font="Regular; 19" backgroundColor="#6e6e6e" transparent="1" text="CWS_KEEPALIVE =" />
	<eLabel position="925,210" size="250,25" font="Regular; 19" backgroundColor="#6e6e6e" transparent="1" text="CWS_INCOMING_PORT = " zPosition="1" />
	<eLabel position="925,240" size="260,25" font="Regular; 19" backgroundColor="#6e6e6e" transparent="1" text="CWS_DEBUG_PORT =" />
<widget source="timeout" render="Label" position="870,210" size="65,25" backgroundColor="#6e6e6e" transparent="1" font="Regular; 19" foregroundColor="#fec000" zPosition="2" />
<widget source="keepalive" render="Label" position="790,240" size="65,25" backgroundColor="#6e6e6e" transparent="1" font="Regular; 19" foregroundColor="#fec000" zPosition="2" />
<widget source="incoming" render="Label" position="1140,210" size="85,25" backgroundColor="#6e6e6e" transparent="1" font="Regular; 19" foregroundColor="#fec000" zPosition="2" />
<widget source="debug" render="Label" position="1120,240" size="85,25" backgroundColor="#6e6e6e" transparent="1" font="Regular; 19" foregroundColor="#fec000" zPosition="2" />
<widget source="enable" render="Label" position="580,450" zPosition="2" size="680,25" font="Regular;21" halign="center" valign="center" backgroundColor="#6e6e6e" foregroundColor="foreground" transparent="1" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="ADD" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="EDITAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="BORRAR" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""


	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel newcamd.list editor"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.able,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.edit,
			"yellow": self.add,
			"blue": self.remove,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Edit"))
		self["key_yellow"] = StaticText(_("Add"))
		self["key_blue"] = StaticText(_("Remove"))
		self["enable"] = StaticText(_("press OK to enable/disable server"))
		self["timeout"] = StaticText()
		self["keepalive"] = StaticText()
		self["debug"] = StaticText()
		self["incoming"] = StaticText()
		self.list = []
		self["menu"] = List(self.list)
		self.listserver()
		
	def listserver(self):
		self.list = []
		disable = ''
		self["timeout"].text = "None"
		self["keepalive"].text = "None"
		self["incoming"].text = "None"
		self["debug"].text = "None" 
		if not fileExists("/usr/keys/newcamd.list"):
			os.system("echo -e 'CWS_CONNECT_TIMEOUT = 120' >> /usr/keys/newcamd.list")
			os.system("echo -e 'CWS_KEEPALIVE = no' >> /usr/keys/newcamd.list")
			os.system("echo -e 'CWS = xxx.xxx.xxx.xxx port login pass 01 02 03 04 05 06 07 08 09 10 11 12 13 14' >> /usr/keys/newcamd.list")
			os.chmod("/usr/keys/newcamd.list", 0644)
		for line in open("/usr/keys/newcamd.list"):
			if line.find("CWS =") > -1 or line.find("CWS_MULTIPLE =") > -1:
				if line[0] == '#':
					disable = '#'
				else:
					disable = ''
				self.list.append(("%s  %s  %s  %s" % (line.split()[2], line.split()[3], line.split()[4], line.split()[5]), line, disable))
			elif line.find("CWS_CONNECT_TIMEOUT") > -1:
				timeout = line.split('=')[-1]
				self["timeout"].text = timeout.lstrip()
			elif line.find("CWS_KEEPALIVE") > -1:
				keepalive = line.split('=')[-1]
				self["keepalive"].text = keepalive.lstrip()
			elif line.find("CWS_INCOMING_PORT") > -1:
				incoming = line.split('=')[-1]
				self["incoming"].text = incoming.lstrip()
			elif line.find("CWS_DEBUG_PORT") > -1:
				debug = line.split('=')[-1]
				self["debug"].text = debug.lstrip()
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.able, "red": self.exit, "yellow": self.add, "blue": self.remove, "cancel": self.close}, -1)
		
	def able(self):
		lineold = "%s %s %s %s %s %s" % (self["menu"].getCurrent()[1].split()[0], self["menu"].getCurrent()[1].split()[1], self["menu"].getCurrent()[1].split()[2], self["menu"].getCurrent()[1].split()[3], self["menu"].getCurrent()[1].split()[4], self["menu"].getCurrent()[1].split()[5])
		if self["menu"].getCurrent()[2] == '#':
			enable = self["menu"].getCurrent()[1].split()[0][1:]
		else:
			enable = '#' + self["menu"].getCurrent()[1].split()[0]
		linenew = "%s %s %s %s %s %s" % (enable, self["menu"].getCurrent()[1].split()[1], self["menu"].getCurrent()[1].split()[2], self["menu"].getCurrent()[1].split()[3], self["menu"].getCurrent()[1].split()[4], self["menu"].getCurrent()[1].split()[5])
		os.system("sed -i 's/%s/%s/w' /usr/keys/newcamd.list" % (lineold, linenew))
		self.listserver()
		
	def edit(self):
		self.session.openWithCallback(self.listserver, NCLAdd, self["menu"].getCurrent()[1])
		
	def add(self):
		self.session.openWithCallback(self.listserver, NCLAdd, None)
		
	def remove(self):
		os.system("sed -i '/%s/d' /usr/keys/newcamd.list" % self["menu"].getCurrent()[1].split()[3])
		self.listserver()
		
	def exit(self):
		self.close()
		
####################################################################
class NCLAdd(ConfigListScreen, Screen):
	skin = """
<screen name="NCLAdd" position="center,center" size="1280,720" title="LBpanel Server Edit" >
		<widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
  <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="GLOBAL" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="ACTUALIZAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

	def __init__(self, session, serverline):
		self.session = session
		self.line = serverline
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel Server Edit"))
		if self.line != None:
			config.plugins.lbpanel.serveredit.value = self.line.split()[2]
			config.plugins.lbpanel.port.value = self.line.split()[3]
			config.plugins.lbpanel.login.value = self.line.split()[4]
			config.plugins.lbpanel.passw.value = self.line.split()[5]
		
		self.list = []
		self.list.append(getConfigListEntry(_("Server (ip/host)"), config.plugins.lbpanel.serveredit))
		self.list.append(getConfigListEntry(_("Port"), config.plugins.lbpanel.port))
		self.list.append(getConfigListEntry(_("User"), config.plugins.lbpanel.login))
		self.list.append(getConfigListEntry(_("Password"), config.plugins.lbpanel.passw))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Update"))
		self["key_yellow"] = StaticText(_("Global"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.ok,
			"yellow": self.param,
			"ok": self.ok
		}, -2)
		
	def param(self):
		self.session.open(NCLEditGlobal)
	
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close()
	
	def ok(self):
		if self.line != None:
			lineold = "%s %s %s %s" % (self.line.split()[2], self.line.split()[3], self.line.split()[4], self.line.split()[5])
			linenew = "%s %s %s %s" % (config.plugins.lbpanel.serveredit.value, config.plugins.lbpanel.port.value, config.plugins.lbpanel.login.value, config.plugins.lbpanel.passw.value)
			os.system("sed -i 's/%s/%s/w' /usr/keys/newcamd.list" % (lineold, linenew))
		else:
			if config.plugins.lbpanel.port.value.find(':') > -1:
				os.system("echo -e 'CWS_MULTIPLE = %s %s %s %s 01 02 03 04 05 06 07 08 09 10 11 12 13 14' >> /usr/keys/newcamd.list" % (config.plugins.lbpanel.serveredit.value, config.plugins.lbpanel.port.value, config.plugins.lbpanel.login.value, config.plugins.lbpanel.passw.value))
			else:
				os.system("echo -e 'CWS = %s %s %s %s 01 02 03 04 05 06 07 08 09 10 11 12 13 14' >> /usr/keys/newcamd.list" % (config.plugins.lbpanel.serveredit.value, config.plugins.lbpanel.port.value, config.plugins.lbpanel.login.value, config.plugins.lbpanel.passw.value))
		for i in self["config"].list:
			i[1].cancel()
		self.close()
####################################################################
class NCLEditGlobal(ConfigListScreen, Screen):
	skin = """
<screen name="NCLEditGlobal" position="center,center" size="1280,720" title="LBpanel Global parameters" >
		<widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
  <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="ACTUALIZAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel Global Parameters"))
		self.list = []
		for line in open("/usr/keys/newcamd.list"):
			if line.find("CWS_CONNECT_TIMEOUT") > -1:
				timeout = line.split('=')[-1]
				config.plugins.lbpanel.timeout.value = timeout.lstrip()
				self.list.append(getConfigListEntry(_("CWS_CONNECT_TIMEOUT"), config.plugins.lbpanel.timeout))
			elif line.find("CWS_KEEPALIVE") > -1:
				keepalive = line.split('=')[-1]
				config.plugins.lbpanel.keepalive.value = keepalive.lstrip()
				self.list.append(getConfigListEntry(_("CWS_KEEPALIVE"), config.plugins.lbpanel.keepalive))
			elif line.find("CWS_INCOMING_PORT") > -1:
				incoming = line.split('=')[-1]
				config.plugins.lbpanel.incoming.value = incoming.lstrip()
				self.list.append(getConfigListEntry(_("CWS_INCOMING_PORT"), config.plugins.lbpanel.incoming))
			elif line.find("CWS_DEBUG_PORT") > -1:
				debug = line.split('=')[-1]
				config.plugins.lbpanel.debug.value = debug.lstrip()
				self.list.append(getConfigListEntry(_("CWS_DEBUG_PORT"), config.plugins.lbpanel.debug))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Update"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.ok,
			"ok": self.ok
		}, -2)
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close()
	
	def ok(self):
		for line in open("/usr/keys/newcamd.list"):
			if line.find("CWS_CONNECT_TIMEOUT") > -1:
				os.system("sed -i '/CWS_CONNECT_TIMEOUT/d' /usr/keys/newcamd.list")
				os.system("echo -e 'CWS_CONNECT_TIMEOUT = %s' >> /usr/keys/newcamd.list" % config.plugins.lbpanel.timeout.value)
			elif line.find("CWS_KEEPALIVE") > -1:
				os.system("sed -i '/CWS_KEEPALIVE/d' /usr/keys/newcamd.list")
				os.system("echo -e 'CWS_KEEPALIVE = %s' >> /usr/keys/newcamd.list" % config.plugins.lbpanel.keepalive.value)
			elif line.find("CWS_INCOMING_PORT") > -1:
				os.system("sed -i '/CWS_INCOMING_PORT/d' /usr/keys/newcamd.list")
				os.system("echo -e 'CWS_INCOMING_PORT = %s' >> /usr/keys/newcamd.list" % config.plugins.lbpanel.incoming.value)
			elif line.find("CWS_DEBUG_PORT") > -1:
				os.system("sed -i '/CWS_DEBUG_PORT/d' /usr/keys/newcamd.list")
				os.system("echo -e 'CWS_DEBUG_PORT = %s' >> /usr/keys/newcamd.list" % config.plugins.lbpanel.debug.value)
		os.system("sed -i sed '/./!d' /usr/keys/newcamd.list")
		for i in self["config"].list:
			i[1].cancel()
		self.close()
##############################################################################
###############################################################################
class ServiceMan(Screen):
	skin = """
<screen name="ServiceMan" position="center,center" size="1150,500" title="LBpanel Softemu Control">
    #<ePixmap position="700,10" zPosition="1" size="450,700" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/fondo3.png" alphatest="blend" transparent="1" />
	<widget source="key_red" render="Label" position="20,460" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="key_green" render="Label" position="190,460" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="key_yellow" render="Label" position="360,460" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<ePixmap position="20,490" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
	<ePixmap position="190,490" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
	<ePixmap position="360,490" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/yellow.png" alphatest="blend" />
	<widget source="menu" render="Listbox" position="20,20" size="660,350" scrollbarMode="showOnDemand">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (150, 20), size = (580, 40), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (80, 80), png = 2), # index 4 is the pixmap
   		],
	"fonts": [gFont("Regular", 30),gFont("Regular", 16)],
	"itemHeight": 90
	}
			</convert>
		</widget>
	</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel SoftEmu Control"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "DirectionActions"],

		{
			"cancel": self.cancel,
			"back": self.cancel,
			"red": self.stopservice,
			"green": self.startservice,
			"yellow": self.restartservice,
		})
		self["key_red"] = StaticText(_("Stop"))
		self["key_green"] = StaticText(_("Start"))
		self["key_yellow"] = StaticText(_("ReStart"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()
		
	def CfgMenu(self):
		self.list = []
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/to.png"))
		dospng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ts.png"))
		trespng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tm.png"))
		cuatropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tcc.png"))
		cincopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tmg.png"))
		seispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tgb.png"))
		sietepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tnc.png"))
		ochopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tnew.png"))
		self.list.append((_("TestOscam"), "TestOscam", onepng))
		self.list.append((_("TestSbox"), "TestSbox", dospng))
		self.list.append((_("TestMbox"), "TestMbox", trespng))
		self.list.append((_("TestCCcam"), "TestCCcam", cuatropng))
		self.list.append((_("TestMgcamd"), "TestMgcamd", cincopng))
		self.list.append((_("TestGbox"), "TestGbox", seispng))
		self.list.append((_("TestNcam"), "TestNcam", sietepng))
		self.list.append((_("TestNewcs"), "TestNewcs", ochopng))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

	def restartservice(self):
		try:
			os.system("/etc/init.d/%s restart" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Restarting %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull") , type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def startservice(self):
		try:
			os.system("/etc/init.d/%s start" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Starting %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull"), type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def stopservice(self):
		try:
			os.system("/etc/init.d/%s stop" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Stoping %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull"), type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def cancel(self):
		self.close()
####################################################################
class MboxMan(Screen):
	skin = """
<screen name="MboxMan" position="center,center" size="1280,720" title="LBpanel ACJ Mbox Script">
    <widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="white" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" size="628,350">
      <convert type="TemplatedMultiContent">
    {"template": [ MultiContentEntryText(pos = (30, 5), size = (460, 50), flags = RT_HALIGN_LEFT, text = 0) ],
    "fonts": [gFont("Regular", 30)],
    "itemHeight": 60
    }
   </convert>
    </widget>
   <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="PARAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="REINICIAR" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="INICIAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel ACJ Mbox Script"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "DirectionActions"],

		{
			"cancel": self.cancel,
			"back": self.cancel,
			"red": self.stopservice,
			"green": self.startservice,
			"yellow": self.restartservice,
		})
		self["key_red"] = StaticText(_("Stop"))
		self["key_green"] = StaticText(_("Start"))
		self["key_yellow"] = StaticText(_("ReStart"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()
		
	def CfgMenu(self):
		self.list = []
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/MB1.png"))
		dospng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/MB2.png"))
		trespng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/MB3.png"))
		cuatropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/MB4.png"))
		self.list.append((_("waitpid0000"), "waitpid0000", onepng))
		self.list.append((_("BorraFakes"), "BorraFakes", dospng))
		self.list.append((_("BorraOffs"), "BorraOffs", trespng))
		self.list.append((_("PeerResolver"), "PeerResolver", cuatropng))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"cancel": self.close}, -1)

	def restartservice(self):
		try:
			os.system("/etc/init.d/%s restart" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Restarting %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull") , type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def startservice(self):
		try:
			os.system("/etc/init.d/%s start" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Starting %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull"), type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def stopservice(self):
		try:
			os.system("/etc/init.d/%s stop" % (self["menu"].getCurrent()[1]))
			self.session.open(MessageBox, _("Stoping %s service" % self["menu"].getCurrent()[1]), type = MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.session.open(MessageBox, _("UnSuccessfull"), type = MessageBox.TYPE_INFO, timeout = 4 )
			
	def cancel(self):
		self.close()
####################################################################

