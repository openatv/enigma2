from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from Components.Button import Button
from Components.Label import Label
from Screens.MessageBox import MessageBox
from HddPartitions import HddPartitions
from HddInfo import HddInfo
from Extra.Disks import Disks
from Extra.ExtraMessageBox import ExtraMessageBox
from Extra.ExtraActionBox import ExtraActionBox
from Extra.MountPoints import MountPoints
from Extra.ExtrasList import ExtrasList, SimpleEntry

import os
import sys

def DiskEntry(model, size, removable):
	if removable:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/diskusb.png"));
	else:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/disk.png"));		
		
	return (picture, model, size)
	
class HddSetup(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Hard Drive Setup">
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
				 MultiContentEntryText(pos = (90, 0), size = (600, 30), font=0, text = 1),
				 MultiContentEntryText(pos = (110, 30), size = (600, 50), font=1, flags = RT_VALIGN_TOP, text = 2),
				 MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 0),
				],
				"fonts": [gFont("Regular", 24),gFont("Regular", 18)],
				"itemHeight": 60
				}
			</convert>
		</widget>
	</screen>"""
	def __init__(self, session, args = 0):
		self.session = session
		
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Device Manager "))
		self.disks = list ()
		
		self.mdisks = Disks()
		for disk in self.mdisks.disks:
			capacity = "%d MB" % (disk[1] / (1024 * 1024))
			self.disks.append(DiskEntry(disk[3], capacity, disk[2]))
		
		self["menu"] = List(self.disks)
		self["key_red"] = Button(_("Mounts"))
		self["key_green"] = Button(_("Info"))
		self["key_yellow"] = Button(_("Init"))
		self["key_blue"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)
	
	def mkfs(self):
		self.formatted += 1
		return self.mdisks.mkfs(self.mdisks.disks[self.sindex][0], self.formatted)
		
	def refresh(self):
		self.disks = list ()
		
		self.mdisks = Disks()
		for disk in self.mdisks.disks:
			capacity = "%d MB" % (disk[1] / (1024 * 1024))
			self.disks.append(DiskEntry(disk[3], capacity, disk[2]))
			
		self["menu"].setList(self.disks)
		
	def checkDefault(self):
		mp = MountPoints()
		mp.read()
		if not mp.exist("/hdd"):
			mp.add(self.mdisks.disks[self.sindex][0], 1, "/hdd")
			mp.write()
			mp.mount(self.mdisks.disks[self.sindex][0], 1, "/hdd")
			os.system("/bin/mkdir /hdd/movie")
			os.system("/bin/mkdir /hdd/music")
			os.system("/bin/mkdir /hdd/picture")
		
	def format(self, result):
		if result != 0:
			self.session.open(MessageBox, _("Cannot format partition %d" % self.formatted), MessageBox.TYPE_ERROR)
		if self.result == 0:
			if self.formatted > 0:
				self.checkDefault()
				self.refresh()
				return
		elif self.result > 0 and self.result < 3:
			if self.formatted > 1:
				self.checkDefault()
				self.refresh()
				return
		elif self.result == 3:
			if self.formatted > 2:
				self.checkDefault()
				self.refresh()
				return
		elif self.result == 4:
			if self.formatted > 3:
				self.checkDefault()
				self.refresh()
				return
				
		self.session.openWithCallback(self.format, ExtraActionBox, "Formatting partition %d" % (self.formatted + 1), "Initialize disk", self.mkfs)
		
	def fdiskEnded(self, result):
		if result == 0:
			self.format(0)
		elif result == -1:
			self.session.open(MessageBox, _("Cannot umount device.\nA record in progress, timeshit or some external tools (like samba and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, _("Partitioning failed!"), MessageBox.TYPE_ERROR)

	def fdisk(self):
		return self.mdisks.fdisk(self.mdisks.disks[self.sindex][0], self.mdisks.disks[self.sindex][1], self.result)

	def initialaze(self, result):
		if result != 5:
			self.result = result
			self.formatted = 0
			mp = MountPoints()
			mp.read()
			mp.deleteDisk(self.mdisks.disks[self.sindex][0])
			mp.write()
			self.session.openWithCallback(self.fdiskEnded, ExtraActionBox, "Partitioning...", "Initialize disk", self.fdisk)
		
	def yellow(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			self.session.openWithCallback(self.initialaze, ExtraMessageBox, "Please select your preferred configuration.", "HDD Partitioner",
										[ [ "One partition", "partitionmanager.png" ],
										[ "Two partitions (50% - 50%)", "partitionmanager.png" ],
										[ "Two partitions (75% - 25%)", "partitionmanager.png" ],
										[ "Three partitions (33% - 33% - 33%)", "partitionmanager.png" ],
										[ "Four partitions (25% - 25% - 25% - 25%)", "partitionmanager.png" ],
										[ "Cancel", "cancel.png" ],
										], 1, 5)
		
	def green(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			self.session.open(HddInfo, self.mdisks.disks[self.sindex][0])
		
	def red(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			self.session.open(HddPartitions, self.mdisks.disks[self.sindex])
		
	def quit(self):
		self.close()
