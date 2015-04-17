# for localized messages
from . import _

from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.Directories import resolveFilename, SCOPE_CURRENT_PLUGIN
from Tools.LoadPixmap import LoadPixmap
from Components.Button import Button
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from HddPartitions import HddPartitions
from HddInfo import HddInfo

from Disks import Disks
from ExtraMessageBox import ExtraMessageBox
from ExtraActionBox import ExtraActionBox
from MountPoints import MountPoints
from boxbranding import getMachineBrand, getMachineName

import os
import sys

def DiskEntry(model, size, removable):
	if removable:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/DeviceManager/icons/diskusb.png"));
	else:
		picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/DeviceManager/icons/disk.png"));

	return (picture, model, size)

class HddSetup(Screen):
	skin = """
	<screen name="HddSetup" position="center,center" size="560,430" title="Hard Drive Setup">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget source="menu" render="Listbox" position="20,45" size="520,380" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{"template": [
					MultiContentEntryPixmapAlphaTest(pos = (5, 0), size = (48, 48), png = 0),
					MultiContentEntryText(pos = (65, 10), size = (330, 38), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_TOP, text = 1),
					MultiContentEntryText(pos = (405, 10), size = (125, 38), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_TOP, text = 2),
					],
					"fonts": [gFont("Regular", 22)],
					"itemHeight": 50
				}
			</convert>
		</widget>
	</screen>"""

	def __init__(self, session, args = 0):
		self.session = session

		Screen.__init__(self, session)
		self.disks = list ()

		self.mdisks = Disks()
		for disk in self.mdisks.disks:
			capacity = "%d MB" % (disk[1] / (1024 * 1024))
			self.disks.append(DiskEntry(disk[3], capacity, disk[2]))

		self["menu"] = List(self.disks)
		self["key_red"] = Button(_("Mounts"))
		self["key_green"] = Button(_("Info"))
		self["key_yellow"] = Button(_("Initialize"))
		self["key_blue"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)

		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Devicelist"))

	def isExt4Supported(self):
		return "ext4" in open("/proc/filesystems").read()

	def mkfs(self):
		self.formatted += 1
		return self.mdisks.mkfs(self.mdisks.disks[self.sindex][0], self.formatted, self.fsresult)

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
		if not mp.exist("/media/hdd"):
			mp.add(self.mdisks.disks[self.sindex][0], 1, "/media/hdd")
			mp.write()
			mp.mount(self.mdisks.disks[self.sindex][0], 1, "/media/hdd")
			os.system("/bin/mkdir -p /media/hdd/movie")

			message = _("Fixed mounted first initialized Storage Device to /media/hdd. It needs a system restart in order to take effect.\nRestart your %s %s now?") % (getMachineBrand(), getMachineName())
			mbox = self.session.openWithCallback(self.restartBox, MessageBox, message, MessageBox.TYPE_YESNO)
			mbox.setTitle(_("Restart %s %s") % (getMachineBrand(), getMachineName()))

	def restartBox(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)

	def format(self, result):
		if result != 0:
			self.session.open(MessageBox, _("Cannot format partition %d") % (self.formatted), MessageBox.TYPE_ERROR)
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

		self.session.openWithCallback(self.format, ExtraActionBox, _("Formatting partition %d") % (self.formatted + 1), _("Initialize disk"), self.mkfs)

	def fdiskEnded(self, result):
		if result == 0:
			self.format(0)
		elif result == -1:
			self.session.open(MessageBox, _("Cannot umount current device.\nA record in progress, timeshift or some external tools (like samba, swapfile and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
		else:
			self.session.open(MessageBox, _("Partitioning failed!"), MessageBox.TYPE_ERROR)

	def fdisk(self):
		return self.mdisks.fdisk(self.mdisks.disks[self.sindex][0], self.mdisks.disks[self.sindex][1], self.result, self.fsresult)

	def initialaze(self, result):
		if not self.isExt4Supported():
			result += 1

		if result != 4:
			self.fsresult = result
			self.formatted = 0
			mp = MountPoints()
			mp.read()
			mp.deleteDisk(self.mdisks.disks[self.sindex][0])
			mp.write()
			self.session.openWithCallback(self.fdiskEnded, ExtraActionBox, _("Partitioning..."), _("Initialize disk"), self.fdisk)

	def chooseFSType(self, result):
		if result != 5:
			self.result = result
			if self.isExt4Supported():
				self.session.openWithCallback(self.initialaze, ExtraMessageBox, _("Format as"), _("Partitioner"),
											[ [ "Ext4", "partitionmanager.png" ],
											[ "Ext3", "partitionmanager.png" ],
											[ "NTFS", "partitionmanager.png" ],
											[ "Fat32", "partitionmanager.png" ],
											[ _("Cancel"), "cancel.png" ],
											], 1, 4)
			else:
				self.session.openWithCallback(self.initialaze, ExtraMessageBox, _("Format as"), _("Partitioner"),
											[ [ "Ext3", "partitionmanager.png" ],
											[ "NTFS", "partitionmanager.png" ],
											[ "Fat32", "partitionmanager.png" ],
											[ _("Cancel"), "cancel.png" ],
											], 1, 3)

	def yellow(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			self.session.openWithCallback(self.chooseFSType, ExtraMessageBox, _("Please select your preferred configuration."), _("Partitioner"),
										[ [ _("One partition"), "partitionmanager.png" ],
										[ _("Two partitions (50% - 50%)"), "partitionmanager.png" ],
										[ _("Two partitions (75% - 25%)"), "partitionmanager.png" ],
										[ _("Three partitions (33% - 33% - 33%)"), "partitionmanager.png" ],
										[ _("Four partitions (25% - 25% - 25% - 25%)"), "partitionmanager.png" ],
										[ _("Cancel"), "cancel.png" ],
										], 1, 5)

	def green(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			self.session.open(HddInfo, self.mdisks.disks[self.sindex][0])

	def red(self):
		if len(self.mdisks.disks) > 0:
			self.sindex = self['menu'].getIndex()
			if len(self.mdisks.disks[self.sindex][5]) == 0:
				self.session.open(MessageBox, _("You need to initialize your storage device first"), MessageBox.TYPE_ERROR)
			else:
				self.session.open(HddPartitions, self.mdisks.disks[self.sindex])

	def quit(self):
		self.close()
