from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.FileList import FileList
from Components.Scanner import openFile
from Components.ScrollLabel import ScrollLabel
from Components.MenuList import MenuList
from Components.config import getConfigListEntry, config, ConfigText, ConfigYesNo, NoSave
from Components.ConfigList import ConfigListScreen, ConfigList
from Components.Pixmap import Pixmap,MultiPixmap
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.MessageBox import MessageBox
from os import path,listdir, remove
from os.path import isdir as os_path_isdir
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
		<ePixmap pixmap="skin_default/buttons/key_menu.png" position="0,35" zPosition="4" size="35,25" alphatest="on" transparent="1" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="list" position="0,70" size="560,325" transparent="0" scrollbarMode="showOnDemand" />
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
		if self.sel:
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
		message = _("Do you want to add any additional infomation ?")
		ybox = self.session.openWithCallback(self.sendlog2, MessageBox, message, MessageBox.TYPE_YESNO)
		ybox.setTitle(_("Addtional Info"))

	def sendlog2(self,answer):
		if answer:
			message = _("Do you want to attach a text file to explain the log ?")
			ybox = self.session.openWithCallback(self.sendlog3, MessageBox, message, MessageBox.TYPE_YESNO)
			ybox.setTitle(_("Attach a file"))
		else:
			self.doSendlog()

	def sendlog3(self,answer):
		if answer:
			self.session.openWithCallback(self.doSendlog, LogManagerFb)
		else:
			config.vixsettings.logmanager_additionalinfo.value = ""
			from Screens.VirtualKeyBoard import VirtualKeyBoard
			self.session.openWithCallback(self.doSendlog, VirtualKeyBoard, title = 'Additonal Info')

	def doSendlog(self, addtionalinfo = None):
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
		if config.vixsettings.logmanageruser.value != '' and config.vixsettings.logmanageruseremail.value != '':
			fromlogman = config.vixsettings.logmanageruser.value + '  <' + config.vixsettings.logmanageruseremail.value + '>'
		else:
			fromlogman = 'ViX Log Manager <vixlogs@world-of-satellite.com>'
		tovixlogs = 'vixlogs@world-of-satellite.com'
		msg['From'] = fromlogman
		msg['To'] = tovixlogs
		msg['Cc'] = fromlogman
		msg['Date'] = formatdate(localtime=True)
		msg['Subject'] = 'Ref: ' + ref
		if not config.vixsettings.logmanager_additionalinfo.value:
			msg.attach(MIMEText(addtionalinfo, 'plain'))
		else:
			msg.attach(MIMEText(config.vixsettings.logmanager_additionalinfo.value, 'plain'))
		msg.attach(data)
		# Send the email via our own SMTP server.
		wos_user = 'vixlogs@world-of-satellite.com'
		wos_pwd = base64.b64decode('NDJJWnojMEpldUxX')

		try:
			print "connecting to server: mail.world-of-satellite.com"
			#socket.setdefaulttimeout(30)
			s = smtplib.SMTP("mail.world-of-satellite.com",26)
			s.login(wos_user, wos_pwd)
			if config.vixsettings.logmanagerusersendcopy.value:
				s.sendmail(fromlogman, [tovixlogs, fromlogman], msg.as_string())
				s.quit()
				self.session.open(MessageBox, _('Log ' + self.sel + ' has been sent to the ViX beta team.\nplease quote ' + ref + ' when asking question about this log\n\nA copy has been sent to yourself.'), MessageBox.TYPE_INFO)
			else:
				s.sendmail(fromlogman, tovixlogs, msg.as_string())
				s.quit()
				self.session.open(MessageBox, _('Log ' + self.sel + ' has been sent to the ViX beta team.\nplease quote ' + ref + ' when asking question about this log'), MessageBox.TYPE_INFO)
		except Exception,e:
			self.session.open(MessageBox, _("Error:\n%s" % e), MessageBox.TYPE_INFO, timeout = 10)
		
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

config.vixsettings.logmanageruser = ConfigText(default='', fixed_size=False)
config.vixsettings.logmanageruseremail = ConfigText(default='', fixed_size=False)
config.vixsettings.logmanagerusersendcopy = ConfigYesNo(default = True)

class LogManagerMenu(ConfigListScreen, Screen):
	skin = """
		<screen name="LogManagerMenu" position="center,center" size="500,285" title="Log Manager Setup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,45" size="480,100" scrollbarMode="showOnDemand" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="440,400" zPosition="1" size="1,1" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/key_text.png" position="290,5" zPosition="4" size="35,25" alphatest="on" transparent="1" />
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
		
		self["actions"] = ActionMap(["SetupActions", 'ColorActions', 'VirtualKeyboardActions'],
		{
			"cancel": self.keyCancel,
			"save": self.keySave,
			'showVirtualKeyboard': self.KeyText
		}, -2)
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))

	def createSetup(self):
		self.editListEntry = None
		self.list = []
		self.list.append(getConfigListEntry(_("User Name"), config.vixsettings.logmanageruser))
		self.list.append(getConfigListEntry(_("e-Mail address"), config.vixsettings.logmanageruseremail))
		self.list.append(getConfigListEntry(_("Send yourself a copy ?"), config.vixsettings.logmanagerusersendcopy))
		self["config"].list = self.list
		self["config"].setList(self.list)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def KeyText(self):
		if self['config'].getCurrent():
			if self['config'].getCurrent()[0] == "User Name" or self['config'].getCurrent()[0] == "e-Mail address":
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()
	
	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

config.vixsettings.logmanager_savedirs = ConfigYesNo(default = True)
config.vixsettings.logmanager_path = ConfigText(default = "/")
config.vixsettings.logmanager_additionalinfo = NoSave(ConfigText(default = ""))

class LogManagerFb(Screen):
	skin = """
		<screen name="LogManagerFb" position="center,center" size="265,430" title="">
			<widget name="list" position="0,0" size="265,430" scrollbarMode="showOnDemand" />
		</screen>
		"""
	def __init__(self, session,path=None):
		if path is None:
			if os_path_isdir(config.vixsettings.logmanager_path.value) and config.vixsettings.logmanager_savedirs.value:
				path = config.vixsettings.logmanager_path.value
			else:
				path = "/"

		self.session = session
		Screen.__init__(self, session)
		self.skin = LogManagerFb.skin
		self.skinName = "LogManagerFb"

		self["list"] = FileList(path, matchingPattern = "^.*")
		self["red"] = Label(_("delete"))
		self["green"] = Label(_("move"))
		self["yellow"] = Label(_("copy"))
		self["blue"] = Label(_("rename"))


		self["actions"] = ActionMap(["ChannelSelectBaseActions","WizardActions", "DirectionActions","MenuActions","NumberActions","ColorActions"],
			{
			 "ok":	  self.ok,
			 "back":	self.exit,
			 "up": self.goUp,
			 "down": self.goDown,
			 "left": self.goLeft,
			 "right": self.goRight,
			 "0": self.doRefresh,
			 }, -1)
		self.onLayoutFinish.append(self.mainlist)

	def exit(self):
		config.vixsettings.logmanager_additionalinfo.value = ""
		if self["list"].getCurrentDirectory() and config.vixsettings.logmanager_savedirs.value:
			config.vixsettings.logmanager_path.value = self["list"].getCurrentDirectory()
			config.vixsettings.logmanager_path.save()
		self.close()

	def ok(self):
		if self.SOURCELIST.canDescent(): # isDir
			self.SOURCELIST.descent()
			if self.SOURCELIST.getCurrentDirectory(): #??? when is it none
				self.setTitle(self.SOURCELIST.getCurrentDirectory())
		else:
			self.onFileAction()

	def goLeft(self):
		self.SOURCELIST.pageUp()

	def goRight(self):
		self.SOURCELIST.pageDown()

	def goUp(self):
		self.SOURCELIST.up()

	def goDown(self):
		self.SOURCELIST.down()

	def doRefresh(self):
		self.SOURCELIST.refresh()

	def mainlist(self):
		self["list"].selectionEnabled(1)
		self.SOURCELIST = self["list"]
		self.setTitle(self.SOURCELIST.getCurrentDirectory())

	def onFileAction(self):
		config.vixsettings.logmanager_additionalinfo.value = data = file(self.SOURCELIST.getCurrentDirectory()+self.SOURCELIST.getFilename()).read()
		if self["list"].getCurrentDirectory() and config.vixsettings.logmanager_savedirs.value:
			config.vixsettings.logmanager_path.value = self["list"].getCurrentDirectory()
			config.vixsettings.logmanager_path.save()
		self.close()
