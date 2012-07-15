from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.config import ConfigSelection, ConfigSubsection, KEY_LEFT, KEY_RIGHT, KEY_0, getConfigListEntry
from Components.ConfigList import ConfigList
from Plugins.Plugin import PluginDescriptor

from Tools.Directories import *
from os import path, makedirs, listdir
from time import localtime
from datetime import date

plugin_path = ""

# FIXME: harddiskmanager has a better overview about available mointpoints!
BackupPath = {
		"mtd" : "/media/backup",
		"hdd" : "/media/hdd/backup",
		"usb" : "/media/usb/backup",
		"cf" : "/media/cf/backup"
	}

MountPoints = {
		"mtd" : "/media/backup",
		"hdd" : "/media/hdd",
		"usb" : "/media/usb",
		"cf" : "/media/cf"
	}

class BackupSetup(Screen):
	skin = """
		<screen position="135,144" size="450,300" title="Backup and Restore" >
			<widget name="config" position="10,10" size="430,240" />
			<widget name="cancel" position="10,255" size="100,40" pixmap="~/red.png" transparent="1" alphatest="on" />
			<widget name="canceltext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" foregroundColor="black" />
			<widget name="ok" position="120,255" size="100,40" pixmap="~/green.png" transparent="1" alphatest="on" />
			<widget name="oktext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="black" />
			<widget name="restore" position="230,255" size="100,40" pixmap="~/yellow.png" transparent="1" alphatest="on" />
			<widget name="restoretext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="black" />
			<widget name="backup" position="340,255" size="100,40" pixmap="~/blue.png" transparent="1" alphatest="on" />
			<widget name="backuptext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="black" />
		</screen>"""
		
	def keyLeft(self):
		self["config"].handleKey(KEY_LEFT)

	def keyRight(self):
		self["config"].handleKey(KEY_RIGHT)

	def keyNumberGlobal(self, number):
		print "You pressed number", number
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(KEY_0+number)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.skin_path = plugin_path
		
		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["backuptext"] = Label(_("Backup"))
		self["restoretext"] = Label(_("Restore"))
		self["restore"] = Pixmap()
		self["backup"] = Pixmap()
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()
		
		self.path = ""
		self.list = []
		self["config"] = ConfigList(self.list)
		self.createSetup()
		
		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight
		}, -1)
		
		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.keyCancel,
			"green": self.keySave,
			"blue": self.Backup,
			"yellow": self.Restore,
		})
		

	def createSetup(self):
		print "Creating BackupSetup"
		self.list = [ ]
		self["config"] = ConfigList(self.list)
		self.backup = ConfigSubsection()
		self.backup.type = ConfigSelection(choices = [("settings", _("enigma2 and network")), ("var", _("/var directory")), ("skin", _("/usr/share/enigma2 directory"))], default="settings")
		self.backup.location = ConfigSelection(choices = [("mtd", _("Backup")), ("hdd", _("Harddisk")), ("usb", _("USB Stick")), ("cf", _("CF Drive"))])
		self.list.append(getConfigListEntry(_("Backup Mode"), self.backup.type))
		self.list.append(getConfigListEntry(_("Backup Location"), self.backup.location))

	def createBackupfolders(self):
		self.path = BackupPath[self.backup.location.value]
		print "Creating Backup Folder if not already there..."
		if (path.exists(self.path) == False):
			makedirs(self.path)

	def Backup(self):
		print "this will start the backup now!"
		self.session.openWithCallback(self.runBackup, MessageBox, _("Do you want to backup now?\nAfter pressing OK, please wait!"))	

	def Restore(self):
		print "this will start the restore now!"
		self.session.open(RestoreMenu, self.backup)

	def runBackup(self, result):
		if result:
			if path.ismount(MountPoints[self.backup.location.value]):
				self.createBackupfolders()
				d = localtime()
				dt = date(d.tm_year, d.tm_mon, d.tm_mday)
				self.path = BackupPath[self.backup.location.value]
				if self.backup.type.value == "settings":
					print "Backup Mode: Settings"
					self.session.open(Console, title = "Backup running", cmdlist = ["tar -czvf " + self.path + "/" + str(dt) + "_settings_backup.tar.gz /etc/enigma2/ /etc/network/interfaces /etc/wpa_supplicant.conf"])
				elif self.backup.type.value == "var":
					print "Backup Mode: var"
					self.session.open(Console, title = "Backup running", cmdlist = [ "tar -czvf " + self.path + "/" + str(dt) + "_var_backup.tar.gz /var/"])
				elif self.backup.type.value == "skin":
					print "Backup Mode: skin"
					self.session.open(Console, title ="Backup running", cmdlist = [ "tar -czvf " + self.path + "/" + str(dt) + "_skin_backup.tar.gz /usr/share/enigma2/"])
			else:
				self.session.open(MessageBox, _("Sorry your Backup destination does not exist\n\nPlease choose an other one."), MessageBox.TYPE_INFO)

class RestoreMenu(Screen):
	skin = """
		<screen position="135,144" size="450,300" title="Restore Backups" >
		<widget name="filelist" position="10,10" size="430,240" scrollbarMode="showOnDemand" />
		<widget name="cancel" position="120,255" size="100,40" pixmap="~/red.png" transparent="1" alphatest="on" />		
		<widget name="canceltext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1" foregroundColor="black" />
		<widget name="restore" position="230,255" size="100,40" pixmap="~/yellow.png" transparent="1" alphatest="on" />
		<widget name="restoretext" position="0,0" size="0,0" valign="center" halign="center" zPosition="2" font="Regular;20" transparent="1"  foregroundColor="black" />
		</screen>"""

	def __init__(self, session, backup):
		Screen.__init__(self, session)
		self.skin_path = plugin_path
		self.backup = backup

		self["canceltext"] = Label(_("Cancel"))
		self["restoretext"] = Label(_("Restore"))
		self["restore"] = Pixmap()
		self["cancel"] = Pixmap()

		self.sel = []
		self.val = []
		self.entry = False
		self.exe = False
		
		self.path = ""

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.KeyOk,
			"cancel": self.keyCancel
		}, -1)

		self["shortcuts"] = ActionMap(["ShortcutActions"],
		{
			"red": self.keyCancel,
			"yellow": self.KeyOk,
		})
		self.flist = []
		self["filelist"] = MenuList(self.flist)
		self.fill_list()

	def fill_list(self):
		self.flist = []
		self.path = BackupPath[self.backup.location.value]
		if (path.exists(self.path) == False):
			makedirs(self.path)
		for file in listdir(self.path):
			if (file.endswith(".tar.gz")):
				self.flist.append((file))
				self.entry = True
				self["filelist"].l.setList(self.flist)

	def KeyOk(self):
		if (self.exe == False) and (self.entry == True):
			self.sel = self["filelist"].getCurrent()
			self.val = self.path + self.sel
			self.session.openWithCallback(self.startRestore, MessageBox, _("are you sure you want to restore\nfollowing backup:\n" + self.sel + "\nEnigma2 will restart after the restore"))

	def keyCancel(self):
		self.close()

	def startRestore(self, ret = False):
		if (ret == True):
			self.exe = True
			self.session.open(Console, title = "Restore running", cmdlist = ["tar -xzvf " + self.path + "/" + self.sel + " -C /", "killall -9 enigma2"])

	def Exit(self):
		self.close()

def BackupMain(session, **kwargs):
	session.open(BackupSetup)

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	return PluginDescriptor(name="Backup/Restore", description="Backup and Restore your Settings", icon="backup.png", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=BackupMain)
