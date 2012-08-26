from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.InfoBar import InfoBar
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarNotifications
from Screens.VirtualKeyBoard import VirtualKeyBoard

from Components.PluginComponent import plugins
from Components.Button import Button
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.MenuList import MenuList
from Components.Label import Label, MultiColorLabel
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigPosition, getConfigListEntry, ConfigBoolean, ConfigInteger, ConfigText, ConfigSelection, configfile, getCharValue

from enigma import eTimer, eConsoleAppContainer, getDesktop, eServiceReference, iPlayableService, iServiceInformation, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, getPrevAsciiCode, eRCInput, fbClass

import os, struct, threading, stat, select, time, socket, select

strIsEmpty = lambda x: x is None or len(x) == 0

HBBTVAPP_PATH = "/usr/local/hbb-browser"
COMMAND_PATH = '/tmp/.sock.hbbtv.cmd'

class GlobalValues:
	command_util   = None
	command_server = None

	before_service = None

	channel_info_sid   = None
	channel_info_onid  = None
	channel_info_tsid  = None
	channel_info_name  = None
	channel_info_orgid = None

	hbbtv_handelr = None

	packet_m  = 0xBBADBEE
	packet_h  = '!IIII'
	packet_hl = struct.calcsize(packet_h)
__gval__ = GlobalValues()

def getPacketHeaders():
	global __gval__
	return (__gval__.packet_m, __gval__.packet_h, __gval__.packet_hl)

def setChannelInfo(sid, onid, tsid, name, orgid):
	if sid is None:   sid   = 0;
	if onid is None:  onid  = 0;
	if tsid is None:  tsid  = 0;
	if name is None:  name  = "";
	if orgid is None: orgid = 0;
	global __gval__
	__gval__.channel_info_sid   = sid
	__gval__.channel_info_onid  = onid
	__gval__.channel_info_tsid  = tsid
	__gval__.channel_info_name  = name
	__gval__.channel_info_orgid = orgid
	print "Set Channel Info >> sid : %X, onid : %X, tsid : %X, name : %s, orgid : %d " % (sid, onid, tsid, name, orgid)
def getChannelInfos():
	global __gval__
	print "Get Channel Info >> sid : %X, onid : %X, tsid : %X, name : %s, orgid : %d " % (__gval__.channel_info_sid, 
		__gval__.channel_info_onid, __gval__.channel_info_tsid, __gval__.channel_info_name, __gval__.channel_info_orgid)
	return (__gval__.channel_info_sid, 
		__gval__.channel_info_onid, 
		__gval__.channel_info_tsid, 
		__gval__.channel_info_name, 
		__gval__.channel_info_orgid)

def getCommandUtil():
	global __gval__
	return __gval__.command_util
def getCommandServer():
	global __gval__
	return __gval__.command_server

def setBeforeService(s):
	global __gval__
	__gval__.before_service = s
def getBeforeService():
	global __gval__
	return __gval__.before_service

def _unpack(packed_data):
	(mg, h, hlen) = getPacketHeaders()

	if strIsEmpty(packed_data):
		return None
	(m, o, l, s) = struct.unpack(h, packed_data[:hlen])
	if m != mg:
		return None
	d = 0
	if l > 0:
		d = packed_data[hlen:hlen+l]
	return (o,d,s)

def _pack(opcode, params=None, reserved=0):
	(m, h, hlen) = getPacketHeaders()
	if strIsEmpty(params):
		params = ''
	packed_data = struct.pack(h, m, opcode, len(params), reserved)
	return packed_data + params

class MMSStreamURL:
	headers = [
                   'GET %s HTTP/1.0'
                  ,'Accept: */* '
                  ,'User-Agent: NSPlayer/7.10.0.3059 '
                  ,'Host: %s '
                  ,'Connection: Close '
		  ]

	def __init__(self):
		self.sendmsg = ''
		for m in self.headers:
			self.sendmsg += m + '\n'
		self.sendmsg += '\n\n'

	def request(self, host, port=80, location='/'):
		sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		sock.connect((host, port))
		sock.send(self.sendmsg%(location, host))
		print "Send Data : "
		print self.sendmsg%(location, host)
		fullydata = ''
		while 1:
			res = sock.recv(1024)
			if res == '': break
			fullydata += res
		sock.close()
		return fullydata

	def parse(self, data):
		for d in data.splitlines():
			if d.startswith('Location: '):
				return d[9:]
		return None

	def getLocationData(self, url):
		url_list,host,location = None,None,None
		try:
			url = url[url.find(':')+3:]
			url_list = url.split('/')
			host = url_list[0]
			location = url[len(url_list[0]):]
		except Exception, err_msg:
			print err_msg
			return None
		html = self.request(host=host, location=location)
		return self.parse(html)

class OpCodeSet:
	def __init__(self):
		self._opcode_ = {
			 "OP_UNKNOWN"			: 0x0000
			,"OP_HBBTV_EXIT"		: 0x0001
			,"OP_HBBTV_OPEN_URL"		: 0x0002
			,"OP_HBBTV_LOAD_AIT"		: 0x0003
			,"OP_HBBTV_UNLOAD_AIT"		: 0x0004
			,"OP_HBBTV_FULLSCREEN"		: 0x0005
			,"OP_HBBTV_TITLE"		: 0x0006
			,"OP_OIPF_GET_CHANNEL_INFO_URL"	: 0x0101
			,"OP_OIPF_GET_CHANNEL_INFO_AIT" : 0x0102
			,"OP_OIPF_GET_CHANNEL_INFO_LIST": 0x0103
			,"OP_VOD_URI"			: 0x0201
			,"OP_VOD_PLAY"			: 0x0202
			,"OP_VOD_STOP"			: 0x0203
			,"OP_VOD_PAUSE"			: 0x0204
			,"OP_VOD_STATUS"		: 0x0205
			,"OP_VOD_FORBIDDEN"		: 0x0206
			,"OP_BROWSER_OPEN_URL"		: 0x0301
		}
		self._opstr_ = {
			 0x0000 : "OP_UNKNOWN"
			,0x0001 : "OP_HBBTV_EXIT"
			,0x0002 : "OP_HBBTV_OPEN_URL"
			,0x0003 : "OP_HBBTV_LOAD_AIT"
			,0x0004 : "OP_HBBTV_UNLOAD_AIT"
			,0x0005 : "OP_HBBTV_FULLSCREEN"
			,0x0006 : "OP_HBBTV_TITLE"
			,0x0101 : "OP_OIPF_GET_CHANNEL_INFO_URL"
			,0x0102 : "OP_OIPF_GET_CHANNEL_INFO_AIT"
			,0x0103 : "OP_OIPF_GET_CHANNEL_INFO_LIST"
			,0x0201 : "OP_VOD_URI"
			,0x0202 : "OP_VOD_PLAY"
			,0x0203 : "OP_VOD_STOP"
			,0x0204 : "OP_VOD_PAUSE"
			,0x0205 : "OP_VOD_STATUS"
			,0x0206 : "OP_VOD_FORBIDDEN"
			,0x0301 : "OP_BROWSER_OPEN_URL"
		}

	def get(self, opstr):
		try:
			return self._opcode_[opstr]
		except: pass
		return self._opcode_["OP_UNKNOWN"]

	def what(self, opcode):
		try:
			return self._opstr_[opcode]
		except: pass
		return self._opstr_["0x0000"]

class SocketParams:
	def __init__(self):
		self.protocol = None
		self.type     = None
		self.addr     = None
		self.buf_size = 4096
		self.handler  = None
		self.timeout  = 5
		self.destroy  = None

class StreamServer:
	def __init__(self, params):
		self._protocol = params.protocol
		self._type     = params.type
		self._addr     = params.addr
		self._buf_size = params.buf_size
		self._handler  = params.handler
		self._timeout  = params.timeout
		self._destroy  = params.destroy

		self._terminated = False
		self._server_thread = None

		self.onHbbTVCloseCB = []
		self.onSetPageTitleCB = []

	def __del__(self):
		if self._destroy is not None:
			self._destroy(self._addr)

	def stop(self):
		self._terminated = True
		if self._server_thread is not None:
			self._server_thread.join()
			self._server_thread = None

	def start(self):
		self._socket = socket.socket(self._protocol, self._type)
		self._socket.settimeout(self._timeout)
		self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._socket.bind(self._addr)
		self._socket.listen(True)

		self._server_thread = threading.Thread(target=self._listen)
		self._server_thread.start()

	def _listen(self):
		select_list = [self._socket]
		def _accept():
			try:
				conn, addr = self._socket.accept()
				self._client(conn, addr)
			except Exception, ErrMsg:
				print "ServerSocket Error >>", ErrMsg
				pass

		while not self._terminated:
			readable, writable, errored = select.select(select_list, [], [], self._timeout)
			for s in readable:
				if s is self._socket:
					_accept()

	def _client(self, conn, addr):
		try:
			send_data     = ''
			received_data = conn.recv(self._buf_size)
			if self._handler is not None and not strIsEmpty(received_data):
				send_data = self._handler.doHandle(received_data, self.onHbbTVCloseCB, self.onSetPageTitleCB)
			self._send(conn, send_data)
		except Exception, ErrMsg: 
			try: conn.close()
			except:pass
			if self._handler is not None:
				self._handler.printError(ErrMsg)
	def _send(self, conn, data) :
		conn.send(data)
		conn.close()

class ServerFactory:
	def doListenUnixTCP(self, name, handler):
		def destroy(name):
			if os.path.exists(name):
				os.unlink(name)
				print "Removed ", name
		destroy(name)

		params = SocketParams()
		params.protocol = socket.AF_UNIX
		params.type     = socket.SOCK_STREAM
		params.addr     = name
		params.handler  = handler
		params.destroy  = destroy

		streamServer = StreamServer(params)
		streamServer.start()
		return streamServer

	def doListenInetTCP(self, ip, port, handler):
		print "not implemented yet!!"
	def doListenUnixDGRAM(self, name, handler):
		print "not implemented yet!!"
	def doListenInetDGRAM(self, ip, port, handler):
		print "not implemented yet!!"

class Handler:
	def doUnpack(self, data):
		return _unpack(data)

	def doPack(self, opcode, params, reserved=0):
		return _pack(opcode, params, reserved)

	def doHandle(self, data, onCloseCB):
		opcode, params = 0x0, 'Invalid Request!!'
		return _pack(opcode, params)

	def printError(self, reason):
		print reason

class BrowserCommandUtil(OpCodeSet):
	def __init__(self):
		self._fd = None
		OpCodeSet.__init__(self)

	def isConnected(self):
		if self._fd is None:
			return False
		return True

	def doConnect(self, filename):
		if not os.path.exists(filename):
			print "file not exists :", filename
			return False
		try:
			self._fd = os.open(filename, os.O_WRONLY|os.O_NONBLOCK)
			if self._fd is None:
				print "fail to open file :", filename
				return False
		except Exception, ErrMsg:
			print ErrMsg
			self._fd = None
			return False
		print "connected!! to ", filename
		return True

	def doDisconnect(self):
		if self._fd is None:
			return
		os.close(self._fd)
		self._fd = None

	def doSend(self, command, params=None, reserved=0):
		if self._fd is None:
			print "connected pipe was not exists!!"
			return False
		data = ''
		try:
			data = _pack(self.get(command), params, reserved)
			if data is None:
				return False
			os.write(self._fd, data)
			print "Send OK!! :", command
		except:	return False
		return True

	def sendCommand(self, command, params=None, reserved=0):
		if not self.isConnected():
			global COMMAND_PATH
			self.doConnect(COMMAND_PATH)
		result = self.doSend(command, params, reserved)
		self.doDisconnect()
		return result

class HandlerHbbTV(Handler):
	_vod_service = None
	def __init__(self, session):
		self._session = session
		self.opcode = OpCodeSet()
		self.handle_map = {
			 0x0001 : self._cb_handleCloseHbbTVBrowser
			,0x0006 : self._cb_handleSetPageTitle
			,0x0101 : self._cb_handleGetChannelInfoForUrl
			,0x0102 : self._cb_handleGetChannelInfoForAIT
			,0x0103 : self._cb_handleGetChannelInfoList
			,0x0201 : self._cb_handleVODPlayerURI
			,0x0202 : self._cb_handleVODPlayerPlay
			,0x0203 : self._cb_handleVODPlayerStop
			,0x0204 : self._cb_handleVODPlayerPlayPause
		}
		self._on_close_cb = None
		self._on_set_title_cb = None

		self._vod_uri = None

	def _handle_dump(self, handle, opcode, data=None):
		if True: return
		print str(handle)
		try:
			print "    - opcode : ", self.opcode.what(opcode)
		except: pass
		print "    - data   : ", data

	def doHandle(self, data, onCloseCB, onSetPageTitleCB):
		opcode, params, reserved = None, None, 0
		self._on_close_cb = onCloseCB
		self._on_set_title_cb = onSetPageTitleCB
		try:
			datas  = self.doUnpack(data)
		except Exception, ErrMsg:
			print "Unpacking packet ERR :", ErrMsg
			params = 'fail to unpack packet!!'
			opcode = self.opcode.get("OP_UNKNOWN")
			return self.doPack(opcode, params)
		else:
			opcode = datas[0]
			params = datas[1]
		self.opcode.what(opcode)

		try:
			#print self.handle_map[opcode]
			(reserved, params) = self.handle_map[opcode](opcode, params)
		except Exception, ErrMsg:
			print "Handling packet ERR :", ErrMsg
			params = 'fail to handle packet!!'
			opcode = self.opcode.get("OP_UNKNOWN")
			return self.doPack(opcode, params)
		self._on_close_cb = None
		self._on_set_title_cb = None
		return self.doPack(opcode, params, reserved)

	def _cb_handleGetChannelInfoForUrl(self, opcode, data):
		self._handle_dump(self._cb_handleGetChannelInfoForUrl, opcode, data)
		(sid, onid, tsid, name, orgid) = getChannelInfos()
		namelen = len(name)
		return (0, struct.pack('!IIII', sid, onid, tsid, namelen) + name)

	def _cb_handleGetChannelInfoForAIT(self, opcode, data):
		self._handle_dump(self._cb_handleGetChannelInfoForAIT, opcode, data)
		(sid, onid, tsid, name, orgid) = getChannelInfos()
		namelen = len(name)
		return (0, struct.pack('!IIIII', orgid, sid, onid, tsid, namelen) + name)

	def _cb_handleGetChannelInfoList(self, opcode, data):
		self._handle_dump(self._cb_handleGetChannelInfoList, opcode, data)
		(sid, onid, tsid, name, orgid) = getChannelInfos()
		namelen = len(name)
		channel_list_size = 1
		return (channel_list_size, struct.pack('!IIII', sid, onid, tsid, namelen) + name)

	def _cb_handleSetPageTitle(self, opcode, data):
		self._handle_dump(self._cb_handleCloseHbbTVBrowser, opcode, data)
		if data.startswith('file://') or data.startswith('http://'):
			return "OK"
		if self._on_set_title_cb is not None:
			for x in self._on_set_title_cb:
				try:
					x(data)
				except Exception, ErrMsg:
					if x in self._on_set_title_cb:
						self._on_set_title_cb.remove(x)
		return (0, "OK")

	def _cb_handleCloseHbbTVBrowser(self, opcode, data):
		self._handle_dump(self._cb_handleCloseHbbTVBrowser, opcode, data)

		if self._on_close_cb:
			for x in self._on_close_cb:
				try:
					x()
				except Exception, ErrMsg:
					if x in self._on_close_cb:
						self._on_close_cb.remove(x)

		command_util = getCommandUtil()
		command_util.sendCommand('OP_HBBTV_FULLSCREEN', None)

		before_service = getBeforeService()
		if before_service is not None:
			self._session.nav.playService(before_service)
		return (0, "OK")

	def _cb_handleVODPlayerURI(self, opcode, data):
		self._vod_uri = None
		hl = struct.calcsize('!II')
		datas = struct.unpack('!II', data[:hl])
		uriLength = datas[1]
		vodUri = data[hl:hl+uriLength]
		self._handle_dump(self._cb_handleVODPlayerURI, opcode, vodUri)
		self._vod_uri = vodUri
		return (0, "OK")

	def doStop(self, restoreBeforeService=True, needStop=True):
		if needStop == True:
			self._session.nav.stopService()
		if self._vod_service is not None and restoreBeforeService:
			before_service = getBeforeService()
			self._session.nav.playService(before_service)
			self._vod_uri = None
		self._vod_service = None

	def getUrl(self):
		return self._vod_uri

	def doRetryOpen(self, url):
		if url is None:
			return False
		for ii in range(5):
			self._vod_service = None
			try:
				print "try to open vod [%d] : %s" % (ii, url)
				self._vod_service = eServiceReference(4097, 0, url)
				self._session.nav.playService(self._vod_service)
				if self._vod_service is not None:
					return True
			except Exception, ErrMsg: 
				print "OpenVOD ERR :", ErrMsg
			time.sleep(1)
		return False

	def _cb_handleVODPlayerPlay(self, opcode, data):
		self._handle_dump(self._cb_handleVODPlayerPlay, opcode, data)
		self.doStop(restoreBeforeService=False)
		if self.doRetryOpen(url=self._vod_uri) == False:
			self.doStop()
		return (0, "OK")

	def _cb_handleVODPlayerStop(self, opcode, data):
		self._handle_dump(self._cb_handleVODPlayerStop, opcode, data)
		self.doStop()	
		return (0, "OK")

	def _cb_handleVODPlayerPlayPause(self, opcode, data):
		self._handle_dump(self._cb_handleVODPlayerPlayPause, opcode, data)
		service = self._session.nav.getCurrentService()
		try:
			pauseFlag = data[0]
			servicePause = service.pause()
			if pauseFlag == 'U':
				servicePause.unpause()
			elif pauseFlag == 'P':
				servicePause.pause()
		except Exception, ErrMsg:
			print "onPause ERR :", ErrMsg
		return (0, "OK")

class HbbTVWindow(Screen, InfoBarNotifications):
	skin = 	"""
		<screen name="HbbTVWindow" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="HbbTV Plugin">
		</screen>
		"""
	def __init__(self, session, url=None, cbf=None, useAIT=False):
		self._session = session
		eRCInput.getInstance().lock()

		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)
		self.__event_tracker = ServiceEventTracker(screen = self, eventmap = {
			iPlayableService.evUser+20: self._serviceForbiden,
		})

		self._url = url
		self._use_ait = useAIT
		self._cb_closed_func = cbf
		self.onLayoutFinish.append(self._layoutFinished)

		command_server = getCommandServer()
		if self._cb_set_page_title not in command_server.onSetPageTitleCB:
			command_server.onSetPageTitleCB.append(self._cb_set_page_title)

		if self._cb_close_window not in command_server.onHbbTVCloseCB:
			command_server.onHbbTVCloseCB.append(self._cb_close_window)

		self._closeTimer = eTimer()
		self._closeTimer.callback.append(self._do_close)

	def _layoutFinished(self):
		command_util = getCommandUtil()
		(sid, onid, tsid, name, orgid) = getChannelInfos()
		params  = struct.pack('!IIIII', orgid, sid, onid, tsid, len(name)) + name
		if self._use_ait:
			command_util.sendCommand('OP_HBBTV_UNLOAD_AIT')
			time.sleep(1)
			command_util.sendCommand('OP_HBBTV_LOAD_AIT', params, 1)
			return
		command_util.sendCommand('OP_HBBTV_LOAD_AIT', params)
		time.sleep(1)
		command_util.sendCommand('OP_HBBTV_OPEN_URL', self._url)

	def _cb_close_window(self):
		self._closeTimer.start(1000)

	def _do_close(self):
		self._closeTimer.stop()
		command_server = getCommandServer()
		try:
			if self._cb_set_page_title in command_server.onSetPageTitleCB:
				command_server.onSetPageTitleCB.remove(self._cb_set_page_title)
		except Exception, ErrMsg: pass
		try:
			if self._cb_close_window in command_server.onHbbTVCloseCB:
					command_server.onHbbTVCloseCB.remove(self._cb_close_window)
		except Exception, ErrMsg: pass
		try:
			if self._cb_closed_func is not None:
				self._cb_closed_func()
		except: pass
		eRCInput.getInstance().unlock()
		self.close()

	def _serviceForbiden(self):
		global __gval__
		real_url = MMSStreamURL().getLocationData(__gval__.hbbtv_handelr.getUrl())
		print "Received URI :\n",real_url

		if real_url is not None:
			__gval__.hbbtv_handelr.doRetryOpen(real_url.strip())

	def _cb_set_page_title(self, title=None):
		print "page title :",title
		if title is None:
			return
		self.setTitle(title)

class HbbTVHelper(Screen):
	skin = 	"""<screen name="HbbTVHelper" position="0,0" size="0,0" backgroundColor="transparent" flags="wfNoBorder" title=" "></screen>"""
	def __init__(self, session):
		global __gval__
		__gval__.hbbtv_handelr = HandlerHbbTV(session)
		__gval__.command_server = ServerFactory().doListenUnixTCP('/tmp/.sock.hbbtv.url', __gval__.hbbtv_handelr)

		self._urls = None
		self._stop_opera()
		self._start_opera()

		Screen.__init__(self, session)
		self._session = session
		self._timer_infobar = eTimer()
		self._timer_infobar.callback.append(self._cb_registrate_infobar)
		self._timer_infobar.start(1000)

		self._excuted_browser = False

		__gval__.command_util = BrowserCommandUtil()

	def _cb_registrate_infobar(self):
		if InfoBar.instance:
			self._timer_infobar.stop()
			if self._cb_ready_for_ait not in InfoBar.instance.onReadyForAIT:
				InfoBar.instance.onReadyForAIT.append(self._cb_ready_for_ait)
			if self._cb_hbbtv_activated not in InfoBar.instance.onHBBTVActivation:
				InfoBar.instance.onHBBTVActivation.append(self._cb_hbbtv_activated)

	def _cb_ready_for_ait(self, orgId=0):
		if orgId == 0:
			if not self._excuted_browser:
				command_util = getCommandUtil()
				command_util.sendCommand('OP_HBBTV_UNLOAD_AIT')
			return
		setChannelInfo(None, None, None, None, None)

		service = self._session.nav.getCurrentService()
                info = service and service.info()
		if info is not None:
			sid  = info.getInfo(iServiceInformation.sSID)
			onid = info.getInfo(iServiceInformation.sONID)
			tsid = info.getInfo(iServiceInformation.sTSID)
			name = info.getName()
			if name is None:
				name = ""
			orgid   = 0
			namelen = len(name)
			for x in info.getInfoObject(iServiceInformation.sHBBTVUrl):
				if x[0] == 1 :
					orgid = x[3]
					break
			setChannelInfo(sid, onid, tsid, name, orgid)

	def _cb_hbbtv_activated(self, title=None, url=None):
		if not self._is_browser_running():
			message = "HbbTV Browser was not running.\nPlease running browser before start HbbTV Application."
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
			return
		service = self._session.nav.getCurrentlyPlayingServiceReference()
		setBeforeService(service)
		self._start_hbbtv_application(title, url)

	def _start_hbbtv_application(self, title, url):
		tmp_url = self.getStartHbbTVUrl()
		if url is None:
			url = tmp_url
		if strIsEmpty(url):
			print "can't get url of hbbtv!!"
			return
		print "success to get url of hbbtv!! >>", url
		if self._excuted_browser:
			print "already excuted opera browser!!"
			return

		use_ait = False
		for x in self._urls:
			control_code = x[0]
			tmp_url = x[2]
			if tmp_url == url and control_code == 1:
				use_ait = True
		self._excuted_browser = True
		self._session.open(HbbTVWindow, url, self._cb_closed_browser, use_ait)

	def _cb_closed_browser(self):
		self._excuted_browser = False

	def _start_opera(self):
		if not self._is_browser_running():
			global HBBTVAPP_PATH
			start_command = '%s/launcher start'%(HBBTVAPP_PATH)
			os.system(start_command)

	def _stop_opera(self):
		global HBBTVAPP_PATH
		try:	os.system('%s/launcher stop'%(HBBTVAPP_PATH))
		except: pass

	def getStartHbbTVUrl(self):
		url, self._urls = None, None
                service = self._session.nav.getCurrentService()
                info = service and service.info()
                if not info: return None
                self._urls = info.getInfoObject(iServiceInformation.sHBBTVUrl)
		for u in self._urls:
			if u[0] == 1: # 0:control code, 1:name, 2:url, 3:orgid, 4:appid
				url = u[2]
		if url is None:
			url = info.getInfoString(iServiceInformation.sHBBTVUrl)
		return url

	def showApplicationSelectionBox(self):
		applications = []
		if self.getStartHbbTVUrl():
			for x in self._urls:
				applications.append((x[1], x))
		else: applications.append(("No detected HbbTV applications.", None))
		self._session.openWithCallback(self._application_selected, ChoiceBox, title=_("Please choose an HbbTV application."), list=applications)

	def _application_selected(self, selected):
		try:
			if selected[1] is None: return
			self._cb_hbbtv_activated(selected[1][1], selected[1][2])
		except Exception, ErrMsg: print ErrMsg

	def showBrowserConfigBox(self):
		start_stop_mode = []
		if self._is_browser_running():
			start_stop_mode.append(('Stop',None))
		else:	start_stop_mode.append(('Start',None))
		self._session.openWithCallback(self._browser_config_selected, ChoiceBox, title=_("Please choose one."), list=start_stop_mode)

	def _browser_config_selected(self, selected):
		if selected is None:
			return
		try:
			mode = selected[0]
			if mode == 'Start':
				if not self._is_browser_running():
					self._start_opera()
			elif mode == 'Stop':
				self._stop_opera()
		except Exception, ErrMsg: print "Config ERR :", ErrMsg

	def _is_browser_running(self):
		try:
			global HBBTVAPP_PATH
			ret = os.popen('%s/launcher check'%(HBBTVAPP_PATH)).read()
			return ret.strip() != "0"
		except Exception, ErrMsg:
			print "Check Browser Running ERR :", ErrMsg
		return False

_g_helper = None
class OperaBrowser(Screen):
	MENUBAR_ITEM_WIDTH  = 150
	MENUBAR_ITEM_HEIGHT = 30
	SUBMENULIST_WIDTH   = 200
	SUBMENULIST_HEIGHT  = 25
	SUBMENULIST_NEXT    = 2

	skin =	"""
		<screen name="Opera Browser" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="Opera Browser">
			<widget name="topArea" zPosition="-1" position="0,0" size="1280,60" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" />
			<widget name="menuitemFile" position="30,20" size="150,30" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" foregroundColors="#9f1313,#a08500" />
			<widget name="menuitemHelp" position="180,20" size="150,30" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" foregroundColors="#9f1313,#a08500" />
			<widget name="menulist" position="50,%d" size="%d,150" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
			<widget name="submenulist" position="%d,%d" size="%d,150" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
			<widget name="bottomArea" position="0,640" size="1280,80" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" />
	        </screen>
		""" % (MENUBAR_ITEM_HEIGHT+30, SUBMENULIST_WIDTH, SUBMENULIST_WIDTH+50+SUBMENULIST_NEXT, MENUBAR_ITEM_HEIGHT+30, SUBMENULIST_WIDTH)

	MENUITEMS_LIST =[[('Open Location', None), ('Start/Stop',None), ('Exit', None)],
			 [('About', None)]]
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["MinuteInputActions", "ColorActions", "InputActions", "InfobarChannelSelection", "EPGSelectActions", "KeyboardInputActions"], {
			 "cancel"      : self.keyCancel
			,"ok"          : self.keyOK
			,"left"        : self.keyLeft
			,"right"       : self.keyRight
			,"up"          : self.keyUp
			,"down"        : self.keyDown
			,"menu"        : self.keyCancel
		}, -2)

		self.menubarCurrentIndex = 0
		self.lvMenuItems = []
		self.lvSubMenuItems = []

		self["topArea"]    = Label()
		self["bottomArea"] = Label()

		self["menuitemFile"] = MultiColorLabel()
		self["menuitemHelp"] = MultiColorLabel()

		self["menulist"] = MenuList(self.setListOnView())
		self["submenulist"] = MenuList(self.setSubListOnView())

		self.toggleMainScreenFlag = True
		self.toggleListViewFlag = False
		self.toggleSubListViewFlag = False
		self.currentListView = self["menulist"]

		self.onLayoutFinish.append(self.layoutFinished)

		self._onCloseTimer = eTimer()
		self._onCloseTimer.callback.append(self._cb_onClose)

	def enableRCMouse(self, mode): #mode=[0|1]|[False|True]
		rcmouse_path = "/proc/stb/fp/mouse"
		if os.path.exists(rcmouse_path):
			os.system("echo %d > %s" % (mode, rcmouse_path))

	def layoutFinished(self):
		self["menuitemFile"].setText("File")
		self["menuitemHelp"].setText("Help")

		self["menulist"].hide()
		self["submenulist"].hide()

		self["bottomArea"].setText("Opera Web Browser Plugin v0.1")
		self.setTitle("BrowserMain")
		self.selectMenuitem()

	def selectMenuitem(self):
		tmp = [self["menuitemFile"], self["menuitemHelp"]]
		self["menuitemFile"].setForegroundColorNum(0)
		self["menuitemHelp"].setForegroundColorNum(0)
		tmp[self.menubarCurrentIndex].setForegroundColorNum(1)

	def popupCloseAll(self):
		self.keyLeft()
		self.keyLeft()
		self.keyUp()
		self.keyCancel()

	def setListOnView(self):
		self.lvMenuItems = self.MENUITEMS_LIST[self.menubarCurrentIndex]	
		return self.lvMenuItems

	def setSubListOnView(self):
		self.lvSubMenuItems = []
		xl = self["menulist"].getCurrent()[1]
		if xl is None: return []
		for x in xl:
			self.lvSubMenuItems.append((x,None))
		return self.lvSubMenuItems

	def toggleMainScreen(self):
		if not self.toggleMainScreenFlag:
			self.show()
		else:	self.hide()
		self.toggleMainScreenFlag = not self.toggleMainScreenFlag

	def toggleListView(self):
		if not self.toggleListViewFlag:
			self["menulist"].show()
		else:	self["menulist"].hide()
		self.toggleListViewFlag = not self.toggleListViewFlag

	def toggleSubListView(self):
		if not self.toggleSubListViewFlag:
			self["submenulist"].show()
		else:	self["submenulist"].hide()
		self.toggleSubListViewFlag = not self.toggleSubListViewFlag

	def setCurrentListView(self, listViewIdx):
		if listViewIdx == 0:
			self.currentListView = None
		elif listViewIdx == 1:
			self.currentListView = self["menulist"]
		elif listViewIdx == 2:
			self.currentListView = self["submenulist"]

	def _cb_onClose(self):
		self._onCloseTimer.stop()
		command_server = getCommandServer()
		try:
			if self._on_close_window in command_server.onHbbTVCloseCB:
					command_server.onHbbTVCloseCB.remove(self._on_close_window)
		except Exception, ErrMsg: pass
		try:
			if self._on_setPageTitle in command_server.onSetPageTitleCB:
				command_server.onSetPageTitleCB.remove(self._on_setPageTitle)
		except Exception, ErrMsg: pass
		self._on_setPageTitle('Opera Browser')
		self.enableRCMouse(False)
		self.toggleMainScreen()
		eRCInput.getInstance().unlock()

	def _on_setPageTitle(self, title=None):
		print "page title :",title
		if title is None:
			return
		self.setTitle(title)

	def cbUrlText(self, data=None):
		print "Inputed Url :", data
		if strIsEmpty(data):
			return
		command_server = getCommandServer()
		if self._on_setPageTitle not in command_server.onSetPageTitleCB:
				command_server.onSetPageTitleCB.append(self._on_setPageTitle)
		if self._on_close_window not in command_server.onHbbTVCloseCB:
			command_server.onHbbTVCloseCB.append(self._on_close_window)
		self.toggleMainScreen()
		self.enableRCMouse(True)
		eRCInput.getInstance().lock()
		command_util = getCommandUtil()
		command_util.sendCommand('OP_BROWSER_OPEN_URL', data)

	def _on_close_window(self):
		self._onCloseTimer.start(1000)

	def _cmd_on_OpenLocation(self):
		global _g_helper
		if not _g_helper._is_browser_running():
			message = "Opera Browser was not running.\nPlease running browser using [File]>[Start/Stop] menu."
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
			return
		self.session.openWithCallback(self.cbUrlText, VirtualKeyBoard, title=("Please enter URL here"), text='http://')
	def _cmd_on_About(self):
		self.session.open(MessageBox, 'Opera Web Browser Plugin v0.1(beta)', type = MessageBox.TYPE_INFO)
	def _cmd_on_Exit(self):
		self.close()
	def _cmd_on_StartStop(self):
		global _g_helper
		if _g_helper is None: 
			return
		_g_helper.showBrowserConfigBox()
	def doCommand(self, command):
		cmd_map = {
			 'Exit'          :self._cmd_on_Exit
			,'About'         :self._cmd_on_About
			,'Open Location' :self._cmd_on_OpenLocation
			,'Start/Stop'    :self._cmd_on_StartStop
		}
		try:
			cmd_map[command]()
		except: pass

	def keyOK(self):
		if not self.toggleListViewFlag:
			self.keyDown()
			return
		if self.currentListView.getCurrent()[1] is None:
			self.doCommand(self.currentListView.getCurrent()[0])
			#self.session.open(MessageBox, _(self.currentListView.getCurrent()[0]), type = MessageBox.TYPE_INFO)
			return
		self.keyRight()

	def updateSelectedMenuitem(self, status):
		if self.menubarCurrentIndex == 0 and status < 0:
			self.menubarCurrentIndex = 1
		elif self.menubarCurrentIndex == 1 and status > 0:
			self.menubarCurrentIndex = 0
		else:	self.menubarCurrentIndex += status
		self.selectMenuitem()

	def keyLeft(self):
		if not self.toggleMainScreenFlag:
			return
		if not self.toggleListViewFlag:
			self.updateSelectedMenuitem(-1)
			return
		if self.toggleSubListViewFlag:
			self.setCurrentListView(1)
			self.toggleSubListView()
			return
		if self.currentListView.getSelectedIndex():
			self.currentListView.pageUp()

	def keyRight(self):
		if not self.toggleMainScreenFlag:
			return
		if not self.toggleListViewFlag:
			self.updateSelectedMenuitem(1)
			return
		if self.currentListView is None:
			return
		if self.currentListView.getCurrent()[1] is not None:
			parentSelectedIndex = self.currentListView.getSelectedIndex()
			self.setCurrentListView(2)
			self.currentListView.setList(self.setSubListOnView())
			self.currentListView.resize(self.SUBMENULIST_WIDTH, self.SUBMENULIST_HEIGHT*len(self.lvSubMenuItems)+5)
			self.currentListView.move(self.MENUBAR_ITEM_WIDTH*self.menubarCurrentIndex + self.SUBMENULIST_WIDTH+self.SUBMENULIST_NEXT + 50,self.MENUBAR_ITEM_HEIGHT+30+(parentSelectedIndex*self.SUBMENULIST_HEIGHT))
			self.toggleSubListView()

	def keyDown(self):
		if not self.toggleMainScreenFlag:
			return
		if self.currentListView is None:
			return
		if not self.toggleListViewFlag:
			self.currentListView.setList(self.setListOnView())
			self.currentListView.resize(self.SUBMENULIST_WIDTH, self.SUBMENULIST_HEIGHT*len(self.lvMenuItems)+5)
			self.currentListView.move(self.MENUBAR_ITEM_WIDTH*self.menubarCurrentIndex+1+ 50,self.MENUBAR_ITEM_HEIGHT+30)
			self.toggleListView()
			return
		self.currentListView.down()

	def keyUp(self):
		if not self.toggleMainScreenFlag:
			return
		if self.currentListView is None:
			return
		if self.currentListView == self["menulist"]:
			if self.currentListView.getSelectedIndex() == 0:
				self.toggleListView()
				return
		self.currentListView.up()

	def keyCancel(self):
		self.toggleMainScreen()

def auto_start_main(reason, **kwargs):
	if reason:
		command_server = getCommandServer()
		command_server.stop()

def session_start_main(session, reason, **kwargs):
	global _g_helper
	_g_helper = session.open(HbbTVHelper)

def plugin_start_main(session, **kwargs):
	session.open(OperaBrowser)

def plugin_extension_start_application(session, **kwargs):
	global _g_helper
	if _g_helper is None: 
		return
	_g_helper.showApplicationSelectionBox()

def plugin_extension_browser_config(session, **kwargs):
	global _g_helper
	if _g_helper is None: 
		return
	_g_helper.showBrowserConfigBox()

def Plugins(path, **kwargs):
	return 	[
		PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=auto_start_main),
		PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, needsRestart=True, fnc=session_start_main, weight=-10),
		PluginDescriptor(name="HbbTV Applications", where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=True, fnc=plugin_extension_start_application),
		PluginDescriptor(name="Browser Start/Stop", where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=True, fnc=plugin_extension_browser_config),
		PluginDescriptor(name="Opera Web Browser", description="start opera web browser", where=PluginDescriptor.WHERE_PLUGINMENU, needsRestart=True, fnc=plugin_start_main)
		]

