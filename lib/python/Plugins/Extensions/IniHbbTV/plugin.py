# for localized messages
from . import _

from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.InfoBar import InfoBar
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarNotifications
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.HelpMenu import HelpableScreen
from Screens.ChannelSelection import service_types_tv

from Components.Language import language
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.MenuList import MenuList
from Components.Label import Label, MultiColorLabel
from Components.ConfigList import ConfigListScreen
from Components.VolumeControl import VolumeControl
from Components.Pixmap import Pixmap
from Components.config import getConfigListEntry, ConfigText, ConfigSelection, config

from enigma import eTimer, eServiceReference, iPlayableService, iServiceInformation, eRCInput, fbClass, eServiceCenter

from bookmark import BookmarkManager, BookmarkData, CategoryData

import os, struct, threading, select, time, socket, select

strIsEmpty = lambda x: x is None or len(x) == 0

HBBTVAPP_PATH = "/usr/local/hbb-browser"
COMMAND_PATH = '/tmp/.sock.hbbtv.cmd'

_g_helper = None

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

	need_restart = False
	plugin_browser = None
__gval__ = GlobalValues()

def setPluginBrowser(browser=None):
	global __gval__
	__gval__.plugin_browser = browser
def getPluginBrowser():
	global __gval__
	return __gval__.plugin_browser

def getPacketHeaders():
	global __gval__
	return (__gval__.packet_m, __gval__.packet_h, __gval__.packet_hl)

def setChannelInfo(sid, onid, tsid, name, orgid):
	if sid is None:   sid   = 0
	if onid is None:  onid  = 0
	if tsid is None:  tsid  = 0
	if name is None:  name  = ""
	if orgid is None: orgid = 0
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

def isNeedRestart():
	global __gval__
	print "Need Restart(GET) : ", __gval__.need_restart
	return __gval__.need_restart
def setNeedRestart(n):
	global __gval__
	__gval__.need_restart = n
	print "Need Restart(SET) : ", __gval__.need_restart

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
				'GET %s HTTP/1.0',
				'Accept: */* ',
				'User-Agent: NSPlayer/7.10.0.3059 ',
				'Host: %s ',
				'Connection: Close '
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
		print "Request."
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
			"OP_UNKNOWN"				: 0x0000,
			"OP_HBBTV_EXIT"				: 0x0001,
			"OP_HBBTV_OPEN_URL"			: 0x0002,
			"OP_HBBTV_LOAD_AIT"			: 0x0003,
			"OP_HBBTV_UNLOAD_AIT"			: 0x0004,
			"OP_HBBTV_FULLSCREEN"			: 0x0005,
			"OP_HBBTV_TITLE"			: 0x0006,
			"OP_HBBTV_RETRY_OPEN_URL"		: 0x0009,
			"OP_HBBTV_CHANGE_CHANNEL"		: 0x000A,
			"OP_OIPF_GET_CHANNEL_INFO_URL"		: 0x0101,
			"OP_OIPF_GET_CHANNEL_INFO_AIT"		: 0x0102,
			"OP_OIPF_GET_CHANNEL_INFO_LIST"		: 0x0103,
			"OP_VOD_URI"				: 0x0201,
			"OP_VOD_PLAY"				: 0x0202,
			"OP_VOD_STOP"				: 0x0203,
			"OP_VOD_PAUSE"				: 0x0204,
			"OP_VOD_STATUS"				: 0x0205,
			"OP_VOD_FORBIDDEN"			: 0x0206,
			"OP_VOD_STOPED"				: 0x0207,
			"OP_VOD_SPEED_CTRL"			: 0x0208,
			"OP_VOD_SEEK_CTRL"			: 0x0209,
			"OP_BROWSER_OPEN_URL"			: 0x0301,
			"OP_BROWSER_VKBD_REQ"			: 0x0309,
			"OP_BROWSER_VKBD_RES"			: 0x030A,
			"OP_BROWSER_VKBD_PASTE_REQ"		: 0x030B,
			"OP_BROWSER_VKBD_PASTE_KEY"		: 0x030C,
			"OP_BROWSER_VKBD_PASTE_MOUSE"		: 0x030D,
			"OP_BROWSER_MENU_REQ"			: 0x030E,
			"OP_BROWSER_MENU_RES"			: 0x030F,
			"OP_DVBAPP_VOL_UP"			: 0x0401,
			"OP_DVBAPP_VOL_DOWN"			: 0x0402,
			"OP_SYSTEM_OUT_OF_MEMORY"		: 0x0501,
			"OP_SYSTEM_NOTIFY_MY_PID"		: 0x0502
		}
		self._opstr_ = {
			0x0000 : "OP_UNKNOWN",
			0x0001 : "OP_HBBTV_EXIT",
			0x0002 : "OP_HBBTV_OPEN_URL",
			0x0003 : "OP_HBBTV_LOAD_AIT",
			0x0004 : "OP_HBBTV_UNLOAD_AIT",
			0x0005 : "OP_HBBTV_FULLSCREEN",
			0x0006 : "OP_HBBTV_TITLE",
			0x0009 : "OP_HBBTV_RETRY_OPEN_URL",
			0x000A : "OP_HBBTV_CHANGE_CHANNEL",
			0x0101 : "OP_OIPF_GET_CHANNEL_INFO_URL",
			0x0102 : "OP_OIPF_GET_CHANNEL_INFO_AIT",
			0x0103 : "OP_OIPF_GET_CHANNEL_INFO_LIST",
			0x0201 : "OP_VOD_URI",
			0x0202 : "OP_VOD_PLAY",
			0x0203 : "OP_VOD_STOP",
			0x0204 : "OP_VOD_PAUSE",
			0x0205 : "OP_VOD_STATUS",
			0x0206 : "OP_VOD_FORBIDDEN",
			0x0207 : "OP_VOD_STOPED",
			0x0208 : "OP_VOD_SPEED_CTRL",
			0x0209 : "OP_VOD_SEEK_CTRL",
			0x0301 : "OP_BROWSER_OPEN_URL",
			0x0309 : "OP_BROWSER_VKBD_REQ",
			0x030A : "OP_BROWSER_VKBD_RES",
			0x030B : "OP_BROWSER_VKBD_PASTE_REQ",
			0x030C : "OP_BROWSER_VKBD_PASTE_KEY",
			0x030D : "OP_BROWSER_VKBD_PASTE_MOUSE",
			0x030E : "OP_BROWSER_MENU_REQ",
			0x030F : "OP_BROWSER_MENU_RES",
			0x0401 : "OP_DVBAPP_VOL_UP",
			0x0402 : "OP_DVBAPP_VOL_DOWN",
			0x0501 : "OP_SYSTEM_OUT_OF_MEMORY",
			0x0502 : "OP_SYSTEM_NOTIFY_MY_PID"
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
		self.type = None
		self.addr = None
		self.buf_size = 4096
		self.handler = None
		self.timeout = 5
		self.destroy = None

class StreamServer:
	def __init__(self, params):
		self._protocol = params.protocol
		self._type = params.type
		self._addr = params.addr
		self._buf_size = params.buf_size
		self._handler = params.handler
		self._timeout = params.timeout
		self._destroy = params.destroy

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
			send_data = ''
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
		params.type = socket.SOCK_STREAM
		params.addr = name
		params.handler = handler
		params.destroy = destroy

		streamServer = StreamServer(params)
		streamServer.start()
		return streamServer

	def doListenInetTCP(self, ip, port, handler):
		print "Not implemented yet!!"
	def doListenUnixDGRAM(self, name, handler):
		print "Not implemented yet!!"
	def doListenInetDGRAM(self, ip, port, handler):
		print "Not implemented yet!!"

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
			print "File not exists :", filename
			return False
		try:
			self._fd = os.open(filename, os.O_WRONLY|os.O_NONBLOCK)
			if self._fd is None:
				print "Fail to open file :", filename
				return False
		except Exception, ErrMsg:
			print ErrMsg
			self._fd = None
			return False
		return True

	def doDisconnect(self):
		if self._fd is None:
			return
		os.close(self._fd)
		self._fd = None

	def doSend(self, command, params=None, reserved=0):
		if self._fd is None:
			print "No found pipe!!"
			return False
		data = ''
		try:
			data = _pack(self.get(command), params, reserved)
			if data is None:
				return False
			os.write(self._fd, data)
			print "Send OK!! :", command
		except: return False
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
			0x0001 : self._cb_handleCloseHbbTVBrowser,
			0x0006 : self._cb_handleSetPageTitle,
			0x0009 : self._cb_handleHbbTVRetryOpen,
			0x000A : self._cb_handleHbbTVChangeChannel,
			0x0101 : self._cb_handleGetChannelInfoForUrl,
			0x0102 : self._cb_handleGetChannelInfoForAIT,
			0x0103 : self._cb_handleGetChannelInfoList,
			0x0201 : self._cb_handleVODPlayerURI,
			0x0202 : self._cb_handleVODPlayerPlay,
			0x0203 : self._cb_handleVODPlayerStop,
			0x0204 : self._cb_handleVODPlayerPlayPause,
			0x0401 : self._cb_handleDVBAppVolUp,
			0x0402 : self._cb_handleDVBAppVolDown,
			0x0208 : self._cb_handleVODSpeedCtrl,
			0x0209 : self._cb_handleVODSeekCtrl,
			0x0501 : self._cb_handleSystemOutOfMemory,
			0x0502 : self._cb_handleSystemNotufyMyPID,
			0x0309 : self._cb_handleShowVirtualKeyboard,
			0x030B : self._cb_handlePasteVirtualKeyboard,
			0x030E : self._cb_handleBrowserMenuReq
		}
		self._on_close_cb = None
		self._on_set_title_cb = None

		self._vod_uri = None

		self._retry_open_url = None
		self._timer_retry_open = eTimer()
		self._timer_paste_vkbd = eTimer()
		self._curren_title = None

	def _handle_dump(self, handle, opcode, data=None):
		if True: return
		print str(handle)
		try:
			print " - opcode : ", self.opcode.what(opcode)
		except: pass
		print " - data	: ", data

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

	def _cb_handleHbbTVChangeChannel(self, opcode, data):
		self._handle_dump(self._cb_handleHbbTVChangeChannel, opcode, data)
		global _g_helper
		if _g_helper is None:
			return (0, "NOK")
		dataItems = data.split(":")
		sid = dataItems[0]
		tsid = dataItems[1]
		if not _g_helper.doChangeChannel(sid, tsid):
			return (0, "NOK")
		return (0, "OK")

	def _cb_handleBrowserMenuReq(self, opcode, data):
		self._handle_dump(self._cb_handleBrowserMenuReq, opcode, data)
		fbClass.getInstance().unlock()
		eRCInput.getInstance().unlock()
		browser = getPluginBrowser()
		if browser is not None:
			browser.setCurrentPageUrl(data, self._curren_title)
		return (0, "OK")

	def _cb_handlePasteVirtualKeyboard(self, opcode, data):
		self._handle_dump(self._cb_handlePasteVirtualKeyboard, opcode, data)
		def _cb_PasteRefocusVirtualKeyboard():
			self._timer_paste_vkbd.stop()
			command_util = getCommandUtil()
			command_util.sendCommand('OP_BROWSER_VKBD_PASTE_MOUSE')
			try:
				self._timer_paste_vkbd.callback.remove(_cb_PasteMouseVirtualKeyboard)
			except: pass
		def _cb_PasteKeyVirtualKeyboard():
			self._timer_paste_vkbd.stop()
			command_util = getCommandUtil()
			command_util.sendCommand('OP_BROWSER_VKBD_PASTE_KEY')
			try:
				self._timer_paste_vkbd.callback.remove(_cb_PasteKeyVirtualKeyboard)
			except: pass
			self._timer_paste_vkbd.callback.append(_cb_PasteRefocusVirtualKeyboard)
			self._timer_paste_vkbd.start(100)
		def _cb_PasteMouseVirtualKeyboard():
			self._timer_paste_vkbd.stop()
			command_util = getCommandUtil()
			command_util.sendCommand('OP_BROWSER_VKBD_PASTE_MOUSE')
			#time.sleep(1)
			#command_util.sendCommand('OP_BROWSER_VKBD_PASTE_MOUSE')
			try:
				self._timer_paste_vkbd.callback.remove(_cb_PasteMouseVirtualKeyboard)
			except: pass
			#self._timer_paste_vkbd.callback.append(_cb_PasteKeyVirtualKeyboard)
			#self._timer_paste_vkbd.start(1000)
		self._timer_paste_vkbd.callback.append(_cb_PasteMouseVirtualKeyboard)
		self._timer_paste_vkbd.start(50)
		return (0, "OK")

	def _cb_virtualKeyboardClosed(self, data=None):
		fbClass.getInstance().lock()
		eRCInput.getInstance().lock()
		command_util = getCommandUtil()
		command_util.sendCommand('OP_BROWSER_VKBD_RES', data)
	def _cb_handleShowVirtualKeyboard(self, opcode, data):
		self._handle_dump(self._cb_handleShowVirtualKeyboard, opcode, data)
		fbClass.getInstance().unlock()
		eRCInput.getInstance().unlock()
		if data == 0 or strIsEmpty(data):
			data = ""
		self._session.openWithCallback(self._cb_virtualKeyboardClosed, VirtualKeyBoard, title=("Please enter URL here"), text=data)
		return (0, "OK")

	def _cb_handleVODSeekCtrl(self, opcode, data):
		self._handle_dump(self._cb_handleVODSeekCtrl, opcode, data)
		headLen = struct.calcsize('!I')
		unpackedData = struct.unpack('!I', data[:headLen])
		seekTime = unpackedData[0]
		service = self._session.nav.getCurrentService()
		seekable = service.seek()
		if seekable is None or not seekable.isCurrentlySeekable():
			raise Exception("This stream is not support manual seek.")
		pts = seekTime
		seekable.seekRelative(pts<0 and -1 or 1, abs(pts))
		return (0, "OK")

	def _cb_handleHbbTVRetryOpen(self, opcode, data):
		def _cb_HbbTVRetryOpenURL():
			self._timer_retry_open.stop()
			if self._retry_open_url is not None:
				command_util = getCommandUtil()
				command_util.sendCommand('OP_HBBTV_RETRY_OPEN_URL', params=self._retry_open_url)
			self._retry_open_url = None
			try:
				self._timer_retry_open.callback.remove(_cb_HbbTVRetryOpenURL)
			except: pass
		self._handle_dump(self._cb_handleHbbTVRetryOpen, opcode, data)
		headLen = struct.calcsize('!I')
		unpackedData = struct.unpack('!I', data[:headLen])
		delayTime = unpackedData[0]
		restartUrl = data[headLen:]

		self._retry_open_url = restartUrl.strip()
		self._timer_retry_open.callback.append(_cb_HbbTVRetryOpenURL)
		self._timer_retry_open.start(delayTime*1000)
		return (0, "OK")

	def _cb_handleSystemNotufyMyPID(self, opcode, data):
		self._handle_dump(self._cb_handleSystemNotufyMyPID, opcode, data)
		return (0, "OK")

	def _cb_handleSystemOutOfMemory(self, opcode, data):
		self._handle_dump(self._cb_handleSystemOutOfMemory, opcode, data)
		setNeedRestart(True)
		return (0, "OK")

	def _cb_handleVODSpeedCtrl(self, opcode, data):
		self._handle_dump(self._cb_handleVODSpeedCtrl, opcode, data)
		headLen = struct.calcsize('!I')
		unpackedData = struct.unpack('!I', data[:headLen])
		playSpeed = unpackedData[0]
		service = self._session.nav.getCurrentService()
		pauseable = service.pause()
		if playSpeed > 2:
			playSpeed = 2
		if pauseable.setFastForward(playSpeed) == -1:
			pauseable.setFastForward(1)
			raise Exception("This stream is not support trick play.")
		return (0, "OK")

	def _cb_handleDVBAppVolUp(self, opcode, data):
		self._handle_dump(self._cb_handleDVBAppVolUp, opcode, data)
		vcm = VolumeControl.instance
		vcm.volUp()
		return (0, "OK")

	def _cb_handleDVBAppVolDown(self, opcode, data):
		self._handle_dump(self._cb_handleDVBAppVolDown, opcode, data)
		vcm = VolumeControl.instance
		vcm.volDown()
		return (0, "OK")

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
					self._curren_title = data
				except Exception, ErrMsg:
					if x in self._on_set_title_cb:
						self._on_set_title_cb.remove(x)
		return (0, "OK")

	def _cb_handleCloseHbbTVBrowser(self, opcode, data):
		self._timer_retry_open.stop()
		try:
			self._timer_retry_open.callback.remove(_cb_HbbTVRetryOpenURL)
		except: pass
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
			self._vod_uri = None
		return (0, "OK")

	def _cb_handleVODPlayerURI(self, opcode, data):
		self._vod_uri = None
		hl = struct.calcsize('!II')
		datas = struct.unpack('!II', data[:hl])
		uriLength = datas[1]
		vodUri = data[hl:hl+uriLength]
		self._handle_dump(self._cb_handleVODPlayerURI, opcode, vodUri)
		self._vod_uri = vodUri
		try:
			if vodUri.find('/zdf/') >= 0:
				tmpUri = MMSStreamURL().getLocationData(vodUri).strip()
				if not strIsEmpty(tmpUri):
					self._vod_uri = tmpUri
		except: pass
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
				print "Try to open vod [%d] : %s" % (ii, url)
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

from libshm import SimpleSharedMemory
_g_ssm_ = None
class HbbTVWindow(Screen, InfoBarNotifications):
	skin = """
		<screen name="HbbTVWindow" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="HbbTV Plugin">
		</screen>
		"""
	def __init__(self, session, url=None, cbf=None, useAIT=False, profile=0):
		self._session = session
		fbClass.getInstance().lock()
		eRCInput.getInstance().lock()

		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evUser+20: self._serviceForbiden,
			iPlayableService.evStart: self._serviceStarted,
			iPlayableService.evEOF: self._serviceEOF,
		})

		self._url = url
		self._use_ait = useAIT
		self._profile = profile
		self._cb_closed_func = cbf
		self.onLayoutFinish.append(self._layoutFinished)

		command_server = getCommandServer()
		if self._cb_set_page_title not in command_server.onSetPageTitleCB:
			command_server.onSetPageTitleCB.append(self._cb_set_page_title)

		if self._cb_close_window not in command_server.onHbbTVCloseCB:
			command_server.onHbbTVCloseCB.append(self._cb_close_window)

		self._closeTimer = eTimer()
		self._closeTimer.callback.append(self._do_close)

		self._currentServicePositionTimer = eTimer()
		self._currentServicePositionTimer.callback.append(self._cb_currentServicePosition)
		self._vodLength = 0

		global _g_ssm_
		self._ssm = _g_ssm_
		self._vod_length = 0

	def getVodPlayTime(self):
		try:
			service = self._session.nav.getCurrentService()
			seek = service and service.seek()
			l = seek.getLength()
			p = seek.getPlayPosition()
			if(not l[0] and not p[0]):
				return (p[1], l[1])
			return (90000,90000)
		except: pass
		return (-1,-1)

	def _cb_currentServicePosition(self):
		def getTimeString(t):
			t = time.localtime(t/90000)
			return "%2d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec)
		position,length = 0,0
		try:
			(position, length) = self.getVodPlayTime()
			self._vod_length = length
			if position == -1 and length == -1:
				raise Exception("Can't get play status")
			#print getTimeString(position), "/", getTimeString(length)
			self._ssm.setStatus(position, length, 1)
		except Exception, ErrMsg:
			print ErrMsg
			self._serviceEOF()

	def _serviceStarted(self):
		try:
			self._ssm.setStatus(0, 0, 0)
			self._currentServicePositionTimer.start(1000)
		except Exception, ErrMsg:
			print ErrMsg

	def _serviceEOF(self):
		self._currentServicePositionTimer.stop()

	def _layoutFinished(self):
		self.setTitle(_('HbbTV Plugin'))
		command_util = getCommandUtil()
		profile = self._profile
		(sid, onid, tsid, name, orgid) = getChannelInfos()
		params = struct.pack('!IIIIII', orgid, profile, sid, onid, tsid, len(name)) + name
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
		fbClass.getInstance().unlock()
		eRCInput.getInstance().unlock()
		self.close()

	def _serviceForbiden(self):
		global __gval__
		real_url = MMSStreamURL().getLocationData(__gval__.hbbtv_handelr.getUrl())
		print "Received URI :\n", real_url

		if real_url is not None:
			__gval__.hbbtv_handelr.doRetryOpen(real_url.strip())

	def _cb_set_page_title(self, title=None):
		print "page title :",title
		if title is None:
			return
		self.setTitle(title)

class HbbTVHelper(Screen, InfoBarNotifications):
	skin = """<screen name="HbbTVHelper" position="0,0" size="0,0" backgroundColor="transparent" flags="wfNoBorder" title=" "></screen>"""
	def __init__(self, session):
		global __gval__
		__gval__.hbbtv_handelr = HandlerHbbTV(session)
		__gval__.command_server = ServerFactory().doListenUnixTCP('/tmp/.sock.hbbtv.url', __gval__.hbbtv_handelr)

		self._restart_opera()

		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)
		self._session = session
		self._timer_infobar = eTimer()
		self._timer_infobar.callback.append(self._cb_registrate_infobar)
		self._timer_infobar.start(1000)

		self._excuted_browser = False
		self._profile = 0

		__gval__.command_util = BrowserCommandUtil()

		global _g_ssm_
		if _g_ssm_ is None:
			_g_ssm_ = SimpleSharedMemory()
			_g_ssm_.doConnect()

		self.__et = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evHBBTVInfo: self._cb_detectedAIT,
				iPlayableService.evUpdatedInfo: self._cb_updateInfo
			})
		self._applicationList = None

		self.mVuplusBox = False
		f = open("/etc/issue")
		issue = f.read()
		f.close()
		if(issue.startswith("Vuplus")):
			self.mVuplusBox = True

	def _cb_detectedAIT(self):
		name = self._cb_ready_for_ait()
		if name is not None and self.mVuplusBox:
			from Screens.InfoBarGenerics import gHbbTvApplication
			gHbbTvApplication.setApplicationName(str(name))

	def _cb_updateInfo(self):
		if not self._excuted_browser:
			command_util = getCommandUtil()
			command_util.sendCommand('OP_HBBTV_UNLOAD_AIT')
		if self.mVuplusBox:
			from Screens.InfoBarGenerics import gHbbTvApplication
			gHbbTvApplication.setApplicationName("")
		#self._applicationList = None

	def _cb_registrate_infobar(self):
		if InfoBar.instance:
			self._timer_infobar.stop()
			if self._cb_hbbtv_activated not in InfoBar.instance.onHBBTVActivation:
				InfoBar.instance.onHBBTVActivation.append(self._cb_hbbtv_activated)

	def _cb_ready_for_ait(self):
		setChannelInfo(None, None, None, None, None)

		service = self._session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			sid = info.getInfo(iServiceInformation.sSID)
			onid = info.getInfo(iServiceInformation.sONID)
			tsid = info.getInfo(iServiceInformation.sTSID)
			name = info.getName()
			if name is None:
				name = ""

			pmtid = info.getInfo(iServiceInformation.sPMTPID)
			demux = info.getInfoString(iServiceInformation.sLiveStreamDemuxId)

			from aitreader import eAITSectionReader
			reader = eAITSectionReader(demux, pmtid, sid)
			if reader.doOpen(info, self.mVuplusBox):
				reader.doParseApplications()
				reader.doDump()
			else:	print "no data!!"

			try:
				self._applicationList = reader.getApplicationList()
				if len(self._applicationList) > 0:
					orgid = int(self._applicationList[0]["orgid"])
					setChannelInfo(sid, onid, tsid, name, orgid)
					return self._applicationList[0]["name"]
			except: pass
		return None

	def _cb_hbbtv_activated(self, title=None, url=None):
		if not self._is_browser_running():
			message = _("HbbTV Browser was not running.\nPlease running browser before start HbbTV Application.")
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
			return
		service = self._session.nav.getCurrentlyPlayingServiceReference()
		setBeforeService(service)
		self._start_hbbtv_application(title, url)

	def _start_hbbtv_application(self, title, url):
		use_ait = False
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

		if isNeedRestart():
			self._restart_opera()
			time.sleep(2)
			setNeedRestart(False)

		for x in self._applicationList:
			control_code = int(x["control"])
			tmp_url = x["url"]
			if tmp_url == url and control_code == 1:
				use_ait = True
		self._excuted_browser = True
		self._session.open(HbbTVWindow, url, self._cb_closed_browser, use_ait, self._profile)

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

	def _restart_opera(self):
		global HBBTVAPP_PATH
		try:	os.system('%s/launcher restart'%(HBBTVAPP_PATH))
		except: pass

	def getStartHbbTVUrl(self):
		url, self._profile = None, 0
		if self._applicationList and len(self._applicationList) > 0:
			self._profile = self._applicationList[0]["profile"]
			url = self._applicationList[0]["url"]
		if url is None:
			service = self._session.nav.getCurrentService()
			info = service and service.info()
			url = info.getInfoString(iServiceInformation.sHBBTVUrl)
		return url

	def showApplicationSelectionBox(self):
		applications = []

		if self.getStartHbbTVUrl():
			for x in self._applicationList:
				applications.append((x["name"], x))
		else: applications.append((_("No detected HbbTV applications."), None))
		self._session.openWithCallback(self._application_selected, ChoiceBox, title=_("Please choose an HbbTV application."), list=applications)

	def _application_selected(self, selected):
		try:
			self._cb_hbbtv_activated(selected[1]["name"], selected[1]["url"])
		except Exception, ErrMsg: print ErrMsg

	def showBrowserConfigBox(self):
		start_stop_mode = []
		if self._is_browser_running():
			start_stop_mode.append((_('Stop'),'Stop'))
		else:	start_stop_mode.append((_('Start'),'Start'))
		self._session.openWithCallback(self._browser_config_selected, ChoiceBox, title=_("Please choose one."), list=start_stop_mode)

	def _browser_config_selected(self, selected):
		if selected is None:
			return
		try:
			mode = selected[1]
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

	def doChangeChannel(self, _sid, _tsid):
		root = eServiceReference(service_types_tv)
		if root is None:
			return False
		serviceList = eServiceCenter.getInstance().list(root)
		if serviceList is None:
			return False
		while True:
			service = serviceList.getNext()
			if service is None or not service.valid():
				break

			#1:0:19:2840:3FB:1:C00000:0:0:0:
			serviceRef = service.toString()
			if strIsEmpty(serviceRef):
				continue
			serviceRefItems = serviceRef.split(":")
			if len(serviceRefItems) < 5:
				continue

			sid	 = serviceRefItems[3]
			tsid = serviceRefItems[4]
			if sid == _sid and tsid == _tsid:
				self._session.nav.playService(eServiceReference(serviceRef))
				service = self._session.nav.getCurrentlyPlayingServiceReference()
				setBeforeService(service)
				return True
		return False

class OperaBrowserSetting:
	def __init__(self):
		self._settingFileName = '/usr/local/hbb-browser/home/setting.ini'
		self._start = None
		self._type = None
		self._read()
	def _read(self):
		f = open(self._settingFileName)
		for line in f.readlines():
			if line.startswith('start='):
				tmp = line[6:len(line)-1].split()
				if tmp[0] == "http://www.vuplus.com/":
					tmp[0] = "http://google.com/"
				self._start = tmp[0]
				if len(tmp) > 1:
					self._type = int(tmp[1])
				else:	self._type = 0
		f.close()
	def _write(self):
		tmpstr = []
		tmpstr.append('start=%s %d\n' % (self._start, self._type))
		f = open(self._settingFileName, 'w')
		f.writelines(tmpstr)
		f.close()
	def setData(self, start, types=0):
		self._start = start
		self._type = types
		self._write()
	def getData(self):
		return {
			'start':self._start,
			'type':self._type,
		}

class OperaBrowserPreferenceWindow(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="600,350" title="Preference">
			<widget name="url" position="5,0" size="590,100" valign="center" font="Regular;20" />
			<widget name="config" position="0,100" size="600,200" scrollbarMode="showOnDemand" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="310,310" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,310" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="310,310" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="150,310" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
		</screen>
		"""
	def __init__(self, session, currentUrl):
		self.session = session
		Screen.__init__(self, session)

		self.menulist = []
		ConfigListScreen.__init__(self, self.menulist)

		self["actions"] = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions"],
			{
				"red"	 : self.keyRed,
				"green"	 : self.keyGreen,
				"ok"	 : self.keyOK,
				"cancel" : self.keyRed
			}, prio=-2)
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["url"] = Label()

		self._currentPageUrl = currentUrl
		if self._currentPageUrl is None:
			self._currentPageUrl = ''
		self._startPageUrl = None

		self.makeMenuEntry()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Preference'))
		try:
			d = OperaBrowserSetting().getData()
			self._startPageUrl = d['start']
			#d['type']
		except: self._startPageUrl = 'http://google.com'
		self.updateStartPageUrl()

	def updateStartPageUrl(self):
		if self.menuItemStartpage.value == "startpage":
			self["url"].setText(self._startPageUrl)
		elif self.menuItemStartpage.value == "current":
			self["url"].setText(self._currentPageUrl)
		elif self.menuItemStartpage.value == "direct":
			self["url"].setText('')

	def keyGreen(self):
		url = self["url"].getText()
		if strIsEmpty(url):
			self.session.open(MessageBox, _('Invalid URL!!(Empty)\nPlease, Input to the URL.'), type=MessageBox.TYPE_INFO)
			return
		mode = 0
		if url.find('/usr/local/manual') > 0:
			mode = 1
		OperaBrowserSetting().setData(url, mode)
		self.close()

	def keyRed(self):
		self.close()

	def keyOK(self):
		def _cb_directInputUrl(data):
			if strIsEmpty(data):
				return
			self["url"].setText(data)
		if self.menuItemStartpage.value == "direct":
			self.session.openWithCallback(_cb_directInputUrl, VirtualKeyBoard, title=(_("Please enter URL here")), text='http://')

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.updateStartPageUrl()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.updateStartPageUrl()

	def makeMenuEntry(self):
		l = []
		l.append(("startpage", _("Start Page")))
		if not strIsEmpty(self._currentPageUrl):
			l.append(("current", _("Current Page")))
		l.append(("direct", _("Direct Input")))
		self.menuItemStartpage = ConfigSelection(default="startpage", choices=l)
		self.menuEntryStartpage = getConfigListEntry(_("Startpage"), self.menuItemStartpage)
		self.resetMenuList()

	def resetMenuList(self):
		self.menulist = []
		self.menulist.append(self.menuEntryStartpage)

		self["config"].list = self.menulist
		self["config"].l.setList(self.menulist)

class BookmarkEditWindow(ConfigListScreen, Screen):
	CATEGORY,BOOKMARK = 0,1
	skin = """
		<screen position="center,center" size="600,140" title="Bookmark Edit">
			<widget name="config" position="0,0" size="600,100" scrollbarMode="showOnDemand" />

			<ePixmap pixmap="skin_default/buttons/red.png" position="310,100" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="150,100" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="310,100" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="150,100" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />

			<widget name="VKeyIcon" pixmap="skin_default/buttons/key_text.png" position="0,100" zPosition="10" size="35,25" transparent="1" alphatest="on" />

		</screen>
		"""
	def __init__(self, session, _mode, _type, _data, _bm):
		self.mMode = _mode
		self.mType = _type
		self.mData = _data
		self.mSession = session
		self.mBookmarkManager = _bm

		if _data is not None:
			print _data.mId

		Screen.__init__(self, session)

		self.menulist = []
		ConfigListScreen.__init__(self, self.menulist)

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions",],
			{
				"ok"	 : self.keyGreen,
				"green"	 : self.keyGreen,
				"red"	 : self.keyRed,
				"cancel" : self.keyRed,
			}, prio=-2)

		self["VKeyIcon"] = Pixmap()
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self.menuItemTitle = None
		self.menuItemUrl   = None
		self.menuItemName  = None

		self.menuEntryName = None
		self.menuEntryTitle = None
		self.menuEntryUrl = None

		self.makeConfigList()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Bookmark') + ' ' + self.mMode)

	def selectedItem(self):
		currentPosition = self["config"].getCurrent()
		if self.mType == BookmarkEditWindow.CATEGORY:
			return (_("Name"), self.menuItemName)
		else:
			if currentPosition == self.menuEntryTitle:
				return (_("Title"), self.menuItemTitle)
			elif currentPosition == self.menuEntryUrl:
				return (_("Url"), self.menuItemUrl)
		return None

	def showMessageBox(self, text):
		msg = _("Invalid ") + text + _("!!(Empty)\nPlease, Input to the") + " " + text + "."
		self.mSession.openWithCallback(self.showVKeyWindow, MessageBox, msg, MessageBox.TYPE_INFO)
		return False

	def showVKeyWindow(self, data=None):
		itemTitle = ""
		itemValue = ""
		selected = self.selectedItem()
		if selected is not None:
			itemValue = selected[1].value
			if strIsEmpty(itemValue):
				itemValue = ""
			itemTitle = selected[0]

		self.session.openWithCallback(self.cbVKeyWindow, VirtualKeyBoard, title=itemTitle, text=itemValue)

	def cbVKeyWindow(self, data=None):
		if data is not None:
			selected = self.selectedItem()
			if selected is not None:
				selected[1].setValue(data)

	def saveData(self):
		if self.mType == BookmarkEditWindow.CATEGORY:
			if self.mMode == _('Add'):
				categoryName = self.menuItemName.value
				if strIsEmpty(categoryName):
					return self.showMessageBox(_("Category Name"))
				self.mBookmarkManager.addCategory(categoryName)
			else:
				if strIsEmpty(self.menuItemName.value):
					return self.showMessageBox(_("Category Name"))
				self.mData.mName = self.menuItemName.value
				self.mBookmarkManager.updateCategory(self.mData)
		else:
			if self.mMode == _('Add'):
				bookmarkTitle = self.menuItemTitle.value
				bookmarkUrl = self.menuItemUrl.value
				if strIsEmpty(bookmarkTitle):
					self["config"].setCurrentIndex(0)
					return self.showMessageBox(_("Bookmark Title"))
				if strIsEmpty(bookmarkUrl):
					self["config"].setCurrentIndex(1)
					return self.showMessageBox(_("Bookmark URL"))
				self.mBookmarkManager.addBookmark(bookmarkTitle, bookmarkUrl, self.mData.mParent, 0)
			else:
				if strIsEmpty(self.menuItemTitle.value):
					self["config"].setCurrentIndex(0)
					return self.showMessageBox(_("Bookmark Title"))
				if strIsEmpty(self.menuItemUrl.value):
					self["config"].setCurrentIndex(1)
					return self.showMessageBox(_("Bookmark URL"))
				self.mData.mTitle = self.menuItemTitle.value
				self.mData.mUrl = self.menuItemUrl.value
				self.mBookmarkManager.updateBookmark(self.mData)
		return True

	def keyGreen(self):
		if not self.saveData():
			return
		self.close(True)
	def keyRed(self):
		self.close(False)
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
	def keyRight(self):
		ConfigListScreen.keyRight(self)
	def makeConfigList(self):
		self.menulist = []

		if self.mType == BookmarkEditWindow.CATEGORY:
			self.menuItemName = ConfigText(default=self.mData.mName, visible_width=65, fixed_size=False)

			self.menuEntryName = getConfigListEntry(_("Name"), self.menuItemName)

			self.menulist.append(self.menuEntryName)
		else:
			self.menuItemTitle = ConfigText(default=self.mData.mTitle, visible_width=65, fixed_size=False)
			self.menuItemUrl   = ConfigText(default=self.mData.mUrl, visible_width=65, fixed_size=False)

			self.menuEntryTitle = getConfigListEntry(_("Title"), self.menuItemTitle)
			self.menuEntryUrl = getConfigListEntry(_("Url"), self.menuItemUrl)

			self.menulist.append(self.menuEntryTitle)
			self.menulist.append(self.menuEntryUrl)

		self["config"].list = self.menulist
		self["config"].l.setList(self.menulist)

class OperaBrowserBookmarkWindow(Screen):
	skin = """
		<screen name="HbbTVBrowserBookmarkWindow" position="center,center" size="600,400" title="Bookmark" >
			<widget name="bookmarklist" position="0,0" size="600,200" zPosition="10" scrollbarMode="showOnDemand" />

			<ePixmap pixmap="skin_default/buttons/key_0.png" position="556,330" size="35,30" alphatest="on" />
			<widget source="key_0" render="Label" position="258,330" zPosition="1" size="300,30" font="Regular;20" halign="right" valign="center"/>

			<ePixmap pixmap="skin_default/buttons/red.png" position="5,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,360" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="450,360" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="450,360" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />
		</screen>
		"""

	def __init__(self, _session, _url=None, _title=None):
		self.mUrl = _url
		self.mTitle = _title
		self.mBookmarkManager = BookmarkManager.getInstance()
		self.mSession = _session
		Screen.__init__(self, _session)
		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions","ColorActions", "NumberActions"],
			{
				"ok"	: self.keyOK,
				"cancel": self.keyCancel,
				"red"	: self.keyRed,
				"green" : self.keyGreen,
				"yellow": self.keyYellow,
				"blue"	: self.keyBlue,
				"0" : self.keyNumber,
			}, prio=-2)

		self["key_red"]	   = StaticText(_("Exit"))
		self["key_green"]  = StaticText(_("Add"))
		self["key_yellow"] = StaticText(_("Edit"))
		self["key_blue"]   = StaticText(_("Delete"))
		self["key_0"]	   = StaticText(_("Set as Startpage"))

		self.mBookmarkList = self.setBookmarkList()
		self["bookmarklist"] = MenuList(self.mBookmarkList)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Bookmark'))

	def setBookmarkList(self):
		l = []
		#self.mBookmarkManager.dump()
		cd = self.mBookmarkManager.getBookmarkRoot()
		for ck in cd.iterkeys():
			l.append(('# ' + cd[ck].mName, cd[ck]))
			bd = cd[ck].mBookmarks
			for bk in bd.iterkeys():
				l.append(('    - ' + bd[bk].mTitle, bd[bk]))
		return l
	def updateBookmarkList(self):
		self.mBookmarkList = self.setBookmarkList()
		self["bookmarklist"].setList(self.mBookmarkList)
	def cbEditWindow(self, ret=False):
		if not ret:
			return
		self.updateBookmarkList()
	def getParentCategory(self):
		idx = self["bookmarklist"].getSelectedIndex()
		try:
			while idx >= 0:
				data = self.mBookmarkList[idx][0].strip()
				if data[0] == '#':
					return self.mBookmarkList[idx][1]
				idx -= 1
		except: pass
		return None
	def isCategoryItem(self):
		try:
			head = self["bookmarklist"].getCurrent()[0].strip()
			if head[0] == '#':
				return True
		except: pass
		return False
	def keyNumber(self):
		data = self["bookmarklist"].getCurrent()[1]
		if strIsEmpty(data.mUrl):
			msg = _("Invalid URL. Please check again!!")
			self.mSession.open(MessageBox, msg, MessageBox.TYPE_INFO)
			return
		def cbSetStartpage(ret=None):
			if ret is None: return
			if ret:
				data = self["bookmarklist"].getCurrent()[1]
				OperaBrowserSetting().setData(data.mUrl, data.mType)
		msg = _("Do you want to set selected url to the Startpage?")
		self.mSession.openWithCallback(cbSetStartpage, MessageBox, msg, MessageBox.TYPE_YESNO, default=True)

	def keyGreen(self):
		def cbGreen(data):
			if data is None:
				return
			if data[1] == 1:
				parent = self.getParentCategory()
				if parent is None:
					return
				if strIsEmpty(self.mTitle):
					return
				retAdd = self.mBookmarkManager.addBookmark(self.mTitle, self.mUrl, parent.mId, 0)
				if not retAdd:
					msg = _("Current page is already exist.")
					self.mSession.open(MessageBox, msg, MessageBox.TYPE_INFO)
				self.cbEditWindow(True)
			elif data[1] == 2:
				parent = self.getParentCategory()
				if parent is None:
					return
				b = BookmarkData(0, '', '', parent.mId, 0)
				self.mSession.openWithCallback(self.cbEditWindow, BookmarkEditWindow, _('Add'), BookmarkEditWindow.BOOKMARK, b, self.mBookmarkManager)
			elif data[1] == 3:
				c = CategoryData(0, '')
				self.mSession.openWithCallback(self.cbEditWindow, BookmarkEditWindow, _('Add'), BookmarkEditWindow.CATEGORY, c, self.mBookmarkManager)
		if strIsEmpty(self.mUrl):
			l = [(_('Direct Input(Bookmark)'),2,), (_('Direct Input(Category)'),3,)]
		else:	l = [(_('Currentpage(Bookmark)'),1,), (_('Direct Input(Bookmark)'),2,), (_('Direct Input(Category)'),3,)]
		self.mSession.openWithCallback(cbGreen, ChoiceBox, title=_("Please choose."), list=l)
	def keyYellow(self):
		data = self["bookmarklist"].getCurrent()[1]
		if self.isCategoryItem():
			self.mSession.openWithCallback(self.cbEditWindow, BookmarkEditWindow, _('Edit'), BookmarkEditWindow.CATEGORY, data, self.mBookmarkManager)
		else:	self.mSession.openWithCallback(self.cbEditWindow, BookmarkEditWindow, _('Edit'), BookmarkEditWindow.BOOKMARK, data, self.mBookmarkManager)
	def keyBlue(self):
		def cbBlue(ret=None):
			if not ret: return
			data = self["bookmarklist"].getCurrent()[1]
			if self.isCategoryItem():
				self.mBookmarkManager.deleteCategory(data.mId)
			else:	self.mBookmarkManager.deleteBookmark(data.mId)
			self.updateBookmarkList()
		if self.isCategoryItem():
			msg = _("Do you want to delete the category and the bookmarks?")
		else:	msg = _("Do you want to delete the bookmark?")
		self.mSession.openWithCallback(cbBlue, MessageBox, msg, MessageBox.TYPE_YESNO, default=True)
	def keyOK(self):
		if self.isCategoryItem(): return

		data = self["bookmarklist"].getCurrent()[1]
		url = data.mUrl.strip()
		if len(url) == 0:
			self.session.open(MessageBox, _("Can't open selected bookmark.\n   - URL data is empty!!"), type=MessageBox.TYPE_INFO)
			return
		mode = data.mType
		if mode:
			lang = language.getLanguage()
			if lang == 'ru_RU' and os.path.exists('/usr/local/manual/ru_RU'):
				url = '/usr/local/manual/ru_RU/main.html'
			elif lang == 'de_DE' and os.path.exists('/usr/local/manual/de_DE'):
				url = '/usr/local/manual/de_DE/main.html'
		self.close((url, mode))
	def keyRed(self):
		self.keyCancel()
	def keyCancel(self):
		self.close()

class BrowserHelpWindow(Screen, HelpableScreen):
	MODE_GLOBAL,MODE_KEYBOARD,MODE_MOUSE = 1,2,3
	skin = """
		<screen name="BrowserHelpWindow" position="center,center" size="600,40" title="Browser Help" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="450,0" size="140,40" alphatest="on" />

			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_blue" render="Label" position="450,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" foregroundColor="#ffffff" transparent="1" />
		</screen>
		"""
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self["key_red"]	   = StaticText(_("Exit"))
		self["key_green"]  = StaticText(_("Global"))
		self["key_yellow"] = StaticText(_("Mouse"))
		self["key_blue"]   = StaticText(_("Keyboard"))

		self["actions"] = ActionMap(["DirectionActions", "OkCancelActions","ColorActions"],
			{
				"ok"	: self.keyRed,
				"cancel": self.keyRed,
				"red"	: self.keyRed,
				"green" : self.keyGreen,
				"yellow": self.keyYellow,
				"blue"	: self.keyBlue,
			}, prio=-2)

		self.showHelpTimer = eTimer()
		self.showHelpTimer.callback.append(self.cbShowHelpTimerClosed)
		self.showHelpTimer.start(500)

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_('Browser Help'))

	def cbShowHelpTimerClosed(self):
		self.showHelpTimer.stop()
		self.setHelpModeActions(self.MODE_GLOBAL)

	def setHelpModeActions(self, _mode=0):
		self.helpList = []
		if _mode == self.MODE_GLOBAL:
			self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
				{
					"cancel" : (self.keyPass, _("Exit the Opera browser.")),
				})
			self["MenuActions"] = HelpableActionMap(self, "MenuActions",
				{
					"menu" : (self.keyPass, _("Show the menu window.")),
				})
			self["ColorActions"] = HelpableActionMap(self, "ColorActions",
				{
					"green"	 : (self.keyPass, _("Enter key")),
					"yellow" : (self.keyPass, _("Show the virtual keyboard window.")),
					"blue"	 : (self.keyPass, _("Backspace key")),
				})
			self["EPGSelectActions"] = HelpableActionMap(self, "EPGSelectActions",
				{
					"info" : (self.keyPass, _("Switch to keyboard/mouse mode.")),
				})

		elif _mode == self.MODE_MOUSE:
			self["DirectionActions"] = HelpableActionMap(self, "DirectionActions",
				{
					"up"	: (self.keyPass, _("Move the mouse pointer up.")),
					"down"	: (self.keyPass, _("Move the mouse pointer down.")),
					"left"	: (self.keyPass, _("Move the mouse pointer left.")),
					"right" : (self.keyPass, _("Move the mouse pointer right.")),
				})
			self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
				{
					"ok" : (self.keyPass, _("Left mouse button")),
				})
			self["EPGSelectActions"] = HelpableActionMap(self, "EPGSelectActions",
				{
					"nextBouquet" : (self.keyPass, _("Right mouse button")),
					"nextService" : (self.keyPass, _("Left key")),
					"prevService" : (self.keyPass, _("Right key")),
				})
		elif _mode == self.MODE_KEYBOARD:
			self["DirectionActions"] = HelpableActionMap(self, "DirectionActions",
				{
					"up"	: (self.keyPass, _("Up key")),
					"down"	: (self.keyPass, _("Down key")),
					"left"	: (self.keyPass, _("Left key")),
					"right" : (self.keyPass, _("Right key")),
				})
			self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
				{
					"ok" : (self.keyPass, _("Enter key")),
				})
			self["EPGSelectActions"] = HelpableActionMap(self, "EPGSelectActions",
				{
					"nextBouquet" : (self.keyPass, _("PageUp key")),
					"prevBouquet" : (self.keyPass, _("PageDown key")),
					"nextService" : (self.keyPass, _("Go to previous page.")),
					"prevService" : (self.keyPass, _("Go to next page.")),
				})

		if _mode > 0:
			self.showHelp()

	def keyPass(self):
		pass

	def keyRed(self):
		self.close()
	def keyGreen(self):
		self.setHelpModeActions(self.MODE_GLOBAL)
	def keyYellow(self):
		self.setHelpModeActions(self.MODE_MOUSE)
	def keyBlue(self):
		self.setHelpModeActions(self.MODE_KEYBOARD)

class OperaBrowser(Screen):
	MENUBAR_ITEM_WIDTH = 150
	MENUBAR_ITEM_HEIGHT = 30
	SUBMENULIST_WIDTH = 200
	SUBMENULIST_HEIGHT = 25
	SUBMENULIST_NEXT = 2

	skin = """
		<screen name="Opera Browser" position="0,0" size="1280,720" backgroundColor="transparent" flags="wfNoBorder" title="Opera Browser">
			<widget name="topArea" zPosition="-1" position="0,0" size="1280,60" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" />
			<widget name="menuitemFile" position="30,20" size="150,30" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" foregroundColors="#9f1313,#a08500" />
			<widget name="menuitemTool" position="180,20" size="150,30" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" foregroundColors="#9f1313,#a08500" />
			<widget name="menuitemHelp" position="330,20" size="150,30" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" foregroundColors="#9f1313,#a08500" />
			<widget name="menulist" position="50,%d" size="%d,150" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
			<widget name="submenulist" position="%d,%d" size="%d,150" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
			<widget name="bottomArea" position="0,640" size="1280,80" font="Regular;20" valign="center" halign="center" backgroundColor="#000000" />
		</screen>
		""" % (MENUBAR_ITEM_HEIGHT+30, SUBMENULIST_WIDTH, SUBMENULIST_WIDTH+50+SUBMENULIST_NEXT, MENUBAR_ITEM_HEIGHT+30, SUBMENULIST_WIDTH)# modify menu

	MENUITEMS_LIST =[
		[(_('Open Startpage'), None), (_('Open URL'), None), (_('Start/Stop'),None), (_('Exit'), None)],
		[(_('Bookmark'), None), (_('Preference'), None)],
		[(_('About'), None), (_('Help'), None)]
	]
	def __init__(self, session, url=None):
		Screen.__init__(self, session)
		self["actions"] = ActionMap(["DirectionActions", "MenuActions", "OkCancelActions"],
			{
				"cancel" : self.keyCancel,
				"ok" : self.keyOK,
				"left" : self.keyLeft,
				"right" : self.keyRight,
				"up" : self.keyUp,
				"down" : self.keyDown,
				"menu" : self.keyMenu
			}, -2)

		self._terminatedBrowser = True
		self._enableKeyEvent = True
		self._currentPageUrl = None
		self._currentPageTitle = None
		self.menubarCurrentIndex = 0
		self.lvMenuItems = []
		self.lvSubMenuItems = []

		self["topArea"] = Label()
		self["bottomArea"] = Label()

		self["menuitemFile"] = MultiColorLabel()# modify menu
		self["menuitemTool"] = MultiColorLabel()
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

		self.paramUrl = url

	def enableRCMouse(self, mode): #mode=[0|1]|[False|True]
		rcmouse_path = "/proc/stb/fp/mouse"
		if os.path.exists(rcmouse_path):
			os.system("echo %d > %s" % (mode, rcmouse_path))

	def layoutFinished(self):
		self["menuitemFile"].setText(_("File"))# modify menu
		self["menuitemTool"].setText(_("Tools"))
		self["menuitemHelp"].setText(_("Help"))

		self["menulist"].hide()
		self["submenulist"].hide()

		self["bottomArea"].setText(_("Opera Web Browser Plugin v1.0"))
		self.setTitle(_("BrowserMain"))
		self.selectMenuitem()

		if self.paramUrl is not None:
			self.keyMenu()
			self.cbUrlText(self.paramUrl, 1)

	def selectMenuitem(self):
		tmp = [self["menuitemFile"], self["menuitemTool"], self["menuitemHelp"]]# modify menu
		self["menuitemFile"].setForegroundColorNum(0)
		self["menuitemTool"].setForegroundColorNum(0)
		self["menuitemHelp"].setForegroundColorNum(0)
		tmp[self.menubarCurrentIndex].setForegroundColorNum(1)

	def popupCloseAll(self):
		self.keyLeft()
		self.keyLeft()
		self.keyUp()
		self.keyCancel()

	def setListOnView(self):
		l = self.MENUITEMS_LIST[self.menubarCurrentIndex]
		if not self._terminatedBrowser and self.menubarCurrentIndex == 0: # running
			l = [(_('Return'), None)]
		self.lvMenuItems = l #self.MENUITEMS_LIST[self.menubarCurrentIndex]
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
		self._on_setPageTitle(_('Opera Browser'))
		self.enableRCMouse(False)
		self.toggleMainScreen()
		fbClass.getInstance().unlock()
		eRCInput.getInstance().unlock()
		self._terminatedBrowser = True
		self._enableKeyEvent = True
		#if not self.toggleListViewFlag:
		#	self.keyDown()
		self._currentPageUrl = ''
		if self.paramUrl is not None:
			self.keyCancel()
		else:
			self.keyRight()
			self.keyLeft()

	def _on_setPageTitle(self, title=None):
		print "Title :",title
		if title is None:
			return
		self.setTitle(title)

	def cbUrlText(self, data=None, mode=0):
		print "Inputed Url :", data, mode
		if strIsEmpty(data):
			return
		#self.hideSubmenu()
		command_server = getCommandServer()
		if self._on_setPageTitle not in command_server.onSetPageTitleCB:
			command_server.onSetPageTitleCB.append(self._on_setPageTitle)
		if self._on_close_window not in command_server.onHbbTVCloseCB:
			command_server.onHbbTVCloseCB.append(self._on_close_window)
		self.toggleMainScreen()
		self.enableRCMouse(True)
		fbClass.getInstance().lock()
		eRCInput.getInstance().lock()
		command_util = getCommandUtil()
		command_util.sendCommand('OP_BROWSER_OPEN_URL', data, mode)
		self._terminatedBrowser = False
		self._enableKeyEvent = False

	def _on_close_window(self):
		self._onCloseTimer.start(1000)

	def _cb_bookmarkWindowClosed(self, data=None):
		if data is None:
			return
		(url, mode) = data
		self.cbUrlText(url, mode)

	def _cmd_on_OpenUrl(self):
		global _g_helper
		if not _g_helper._is_browser_running():
			message = _("Opera Browser was not running.\nPlease running browser using [File]>[Start/Stop] menu.")
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
			return
		self.session.openWithCallback(self.cbUrlText, VirtualKeyBoard, title=(_("Please enter URL here")), text='http://')
	def _cmd_on_About(self):
		self.session.open(MessageBox, _('Opera Web Browser Plugin v1.0'), type=MessageBox.TYPE_INFO)
	def _cmd_on_Exit(self):
		self.close()
	def _cmd_on_StartStop(self):
		global _g_helper
		if _g_helper is None:
			return
		_g_helper.showBrowserConfigBox()
	def _cmd_on_Bookmark(self):
		url = self._currentPageUrl
		if url is None:
			url = ''
		title = self._currentPageTitle
		if title is None:
			title = ''
		self.session.openWithCallback(self._cb_bookmarkWindowClosed, OperaBrowserBookmarkWindow, url, title)
	def _cmd_on_Preference(self):
		url = self._currentPageUrl
		if url is None:
			url = ''
		self.session.open(OperaBrowserPreferenceWindow, url)
	def _cmd_on_OpenStartpage(self):
		global _g_helper
		if not _g_helper._is_browser_running():
			message = _("Opera Browser was not running.\nPlease running browser using [File]>[Start/Stop] menu.")
			self.session.open(MessageBox, message, MessageBox.TYPE_INFO)
			return
		mode = 0
		start = 'http://google.com'
		try:
			d = OperaBrowserSetting().getData()
			start = d['start']
			mode = d['type']
		except: pass
		self.cbUrlText(start, mode)
	def _cmd_on_ReturnToBrowser(self):
		self.keyCancel()

	def _cmd_on_Help(self):
		self.session.open(BrowserHelpWindow)

	def doCommand(self, command):
		# modify menu
		cmd_map = {}
		cmd_map[_('Exit')] = self._cmd_on_Exit
		cmd_map[_('Help')] = self._cmd_on_Help
		cmd_map[_('About')] = self._cmd_on_About
		cmd_map[_('Open URL')] = self._cmd_on_OpenUrl
		cmd_map[_('Start/Stop')] = self._cmd_on_StartStop
		cmd_map[_('Bookmark')] = self._cmd_on_Bookmark
		cmd_map[_('Preference')] = self._cmd_on_Preference
		cmd_map[_('Return')] = self._cmd_on_ReturnToBrowser
		cmd_map[_('Open Startpage')] = self._cmd_on_OpenStartpage
		try:
			cmd_map[command]()
		except Exception, ErrMsg: print ErrMsg

	def keyOK(self):
		if not self.toggleListViewFlag:
			self.keyDown()
			return
		if self.currentListView.getCurrent()[1] is None:
			self.doCommand(self.currentListView.getCurrent()[0])
			#self.session.open(MessageBox, _(self.currentListView.getCurrent()[0]), type=MessageBox.TYPE_INFO)
			return
		self.keyRight()

	def updateSelectedMenuitem(self, status):
		if self.menubarCurrentIndex == 0 and status < 0:
			self.menubarCurrentIndex = 2 # modify menu
		elif self.menubarCurrentIndex == 2 and status > 0: # modify menu
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
		#if self.currentListView.getSelectedIndex():
		self.currentListView.pageUp()
		self.keyUp()
		self.keyLeft()
		self.keyDown()

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
			self.currentListView.move(self.MENUBAR_ITEM_WIDTH*self.menubarCurrentIndex + self.SUBMENULIST_WIDTH+self.SUBMENULIST_NEXT + 50, self.MENUBAR_ITEM_HEIGHT+30+(parentSelectedIndex*self.SUBMENULIST_HEIGHT))
			self.toggleSubListView()
			return
		self.currentListView.pageUp()
		self.keyUp()
		self.keyRight()
		self.keyDown()

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
		if not self._terminatedBrowser:
			#self._session.openWithCallback(self._cb_virtualKeyboardClosed, VirtualKeyBoard, title=("Please enter URL here"), text="")
			fbClass.getInstance().lock()
			eRCInput.getInstance().lock()
			if self.toggleListViewFlag:
				self.toggleMainScreen()
			self._currentPageUrl   = None
			self._currentPageTitle = None
			command_util = getCommandUtil()
			command_util.sendCommand('OP_BROWSER_MENU_RES')
			return
		self.close()

	def keyMenu(self):
		self.toggleMainScreen()

	def setCurrentPageUrl(self, url, title=None):
		self._currentPageUrl = url
		if title is None:
			idx = len(url)
			if idx > 10: idx = 10
			title = url[:idx]
		self._currentPageTitle = title
		print self._currentPageUrl
		self.toggleMainScreen()
		self.hideSubmenu()
		self.keyDown()

	def hideSubmenu(self):
		self.currentListView.pageUp()
		self.keyUp()

def auto_start_main(reason, **kwargs):
	if reason:
		try:
			command_server = getCommandServer()
			command_server.stop()
		except:
			pass

from  Screens.HelpMenu import HelpableScreen
def session_start_main(session, reason, **kwargs):
	fbClass.getInstance().unlock()
	eRCInput.getInstance().unlock()
	global _g_helper
	_g_helper = session.open(HbbTVHelper)

	HelpableScreen.__init__ = HelpableScreen__init__
	HelpableScreen.session = session

def HelpableScreen__init__(self):
	if isinstance(self, HelpableScreen):
		HelpableScreen.showManual = showManual

		self["helpActions"] = ActionMap(["HelpbuttonActions"],
			{
				"help_b" : self.showHelp,
				"help_l" : self.showManual,
			}, -2)

_g_clearBrowserDataTimer = eTimer()
def showManual(self):
	if not os.path.exists('/usr/local/manual'):
		return

	url = 'file:///usr/local/manual/main.html'
	lang = language.getLanguage()
	if lang == 'ru_RU' and os.path.exists('/usr/local/manual/ru_RU'):
		url = 'file:///usr/local/manual/ru_RU/main.html'
	elif lang == 'de_DE' and os.path.exists('/usr/local/manual/de_DE'):
		url = 'file:///usr/local/manual/de_DE/main.html'

	def _do_clean():
		_g_clearBrowserDataTimer.stop()
		try:	_g_clearBrowserDataTimer.callback.remove(_do_clean)
		except: pass
		setPluginBrowser(None)

	def clearBrowserData():
		_g_clearBrowserDataTimer.callback.append(_do_clean)
		_g_clearBrowserDataTimer.start(50)
	setPluginBrowser(self.session.openWithCallback(clearBrowserData, OperaBrowser, url))

def plugin_start_main(session, **kwargs):
	#session.open(OperaBrowser)
	def _do_clean():
		_g_clearBrowserDataTimer.stop()
		try:	_g_clearBrowserDataTimer.callback.remove(_do_clean)
		except: pass
		setPluginBrowser(None)
	def clearBrowserData():
		_g_clearBrowserDataTimer.callback.append(_do_clean)
		_g_clearBrowserDataTimer.start(50)
	setPluginBrowser(session.openWithCallback(clearBrowserData, OperaBrowser))

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
	l = []
	l.append(PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, needsRestart=True, fnc=auto_start_main))
	if not config.misc.firstrun.getValue():
		l.append(PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, needsRestart=True, fnc=session_start_main, weight=-10))
	l.append(PluginDescriptor(name=_("HbbTV Applications"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=True, fnc=plugin_extension_start_application))
	l.append(PluginDescriptor(name=_("Browser Start/Stop"), where=PluginDescriptor.WHERE_EXTENSIONSMENU, needsRestart=True, fnc=plugin_extension_browser_config))
	l.append(PluginDescriptor(name=_("Web Browser"), description=_("start opera web browser"), where=PluginDescriptor.WHERE_PLUGINMENU, needsRestart=True, fnc=plugin_start_main))

	return l

