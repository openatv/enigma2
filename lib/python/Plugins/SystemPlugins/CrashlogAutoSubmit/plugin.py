from Plugins.Plugin import PluginDescriptor
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText, ConfigSelection, ConfigYesNo,ConfigText
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from enigma import ePoint
from Tools import Notifications

import os
from twisted.mail import smtp, relaymanager
import MimeWriter, mimetools, StringIO
from __init__ import bin2long, long2bin, rsa_pub1024, decrypt_block, validate_cert, read_random

config.plugins.crashlogautosubmit = ConfigSubsection()
config.plugins.crashlogautosubmit.sendmail = ConfigSelection(default = "send", choices = [
	("send", _("Always ask before sending")), ("send_always", _("Don't ask, just send")), ("send_never", _("Disable crashlog reporting"))])
config.plugins.crashlogautosubmit.sendlog = ConfigSelection(default = "rename", choices = [
	("delete", _("Delete crashlogs")), ("rename", _("Rename crashlogs"))])
config.plugins.crashlogautosubmit.attachemail = ConfigYesNo(default = False)
config.plugins.crashlogautosubmit.email = ConfigText(default = "myemail@home.com", fixed_size = False)
config.plugins.crashlogautosubmit.name = ConfigText(default = "Dreambox User", fixed_size = False)
config.plugins.crashlogautosubmit.sendAnonCrashlog = ConfigYesNo(default = True)
config.plugins.crashlogautosubmit.addNetwork = ConfigYesNo(default = False)
config.plugins.crashlogautosubmit.addWlan = ConfigYesNo(default = False)

class CrashlogAutoSubmitConfiguration(Screen, ConfigListScreen):

	oldMailEntryValue = config.plugins.crashlogautosubmit.sendmail.value

	skin = """
		<screen name="CrashlogAutoSubmitConfiguration" position="center,center" size="560,440" title="CrashlogAutoSubmit settings" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" zPosition="2" position="5,50" size="550,300" scrollbarMode="showOnDemand" transparent="1" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,390" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget source="status" render="Label" position="10,400" size="540,40" zPosition="10" font="Regular;20" halign="center" valign="center" backgroundColor="#25062748" transparent="1"/>
			<widget name="VKeyIcon" pixmap="skin_default/buttons/key_text.png" position="10,420" zPosition="10" size="35,25" transparent="1" alphatest="on" />
			<widget name="HelpWindow" pixmap="skin_default/vkey_icon.png" position="160,325" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.MailEntry = None
		self.LogEntry = None
		self.addEmailEntry = None
		self.EmailEntry = None
		self.NameEntry = None
		self.AnonCrashlogEntry = None
		self.NetworkEntry = None
		self.WlanEntry = None
		self.msgCrashlogMailer = False

		self["shortcuts"] = ActionMap(["ShortcutActions", "SetupActions" ],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)

		self["VirtualKB"] = ActionMap(["VirtualKeyboardActions" ],
		{
			"showVirtualKeyboard": self.KeyText,
		}, -1)

		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self.createSetup()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["status"] = StaticText()
		self["VKeyIcon"] = Pixmap()
		self["HelpWindow"] = Pixmap()

		self["VKeyIcon"].hide()
		self["VirtualKB"].setEnabled(False)
		self.onShown.append(self.setWindowTitle)
		self.onClose.append(self.msgCrashlogNotifier)


	def setWindowTitle(self):
		self.setTitle(_("CrashlogAutoSubmit settings..."))

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def KeyText(self):
			if self["config"].getCurrent() == self.EmailEntry:
				self.session.openWithCallback(self.EmailCallback, VirtualKeyBoard, title = (_("Please enter your email address here:")), text = config.plugins.crashlogautosubmit.email.value)
			if self["config"].getCurrent() == self.NameEntry:
				self.session.openWithCallback(self.NameCallback, VirtualKeyBoard, title = (_("Please enter your name here (optional):")), text = config.plugins.crashlogautosubmit.name.value)

	def EmailCallback(self, callback = None):
		if callback is not None and len(callback):
			config.plugins.crashlogautosubmit.email.setValue(callback)
			self["config"].invalidate(self.EmailEntry)

	def NameCallback(self, callback = None):
		if callback is not None and len(callback):
			config.plugins.crashlogautosubmit.name.setValue(callback)
			self["config"].invalidate(self.NameEntry)

	def createSetup(self):
		self.list = []
		self.MailEntry = getConfigListEntry(_("How to handle found crashlogs?"), config.plugins.crashlogautosubmit.sendmail)
		self.LogEntry = getConfigListEntry(_("What to do with submitted crashlogs?"), config.plugins.crashlogautosubmit.sendlog)
		self.addEmailEntry = getConfigListEntry(_("Include your email and name (optional) in the mail?"), config.plugins.crashlogautosubmit.attachemail)
		self.EmailEntry = getConfigListEntry(_("Your email address:"), config.plugins.crashlogautosubmit.email)
		self.NameEntry = getConfigListEntry(_("Your name (optional):"), config.plugins.crashlogautosubmit.name)
		self.AnonCrashlogEntry = getConfigListEntry(_("Anonymize crashlog?"), config.plugins.crashlogautosubmit.sendAnonCrashlog)
		self.NetworkEntry = getConfigListEntry(_("Add network configuration?"), config.plugins.crashlogautosubmit.addNetwork)
		self.WlanEntry = getConfigListEntry(_("Add WLAN configuration?"), config.plugins.crashlogautosubmit.addWlan)

		self.list.append( self.MailEntry )
		if config.plugins.crashlogautosubmit.sendmail.value is not "send_never":
			self.list.append( self.LogEntry )
			self.list.append( self.addEmailEntry )
			if config.plugins.crashlogautosubmit.attachemail.value is True:
				self.list.append( self.EmailEntry )
				self.list.append( self.NameEntry )
			self.list.append( self.AnonCrashlogEntry )
			self.list.append( self.NetworkEntry )
			self.list.append( self.WlanEntry )

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

		if not self.sendmailChanged in config.plugins.crashlogautosubmit.sendmail.notifiers:
			config.plugins.crashlogautosubmit.sendmail.notifiers.append(self.sendmailChanged)

	def sendmailChanged(self, configElement):
		if configElement.value != CrashlogAutoSubmitConfiguration.oldMailEntryValue:
			self.msgCrashlogMailer = True
		else:
			self.msgCrashlogMailer = False

	def newConfig(self):
		if self["config"].getCurrent() == self.MailEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.addEmailEntry:
			self.createSetup()

	def selectionChanged(self):
		current = self["config"].getCurrent()
		if current == self.MailEntry:
			self["status"].setText(_("Decide what should be done when crashlogs are found."))
			self.disableVKeyIcon()
		elif current == self.LogEntry:
			self["status"].setText(_("Decide what should happen to the crashlogs after submission."))
			self.disableVKeyIcon()
		elif current == self.addEmailEntry:
			self["status"].setText(_("Do you want to submit your email address and name so that we can contact you if needed?"))
			self.disableVKeyIcon()
		elif current == self.EmailEntry:
			self["status"].setText(_("Enter your email address so that we can contact you if needed."))
			self.enableVKeyIcon()
			self.showKeypad()
		elif current == self.NameEntry:
			self["status"].setText(_("Optionally enter your name if you want to."))
			self.enableVKeyIcon()
			self.showKeypad()
		elif current == self.AnonCrashlogEntry:
			self["status"].setText(_("Adds enigma2 settings and dreambox model informations like SN, rev... if enabled."))
			self.disableVKeyIcon()
		elif current == self.NetworkEntry:
			self["status"].setText(_("Adds network configuration if enabled."))
			self.disableVKeyIcon()
		elif current == self.WlanEntry:
			self["status"].setText(_("Adds wlan configuration if enabled."))
			self.disableVKeyIcon()

	def enableVKeyIcon(self):
		self["VKeyIcon"].show()
		self["VirtualKB"].setEnabled(True)

	def showKeypad(self):
		current = self["config"].getCurrent()
		helpwindowpos = self["HelpWindow"].getPosition()
		if hasattr(current[1], 'help_window'):
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.show()
				current[1].help_window.instance.move(ePoint(helpwindowpos[0],helpwindowpos[1]))

	def disableVKeyIcon(self):
		self["VKeyIcon"].hide()
		self["VirtualKB"].setEnabled(False)

	def hideKeypad(self):
		current = self["config"].getCurrent()
		if hasattr(current[1], 'help_window'):
			if current[1].help_window.instance is not None:
				current[1].help_window.instance.hide()

	def cancelConfirm(self, result):
		if not result:
			self.showKeypad()
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		print "cancel"
		if self["config"].isChanged():
			self.hideKeypad()
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def keySave(self):
		print "saving"
		CrashlogAutoSubmitConfiguration.oldMailEntryValue = config.plugins.crashlogautosubmit.sendmail.value
		ConfigListScreen.keySave(self)

	def msgCrashlogNotifier(self):
		if self.msgCrashlogMailer is True:
			try:
				callCrashMailer(True, self.session)
			except AttributeError:
				print "error, not restarting crashlogmailer"


def mxServerFound(mxServer,session):
	print "[CrashlogAutoSubmit] - mxServerFound -->", mxServer
	crashLogFilelist = []
	message = StringIO.StringIO()
	writer = MimeWriter.MimeWriter(message)
	mailFrom = "enigma2@crashlog.dream-multimedia-tv.de"
	mailTo = "enigma2@crashlog.dream-multimedia-tv.de"
	subject = "Automatically generated crashlogmail"
	# Define the main body headers.
	writer.addheader('To', "dream-multimedia-crashlogs <enigma2@crashlog.dream-multimedia-tv.de>")
	writer.addheader('From', "CrashlogAutoSubmitter <enigma2@crashlog.dream-multimedia-tv.de>")
	writer.addheader('Subject', str(subject))
	writer.addheader('Date', smtp.rfc822date())
	if config.plugins.crashlogautosubmit.attachemail.value is True:
		if  str(config.plugins.crashlogautosubmit.email.value) != "myemail@home.com":
			writer.addheader('Reply-To', str(str(config.plugins.crashlogautosubmit.email.value)))
	writer.addheader('MIME-Version', '1.0')
	writer.startmultipartbody('mixed')
	# start with a text/plain part
	part = writer.nextpart()
	body = part.startbody('text/plain')
	part.flushheaders()
	# Define the message body
	body_text1 = "\nHello\n\nHere are some crashlogs i found for you.\n"
	if  str(config.plugins.crashlogautosubmit.email.value) == "myemail@home.com":
		user_email = ""
	else:
		user_email = "\nUser supplied email address: " + str(config.plugins.crashlogautosubmit.email.value)
	if str(config.plugins.crashlogautosubmit.name.value) ==  "Dreambox User":
		user_name = ""
	else:
		user_name = "\n\nOptional supplied name: " + str(config.plugins.crashlogautosubmit.name.value)
	body_text2 = "\n\nThis is an automatically generated email from the CrashlogAutoSubmit plugin.\n\n\nHave a nice day.\n"
	body_text = body_text1 + user_email + user_name + body_text2
	body.write(body_text)

	list = (
		(_("Yes"), "send"),
		(_("Yes, and don't ask again"), "send_always"),
		(_("No, not now"), "send_not"),
		(_("No, send them never"), "send_never")
	)

	def handleError(error):
		print "[CrashlogAutoSubmit] - Message send Error -->", error.getErrorMessage()

	def handleSuccess(result):
		print "[CrashlogAutoSubmit] - Message sent successfully -->",result
		if len(crashLogFilelist):
			for crashlog in crashLogFilelist:
				if config.plugins.crashlogautosubmit.sendlog.value == "delete":
					os.remove(crashlog)
				elif config.plugins.crashlogautosubmit.sendlog.value == "rename":
					currfilename = str(os.path.basename(crashlog))
					newfilename = "/media/hdd/" + currfilename + ".sent"
					os.rename(crashlog,newfilename)

	def send_mail():
		print "[CrashlogAutoSubmit] - send_mail"
		if len(crashLogFilelist):
			for crashlog in crashLogFilelist:
				filename = str(os.path.basename(crashlog))
				subpart = writer.nextpart()
				subpart.addheader("Content-Transfer-Encoding", 'base64')
				subpart.addheader("Content-Disposition",'attachment; filename="%s"' % filename)
				subpart.addheader('Content-Description', 'Enigma2 crashlog')
				body = subpart.startbody("%s; name=%s" % ('application/octet-stream', filename))
				mimetools.encode(open(crashlog, 'rb'), body, 'base64')
		writer.lastpart()
		sending = smtp.sendmail(str(mxServer), mailFrom, mailTo, message.getvalue())
		sending.addCallback(handleSuccess).addErrback(handleError)

	def handleAnswer(answer):
		answer = answer and answer[1]
		print "[CrashlogAutoSubmit] - handleAnswer --> ",answer
		if answer == "send":
			send_mail()
		elif answer == "send_always":
			config.plugins.crashlogautosubmit.sendmail.value = "send_always"
			config.plugins.crashlogautosubmit.sendmail.save()
			config.plugins.crashlogautosubmit.save()
			config.plugins.save()
			config.save()
			send_mail()
		elif answer in ( None, "send_never"):
			config.plugins.crashlogautosubmit.sendmail.value = "send_never"
			config.plugins.crashlogautosubmit.sendmail.save()
			config.plugins.crashlogautosubmit.save()
			config.plugins.save()
			config.save()
		elif answer == "send_not":
			print "[CrashlogAutoSubmit] - not sending crashlogs for this time."

	for crashlog in os.listdir('/media/hdd'):
		if crashlog.startswith("enigma2_crash_") and crashlog.endswith(".log"):
			print "[CrashlogAutoSubmit] - found crashlog: ",os.path.basename(crashlog)
			crashLogFilelist.append('/media/hdd/' + crashlog)

	if len(crashLogFilelist):
		if config.plugins.crashlogautosubmit.sendmail.value == "send":
			Notifications.AddNotificationWithCallback(handleAnswer, ChoiceBox, title=_("Crashlogs found!\nSend them to Dream Multimedia?"), list = list)
		elif config.plugins.crashlogautosubmit.sendmail.value == "send_always":
			send_mail()
	else:
		print "[CrashlogAutoSubmit] - no crashlogs found."


def getMailExchange(host):
	print "[CrashlogAutoSubmit] - getMailExchange"
	return relaymanager.MXCalculator().getMX(host).addCallback(_gotMXRecord)

def _gotMXRecord(mxRecord):
	return str(mxRecord.name)


def startMailer(session):
	if config.plugins.crashlogautosubmit.sendmail.value == "send_never":
		print "[CrashlogAutoSubmit] - not starting CrashlogAutoSubmit"
		return False

	def gotMXServer(mxServer):
		print "[CrashlogAutoSubmit] gotMXServer: ",mxServer
		mxServerFound(mxServer,session)

	def handleMXError(error):
		print "[CrashlogAutoSubmit] - MX resolve ERROR:", error.getErrorMessage()

	if not config.misc.firstrun.value:
		getMailExchange('crashlog.dream-multimedia-tv.de').addCallback(gotMXServer).addErrback(handleMXError)


def callCrashMailer(result,session):
	if result is True:
		print "[CrashlogAutoSubmit] - config changed"
		startMailer(session)
	else:
		print "[CrashlogAutoSubmit] - config not changed"


def autostart(reason, **kwargs):
	print "[CrashlogAutoSubmit] - autostart"
	try:
		device = open("/proc/stb/info/model", "r").readline().strip()
	except:
		device = ""	
	if "session" in kwargs:
			try:
				startMailer(kwargs["session"])
			except ImportError, e:
				print "[CrashlogAutoSubmit] Twisted-mail not available, not starting CrashlogAutoSubmitter", e


def openconfig(session, **kwargs):
	session.open(CrashlogAutoSubmitConfiguration)


def selSetup(menuid, **kwargs):
	if menuid != "system":
		return [ ]

	return [(_("Crashlog settings"), openconfig, "crashlog_config", 70)]


def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], needsRestart = False, fnc = autostart),
		PluginDescriptor(name=_("CrashlogAutoSubmit"), description=_("CrashlogAutoSubmit settings"),where=PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=selSetup)]

