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
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Sources.List import List
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_PLUGINS, SCOPE_LANGUAGE
from Tools.LoadPixmap import LoadPixmap
from Components.Button import Button
from Components.Language import language
from Components.config import config, ConfigElement, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_OK
from os import environ
import gettext
import ExtraActionBox


import os
import sys

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
                         

def DaemonEntry(name, picture, description, started, installed):
	if started:
		pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_on1.png"));
	else:
		pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_off1.png"));
	if not installed:
		pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/lock_error1.png"));
		
	pixmap2 = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/daemons/" + picture));
	if not pixmap2:
		pixmap2 = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/extra/empty.png"));
	
	return (pixmap2, name, description, pixmap)
	
class LBDaemonsList(Screen):
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		
		self.running = list()
		self.installed = list()
		self.daemons = list()
		
		self["menu"] = List(list())
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["key_green"] = Button("")
		self["key_red"] = Button("")
		self["key_ok"] = Button("")
		self["key_blue"] = Button(_("Exit"))
		self["key_yellow"] = Button("")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"red": self.red,
			"ok": self.red,
			"green": self.green,
			"cancel": self.quit,
		}, -2)
		
		self.onFirstExecBegin.append(self.drawList)
	
	def selectionChanged(self):
		if len(self.daemons) > 0:
			index = self["menu"].getIndex()
			if self.installed[index]:
				if self.running[index]:
					self["key_red"].setText(_("Stop"))
				else:
					self["key_red"].setText(_("Iniciar"))
				
				if self.daemons[index][6]:
					self["key_yellow"].setText(_("Configure"))
				else:
					self["key_yellow"].setText("")
				
				self["key_green"].setText("")
			else:
				self["key_red"].setText("")
				self["key_yellow"].setText("")
				if self.daemons[index][9]:
					self["key_green"].setText(_("Install"))
				else:
					self["key_green"].setText("")
		
	def drawList(self, ret = None):
		self.session.open(ExtraActionBox, _("Testing daemons status..."), _("Daemons"), self.actionDrawList)


	def actionDrawList(self):
		self.ishowed = True
		if len(self.daemons) == 0:
			self.loadList()
		self.checkInstalled()
		self.checkRunning()
	
		list = []
		i = 0
		for daemon in self.daemons:
			list.append(DaemonEntry(daemon[0], "%s" % daemon[2], daemon[1], self.running[i], self.installed[i]))
			i += 1
		
		self["menu"].setList(list)
	
	def checkRunning(self):
		self.running = list()
		for daemon in self.daemons:
			self.running.append(daemon[3]())
			
	def checkInstalled(self):
		self.installed = list()
		for daemon in self.daemons:
			self.installed.append(daemon[7]())
		
	def loadList(self):
		self.daemons = list()
		tdaemons = crawlDirectory("%s/Daemons/" % os.path.dirname(sys.modules[__name__].__file__), ".*\.ext$")
		tdaemons.sort()
		for daemon in tdaemons:
			if daemon[1][:1] != ".":
				src = open(os.path.join(daemon[0], daemon[1]))
				exec src.read()
				src.close()
				self.daemons.append((daemon_name, daemon_description, daemon_icon, daemon_fnc_status, daemon_fnc_start, daemon_fnc_stop, daemon_class_config, daemon_fnc_installed, daemon_fnc_boot, daemon_package))
	
	def yellow(self):
		index = self["menu"].getIndex()
		if self.installed[index]:
			if self.daemons[index][6]:
				self.session.open(self.daemons[index][6])


	def green(self):
		index = self["menu"].getIndex()
		if not self.installed[index]:
			if self.daemons[index][9]:
				smstack.add(SMStack.INSTALL, self.daemons[index][9])
				self.session.openWithCallback(self.drawList, SMStatus)
			
	def red(self):
		if len(self.daemons) > 0:
			index = self["menu"].getIndex()
			if self.running[index]:
				self.session.openWithCallback(self.drawList, ExtraActionBox, _("Stoping %s...") % self.daemons[index][0], _("Daemons"), self.startstop)
			else:
				self.session.openWithCallback(self.drawList, ExtraActionBox, _("Starting %s...") % self.daemons[index][0], _("Daemons"), self.startstop)
			
	def startstop(self):
		if len(self.daemons) > 0:
			index = self["menu"].getIndex()
			if self.installed[index]:
				if self.running[index]:
					self.daemons[index][5]()
				else:
					self.daemons[index][4]()
				self.daemons[index][8](self.daemons[index][3]())
		
	def quit(self):
		self.close()
