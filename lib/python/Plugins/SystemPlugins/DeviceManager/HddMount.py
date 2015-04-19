# for localized messages
from . import _

from enigma import *
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Tools.Directories import fileExists, crawlDirectory, resolveFilename, SCOPE_CURRENT_PLUGIN
from Tools.LoadPixmap import LoadPixmap
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Button import Button
from Components.Label import Label
from Components.Sources.List import List
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop

from MountPoints import MountPoints
from Disks import Disks
from ExtraMessageBox import ExtraMessageBox
from boxbranding import getMachineBrand, getMachineName

import os
import sys
import re

class HddMount(Screen):
	skin = """
	<screen name="HddMount" position="center,center" size="560,430" title="Hard Drive Mount">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget name="menu" position="20,45" scrollbarMode="showOnDemand" size="520,380" transparent="1" />
	</screen>"""

	def __init__(self, session, device, partition):
		Screen.__init__(self, session)

		self.device = device
		self.partition = partition
		self.mountpoints = MountPoints()
		self.mountpoints.read()
		self.fast = False

		self.list = []
		self.list.append(_("Mount as main hdd"))
		self.list.append(_("Mount as /media/hdd1"))
		self.list.append(_("Mount as /media/hdd2"))
		self.list.append(_("Mount as /media/hdd3"))
		self.list.append(_("Mount as /media/hdd4"))
		self.list.append(_("Mount as /media/hdd5"))
		self.list.append(_("Mount as /media/usb"))
		self.list.append(_("Mount as /media/usb1"))
		self.list.append(_("Mount as /media/usb2"))
		self.list.append(_("Mount as /media/usb3"))
		self.list.append(_("Mount as /media/usb4"))
		self.list.append(_("Mount as /media/usb5"))
		self.list.append(_("Mount on custom path"))

		self["menu"] = MenuList(self.list)

		self["key_red"] = Button(_("Fixed mount"))
		self["key_green"] = Button(_("Fast mount"))
		self["key_blue"] = Button(_("Exit"))
		self["key_yellow"] = Button("")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"green": self.green,
			"red": self.ok,
			"cancel": self.quit,
		}, -2)

		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Mountpoints"))

	def ok(self):
		self.fast = False
		selected = self["menu"].getSelectedIndex()
		if selected == 0:
			self.setMountPoint("/media/hdd")
		elif selected == 1:
			self.setMountPoint("/media/hdd1")
		elif selected == 2:
			self.setMountPoint("/media/hdd2")
		elif selected == 3:
			self.setMountPoint("/media/hdd3")
		elif selected == 4:
			self.setMountPoint("/media/hdd4")
		elif selected == 5:
			self.setMountPoint("/media/hdd5")
		elif selected == 6:
			self.setMountPoint("/media/usb")
		elif selected == 7:
			self.setMountPoint("/media/usb1")
		elif selected == 8:
			self.setMountPoint("/media/usb2")
		elif selected == 9:
			self.setMountPoint("/media/usb3")
		elif selected == 10:
			self.setMountPoint("/media/usb4")
		elif selected == 11:
			self.setMountPoint("/media/usb5")
		elif selected == 12:
			self.session.openWithCallback(self.customPath, VirtualKeyBoard, title = (_("Insert mount point:")), text = _("/media/custom"))

	def green(self):
		self.fast = True
		selected = self["menu"].getSelectedIndex()
		if selected == 0:
			self.setMountPoint("/media/hdd")
		elif selected == 1:
			self.setMountPoint("/media/hdd1")
		elif selected == 2:
			self.setMountPoint("/media/hdd2")
		elif selected == 3:
			self.setMountPoint("/media/hdd3")
		elif selected == 4:
			self.setMountPoint("/media/hdd4")
		elif selected == 5:
			self.setMountPoint("/media/hdd5")
		elif selected == 6:
			self.setMountPoint("/media/usb")
		elif selected == 7:
			self.setMountPoint("/media/usb1")
		elif selected == 8:
			self.setMountPoint("/media/usb2")
		elif selected == 9:
			self.setMountPoint("/media/usb3")
		elif selected == 10:
			self.setMountPoint("/media/usb4")
		elif selected == 11:
			self.setMountPoint("/media/usb5")
		elif selected == 12:
			self.session.openWithCallback(self.customPath, VirtualKeyBoard, title = (_("Insert mount point:")), text = _("/media/custom"))

	def customPath(self, result):
		if result and len(result) > 0:
			result = result.rstrip("/")
			os.system("mkdir -p %s" % result)
			self.setMountPoint(result)

	def setMountPoint(self, path):
		self.cpath = path
		if self.mountpoints.exist(path):
			self.session.openWithCallback(self.setMountPointCb, ExtraMessageBox, _("Selected mount point is already used by another drive."), _("Mount point exist!"),
																[ [ _("Change old drive with this new drive"), "ok.png" ],
																[ _("Keep old drive"), "cancel.png" ],
																])
		else:
			self.setMountPointCb(0)

	def setMountPointCb(self, result):
		if result == 0:
			if self.mountpoints.isMounted(self.cpath):
				if not self.mountpoints.umount(self.cpath):
					self.session.open(MessageBox, _("Cannot umount current drive.\nA record in progress, timeshift or some external tools (like samba, swapfile and nfsd) may cause this problem.\nPlease stop this actions/applications and try again"), MessageBox.TYPE_ERROR)
					self.close()
					return
			self.mountpoints.delete(self.cpath)
			if not self.fast:
				self.mountpoints.add(self.device, self.partition, self.cpath)
			self.mountpoints.write()
			if not self.mountpoints.mount(self.device, self.partition, self.cpath):
				self.session.open(MessageBox, _("Cannot mount new drive.\nPlease check filesystem or format it and try again"), MessageBox.TYPE_ERROR)
			elif self.cpath == "/media/hdd":
				os.system("/bin/mkdir -p /media/hdd/movie")

			if not self.fast:
				message = _("Device Fixed Mount Point change needs a system restart in order to take effect.\nRestart your %s %s now?") % (getMachineBrand(), getMachineName())
				mbox = self.session.openWithCallback(self.restartBox, MessageBox, message, MessageBox.TYPE_YESNO)
				mbox.setTitle(_("Restart %s %s") % (getMachineBrand(), getMachineName()))
			else:
				self.close()

	def restartBox(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()

	def quit(self):
		self.close()

def MountEntry(description, details):
	picture = LoadPixmap(cached = True, path = resolveFilename(SCOPE_CURRENT_PLUGIN, "SystemPlugins/DeviceManager/icons/diskusb.png"));
	return (picture, description, details)

class HddFastRemove(Screen):
	skin = """
	<screen name="HddFastRemove" position="center,center" size="560,430" title="Hard Drive Fast Umount">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="140,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_blue" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget source="menu" render="Listbox" position="10,55" size="520,380" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{"template": [
					MultiContentEntryPixmapAlphaTest(pos = (5, 0), size = (48, 48), png = 0),
					MultiContentEntryText(pos = (65, 3), size = (190, 38), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_TOP, text = 1),
					MultiContentEntryText(pos = (165, 27), size = (290, 38), font=1, flags = RT_HALIGN_LEFT|RT_VALIGN_TOP, text = 2),
					],
					"fonts": [gFont("Regular", 22), gFont("Regular", 18)],
					"itemHeight": 50
				}
			</convert>
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.refreshMP(False)

		self["menu"] = List(self.disks)
		self["key_red"] = Button(_("Unmount"))
		self["key_blue"] = Button(_("Exit"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"red": self.red,
			"cancel": self.quit,
		}, -2)

		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("Fast Mounted Remove"))

	def red(self):
		if len(self.mounts) > 0:
			self.sindex = self["menu"].getIndex()
			self.mountpoints.umount(self.mounts[self.sindex]) # actually umount device here - also check both cases possible - for instance error case also check with stay in /e.g. /media/usb folder on telnet
			self.session.open(MessageBox, _("Fast mounted Media unmounted.\nYou can safely remove the Device now, if no further Partitions (displayed as P.x on Devicelist - where x >=2) are mounted on the same Device.\nPlease unmount Fixed Mounted Devices with Device Manager Panel!"), MessageBox.TYPE_INFO)
			self.refreshMP(True)

	def refreshMP(self, uirefresh = True):
		self.mdisks = Disks()
		self.mountpoints = MountPoints()
		self.mountpoints.read()
		self.disks = list ()
		self.mounts = list ()
		for disk in self.mdisks.disks:
			if disk[2] == True:
				diskname = disk[3]
				for partition in disk[5]:
					mp = ""
					rmp = ""
					try:
						mp = self.mountpoints.get(partition[0][:3], int(partition[0][3:]))
						rmp = self.mountpoints.getRealMount(partition[0][:3], int(partition[0][3:]))
					except Exception, e:
						pass
					if len(mp) > 0:
						self.disks.append(MountEntry(disk[3], "P.%s (Fixed: %s)" % (partition[0][3:], mp)))
						self.mounts.append(mp)
					elif len(rmp) > 0:
						self.disks.append(MountEntry(disk[3], "P.%s (Fast: %s)" % (partition[0][3:], rmp)))
						self.mounts.append(rmp)
		if uirefresh:
			self["menu"].setList(self.disks)

	def quit(self):
		self.close()
