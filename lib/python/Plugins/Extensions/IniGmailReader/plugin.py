from TagStrip import strip_readable
import email, re, os
from email.header import decode_header
from Screens.Screen import Screen
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap,NumberActionMap
from Components.About import about
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.ScrollLabel import ScrollLabel
from twisted.web.client import downloadPage,getPage
from Plugins.Plugin import PluginDescriptor
from Components.Button import Button
import urllib2
from urllib2 import URLError
from Screens.Standby import TryQuitMainloop
import urllib2
import feedparser
from enigma import eTimer,eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER , getDesktop, loadPNG , loadPic
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest

from Components.config import config, ConfigDirectory, ConfigSubsection, ConfigSubList, \
	ConfigEnableDisable, ConfigNumber, ConfigText, ConfigSelection, \
	ConfigYesNo, ConfigPassword, getConfigListEntry, configfile

config.plugins.gmail = ConfigSubsection()

config.plugins.gmail.username = ConfigText(default = 'username', visible_width = 50, fixed_size = False)
config.plugins.gmail.password = ConfigText(default = 'password', visible_width = 50, fixed_size = False)
labels=(["inbox","unread","all","read","starred","spam","sent","trash","draft"])
config.plugins.gmail.label = ConfigSelection(default = 'inbox',choices=(labels))
checkgmailtimes=(["disabled","2","5","10","30","60","120","240","480"])
config.plugins.gmail.checktimes = ConfigSelection(default = 'disabled',choices=(checkgmailtimes))
config.plugins.gmail.gmailcount = ConfigNumber(default = 0)

sliderfile="/usr/lib/enigma2/python/Plugins/Extensions/IniGmailReader/slider.png"
c7color=0xADFF2F
c2color=0xFFA500
c1color=0xFFFF00
c3color=0xEEE8AA
c5color=0xFF0000
c4color=0xFF4500
c6color=0x00FF7F
c8color=0xC71585
c9color=0xD2691E

pluginfolder="/usr/lib/enigma2/python/Plugins/Extensions/IniGmailReader/"

def wfile(st):
	fp=open("/tmp/lf.txt","w")
	fp.write(st)
	fp.close()

import imaplib
def gmaillogin():
	global mail
	mail = imaplib.IMAP4_SSL('imap.gmail.com')
	username=str(config.plugins.gmail.username.value)
	password=str(config.plugins.gmail.password.value)
	mail = imaplib.IMAP4_SSL('imap.gmail.com')
	mail.login(username+"@gmail.com", password)
	return mail

def getidlist():
	nidlist=[]
	try:
		mail=gmaillogin()
		mail.list()
		# Out: list of "folders" aka labels in gmail.
		tlabel=str(config.plugins.gmail.label.value)
		mail.select(tlabel) # connect to inbo
		result, data = mail.search(None, "UNSEEN")

		ids = data[0] # data is a list.
		id_list = ids.split() # ids is a space separated string

		idlist=[]
		for id in id_list[-20:]:
			idlist.append(id)

		nidlist= idlist[::-1]

		return nidlist
	except:
		return nidlist

def viewgmail(message_id):
	mail.list()
	# Out: list of "folders" aka labels in gmail.
	tlabel=str(config.plugins.gmail.label.value)
	mail.select(tlabel) # connect to inbo
	result, data = mail.search(None, "UNSEEN")
	result, data = mail.fetch(message_id, "(RFC822)") # fetch the email body (RFC822) for the given ID
	raw_email = data[0][1] # here's the body, which is raw text of the whole email
	wfile(str(message_id)+"\n"+raw_email)

	return raw_email

def get_unread_msgs(user, passwd,tlabel):
	try:
		auth_handler = urllib2.HTTPBasicAuthHandler()
		auth_handler.add_password(
			realm='New mail feed',
			uri='https://mail.google.com',
			user='%s@gmail.com' % user,
			passwd=passwd
		)
		opener = urllib2.build_opener(auth_handler)
		urllib2.install_opener(opener)
		url='https://mail.google.com/mail/feed/atom/'+tlabel
		feed = urllib2.urlopen(url)

		return feed.read()
	except:
		return "error"

def getgmail():
	list=[]
	try:
		user=config.plugins.gmail.username.value
		password=config.plugins.gmail.password.value
		tlabel=str(config.plugins.gmail.label.value)
		feedtext=get_unread_msgs(user,password,tlabel)
		if feedtext=="error":
			return list
		fileObj = open("feed.xml","w")
		fileObj.write(feedtext)
		fileObj.close()
		feed = feedparser.parse('feed.xml')

		for item in feed.entries:
			try:
				date=item.published
			except:
				date=""
			try:
				title=item.title
			except:
				title=""
			try:
				author=item.author
			except:
				author=""
			try:
				summary=item.summary
			except:
				summary=""

			list.append([date,title,author,summary])

		return list

	except:
		return list

class  Gmailfeedsscrn(Screen):
	skin = """
		<screen position="center,center" size="920,520" title="GMail Reader" >
		<widget name="menu" position="0,0" size="920,500" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
		<widget name="info" position="150,50" zPosition="4" size="620,300" font="Regular;24" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />
		</screen>"""

	def __init__(self, session, args = 0):
		self.session = session
		info="Please wait while getting email\nUse Setup to enter username and password"

		self["info"] = Label()
		self["info"].setText(info)
		self["key_red"] = Button(_("Setup"))
		self["key_green"] = Label()
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["menu"] = MenuList([], True, eListboxPythonMultiContent)
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["WizardActions","MenuActions", "DirectionActions", "ColorActions"],
		{
			"red": self.showsettings,
			"cancel": self.close,
			"back": self.close,
			"ok"    :self.gmailviewer,
		}, -1)
		self.onLayoutFinish.append(self.checkpass)
		self.onShow.append(self.UpdateTitle)

	def gmailviewer(self):
		tlabel=str(config.plugins.gmail.label.value)
		if not tlabel=="inbox" :
			self.session.open( MessageBox, _("You can only view messages from inbox. Use setup to change label to inbox."), MessageBox.TYPE_WARNING,10)
			return
		idlist=[]
		idlist=getidlist()
		if len(idlist)==0:
			self.session.open( MessageBox, _("Sorry! Unable to view email body, try again later."), MessageBox.TYPE_WARNING,10)
			return
		currentindex = self["menu"].getSelectedIndex()
		message_id=idlist[currentindex]
		body= viewgmail(message_id)

		tdate=str(self.gmails[currentindex][0])
		title= str(self.gmails[currentindex][1])
		author=str(self.gmails[currentindex][2])
		summary=str(self.gmails[currentindex][3])
		self.session.openWithCallback(self.refresh, Gmailbodyviewer, title, body, tdate, author)

	def UpdateTitle(self):
		pass

	def checkpass(self):
		if config.plugins.gmail.password.value=="" or config.plugins.gmail.username.value=="" :
			info="Use setup to enter username and password"
			self["info"].setText(info)
		else:
			self.refresh(True)

	def showsettings(self):
		self.session.openWithCallback(self.refresh,GmailSetup)

	def refresh(self,result):
		if result:
			thegmails=[]
			self["menu"].l.setList(thegmails)
			self["info"].setText("")
			self["menu"].show()
			info="Please wait while getting email\nUse Setup to enter username and password"
			self["info"].setText(info)
			self.timer = eTimer()
			self.timer.callback.append(self.ListToMulticontentgmails)
			self.timer.start(50, 1)

	def ListToMulticontentgmails(self):
		list=getgmail()

		if not list:
			self["info"].setText("error in gettings gmail,may be label search empty,check internet or check login data and selected label from settings(menu)")
			return
		res = []
		theevents = []
		self.gmails=list

		#set item height for menulist to 40
		self["menu"].l.setItemHeight(100)
		thegmails=[]
		#we set the font and size for each item in mylist
		self["menu"].l.setFont(0, gFont("Regular", 20))
		try:
			k=0
			png=sliderfile
			for item in self.gmails:
				date=str(item[0])
				title= str(item[1])
				author=str(item[2])
				summary=str(item[3])
				res = []
				res.append(MultiContentEntryText(pos=(0, 0), size=(2, 30), font=0, flags = RT_HALIGN_LEFT, text="", color=c1color, color_sel=c1color))
				res.append(MultiContentEntryText(pos=(10, 0), size=(230, 35), font=0, flags = RT_HALIGN_LEFT, text=date, color=c1color, color_sel=c1color))
				res.append(MultiContentEntryText(pos=(240, 0), size=(600, 35), font=0, flags = RT_HALIGN_LEFT, text=title, color=c2color, color_sel=c2color))
				res.append(MultiContentEntryText(pos=(10, 35), size=(650, 30), font=0, flags = RT_HALIGN_LEFT, text=author, color=c3color, color_sel=c3color))
				res.append(MultiContentEntryText(pos=(10, 65), size=(910, 55), font=0, flags = RT_HALIGN_LEFT, text=summary, color=c4color, color_sel=c4color))
				res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 95), size=(660, 5), png=loadPNG(png)))
				thegmails.append(res)
				res = []
		except:
				thegmails.append(res)
				res = []

		self["menu"].l.setList(thegmails)
		self["info"].setText("")
		self["menu"].show()

class GmailSetup(Screen, ConfigListScreen):
	skin = """<screen name="GmailSetup" position="center,center" size="640,520" title="settings" >
		<ePixmap name="red" position="195,10" zPosition="2" size="150,30" pixmap="skin_default/buttons/button_red.png" transparent="1" alphatest="on" />
		<ePixmap name="green" position="321,10" zPosition="2" size="150,30" pixmap="skin_default/buttons/button_green.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="182,17" size="150,45" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;20" transparent="1" shadowColor="#25062748" shadowOffset="-2,-2" />
		<widget name="key_green" position="312,17" size="150,45" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;18" transparent="1" shadowColor="#25062748" shadowOffset="-2,-2" />
		<widget name="config" position="15,150" size="610,320" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Label()
		self["key_blue"] = Button(_("Keyboard"))
		self.list = [ ]

		self.checktimestart=config.plugins.gmail.checktimes.value

		self.list.append(getConfigListEntry(_("Username:"), config.plugins.gmail.username))
		self.list.append(getConfigListEntry(_("Password:"), config.plugins.gmail.password))
		self.list.append(getConfigListEntry(_("Label:"), config.plugins.gmail.label))
		self.list.append(getConfigListEntry(_("New email check /minutes:"), config.plugins.gmail.checktimes))
		ConfigListScreen.__init__(self, self.list, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.keySave,
			"red": self.keyClose,
			"cancel": self.keyClose,
			"blue" : self.openKeyboard,
			"ok": self.keySave,
		}, -2)

	def openKeyboard(self):
		sel = self['config'].getCurrent()
		if sel:
			if sel[0]== _("Username:") or sel[0] == _("Password:"):
				if self["config"].getCurrent()[1].help_window.instance is not None:
					self["config"].getCurrent()[1].help_window.hide()
			self.vkvar = sel[0]
			if self.vkvar == _("Username:") or self.vkvar == _("Password:"):
				from Screens.VirtualKeyBoard import VirtualKeyBoard
				self.session.openWithCallback(self.VirtualKeyBoardCallback, VirtualKeyBoard, title = self["config"].getCurrent()[0], text = self["config"].getCurrent()[1].getValue())

	def VirtualKeyBoardCallback(self, callback = None):
		if callback is not None and len(callback):
			self["config"].getCurrent()[1].setValue(callback)
			self["config"].invalidate(self["config"].getCurrent())

	def restartenigma(self,result):
		if result:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close(True)

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		if config.plugins.gmail.checktimes.value==self.checktimestart:
			pass
		else:
			self.session.openWithCallback(self.restartenigma, MessageBox, _("Restart GUI to load new settings?"), MessageBox.TYPE_YESNO)
			return

		self.close(True)

	def keyClose(self):
		for x in self["config"].list:
			x[1].cancel()

		self.close(False)

	def keyClose(self):
		self.close(False)

def main(session, **kwargs):
	session.open(Gmailfeedsscrn)

def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
		PluginDescriptor(name="GMail Reader", description="GMail Reader", where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main),
		PluginDescriptor(name="GMail Reader", description="GMail Reader", where = PluginDescriptor.WHERE_PLUGINMENU, icon="gmail.png", fnc=main)]

class gmailnotifier(Screen):
	skin = """<screen name="gmailnotifier" position="40,150" size="200,100" title="New GMail"  flags="wfNoBorder" >
		<widget name="info" position="0,0" size="200,100" font="Regular;20" zPosition="2" transparent="1" valign="center" halign="center" />
		</screen>"""

	def __init__(self, session,msg=None):
		Screen.__init__(self, session)

		self.session=session
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.readgmail,
			"cancel": self.disappear,
		}, -1)
		self["info"]=Label(msg)
		self.timer = eTimer()
		self.timer.callback.append(self.disappear)
		self.timer.start(20000, True)

	def readgmail(self):
		self.session.openWithCallback(self.disappear,Gmailfeedsscrn)

	def disappear(self):
		self.close()

def stoploop():
	StayLoop.stopTimer()

def autostart(reason, **kwargs):
	try:
		if config.plugins.gmail.checktimes.value=="disabled":
			return
	except:
			pass

	global session
	if reason == 0 and kwargs.has_key("session"):
		session = kwargs["session"]
		session.open(DocompareTimes)

class DocompareTimes(Screen):
	skin = """<screen position="100,150" size="300,100" title="New GMail" >
		</screen>"""

	def __init__(self,session):
		Screen.__init__(self,session)

		self.session = session
		minutecount=str(config.plugins.gmail.checktimes.value)
		if minutecount=="disabled":
			return
		minutes=int(minutecount)
		mseconds=minutes* 60000
		self.minutecount=mseconds
		self.TimerPrayerTimes = eTimer()
		self.TimerPrayerTimes.stop()
		self.TimerPrayerTimes.timeout.get().append(self.Checkcounts)
		self.TimerPrayerTimes.start(self.minutecount,True)

	def repeat(self,result=None):
		self.TimerPrayerTimes = eTimer()
		self.TimerPrayerTimes.stop()
		self.TimerPrayerTimes.timeout.get().append(self.Checkcounts)
		self.TimerPrayerTimes.start(self.minutecount,True)

	def Checkcounts(self):
		netcount = comparecounts()
#		print "[GMail] netcount:", netcount
		if netcount>0:
			msg = "%d new email%s.\nPress OK to view." % (netcount, "s" if netcount > 1 else "")
#			print "[GMail]", msg
			self.session.openWithCallback(self.repeat, gmailnotifier, msg)
		else:
			self.repeat()

def getnewgmailcount():
	try:
		newEmail=""
		USERNAME=str(config.plugins.gmail.username.value)
		PASSWORD=str(config.plugins.gmail.password.value )
		tlabel=""
		feedtext=get_unread_msgs(USERNAME,PASSWORD,tlabel)
		if feedtext=="error":
			return 0

		gmailcount = int(feedparser.parse(feedtext)["feed"]["fullcount"])
		return gmailcount
	except:
		return 0

def comparecounts():
	netcount=0
	oldcount=config.plugins.gmail.gmailcount.value
#	print "[GMail] oldcount",oldcount
	newcount=getnewgmailcount()
#	print "[GMail] newcount",newcount
	netcount=newcount-oldcount
#	print "[GMail] netcount",netcount
	if newcount and newcount != oldcount:
		config.plugins.gmail.gmailcount.value=newcount
		config.plugins.gmail.gmailcount.save()
		configfile.save()
	return netcount

class Gmailbodyviewer(Screen):
	skin = """<screen name="Gmailbodyviewer" position="center,center" size="920,600" title="GMail Reader - View E-mail" >
			<widget name="title" position="20,0" zPosition="1" size="880,30" font="Regular;20" transparent="1"  backgroundColor="#00000000" foregroundColor="yellow" valign="center" halign="left" />
			<widget name="author" position="20,60" size="600,30" transparent="1" halign="left" font="Regular;20" foregroundColor="yellow"/>
			<widget name="tdate" position="620,60" size="300,30" transparent="1" halign="left" font="Regular;20" foregroundColor="yellow"/>
			<ePixmap position="15,88" size="890,12" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IniGmailReader/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>
			<widget name="text" position="20,100" size="880,400" font="Regular;22" />
			<ePixmap position="15,510" size="890,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/IniGmailReader/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>
		</screen>"""

	def __init__(self, session, title=None,body=None,tdate=None,author=None):
		self.gmailmsg= body

		self.session=session
		self.itemscount=10
		self["author"] = Label(_("From: ") + author)
		self["title"] = Label(_("Subject: ") + title)
		self["tdate"] = Label(_("Date: ") + tdate)
		self["key_red"] = Button(_("Close"))
		self["key_green"] = Label()
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["text"] = ScrollLabel("")

		txt=""
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["PiPSetupActions","WizardActions","ColorActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"up": self["text"].pageUp,
			"down": self["text"].pageDown
		}, -1)

		self.onLayoutFinish.append(self.updatetitle)
		self.timer = eTimer()
		self.timer.callback.append(self.getplainmessage)
		self.timer.start(100, 1)

	def updatetitle(self):
		txt="Fetching email body,please wait..."
		self["text"].setText(txt)
		self.setTitle("GMail Reader")

	def getemailinfo(self,msg):
		self._email = msg
		#header=decodeHeader(_("From") +": %s" %self._email.get('from', _('no from')))
		#msgdate = email.utils.parsedate_tz(self._email.get("date", ""))
		#self["date"] = Label(_("Date") +": %s" % (time.ctime(email.utils.mktime_tz(msgdate)) if msgdate else _("no date")))
		#subject = decodeHeader(_("Subject") +": %s" %self._email.get('subject', _('no subject')))
		body=self._email.messagebodys[0].getData()
		if not body.strip()=="":
			self["text"].setText(body)
		else:
			self["text"].setText("Sorry,unable to read email" )

	def getplainmessage(self):
		msg = email.Parser.Parser().parsestr(self.gmailmsg)
		msg.messagebodys = []
		msg.attachments = []

		if msg.is_multipart():
			for part in msg.walk():
				if part.get_content_maintype()=="multipart":
					continue
				if part.get_content_maintype() == 'text' and part.get_filename() is None:
					if part.get_content_subtype() == "html":
						msg.messagebodys.append(EmailBody(part))
					elif part.get_content_subtype() == "plain":
						msg.messagebodys.append(EmailBody(part))
					else:
						pass
						##debug("[EmailScreen] onMessageLoaded: unknown content type=%s/%s" %(str(part.get_content_maintype()), str(part.get_content_subtype())))
				else:
					pass
					#debug("[EmailScreen] onMessageLoaded: found Attachment with  %s and name %s" %(str(part.get_content_type()), str(part.get_filename())))
					#msg.attachments.append(EmailAttachment(part.get_filename(), part.get_content_type(), part.get_payload()))
		else:
			msg.messagebodys.append(EmailBody(msg))

		self.getemailinfo(msg)

	def exit(self):
		self.close(True)


class EmailBody:
	def __init__(self, data):
		self.data = data

	def getEncoding(self):
		return self.data.get_content_charset()

	def getData(self):
		text = self.data.get_payload(decode=True)
		if self.getEncoding():
			try:
				text = text.decode(self.getEncoding())
			except UnicodeDecodeError:
				pass
		# debug('EmailBody/getData text: ' +  text)
		#=======================================================================
		# if self.getEncoding():
		#	text = text.decode(self.getEncoding())
		#=======================================================================
		if self.getContenttype() == "text/html":
			#debug("[EmailBody] stripping html")
			text = strip_readable(text)
			# debug('EmailBody/getData text: ' +  text)

		try:
			return text.encode('utf-8')
		except UnicodeDecodeError:
			return text


	def getContenttype(self):
		return self.data.get_content_type()

def decodeHeader(text, default=''):
	if text is None:
		return _(default)
	text = text.replace('\r',' ').replace('\n',' ').replace('\t',' ')
	text = re.sub('\s\s+', ' ', text)
	textNew = ""
	for part in decode_header(text):
		(content, charset) = part
		# print("[GMail] decodeHeader content/charset: %s/%s" %(repr(content),charset))
		if charset:
			textNew += content.decode(charset)
		else:
			textNew += content
	try:
		return textNew.encode('utf-8')
	except UnicodeDecodeError: # for faulty mail software systems
		return textNew.decode('iso-8859-1').encode('utf-8')
