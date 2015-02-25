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

from enigma import *
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Sources.List import List
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_CURRENT_SKIN
from Components.Button import Button
from Components.config import config, ConfigElement, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_OK
import ExtraActionBox
import sys
from Screens.Screen import Screen
from Screens.PluginBrowser import PluginBrowser
from Components.PluginComponent import plugins
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Tools.LoadPixmap import LoadPixmap
from Screens.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigClock, ConfigSelection, ConfigSubsection, ConfigYesNo, configfile, NoSave
from Components.ConfigList import ConfigListScreen
from Tools.Directories import fileExists
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.About import about
from os import environ
from OpenSSL import SSL
import os
import gettext
import LBCamEmu
import LBipk
import LBtools
import LBDaemonsList
#import LBAbout
from enigma import eEPGCache
from types import *
from enigma import *
import sys, traceback
import re
import time
import new
import _enigma
import enigma
import smtplib
import commands
import urllib

global min
min = 0
global cronvar
cronvar = 85

lang = language.getLanguage()
environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("messages", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "SystemPlugins/LBpanel/locale/"))

def _(txt):
	t = gettext.dgettext("messages", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

##################################################################
config.plugins.lbpanel.showmain = ConfigYesNo(default = True)
config.plugins.lbpanel.showepanelmenu = ConfigYesNo(default = True)
config.plugins.lbpanel.showextsoft = ConfigYesNo(default = True)
config.plugins.lbpanel.shownclsw = ConfigYesNo(default = False)
config.plugins.lbpanel.showwcsw = ConfigYesNo(default = False)
config.plugins.lbpanel.showclviewer = ConfigYesNo(default = False)
config.plugins.lbpanel.showscriptex = ConfigYesNo(default = False)
config.plugins.lbpanel.showusbunmt = ConfigYesNo(default = False)
config.plugins.lbpanel.showsetupipk = ConfigYesNo(default = False)
config.plugins.lbpanel.showpbmain = ConfigYesNo(default = False)
config.plugins.lbpanel.filtername = ConfigYesNo(default = False)
config.plugins.lbpanel.update = ConfigYesNo(default = True)
config.plugins.lbpanel.updatesettings = ConfigYesNo(default = True)
config.plugins.lbpanel.lbemail = ConfigYesNo(default = False)
config.plugins.lbpanel.lbiemail = ConfigYesNo(default = False)
config.plugins.lbpanel.lbemailto = ConfigText(default = "mail@gmail.com",fixed_size = False, visible_width=30)
config.plugins.lbpanel.smtpserver = ConfigText(default = "smtp.gmail.com:587",fixed_size = False, visible_width=30)
config.plugins.lbpanel.smtpuser = ConfigText(default = "I@gmail.com",fixed_size = False, visible_width=30)
config.plugins.lbpanel.smtppass = ConfigPassword(default = "mailpass",fixed_size = False, visible_width=15)
config.plugins.lbpanel.lbemailproto =ConfigSelection(default = "tls", choices = [
                ("tls", "tls"),
		("ssl", "ssl"),
		])                                                                
config.plugins.lbpanel.testcam = ConfigYesNo(default = False)
config.plugins.lbpanel.activeemu = ConfigText(default = "NotSelected")
##################################################################

# Check if feed is active
if not os.path.isfile("/etc/opkg/lbappstore.conf"):
	with open ('/etc/opkg/lbappstore.conf', 'a') as f: f.write ("src/gz lbutils http://appstore.linux-box.es/files" + '\n')
                                
# Generic function to send email
def sendemail(from_addr, to_addr, cc_addr,
              subject, message,
              login, password,
              smtpserver='smtp.gmail.com:587'):

    print "ENVIANDO EMAIL"
    try:
    	proto = config.plugins.lbpanel.lbemailproto.value
    	if config.plugins.lbpanel.lbemail.value == True: 
    		header  = 'From: %s\n' % from_addr
    		header += 'To: %s\n' % to_addr
    		header += 'Cc: %s\n' % cc_addr
    		header += 'Subject: %s\n\n' % subject
    		message = header + message

    		server = smtplib.SMTP(smtpserver)
    		server.ehlo()
    		server.starttls()
    		server.login(login,password)
    		problems = server.sendmail(from_addr, to_addr, message)
    		server.quit()
	if config.plugins.lbpanel.lbiemail.value == True:
		f = { 'from' : from_addr, 'to' : to_addr, 'cc' : '', 'subject' : subject, 'message' : message, 'server' : smtpserver, 'proto' : proto, 'user' : login, 'password' : password}
		url = 'https://appstore.linux-box.es/semail.php?%s' % (urllib.urlencode(f))	
		os.popen("wget --no-check-certificate '%s' -O  /tmp/.ilbmail.log" % (url))
    except:
        fo = open("/tmp/.lbemail.error","a+")
        fo.close()
        config.plugins.lbpanel.lbemail.value = False
    	config.plugins.lbpanel.lbemail.save()
    	
def lbversion():
	return ("LBpanel_0.99_Red_Bee_r19")

class LBPanel2(Screen):
	skin = """
<screen name="LBPanel2" position="0,0" size="1280,720" >
<widget source="lb_version" render="Label" position="50,605" zPosition="2" size="450,30" font="Regular;15" halign="center" valign="center" backgroundColor="#d3d3d3" foregroundColor="#000000" transparent="1" />
<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="white" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" size="628,350">
      <convert type="TemplatedMultiContent">
    {"template": [ MultiContentEntryText(pos = (30, 5), size = (460, 50), flags = RT_HALIGN_LEFT, text = 0) ],
    "fonts": [gFont("Regular", 30)],
    "itemHeight": 60
    }
   </convert>
    </widget>
    <eLabel text="MENU" position="1115,650" size="100,30" zPosition="5" font="Regular;20" valign="center" halign="center" backgroundColor="white" foregroundColor="black" transparent="0" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="SERVICIOS" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="CAMEMU" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="IPK TOOLS" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Red Bee"))
		#version = (_("Version: %s") % lbversion())
		#self["LBversion"].setText("version")
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "CCcamInfoActions", "EPGSelectActions"],
		{
			"ok": self.keyOK,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"menu": self.keyMenu,
			
		})
		self["lb_version"] = StaticText(_("Version: %s") % lbversion())
		self.list = []
		self["menu"] = List(self.list)
		self.mList()

	def mList(self):
		self.list = []
		zeropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/softcams.png"))
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/softcams.png"))
		sixpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/cardserver.png"))
		twopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/tools.png"))
		backuppng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/backup.png"))
		trespng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/seleck.png"))
		treepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/install.png"))
		fourpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/epp2.png"))
		sixpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/system.png"))
		sevenpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/addon.png"))
		cuatropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/daemons.png"))
		cincopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/infop.png"))
		settings = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/settings.png"))
		#self.list.append((_("About"),"com_zero", _("About this machine, Info about software and hardware"), zeropng))
		self.list.append((_("SoftEmus"),"com_one", _("CamEmu start-stop, Test Emu Control, Info Emus"), onepng))
		self.list.append((_("Services "),"com_two", _("Epg,Ntp,scripts,info ..."), twopng ))
		self.list.append((_("System"),"com_six", _("Kernel modules,swap,ftp,samba,crond,usb"), sixpng ))
		#self.list.append((_("Skins LCD Selector"),"com_tres", _("LCD Skins selector"), trespng ))
		self.list.append((_("Package install"),"com_four", _("Install /uninstall ipk,tar.gz en /tmp"), treepng))
		self.list.append((_("Settings"),"com_settings", _("Settings of LBpanel"), settings))
		self.list.append((_("Add-ons"),"com_seven", _("Plugins"), sevenpng))
		#self.list.append((_("LB Daemons"),"com_cuatro", _("Lista Daemons"), cuatropng))
		#self.list.append((_("Info Panel"),"com_cinco", _("Informacion Panel"), cincopng))
		self["menu"].setList(self.list)


	def exit(self):
		self.close()

	def keyOK(self, returnValue = None):
		if returnValue == None:
			returnValue = self["menu"].getCurrent()[1]
			if returnValue is "com_zero":
				self.session.open(LBAbout.About)
			if returnValue is "com_one":
				self.session.open(LBCamEmu.CamEmuPanel)
			elif returnValue is "com_two":
				self.session.open(LBtools.ToolsScreen)
			elif returnValue is "com_tree":
				self.session.open(backup.BackupSuite)
			#elif returnValue is "com_tres":
				#self.session.open(LCDselectorScreen)
			elif returnValue is "com_four":
				self.session.open(LBipk.IPKToolsScreen)
			elif returnValue is "com_five":
				self.session.open(ConfigExtentions)
			elif returnValue is "com_six":
				self.session.open(LBtools.SystemScreen)
			elif returnValue is "com_seven":
				self.session.open(PluginBrowser)
			elif returnValue is "com_settings":
				self.session.open(LBsettings)
			#elif returnValue is "com_cuatro":
				#self.session.open(LBDaemonsList.LBDaemonsList)
			#elif returnValue is "com_cinco":
				#self.session.open(info)
			else:
				print "\n[LBpanel] cancel\n"
				self.close(None)

	def keyBlue (self):
		self.session.open(LBipk.IPKToolsScreen)
				
	def keyYellow (self):
		self.session.open(LBtools.ToolsScreen)

	def keyMenu (self):
		self.session.open(descargasScreen)
		
	def keyGreen (self):
		self.session.open(LBCamEmu.emuSel2)
	
	def infoKey (self):
		self.session.openWithCallback(self.mList,info)
		
##########################################################################################
class info(Screen):
	skin = """
<screen name="info" position="center,105" size="600,570" title="lb_title">
	<ePixmap position="20,562" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
	<widget source="key_red" render="Label" position="20,532" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="MemoryLabel" render="Label" position="20,375" size="150,22" font="Regular; 20" halign="right" foregroundColor="#aaaaaa" />
	<widget source="SwapLabel" render="Label" position="20,400" size="150,22" font="Regular; 20" halign="right" foregroundColor="#aaaaaa" />
	<widget source="FlashLabel" render="Label" position="20,425" size="150,22" font="Regular; 20" halign="right" foregroundColor="#aaaaaa" />
	<widget source="memTotal" render="Label" position="180,375" zPosition="2" size="400,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="swapTotal" render="Label" position="180,400" zPosition="2" size="400,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="flashTotal" render="Label" position="180,425" zPosition="2" size="400,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="deviceLabel" render="Label" position="20,250" size="200,22" font="Regular; 20" halign="left" foregroundColor="#aaaaaa" />
	<widget source="device" render="Label" position="20,275" zPosition="2" size="560,88" font="Regular;20" halign="left" valign="top" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="Hardware" render="Label" position="230,10" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="Image" render="Label" position="230,35" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="Kernel" render="Label" position="230,60" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="EnigmaVersion" render="Label" position="230,110" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="HardwareLabel" render="Label" position="20,10" zPosition="2" size="200,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="ImageLabel" render="Label" position="20,35" zPosition="2" size="200,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="KernelLabel" render="Label" position="20,59" zPosition="2" size="200,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="EnigmaVersionLabel" render="Label" position="20,110" zPosition="2" size="200,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="nimLabel" render="Label" position="20,145" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="nim" render="Label" position="20,170" zPosition="2" size="500,66" font="Regular;20" halign="left" valign="top" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="driver" render="Label" position="230,85" zPosition="2" size="200,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="driverLabel" render="Label" position="20,85" zPosition="2" size="200,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<eLabel position="30,140" size="540,2" backgroundColor="#aaaaaa" />
	<eLabel position="30,242" size="540,2" backgroundColor="#aaaaaa" />
	<eLabel position="30,367" size="540,2" backgroundColor="#aaaaaa" />
	<eLabel position="30,454" size="540,2" backgroundColor="#aaaaaa" />
	<eLabel position="230,494" size="320,2" backgroundColor="#aaaaaa" />
	<ePixmap position="20,463" size="180,47" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/2boom.png" alphatest="blend" />
	<widget source="panelver" render="Label" position="470,463" zPosition="2" size="100,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="LBpanel" render="Label" position="215,463" zPosition="2" size="250,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="cardserver" render="Label" position="350,528" zPosition="2" size="225,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="cardserverLabel" render="Label" position="215,528" zPosition="2" size="130,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
	<widget source="softcam" render="Label" position="350,503" zPosition="2" size="225,22" font="Regular;20" halign="left" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="softcamLabel" render="Label" position="215,503" zPosition="2" size="130,22" font="Regular;20" halign="right" valign="center" backgroundColor="background" foregroundColor="#aaaaaa" transparent="1" />
 </screen>"""

 	skin = skin.replace("lb_title", _("Linux Box Panel Red Bee Edition"))
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.cancel,
			"back": self.cancel,
			"red": self.cancel,
			"ok": self.cancel,
			})
		self["key_red"] = StaticText(_("Close"))
		self["MemoryLabel"] = StaticText(_("Memory:"))
		self["SwapLabel"] = StaticText(_("Swap:"))
		self["FlashLabel"] = StaticText(_("Flash:"))
		self["memTotal"] = StaticText()
		self["swapTotal"] = StaticText()
		self["flashTotal"] = StaticText()
		self["device"] = StaticText()
		self["deviceLabel"] = StaticText(_("Devices:"))
		self["Hardware"] = StaticText()
		self["Image"] = StaticText()
		self["Kernel"] = StaticText()
		self["nim"] = StaticText()
		self["nimLabel"] = StaticText(_("Detected NIMs:"))
		self["EnigmaVersion"] = StaticText()
		self["HardwareLabel"] = StaticText(_("Hardware:"))
		self["ImageLabel"] = StaticText(_("Image:"))
		self["KernelLabel"] = StaticText(_("Kernel Version:"))
		self["EnigmaVersionLabel"] = StaticText(_("Last Upgrade:"))
		self["driver"] = StaticText()
		self["driverLabel"] = StaticText(_("Driver Version:"))
		self["LBpanel"] = StaticText(_("LBpanel Ver: 1.1"))
		self["panelver"] = StaticText()
		self["softcamLabel"] = StaticText(_("Softcam:"))
		self["softcam"] = StaticText()
		self["cardserverLabel"] = StaticText(_("Cardserver:"))
		self["cardserver"] = StaticText()
		self.memInfo()
		self.FlashMem()
		self.devices()
		self.mainInfo()
		self.verinfo()
		self.emuname()
		
	def status(self):
		path = ' '
		if fileExists("/usr/lib/opkg/status"):
			path = "/usr/lib/opkg/status"
		elif fileExists("/var/lib/opkg/status"):
			path = "/var/lib/opkg/status"
		return path
		
	def emuname(self):
		nameemu = []
		namecard = []
		if fileExists("/etc/init.d/softcam"):
			try:
				for line in open("/etc/init.d/softcam"):
					if line.find("echo") > -1:
						nameemu.append(line)
				self["softcam"].text = "%s" % nameemu[1].split('"')[1]
			except:
				self["softcam"].text = _("Not Active")
		else:
			self["softcam"].text = _("Not Installed")
		if fileExists("/etc/init.d/cardserver"):
			try:
				for line in open("/etc/init.d/cardserver"):
					if line.find("echo") > -1:
						namecard.append(line)
				self["cardserver"].text = "%s" % namecard[1].split('"')[1]
			except:
				self["cardserver"].text = _("Not Active")
		else:
			self["cardserver"].text = _("Not Installed")
		
	def devices(self):
		list = ""
		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					list += ((_("%s  %s  (%d.%03d GB free)\n") % (hdd.model(), hdd.capacity(), hdd.free()/1024 , hdd.free()%1024)))
				else:
					list += ((_("%s  %s  (%03d MB free)\n") % (hdd.model(), hdd.capacity(),hdd.free())))
		else:
			hddinfo = _("none")
		self["device"].text = list
		
	def mainInfo(self):
		listnims = ""
		package = 0
		self["Hardware"].text = about.getHardwareTypeString()
		self["Image"].text = about.getImageTypeString()
		self["Kernel"].text = about.getKernelVersionString()
		self["EnigmaVersion"].text = about.getImageVersionString()
		nims = nimmanager.nimList()
		for count in range(len(nims)):
			if count < 4:
				listnims += "%s\n" % nims[count]
			else:
				listnims += "\n"
		self["nim"].text = listnims
		for line in open(self.status()):
			if line.find("-dvb-modules") > -1 and line.find("Package:") > -1:
				package = 1
			if line.find("Version:") > -1 and package == 1:
				package = 0
				try:
					self["driver"].text = line.split()[1]
				except:
					self["driver"].text = " "
				break

	def memInfo(self):
		mem = open("/proc/meminfo", "r")
		for line in mem:
			if line.find("MemTotal:") > -1:
				memtotal = line.split()[1]
			elif line.find("MemFree:") > -1:
				memfree = line.split()[1]
			elif line.find("SwapTotal:") > -1:
				swaptotal =  line.split()[1]
			elif line.find("SwapFree:") > -1:
				swapfree = line.split()[1]
		self["memTotal"].text = _("Total: %s Kb  Free: %s Kb") % (memtotal, memfree)
		self["swapTotal"].text = _("Total: %s Kb  Free: %s Kb") % (swaptotal, swapfree)
		mem.close()
		
	def FlashMem(self):
		flash = os.popen("df | grep root")
		try:
			for line in flash:
				if line.find("root") > -1:
					self["flashTotal"].text = _("Total: %s Kb  Free: %s Kb") % (line.split()[1], line.split()[3])
		except:
			pass
		
	def verinfo(self):
		package = 0
		self["panelver"].text = " "
		for line in open(self.status()):
			if line.find("LBpanel") > -1:
				package = 1
			if line.find("Version:") > -1 and package == 1:
				package = 0
				try:
					self["panelver"].text = line.split()[1]
				except:
					self["panelver"].text = " "
				break

		
	def cancel(self):
		self.close()
####################################################################
class ConfigExtentions(ConfigListScreen, Screen):
	skin = """
<screen name="ConfigExtentions" position="center,160" size="750,370" title="lb_title">
		<widget position="15,10" size="720,300" name="config" scrollbarMode="showOnDemand" />
		<ePixmap position="10,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
		<widget source="key_red" render="Label" position="10,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
		<ePixmap position="175,358" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
		<widget source="key_green" render="Label" position="175,328" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
		<ePixmap position="340,358" zPosition="1" size="230,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/yellow.png" alphatest="blend" />
		<widget source="key_yellow" render="Label" position="340,328" zPosition="2" size="230,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
</screen>"""

	skin = skin.replace("lb_title", _("LBpanel Menu/Extension Menu Config"))
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel Menu/Extensionmenu config"))
		self.list = []
		self.list.append(getConfigListEntry(_("Show LBPanel in Main Menu"), config.plugins.lbpanel.showmain))
		self.list.append(getConfigListEntry(_("Show LBPanel in Extension Menu"), config.plugins.lbpanel.showepanelmenu))
		self.list.append(getConfigListEntry(_("Show CamEmu Manager in Extension Menu"), config.plugins.lbpanel.showextsoft))
		self.list.append(getConfigListEntry(_("Show LB-NewCamd.list switcher in Extension Menu"), config.plugins.lbpanel.shownclsw))
		self.list.append(getConfigListEntry(_("Show LB-Wicardd.conf switcher in Extension Menu"), config.plugins.lbpanel.showwcsw))
		self.list.append(getConfigListEntry(_("Show LB-CrashLog viewr in ExtensionMenu"), config.plugins.lbpanel.showclviewer))
		self.list.append(getConfigListEntry(_("Show LB-Script Executter in Extension Menu"), config.plugins.lbpanel.showscriptex))
		self.list.append(getConfigListEntry(_("Show LB-Usb Unmount in Extension Menu"), config.plugins.lbpanel.showusbunmt))
		self.list.append(getConfigListEntry(_("Show LB-Installer in Extension Menu"), config.plugins.lbpanel.showsetupipk))
		self.list.append(getConfigListEntry(_("Show PluginBrowser in LBPanel Main Menu"), config.plugins.lbpanel.showpbmain))
		self.list.append(getConfigListEntry(_("Filter by Name in download extentions"), config.plugins.lbpanel.filtername))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Restart GUI"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "EPGSelectActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.restart_einigma,
			"ok": self.save
		}, -2)
		
	def cancel(self):
		self.close(False)
		
	def restart_einigma(self):
		self.session.open(TryQuitMainloop, 3)
	
	def save(self):
		config.plugins.lbpanel.showmain.save()
		config.plugins.lbpanel.showepanelmenu.save()
		config.plugins.lbpanel.showextsoft.save()
		config.plugins.lbpanel.shownclsw.save()
		config.plugins.lbpanel.showwcsw.save()
		config.plugins.lbpanel.showclviewer.save()
		config.plugins.lbpanel.showscriptex.save()
		config.plugins.lbpanel.showusbunmt.save()
		config.plugins.lbpanel.showsetupipk.save()
		config.plugins.lbpanel.showpbmain.save()
		config.plugins.lbpanel.filtername.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("Configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )


######################################################################################
class descargasScreen(Screen):
	skin = """
	<screen name="descargasScreen" position="0,0" size="1280,720" title="LBpanel Download">
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
    <eLabel text="BORRAR" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="REINICIAR E2" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("Download Bee"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.OK,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"yellow": self.clear,
			"green": self.restartGUI,
		})
		self.list = []
		self["menu"] = List(self.list)
		self.mList()

	def mList(self):
		self.list = []
		#onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		#treepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		#sixpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		#fivepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		dospng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		cuatropng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		cincopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ipk.png"))
		#self.list.append((_("IPK installer"),"one", _("Install ipk, bh.tgz, tar.gz, nab.tgz in /tmp"), onepng ))
		#self.list.append((_("Feed installer"),"six", _("Feed installer"), sixpng ))
		#self.list.append((_("Download extensions"),"five", _("Download feeds packages"), fivepng))
		#self.list.append((_("IPK delete packages"),"four", _("Delete IPK packages"), treepng ))
		self.list.append((_("Sorys Channel List"),"dos", _("Download Sorys Channel List"), dospng ))
		self.list.append((_("Download config emus"),"cuatro", _("Download Config Emus"), cuatropng ))
		self.list.append((_("Download Picon"),"cinco", _("Download Picon"), cincopng ))
		self["menu"].setList(self.list)
		
	def exit(self):
		self.close()
		
	def clear(self):
		self.session.open(installremove)
		
	def restartGUI(self):
		self.session.open(TryQuitMainloop, 3)

	def OK(self):
		item = self["menu"].getCurrent()[1]
		#if item is "one":
			#self.session.openWithCallback(self.mList,InstallAll)
		#elif item is "four":
			#self.session.openWithCallback(self.mList,RemoveIPK)
		#elif item is "five":
			#self.session.openWithCallback(self.mList,DownloadFeed)
		#elif item is "six":
			#self.session.openWithCallback(self.mList,downfeed)
		if item is "dos":
			self.session.openWithCallback(self.mList,installsorys)
		elif item is "cuatro":
			self.session.openWithCallback(self.mList,installconfigemus)
		elif item is "cinco":
			self.session.openWithCallback(self.mList,installpicon)
			
###############################################
class installsorys(Screen):
	skin = """
<screen name="installsorys" position="0,0" size="1280,720" title="LBpanel-Download Sorys Settings">
    
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
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel-Download Sorys Settings"))
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
		os.system("opkg update")
		camdlist = os.popen("opkg list | grep sorys")
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
		
	def setup(self):
		self.session.open(Console,title = _("Installing Sorys Settings"), cmdlist = ["opkg install -force-overwrite %s" % self["menu"].getCurrent()[0]])
		
		
	def cancel(self):
		self.close()
#################################################
class installconfigemus(Screen):
	skin = """

<screen name="installconfigemus" position="0,0" size="1280,720" title="LBpanel-Download Config-Emus">
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
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel-Download Config Emus"))
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
		os.system("opkg update")
		camdlist = os.popen("opkg list | grep emucfg")
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
		
	def setup(self):
		os.system("opkg install -force-overwrite %s" % self["menu"].getCurrent()[0])
		self.mbox = self.session.open(MessageBox, _("%s is installed" % self["menu"].getCurrent()[0]), MessageBox.TYPE_INFO, timeout = 4 )
		
		
	def cancel(self):
		self.close()
#################################################
class installpicon(Screen):
	skin = """

<screen name="installpicon" position="0,0" size="1280,720" title="LBpanel-Download Picon">
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
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel-Download picon"))
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
		os.system("opkg update")
		camdlist = os.popen("opkg list | grep piconLB")
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
		
	def setup(self):
		os.system("opkg install -force-overwrite %s" % self["menu"].getCurrent()[0])
		self.mbox = self.session.open(MessageBox, _("%s is installed" % self["menu"].getCurrent()[0]), MessageBox.TYPE_INFO, timeout = 4 )
		
	def cancel(self):
		self.close()
#################################################
class installremove(Screen):
	skin = """

<screen name="installremove" position="0,0" size="1280,720" title="lb_title">
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
    <eLabel text="REMOVE" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
	  
	skin = skin.replace("lb_title", _("LBpanel - Remove Bee installed"))  
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
		camdlist = os.popen("opkg list-installed | grep -e 'sorys' -e 'emucfg' -e 'piconLB'")
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
class LBsettings(ConfigListScreen, Screen):
	skin = """
<screen name="scanhost" position="0,0" size="1280,720" title="LBpanel - Config">
   
  <widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
  <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Configuration"))
		self.list = []
		self.list.append(getConfigListEntry(_("Auto Update LBpanel"), config.plugins.lbpanel.update))
		self.list.append(getConfigListEntry(_("Auto Update Settings"), config.plugins.lbpanel.updatesettings))
		self.list.append(getConfigListEntry(_("Send email on report by local to user?"), config.plugins.lbpanel.lbemail))
		self.list.append(getConfigListEntry(_("Send email on report by proxy to user?"), config.plugins.lbpanel.lbiemail))
		self.list.append(getConfigListEntry(_("Send errors/reports to: (email)"), config.plugins.lbpanel.lbemailto))
		self.list.append(getConfigListEntry(_("Smtp server"), config.plugins.lbpanel.smtpserver))  
		self.list.append(getConfigListEntry(_("Smtp user"), config.plugins.lbpanel.smtpuser))
		self.list.append(getConfigListEntry(_("Smtp password"), config.plugins.lbpanel.smtppass))
		self.list.append(getConfigListEntry(_("Smtp protocol"), config.plugins.lbpanel.lbemailproto))
		self.list.append(getConfigListEntry(_("Enable Softcam check?"), config.plugins.lbpanel.testcam))                                                                                
		ConfigListScreen.__init__(self, self.list)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"ok": self.save
		}, -2)
		
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close(False)
	
	def save(self):
		config.plugins.lbpanel.update.save()
		config.plugins.lbpanel.updatesettings.save()
                config.plugins.lbpanel.lbemail.save()
                config.plugins.lbpanel.lbiemail.save()  
		config.plugins.lbpanel.lbemailto.save()
		config.plugins.lbpanel.smtpserver.save()
		config.plugins.lbpanel.smtpuser.save()  
		config.plugins.lbpanel.smtppass.save()
		config.plugins.lbpanel.lbemailproto.save()
		config.plugins.lbpanel.testcam.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("Configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )

################################################################################################################

####################################################################
## Cron especific function for lbpanel
class lbCron():
	def __init__(self):
		self.dialog = None

	def gotSession(self, session):
		self.session = session
		self.timer = enigma.eTimer() 
		self.timer.callback.append(self.update)
		self.timer.start(60000, True)

	def update(self):
		self.timer.stop()
		now = time.localtime(time.time())
		# cron update control, test every hour, execute a script to test.
                global cronvar
		cronvar += 1
		## Check for updates
		print "Executing update LBpanel in %s minutes" % (90 - cronvar)
		if (cronvar == 90 ):
			cronvar = 0
			if (config.plugins.lbpanel.update.value):
				os.system("sh /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/lbutils.sh testupdate &")
			if (config.plugins.lbpanel.updatesettings.value):
				os.system("sh /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/lbutils.sh testsettings &")
		if (os.path.isfile("/tmp/.lbpanel.update") and config.plugins.lbpanel.update.value):
			print "LBpanel updated"
			self.mbox = self.session.open(MessageBox,(_("LBpanel has been updated, restart Enigma2 to activate your changes.")), MessageBox.TYPE_INFO, timeout = 30 )
			os.remove("/tmp/.lbpanel.update")
			
		if (os.path.isfile("/tmp/.lbsettings.update")):
			print "LBpanel settings updated"
			self.mbox = self.session.open(MessageBox,(_("LBpanel settings has been updated, restart Enigma2 to activate your changes.")), MessageBox.TYPE_INFO, timeout = 30 )
			os.remove("/tmp/.lbsettings.update")
		# cron control epg
		if (config.plugins.lbpanel.auto.value == "yes" and config.plugins.lbpanel.epgtime.value[0] == now.tm_hour and config.plugins.lbpanel.epgtime.value[1] == now.tm_min):
			self.dload()
		# cron control epg2
		if (config.plugins.lbpanel.auto2.value == "yes" and config.plugins.lbpanel.epgtime2.value[0] == now.tm_hour and config.plugins.lbpanel.epgtime2.value[1] == now.tm_min):
			myepg = LBtools.epgscript(self.session)
			myepg.downepg()
		# reload epg
		if (os.path.isfile("/tmp/.epgreload")):
			#epgreload = LBtools.epgdmanual(self.session)
			#epgreload.reload()
			os.remove("/tmp/.epgreload")
		# cron control scan peer
		if (config.plugins.lbpanel.checkauto.value == "yes" and config.plugins.lbpanel.checkhour.value[0] == now.tm_hour and config.plugins.lbpanel.checkhour.value[1] == now.tm_min):
			self.scanpeer()
                #cron for send email
                if ((config.plugins.lbpanel.lbemail.value or config.plugins.lbpanel.lbiemail.value) and os.path.isfile("/tmp/.lbscan.end")):
                	os.remove("/tmp/.lbscan.end")
                	msg = ""
                        scaninfo = open("/tmp/.lbscan.log", "r")
                        for line in scaninfo:
                               msg += line  	
			scaninfo.close()
                	sendemail(config.plugins.lbpanel.smtpuser.value, config.plugins.lbpanel.lbemailto.value,"", "Scan report from LBpanel",msg,config.plugins.lbpanel.smtpuser.value,config.plugins.lbpanel.smtppass.value)
                # i-email error test
                if (os.path.isfile("/tmp/.ilbmail.log")):
                	log = open("/tmp/.ilbmail.log", "r")
                	msg = ""
                	for line in log:
                		msg += line
                	if ("Error sending" in msg ):
                		self.mbox = self.session.open(MessageBox,(msg), MessageBox.TYPE_INFO, timeout = 30 )
				
			log.close()
			os.remove("/tmp/.ilbmail.log")
                #cron for testcam
                print "Testing softcam  %s" % (config.plugins.lbpanel.activeemu.value)
                if (config.plugins.lbpanel.testcam.value and config.plugins.lbpanel.activeemu.value != "NotSelected" ):
                	# Test if a cam is live
                	actcam = config.plugins.lbpanel.activeemu.value
                	actcam = actcam.replace("camemu.", "")
                	if ( int(commands.getoutput('pidof %s |wc -w' % actcam)) == 0):
                		print "Restarting softcam %s" % (config.plugins.lbpanel.activeemu.value)
                		os.system("/usr/CamEmu/%s restart &" % config.plugins.lbpanel.activeemu.value )
				if (config.plugins.lbpanel.lbemail.value or config.plugins.lbpanel.lbiemail.value):
					if os.path.exists("/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/templates/errorcam.msg"):
						f = open("/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/templates/errorcam.msg")
						subj = f.readline()
						msg = f.read()
						f.close
						subj = subj.replace(".cam.",actcam)
						msg = msg.replace(".cam.",actcam)
					else:
						subj = _("Softcam error")
						msg = _('The cam %s appears to malfunction.\nService has been restarted.\nLBpanel\n') % actcam
					sendemail(config.plugins.lbpanel.smtpuser.value, config.plugins.lbpanel.lbemailto.value,"" ,subj ,msg, config.plugins.lbpanel.smtpuser.value,config.plugins.lbpanel.smtppass.value)
		if config.plugins.lbpanel.autosave.value != '0':
			global min
			if min > int(config.plugins.lbpanel.autosave.value) and config.plugins.lbpanel.epgtime.value[1] != now.tm_min:
				min = 0
				self.save_load_epg()
				if config.plugins.lbpanel.autobackup.value:
					self.autobackup()
			else:
				min = min + 1
		# Test errors
		if (os.path.isfile("/tmp/.lbemail.error")):
			print "LBpanel settings updated"
			self.mbox = self.session.open(MessageBox,(_("Email send error:\nYour system not support send local email\nPlease select proxy option to send email")), MessageBox.TYPE_ERROR, timeout = 30 )
			os.remove("/tmp/.lbemail.error")
		self.timer.start(60000, True)
		
	def autobackup(self):
		os.system("gzip -c %sepg.dat > %sepgtmp/epg.dat.gz" % (config.plugins.lbpanel.direct.value, config.plugins.lbpanel.direct.value))
		
	def save_load_epg(self):
		epgcache = new.instancemethod(_enigma.eEPGCache_save,None,eEPGCache)
		epgcache = eEPGCache.getInstance().save()
		epgcache = new.instancemethod(_enigma.eEPGCache_load,None,eEPGCache)
		epgcache = eEPGCache.getInstance().load()

	def scanpeer(self):
		os.system("/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/lbscan.py %s %s %s %s &" % (config.plugins.lbpanel.checktype.value, config.plugins.lbpanel.autocheck.value, config.plugins.lbpanel.checkoff.value, config.plugins.lbpanel.warnonlyemail.value))
	
	def dload(self):
		try:
                        os.system("wget -q http://appstore.linux-box.es/epg/epg.dat.gz -O %sepg.dat.gz" % (config.plugins.lbpanel.direct.value))
                        if fileExists("%sepg.dat" % config.plugins.lbpanel.direct.value):
                                os.unlink("%sepg.dat" % config.plugins.lbpanel.direct.value)
                                os.system("rm -f %sepg.dat" % config.plugins.lbpanel.direct.value)
                        if not os.path.exists("%sepgtmp" % config.plugins.lbpanel.direct.value):  
                                os.system("mkdir -p %sepgtmp" % config.plugins.lbpanel.direct.value)
                        os.system("cp -f %sepg.dat.gz %sepgtmp" % (config.plugins.lbpanel.direct.value, config.plugins.lbpanel.direct.value))
                        os.system("gzip -df %sepg.dat.gz" % config.plugins.lbpanel.direct.value)
                        os.chmod("%sepg.dat" % config.plugins.lbpanel.direct.value, 0644)
                        self.mbox = self.session.open(MessageBox,(_("EPG downloaded")), MessageBox.TYPE_INFO, timeout = 4 )
                        epgcache = new.instancemethod(_enigma.eEPGCache_load,None,eEPGCache)
                        epgcache = eEPGCache.getInstance().load()

#			os.system("wget -q http://www.xmltvepg.be/dplus/epg.dat.gz -O %sepg.dat.gz" % (config.plugins.lbpanel.lang.value, config.plugins.lbpanel.direct.value))
#			if fileExists("%sepg.dat" % config.plugins.lbpanel.direct.value):
#				os.unlink("%sepg.dat" % config.plugins.lbpanel.direct.value)
#				os.system("rm -f %sepg.dat" % config.plugins.lbpanel.direct.value)
#			if not os.path.exists("%sepgtmp" % config.plugins.lbpanel.direct.value):
#				os.system("mkdir -p %sepgtmp" % config.plugins.lbpanel.direct.value)
#			os.system("cp -f %sepg.dat.gz %sepgtmp" % (config.plugins.lbpanel.direct.value, config.plugins.lbpanel.direct.value))
#			os.system("gzip -df %sepg.dat.gz" % config.plugins.lbpanel.direct.value)
#			if fileExists("%sepg.dat" % config.plugins.lbpanel.direct.value):
#				os.chmod("%sepg.dat" % config.plugins.lbpanel.direct.value, 0644)
#			epgcache = new.instancemethod(_enigma.eEPGCache_load,None,eEPGCache)
#			epgcache = eEPGCache.getInstance().load()
#			self.mbox = self.session.open(MessageBox,(_("EPG downloaded")), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.mbox = self.session.open(MessageBox,(_("Sorry, EPG download error")), MessageBox.TYPE_INFO, timeout = 4 )
#####################################################
def main(session, **kwargs):
	session.open(epgdn2)
##############################################################################
pEmu = lbCron()
##############################################################################
def sessionstart(reason,session=None, **kwargs):
	if reason == 0:
		pEmu.gotSession(session)
##############################################################################
def main(session, **kwargs):
	session.open(LBPanel2)

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("LBpanel"), main, _("Linux_Box_Panel"), 48)]
	return []

def extsoft(session, **kwargs):
	session.open(LBCamEmu.emuSel2)
	
def nclsw(session, **kwargs):
	session.open(LBCamEmu.NCLSwp2)
	
def wcsw(session, **kwargs):
	session.open(LBCamEmu.wicconfsw)
	
def clviewer(session, **kwargs):
	session.open(LBtools.CrashLogScreen)
	
def scriptex(session, **kwargs):
	session.open(LBtools.ScriptScreen)
	
def usbunmt(session, **kwargs):
	session.open(LBtools.UsbScreen)
	
def setupipk(session, **kwargs):
	session.open(LBipk.InstallAll)
	
def Plugins(**kwargs):
	list = [PluginDescriptor(name=_("LBpanel - Red Bee"), description=_("Linux-Box Panel by LBTEAM"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon="images/LBPanel.png", fnc=main)]
	if config.plugins.lbpanel.showepanelmenu.value:
		list.append(PluginDescriptor(name=_("LBpanel"), description=_("Linux-Box Panel"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main))
	if config.plugins.lbpanel.showextsoft.value:
		list.append(PluginDescriptor(name=_("CamEmu Manager"), description=_("Start, Stop, Restart Sofcam/Cardserver"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=extsoft))
	if config.plugins.lbpanel.shownclsw.value:
		list.append(PluginDescriptor(name=_("LB-Newcamd.list switcher"), description=_("Switch newcamd.list with remote conrol"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=nclsw))
	if config.plugins.lbpanel.showwcsw.value:
		list.append(PluginDescriptor(name=_("LB-Wicardd.conf switcher"), description=_("Switch wicardd.conf with remote conrol"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=wcsw))
	if config.plugins.lbpanel.showclviewer.value:
		list.append(PluginDescriptor(name=_("LB-Crashlog viewer"), description=_("Switch newcamd.list with remote conrol"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=clviewer))
	if config.plugins.lbpanel.showscriptex.value:
		list.append(PluginDescriptor(name=_("LB-Script Executer"), description=_("Start scripts from /usr/script"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=scriptex))
	if config.plugins.lbpanel.showusbunmt.value:
		list.append(PluginDescriptor(name=_("LB-Unmount USB"), description=_("Unmount usb devices"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=usbunmt))
	if config.plugins.lbpanel.showsetupipk.value:
		list.append(PluginDescriptor(name=_("LB-Installer"), description=_("install & forced install ipk, bh.tgz, tar.gz, nab.tgz from /tmp"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=setupipk))
	if config.plugins.lbpanel.showmain.value:
		list.append(PluginDescriptor(name=_("LBPanel"), description=_("LBTeam Panel Plugin"), where = [PluginDescriptor.WHERE_MENU], fnc=menu))
	list.append(PluginDescriptor(name=_("LBPanel"), description=_("LBTeam Panel Plugin"), where = [PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc = sessionstart))
	return list


