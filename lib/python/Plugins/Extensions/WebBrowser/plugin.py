from Plugins.Plugin import PluginDescriptor

import time, os, socket, thread, socket, copy
from socket import gaierror, error
from os import path as os_path, remove as os_remove

import gdata.youtube
import gdata.youtube.service
from gdata.service import BadAuthentication

from twisted.web import client
from twisted.internet import reactor

from urlparse import parse_qs
from urllib import quote, unquote_plus, unquote
from urllib2 import Request, URLError, urlopen as urlopen2
from httplib import HTTPConnection, CannotSendRequest, BadStatusLine, HTTPException

from Components.Button import Button
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Language import language
from Components.Sources.List import List
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config, ConfigSelection, getConfigListEntry, ConfigSlider

from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.DefaultWizard import DefaultWizard
from Screens.InfoBarGenerics import InfoBarNotifications

from enigma import eTimer, eServiceReference, iPlayableService, fbClass, eRCInput, eConsoleAppContainer

HTTPConnection.debuglevel = 1

def excute_cmd(cmd):
	print "prepared cmd:", cmd
	os.system(cmd)

alpha_value = 0
def change_galpha(set_const, set_value):
	op  = "/proc/stb/fb/alpha_op"
	val = "/proc/stb/fb/alpha_value"
	global alpha_value
	if os.path.exists(op) and set_const and alpha_value < 255:
		excute_cmd("echo \"const\" > %s" % (op))
	else:
		excute_cmd("echo \"copypsrc\" > %s" % (op))

	if os.path.exists(val) and set_value:
		excute_cmd("echo \"%s\" > %s" % (str(hex(alpha_value)), val))

def enable_rc_mouse(mode): #mode=[0|1]|[False|True]
	mouse_cond = "/proc/stb/fp/mouse"
	if os.path.exists(mouse_cond):
		excute_cmd("echo %d > %s" % (mode, mouse_cond))

def is_process_running(pname):
	if pname is None or len(pname) == 0:
		return False

	cmd = "/bin/ps -ef | grep %s | grep -v grep | awk \'{print $5}\'"%(pname)
	for line in os.popen(cmd).readlines():
		return True
	return False

lock = False
def wb_lock(alpha_on=True):
	global lock
	lock = True
	if alpha_on:
		change_galpha(set_const=False, set_value=False)
	fbClass.getInstance().unlock()

def wb_unlock(alpha_on=True):
	global lock
	if alpha_on:
		change_galpha(set_const=True, set_value=False)
	fbClass.getInstance().lock()
	lock = False

def wb_islock():
	global lock
	return lock

class Player(Screen, InfoBarNotifications):
	skin = 	"""
		<screen name="Player" flags="wfNoBorder" position="center,620" size="455,53" title="Webbrowser" backgroundColor="transparent">
			<ePixmap pixmap="skin_default/mp_wb_background.png" position="0,0" zPosition="-1" size="455,53" />
			<ePixmap pixmap="skin_default/icons/mp_wb_buttons.png" position="40,23" size="30,13" alphatest="on" />

			<widget source="session.CurrentService" render="PositionGauge" position="80,25" size="220,10" zPosition="2" pointer="skin_default/position_pointer.png:540,0" transparent="1" foregroundColor="#20224f">
				<convert type="ServicePosition">Gauge</convert>
			</widget>
			
			<widget source="session.CurrentService" render="Label" position="310,20" size="50,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" >
				<convert type="ServicePosition">Position</convert>
			</widget>
			<widget name="sidebar" position="362,20" size="10,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" />
			<widget source="session.CurrentService" render="Label" position="374,20" size="50,20" font="Regular;18" halign="center" valign="center" backgroundColor="#4e5a74" transparent="1" > 
				<convert type="ServicePosition">Length</convert>
			</widget>
		</screen>
		"""
	PLAYER_IDLE	= 0
	PLAYER_PLAYING 	= 1
	PLAYER_PAUSED 	= 2

	def __init__(self, session, service, lastservice):
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)

		self.session     = session
		self.service     = service
		self.lastservice = lastservice
		self["actions"] = ActionMap(["OkCancelActions", "InfobarSeekActions", "MediaPlayerActions", "MovieSelectionActions"],
		{
			"ok": self.doInfoAction,
			"cancel": self.doExit,
			"stop": self.doExit,
			"playpauseService": self.playpauseService,
		}, -2)
		self["sidebar"] = Label(_("/"))

		self.__event_tracker = ServiceEventTracker(screen = self, eventmap =
		{
			iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evEOF: self.__evEOF,
		})

		self.hidetimer = eTimer()
		self.hidetimer.timeout.get().append(self.doInfoAction)

		self.state = self.PLAYER_PLAYING
		self.lastseekstate = self.PLAYER_PLAYING
		self.__seekableStatusChanged()
	
		self.onClose.append(self.__onClose)
		self.doPlay()

	def __onClose(self):
		self.session.nav.stopService()

	def __seekableStatusChanged(self):
		service = self.session.nav.getCurrentService()
		if service is not None:
			seek = service.seek()
			if seek is None or not seek.isCurrentlySeekable():
				self.setSeekState(self.PLAYER_PLAYING)

	def __serviceStarted(self):
		self.state = self.PLAYER_PLAYING
		self.__seekableStatusChanged()

	def __evEOF(self):
		self.doExit()

	def __setHideTimer(self):
		self.hidetimer.start(5000)

	def doExit(self):
		list = ((_("Yes"), "y"), (_("No, but play video again"), "n"),)
		self.session.openWithCallback(self.cbDoExit, ChoiceBox, title=_("Stop playing this movie?"), list = list)

	def cbDoExit(self, answer):
		answer = answer and answer[1]
		if answer == "y":
			wb_unlock()
			self.close()
		elif answer == "n":
			if self.state != self.PLAYER_IDLE:
				self.session.nav.stopService()
				self.state = self.PLAYER_IDLE
			self.doPlay()

	def setSeekState(self, wantstate):
		service = self.session.nav.getCurrentService()
		if service is None:
			print "No Service found"
			return

		pauseable = service.pause()
		if pauseable is not None:
			if wantstate == self.PLAYER_PAUSED:
				pauseable.pause()
				self.state = self.PLAYER_PAUSED
				if not self.shown:
					self.hidetimer.stop()
					self.show()
			elif wantstate == self.PLAYER_PLAYING:
				pauseable.unpause()
				self.state = self.PLAYER_PLAYING
				if self.shown:
					self.__setHideTimer()
		else:
			self.state = self.PLAYER_PLAYING

	def doInfoAction(self):
		if self.shown:
			self.hide()
			self.hidetimer.stop()
		else:
			self.show()
			if self.state == self.PLAYER_PLAYING:
				self.__setHideTimer()

	def doPlay(self):
		if self.state == self.PLAYER_PAUSED:
			if self.shown:
				self.__setHideTimer()	
		self.state = self.PLAYER_PLAYING
		self.session.nav.playService(self.service)
		if self.shown:
			self.__setHideTimer()

	def playpauseService(self):
		if self.state == self.PLAYER_PLAYING:
			self.setSeekState(self.PLAYER_PAUSED)
		elif self.state == self.PLAYER_PAUSED:
			self.setSeekState(self.PLAYER_PLAYING)

VIDEO_FMT_PRIORITY_MAP = {
	'38' : 1, #MP4 Original (HD)
	'37' : 2, #MP4 1080p (HD)
	'22' : 3, #MP4 720p (HD)
	'18' : 4, #MP4 360p
	'35' : 5, #FLV 480p
	'34' : 6, #FLV 360p
}
std_headers = {
	'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.6) Gecko/20100627 Firefox/3.6.6',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
	'Accept-Language': 'en-us,en;q=0.5',
}

class PlayerLauncher:
	def getVideoUrl(self, video_id):
		video_url = None

		if video_id is None or video_id == "":
			return video_url

		# Getting video webpage
		watch_url = 'http://www.youtube.com/watch?v=%s&gl=US&hl=en' % video_id
		watchrequest = Request(watch_url, None, std_headers)
		try:
			#print "trying to find out if a HD Stream is available",watch_url
			watchvideopage = urlopen2(watchrequest).read()
		except (URLError, HTTPException, socket.error), err:
			print "Error: Unable to retrieve watchpage - Error code: ", str(err)
			return video_url

		# Get video info
		for el in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
			info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en' % (video_id, el))
			request = Request(info_url, None, std_headers)
			try:
				infopage = urlopen2(request).read()
				videoinfo = parse_qs(infopage)
				if ('url_encoded_fmt_stream_map' or 'fmt_url_map') in videoinfo:
					break
			except (URLError, HTTPException, socket.error), err:
				print "Error: unable to download video infopage",str(err)
				return video_url

		if ('url_encoded_fmt_stream_map' or 'fmt_url_map') not in videoinfo:
			if 'reason' not in videoinfo:
				print 'Error: unable to extract "fmt_url_map" or "url_encoded_fmt_stream_map" parameter for unknown reason'
			else:
				reason = unquote_plus(videoinfo['reason'][0])
				print 'Error: YouTube said: %s' % reason.decode('utf-8')
			return video_url

		video_fmt_map = {}
		fmt_infomap = {}
		if videoinfo.has_key('url_encoded_fmt_stream_map'):
			tmp_fmtUrlDATA = videoinfo['url_encoded_fmt_stream_map'][0].split(',url=')
		else:
			tmp_fmtUrlDATA = videoinfo['fmt_url_map'][0].split(',')
		for fmtstring in tmp_fmtUrlDATA:
			if videoinfo.has_key('url_encoded_fmt_stream_map'):
				(fmturl, fmtid) = fmtstring.split('&itag=')
				if fmturl.find("url=") !=-1:
					fmturl = fmturl.replace("url=","")
			else:
				(fmtid,fmturl) = fmtstring.split('|')
			if VIDEO_FMT_PRIORITY_MAP.has_key(fmtid):
				video_fmt_map[VIDEO_FMT_PRIORITY_MAP[fmtid]] = { 'fmtid': fmtid, 'fmturl': unquote_plus(fmturl) }
			fmt_infomap[int(fmtid)] = unquote_plus(fmturl)
		print "got",sorted(fmt_infomap.iterkeys())
		if video_fmt_map and len(video_fmt_map):
			video_url = video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]['fmturl'].split(';')[0]
			#print "found best available video format:",video_fmt_map[sorted(video_fmt_map.iterkeys())[0]]['fmtid']
			#print "found best available video url:",video_url
		return video_url

	def run(self, tubeid, session, service):
		try:
			myurl = self.getVideoUrl(tubeid)
			print "Playing URL", myurl
			if myurl is None:
				session.open(MessageBox, _("Sorry, video is not available!"), MessageBox.TYPE_INFO)
				return
			myreference = eServiceReference(4097, 0, myurl)
			session.open(Player, myreference, service)
		except Exception, msg:
			wb_unlock()
			print "Error >>", msg

class PlayerService:
	def __init__(self, session):
		self.enable = False
		self.socket_timeout = 0
		self.max_buffer_size = 1024
		self.uds_file = "/tmp/player.tmp"
		self.session = session
		try:
			os.remove(self.uds_file)
		except OSError:
			pass
	
	def start(self, timeout = 1):
		self.socket_timeout = timeout
		thread.start_new_thread(self.run, (True,))

	def stop(self):
		self.enable = False

	def isRunning(self):
		return self.enable

	def run(self, e = True):
		if self.enable:
			return
		print "PlayerService start!!"
		self.enable = e
		self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.sock.settimeout(self.socket_timeout)
		self.sock.bind(self.uds_file)
		self.sock.listen(1)
		while(self.enable):
			try:
				conn, addr = self.sock.accept()
				self.parseHandle(conn, addr)
			except socket.timeout:
				#print "[socket timeout]"
				pass
		print "PlayerService stop!!"

	def parseHandle(self, conn, addr):
		# [http://www.youtube.com/watch?v=BpThu778qB4&feature=related]
		data = conn.recv(self.max_buffer_size)
		print "[%s]" % (data)
		enable_rc_mouse(False)
		if data.startswith("http://www.youtube.com"):
			print "youtube start!!"
			tmp = data.split("?")
			print tmp # ['http://www.youtube.com/watch', 'v=BpThu778qB4&feature=related']
			service = self.session.nav.getCurrentlyPlayingServiceReference()
			if len(tmp) == 2 and tmp[0] == "http://www.youtube.com/watch":
				tmp = tmp[1].split("&")
				print tmp # ['v=BpThu778qB4', 'feature=related']
				if len(tmp) == 2:
					tmp = tmp[0].split("=")
					print tmp # ['v', 'BpThu778qB4']
					if len(tmp) == 2 and tmp[0] == "v":
						wb_lock()
						player = PlayerLauncher()
						player.run(tmp[1], self.session, service)
						while wb_islock():
							time.sleep(1)
						self.session.nav.playService(service)
						data = "ok$"
					else:
						data = "nok$parsing fail"
				else:
					data = "nok$parsing fail"
			else:
				data = "nok$parsing fail"
			self.sendResponse(conn, data)
		elif data.startswith("vk://open"):
			print "virtual keyboard start!!"
			from Screens.VirtualKeyBoard import VirtualKeyBoard
			wb_lock()
			self.vk_conn = conn
			self.session.openWithCallback(self.cbOpenKeyboard, VirtualKeyBoard, title = (_("Enter your input data")), text = "")

        def cbOpenKeyboard(self, data = None):
		print "virtual keyboard callback!!"
		wb_unlock()
		self.sendResponse(self.vk_conn, data)
		
	def sendResponse(self, conn, data):
		if data is None or len(data) == 0:
			data = ""
		enable_rc_mouse(True)
		conn.send(data)
		conn.close()

class BrowserLauncher(ConfigListScreen, Screen):
	skin=   """
		<screen name="BrowserLauncher" position="center,center" size="315,500" title="Web Browser">
			<ePixmap pixmap="skin_default/buttons/red.png" position="15,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="15,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" transparent="1" />
			<widget name="config" position="0,50" size="309,100" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/rc_wb_desc.png" position="0,150" size="309,296" alphatest="on" />
			<widget name="info" position="0,455" size="309,50" font="Regular;18" halign="center" foregroundColor="blue" transparent="1" />
		</screen>
		"""

	def __init__(self, session): 
		Screen.__init__(self, session)
                self.session = session
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self.browser_root = "/usr/bin"
		self.browser_name = "arora"
		self.conf_file = "/usr/lib/enigma2/python/Plugins/Extensions/WebBrowser/settings.conf"
		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", ],
                {	"red": self.keyCancel,
			"green": self.keyGo,
			"cancel": self.keyExit,
                }, -2)
		self.info = Label(_("If you want to quit the Browser,\nPress RED -> EXIT."))
		self["info"] = self.info
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Start"))

		self.conf_alpha = ""
		self.conf_mouse = ""
		self.conf_keyboard = ""
		self.conf_keymap = ""

		self.usb_mouse = None
		self.usb_keyboard = None
		self.rc_mouse = None
		self.rc_keyboard = None

		self.makeConfig()
		#time.sleep(2)

		self.lock = False
		self.service = PlayerService(self.session)
		self.service.start(timeout=5)

		self.exit_wait_cond = False
		self.timer_exit_cond = eTimer()
		self.timer_exit_cond.callback.append(self.resetExitCond)

		self.test_cond = True
		self.current_lang_idx = language.getActiveLanguageIndex()

	def keyNone(self):
		None

	def doExit(self):
		change_galpha(set_const=False, set_value=False)
		self.saveConfig()
		self.service.stop()
		excute_cmd("killall -15 %s"%(self.browser_name))
		excute_cmd("echo 60 > /proc/sys/vm/swappiness")
		enable_rc_mouse(False) #rc-mouse off
		language.activateLanguageIndex(self.current_lang_idx)
		fbClass.getInstance().unlock()
		#eRCInput.getInstance().unlock()
		self.close()

	def keyExit(self):
		if self.exit_wait_cond:
			self.doExit()
		if is_process_running(self.browser_name) == False:
			self.doExit()

	def keyLeft(self):
		if is_process_running(self.browser_name) == False:
			ConfigListScreen.keyLeft(self)
			global alpha_value
			alpha_value = self.alpha.value
			#self.saveConfig()

	def keyRight(self):
		if is_process_running(self.browser_name) == False:
			ConfigListScreen.keyRight(self)
			alpha_value = self.alpha.value
			#self.saveConfig()

	def keyCancel(self):
		if is_process_running(self.browser_name) == False:
			self.doExit()
		self.exit_wait_cond = True
		self.timer_exit_cond.start(5000)

	# mouse:keyboard:alpha_value
	def saveConfig(self):
		if is_process_running(self.browser_name) == False:
			command = "echo \"%s:%s:%d:%s\" > %s"%(self.mouse.value, self.keyboard.value, int(self.alpha.value), self.langs.value, self.conf_file)
			excute_cmd(command)

	# mouse:keyboard:alpha_value
	def loadConfig(self):
		if os.path.exists(self.conf_file) == False:
			return
		config_list = open(self.conf_file).readline().strip().split(':')
		if len(config_list) == 3:
			self.conf_mouse 	= config_list[0]
			self.conf_keyboard 	= config_list[1]
			self.conf_alpha 	= config_list[2]
		elif len(config_list) == 4:
			self.conf_mouse 	= config_list[0]
			self.conf_keyboard 	= config_list[1]
			self.conf_alpha 	= config_list[2]
			self.conf_keymap 	= config_list[3]
		print "load config : ", config_list

	def resetExitCond(self):
		self.timer_exit_cond.stop()
		self.exit_wait_cond = False

	def makeConfig(self):
		self.loadConfig()
		self.devices_string = ""
		self.devices = eConsoleAppContainer()
		self.devices.dataAvail.append(self.callbackDevicesDataAvail)
		self.devices.appClosed.append(self.callbakcDevicesAppClose)
		self.devices.execute(_("cat /proc/bus/input/devices"))

	def callbackDevicesDataAvail(self, ret_data):
		self.devices_string = self.devices_string + ret_data

	def callbakcDevicesAppClose(self, retval):
		self.name_list  = []
		self.mouse_list = None
		self.keyboard_list = None
		
		self.makeHandlerList(self.devices_string)

		if self.conf_mouse == "" or self.getHandlerName(self.conf_mouse) is None:
			self.conf_mouse = self.mouse_list[0][0]
		self.mouse = ConfigSelection(default = self.conf_mouse, choices = self.mouse_list)
		self.list.append(getConfigListEntry(_('Mouse'), self.mouse))		

		if self.conf_keyboard == "" or self.getHandlerName(self.conf_keyboard) is None:
			self.conf_keyboard = self.keyboard_list[0][0]
		self.keyboard = ConfigSelection(default = self.conf_keyboard, choices = self.keyboard_list)
		self.list.append(getConfigListEntry(_('Keyboard'), self.keyboard))

		if self.conf_alpha == "":
			self.conf_alpha = "255"
		self.alpha = ConfigSlider(default = int(self.conf_alpha), increment = 10, limits = (0, 255))
		self.list.append(getConfigListEntry(_("Alpha Value"), self.alpha))

		if self.conf_keymap == "":
			self.conf_keymap = self.getLanguage()
		self.lang_list = [("en", "English"), ("de", "German")]
		self.langs = ConfigSelection(default = self.conf_keymap, choices = self.lang_list)
		self.list.append(getConfigListEntry(_("Language"), self.langs))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def getLanguage(self, lang=language.getLanguage()):
		if self.current_lang_idx == 1:
			return "de"
		return "en"

	def makeHandlerList(self, data):
		n = ""
		p = ""
		h_list = []

		event_list = []
		lines = data.split('\n')
		for line in lines:
			print ">>", line
			if line is not None and len(line) > 0:
				if line[0] == 'I':
					n = ""
					p = ""
					h_list = []
				elif line[0] == 'N':
					n = line[8:].strip()
				elif line[0] == 'P':
					p = line[8:].strip()
				elif line[0] == 'H':
					h_list = line[12:].strip().split()
					tn = line[12:].strip().find("mouse")
					for h in h_list:
						event_list.append((h, _(h)))
						self.name_list.append((h, n))
						if n[1:].startswith("dream") and self.rc_mouse is None:
							self.rc_mouse = copy.deepcopy(h)
							self.rc_keyboard = copy.deepcopy(h)
							print "detected!! rc"
							continue
						if h.startswith("mouse") and self.usb_mouse is None:
							self.usb_mouse = copy.deepcopy(h)
							print "detected!! usb mouse"
							continue
						if tn == -1 and self.usb_keyboard is None:
							self.usb_keyboard = copy.deepcopy(h)
							print "detected!! usb keyboard"
				elif line[0] == 'B' and line[3:].startswith("ABS") and p.startswith("usb-"):
					for h in h_list:
						if self.usb_mouse is not None:
							break
						if self.usb_keyboard is not None and h == self.usb_keyboard[0]:
							self.usb_keyboard = None
							print "clean!! usb keyboard"
						self.usb_mouse = copy.deepcopy(h)
						print "detected!! usb mouse"

		tmp = copy.deepcopy(event_list)
		if self.usb_mouse is not None:
			tmp.insert(0, ("musb", "USB Mouse"))
		if self.rc_mouse is not None:
			tmp.insert(0, ("mrc", "Remote Control"))
		self.mouse_list = tmp

		tmp = copy.deepcopy(event_list)
		if self.usb_keyboard is not None:
			tmp.insert(0, ("kusb", "USB Keyboard"))
		if self.rc_keyboard is not None:
			tmp.insert(0, ("krc", "Remote Control"))
		self.keyboard_list = tmp
		print "E:", event_list
		print "M:", self.mouse_list
		print "K:", self.keyboard_list

	def startBrowser(self):
		self.timer_start.stop()

		self.lock = True
		excute_cmd("killall -15 %s"%(self.browser_name))
		excute_cmd("echo 0 > /proc/sys/vm/swappiness")

		kbd_cmd = " "
		mouse_cmd = " "
		extra_cmd = " " 
		browser_cmd = "%s/%s -qws" % (self.browser_root, self.browser_name)

		mouse_param = self.mouse.value
		if self.mouse.value == "mrc":
			mouse_param = self.rc_mouse
		elif self.mouse.value == "musb":
			mouse_param = self.usb_mouse
		keyboard_param = self.keyboard.value
		if self.keyboard.value == "krc":
			keyboard_param = self.rc_keyboard
		elif self.keyboard.value == "kusb":
			keyboard_param = self.usb_keyboard

		if self.getHandlerName(mouse_param)[1:].startswith("dreambox"):
			enable_rc_mouse(True) #rc-mouse on
		if str(mouse_param).startswith("event"):
			mouse_cmd = "export QWS_MOUSE_PROTO=LinuxInput:/dev/input/%s; " % (str(mouse_param))

		keymap_param = ""
		if self.langs.value == "de":
			keymap_param = ":keymap=/usr/share/keymaps/player/de.qmap"
		kbd_cmd = "export QWS_KEYBOARD=LinuxInput:/dev/input/%s%s; " % (str(keyboard_param), keymap_param)

		cmd = "%s%s%s%s" % (extra_cmd, kbd_cmd, mouse_cmd, browser_cmd)
		print "prepared command : [%s]" % cmd

		self.launcher = eConsoleAppContainer()
		self.launcher.appClosed.append(self.callbackLauncherAppClosed)
		self.launcher.dataAvail.append(self.callbackLauncherDataAvail)

		fbClass.getInstance().lock()
		#eRCInput.getInstance().lock()

		global alpha_value
		alpha_value = self.alpha.value
		change_galpha(set_const=True, set_value=True)

		self.launcher.execute(cmd)
		print "started browser..."

	def keyGo(self):
		self.saveConfig()
		self.info.setText("Starting Webbrowser. Please wait...")
		if self.lock == False:
			if self.langs.value == "de":
				language.activateLanguageIndex(1)
			else:
				language.activateLanguageIndex(0)
			self.timer_start = eTimer()
			self.timer_start.callback.append(self.startBrowser)
			self.timer_start.start(10)

	def getHandlerName(self, v):
		if v == "mrc":
			v = self.rc_mouse
		elif v == "musb":
			v = self.usb_mouse
		elif v == "krc":
			v = self.rc_keyboard
		elif v == "kusb":
			v = self.usb_keyboard
		for l in self.name_list:
			if l[0] == v:
				return l[1]
		return None

	def callbackLauncherDataAvail(self, ret_data):
		print ret_data
		if ret_data.startswith("--done--"):
			self.lock = False
			self.doExit()

	def callbackLauncherAppClosed(self, retval = 1):
		self.lock = False

def sessionstart(session, **kwargs):
	enable_rc_mouse(False)
	change_galpha(set_const=False, set_value=True)
	excute_cmd("killall -15 arora")

def main(session, **kwargs):
	session.open(BrowserLauncher)

def Plugins(**kwargs):
	return [PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, needsRestart = False, fnc=sessionstart),
		PluginDescriptor(name=_("Web Browser"), description="start web browser", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)]


