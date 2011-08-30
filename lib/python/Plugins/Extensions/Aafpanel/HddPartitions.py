from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from Components.Button import Button
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Extra.Disks import Disks
from Extra.ExtraActionBox import ExtraActionBox
from Extra.MountPoints import MountPoints
from HddMount import HddMount

import os
import sys

def PartitionEntry(description, size):
	picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/partitionmanager.png"));
		
	return (picture, description, size)

class HddPartitions(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Hard Drive Partitions">
		<ePixmap position="0,360"   zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap position="140,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap position="280,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
		<ePixmap position="420,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_yellow" position="280,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_blue" position="420,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget source="menu" render="Listbox" position="10,50" size="620,450" font="Regular;16" scrollbarMode="showOnDemand" >
			<convert type="TemplatedMultiContent">
				{"template": [
				 MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 0),
				 MultiContentEntryText(pos = (90, 0), size = (600, 30), font=0, text = 1),
				 MultiContentEntryText(pos = (110, 30), size = (600, 50), font=1, flags = RT_VALIGN_TOP, text = 2),
				],
				"fonts": [gFont("Regular", 24),gFont("Regular", 18)],
				"itemHeight": 60
				}
			</convert>
		</widget>
	</screen>"""
	def __init__(self, session, disk):
		self.session = session
		
		Screen.__init__(self, session)
		self.disk = disk
		self.refreshMP(False)
		
		self["menu"] = List(self.partitions)
		self["menu"].onSelectionChanged.append(self.selectionChanged)
		self["key_red"] = Button("")
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)
		
		if len(self.disk[5]) > 0:
			if self.disk[5][0][2] == "Linux":
				self["key_green"].setText(_("Check"))
				self["key_yellow"].setText(_("Format"))
				
		if self.disk[5][0][2] == "Linux swap":
			self["key_red"].setText("")
		else:
			mp = self.mountpoints.get(self.disk[0], 1)
			if len(mp) > 0:
				self.mounted = True
				self["key_red"].setText(_("Umount"))
			else:
				self.mounted = False
				self["key_red"].setText(_("Mount"))
		
	def selectionChanged(self):
		self["key_green"].setText("")
		self["key_yellow"].setText("")
		if len(self.disk[5]) > 0:
			index = self["menu"].getIndex()
			if self.disk[5][index][2] == "Linux":
				self["key_green"].setText(_("Check"))
				self["key_yellow"].setText(_("Format"))
				
			if self.disk[5][index][2] == "Linux swap":
				self["key_red"].setText("")
			else:
				mp = self.mountpoints.get(self.disk[0], index+1)
				if len(mp) > 0:
					self.mounted = True
					self["key_red"].setText(_("Umount"))
				else:
					self.mounted = False
					self["key_red"].setText(_("Mount"))
				
	def chkfs(self):
		disks = Disks()
		ret = disks.chkfs(self.disk[5][self.index][0][:3], self.index+1)
		if ret == 0:
			self.session.open(MessageBox, _("Check disk terminated with success"), MessageBox.TYPE_INFO)
		elif ret == -1:
			self.session.open(MessageBox, _("Cannot umount current drive.\nA record in progress, timeshit or some external tools (like samba and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, _("Error checking disk. The disk may be damaged"), MessageBox.TYPE_ERROR)
			
	def mkfs(self):
		disks = Disks()
		ret = disks.mkfs(self.disk[5][self.index][0][:3], self.index+1)
		if ret == 0:
			self.session.open(MessageBox, _("Format terminated with success"), MessageBox.TYPE_INFO)
		elif ret == -2:
			self.session.open(MessageBox, _("Cannot format current drive.\nA record in progress, timeshit or some external tools (like samba and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, _("Error formatting disk. The disk may be damaged"), MessageBox.TYPE_ERROR)
			
	def green(self):
		if len(self.disk[5]) > 0:
			index = self["menu"].getIndex()
			if self.disk[5][index][2] == "Linux":
				self.index = index
				self.session.open(ExtraActionBox, "Checking disk %s" % self.disk[5][index][0], "Checking disk", self.chkfs)
				
	def yellow(self):
		if len(self.disk[5]) > 0:
			index = self["menu"].getIndex()
			if self.disk[5][index][2] == "Linux":
				self.index = index
				self.session.open(ExtraActionBox, "Formatting disk %s" % self.disk[5][index][0], "Formatting disk", self.mkfs)
				
	def refreshMP(self, uirefresh = True):
		self.partitions = []
		self.mountpoints = MountPoints()
		self.mountpoints.read()
		count = 1
		for part in self.disk[5]:
			capacity = "%d MB" % (part[1] / (1024 * 1024))
			mp = self.mountpoints.get(self.disk[0], count)
			if len(mp) > 0:
				self.partitions.append(PartitionEntry("Partition %d - %s (%s)" % (count, part[2], mp), capacity))
			else:
				self.partitions.append(PartitionEntry("Partition %d - %s" % (count, part[2]), capacity))
			count += 1
		
		if uirefresh:
			self["menu"].setList(self.partitions)
		
	def red(self):
		if len(self.disk[5]) > 0:
			index = self["menu"].getIndex()
			if self.disk[5][index][2] == "Linux swap":
				return
				
		if len(self.partitions) > 0:
			self.sindex = self['menu'].getIndex()
			if self.mounted:
				mp = self.mountpoints.get(self.disk[0], self.sindex+1)
				if len(mp) > 0:
					if self.mountpoints.isMounted(mp):
						if self.mountpoints.umount(mp):
							self.mountpoints.delete(mp)
							self.mountpoints.write()
						else:
							self.session.open(MessageBox, _("Cannot umount device.\nA record in progress, timeshit or some external tools (like samba and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
					else:
						self.mountpoints.delete(mp)
						self.mountpoints.write()
						
				self.refreshMP()
			else:
				self.session.openWithCallback(self.refreshMP, HddMount, self.disk[0], self.sindex+1)
		
	def quit(self):
		self.close()
