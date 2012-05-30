from Plugins.Plugin import PluginDescriptor

import os
from xml.etree.cElementTree import fromstring, ElementTree

from enigma import gFont, eTimer, eConsoleAppContainer, ePicLoad, loadPNG, getDesktop, eServiceReference, iPlayableService, eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InfoBarGenerics import InfoBarNotifications

from Components.Button import Button
from Components.Label import Label
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.config import config, ConfigSelection, getConfigListEntry, ConfigText, ConfigDirectory, ConfigYesNo, ConfigSelection
from Components.FileList import FileList, FileEntryComponent
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap, MovingPixmap
from Components.AVSwitch import AVSwitch
from Components.ServiceEventTracker import ServiceEventTracker

from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS

PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/StreamTV")

class StreamTVPlayer(Screen, InfoBarNotifications):
	skin = 	"""
		<screen name="StreamTVPlayer" flags="wfNoBorder" position="0,570" size="1280,190" title="StreamTV Player" backgroundColor="#41000000" >
			<ePixmap position="80,25" size="117,72" pixmap="%s/channel_background.png" zPosition="-1" transparent="1" alphatest="blend" />
			<widget name="channel_icon" position="121,43" zPosition="10" size="35,35" backgroundColor="#41000000" />
			<widget name="channel_name" position="250,20" size="650,40" font="Regular;36" halign="left" valign="center" foregroundColor="#ffffff" backgroundColor="#41000000" />
			<widget name="channel_uri" position="250,70" size="950,60" font="Regular;22" halign="left" valign="top" foregroundColor="#ffffff" backgroundColor="#41000000" />
			<widget source="session.CurrentService" render="Label" position="805,20" size="300,40" font="Regular;30" halign="right" valign="center" foregroundColor="#f4df8d" backgroundColor="#41000000" transparent="1" >
				<convert type="ServicePosition">Position</convert>
			</widget>
		</screen>
		""" % (PLUGIN_PATH)

	PLAYER_IDLE	= 0
	PLAYER_PLAYING 	= 1
	PLAYER_PAUSED 	= 2
	def __init__(self, session, service, cbServiceCommand, chName, chURL, chIcon):
		Screen.__init__(self, session)
		InfoBarNotifications.__init__(self)

		isEmpty = lambda x: x is None or len(x)==0 or x == 'None'
		if isEmpty(chName): chName = 'Unknown'
		if isEmpty(chURL):  chURL  = 'Unknown'
		if isEmpty(chIcon): chIcon = 'default.png'
		chIcon = '%s/icons/%s'%(PLUGIN_PATH,chIcon)
		self.session = session
		self.service = service
		self.cbServiceCommand = cbServiceCommand
		self["actions"] = ActionMap(["OkCancelActions", "InfobarSeekActions", "MediaPlayerActions", "MovieSelectionActions"], {
			"ok": self.doInfoAction,
			"cancel": self.doExit,
			"stop": self.doExit,
			"playpauseService": self.playpauseService,
		}, -2)

		self.__event_tracker = ServiceEventTracker(screen = self, eventmap = {
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

		self['channel_icon'] = Pixmap()
		self['channel_name'] = Label(chName)
		self['channel_uri']  = Label(chURL)

		self.picload = ePicLoad()
		self.scale   = AVSwitch().getFramebufferScale()
		self.picload.PictureData.get().append(self.cbDrawChannelIcon)
		print self.scale[0]
		print self.scale[1]
		self.picload.setPara((35, 35, self.scale[0], self.scale[1], False, 0, "#00000000"))
		self.picload.startDecode(chIcon)

		self.bypassExit = False
		self.cbServiceCommand(('docommand',self.doCommand))

	def doCommand(self, cmd):
		if cmd == 'bypass_exit':
			self.bypassExit = True
			
	def cbDrawChannelIcon(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr != None:
			self["channel_icon"].instance.setPixmap(ptr.__deref__())
			self["channel_icon"].show()

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
		if self.bypassExit:
			return
		self.doExit()

	def __setHideTimer(self):
		self.hidetimer.start(5000)

	def doExit(self):
		list = ((_("Yes"), "y"), (_("No"), "n"),)
		self.session.openWithCallback(self.cbDoExit, ChoiceBox, title=_("Stop playing this stream?"), list=list)

	def cbDoExit(self, answer):
		answer = answer and answer[1]
		if answer == "y":
			self.cbServiceCommand()
			self.close()

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
			self.hidetimer.stop()
			self.hide()
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

class StreamURIParser:
	def __init__(self, xml):
		self.xml = xml

	def parseStreamList(self):
		tvlist = []
		tree = ElementTree()
		tree.parse(self.xml)

		for iptv in tree.findall('iptv'):
			n = str(iptv.findtext('name'))
			i = str(iptv.findtext('icon'))
			u = str(iptv.findtext('uri'))
			t = str(iptv.findtext('type'))
			tvlist.append({'name':n, 'icon':i, 'type':t, 'uri':self.parseStreamURI(u)})
		return tvlist

	def parseStreamURI(self, uri):
		uriInfo = {}
		splitedURI = uri.split()
		uriInfo['URL'] = splitedURI[0]
		for x in splitedURI[1:]:
			i = x.find('=')
			uriInfo[x[:i].upper()] = str(x[i+1:])
		return uriInfo

def streamListEntry(entry):
	#print entry
	uriInfo = entry[1].get('uri')
	return [entry,
		(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, 5, 1, 35, 35, loadPNG('%s/icons/%s' % (PLUGIN_PATH, str(entry[1].get('icon'))) )),
		(eListboxPythonMultiContent.TYPE_TEXT,45,7,200,37,0,RT_HALIGN_LEFT,entry[0]),
		(eListboxPythonMultiContent.TYPE_TEXT,250,7,310,37,1,RT_HALIGN_LEFT,str(uriInfo.get('URL')))
	] 

class StreamTVList(Screen):
	skin = 	"""
		<screen name="StreamTVList" position="center,center" size="600,350" title="StreamTV List">
			<widget name="streamlist" position="0,0" size="600,350" backgroundColor="#000000" zPosition="10" scrollbarMode="showOnDemand" />
	        </screen>
		"""
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self["actions"]  = ActionMap(["OkCancelActions", "ShortcutActions", "WizardActions", "ColorActions", "SetupActions", "NumberActions", "MenuActions"], {
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
		}, -1)

		self.streamBin  = resolveFilename(SCOPE_PLUGINS, "Extensions/StreamTV/rtmpdump")
		self.streamFile = resolveFilename(SCOPE_PLUGINS, "Extensions/StreamTV/stream.xml")

		self.streamList = []
		self.makeStreamList()

		self.streamMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.streamMenuList.l.setFont(0, gFont('Regular', 22))
		self.streamMenuList.l.setFont(1, gFont('Regular', 18))
		self.streamMenuList.l.setItemHeight(37) 
		self['streamlist'] = self.streamMenuList
		self.streamMenuList.setList(map(streamListEntry, self.streamList))

		self.onLayoutFinish.append(self.layoutFinished)

		self.rtmpConsole    = None
		self.beforeService  = None
		self.currentService = None
		self.playerStoped   = False
		self.serviceDoCommand = None

		self.keyLocked = False

	def layoutFinished(self):
		rc = os.popen('ps -ef | grep rtmpdump | grep -v grep').read()
		print "a process already running :", rc
		if rc is not None:
			if rc.strip() != '':
				os.system('killall -INT rtmpdump')
	def keyLeft(self):
		if self.keyLocked:
			return
		self['streamlist'].pageUp()

	def keyRight(self):
		if self.keyLocked:
			return
		self['streamlist'].pageDown()

	def keyUp(self):
		if self.keyLocked:
			return
		self['streamlist'].up()

	def keyDown(self):
		if self.keyLocked:
			return
		self['streamlist'].down()

	def keyCancel(self):
		self.cbAppClosed(True)
		self.close()

	def keyOK(self):
		if self.keyLocked:
			return
		self.keyLocked = True
		self.rtmpConsole    = None
		self.beforeService  = None
		self.currentService = None
		self.playerStoped   = False
		self.serviceDoCommand = None

		streamInfo = self["streamlist"].getCurrent()[0][1]
		uriInfo    = streamInfo.get('uri')
		typeInfo   = streamInfo.get('type').split(':')

		protocol = typeInfo[0]
		url      = uriInfo.get('URL')
		if protocol == 'rtmp':
			self.layoutFinished()
			self.rtmpConsole = eConsoleAppContainer()
			self.rtmpConsole.dataAvail.append(self.cbDataAvail)
			self.rtmpConsole.appClosed.append(self.cbAppClosed)
			self.rtmpConsole.execute(self.makeCommand(uriInfo))
		elif protocol in ('rtsp', 'http', 'hls'):
			serviceType = typeInfo[1]
			bufferSize  = typeInfo[2]
			self.doStreamAction(url, serviceType, bufferSize)

	def doStreamAction(self, url=None, serviceType='4097', bufferSize=None):
		if url is None:
			url='/tmp/stream.avi'
			self.streamPlayerTimer.stop()
			#if os.path.exists(url):
			#	os.unlink(url)
		try:
			serviceType = int(serviceType)
		except:	serviceType = 4097
		try:
			bufferSize = int(bufferSize)
		except:	bufferSize = None

		service = eServiceReference(serviceType, 0, url)
		#if bufferSize is not None:
		#	service.setData(2, bufferSize*1024)

		streamInfo = self["streamlist"].getCurrent()[0][1]
		uriInfo    = streamInfo.get('uri')
		self.beforeService  = self.session.nav.getCurrentlyPlayingServiceReference()
		self.currentService = self.session.openWithCallback(self.cbFinishedStream, 
								    StreamTVPlayer, 
								    service, 
								    cbServiceCommand=self.cbServiceCommand,
								    chName=str(streamInfo.get('name')),
								    chURL =str(uriInfo.get('URL')),
								    chIcon=str(streamInfo.get('icon')))

	def cbServiceCommand(self, params=None):
		if params is None:
			self.playerStoped = True
			return
		if params[0] == 'docommand':
			self.serviceDoCommand = params[1]

	def cbAppClosed(self, ret):
		print ret
		self.doConsoleStop()
		if self.currentService is not None and not self.playerStoped:
			self.serviceDoCommand('bypass_exit')
			message = "The connection was terminated from the stream server."
			self.session.open(MessageBox, message, type=MessageBox.TYPE_INFO)
			self.currentService.close()
			self.currentService = None
			self.serviceDoCommand = None

	def cbDataAvail(self, data):
		print data
		if str(data) == 'Connected...':
			self.streamPlayerTimer = eTimer()
			self.streamPlayerTimer.timeout.get().append(self.doStreamAction)
			self.streamPlayerTimer.start(1000)

	def cbFinishedStream(self):
		self.doConsoleStop()
		self.session.nav.playService(self.beforeService)
		print 'player done!!'

	def doConsoleStop(self):
		self.keyLocked = False
		if self.rtmpConsole is not None:
			self.rtmpConsole.sendCtrlC()
			self.rtmpConsole = None

	def makeCommand(self, uriInfo):
		def appendCommand(key, option):
			try:
				d = uriInfo.get(key)
				if d is not None:
					return "-%s %s " %(option, d)
			except: pass
			return ''
		command  = '%s -v ' % (self.streamBin)
		command += appendCommand('URL', 'r')
		command += appendCommand('PLAYPATH', 'y')
		command += appendCommand('SWFURL', 'W')
		return command

	def makeStreamList(self):
		streamDB = StreamURIParser(self.streamFile).parseStreamList()
		self.streamList = []
		for x in streamDB:
			self.streamList.append((x.get('name'), x))

def main(session, **kwargs):
	session.open(StreamTVList)
                                                           
def Plugins(**kwargs):
	return PluginDescriptor(name=_("StreamTVPlayer"), description="Watching IPTV implemented by RTSP/RTMP protocol.", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main)


