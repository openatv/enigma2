from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.MenuList import MenuList
from Components.config import getConfigListEntry, config, ConfigText
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.Pixmap import Pixmap,MultiPixmap
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from os import path,listdir, remove
from time import time, localtime

# Import smtplib for the actual sending function
import smtplib, base64

# Here are the email package modules we'll need
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.Utils import formatdate
from email import encoders

class LogManager(Screen):
	skin = """<screen name="LogManager" position="center,center" size="560,400" title="Log Manager" flags="wfBorder">
		<ePixmap pixmap="skin_default/buttons/key_menu.png" position="0,40" zPosition="4" size="35,25" alphatest="on" transparent="1" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="list" position="0,60" size="560,340" transparent="0" scrollbarMode="showOnDemand" />
		<applet type="onLayoutFinish">
			self["list"].instance.setItemHeight(25)
		</applet>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.logtype = 'crashlogs'
		self['myactions'] = ActionMap(['ColorActions', 'OkCancelActions', 'DirectionActions', "TimerEditActions", "MenuActions"],
			{
				'ok': self.showLog,
				'cancel': self.close,
				'red': self.changelogtype,
				'green': self.showLog,
				'yellow': self.deletelog,
				'blue': self.sendlog,
				'log': self.showLog,
				'menu': self.createSetup,
			}, -1)

		self["key_red"] = Button(_("Debug Logs"))
		self["key_green"] = Button(_("View"))
		self["key_yellow"] = Button(_("Delete"))
		self["key_blue"] = Button(_("Send"))
		self.emlist = []
		self.populate_List()
		self['list'] = MenuList(self.emlist)

	def createSetup(self):
		self.session.open(LogManagerMenu)

	def populate_List(self, answer = False):
		if self.logtype == 'crashlogs':
			self["key_red"].setText(_("Debug Logs"))
			self.loglist = listdir('/media/hdd/')
			del self.emlist[:]
			for fil in self.loglist:
				if fil.startswith('enigma2_crash'):
					self.emlist.append(fil)
		else:
			self["key_red"].setText(_("Crash Logs"))
			self.loglist = listdir(config.crash.debug_path.value)
			del self.emlist[:]
			for fil in self.loglist:
				if fil.startswith('Enigma2'):
					self.emlist.append(fil)
		self.emlist.sort()	

	def changelogtype(self):
		self["list"].instance.moveSelectionTo(0)
		if self.logtype == 'crashlogs':
			self.logtype = 'debuglogs'
		else:
			self.logtype = 'crashlogs'
		message = _("Please Wait..")
		ybox = self.session.openWithCallback(self.populate_List, MessageBox, message, MessageBox.TYPE_INFO, timeout = 2)
		ybox.setTitle(_("Finding files"))

	def showLog(self):
		self.sel = self['list'].getCurrent()
		self.session.open(LogManagerViewLog, self.sel, self.logtype)

	def deletelog(self):
		self.sel = self['list'].getCurrent()
		if self.sel:
			message = _("Are you sure you want to delete this log:\n ") + self.sel
			ybox = self.session.openWithCallback(self.doDelete, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Remove Confirmation"))
		else:
			self.session.open(MessageBox, _("You have no logs to delete."), MessageBox.TYPE_INFO, timeout = 10)

	def doDelete(self, answer):
		if answer is True:
			self.sel = self['list'].getCurrent()
			self["list"].instance.moveSelectionTo(0)
			if self.logtype == 'crashlogs':
				remove('/media/hdd/' + self.sel)
			else:
				remove(config.crash.debug_path.value + self.sel)
		self.populate_List()

	def sendlog(self):
		ref = str(time())
		self.sel = self['list'].getCurrent()
		self["list"].instance.moveSelectionTo(0)
		if self.logtype == 'crashlogs':
			fp = open('/media/hdd/' + self.sel, 'rb')
			data = MIMEText(fp.read())
			fp.close()
		else:
			fp = open(config.crash.debug_path.value + self.sel, 'rb')
			data= MIMEText(fp.read())
			fp.close()
			
		# Create the container (outer) email message.
		msg = MIMEMultipart()
		if config.vixsettings.user_command.value != " " and config.vixsettings.logmanageruseremail.value != ' ':
			fromlogman = config.vixsettings.user_command.value + '  <' + config.vixsettings.logmanageruseremail.value + '>'
		else:
			fromlogman = 'ViX Log Manager <vixlogs@world-of-satellite.com>'
		tovixlogs = 'vixlogs@world-of-satellite.com'
		msg['From'] = fromlogman
		msg['To'] = tovixlogs
		msg['Date'] = formatdate(localtime=True)
		msg['Subject'] = 'Ref: ' + ref
		msg.attach(MIMEText('please find attached my crash from', 'plain'))
		msg.attach(data)
		# Send the email via our own SMTP server.
		wos_user = 'vixlogs@world-of-satellite.com'
		wos_pwd = base64.b64decode('NDJJWnojMEpldUxX')
		s = smtplib.SMTP("mail.world-of-satellite.com",25)
		s.login(wos_user, wos_pwd)
		s.sendmail(fromuser, tovixlogs, msg.as_string())
		s.quit()
		self.session.open(MessageBox, _('Log ' + self.sel + ' has been sent to the ViX beta team.\nplease quote ' + ref + ' when asking question about this log'), MessageBox.TYPE_INFO)
		
	def myclose(self):
		self.close()
			

class LogManagerViewLog(Screen):
	skin = """
<screen name="LogManagerViewLog" position="center,center" size="700,400" title="Log Manager" >
	<widget name="list" position="0,0" size="700,400" font="Console;14" />
</screen>"""
	def __init__(self, session, selected, logtype):
		self.session = session
		Screen.__init__(self, session)
		self.skinName = "LogManagerViewLog"
		if logtype == 'crashlogs':
			selected = '/media/hdd/' + selected
		else:
			selected = config.crash.debug_path.value + selected
		if path.exists(selected):
			log = file(selected).read()
		else:
			log = ""
		self["list"] = ScrollLabel(str(log))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
		{
			"cancel": self.cancel,
			"ok": self.cancel,
			"up": self["list"].pageUp,
			"down": self["list"].pageDown,
			"right": self["list"].lastPage
		}, -2)

	def cancel(self):
		self.close()

config.vixsettings.logmanageruser = ConfigText(default=' ', fixed_size=False)
config.vixsettings.logmanageruseremail = ConfigText(default=' ', fixed_size=False)

class LogManagerMenu(ConfigListScreen, Screen):
	skin = """
		<screen name="LogManagerMenu" position="center,center" size="500,285" title="Log Manager Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,45" size="480,100" scrollbarMode="showOnDemand" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="440,400" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skin = LogManagerMenu.skin
		self.skinName = "LogManagerMenu"
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()
		
		self["actions"] = ActionMap(["SetupActions", 'ColorActions'],
		{
			"cancel": self.keyCancel,
			"save": self.keySaveNew,
			'yellow': self.vkeyb
		}, -2)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self['key_yellow'] = Label(_('KeyBoard'))

	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("User Name"), config.vixsettings.logmanageruser))
		self.list.append(getConfigListEntry(_("e-Mail address"), config.vixsettings.logmanageruseremail))
		self["config"].list = self.list
		self["config"].setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def keySaveNew(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def vkeyb(self):
		sel = self['config'].getCurrent()
		if sel:
			self.vkvar = sel[0]
			self.session.openWithCallback(self.UpdateAgain, VirtualKeyBoard, title=self.vkvar, text=config.vixsettings.logmanageruser.value)

	def UpdateAgain(self, text):
		self.list = []
		if text is None or text == '':
			text = ' '
		if self.vkvar == "User Name":
			config.vixsettings.logmanageruser.value = text
		elif self.vkvar == "e-Mail address":
			config.vixsettings.logmanageruseremail.value = text
		self.list = []
		self.list.append(getConfigListEntry(_("User Name"), config.vixsettings.logmanageruser))
		self.list.append(getConfigListEntry(_("e-Mail address"), config.vixsettings.logmanageruseremail))
		self["config"].list = self.list
		self["config"].setList(self.list)
		return None
