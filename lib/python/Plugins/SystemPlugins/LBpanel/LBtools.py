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
# Swap code based on original alibabu

from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.Sources.StaticText import StaticText
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigClock, ConfigSelection, ConfigSubsection, ConfigYesNo,  config, configfile
from Components.ConfigList import ConfigListScreen
from Components.Harddisk import harddiskmanager
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Input import Input
from Tools.LoadPixmap import LoadPixmap
from Screens.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Tools.Directories import fileExists
from Plugins.Plugin import PluginDescriptor
from Components.Language import language
from Components.ScrollLabel import ScrollLabel
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigSelection, ConfigSubsection, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from ServiceReference import ServiceReference
from time import *
from enigma import eEPGCache
from types import *
from enigma import *
import sys, traceback
import re
import new
import _enigma
import enigma
import time
import datetime
from os import environ
import os
import os.path 
import gettext
import MountManager
import RestartNetwork
import urllib

lang = language.getLanguage()
environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("messages", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "SystemPlugins/LBpanel/locale/"))

def mountp():
	pathmp = []
	if fileExists("/proc/mounts"):
		for line in open("/proc/mounts"):
			if line.find("/dev/sd") > -1:
				pathmp.append(line.split()[1].replace('\\040', ' ') + "/")
	pathmp.append("/usr/share/enigma2/")
	return pathmp

def _(txt):
	t = gettext.dgettext("messages", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t
######################################################################################
config.plugins.lbpanel = ConfigSubsection()
config.plugins.lbpanel.scriptpath = ConfigSelection(default = "/usr/CamEmu/script/", choices = [
		("/usr/CamEmu/script/", _("/usr/CamEmu/script/")),
		("/media/hdd/script/", _("/media/hdd/script/")),
		("/media/usb/script/", _("/media/usb/script/")),
])
config.plugins.lbpanel.scriptpath1 = ConfigSelection(default = "/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/libmem/", choices = [
		("/usr/script/", _("/usr/script/")),
		("/media/hdd/script/", _("/media/hdd/script/")),
		("/media/usb/script/", _("/media/usb/script/")),
])
config.plugins.lbpanel.direct = ConfigSelection(default = "/media/hdd/", choices = [
		("/media/hdd/", _("/media/hdd/")),
		("/media/usb/", _("/media/usb/")),
		("/usr/share/enigma2/", _("/usr/share/enigma2/")),
		("/media/cf/", _("/media/cf/")),
])
config.plugins.lbpanel.auto = ConfigSelection(default = "no", choices = [
		("no", _("no")),
		("yes", _("yes")),
		])
config.plugins.lbpanel.auto2 = ConfigSelection(default = "no", choices = [
                ("no", _("no")),
		("yes", _("yes")),
		])
                                                
config.plugins.lbpanel.lang = ConfigSelection(default = "es", choices = [
		("es", _("spain d+")),
		])
config.plugins.lbpanel.epgtime = ConfigClock(default = ((16*60) + 15) * 60) # 18:15
config.plugins.lbpanel.epgtime2 = ConfigClock(default = ((16*60) + 15) * 60)
#config.plugins.lbpanel.weekday = ConfigSelection(default = "01", choices = [
#		("00", _("Mo")),
#		("01", _("Tu")),
#		("02", _("We")),
#		("03", _("Th")),
#		("04", _("Fr")),
#		("05", _("Sa")),
#		("06", _("Su")),
#		])
######################################################################
config.plugins.lbpanel.min = ConfigSelection(default = "*", choices = [
		("*", "*"),
		("5", "5"),
		("10", "10"),
		("15", "15"),
		("20", "20"),
		("25", "25"),
		("30", "30"),
		("35", "35"),
		("40", "40"),
		("45", "45"),
		("50", "50"),
		("55", "55"),
		])
config.plugins.lbpanel.hour = ConfigSelection(default = "*", choices = [
		("*", "*"),
		("0", "0"),
		("1", "1"),
		("2", "2"),
		("3", "3"),
		("4", "4"),
		("5", "5"),
		("6", "6"),
		("7", "7"),
		("8", "8"),
		("9", "9"),
		("10", "10"),
		("11", "11"),
		("12", "12"),
		("13", "13"),
		("14", "14"),
		("15", "15"),
		("16", "16"),
		("17", "17"),
		("18", "18"),
		("19", "19"),
		("20", "20"),
		("21", "21"),
		("22", "22"),
		("23", "23"),
		])
config.plugins.lbpanel.dayofmonth = ConfigSelection(default = "*", choices = [
		("*", "*"),
		("1", "1"),
		("2", "2"),
		("3", "3"),
		("4", "4"),
		("5", "5"),
		("6", "6"),
		("7", "7"),
		("8", "8"),
		("9", "9"),
		("10", "10"),
		("11", "11"),
		("12", "12"),
		("13", "13"),
		("14", "14"),
		("15", "15"),
		("16", "16"),
		("17", "17"),
		("18", "18"),
		("19", "19"),
		("20", "20"),
		("21", "21"),
		("22", "22"),
		("23", "23"),
		("24", "24"),
		("25", "25"),
		("26", "26"),
		("27", "27"),
		("28", "28"),
		("29", "29"),
		("30", "30"),
		("31", "31"),
		])
config.plugins.lbpanel.month = ConfigSelection(default = "*", choices = [
		("*", "*"),
		("1", _("Jan.")),
		("2", _("Feb.")),
		("3", _("Mar.")),
		("4", _("Apr.")),
		("5", _("May")),
		("6", _("Jun.")),
		("7", _("Jul")),
		("8", _("Aug.")),
		("9", _("Sep.")),
		("10", _("Oct.")),
		("11", _("Nov.")),
		("12", _("Dec.")),
		])
config.plugins.lbpanel.dayofweek = ConfigSelection(default = "*", choices = [
		("*", "*"),
		("0", _("Su")),
		("1", _("Mo")),
		("2", _("Tu")),
		("3", _("We")),
		("4", _("Th")),
		("5", _("Fr")),
		("6", _("Sa")),
		])
config.plugins.lbpanel.command = ConfigText(default="/usr/bin/", visible_width = 70, fixed_size = False)
config.plugins.lbpanel.every = ConfigSelection(default = "0", choices = [
		("0", _("No")),
		("1", _("Min")),
		("2", _("Hour")),
		("3", _("Day of month")),
		("4", _("Month")),
		("5", _("Day of week")),
		])
######################################################################################
config.plugins.lbpanel.manual = ConfigSelection(default = "0", choices = [
		("0", _("Auto")),
		("1", _("Manual")),
		])
config.plugins.lbpanel.manualserver = ConfigText(default="ntp.ubuntu.com", visible_width = 70, fixed_size = False)
config.plugins.lbpanel.server = ConfigSelection(default = "es.pool.ntp.org", choices = [
		("ao.pool.ntp.org",_("Angola")),
		("mg.pool.ntp.org",_("Madagascar")),
		("za.pool.ntp.org",_("South Africa")),
		("tz.pool.ntp.org",_("Tanzania")),
		("bd.pool.ntp.org",_("Bangladesh")),
		("cn.pool.ntp.org",_("China")),
		("hk.pool.ntp.org",_("Hong Kong")),
		("in.pool.ntp.org",_("India")),
		("id.pool.ntp.org",_("Indonesia")),
		("ir.pool.ntp.org",_("Iran")),
		("jp.pool.ntp.org",_("Japan")),
		("kz.pool.ntp.org",_("Kazakhstan")),
		("kr.pool.ntp.org",_("Korea")),
		("my.pool.ntp.org",_("Malaysia")),
		("pk.pool.ntp.org",_("Pakistan")),
		("ph.pool.ntp.org",_("Philippines")),
		("sg.pool.ntp.org",_("Singapore")),
		("tw.pool.ntp.org",_("Taiwan")),
		("th.pool.ntp.org",_("Thailand")),
		("tr.pool.ntp.org",_("Turkey")),
		("ae.pool.ntp.org",_("United Arab Emirates")),
		("uz.pool.ntp.org",_("Uzbekistan")),
		("vn.pool.ntp.org",_("Vietnam")),
		("at.pool.ntp.org",_("Austria")),
		("by.pool.ntp.org",_("Belarus")),
		("be.pool.ntp.org",_("Belgium")),
		("bg.pool.ntp.org",_("Bulgaria")),
		("cz.pool.ntp.org",_("Czech Republic")),
		("dk.pool.ntp.org",_("Denmark")),
		("ee.pool.ntp.org",_("Estonia")),
		("fi.pool.ntp.org",_("Finland")),
		("fr.pool.ntp.org",_("France")),
		("de.pool.ntp.org",_("Germany")),
		("gr.pool.ntp.org",_("Greece")),
		("hu.pool.ntp.org",_("Hungary")),
		("ie.pool.ntp.org",_("Ireland")),
		("it.pool.ntp.org",_("Italy")),
		("lv.pool.ntp.org",_("Latvia")),
		("lt.pool.ntp.org",_("Lithuania")),
		("lu.pool.ntp.org",_("Luxembourg")),
		("mk.pool.ntp.org",_("Macedonia")),
		("md.pool.ntp.org",_("Moldova")),
		("nl.pool.ntp.org",_("Netherlands")),
		("no.pool.ntp.org",_("Norway")),
		("pl.pool.ntp.org",_("Poland")),
		("pt.pool.ntp.org",_("Portugal")),
		("ro.pool.ntp.org",_("Romania")),
		("ru.pool.ntp.org",_("Russian Federation")),
		("sk.pool.ntp.org",_("Slovakia")),
		("si.pool.ntp.org",_("Slovenia")),
		("es.pool.ntp.org",_("Spain")),
		("se.pool.ntp.org",_("Sweden")),
		("ch.pool.ntp.org",_("Switzerland")),
		("ua.pool.ntp.org",_("Ukraine")),
		("uk.pool.ntp.org",_("United Kingdom")),
		("bs.pool.ntp.org",_("Bahamas")),
		("ca.pool.ntp.org",_("Canada")),
		("gt.pool.ntp.org",_("Guatemala")),
		("mx.pool.ntp.org",_("Mexico")),
		("pa.pool.ntp.org",_("Panama")),
		("us.pool.ntp.org",_("United States")),
		("au.pool.ntp.org",_("Australia")),
		("nz.pool.ntp.org",_("New Zealand")),
		("ar.pool.ntp.org",_("Argentina")),
		("br.pool.ntp.org",_("Brazil")),
		("cl.pool.ntp.org",_("Chile")),
		])
config.plugins.lbpanel.onoff = ConfigSelection(default = "0", choices = [
		("0", _("No")),
		("1", _("Yes")),
		])
config.plugins.lbpanel.time = ConfigSelection(default = "30", choices = [
		("30", _("30 min")),
		("1", _("60 min")),
		("2", _("120 min")),
		("3", _("180 min")),
		("4", _("240 min")),
		])
config.plugins.lbpanel.TransponderTime = ConfigSelection(default = "0", choices = [
		("0", _("Off")),
		("1", _("On")),
		])
config.plugins.lbpanel.cold = ConfigSelection(default = "0", choices = [
		("0", _("No")),
		("1", _("Yes")),
		])
config.plugins.lbpanel.autosave = ConfigSelection(default = '0', choices = [
		('0', _("Off")),
		('29', _("30 min")),
		('59', _("60 min")),
		('119', _("120 min")),
		('179', _("180 min")),
		('239', _("240 min")),
		])
config.plugins.lbpanel.autobackup = ConfigYesNo(default = False)
######################################################################################
## lbscan section
config.plugins.lbpanel.checkauto = ConfigSelection(default = "no", choices = [
               ("yes", _("Yes")),
               ("no", _("No")), 
])
config.plugins.lbpanel.autocheck = ConfigSelection(default = "yes", choices = [
               ("yes", _("Yes")),   
               ("no", _("No")),    
 ])

config.plugins.lbpanel.checktype = ConfigSelection(default = "fast", choices = [
               ("fast", _("Fast")),   
               ("full", _("Full")),    
               ])
                              
config.plugins.lbpanel.checkhour = ConfigClock(default = ((18*60) + 30) * 60) # 20:30

config.plugins.lbpanel.checkoff = ConfigSelection(default = "yes", choices = [
               ("yes", _("Yes")),
               ("no", _("No")), 
])
config.plugins.lbpanel.lbemail = ConfigYesNo(default = False)
config.plugins.lbpanel.warnonlyemail = ConfigSelection(default = "yes", choices = [
               ("yes", _("Yes")),   
               ("no", _("No")), 
])                              
config.plugins.lbpanel.lbemailto = ConfigText(default = "mail@gmail.com",fixed_size = False, visible_width=30) 
config.plugins.lbpanel.smtpserver = ConfigText(default = "smtp.gmail.com:587",fixed_size = False, visible_width=30)
config.plugins.lbpanel.smtpuser = ConfigText(default = "I@gmail.com",fixed_size = False, visible_width=30)
config.plugins.lbpanel.smtppass = ConfigPassword(default = "mailpass",fixed_size = False, visible_width=15)
#Compatibility for any image
config.misc.useTransponderTime = ConfigYesNo(default = False)
config.tv.lastservice = ConfigText(default = "")
#####################################################################################
## NTP Server init
if config.plugins.lbpanel.cold.value == "1":
	# NTP Server init at start
	if not fileExists("/usr/bin/ntpdate"):
		os.system("tar -C/ -xzpvf /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.tar.gz")
	os.system("killall -9 ntpdate")
	if config.plugins.lbpanel.manual.value == "0":
		os.system("/usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.server.value))
	else:
		os.system("/usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.manualserver.value))			                                                                                                                                                                                                                                                                                                                                                                                                                 

class ToolsScreen(Screen):
	skin = """
		<screen name="ToolsScreen" position="0,0" size="1280,720" title="LBpanel - Services">
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
    <eLabel text="HDD DORMIR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Services"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.keyOK,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.GreenKey,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("HDD sleep"))
		self.list = []
		self["menu"] = List(self.list)
		self.mList()

	def mList(self):
		self.list = []
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/crash.png"))
		twopng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/info2.png"))
		treepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/epg.png"))
		fivepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/script.png"))
		sixpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/ntp.png"))
		sevenpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/libmemoria.png"))
		dospng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/net1.png"))
		eightpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/scan.png"))
		self.list.append((_("Tools Crashlog"),"com_one", _("Manage crashlog files"), onepng ))
		self.list.append((_("System Info"),"com_two", _("System info (free, dh -f)"), twopng ))
		self.list.append((_("Download D+ EPG"),"com_tree", _("Download D+ EPG"), treepng ))
		self.list.append((_("SAT Down D+ EPG"),"com_four", _("Download D+ EPG"), treepng ))
		self.list.append((_("Scan Peer Security"),"com_scan", _("Check host security"), eightpng ))
		self.list.append((_("NTP Sync"),"com_six", _("Ntp sync: 30 min,60 min,120 min, 240"), sixpng ))
		self.list.append((_("User Scripts"),"com_five", _("User Scripts"), fivepng ))
		self.list.append((_("Free Memory"),"com_seven", _("Launcher free memory"), sevenpng ))
		self.list.append((_("Network"),"com_dos", _("Restart network"), dospng ))
		self["menu"].setList(self.list)

	def exit(self):
		self.close()
		
	def GreenKey(self):
		ishdd = open("/proc/mounts", "r")
		for line in ishdd:
			if line.find("/media/hdd") > -1:
				mountpointname = line.split()
				os.system("hdparm -y %s" % (mountpointname[0]))
				self.mbox = self.session.open(MessageBox,_("HDD go sleep"), MessageBox.TYPE_INFO, timeout = 4 )

	
		
	def keyOK(self, returnValue = None):
		if returnValue == None:
			returnValue = self["menu"].getCurrent()[1]
			if returnValue is "com_one":
				self.session.openWithCallback(self.mList,CrashLogScreen)
			elif returnValue is "com_two":
				self.session.openWithCallback(self.mList,Info2Screen)
			elif returnValue is "com_tree":
				self.session.open(epgdn)
			elif returnValue is "com_four":
				self.session.open(epgscript)
			elif returnValue is "com_five":
				self.session.openWithCallback(self.mList, ScriptScreen)
			elif returnValue is "com_six":
				self.session.openWithCallback(self.mList, NTPScreen)
			elif returnValue is "com_seven":
				self.session.open(Console,title = _("Free Memory"), cmdlist = ["sh /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/libmem/PULSE_OK.sh"])
			elif returnValue is "com_dos":
				self.session.open(RestartNetwork.RestartNetwork)
			elif returnValue is "com_scan":
                                self.session.open(scanhost)
			else:
				print "\n[BackupSuite] cancel\n"
				self.close(None)
###############################################################################
class SwapScreen2(Screen):
	skin = """
		<screen name="SwapScreen2" position="0,0" size="1280,720" title="LBpanel - Swap Manager">
				  
	<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
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
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - Swap Manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.Menu,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
		})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.Menu()
		
	def Menu(self):
		self.list = []
		minispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/swapmini.png"))
		minisonpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/swapminion.png"))
		for line in mountp():
			if line not in "/usr/share/enigma2/":
				try:
					if self.swapiswork() in line:
						self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minisonpng, line))
					else:
						self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minispng, line))
				except:
					self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minispng, line))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.MenuDo, "cancel": self.close}, -1)
		
	def swapiswork(self):
		if fileExists("/proc/swaps"):
			for line in open("/proc/swaps"):
				if line.find("media") > -1:
					return line.split()[0][:-9]
		else:
			return " "
		
	def MenuDo(self):
		swppath = self["menu"].getCurrent()[3] + "swapfile"
		self.session.openWithCallback(self.Menu,SwapScreen, swppath)
	
	def exit(self):
		self.close()
####################################################################
class SwapScreen(Screen):
	skin = """
		<screen name="SwapScreen" position="0,0" size="1280,720" title="LBpanel - Swap Manager">
		  
	<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 3 is the Description
		MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (50, 40), png = 3), # index 4 is the pixmap
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
   </screen>"""

	def __init__(self, session, swapdirect):
		self.swapfile = swapdirect
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("Add Swap Manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.CfgMenuDo,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
		})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()

	def isSwapPossible(self):
		for line in open("/proc/mounts"):
			fields= line.rstrip('\n').split()
			if fields[1] == "%s" % self.swapfile[:-9]:
				if fields[2] == 'ext2' or fields[2] == 'ext3' or fields[2] == 'ext4' or fields[2] == 'vfat':
					return 1
				else:
					return 0
		return 0
		
	def isSwapRun(self):
		try:
			for line in open('/proc/swaps'):
				if line.find(self.swapfile) > -1:
					return 1
			return 0
		except:
			pass
			
	def isSwapSize(self):
		try:
			swapsize = os.path.getsize(self.swapfile) / 1048576
			return ("%sMb" % swapsize)
		except:
			pass
			
	def makeSwapFile(self, size):
		try:
			os.system("dd if=/dev/zero of=%s bs=1024 count=%s" % (self.swapfile, size))
			os.system("mkswap %s" % (self.swapfile))
			self.mbox = self.session.open(MessageBox,_("Swap file created"), MessageBox.TYPE_INFO, timeout = 4 )
			self.CfgMenu()
		except:
			pass
	
	def CfgMenu(self):
		self.list = []
		minispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/swapmini.png"))
		minisonpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/swapminion.png"))
		if self.isSwapPossible():
			if os.path.exists(self.swapfile):
				if self.isSwapRun() == 1:
					self.list.append((_("Swap off"),"5", (_("Swap on %s off (%s)") % (self.swapfile[7:10].upper(), self.isSwapSize())), minisonpng))
				else:
					self.list.append((_("Swap on"),"4", (_("Swap on %s on (%s)") % (self.swapfile[7:10].upper(), self.isSwapSize())), minispng))
					self.list.append((_("Remove swap"),"7",( _("Remove swap on %s (%s)") % (self.swapfile[7:10].upper(), self.isSwapSize())), minispng))
			else:
				self.list.append((_("Make swap"),"11", _("Make swap on %s (128MB)") % self.swapfile[7:10].upper(), minispng))
				self.list.append((_("Make swap"),"12", _("Make swap on %s (256MB)") % self.swapfile[7:10].upper(), minispng))
				self.list.append((_("Make swap"),"13", _("Make swap on %s (512MB)") % self.swapfile[7:10].upper(), minispng))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.CfgMenuDo, "cancel": self.close}, -1)
			
	def CfgMenuDo(self):
		m_choice = self["menu"].getCurrent()[1]
		if m_choice is "4":
			try:
				for line in open("/proc/swaps"):
					if  line.find("swapfile") > -1:
						os.system("swapoff %s" % (line.split()[0]))
			except:
				pass
			os.system("swapon %s" % (self.swapfile))
			os.system("sed -i '/swap/d' /etc/fstab")
			os.system("echo -e '%s/swapfile swap swap defaults 0 0' >> /etc/fstab" % self.swapfile[:10])
			self.mbox = self.session.open(MessageBox,_("Swap file started"), MessageBox.TYPE_INFO, timeout = 4 )
			self.CfgMenu()
		elif m_choice is "5":
			os.system("swapoff %s" % (self.swapfile))
			os.system("sed -i '/swap/d' /etc/fstab")
			self.mbox = self.session.open(MessageBox,_("Swap file stoped"), MessageBox.TYPE_INFO, timeout = 4 )
			self.CfgMenu()
		elif m_choice is "11":
			self.makeSwapFile("131072")

		elif m_choice is "12":
			self.makeSwapFile("262144")

		elif m_choice is "13":
			self.makeSwapFile("524288")

		elif m_choice is "7":
			os.system("rm %s" % (self.swapfile))
			self.mbox = self.session.open(MessageBox,_("Swap file removed"), MessageBox.TYPE_INFO, timeout = 4 )
			self.CfgMenu()
			
	def exit(self):
		self.close()
####################################################################
class UsbScreen(Screen):
	skin = """
<screen name="UsbScreen" position="center,160" size="1150,500" title="LBpanel - Unmount manager">
  #<ePixmap position="700,10" zPosition="1" size="450,700" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/fondo18.png" alphatest="blend" transparent="1" />
	<ePixmap position="20,488" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
	<widget source="key_red" render="Label" position="20,458" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="key_green" render="Label" position="190,458" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget source="key_yellow" render="Label" position="360,458" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<ePixmap position="190,488" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
	<ePixmap position="360,488" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/yellow.png" alphatest="blend" />
	<widget source="menu" render="Listbox" position="20,20" size="660,450" scrollbarMode="showOnDemand">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
		MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (100, 60), png = 2), # index 4 is the pixmap
			],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 70
	}
			</convert>
		</widget>
	</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - Unmount manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.Ok,
			"yellow": self.CfgMenu,
			})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("UnMount"))
		self["key_yellow"] = StaticText(_("reFresh"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()
		
	def CfgMenu(self):
		self.list = []
		minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/usbico.png"))
		hddlist = harddiskmanager.HDDList()
		hddinfo = ""
		if hddlist:
			for count in range(len(hddlist)):
				hdd = hddlist[count][1]
				devpnt = self.devpoint(hdd.mountDevice())
				if hdd.mountDevice() != '/media/hdd':
					if devpnt != None:
						if int(hdd.free()) > 1024:
							self.list.append(("%s" % hdd.model(),"%s  %s  %s (%d.%03d GB free)" % (devpnt, self.filesystem(hdd.mountDevice()),hdd.capacity(), hdd.free()/1024 , hdd.free()%1024 ), minipng, devpnt))
						else:
							self.list.append(("%s" % hdd.model(),"%s  %s  %s (%03d MB free)" % (devpnt, self.filesystem(hdd.mountDevice()), hdd.capacity(),hdd.free()), minipng, devpnt))
		else:
			hddinfo = _("none")
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)
		
	def Ok(self):
		try:
			item = self["menu"].getCurrent()[3]
			os.system("umount -f %s" % item)
			self.mbox = self.session.open(MessageBox,_("Unmounted %s" % item), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			pass
		self.CfgMenu()
		
	def filesystem(self, mountpoint):
		try:
			for line in open("/proc/mounts"):
				if line.find(mountpoint)  > -1:
					return "%s  %s" % (line.split()[2], line.split()[3].split(',')[0])
		except:
			pass
			
	def devpoint(self, mountpoint):
		try:
			for line in open("/proc/mounts"):
				if line.find(mountpoint)  > -1:
					return line.split()[0]
		except:
			pass
			
	def exit(self):
		self.close()
		
####################################################################
class ScriptScreen(Screen):
	skin = """
	<screen name="ScriptScreen" position="0,0" size="1280,720" title="LBpanel - User Script" >
	   <widget name="list" position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" scrollbarMode="showOnDemand" />
  <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="CONFIG" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.session = session
		self.setTitle(_("LBpanel - User Script"))
		self.scrpit_menu()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Config"))
		self["actions"] = ActionMap(["OkCancelActions","ColorActions"], {"ok": self.run, "red": self.exit, "green": self.config_path, "cancel": self.close}, -1)
		
	def scrpit_menu(self):
		list = []
		try:
			list = os.listdir("%s" % config.plugins.lbpanel.scriptpath.value[:-1])
			list = [x[:-3] for x in list if x.endswith('.sh')]
		except:
			list = []
		list.sort()
		self["list"] = MenuList(list)
		
	def run(self):
		script = self["list"].getCurrent()
		if script is not None:
			name = ("%s%s.sh" % (config.plugins.lbpanel.scriptpath.value, script))
			os.chmod(name, 0755)
			self.session.open(Console, script.replace("_", " "), cmdlist=[name])
			
	def config_path(self):
		self.session.open(ConfigScript)

	def exit(self):
		self.close()
########################################################################
class ConfigScript(ConfigListScreen, Screen):
	skin = """
<screen name="ConfigScript" position="0,0" size="1280,720" title="LBpanel - Config script Executer">
		<widget name="config" position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" scrollbarMode="showOnDemand" />

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
		self.setTitle(_("LBpanel - Config script Executer"))
		self.list = []
		self.list.append(getConfigListEntry(_("Set script path"), config.plugins.lbpanel.scriptpath))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "EPGSelectActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"ok": self.save
		}, -2)
		
	def cancel(self):
		self.close()
		
	def save(self):
		if not os.path.exists(config.plugins.lbpanel.scriptpath.value):
			try:
				os.system("mkdir %s" % config.plugins.lbpanel.scriptpath.value)
			except:
				pass
		config.plugins.lbpanel.scriptpath.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )
########################################################################
class NTPScreen(ConfigListScreen, Screen):
	skin = """
<screen name="NTPScreen" position="0,0" size="1280,720" title="LBpanel - NTP Sync">
    		<widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
 <!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="ACTUALIZAR HORA" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="MANUAL" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - NTP Sync"))
		self.cfgMenu()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("Update Now"))
		self["key_blue"] = StaticText(_("Manual"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "EPGSelectActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.UpdateNow,
			"blue": self.Manual,
			"ok": self.save
		}, -2)
		
	def cfgMenu(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Sync NTP"), config.plugins.lbpanel.onoff))
		self.list.append(getConfigListEntry(_("Set time of upgrade"), config.plugins.lbpanel.time))
		self.list.append(getConfigListEntry(_("Set time of transponder"), config.plugins.lbpanel.TransponderTime))
		self.list.append(getConfigListEntry(_("Sync on boot"), config.plugins.lbpanel.cold))
		self.list.append(getConfigListEntry(_("Server mode"), config.plugins.lbpanel.manual))
		self.list.append(getConfigListEntry(_("Select time zone"), config.plugins.lbpanel.server))
		self.list.append(getConfigListEntry(_("Select ntp server"), config.plugins.lbpanel.manualserver))
		ConfigListScreen.__init__(self, self.list)
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close()
		
	def Manual(self):
		ManualSetTime(self.session)
	
	def save(self):
		if os.path.exists("/etc/bhcron"):
			path = "/etc/bhcron/root"
			if not os.path.exists("/etc/cron"):
				 os.system("ln -s /etc/bhcron /etc/cron")
		else:
			path = "/etc/cron/root"

		if not os.path.exists("/etc/cron"):	
			os.makedirs("/etc/cron")
			if not os.path.exists("/etc/cron/crontabs/"):
				os.makedirs("/etc/cron/crontabs") 

		if config.plugins.lbpanel.onoff.value == "0":
			if fileExists(path):
				os.system("crontab -l | grep -v '/usr/bin/ntpdate -s -u' | crontab -" )
				os.system("awk '!/ntpdate/' %s > /tmp/.cronntp" % path)
				os.system("mv /tmp/.cronntp /etc/cron/root")
		if config.plugins.lbpanel.onoff.value == "1":
			if fileExists(path):
				os.system("crontab -l | grep -v '/usr/bin/ntpdate -s -u' | crontab -" )
				os.system("awk '!/ntpdate/' %s > /tmp/.cronntp" % path)
				os.system("mv /tmp/.cronntp /etc/cron/root")
			if config.plugins.lbpanel.manual.value == "0":
				if config.plugins.lbpanel.time.value == "30":
					data = "/%s * * * * /usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.time.value, config.plugins.lbpanel.server.value)
				else:
					data = "* /%s * * * /usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.time.value, config.plugins.lbpanel.server.value)
			else:
				if config.plugins.lbpanel.time.value == "30":
					data = "/%s * * * * /usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.time.value, config.plugins.lbpanel.manualserver.value)
				else:
					data = "* /%s * * * /usr/bin/ntpdate -s -u %s" % (config.plugins.lbpanel.time.value, config.plugins.lbpanel.manualserver.value)
		
			os.system("echo -e '%s' >> %s" % (data, path))
			os.system("echo '%s' | crontab -" % (data))

		if fileExists(path):
			os.chmod("%s" % path, 0644)
		if config.plugins.lbpanel.TransponderTime.value == "0": 
			config.misc.useTransponderTime.value = False
			config.misc.useTransponderTime.save()
		else:
			config.misc.useTransponderTime.value = True
			config.misc.useTransponderTime.save()
#		if config.plugins.lbpanel.cold.value == "0":
#			if fileExists("/etc/rcS.d/S42ntpdate.sh"):
#				os.unlink("/etc/rcS.d/S42ntpdate.sh")
#		else:
#			os.system("tar -C/ -xzpvf /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.tar.gz")
#			if fileExists("/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.sh"):
#				#Change NTP server in config file
#				if config.plugins.lbpanel.manual.value == "0":
#					os.system("sed -i 's/ntp_server/%s/g' /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.sh" % config.plugins.lbpanel.server.value)
#				else:
#					os.system("sed -i 's/ntp_server/%s/g' /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.sh" % config.plugins.lbpanel.manualserver.value)
#			if not fileExists("/etc/rcS.d/S42ntpdate.sh"):
#				os.symlink("/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/ntpdate.sh", "/etc/rcS.d/S42ntpdate.sh")
#				os.chmod("/etc/rcS.d/S42ntpdate.sh", 0777)
		for i in self["config"].list:
			i[1].save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("Configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )
			
	def UpdateNow(self):
		list =""
		synkinfo = os.popen("/usr/bin/ntpdate -v -u pool.ntp.org")
		for line in synkinfo:
			list += line
		self.mbox = self.session.open(MessageBox,list, MessageBox.TYPE_INFO, timeout = 6 )
####################################################################
class ManualSetTime(Screen):
	def __init__(self, session):
		self.session = session
		self.currentime = strftime("%d:%m:%Y %H:%M",localtime())
		self.session.openWithCallback(self.newTime,InputBox, text="%s" % (self.currentime), maxSize=16, type=Input.NUMBER)

	def newTime(self,what):
		try:
			lenstr=len(what)
		except:
			lengstr = 0
		if what is None:
			self.breakSetTime(_("new time not available"))
		elif ((what.count(" ") < 1) or (what.count(":") < 3) or (lenstr != 16)):
			self.breakSetTime(_("bad format"))
		else:
			newdate = what.split(" ",1)[0]
			newtime = what.split(" ",1)[1]
			newday = newdate.split(":",2)[0]
			newmonth = newdate.split(":",2)[1]
			newyear = newdate.split(":",2)[2]
			newhour = newtime.split(":",1)[0]
			newmin = newtime.split(":",1)[1]
			maxmonth = 31
			if (int(newmonth) == 4) or (int(newmonth) == 6) or (int(newmonth) == 9) or (int(newmonth) == 11):
				maxmonth=30
			elif (int(newmonth) == 2):
				if ((4*int(int(newyear)/4)) == int(newyear)):
					maxmonth=28
				else:
					maxmonth=27
			if (int(newyear) < 2007) or (int(newyear) > 2027)  or (len(newyear) < 4):
				self.breakSetTime(_("bad year %s") %newyear)
			elif (int(newmonth) < 0) or (int(newmonth) >12) or (len(newmonth) < 2):
				self.breakSetTime(_("bad month %s") %newmonth)
			elif (int(newday) < 1) or (int(newday) > maxmonth) or (len(newday) < 2):
				self.breakSetTime(_("bad day %s") %newday)
			elif (int(newhour) < 0) or (int(newhour) > 23) or (len(newhour) < 2):
				self.breakSetTime(_("bad hour %s") %newhour)
			elif (int(newmin) < 0) or (int(newmin) > 59) or (len(newmin) < 2):
				self.breakSetTime(_("bad minute %s") %newmin)
			else:
				self.newtime = "%s%s%s%s%s" %(newmonth,newday,newhour,newmin,newyear)
				self.session.openWithCallback(self.ChangeTime,MessageBox,_("Apply the new System time?"), MessageBox.TYPE_YESNO)

	def ChangeTime(self,what):
		if what is True:
			os.system("date %s" % (self.newtime))
		else:
			self.breakSetTime(_("not confirmed"))

	def breakSetTime(self,reason):
		self.session.open(MessageBox,(_("Change system time was canceled, because %s") % reason), MessageBox.TYPE_WARNING)

####################################################################
class SystemScreen(Screen):
	skin = """
		<screen name="SystemScreen" position="0,0" size="1280,720" title="LBpanel - System utils">
	<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="white" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" size="628,350">
      <convert type="TemplatedMultiContent">
    {"template": [ MultiContentEntryText(pos = (30, 5), size = (490, 50), flags = RT_HALIGN_LEFT, text = 0) ],
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
    <eLabel text="RESET PASSWD" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - System Utils"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.keyOK,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.resetpass,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Reset Passwd"))
		self.list = []
		self["menu"] = List(self.list)
		self.mList()

	def mList(self):
		self.list = []
		onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/kernel.png"))
		fourpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/swap.png"))
		fivepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/cron.png"))
		seispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/disco.png"))
		treepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/unusb.png"))
		self.list.append((_("Manager Kernel Modules"),"1", _("Load & unload Kernel Modules"), onepng))
		self.list.append((_("Cron Manager"),"5", _("Cron Manager"), fivepng))
		self.list.append((_("Mount Manager"),"6", _("HArd Disc Manager"), seispng))
		self.list.append((_("Swap Manager"),"4", _("Start, Stop, Create, Remove Swap Files"), fourpng ))
		self.list.append((_("My IP"),"3", _("Public IP"), treepng ))
		self["menu"].setList(self.list)

	def exit(self):
		self.close()

	def resetpass(self):
		os.system("passwd -d root")
		self.mbox = self.session.open(MessageBox,_("Your password has been reset"), MessageBox.TYPE_INFO, timeout = 4 )

	
	def keyOK(self, returnValue = None):
		if returnValue == None:
			returnValue = self["menu"].getCurrent()[1]
			if returnValue is "1":
				self.session.openWithCallback(self.mList,KernelScreen)
			elif returnValue is "3":
				os.popen("wget -qO /tmp/.myip http://appstore.linux-box.es/myip.php")
				f = open("/tmp/.myip")
				myip = f.readline()
				f.close()
				self.mbox = self.session.open(MessageBox,_("Your public IP is: %s") % (myip), MessageBox.TYPE_INFO, timeout = 20 )
			elif returnValue is "4":
				self.session.openWithCallback(self.mList,SwapScreen2)
			elif returnValue is "5":
				self.session.openWithCallback(self.mList,CrontabMan)
			elif returnValue is "6":
				self.session.open(MountManager.LBHddMount)
			else:
				print "\n[BackupSuite] cancel\n"
				self.close(None)
###############################################################################
class KernelScreen(Screen):
	skin = """
<screen name="KernelScreen" position="0,0" size="1280,720" title="LBpanel - Kernel Modules Manager">
 <widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
		MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (51, 40), png = 2), # index 4 is the pixmap
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
    <eLabel text="LSMOD" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="CARGA-DESCARGA" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="REINICIAR" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="700,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
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
		self.setTitle(_("LBpanel - Kernel Modules Manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.Ok,
			"yellow": self.YellowKey,
			"blue": self.BlueKey,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Load/UnLoad"))
		self["key_yellow"] = StaticText(_("LsMod"))
		self["key_blue"] = StaticText(_("Reboot"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()
		
	def BlueKey(self):
		os.system("reboot")
		
	def YellowKey(self):
		self.session.openWithCallback(self.CfgMenu,lsmodScreen)
		
	def IsRunnigModDig(self, what):
		modrun = os.popen ("lsmod | grep %s" % (what[:-4]))
		for line in modrun:
			if line.find(what[:-4]) > -1:
				return 1
				break
		return 0
		
	def CfgMenu(self):
		self.list = []
		if  os.path.exists("/etc/modutils"):
			DvrName = os.popen("modprobe -l -t drivers")
		else:
			DvrName = os.popen("modprobe -l | grep  drivers")
		for line in DvrName:
			kernDrv = line.split("/")
			if self.IsRunnigModDig(kernDrv[-1]) == 1:
				minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/kernelminimem.png"))
				self.list.append((kernDrv[-1],line,minipng, "1"))
			else:
				minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/kernelmini.png"))
				self.list.append((kernDrv[-1],line,minipng, "0"))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.Ok, "cancel": self.close}, -1)

	def Ok(self):
		item = self["menu"].getCurrent()
		isrunning = item[3]
		nlist = item[0]
		if item[3] == "0":
			os.system(("modprobe %s" % (nlist[:-4])))
			if  os.path.exists("/etc/modutils"):	
				os.system(("echo %s>/etc/modutils/%s" % (nlist[:-4],nlist[:-4])))
			else:
				os.system(("echo %s>/etc/modules-load.d/%s.conf" % (nlist[:-4],nlist[:-4])))
			os.chmod(("/etc/modules-load.d/%s.conf" % (nlist[:-4])), 0644)
			os.system("update-modules")
			self.mbox = self.session.open(MessageBox,(_("Loaded %s") % (nlist)), MessageBox.TYPE_INFO, timeout = 4 )
		else:
			os.system(("rmmod %s" % ( nlist[:-4])))
			if  os.path.exists("/etc/modutils"):
				os.system(("rm /etc/modutils/%s" % (nlist[:-4])))
			else:
				os.system(("rm /etc/modules-load.d/%s.conf" % (nlist[:-4])))
			os.system("update-modules")
			self.mbox = self.session.open(MessageBox,(_("UnLoaded %s") % (nlist)), MessageBox.TYPE_INFO, timeout = 4 )
		self.CfgMenu()
		
	def exit(self):
		self.close()
####################################################################
class lsmodScreen(Screen):
	skin = """
<screen name="lsmodScreen" position="0,0" size="1280,720" title="LBpanel - List Kernel Drivers in Memory">

	<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
		MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (51, 40), png = 2), # index 4 is the pixmap
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
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - List Kernel Drivers in Memory"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()
		
	def CfgMenu(self):
		self.list = []
		DvrName = os.popen("lsmod")
		minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/kernelminimem.png"))
		for line in DvrName:
			item = line.split(" ")
			size = line[:28].split(" ")
			minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/kernelminimem.png"))
			if line.find("Module") != 0:
				self.list.append((item[0],( _("size: %s  %s") % (size[-1], item[-1])), minipng))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)

	def exit(self):
		self.close()
####################################################################
class CrashLogScreen(Screen):
	skin = """
<screen name="CrashLogScreen" position="0,0" size="1280,720" title="LBpanel - Crashlog files">

	<widget source="menu" render="Listbox" position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" scrollbarMode="showNever" backgroundColorSelected="#fd6502" transparent="1">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (70, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
		MultiContentEntryText(pos = (80, 29), size = (580, 18), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
		MultiContentEntryPixmapAlphaTest(pos = (5, 5), size = (51, 40), png = 2), # index 4 is the pixmap
			],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 50
	}
			</convert>
		</widget>
	 <eLabel text="OK" position="1115,650" size="100,30" zPosition="5" font="Regular;20" valign="center" halign="center" backgroundColor="white" foregroundColor="black" transparent="0" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="BORRAR" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="ENVIAR EMAIL" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="BORRAR TODO" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Crashlog files"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.SendMail,
			"yellow": self.YellowKey,
			"blue": self.BlueKey,
			})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Send by email"))
		self["key_yellow"] = StaticText(_("Remove"))
		self["key_blue"] = StaticText(_("Remove All"))
		self["key_ok"] = StaticText(_("View"))
		self.list = []
		self["menu"] = List(self.list)
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		self.CfgMenu()
		
	def CfgMenu(self):
		self.list = []
		minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/LBpanel/images/crashmini.png"))
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		try:
			crashfiles = os.listdir(crashdir)
			for line in crashfiles:
				if line.find("enigma2_crash") > -1:
					self.list.append((line,"%s" % time.ctime(os.path.getctime(crashdir + line)), minipng))
		except:
			pass
		self.list.sort()
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)
		
	def Ok(self):
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		try:
			item = crashdir + self["menu"].getCurrent()[0]
			self.session.openWithCallback(self.CfgMenu,LogScreen, item)
		except:
			pass

	def SendMail(self):
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		#try:
                print "Send email with craslog"
                item = crashdir + self["menu"].getCurrent()[0]
                file = open(crashdir + self["menu"].getCurrent()[0] , "r")
                crash = file.read()
                file.close()
			
                subj = _("Enigma2 Crashlog")
                msg = _('Report of crashlog.\nLBpanel\n\n%s') % crash
                mail = LBTools()
                mail.sendemail(config.plugins.lbpanel.smtpuser.value, config.plugins.lbpanel.lbemailto.value,subj , msg, config.plugins.lbpanel.smtpuser.value, config.plugins.lbpanel.smtppass.value)
                self.mbox = self.session.open(MessageBox,(_("Crashlog send by email: %s") % (item)), MessageBox.TYPE_INFO, timeout = 4 )
		#except:
		#	pass
	
	def YellowKey(self):
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		item = crashdir +  self["menu"].getCurrent()[0]
		try:
			os.system("rm %s"%(item))
			self.mbox = self.session.open(MessageBox,(_("Removed %s") % (item)), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.mbox = self.session.open(MessageBox,(_("Failed remove")), MessageBox.TYPE_INFO, timeout = 4 )
		self.CfgMenu()
		
	def BlueKey(self):
		if (os.path.isdir("/home/root/logs")):
		 	crashdir = "/home/root/logs/"
		else:
			crashdir = "/media/hdd/"
		try:
			os.system("rm %senigma2_crash*.log" % (crashdir))
			self.mbox = self.session.open(MessageBox,(_("Removed All Crashlog Files") ), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.mbox = self.session.open(MessageBox,(_("Failed remove")), MessageBox.TYPE_INFO, timeout = 4 )
		self.CfgMenu()
		
	def exit(self):
		self.close()
####################################################################
class LogScreen(Screen):
	skin = """
<screen name="LogScreen" position="0,0" size="1280,720" title="LBpanel - View Crashlog file">
<widget name="text" size="628,350" position="595,195" foregroundColor="#ffffff" backgroundColor="#e6e6e6" transparent="1" font="Regular;15" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="GUARDAR" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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

	def __init__(self, session, what):
		self.session = session
		Screen.__init__(self, session)
		self.crashfile = what
		self.setTitle(_("LBpanel - View Crashlog file"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.GreenKey,
			"yellow": self.YellowKey,
			})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Restart GUI"))
		self["key_yellow"] = StaticText(_("Save"))
		self["text"] = ScrollLabel("")
		self.listcrah()
		
	def exit(self):
		self.close()
	
	def GreenKey(self):
		self.session.open(TryQuitMainloop, 3)
		
	def YellowKey(self):
		os.system("gzip %s" % (self.crashfile))
		os.system("mv %s.gz /tmp" % (self.crashfile))
		self.mbox = self.session.open(MessageBox,_("%s.gz created in /tmp") % self.crashfile, MessageBox.TYPE_INFO, timeout = 4)
		
	def listcrah(self):
		list = " "
		files = open(self.crashfile, "r")
		for line in files:
			if line.find("Traceback (most recent call last):") != -1:
				for line in files:
					list += line
					if line.find("]]>") != -1:
						break
		self["text"].setText(list)
		files.close()
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "CCcamInfoActions"], { "cancel": self.close, "up": self["text"].pageUp, "left": self["text"].pageUp, "down": self["text"].pageDown, "right": self["text"].pageDown,}, -1)
######################################################################################
class epgdn(ConfigListScreen, Screen):
	skin = """
<screen name="epgdn" position="0,0" size="1280,720" title="LBpanel - EPG D+">
    
  <widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="DESCARGA" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="MANUAL" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - D+ EPG"))
		self.list = []
		self.list.append(getConfigListEntry(_("Select where to save epg.dat"), config.plugins.lbpanel.direct))
		self.list.append(getConfigListEntry(_("Select D+ epg"), config.plugins.lbpanel.lang))
		self.list.append(getConfigListEntry(_("Auto download epg.dat"), config.plugins.lbpanel.auto))
		self.list.append(getConfigListEntry(_("Auto download hour"), config.plugins.lbpanel.epgtime))
		self.list.append(getConfigListEntry(_("Auto load and save EPG"), config.plugins.lbpanel.autosave))
		self.list.append(getConfigListEntry(_("Save copy in ../epgtmp.gz"), config.plugins.lbpanel.autobackup))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("EPG Download"))
		self["key_blue"] = StaticText(_("Manual"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.downepg,
			"blue": self.manual,
			"ok": self.save
		}, -2)
		
	def downepg(self):
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
		except:
			self.mbox = self.session.open(MessageBox,(_("Sorry, the EPG download error")), MessageBox.TYPE_INFO, timeout = 4 )

	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close(False)
	
	def save(self):
		config.misc.epgcache_filename.value = ("%sepg.dat" % config.plugins.lbpanel.direct.value)
		config.misc.epgcache_filename.save()
		config.plugins.lbpanel.epgtime.save()
		config.plugins.lbpanel.lang.save()
		config.plugins.lbpanel.direct.save()
		config.plugins.lbpanel.auto.save()
		config.plugins.lbpanel.autosave.save()
		config.plugins.lbpanel.autobackup.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )
################################################################################################################
	def manual(self):
		self.session.open(epgdmanual)
################################################################################################################
	def restart(self):
		self.session.open(TryQuitMainloop, 3)
#####################################################
################################################################################################################

## Timer especific function for epg
class Ttimer():
        def __init__(self):
                self.dialog = None
                        
        def gotSession(self, session):
                self.session = session
                self.timer = enigma.eTimer() 
                self.timer.callback.append(self.run)
                self.timer.start(3000, True)
                                                                                                
        def run(self):
                self.timer.stop()
                os.system("sh /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/script/run.e2.sh")
                self.session.nav.playService(eServiceReference(config.tv.lastservice.value))
                self.mbox = self.session.open(MessageBox,(_("EPG downloaded")), MessageBox.TYPE_INFO, timeout = 5 )                                                                                                                                        

class epgscript(ConfigListScreen, Screen):
	skin = """
<screen name="epgdn" position="0,0" size="1280,720" title="LBpanel - EPG D+">
    
  <widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="DESCARGA" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="MANUAL" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - D+ SAT EPG"))
		self.list = []
		self.list.append(getConfigListEntry(_("Select where to save epg.dat"), config.plugins.lbpanel.direct))
		self.list.append(getConfigListEntry(_("Select D+ epg"), config.plugins.lbpanel.lang))
		self.list.append(getConfigListEntry(_("Auto download epg.dat"), config.plugins.lbpanel.auto2))
		self.list.append(getConfigListEntry(_("Auto download hour"), config.plugins.lbpanel.epgtime2))
		self.list.append(getConfigListEntry(_("Auto load and save EPG"), config.plugins.lbpanel.autosave))
		self.list.append(getConfigListEntry(_("Save copy in ../epgtmp.gz"), config.plugins.lbpanel.autobackup))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("EPG Download"))
		self["key_blue"] = StaticText(_("Manual"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.downepg,
			"blue": self.manual,
			"ok": self.save
		}, -2)
	
	def zapTo(self, reftozap):
	        self.session.nav.playService(eServiceReference(reftozap))

	def downepg(self):
                self.oldService = self.session.nav.getCurrentlyPlayingServiceReference().toString()
                channel = "1:0:1:75C6:422:1:C00000:0:0:0:"
                self.zapTo(channel)
                fo = open("/tmp/.lbepg","a+")
                fo.close()
                mt = Ttimer()
                mt.gotSession(self.session)

	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close(False)
	
	def save(self):
		config.misc.epgcache_filename.value = ("%sepg.dat" % config.plugins.lbpanel.direct.value)
		config.misc.epgcache_filename.save()
		config.plugins.lbpanel.epgtime2.save()
		config.plugins.lbpanel.lang.save()
		config.plugins.lbpanel.direct.save()
		config.plugins.lbpanel.auto2.save()
		config.plugins.lbpanel.autosave.save()
		config.plugins.lbpanel.autobackup.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )
################################################################################################################
	def manual(self):
		self.session.open(epgdmanual)
################################################################################################################
	def restart(self):
		self.session.open(TryQuitMainloop, 3)
#####################################################
################################################################################################################

class epgdmanual(Screen):
	skin = """
<screen name="epgdmanual" position="center,260" size="850,50" title="LBpanel - EPG D+">
  <ePixmap position="10,40" zPosition="1" size="165,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
  <widget source="key_red" render="Label" position="10,10" zPosition="2" size="165,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
  <ePixmap position="175,40" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/green.png" alphatest="blend" />
  <widget source="key_green" render="Label" position="175,10" zPosition="2" size="200,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
  <ePixmap position="375,40" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/yellow.png" alphatest="blend" />
  <widget source="key_yellow" render="Label" position="375,10" zPosition="2" size="200,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
  <ePixmap position="574,40" zPosition="1" size="200,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/blue.png" alphatest="blend" />
  <widget source="key_blue" render="Label" position="574,10" zPosition="2" size="200,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
</screen>"""
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - EPG D+"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save epg.dat"))
		self["key_yellow"] = StaticText(_("Restore epg.dat"))
		self["key_blue"] = StaticText(_("Reload epg.dat"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.savepg,
			"yellow": self.restepg,
			"blue": self.reload,
		}, -2)
################################################################################################################
	def reload(self):
		try:
			if fileExists("%sepgtmp/epg.dat.gz" % config.plugins.lbpanel.direct.value):
				os.system("cp -f %sepgtmp/epg.dat.gz %s" % (config.plugins.lbpanel.direct.value, config.plugins.lbpanel.direct.value))
				os.system("gzip -df %sepg.dat.gz" % config.plugins.lbpanel.direct.value)
				os.chmod("%sepg.dat" % config.plugins.lbpanel.direct.value, 0644)
			epgcache = new.instancemethod(_enigma.eEPGCache_load,None,eEPGCache)
			epgcache = eEPGCache.getInstance().load()
			self.mbox = self.session.open(MessageBox,(_("epg.dat reloaded")), MessageBox.TYPE_INFO, timeout = 4 )
		except:
			self.mbox = self.session.open(MessageBox,(_("reload epg.dat failed")), MessageBox.TYPE_INFO, timeout = 4 )
################################################################################################################
	def savepg(self):
		epgcache = new.instancemethod(_enigma.eEPGCache_save,None,eEPGCache)
		epgcache = eEPGCache.getInstance().save()
		self.mbox = self.session.open(MessageBox,(_("epg.dat saved")), MessageBox.TYPE_INFO, timeout = 4 )
		
	def restepg(self):
		epgcache = new.instancemethod(_enigma.eEPGCache_load,None,eEPGCache)
		epgcache = eEPGCache.getInstance().load()
		self.mbox = self.session.open(MessageBox,(_("epg.dat restored")), MessageBox.TYPE_INFO, timeout = 4 )
		
	def cancel(self):
		self.close(False)
##############################################################################
class CrontabMan(Screen):
	skin = """
<screen name="CrontabMan" position="0,0" size="1280,720" title="LBpanel - Cron Manager">
  
	<widget source="menu" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
		<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (10, 2), size = (580, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
			],
	"fonts": [gFont("Regular", 23),gFont("Regular", 16)],
	"itemHeight": 29
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
    <eLabel text="ADD" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Cron Manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],

		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.GreenKey,
			"yellow": self.YellowKey,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Add tabs"))
		self["key_yellow"] = StaticText(_("Remove tabs"))
		self.list = []
		self["menu"] = List(self.list)
		self.cMenu()

	def cMenu(self):
		self.list = []
		count = 0
		# Black Hole compatibility
		if os.path.exists("/etc/bhcron"):
			path = "/etc/bhcron/root"
			if not os.path.exists("/etc/cron"):
				 os.system("ln -s /etc/bhcron /etc/cron")
		else:
			path = "/etc/cron/root"
			# Test if cron is installed                        

		if not os.path.exists("/etc/cron"):	
			os.makedirs("/etc/cron")
			if not os.path.exists("/etc/cron/crontabs/"):
				os.makedirs("/etc/cron/crontabs") 
		
		if fileExists(path):
			cron = open(path, "r")
			for line in cron:
				count = count + 1
				self.list.append((line, count))
			cron.close()
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.Ok, "cancel": self.close}, -1)

	def Ok(self):
		self.close()
		
	def GreenKey(self):
		self.session.openWithCallback(self.cMenu,CrontabManAdd)

	
	def YellowKey(self):
		if os.path.exists("/etc/bhcron"):
			path = "/etc/bhcron/root"
		else:
			path = "/etc/cron/root"                        
		print "Executing: awk 'NR!=%s' %s > %s" % (str(self["menu"].getCurrent()[1]), path, path)
		os.system("awk 'NR!=%s' %s > /tmp/.cron" % (str(self["menu"].getCurrent()[1]), path))
		os.system("mv /tmp/.cron %s" % (path ))
		ccron = str(self["menu"].getCurrent()[0] [:-1])
		ccron = ccron.replace("*","\*")
		print "crontab -l | grep -v '%s' | crontab -" % (ccron)
		os.system("crontab -l | grep -v '%s' | crontab -" % (ccron))
		self.cMenu()
		
	def exit(self):
		self.close()
####################################################################
class CrontabManAdd(ConfigListScreen, Screen):
	skin = """
<screen name="CrontabManAdd" position="0,0" size="1280,720" title="LBpanel - Add tabs" >
		<widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="ADD" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Add tabs"))
		self.list = []
		self.list.append(getConfigListEntry(_("Min"), config.plugins.lbpanel.min))
		self.list.append(getConfigListEntry(_("Hour"), config.plugins.lbpanel.hour))
		self.list.append(getConfigListEntry(_("Day of month"), config.plugins.lbpanel.dayofmonth))
		self.list.append(getConfigListEntry(_("Month"), config.plugins.lbpanel.month))
		self.list.append(getConfigListEntry(_("Day of week"), config.plugins.lbpanel.dayofweek))
		self.list.append(getConfigListEntry(_("Command"), config.plugins.lbpanel.command))
		self.list.append(getConfigListEntry(_("Every"), config.plugins.lbpanel.every))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Add"))
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
		everymin = ""
		everyhour = ""
		everydayofmonth = ""
		everymonth = ""
		everydayofweek = ""
		if config.plugins.lbpanel.min.value != '*' and config.plugins.lbpanel.every.value == '1':
			everymin = '/'
		elif config.plugins.lbpanel.hour.value != '*' and config.plugins.lbpanel.every.value == '2':
			everyhour = '/'
		elif config.plugins.lbpanel.dayofmonth.value != '*' and config.plugins.lbpanel.every.value == '3':
			everydayofmonth = '/'
		elif config.plugins.lbpanel.month.value != '*' and config.plugins.lbpanel.every.value == '4':
			everymonth = '/'
		elif config.plugins.lbpanel.dayofweek.value != '*' and config.plugins.lbpanel.every.value == '5':
			everydayofweek = '/'
			
		if config.plugins.lbpanel.min.value == '*' and config.plugins.lbpanel.hour.value == '*' and config.plugins.lbpanel.dayofmonth.value == '*' and config.plugins.lbpanel.month.value == '*' and  config.plugins.lbpanel.dayofweek.value == '*':
			print ("error")
		else:
			if os.path.exists("/etc/bhcron"):
				path = "/etc/bhcron/root"
			else:
				path = "/etc/cron/root"                        

			os.system("echo -e '%s%s %s%s %s%s %s%s %s%s    %s' >> %s" % (everymin, config.plugins.lbpanel.min.value,
										everyhour, config.plugins.lbpanel.hour.value, 
										everydayofmonth, config.plugins.lbpanel.dayofmonth.value,
										everymonth, config.plugins.lbpanel.month.value,
										everydayofweek, config.plugins.lbpanel.dayofweek.value,
										config.plugins.lbpanel.command.value,
										path))
			os.system("echo -e '%s%s %s%s %s%s %s%s %s%s    %s'  | crontab -" % (everymin, config.plugins.lbpanel.min.value,
										everyhour, config.plugins.lbpanel.hour.value, 
										everydayofmonth, config.plugins.lbpanel.dayofmonth.value,
										everymonth, config.plugins.lbpanel.month.value,
										everydayofweek, config.plugins.lbpanel.dayofweek.value,
										config.plugins.lbpanel.command.value))
		
		#os.system("echo -e 'root' >> /etc/cron/crontabs/cron.update")
		for i in self["config"].list:
			i[1].cancel()
		self.close()
###############################################################################
class Info2Screen(Screen):
	skin = """
<screen name="Info2Screen" position="0,0" size="1280,720" title="LBpanel - System Info">
	<widget name="text" position="595,215" size="628,400" zPosition="2" backgroundColor="#6e6e6e" foregroundColor="#ffffff" transparent="1" font="Console;15" />

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
    <eLabel position="592,191" size="629,420" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - System Info"))
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
			os.system("free>/tmp/mem && echo>>/tmp/mem && df -h>>/tmp/mem")
			meminfo = open("/tmp/mem", "r")
			for line in meminfo:
				list += line
			self["text"].setText(list)
			meminfo.close()
			os.system("rm /tmp/mem")
		except:
			list = " "
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], { "cancel": self.close, "up": self["text"].pageUp, "left": self["text"].pageUp, "down": self["text"].pageDown, "right": self["text"].pageDown,}, -1)
######################################################################################
#class Libermen(Screen):
#	skin = """
#	<screen name="ScriptScreen" position="center,160" size="1150,500" title="LBpanel - Free Memory" >
#	    <ePixmap position="715,10" zPosition="1" size="450,700" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/#fondo12.png" alphatest="blend" transparent="1" />
#			<widget name="list" position="20,10" size="660,450" scrollbarMode="showOnDemand" />
#		<ePixmap position="20,488" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
#		<widget source="key_red" render="Label" position="20,458" zPosition="2" size="170,30" font="Regular;20" halign="center" #valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
#		</screen>"""

#	def __init__(self, session):
#		Screen.__init__(self, session)
#		self.session = session
#		self.setTitle(_("LBpanel - Free Memory"))
#		self.scrpit_menu()
#		self["key_red"] = StaticText(_("Close"))
#		self["actions"] = ActionMap(["OkCancelActions","ColorActions"], {"ok": self.run, "red": self.exit, "cancel": self.close}, -1)
#		
#	def scrpit_menu(self):
#		list = []
#		try:
#			list = os.listdir("%s" % config.plugins.lbpanel.scriptpath1.value[:-1])
#			list = [x[:-3] for x in list if x.endswith('.sh')]
#		except:
#			list = []
#		list.sort()
#		self["list"] = MenuList(list)
#		
#	def run(self):
#		script = self["list"].getCurrent()
#		if script is not None:
#			name = ("%s%s.sh" % (config.plugins.lbpanel.scriptpath1.value, script))
#			os.chmod(name, 0755)
#			self.session.open(Console, script.replace("_", " "), cmdlist=[name])
#			
#	def config_path(self):
#		self.session.open(ConfigScript)

#	def exit(self):
#		self.close()

######################################################################################
class scanhost(ConfigListScreen, Screen):
	skin = """
<screen name="scanhost" position="0,0" size="1280,720" title="LBpanel - Check Hosts">
     <widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
<widget name="LabelStatus" backgroundColor="#6e6e6e" foregroundColor="#ffffff" transparent="1" position="680,400" zPosition="2" size="550,40"  font="Regular;20"/>
<ePixmap position="645,402" zPosition="1" size="25,25" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/bomb.png" transparent="1" alphatest="on" />
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CERRAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="VER" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="INICIAR" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
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
		self.setTitle(_("LBpanel - Check Host"))
		self.list = []
		self.list.append(getConfigListEntry(_("Auto Daily Test"), config.plugins.lbpanel.checkauto))
		self.list.append(getConfigListEntry(_("Hour"), config.plugins.lbpanel.checkhour))
		self.list.append(getConfigListEntry(_("Disable Faulty Lines?"), config.plugins.lbpanel.checkoff))
		self.list.append(getConfigListEntry(_("Scan type"), config.plugins.lbpanel.checktype))
		self.list.append(getConfigListEntry(_("Auto scan localhost"), config.plugins.lbpanel.autocheck))
		#self.list.append(getConfigListEntry(_("Send email with log?"), config.plugins.lbpanel.lbemail))
		self.list.append(getConfigListEntry(_("Send email only in danger lines?"), config.plugins.lbpanel.warnonlyemail))
		#self.list.append(getConfigListEntry(_("Send report to: (email)"), config.plugins.lbpanel.lbemailto))
		#self.list.append(getConfigListEntry(_("Smtp server"), config.plugins.lbpanel.smtpserver))
		#self.list.append(getConfigListEntry(_("Smtp user"), config.plugins.lbpanel.smtpuser))
		#self.list.append(getConfigListEntry(_("Smtp password"), config.plugins.lbpanel.smtppass))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText(_("View"))
		self["key_blue"] = StaticText(_("Run"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"yellow": self.viewscanlog,
			"blue": self.checkt,
			"ok": self.save
		}, -2)
		self["LabelStatus"] = Label(_("Configure and press blue key to check"))
		
        def check(self):
	        try:   
			self["LabelStatus"].setText("Scan init")                     
        		os.system("sh /usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/lbscan.py %s %s %s %s" % (config.plugins.lbpanel.checktype.value, config.plugins.lbpanel.autocheck.value, config.plugins.lbpanel.checkoff.value, config.plugins.lbpanel.warnonlyemail.value))
        		self["LabelStatus"].setText("Scan end")
        		self.session.open(showScan)
                except IOError:
                      	self.mbox = self.session.open(MessageBox,(_("Sorry, I can not find lbscan.py")), MessageBox.TYPE_INFO, timeout = 4 )
		
        def checkt(self):
	        try:   
	        	self["LabelStatus"].setText("Scan init")
        		self.session.open(Console,_("Scan peer"),["/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/lbscan.py " + config.plugins.lbpanel.checktype.value + " " + config.plugins.lbpanel.autocheck.value + " " + config.plugins.lbpanel.checkoff.value + " " + config.plugins.lbpanel.warnonlyemail.value])
        		self["LabelStatus"].setText("Scan end")
        		# Send email with result by cron
        		
#        		self.session.open(showScan)
                except:
                      	self.mbox = self.session.open(MessageBox,(_("Sorry, I can not find lbscan.py")), MessageBox.TYPE_INFO, timeout = 4 )
	def viewscanlog(self):
		if (os.path.exists("/tmp/.lbscan.log")):
			 self.session.open(showScan)
		else:
			 self.mbox = self.session.open(MessageBox,(_("Sorry, I can not find scan data, scan first")), MessageBox.TYPE_INFO, timeout = 4 )
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close(False)
	
	def save(self):
		config.plugins.lbpanel.checkauto.save()
		config.plugins.lbpanel.checkhour.save()
		config.plugins.lbpanel.checkoff.save()
		config.plugins.lbpanel.checktype.save()
		config.plugins.lbpanel.autocheck.save()
#		config.plugins.lbpanel.lbemail.save()
		config.plugins.lbpanel.warnonlyemail.save()
#		config.plugins.lbpanel.lbemailto.save()
#		config.plugins.lbpanel.smtpserver.save()
#		config.plugins.lbpanel.smtpuser.save()
#		config.plugins.lbpanel.smtppass.save()
		configfile.save()
		self.mbox = self.session.open(MessageBox,(_("Configuration is saved")), MessageBox.TYPE_INFO, timeout = 4 )

	def messagebox(self):
		self.mbox = self.session.open(MessageBox,(_("Scaning hosts, please wait")), MessageBox.TYPE_INFO, timeout = 4 )
	
	
################################################################################################################
class showScan(Screen):
	skin = """
<screen name="Show Scan" position="center,100" size="890,560" title="LBpanel - Scan Results">
	<ePixmap position="20,548" zPosition="1" size="170,2" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/red.png" alphatest="blend" />
	<widget source="key_red" render="Label" position="20,518" zPosition="2" size="170,30" font="Regular;20" halign="center" valign="center" backgroundColor="background" foregroundColor="foreground" transparent="1" />
	<widget name="text" position="15,10" size="860,500" font="Console;20" />
</screen>"""

	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.setTitle(_("LBpanel - Scan Results"))
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
			scaninfo = open("/tmp/.lbscan.log", "r")
			for line in scaninfo:				
			        list += line
			self["text"].setText(list)
			scaninfo.close()
		except:
			list = " "
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"], { "cancel": self.close, "up": self["text"].pageUp, "left": self["text"].pageUp, "down": self["text"].pageDown, "right": self["text"].pageDown,}, -1)

class LBTools():

   # Generic function to send email
   def sendemail(self, from_addr, to_addr,
              subject, message,
              login, password,
              smtpserver='smtp.gmail.com:587', cc_addr=""):
        
        if (not os.path.isfile("/usr/bin/curl")):
                os.popen("opkg install curl")
                if (not os.path.isfile("/usr/bin/curl")):
                        os.popen("opkg install http://appstore.linux-box.es/files/curl_7.24.0-r0_mips32el.ipk")
                        if (not os.path.isfile("/usr/bin/curl")):
                                self.mbox = self.session.open(MessageBox,(_("Mail is not send. Curl is not installed, please install curl")), MessageBox.TYPE_ERROR, timeout = 10 )
        #try:
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
                f = { 'from' : from_addr, 'to' : to_addr, 'cc' : '', 'subject' : subject, 'server' : smtpserver, 'proto' : proto, 'user' : login, 'password' : password}
                url = 'https://appstore.linux-box.es/semail.php?%s' % (urllib.urlencode(f))	
                f = open("/tmp/.mail","w")
                f.write(message)
                f.close()
                os.system('curl -F body=@"/tmp/.mail" -k "%s"' % (url))
	#except Exception as e: print(e)
	#except:
        	#fo = open("/tmp/.lbemail.error","a+")
        	#fo.close()
        	#config.plugins.lbpanel.lbemail.value = False
        	#config.plugins.lbpanel.lbemail.save()
