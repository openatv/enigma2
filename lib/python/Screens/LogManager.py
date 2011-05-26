from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.MenuList import MenuList
from Components.config import config
from Screens.MessageBox import MessageBox
from os import path,listdir, remove

import urllib

# Python interface to the Pastebin API
# More information here: http://pastebin.com/api.php
# Blog post: http://http://breakingcode.wordpress.com/2010/03/06/using-the-pastebin-api-with-python/
class Pastebin(object):

    # Valid Pastebin URLs begin with this string
    prefix_url = 'http://pastebin.com/'

    # Valid Pastebin URLs with a custom subdomain begin with this string
    subdomain_url = 'http://%s.pastebin.com/' # % paste_subdomain

    # URL to the POST API
    api_url = 'http://pastebin.com/api_public.php'
    #api_url = 'http://pastebin.com/api/api_post.php'

    # Valid paste_expire_date values
    paste_expire_date = ('N', '10M', '1H', '1D', '1M')

    # Valid parse_format values
    paste_format = (
        'abap', 'actionscript', 'actionscript3', 'ada', 'apache',
        'applescript', 'apt_sources', 'asm', 'asp', 'autoit', 'avisynth',
        'bash', 'basic4gl', 'bibtex', 'blitzbasic', 'bnf', 'boo', 'bf', 'c',
        'c_mac', 'cill', 'csharp', 'cpp', 'caddcl', 'cadlisp', 'cfdg',
        'klonec', 'klonecpp', 'cmake', 'cobol', 'cfm', 'css', 'd', 'dcs',
        'delphi', 'dff', 'div', 'dos', 'dot', 'eiffel', 'email', 'erlang',
        'fo', 'fortran', 'freebasic', 'gml', 'genero', 'gettext', 'groovy',
        'haskell', 'hq9plus', 'html4strict', 'idl', 'ini', 'inno', 'intercal',
        'io', 'java', 'java5', 'javascript', 'kixtart', 'latex', 'lsl2',
        'lisp', 'locobasic', 'lolcode', 'lotusformulas', 'lotusscript',
        'lscript', 'lua', 'm68k', 'make', 'matlab', 'matlab', 'mirc',
        'modula3', 'mpasm', 'mxml', 'mysql', 'text', 'nsis', 'oberon2', 'objc',
        'ocaml-brief', 'ocaml', 'glsl', 'oobas', 'oracle11', 'oracle8',
        'pascal', 'pawn', 'per', 'perl', 'php', 'php-brief', 'pic16',
        'pixelbender', 'plsql', 'povray', 'powershell', 'progress', 'prolog',
        'properties', 'providex', 'python', 'qbasic', 'rails', 'rebol', 'reg',
        'robots', 'ruby', 'gnuplot', 'sas', 'scala', 'scheme', 'scilab',
        'sdlbasic', 'smalltalk', 'smarty', 'sql', 'tsql', 'tcl', 'tcl',
        'teraterm', 'thinbasic', 'typoscript', 'unreal', 'vbnet', 'verilog',
        'vhdl', 'vim', 'visualprolog', 'vb', 'visualfoxpro', 'whitespace',
        'whois', 'winbatch', 'xml', 'xorg_conf', 'xpp', 'z80'
    )

    # Submit a code snippet to Pastebin
    @classmethod
    def submit(cls, paste_code,
                paste_name = None, paste_subdomain = None,
                paste_private = None, paste_expire_date = None,
                paste_format = None, dev_key = None,
                user_name = None, user_password = None):

        # Code snippet to submit
        argv = { 'paste_code' : str(paste_code) }

        # Name of the poster
        if paste_name is not None:
            argv['paste_name'] = str(paste_name)

	# Developer Key
        if dev_key is not None:
            argv['dev_key'] = str(dev_key)

	# User Name
        if user_name is not None:
            argv['user_name'] = str(user_name)

	# User Password
        if user_password is not None:
            argv['user_password'] = str(user_password)

        # Custom subdomain
        if paste_subdomain is not None:
            paste_subdomain = str(paste_subdomain).strip().lower()
            argv['paste_subdomain'] = paste_subdomain

        # Is the snippet private?
        if paste_private is not None:
            argv['paste_private'] = int(bool(int(paste_private)))

        # Expiration for the snippet
        if paste_expire_date is not None:
            paste_expire_date = str(paste_expire_date).strip().upper()
            if not paste_expire_date in cls.paste_expire_date:
                raise ValueError, "Bad expire date: %s" % paste_expire_date

        # Syntax highlighting
        if paste_format is not None:
            paste_format = str(paste_format).strip().lower()
            if not paste_format in cls.paste_format:
                raise ValueError, "Bad format: %s" % paste_format
            argv['paste_format'] = paste_format

        # Make the request to the Pastebin API
        fd = urllib.urlopen(cls.api_url, urllib.urlencode(argv))
        try:
            response = fd.read()
        finally:
            fd.close()
        del fd

        # Return the new snippet URL on success, raise exception on error
        if argv.has_key('paste_subdomain'):
            prefix = cls.subdomain_url % paste_subdomain
        else:
            prefix = cls.prefix_url
        if not response.startswith(prefix):
            raise RuntimeError, response
        return response

class LogManager(Screen):
	skin = """<screen name="LogManager" position="center,center" size="560,400" title="Log Manager" flags="wfBorder">
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
		self["title"] = Label(_("Log Manager"))
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
		self.session.open(CrashlogAutoSubmitConfiguration)

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
		self.sel = self['list'].getCurrent()
		self["list"].instance.moveSelectionTo(0)
		if self.logtype == 'crashlogs':
			data = open('/media/hdd/' + self.sel, 'rb').read()
		else:
			data = open(config.crash.debug_path.value + self.sel, 'rb').read()
			
		url = Pastebin.submit(paste_code = data, paste_name = 'ViX-Image', dev_key = '99332e2f3765ed8610e3ec3fbea90791', user_name = 'andyblac', user_password = 'x6cAsDdn')
		self.session.open(MessageBox, _("This is the part you need to post. \n") + url, MessageBox.TYPE_INFO)

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

