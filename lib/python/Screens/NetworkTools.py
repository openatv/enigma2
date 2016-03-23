import time
from os import chmod, access, remove, X_OK
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.Console import Console
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.ScrollLabel import ScrollLabel
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigIP, ConfigText, ConfigPassword, ConfigSelection, getConfigListEntry, ConfigNumber, ConfigLocations, NoSave, ConfigMacText
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, HelpableActionMap
from Tools.Directories import fileExists
from boxbranding import getMachineBrand, getMachineName, getBoxType
from subprocess import call
import commands
import os

basegroup = "packagegroup-base"

class NetworkNfs(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("NFS Setup"))
		self.skinName = "NetworkNfs"
		self.onChangedEntry = [ ]
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label()
		self.Console = Console()
		self.my_nfs_active = False
		self.my_nfs_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.NfsStartStop, 'yellow': self.Nfsset})
		self.service_name = basegroup + '-nfs'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox,_('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input = False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval,extra_args=None):
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.InstallPackage,MessageBox,_('Your %s %s will be restarted after the installation of service.\nReady to install %s ?')  % (getMachineBrand(), getMachineName(), self.service_name), MessageBox.TYPE_YESNO)

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox,_("please wait..."), MessageBox.TYPE_INFO, enable_input = False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self,result = None, retval = None, extra_args = None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage,MessageBox,_('Your %s %s will be restarted after the removal of service.\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove %s ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox,_("please wait..."), MessageBox.TYPE_INFO, enable_input = False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self,result = None, retval = None, extra_args = None):
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		return NetworkServicesSummary

	def NfsStartStop(self):
		if not self.my_nfs_run:
			self.Console.ePopen('/etc/init.d/nfsserver start', self.StartStopCallback)
		elif self.my_nfs_run:
			self.Console.ePopen('/etc/init.d/nfsserver stop', self.StartStopCallback)

	def StartStopCallback(self, result = None, retval = None, extra_args = None):
		time.sleep(3)
		self.updateService()

	def Nfsset(self):
		if fileExists('/etc/rc2.d/S13nfsserver'):
			self.Console.ePopen('update-rc.d -f nfsserver remove', self.StartStopCallback)
		else:
			self.Console.ePopen('update-rc.d -f nfsserver defaults 13', self.StartStopCallback)

	def updateService(self):
		import process
		p = process.ProcessList()
		nfs_process = str(p.named('nfsd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_nfs_active = False
		self.my_nfs_run = False
		if fileExists('/etc/rc2.d/S13nfsserver'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_nfs_active = True
		if nfs_process:
			self.my_nfs_run = True
		if self.my_nfs_run:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary= self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_green'].setText(_("Start"))
			status_summary= self['lab2'].text + ' ' + self['labstop'].text
		title = _("NFS Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

class NetworkSamba(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Setup"))
		self.skinName = "NetworkSamba"
		self.onChangedEntry = [ ]
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_green'] = Label(_("Start"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label(_("Show Log"))
		self.Console = Console()
		self.my_Samba_active = False
		self.my_Samba_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.SambaStartStop, 'yellow': self.activateSamba, 'blue': self.Sambashowlog})
		self.service_name = basegroup + '-smbfs-server'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.checkNetworkState)

	def checkNetworkState(self, str, retval, extra_args):
		if 'Collected errors' in str:
			self.session.openWithCallback(self.close, MessageBox, _("A background update check is in progress, please wait a few minutes and try again."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif not str:
			self.feedscheck = self.session.open(MessageBox,_('Please wait while feeds state is checked.'), MessageBox.TYPE_INFO, enable_input = False)
			self.feedscheck.setTitle(_('Checking Feeds'))
			cmd1 = "opkg update"
			self.CheckConsole = Console()
			self.CheckConsole.ePopen(cmd1, self.checkNetworkStateFinished)
		else:
			self.updateService()

	def checkNetworkStateFinished(self, result, retval,extra_args=None):
		if 'bad address' in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Your %s %s is not connected to the internet, please check your network settings and try again.") % (getMachineBrand(), getMachineName()), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		elif ('wget returned 1' or 'wget returned 255' or '404 Not Found') in result:
			self.session.openWithCallback(self.InstallPackageFailed, MessageBox, _("Sorry feeds are down for maintenance, please try again later."), type=MessageBox.TYPE_INFO, timeout=10, close_on_any_key=True)
		else:
			self.session.openWithCallback(self.QuestionCallback, MessageBox,_('Your %s %s will be restarted after the installation of service.\nReady to install %s ?')  % (getMachineBrand(), getMachineName(), self.service_name), MessageBox.TYPE_YESNO)

	def QuestionCallback(self, val):
		if val:
			self.session.openWithCallback(self.InstallPackage, MessageBox, _('Do you want to also install samba client?\nThis allows you to mount your windows shares on this device.'), MessageBox.TYPE_YESNO)
		else:
			self.feedscheck.close()
			self.close()

	def InstallPackage(self, val):
		if val:
			self.service_name = self.service_name + ' ' + basegroup + '-smbfs-client'
		self.doInstall(self.installComplete, self.service_name)

	def InstallPackageFailed(self, val):
		self.feedscheck.close()
		self.close()

	def doInstall(self, callback, pkgname):
		self.message = self.session.open(MessageBox,_("please wait..."), MessageBox.TYPE_INFO, enable_input = False)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname, callback)

	def installComplete(self,result = None, retval = None, extra_args = None):
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.service_name = self.service_name + ' ' + basegroup + '-smbfs-client'
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.RemovedataAvail)

	def RemovedataAvail(self, str, retval, extra_args):
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage,MessageBox,_('Your %s %s will be restarted after the removal of service.\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove %s ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self.message = self.session.open(MessageBox,_("please wait..."), MessageBox.TYPE_INFO, enable_input = False)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove', callback)

	def removeComplete(self,result = None, retval = None, extra_args = None):
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		return NetworkServicesSummary

	def Sambashowlog(self):
		self.session.open(NetworkSambaLog)

	def SambaStartStop(self):
		commands = []
		if not self.my_Samba_run:
			commands.append('/etc/init.d/samba start')
		elif self.my_Samba_run:
			commands.append('/etc/init.d/samba stop')
			commands.append('killall nmbd')
			commands.append('killall smbd')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def StartStopCallback(self, result = None, retval = None, extra_args = None):
		time.sleep(3)
		self.updateService()

	def activateSamba(self):
		commands = []
		if fileExists('/etc/rc2.d/S20samba'):
			commands.append('update-rc.d -f samba remove')
		else:
			commands.append('update-rc.d -f samba defaults')
		self.Console.eBatch(commands, self.StartStopCallback, debug=True)

	def updateService(self):
		import process
		p = process.ProcessList()
		samba_process = str(p.named('smbd')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_Samba_active = False
		if fileExists('/etc/rc2.d/S20samba'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_Samba_active = True

		self.my_Samba_run = False

		if samba_process:
			self.my_Samba_run = True

		if self.my_Samba_run:
			self['labstop'].hide()
			self['labactive'].show()
			self['labrun'].show()
			self['key_green'].setText(_("Stop"))
			status_summary = self['lab2'].text + ' ' + self['labrun'].text
		else:
			self['labrun'].hide()
			self['labstop'].show()
			self['labactive'].show()
			self['key_green'].setText(_("Start"))
			status_summary = self['lab2'].text + ' ' + self['labstop'].text
		title = _("Samba Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)

class NetworkSambaLog(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Samba Log"))
		self.skinName = "NetworkLog"
		self['infotext'] = ScrollLabel('')
		self.Console = Console()
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'up': self['infotext'].pageUp, 'down': self['infotext'].pageDown})
		strview = ''
		self.Console.ePopen('tail /tmp/smb.log > /tmp/tmp.log')
		time.sleep(1)
		if fileExists('/tmp/tmp.log'):
			f = open('/tmp/tmp.log', 'r')
			for line in f.readlines():
				strview += line
			f.close()
			remove('/tmp/tmp.log')
		self['infotext'].setText(strview)

class NetworkServicesSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["title"] = StaticText("")
		self["status_summary"] = StaticText("")
		self["autostartstatus_summary"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.updateService()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, title, status_summary, autostartstatus_summary):
		self["title"].text = title
		self["status_summary"].text = status_summary
		self["autostartstatus_summary"].text = autostartstatus_summary

class InetdRecovery(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Inetd recovery"))
		
		self["key_red"] = Label(_("Cancel"))
		self["key_blue"] = Label(_("Recover"))

		self.list = []
		
		self.ipv6 = NoSave(ConfigYesNo(default=False))
		self.list.append(getConfigListEntry(_("IPv6"), self.ipv6))
		
		ConfigListScreen.__init__(self, self.list)

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions", {
			"cancel": (self.close, _("exit inetd recovery"))
		})
		self["ColorActions"] = HelpableActionMap(self, "ColorActions", {
			"red": (self.close, _("exit inetd recovery")),
			"blue": (self.keyBlue, _("recover inetd")),
		})
		
	def keyBlue(self):
		sockTypetcp = "tcp"
		sockTypeudp = "udp"
		if self.ipv6.value:
			sockTypetcp = "tcp6"
			sockTypeudp = "udp6"
			
		inetdData  = "# /etc/inetd.conf:  see inetd(8) for further informations.\n"
		inetdData += "#\n"
		inetdData += "# Internet server configuration database\n"
		inetdData += "#\n"
		inetdData += "# If you want to disable an entry so it isn't touched during\n"
		inetdData += "# package updates just comment it out with a single '#' character.\n"
		inetdData += "#\n"
		inetdData += "# <service_name> <sock_type> <proto> <flags> <user> <server_path> <args>\n"
		inetdData += "#\n"
		inetdData += "#:INTERNAL: Internal services\n"
		inetdData += "#echo	stream	" + sockTypetcp + "	nowait	root	internal\n"
		inetdData += "#echo	dgram	" + sockTypeudp + "	wait	root	internal\n"
		inetdData += "#chargen	stream	" + sockTypetcp + "	nowait	root	internal\n"
		inetdData += "#chargen	dgram	" + sockTypeudp + "	wait	root	internal\n"
		inetdData += "#discard	stream	" + sockTypetcp + "	nowait	root	internal\n"
		inetdData += "#discard	dgram	" + sockTypeudp + "	wait	root	internal\n"
		inetdData += "#daytime	stream	" + sockTypetcp + "	nowait	root	internal\n"
		inetdData += "#daytime	dgram	" + sockTypeudp + "	wait	root	internal\n"
		inetdData += "#time	stream	tcp	nowait	root	internal\n"
		inetdData += "#time	dgram	" + sockTypeudp + "	wait	root	internal\n"
		inetdData += "#ftp	stream	" + sockTypetcp + "	nowait	root	/usr/sbin/vsftpd	vsftpd\n"
		inetdData += "#ftp	stream	" + sockTypetcp + "	nowait	root	ftpd	ftpd -w /\n"
		inetdData += "#telnet	stream	" + sockTypetcp + "	nowait	root	/usr/sbin/telnetd	telnetd\n"
		if fileExists('/usr/sbin/smbd'):
			inetdData += "#microsoft-ds	stream	" + sockTypetcp + "	nowait	root	/usr/sbin/smbd	smbd\n"
		if fileExists('/usr/sbin/nmbd'):
			inetdData += "#netbios-ns	dgram	" + sockTypeudp + "	wait	root	/usr/sbin/nmbd	nmbd\n"
		if fileExists('/usr/bin/streamproxy'):
			inetdData += "#8001	stream	" + sockTypetcp + "	nowait	root	/usr/bin/streamproxy	streamproxy\n"
		if getBoxType() in ('gbuhdquad', 'gbquad', 'gbquadplus'):
			inetdData += "8002	stream	" + sockTypetcp + "	nowait	root	/usr/bin/transtreamproxy	transtreamproxy\n"
			
		fd = file("/etc/inetd.conf", 'w')
		fd.write(inetdData)
		fd.close()
		self.inetdRestart()
		
		self.session.open(MessageBox, _("Successfully restored /etc/inetd.conf!"), type = MessageBox.TYPE_INFO,timeout = 10)
		self.close()
		
	def inetdRestart(self):
		if fileExists("/etc/init.d/inetd"):
			os.system("/etc/init.d/inetd restart")
		elif fileExists("/etc/init.d/inetd.busybox"):
			os.system("/etc/init.d/inetd.busybox restart")