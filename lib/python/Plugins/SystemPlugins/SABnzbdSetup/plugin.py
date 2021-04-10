from boxbranding import getMachineBrand, getMachineName
import time

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Console import Console
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Tools.Directories import fileExists


class SABnzbdSetupScreen(Screen):
	skin = """
		<screen position="center,center" size="560,310" title="Samba Setup">
			<widget name="lab1" position="20,90" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labactive" position="180,90" size="250,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="lab2" position="20,160" size="150,30" font="Regular;20" valign="center" transparent="0"/>
			<widget name="labstop" position="180,160" size="100,30" font="Regular;20" valign="center" halign="center" backgroundColor="red"/>
			<widget name="labrun" position="180,160" size="100,30" zPosition="1" font="Regular;20" valign="center"  halign="center" backgroundColor="green"/>
			<ePixmap pixmap="buttons/red.png" position="0,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/yellow.png" position="280,260" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/blue.png" position="420,260" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="420,260" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("SABnzbd Setup"))
		self.skinName = "NetworkServiceSetup"
		self.onChangedEntry = []
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key_red'] = Label(_("Remove Service"))
		self['key_green'] = Label(_("Start"))
		self['key_yellow'] = Label(_("Autostart"))
		self['key_blue'] = Label()
		self['status_summary'] = StaticText()
		self['autostartstatus_summary'] = StaticText()
		self.Console = Console()
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.close, 'back': self.close, 'red': self.UninstallCheck, 'green': self.SABnzbdStartStop, 'yellow': self.activateSABnzbd})
		self.service_name = 'sabnzbd'
		self.onLayoutFinish.append(self.InstallCheck)

	def InstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.InstalldataAvail)

	def InstalldataAvail(self, str, retval, extra_args):
		if not str:
			restartbox = self.session.openWithCallback(self.InstallPackage, MessageBox, _('Your %s %s will be restarted after the installation of service.\n\nDo you want to install now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to install "%s" ?') % self.service_name)
		else:
			self.updateService()

	def InstallPackage(self, val):
		if val:
			self.doInstall(self.installComplete, self.service_name)
		else:
			self.close()

	def doInstall(self, callback, pkgname):
		self["actions"].setEnabled(False)
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO)
		self.message.setTitle(_('Installing Service'))
		self.Console.ePopen('/usr/bin/opkg install ' + pkgname + ' sync', callback)

	def installComplete(self, result=None, retval=None, extra_args=None):
		self["actions"].setEnabled(True)
		from Screens.Standby import TryQuitMainloop
		self.session.open(TryQuitMainloop, 2)

	def UninstallCheck(self):
		self.Console.ePopen('/usr/bin/opkg list_installed ' + self.service_name, self.UninstalldataAvail)

	def UninstalldataAvail(self, str, retval, extra_args):
		if str:
			restartbox = self.session.openWithCallback(self.RemovePackage, MessageBox, _('Your %s %s will be restarted after the removal of service\nDo you want to remove now ?') % (getMachineBrand(), getMachineName()), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_('Ready to remove "%s" ?') % self.service_name)
		else:
			self.updateService()

	def RemovePackage(self, val):
		if val:
			self.doRemove(self.removeComplete, self.service_name)

	def doRemove(self, callback, pkgname):
		self["actions"].setEnabled(False)
		self.message = self.session.open(MessageBox, _("please wait..."), MessageBox.TYPE_INFO)
		self.message.setTitle(_('Removing Service'))
		self.Console.ePopen('/usr/bin/opkg remove ' + pkgname + ' --force-remove --autoremove sync', callback)

	def removeComplete(self, result=None, retval=None, extra_args=None):
		self["actions"].setEnabled(True)
		from Screens.Standby import TryQuitMainloop
		self.session.open(TryQuitMainloop, 2)

	def createSummary(self):
		from Screens.NetworkSetup import NetworkServicesSummary
		return NetworkServicesSummary

	def SABnzbdStartStop(self):
		if not self.my_sabnzbd_run:
			self.Console.ePopen('/etc/init.d/sabnzbd start')
			time.sleep(3)
			self.updateService()
		elif self.my_sabnzbd_run:
			self.Console.ePopen('/etc/init.d/sabnzbd stop')
			time.sleep(3)
			self.updateService()

	def activateSABnzbd(self):
		if fileExists('/etc/rc2.d/S20sabnzbd'):
			self.Console.ePopen('update-rc.d -f sabnzbd remove')
		else:
			self.Console.ePopen('update-rc.d -f sabnzbd defaults')
		time.sleep(3)
		self.updateService()

	def updateService(self, result=None, retval=None, extra_args=None):
		import process
		p = process.ProcessList()
		sabnzbd_process = str(p.named('SABnzbd.py')).strip('[]')
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].setText(_("Disabled"))
		self.my_sabnzbd_active = False
		self.my_sabnzbd_run = False
		if fileExists('/etc/rc2.d/S20sabnzbd'):
			self['labactive'].setText(_("Enabled"))
			self['labactive'].show()
			self.my_sabnzbd_active = True
		if sabnzbd_process:
			self.my_sabnzbd_run = True
		if self.my_sabnzbd_run:
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
		title = _("SABnzbd Setup")
		autostartstatus_summary = self['lab1'].text + ' ' + self['labactive'].text

		for cb in self.onChangedEntry:
			cb(title, status_summary, autostartstatus_summary)


def Plugins(**kwargs):
	return []
