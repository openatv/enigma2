# for localized messages
from . import _
from Components.Button import Button
from Components.ActionMap import ActionMap, NumberActionMap
from Components.config import getConfigListEntry, config, ConfigSubsection, ConfigYesNo, ConfigText, ConfigSelection, ConfigInteger, ConfigClock, NoSave, configfile
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.Label import Label
from Components.Sources.List import List
from Components.ScrollLabel import ScrollLabel
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Harddisk import harddiskmanager
from Components.Language import language
from Components.Pixmap import Pixmap,MultiPixmap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Console import Console
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from base64 import encodestring
from enigma import eListboxPythonMultiContent, ePoint, eTimer, getDesktop, gFont, iPlayableService, iServiceInformation, loadPNG, RT_HALIGN_RIGHT
from skin import parseColor
from os import system, listdir, remove, rename, symlink, unlink, path, mkdir, access, W_OK, R_OK, F_OK, popen
from enigma import eTimer, ePoint
from time import sleep
from Screens.VirtualKeyBoard import VirtualKeyBoard

import os

config.plugins.aafpanel = ConfigSubsection()
config.plugins.aafpanel.cronmanager_commandtype = NoSave(ConfigSelection(choices = [ ('custom',_("Custom")),('predefined',_("Predefined")) ]))
config.plugins.aafpanel.cronmanager_cmdtime = NoSave(ConfigClock(default=0))
config.plugins.aafpanel.cronmanager_cmdtime.value, mytmpt = ([0, 0], [0, 0])
config.plugins.aafpanel.cronmanager_user_command = NoSave(ConfigText(fixed_size=False))
config.plugins.aafpanel.cronmanager_runwhen = NoSave(ConfigSelection(default='Daily', choices = [('Hourly', _("Hourly")),('Daily', _("Daily")),('Weekly', _("Weekly")),('Monthly', _("Monthly"))]))
config.plugins.aafpanel.cronmanager_dayofweek = NoSave(ConfigSelection(default='Monday', choices = [('Monday', _("Monday")),('Tuesday', _("Tuesday")),('Wednesday', _("Wednesday")),('Thursday', _("Thursday")),('Friday', _("Friday")),('Saturday', _("Saturday")),('Sunday', _("Sunday"))]))
config.plugins.aafpanel.cronmanager_dayofmonth = NoSave(ConfigInteger(default=1, limits=(1, 31)))

class CronManager(Screen):
	skin = """
		<screen position="center,center" size="590,400" title="Cron Manager">
			<widget name="lab1" position="10,0" size="100,24" font="Regular;20" valign="center" transparent="0" />
			<widget name="labdisabled" position="110,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="red" zPosition="1" />
			<widget name="labactive" position="110,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="green" zPosition="2" />
			<widget name="lab2" position="240,0" size="150,24" font="Regular;20" valign="center" transparent="0" />
			<widget name="labstop" position="390,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="red" zPosition="1" />
			<widget name="labrun" position="390,0" size="100,24" font="Regular;20" valign="center" halign="center" backgroundColor="green" zPosition="2"/>
			<widget source="list" render="Listbox" position="10,35" size="540,325" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,350" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="150,350" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="300,350" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="450,350" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_yellow" position="150,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_green" position="300,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget name="key_blue" position="450,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		</screen>"""


	def __init__(self, session):
		Screen.__init__(self, session)
		if not path.exists('/usr/scripts'):
			mkdir('/usr/scripts', 0755)
		Screen.setTitle(self, _("Cron Manager"))
		self['lab1'] = Label(_("Autostart:"))
		self['labactive'] = Label(_(_("Active")))
		self['labdisabled'] = Label(_(_("Disabled")))
		self['lab2'] = Label(_("Current Status:"))
		self['labstop'] = Label(_("Stopped"))
		self['labrun'] = Label(_("Running"))
		self['key'] = Label(_("H: = Hourly / D: = Daily / W: = Weekly / M: = Monthly"))
		self.Console = Console()
		self.my_crond_active = False
		self.my_crond_run = False
		
		self['key_red'] = Label(_("Add"))
		self['key_green'] = Label(_("Delete"))
		self['key_yellow'] = Label(_("Start"))
		self['key_blue'] = Label(_("Autostart"))
		self.list = []
		self['list'] = List(self.list)
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'ok': self.info, 'back': self.close, 'red': self.addtocron, 'green': self.delcron, 'yellow': self.CrondStart, 'blue': self.autostart})
		self.onLayoutFinish.append(self.updateList)

	def CrondStart(self):
		if self.my_crond_run == False:
			self.Console.ePopen('/etc/init.d/busybox-cron start')
			sleep(3)
			self.updateList()
		elif self.my_crond_run == True:
			self.Console.ePopen('/etc/init.d/busybox-cron stop')
			sleep(3)
			self.updateList()

	def autostart(self):
		if path.exists('/etc/rc0.d/K20busybox-cron'):
			unlink('/etc/rc0.d/K20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc0.d/K20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc1.d/K20busybox-cron'):
			unlink('/etc/rc1.d/K20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc1.d/K20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc2.d/S20busybox-cron'):
			unlink('/etc/rc2.d/S20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc2.d/S20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc3.d/S20busybox-cron'):
			unlink('/etc/rc3.d/S20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc3.d/S20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc4.d/S20busybox-cron'):
			unlink('/etc/rc4.d/S20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc4.d/S20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc5.d/S20busybox-cron'):
			unlink('/etc/rc5.d/S20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc5.d/S20busybox-cron')
			mymess = _("Autostart Enabled.")

		if path.exists('/etc/rc6.d/K20busybox-cron'):
			unlink('/etc/rc6.d/K20busybox-cron')
			mymess = _("Autostart Disabled.")
		else:
			symlink('/etc/init.d/busybox-cron', '/etc/rc6.d/K20busybox-cron')
			mymess = _("Autostart Enabled.")

		mybox = self.session.open(MessageBox, mymess, MessageBox.TYPE_INFO, timeout = 10)
		mybox.setTitle(_("Info"))
		self.updateList()

	def addtocron(self):
		self.session.openWithCallback(self.updateList, SetupCronConf)

	def updateList(self):
		self['labrun'].hide()
		self['labstop'].hide()
		self['labactive'].hide()
		self['labdisabled'].hide()
		self.my_crond_active = False
		self.my_crond_run = False
		if path.exists('/etc/rc3.d/S20busybox-cron'):
			self['labdisabled'].hide()
			self['labactive'].show()
			self.my_crond_active = True
		else:
			self['labactive'].hide()
			self['labdisabled'].show()
		if self.check_crond():
			self.my_crond_run = True
		if self.my_crond_run == True:
			self['labstop'].hide()
			self['labrun'].show()
			self['key_yellow'].setText(_("Stop"))
		else:
			self['labstop'].show()
			self['labrun'].hide()
			self['key_yellow'].setText(_("Start"))

		self.list = []
		if path.exists('/etc/cron/crontabs/root'):
			f = open('/etc/cron/crontabs/root', 'r')
			for line in f.readlines():
				parts = line.strip().split()
				if parts:
					if parts[1] == '*':
						try:
							line2 = 'H: 00:' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
						except:
							try:
								line2 = 'H: 00:' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
							except:
								try:
									line2 = 'H: 00:' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
								except:
									try:
										line2 = 'H: 00:' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
									except:
										line2 = 'H: 00:' + parts[0].zfill(2) + '\t' + parts[5]
						res = (line2, line)
						self.list.append(res)
					elif parts[2] == '*' and parts[4] == '*':
						try:
							line2 = 'D: ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
						except:
							try:
								line2 = 'D: ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
							except:
								try:
									line2 = 'D: ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
								except:
									try:
										line2 = 'D: ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
									except:
										line2 = 'D: ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						res = (line2, line)
						self.list.append(res)
					elif parts[3] == '*':
						if parts[4] == "*":
							try:
								line2 = 'M:  Day ' + parts[2] + '  ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'M:  Day ' + parts[2] + '  ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'M:  Day ' + parts[2] + '  ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'M:  Day ' + parts[2] + '  ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'M:  Day ' + parts[2] + '  ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "0":
							try:
								line2 = 'W:  Sunday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Sunday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Sunday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Sunday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Sunday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "1":
							try:
								line2 = 'W:  Monnday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Monday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Monday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Monday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Monday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "2":
							try:
								line2 = 'W:  Tuesnday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Tuesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Tuesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Tuesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Tuesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "3":
							try:
								line2 = 'W:  Wednesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Wednesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Wednesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Wednesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Wednesday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "4":
							try:
								line2 = 'W:  Thursday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Thursday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Thursday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Thursday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Thursday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "5":
							try:
								line2 = 'W:  Friday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Friday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Friday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Friday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Friday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						elif parts[4] == "6":
							try:
								line2 = 'W:  Saturday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8] + parts[9]
							except:
								try:
									line2 = 'W:  Saturday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7] + parts[8]
								except:
									try:
										line2 = 'W:  Saturday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6] + parts[7]
									except:
										try:
											line2 = 'W:  Saturday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5] + parts[6]
										except:
											line2 = 'W:  Saturday ' + parts[1].zfill(2) + ':' + parts[0].zfill(2) + '\t' + parts[5]
						res = (line2, line)
						self.list.append(res)
			f.close()
		self['list'].list = self.list

	def delcron(self):
		self.sel = self['list'].getCurrent()
		if self.sel:
			message = _("Are you sure you want to delete this:\n ") + self.sel
			ybox = self.session.openWithCallback(self.doDelCron, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Remove Confirmation"))

	def doDelCron(self):
		mysel = self['list'].getCurrent()
		if mysel:
			myline = mysel[1]
			file('/etc/cron/crontabs/root.tmp', 'w').writelines([l for l in file('/etc/cron/crontabs/root').readlines() if myline not in l])
			rename('/etc/cron/crontabs/root.tmp','/etc/cron/crontabs/root')
			rc = system('crontab /etc/cron/crontabs/root -c /etc/cron/crontabs')
			self.updateList()

	def info(self):
		mysel = self['list'].getCurrent()
		if mysel:
			myline = mysel[1]
			self.session.open(MessageBox, _(myline), MessageBox.TYPE_INFO)
			
	def check_crond(self):
		process = os.popen("ps | grep crond").read().splitlines()
		if len(process) > 2:
			return 1
		else:
			return 0		

class SetupCronConf(Screen, ConfigListScreen):
	skin = """
		<screen position="center,center" size="560,400" title="Cron Manager">
			<widget name="config" position="10,20" size="540,400" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="90,350" size="140,40" alphatest="on" />
			<widget name="key_red" position="90,350" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="160,260" zPosition="1" size="1,1" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_text.png" position="250,353" zPosition="4" size="35,25" alphatest="on" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Cron Manager"))
		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self['key_red'] = Label(_("Save"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', 'VirtualKeyboardActions'], {'red': self.checkentry, 'back': self.close, 'showVirtualKeyboard': self.KeyText})
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.createSetup()

	def createSetup(self):
		predefinedlist = []
		f = listdir('/usr/scripts')
		if f:
			for line in f:
				parts = line.split()
				path = "/usr/scripts/"
				pkg = parts[0]
				description = path + parts[0]
				if pkg.find('.sh') >= 0:
					predefinedlist.append((description, pkg))
			predefinedlist.sort()
		config.plugins.aafpanel.cronmanager_predefined_command = NoSave(ConfigSelection(choices = predefinedlist))
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("Run how often ?"), config.plugins.aafpanel.cronmanager_runwhen))
		if config.plugins.aafpanel.cronmanager_runwhen.value != 'Hourly':
			self.list.append(getConfigListEntry(_("Time to execute command or script"), config.plugins.aafpanel.cronmanager_cmdtime))
		if config.plugins.aafpanel.cronmanager_runwhen.value == 'Weekly':
			self.list.append(getConfigListEntry(_("What Day of week ?"), config.plugins.aafpanel.cronmanager_dayofweek))
		if config.plugins.aafpanel.cronmanager_runwhen.value == 'Monthly':
			self.list.append(getConfigListEntry(_("What Day of month ?"), config.plugins.aafpanel.cronmanager_dayofmonth))
		self.list.append(getConfigListEntry(_("Command type"), config.plugins.aafpanel.cronmanager_commandtype))
		if config.plugins.aafpanel.cronmanager_commandtype.value == 'custom':
			self.list.append(getConfigListEntry(_("Command To Run"), config.plugins.aafpanel.cronmanager_user_command))
		else:
			self.list.append(getConfigListEntry(_("Command To Run"), config.plugins.aafpanel.cronmanager_predefined_command))
		self["config"].list = self.list
		self["config"].setList(self.list)

	# for summary:
	def changedEntry(self):
		if self["config"].getCurrent()[0] == _("Run how often ?") or self["config"].getCurrent()[0] == _("Command type"):
			self.createSetup()
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def KeyText(self):
		sel = self['config'].getCurrent()
		if sel:
			self.vkvar = sel[0]
			if self.vkvar == _("Command To Run"):
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def checkentry(self):
		msg = ''
		if (config.plugins.aafpanel.cronmanager_commandtype.value == 'predefined' and config.plugins.aafpanel.cronmanager_predefined_command.value == '') or config.plugins.aafpanel.cronmanager_commandtype.value == 'custom' and config.plugins.aafpanel.cronmanager_user_command.value == '':
			msg = 'You must set at least one Command'
		if msg:
			self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
		else:
			self.saveMycron()

	def saveMycron(self):
		hour = '%02d' % config.plugins.aafpanel.cronmanager_cmdtime.value[0]
		minutes = '%02d' % config.plugins.aafpanel.cronmanager_cmdtime.value[1]
		if config.plugins.aafpanel.cronmanager_commandtype.value == 'predefined' and config.plugins.aafpanel.cronmanager_predefined_command.value != '':
			command = config.plugins.aafpanel.cronmanager_predefined_command.value
		else:
			command = config.plugins.aafpanel.cronmanager_user_command.value

		if config.plugins.aafpanel.cronmanager_runwhen.value == 'Hourly':
			newcron = minutes + ' ' + ' * * * * ' + command.strip() + '\n'
		elif config.plugins.aafpanel.cronmanager_runwhen.value == 'Daily':
			newcron = minutes + ' ' + hour + ' * * * ' + command.strip() + '\n'
		elif config.plugins.aafpanel.cronmanager_runwhen.value == 'Weekly':
			if config.plugins.aafpanel.cronmanager_dayofweek.value == 'Sunday':
				newcron = minutes + ' ' + hour + ' * * 0 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Monday':
				newcron = minutes + ' ' + hour + ' * * 1 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Tuesday':
				newcron = minutes + ' ' + hour + ' * * 2 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Wednesday':
				newcron = minutes + ' ' + hour + ' * * 3 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Thursday':
				newcron = minutes + ' ' + hour + ' * * 4 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Friday':
				newcron = minutes + ' ' + hour + ' * * 5 ' + command.strip() + '\n'
			elif config.plugins.aafpanel.cronmanager_dayofweek.value == 'Saturday':
				newcron = minutes + ' ' + hour + ' * * 6 ' + command.strip() + '\n'
		elif config.plugins.aafpanel.cronmanager_runwhen.value == 'Monthly':
			newcron = minutes + ' ' + hour + ' ' + str(config.plugins.aafpanel.cronmanager_dayofmonth.value) + ' * * ' + command.strip() + '\n'
		else:
			command = config.plugins.aafpanel.cronmanager_user_command.value

		out = open('/etc/cron/crontabs/root', 'a')
		out.write(newcron)
		out.close()
		rc = system('crontab /etc/cron/crontabs/root -c /etc/cron/crontabs')
		config.plugins.aafpanel.cronmanager_predefined_command.value = 'None'
		config.plugins.aafpanel.cronmanager_user_command.value = 'None'
		config.plugins.aafpanel.cronmanager_runwhen.value = 'Daily'
		config.plugins.aafpanel.cronmanager_dayofweek.value = 'Monday'
		config.plugins.aafpanel.cronmanager_dayofmonth.value = 1
		config.plugins.aafpanel.cronmanager_cmdtime.value, mytmpt = ([0, 0], [0, 0])
		self.close()

