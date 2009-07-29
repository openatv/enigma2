from Plugins.Plugin import PluginDescriptor
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
import os
from twisted.mail import smtp, relaymanager

config.plugins.crashlogautosubmit = ConfigSubsection()
config.plugins.crashlogautosubmit.sendmail = ConfigSelection(default = "send", choices = [
	("send", _("Always ask before sending")), ("send_always", _("Don't ask, just send")), ("send_never", _("Disable crashlog reporting"))])
config.plugins.crashlogautosubmit.sendlog = ConfigSelection(default = "rename", choices = [
	("delete", _("Delete crashlogs")), ("rename", _("Rename crashlogs"))])


class CrashlogAutoSubmitConfiguration(Screen, ConfigListScreen):
	skin = """
		<screen name="CrashlogAutoSubmitConfiguration" position="80,80" size="560,400" title="CrashlogAutoSubmitConfiguration..." >
			<widget name="config" zPosition="2" position="5,5" size="550,360" scrollbarMode="showOnDemand" transparent="1" />
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,370" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="closetext" position="0,370" zPosition="10" size="140,40" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,370" zPosition="2" size="140,40" transparent="1" alphatest="on" />
			<widget name="installtext" position="140,370" zPosition="10" size="140,40" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.MailEntry = None
		self.LogEntry = None

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions" ],
		{
			"ok": self.keySave,
			"back": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -1)

		self.list = []
		ConfigListScreen.__init__(self, self.list,session = self.session)
		self.createSetup()

		self["closetext"] = Label(_("Close"))
		self["installtext"] = Label(_("Save"))
		self.onShown.append(self.setWindowTitle)

	def setWindowTitle(self):
		self.setTitle(_("CrashlogAutoSubmitConfiguration"))

	def exit(self):
		self.close(False, self.session)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def createSetup(self):
		self.list = []
		self.MailEntry = getConfigListEntry(_("How to handle found crashlogs:"), config.plugins.crashlogautosubmit.sendmail)
		self.LogEntry = getConfigListEntry(_("What to do with sent crashlogs:"), config.plugins.crashlogautosubmit.sendlog)
		self.list.append(self.MailEntry)
		if config.plugins.crashlogautosubmit.sendmail.value is not "send_never":
			self.list.append(self.LogEntry )
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.MailEntry:
			self.createSetup()

	def keyCancel(self):
		print "cancel"
		for x in self["config"].list:
			x[1].cancel()
		self.close(False, self.session)

	def keySave(self):
		print "saving"
		config.plugins.crashlogautosubmit.sendmail.save()
		config.plugins.crashlogautosubmit.sendlog.save()
		for x in self["config"].list:
			x[1].save()
		config.plugins.crashlogautosubmit.save()
		config.plugins.save()
		self.close(True, self.session)


def mxServerFound(mxServer,session):
	print "[CrashlogAutoSubmit] - mxServerFound -->", mxServer
	mailFrom = "enigma2@crashlog.dream-multimedia-tv.de"
	mailTo = "enigma2@crashlog.dream-multimedia-tv.de"
	subject = "Automatically generated crashlogmail"
	mailtext = "\nHello\n\nHere are some crashlogs i found for you.\n\n"
	mailfooter = "This is an automatically generated email.  You cant answer!!!"
	headers = { 'from': 'CrashlogAutoSubmitter <enigma2@crashlog.dream-multimedia-tv.de>', 'to': 'dream-multimedia-crashlogs <enigma2@crashlog.dream-multimedia-tv.de>', 'subject' : str(subject) }
	mailData = mailtext + mailfooter
	attachments = [] #(filename, mimetype, attachment as string)
	crashLogFilelist = []

	list = (
		(_("Yes"), "send"),
		(_("Yes, and don't ask again."), "send_always"),
		(_("No, send them never."), "send_never")
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
		attachments = []
		if len(crashLogFilelist):
			for crashlog in crashLogFilelist:
				filename = str(os.path.basename(crashlog))
				mimetype = "text/plain"
				f = open (crashlog, 'r')
				attachment = str(f.read())
				f.close()
				attachments.append ((filename,mimetype,attachment))
		sending = smtp.sendEmail(str(mxServer), mailFrom, mailTo, str(mailData), headers, attachments)
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

	for crashlog in os.listdir('/media/hdd'):
		if crashlog.startswith("enigma2_crash_") and crashlog.endswith(".log"):
			print "[CrashlogAutoSubmit] - found crashlog: ",os.path.basename(crashlog)
			crashLogFilelist.append('/media/hdd/' + crashlog)

	if len(crashLogFilelist):
		if config.plugins.crashlogautosubmit.sendmail.value == "send":
			session.openWithCallback(handleAnswer, ChoiceBox, title=_("Crashlogs found!\nSend them to Dream Multimedia ?"), list = list)
		elif config.plugins.crashlogautosubmit.sendmail.value == "send_always":
			send_mail()


def getMailExchange(host):
	print "[CrashlogAutoSubmit] - getMailExchange"

	def handleMXError(error):
		print "[CrashlogAutoSubmit] - DNS-Error, sending aborted -->", error.getErrorMessage()

	def cbMX(mxRecord):
		return str(mxRecord.name)

	return relaymanager.MXCalculator().getMX(host).addCallback(cbMX).addErrback(handleMXError)


def startMailer(session):
	if config.plugins.crashlogautosubmit.sendmail.value == "send_never":
		print "[CrashlogAutoSubmit] - not starting CrashlogAutoSubmit"
		return False

	getMailExchange('crashlog.dream-multimedia-tv.de').addCallback(mxServerFound,session)


def autostart(reason, **kwargs):
	print "[CrashlogAutoSubmit] - autostart"
	if "session" in kwargs:
		try:
			startMailer(kwargs["session"])
		except ImportError, e:
			print "[CrashlogAutoSubmit] Twisted-mail not available, not starting CrashlogAutoSubmitter", e

def openconfig(session, **kwargs):
	session.openWithCallback(configCB, CrashlogAutoSubmitConfiguration)

def configCB(result, session):
	if result is True:
		print "[CrashlogAutoSubmit] - config changed"
		startMailer(session)
	else:
		print "[CrashlogAutoSubmit] - config not changed"


def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
		PluginDescriptor(name=_("CrashlogAutoSubmit"), description=_("Configuration for the CrashlogAutoSubmitter"),
							where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=openconfig)]

