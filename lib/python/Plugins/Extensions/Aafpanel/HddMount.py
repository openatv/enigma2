# -*- coding: utf-8 -*-
from enigma import *
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Tools.Directories import fileExists, crawlDirectory
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Button import Button
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Extra.MountPoints import MountPoints
from Extra.ExtraMessageBox import ExtraMessageBox

import os
import sys
import re

class HddMount(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Hard Drive Mount">
		<widget name="menu" position="10,10" scrollbarMode="showOnDemand" size="540,320"/>
		<ePixmap position="0,360"   zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap position="140,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap position="280,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
		<ePixmap position="420,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
        <widget name="key_red" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
        <widget name="key_green" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
        <widget name="key_yellow" position="280,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
        <widget name="key_blue" position="420,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""
	def __init__(self, session, device, partition):
		Screen.__init__(self, session)
		
		self.device = device
		self.partition = partition
		self.mountpoints = MountPoints()
		self.mountpoints.read()
		
		self.list = []
		self.list.append("Mount as main hdd")
		self.list.append("Mount as /media/usb")
		self.list.append("Mount as /media/usb1")
		self.list.append("Mount as /media/usb2")
		self.list.append("Mount as /media/usb3")
		self.list.append("Mount as /media/cf")
		self.list.append("Mount as /media/mmc1")
		self.list.append("Mount on custom path")
		
		self["menu"] = MenuList(self.list)
		
		self["key_green"] = Button("")
		self["key_red"] = Button(_("Ok"))
		self["key_blue"] = Button(_("Exit"))
		self["key_yellow"] = Button("")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			#"yellow": self.yellow,
			"red": self.ok,
			"ok": self.ok,
			"cancel": self.quit,
		}, -2)
		
	def ok(self):
		selected = self["menu"].getSelectedIndex()
		if selected == 0:
			self.setMountPoint("/media/hdd")
		elif selected == 1:
			self.setMountPoint("/media/usb")
		elif selected == 2:
			self.setMountPoint("/media/usb1")
		elif selected == 3:
			self.setMountPoint("/media/usb2")
		elif selected == 4:
			self.setMountPoint("/media/usb3")
		elif selected == 5:
			self.setMountPoint("/media/cf")
		elif selected == 6:
			self.setMountPoint("/media/mmc1")
		elif selected == 7:
			self.session.openWithCallback(self.customPath, VirtualKeyBoard, title = (_("Insert mount point:")), text = "/media/custom")
			
	def customPath(self, result):
		if result and len(result) > 0:
			result = result.rstrip("/")
			os.system("mkdir -p %s" % result)
			self.setMountPoint(result)
		
	def setMountPoint(self, path):
		self.cpath = path
		if self.mountpoints.exist(path):
			self.session.openWithCallback(self.setMountPointCb, ExtraMessageBox, "Selected mount point is already used by another drive.", "Mount point exist!",
																[ [ "Change old drive with this new drive", "ok.png" ],
																[ "Mantain old drive", "cancel.png" ],
																])
		else:
			self.setMountPointCb(0)
			
	def setMountPointCb(self, result):
		if result == 0:
			if self.mountpoints.isMounted(self.cpath):
				if not self.mountpoints.umount(self.cpath):
					self.session.open(MessageBox, _("Cannot umount current drive.\nA record in progress, timeshit or some external tools (like samba and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
					self.close()
					return
			self.mountpoints.delete(self.cpath)
			self.mountpoints.add(self.device, self.partition, self.cpath)
			self.mountpoints.write()
			if not self.mountpoints.mount(self.device, self.partition, self.cpath):
				self.session.open(MessageBox, _("Cannot mount new drive.\nPlease check filesystem or format it and try again"), MessageBox.TYPE_ERROR)
			elif self.cpath == "/media/hdd":
				os.system("/bin/mkdir /hdd/movie")
				os.system("/bin/mkdir /hdd/music")
				os.system("/bin/mkdir /hdd/picture")

			self.close()
	
	def quit(self):
		self.close()
