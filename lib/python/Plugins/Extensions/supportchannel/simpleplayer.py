#	-*-	coding:	utf-8	-*-

try:
	import mechanize
except:
	print "No 'mechanize' module"
	mechanizeModule = False
else:
	print "Module 'mechanize' loaded"
	mechanizeModule = True

import Queue
import random
from Screens.InfoBarGenerics import *
from imports import *
from youtubelink import YoutubeLink
from coverhelper import CoverHelper

is_avSetupScreen = False
try:
	from Plugins.SystemPlugins.Videomode.plugin import VideoSetup
	from Plugins.SystemPlugins.Videomode.VideoHardware import video_hw
except:
	VideoSetupPresent = False
else:
	VideoSetupPresent = True

if not VideoSetupPresent:
	try:
		from Plugins.SystemPlugins.Videomode.plugin import avSetupScreen
	except:
		VideoSetupPresent = False
	else:
		VideoSetupPresent = True
		is_avSetupScreen = True

try:
	from Plugins.Extensions.mediainfo.plugin import mediaInfo
	MediainfoPresent = True
except:
	MediainfoPresent = False

class SimpleSeekHelper:

	def __init__(self):
		self["seekbarcursor"] = MovingPixmap()
		self["seekbarcursor"].hide()
		self["seekbartime"] = Label()
		self["seekbartime"].hide()
		self.cursorTimer = eTimer()
		self.cursorTimer.callback.append(self.__updateCursor)
		self.cursorShown = False
		self.seekBarShown = False
		self.seekBarLocked = False
		self.isNumberSeek = False
		self.counter = 0
		self.onHide.append(self.__seekBarHide)
		self.onShow.append(self.__seekBarShown)
		self.resetMySpass()

	def initSeek(self):
		self.percent = 0.0
		self.length = None
		self.cursorShown = False
		self.counter = 1
		service = self.session.nav.getCurrentService()
		if service:
			self.seek = service.seek()
			if self.seek:
				self.length = self.seek.getLength()
				position = self.seek.getPlayPosition()
				if self.length[1] and position[1]:
					if self.myspass_len:
						self.length[1] = self.myspass_len
						position[1] += self.myspass_ofs
					else:
						self.myspass_len = self.length[1]
						self.mySpassPath = self.session.nav.getCurrentlyPlayingServiceReference().getPath()
						if '/myspass' in self.mySpassPath:
							self.isMySpass = True
						elif 'file=retro-tv' in self.mySpassPath:
							#self.isRetroTv = True
							#self.isMySpass = True
							pass
						elif '007i.net' in self.mySpassPath:
							self.isMySpass = True
						elif 'eroprofile.com' in self.mySpassPath:
							self.isMySpass = True
						elif 'media.amateurporn.net' in self.mySpassPath:
							self.isMySpass = True
						elif 'media.hdporn.net' in self.mySpassPath:
							self.isMySpass = True
						elif 'amateurslust.com' in self.mySpassPath:
							self.isMySpass = True

					self.percent = float(position[1]) * 100.0 / float(self.length[1])
					if not self.isNumberSeek:
						InfoBarShowHide.lockShow(self)
						self.seekBarLocked = True
						self["seekbartime"].show()
						self.cursorTimer.start(200, False)

	def __seekBarShown(self):
		#print "seekBarShown:"
		self.seekBarShown = True

	def __seekBarHide(self):
		#print "seekBarHide:"
		self.seekBarShown = False

	def toggleShow(self):
		#print "toggleShow:"
		if self.seekBarLocked:
			self.seekOK()
		else:
			InfoBarShowHide.toggleShow(self)

	def __updateCursor(self):
		if self.length:
			x = 273 + int(6.86 * self.percent)
			self["seekbarcursor"].moveTo(x, 626, 1)
			self["seekbarcursor"].startMoving()
			pts = int(float(self.length[1]) / 100.0 * self.percent)
			self["seekbartime"].setText("%d:%02d" % ((pts/60/90000), ((pts/90000)%60)))
			if not self.cursorShown:
				if not self.counter:
					self.cursorShown = True
					self["seekbarcursor"].show()
				else:
					self.counter -= 1

	def seekExit(self):
		#print "seekExit:"
		if not self.isNumberSeek:
			self.seekBarLocked = False
			self.cursorTimer.stop()
			self.unlockShow()
			self["seekbarcursor"].hide()
			self["seekbartime"].hide()
		else:
			self.isNumberSeek = False

	def seekOK(self):
		#print "seekOK:"
		if self.length:
			seekpos = float(self.length[1]) / 100.0 * self.percent
			#if self.ltype == 'myspass':
			if self.isMySpass:
				self.myspass_ofs = seekpos
				self.doMySpassSeekTo(seekpos)
			else:
				self.seek.seekTo(int(seekpos))
				self.seekExit()
		else:
			self.seekExit()

	def seekLeft(self):
		#print "seekLeft:"
		self.percent -= float(config.supportchannel.sp_seekbar_sensibility.value) / 10.0
		if self.percent < 0.0:
			self.percent = 0.0

	def seekRight(self):
		#print "seekRight:"
		self.percent += float(config.supportchannel.sp_seekbar_sensibility.value) / 10.0
		if self.percent > 100.0:
			self.percent = 100.0

	def numberKeySeek(self, val):
		#print "numberKeySeek:"
		length = float(self.length[1])
		if length > 0.0:
			pts = int(length / 100.0 * self.percent) + val * 90000
			self.percent = pts * 100 / length
			if self.percent < 0.0:
				self.percent = 0.0
			elif self.percent > 100.0:
				self.percent = 100.0

			self.seekOK()
			if config.usage.show_infobar_on_skip.value:
				self.doShow()
		else:
			return

	def doMySpassSeekTo(self, seekpos):
		service = self.session.nav.getCurrentService()
		title = service.info().getName()
		path = self.mySpassPath
		seeksecs = seekpos / 90000
		#print "seeksecs:",seeksecs
		if self.isRetroTv:
			url = "%s&start=%ld" % (path.split('&')[0], int(seeksecs*145000))
		else:
			url = "%s?start=%f" % (path.split('?')[0], seeksecs)
		#print "seekto:",url
		sref = eServiceReference(0x1001, 0, url)
		sref.setName(title)
		self.seekExit()
		self.session.nav.stopService()
		self.session.nav.playService(sref)

	def restartMySpass(self):
		self.resetMySpass()
		self.doMySpassSeekTo(0L)

	def resetMySpass(self):
		self.myspass_ofs = 0L
		self.myspass_len = 0L
		self.mySpassPath = None
		self.isMySpass = False
		self.isRetroTv = False
		self.isNumberSeek = False

	def cancelSeek(self):
		if self.seekBarLocked:
			self.seekExit()

class SimplePlayerResume:

	def __init__(self):
		self.posTrackerActive = False
		self.currService = None
		self.eof_resume = False
		self.use_sp_resume = config.supportchannel.sp_on_movie_start.value != "start"
		self.posTrackerTimer = eTimer()
		self.posTrackerTimer.callback.append(self.savePlayPosition)
		self.eofResumeTimer = eTimer()
		self.eofResumeTimer.callback.append(self.resetEOFResumeFlag)
		self.eofResumeFlag = False

		self.onClose.append(self.stopPlayPositionTracker)

	def initPlayPositionTracker(self, lru_key):
#		print 'SP: initPlayPositionTracker:'
		if self.use_sp_resume and not self.posTrackerActive and not self.playerMode in 'MP3':
			self.posTrackerActive = True
			self.lruKey = lru_key
			self.posTrackerTimer.start(1000*1, True)
#			print "SP: pos. tracker startet"

	def stopPlayPositionTracker(self):
#		print 'SP: stopPlayPositionTracker:'
		if self.posTrackerActive:
			self.posTrackerTimer.stop()
			self.posTrackerActive = False
			self.currService = None
		self.eofResumeTimer.stop()
		self.eofResumeFlag = False

	def savePlayPosition(self):
#		print 'SP: savePlayPosition:'
		if self.posTrackerActive:
			if not self.currService:
#				print 'SP: got service'
				service = self.session.nav.getCurrentService()
				if service:
					seek = service.seek()
					if seek:
#						print 'SP: got seek'
						length = seek.getLength()
						position = seek.getPlayPosition()
						if length[1] > 0 and position[1] > 0:
							if self.lruKey in mp_globals.lruCache:
								lru_value = mp_globals.lruCache[self.lruKey]
								if length[1]+5*90000 > lru_value[0]:
									self.resumePlayback(lru_value[0], lru_value[1])
							else:
								mp_globals.lruCache[self.lruKey] = (length[1], position[1])
							self.currService = service
				self.posTrackerTimer.start(1000*1, True)
			else:
				seek = self.currService.seek()
				if seek:
					length = seek.getLength()[1]
					position = seek.getPlayPosition()[1]
					mp_globals.lruCache[self.lruKey] = (length, position)
#					print 'SP: playpos:',position
#					print 'SP: playlen:',length
#				self.posTrackerTimer.start(1000*5, True)

	def resumePlayback(self, length, last):
		self.resume_point = last
		if (length > 0) and abs(length - last) < 4*90000:
			return
		l = last / 90000
		if self.eof_resume or config.supportchannel.sp_on_movie_start.value == "resume":
			self.eof_resume = False
			self.session.openWithCallback(self.playLastCB, MessageBox, _("Resuming playback"), timeout=2, type=MessageBox.TYPE_INFO)
		elif config.supportchannel.sp_on_movie_start.value == "ask":
			self.session.openWithCallback(self.playLastCB, MessageBox, _("Do you want to resume this playback?") + "\n" + (_("Resume position at %s") % ("%d:%02d:%02d" % (l/3600, l%3600/60, l%60))), timeout=10)

	def resetEOFResumeFlag(self):
#		print 'SP: resetEOFResumeFlag:'
		self.eofResumeFlag = False

	def resumeEOF(self):
#		print 'SP: resumeEOF:'
		if self.use_sp_resume and self.posTrackerActive and self.lruKey in mp_globals.lruCache:
			self.savePlayPosition()
			lru_value = mp_globals.lruCache[self.lruKey]
			if (lru_value[1]+90000*5) < lru_value[0]:
				if self.eofResumeFlag:
					return True
				self.eofResumeFlag = True
				self.eofResumeTimer.start(1000*15, True)
				self.doSeek(0)
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.eof_resume = True
				self.resumePlayback(lru_value[0], lru_value[1])
				return True
			elif (lru_value[1]+90000*4) >= lru_value[0]:
				self.stopPlayPositionTracker()
				mp_globals.lruCache.cache.pop()

		return False

	def playLastCB(self, answer):
		print 'playLastCB:'
		if answer == True:
			self.doSeek(self.resume_point)
		self.hideAfterResume()

	def hideAfterResume(self):
		print 'hideAfterResume:'
		if isinstance(self, InfoBarShowHide):
			self.hide()

class SimplePlaylist(Screen):

	def __init__(self, session, playList, playIdx, playMode, listTitle=None, plType='local', title_inr=0, queue=None, mp_event=None, listEntryPar=None, playFunc=None, playerMode=None):
		self.session = session

		self.plugin_path = mp_globals.pluginPath
		self.skin_path =  mp_globals.pluginPath + "/skins"

		path = "%s/%s/defaultPlaylistScreen.xml" % (self.skin_path, config.supportchannel.skin.value)
		if not fileExists(path):
			path = self.skin_path + "/original/defaultPlaylistScreen.xml"

		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.supportchannel.minitv.value)

		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions",'MediaPlayerSeekActions',"EPGSelectActions",'ColorActions','InfobarActions'],
		{
			'cancel':	self.exit,
			'red':		self.exit,
			'green':	self.toPlayer,
			'yellow':	self.changePlaymode,
			'blue':		self.deleteEntry,
			'ok': 		self.ok
		}, -2)

		self.playList = playList
		self.playIdx = playIdx
		self.listTitle = listTitle
		self.plType = plType
		self.title_inr = title_inr
		self.playlistQ = queue
		self.event = mp_event
		self.listEntryPar = listEntryPar
		self.playMode = playMode
		self.playFunc = playFunc
		self.playerMode = playerMode

		self["title"] = Label("")
		self["coverArt"] = Pixmap()
		self._Cover = CoverHelper(self['coverArt'])
		self["songtitle"] = Label ("")
		self["artist"] = Label ("")
		self["album"] = Label ("")
		if self.plType == 'global':
			self['F4'] = Label("Löschen")
		else:
			self['F4'] = Label("")
		if playerMode in 'MP3':
			self['F2'] = Label("to Player")
		else:
			self['F2'] = Label("")
		self['F3'] = Label("Playmode")
		self['F1'] = Label("Exit")
		self['playmode'] = Label(self.playMode[0].capitalize())

		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont('mediaportal', 23))
		if self.plType != 'global' and self.listEntryPar:
			self.chooseMenuList.l.setItemHeight(self.listEntryPar[3])
		else:
			self.chooseMenuList.l.setItemHeight(25)
		self['streamlist'] = self.chooseMenuList

		self.onClose.append(self.resetEvent)

		self.onLayoutFinish.append(self.showPlaylist)

	def updateStatus(self):
		print "updateStatus:"
		if self.playlistQ and not self.playlistQ.empty():
			t = self.playlistQ.get_nowait()
			self["songtitle"].setText(t[1])
			self["artist"].setText(t[2])
			self["album"].setText(t[3])
			self.getCover(t[4])
			if t[5] == self.plType:
				self.playIdx = t[0]
				if self.playIdx >= len(self.playList):
					self.playIdx = 0
				self['streamlist'].moveToIndex(self.playIdx)

	def playListEntry(self, entry):
		if self.plType != 'global' and self.listEntryPar:
			return [entry,
				(eListboxPythonMultiContent.TYPE_TEXT, self.listEntryPar[0], self.listEntryPar[1], self.listEntryPar[2], self.listEntryPar[3], self.listEntryPar[4], RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[self.listEntryPar[6]]+self.listEntryPar[5]+entry[self.listEntryPar[7]])
				]
		else:
			return [entry,
				(eListboxPythonMultiContent.TYPE_TEXT, 20, 0, 860, 25, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, entry[self.title_inr])
				]

	def showPlaylist(self):
		print 'showPlaylist:'

		if self.listTitle:
			self['title'].setText("MP Playlist - %s" % self.listTitle)
		else:
			self['title'].setText("MP %s Playlist-%02d" % (self.plType, config.supportchannel.sp_pl_number.value))

		self.chooseMenuList.setList(map(self.playListEntry, self.playList))

		if self.event:
			self.event.addCallback(self.updateStatus)
		else:
			self['streamlist'].moveToIndex(self.playIdx)

	def getCover(self, url):
		print "getCover:", url
		self._Cover.getCover(url)

	def deleteEntry(self):
		if self.plType == 'global':
			idx = self['streamlist'].getSelectedIndex()
			self.close([idx,'del',self.playList])

	def toPlayer(self):
		if self.playerMode in 'MP3':
			self.close([-2,'',self.playList])

	def exit(self):
		self.close([-1,'',self.playList])

	def ok(self):
		if len(self.playList) == 0:
			self.exit()
		idx = self['streamlist'].getSelectedIndex()
		if self.playFunc:
			self.playFunc(idx)
		else:
			self.close([idx,'',self.playList])

	def resetEvent(self):
		print "resetEvent:"
		if self.event:
			self.event.reset()

	def createSummary(self):
		print "createSummary"
		return SimplePlayerSummary

	def changePlaymode(self):
		if self.playMode[0] == "forward":
			self.playMode[0] = "backward"
		elif self.playMode[0] == "backward":
			self.playMode[0] = "random"
		else:
			self.playMode[0] = "forward"

		self["playmode"].setText(self.playMode[0].capitalize())

class SimplePlayer(Screen, SimpleSeekHelper, SimplePlayerResume, InfoBarMenu, InfoBarBase, InfoBarSeek, InfoBarNotifications, InfoBarServiceNotifications, InfoBarPVRState, InfoBarShowHide, InfoBarAudioSelection, InfoBarSubtitleSupport, InfoBarSimpleEventView):
	ALLOW_SUSPEND = True

	def __init__(self, session, playList, playIdx=0, playAll=False, listTitle=None, plType='local', title_inr=0, cover=False, ltype='', autoScrSaver=False, showPlaylist=True, listEntryPar=None, playList2=[], playerMode='VIDEO'):
		try:
			from enigma import eServiceMP3
		except:
			is_eServiceMP3 = False
			print "No MP3 service"
		else:
			is_eServiceMP3 = True
			print "MP3 service imported"

		Screen.__init__(self, session)
		print "SimplePlayer:"
		self.session = session
		self.plugin_path = "/usr/lib/enigma2/python/Plugins/Extensions/supportchannel"
		self.skin_path = "/usr/lib/enigma2/python/Plugins/Extensions/supportchannel" + "/skins"
		self.wallicon_path = "/usr/lib/enigma2/python/Plugins/Extensions/supportchannel" + "/icons_wall/"

		path = "%s/simpleplayer/SimplePlayer.xml" % self.skin_path
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		self.setActionPrio()
		self["actions"] = ActionMap(["WizardActions",'MediaPlayerSeekActions',"EPGSelectActions",'MoviePlayerActions','ColorActions','InfobarActions',"MenuActions","HelpActions"],
		{
			"leavePlayer": self.leavePlayer,
			config.supportchannel.sp_mi_key.value: self.openMediainfo,
			"menu":		self.openMenu,
			"up": 		self.openPlaylist,
			"down":		self.randomNow,
			"back":		self.leavePlayer,
			"left":		self.seekBack,
			"right":	self.seekFwd,
			"seekdef:1": self.Key1,
			"seekdef:3": self.Key3,
			"seekdef:4": self.Key4,
			"seekdef:6": self.Key6,
			"seekdef:7": self.Key7,
			"seekdef:9": self.Key9

		}, self.action_prio)

		SimpleSeekHelper.__init__(self)
		SimplePlayerResume.__init__(self)
		InfoBarMenu.__init__(self)
		InfoBarNotifications.__init__(self)
		InfoBarServiceNotifications.__init__(self)
		InfoBarBase.__init__(self)
		InfoBarShowHide.__init__(self)
		InfoBarAudioSelection.__init__(self)
		InfoBarSubtitleSupport.__init__(self)
		InfoBarSimpleEventView.__init__(self)

		self.allowPiP = False
		InfoBarSeek.__init__(self)
		InfoBarPVRState.__init__(self)

		self.skinName = 'MediaPortal SimplePlayer'
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()

		self.playerMode = playerMode
		self.keyPlayNextLocked = False
		self.isTSVideo = False
		self.showGlobalPlaylist = True
		self.showPlaylist = showPlaylist
		self.scrSaver = ''
		self.saverActive = False
		self.autoScrSaver = autoScrSaver
		self.pl_open = False
		self.playMode = [str(config.supportchannel.sp_playmode.value)]
		self.listTitle = listTitle
		self.playAll = playAll
		self.playList = playList
		self.playIdx = playIdx
		if plType == 'local':
			self.playLen = len(playList)
		else:
			self.playLen = len(playList2)

		self.listEntryPar=listEntryPar
		self.returning = False
		self.pl_entry = ['', '', '', '', '', '', '', '', '']
		self.plType = plType
		self.playList2 = playList2
		self.pl_name = 'mp_global_pl_%02d' % config.supportchannel.sp_pl_number.value
		self.title_inr = title_inr
		self.cover = cover
		self.ltype = ltype
		self.playlistQ = Queue.Queue(0)
		self.pl_status = (0, '', '', '', '', '')
		self.pl_event = SimpleEvent()
		self['spcoverframe'] = Pixmap()
		self['spcoverfg'] = Pixmap()
		self['Icon'] = Pixmap()
		self._Icon = CoverHelper(self['Icon'])
		self['premiumizemeoff'] = Pixmap()
		self['premiumizemeon'] = Pixmap()
		self['premiumizemeon'].hide()

		# load default cover
		self['Cover'] = Pixmap()
		self._Cover = CoverHelper(self['Cover'], nc_callback=self.hideSPCover)
		self.coverBGisHidden = False
		self.cover2 = False

		self.SaverTimer = eTimer()
		self.SaverTimer.callback.append(self.openSaver)

		self.hideSPCover()
		self.configSaver()
		self.onClose.append(self.playExit)
		self.onFirstExecBegin.append(self.showIcon)
		self.onFirstExecBegin.append(self.playVideo)

		if self.playerMode in 'MP3':
			self.onFirstExecBegin.append(self.openPlaylist)

		if is_eServiceMP3:
			self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
				{
					eServiceMP3.evAudioDecodeError: self.__evAudioDecodeError,
					eServiceMP3.evVideoDecodeError: self.__evVideoDecodeError,
					eServiceMP3.evPluginError: self.__evPluginError,
					eServiceMP3.evStreamingSrcError: self.__evStreamingSrcError
				})

	def __evAudioDecodeError(self):
		if not config.supportchannel.sp_show_errors.value:
			return
		from Screens.MessageBox import MessageBox
		from enigma import iServiceInformation
		currPlay = self.session.nav.getCurrentService()
		sTagAudioCodec = currPlay.info().getInfoString(iServiceInformation.sTagAudioCodec)
		print "[__evAudioDecodeError] audio-codec %s can't be decoded by hardware" % (sTagAudioCodec)
		self.session.open(MessageBox, _("This STB can't decode %s streams!") % sTagAudioCodec, type = MessageBox.TYPE_INFO,timeout = 10 )

	def __evVideoDecodeError(self):
		if not config.supportchannel.sp_show_errors.value:
			return
		from Screens.MessageBox import MessageBox
		from enigma import iServiceInformation
		currPlay = self.session.nav.getCurrentService()
		sTagVideoCodec = currPlay.info().getInfoString(iServiceInformation.sTagVideoCodec)
		print "[__evVideoDecodeError] video-codec %s can't be decoded by hardware" % (sTagVideoCodec)
		self.session.open(MessageBox, _("This STB can't decode %s streams!") % sTagVideoCodec, type = MessageBox.TYPE_INFO,timeout = 10 )

	def __evPluginError(self):
		if not config.supportchannel.sp_show_errors.value:
			return
		from Screens.MessageBox import MessageBox
		from enigma import iServiceInformation
		currPlay = self.session.nav.getCurrentService()
		message = currPlay.info().getInfoString(iServiceInformation.sUser+12)
		print "[__evPluginError]" , message
		self.session.open(MessageBox, message, type = MessageBox.TYPE_INFO,timeout = 10 )

	def __evStreamingSrcError(self):
		if not config.supportchannel.sp_show_errors.value:
			return
		from Screens.MessageBox import MessageBox
		from enigma import iServiceInformation
		currPlay = self.session.nav.getCurrentService()
		message = currPlay.info().getInfoString(iServiceInformation.sUser+12)
		print "[__evStreamingSrcError]", message
		self.session.open(MessageBox, _("Streaming error: %s") % message, type = MessageBox.TYPE_INFO,timeout = 10 )

	def playVideo(self):
		print "playVideo:"
		self.isTSVideo = False
		if self.seekBarLocked:
			self.cancelSeek()
		self.resetMySpass()
		if self.plType == 'global':
			self.getVideo2()
		else:
			self.cover2 = False
			self.getVideo()

	def playSelectedVideo(self, idx):
		self.playIdx = idx
		self.playVideo()

	def dataError(self, error):
		print "dataError:"
		printl(error,self,"E")
		if config.supportchannel.sp_show_errors.value:
			self.session.openWithCallback(self.dataError2, MessageBox, str(error), MessageBox.TYPE_INFO, timeout=10)
		else:
			reactor.callLater(2, self.dataError2, None)

	def dataError2(self, res):
		self.playNextStream(config.supportchannel.sp_on_movie_eof.value)

	def playStream(self, title, url=None, album='', artist='', imgurl=''):
		print "playStream: ",title,url
		if not url:
			return

		if mp_globals.proxy:
			self['premiumizemeoff'].hide()
			self['premiumizemeon'].show()
			mp_globals.proxy = False
		else:
			self['premiumizemeon'].hide()
			self['premiumizemeoff'].show()

		if self.cover or self.cover2:
			self.showCover(imgurl)

		if url.endswith('.ts'):
			sref = eServiceReference(0x0001, 0, url)
			self.isTSVideo = True
		else:
			sref = eServiceReference(0x1001, 0, url)
			self.isTSVideo = False

		pos = title.find('. ', 0, 5)
		if pos > 0:
			pos += 2
			title = title[pos:]

		if artist != '':
			video_title = artist + ' - ' + title
		else:
			video_title = title
		sref.setName(video_title)

		if self.cover:
			cflag = '1'
		else:
			cflag = '0'

		self.pl_entry = [title, None, artist, album, self.ltype, '', imgurl, cflag]

		self.stopPlayPositionTracker()

		self.session.nav.stopService()
		self.session.nav.playService(sref)

		if len(video_title) > 0:
			lru_key = video_title
		else:
			lru_key = url
		self.initPlayPositionTracker(lru_key)

		self.pl_status = (self.playIdx, title, artist, album, imgurl, self.plType)
		if self.pl_open:
			self.playlistQ.put(self.pl_status)
			self.pl_event.genEvent()

		self.keyPlayNextLocked = False


	def playPrevStream(self, value):
		print "_prevStream:"
		if not self.playAll or self.playLen <= 1:
			self.handleLeave(value)
		else:
			if self.playIdx > 0:
				self.playIdx -= 1
			else:
				self.playIdx = self.playLen - 1
			self.playVideo()

	def playNextStream(self, value):
		print "playNextStream:"
		if not self.playAll or self.playLen <= 1:
			self.handleLeave(value)
		else:
			if self.playIdx in range(0, self.playLen-1):
				self.playIdx += 1
			else:
				self.playIdx = 0
			self.playVideo()

	def playRandom(self, value):
		print 'playRandom:'
		if self.playLen > 1 and self.playAll:
			self.playIdx = random.randint(0, self.playLen-1)
			self.playVideo()
		else:
			self.handleLeave(value)

	def randomNow(self):
		if self.playAll:
			self.playRandom(config.supportchannel.sp_on_movie_stop.value)

	def seekFwd(self):
		if self.isTSVideo:
			InfoBarSeek.seekFwd(self)
		elif self.seekBarShown and not self.seekBarLocked:
			self.initSeek()
		elif self.seekBarLocked:
			self.seekRight()
		elif self.playAll and not self.keyPlayNextLocked:
			self.keyPlayNextLocked = True
			self.playNextStream(config.supportchannel.sp_on_movie_stop.value)

	def seekBack(self):
		if self.isTSVideo:
			InfoBarSeek.seekBack(self)
		elif self.seekBarShown and not self.seekBarLocked:
			self.initSeek()
		elif self.seekBarLocked:
			self.seekLeft()
		elif self.playAll and not self.keyPlayNextLocked:
			self.keyPlayNextLocked = True
			self.playPrevStream(config.supportchannel.sp_on_movie_stop.value)

	def Key1(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(-int(config.seek.selfdefined_13.value))

	def Key3(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(int(config.seek.selfdefined_13.value))

	def Key4(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(-int(config.seek.selfdefined_46.value))

	def Key6(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(int(config.seek.selfdefined_46.value))

	def Key7(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(-int(config.seek.selfdefined_79.value))

	def Key9(self):
		self.isNumberSeek = True
		self.initSeek()
		self.numberKeySeek(int(config.seek.selfdefined_79.value))

	def handleLeave(self, how):
		print "handleLeave:"
		if self.playerMode in 'MP3':
			self.openPlaylist()
			return
		self.is_closing = True
		if how == "ask":
			if self.plType == 'local':
				list = (
					(_("Ja"), "quit"),
					("Ja & Service zur glob. Playlist-%02d hinzufügen" % config.supportchannel.sp_pl_number.value, "add"),
					(_("Nein"), "continue"),
					(_("Nein, aber von Anfang an neu beginnen"), "restart")
				)
			else:
				list = (
					(_("Ja"), "quit"),
					(_("Nein"), "continue"),
					(_("Nein, aber von Anfang an neu beginnen"), "restart")
				)

			from Screens.ChoiceBox import ChoiceBox
			self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Stop playing this movie?"), list = list)
		else:
			self.leavePlayerConfirmed([True, how])

	def leavePlayerConfirmed(self, answer):
		print "leavePlayerConfirmed:"
		answer = answer and answer[1]
		print answer

		self.savePlayPosition()

		if answer in ("quit", "movielist"):
			self.close()
		elif answer == "restart":
			if self.isMySpass:
				self.restartMySpass()
			else:
				self.doSeek(0)
				self.setSeekState(self.SEEK_STATE_PLAY)
		elif answer == "add":
			self.addToPlaylist()
			self.close()

	def leavePlayer(self):
		print "leavePlayer:"
		if self.seekBarLocked:
			self.cancelSeek()
		else:
			self.handleLeave(config.supportchannel.sp_on_movie_stop.value)

	def doEofInternal(self, playing):
		print "doEofInt:"
		if playing:
			if not self.resumeEOF():
				if self.playMode[0] == 'random':
					self.playRandom(config.supportchannel.sp_on_movie_eof.value)
				elif self.playMode[0] == 'forward':
					self.playNextStream(config.supportchannel.sp_on_movie_eof.value)
				elif self.playMode[0] == 'backward':
					self.playPrevStream(config.supportchannel.sp_on_movie_eof.value)
			else:
				self.close()

	def playExit(self):
		print "playExit:"
		self.SaverTimer.stop()
		del self.SaverTimer
		if isinstance(self, SimpleSeekHelper):
			del self.cursorTimer
		if isinstance(self, SimplePlayerResume):
			del self.posTrackerTimer
			del self.eofResumeTimer

		if not self.playerMode in 'MP3':
			self.restoreLastService()

	def restoreLastService(self):
		if config.supportchannel.restorelastservice.value == "1":
			self.session.nav.playService(self.lastservice)
		else:
			self.session.nav.stopService()

	def getVideo(self):
		print "getVideo:"
		title = self.playList[self.playIdx][0]
		url = self.playList[self.playIdx][1]
		if len(self.playList[0]) == 3:
			iurl = self.playList[self.playIdx][2]
		else:
			iurl = ''
		self.playStream(title, url, imgurl=iurl)

	def getVideo2(self):
		print "getVideo2:"
		if self.playLen > 0:
			titel = self.playList2[self.playIdx][1]
			url = self.playList2[self.playIdx][2]
			album = self.playList2[self.playIdx][3]
			artist = self.playList2[self.playIdx][4]
			imgurl = self.playList2[self.playIdx][7]
			self.cover2 = self.playList2[self.playIdx][8] == '1' and self.plType == 'global'

			if len(self.playList2[self.playIdx]) < 6:
				ltype = ''
			else:
				ltype = self.playList2[self.playIdx][5]

			if ltype == 'youtube':
				YoutubeLink(self.session).getLink(self.playStream, self.dataError, titel, url, imgurl)
			elif ltype == 'putpattv':
				token = self.playList2[self.playIdx][6]
				PutpattvLink(self.session).getLink(self.playStream, self.dataError, titel, url, token, imgurl)
			elif ltype == 'myvideo':
				token = self.playList2[self.playIdx][6]
				MyvideoLink(self.session).getLink(self.playStream, self.dataError, titel, url, token, imgurl)
			elif ltype == 'songsto' and not url:
				token = self.playList2[self.playIdx][6]
				SongstoLink(self.session).getLink(self.playStream, self.dataError, titel, artist, album, token, imgurl)
			elif mechanizeModule and ltype == 'canna':
				CannaLink(self.session).getLink(self.playStream, self.dataError, titel, artist, album, url, imgurl)
			elif ltype == 'eighties':
				token = self.playList2[self.playIdx][6]
				EightiesLink(self.session).getLink(self.playStream, self.dataError, titel, artist, album, url, token, imgurl)
			elif ltype == 'mtv':
				MTVdeLink(self.session).getLink(self.playStream, self.dataError, titel, artist, url, imgurl)
			elif url:
				self.playStream(titel, url, album, artist, imgurl=imgurl)
		else:
			self.close()

	def openPlaylist(self, pl_class=SimplePlaylist):
		if  ((self.showGlobalPlaylist and self.plType == 'global') or self.showPlaylist) and self.playLen > 0:
			if self.playlistQ.empty():
				self.playlistQ.put(self.pl_status)
			self.pl_open = True
			self.pl_event.genEvent()

			if self.plType == 'local':
				self.session.openWithCallback(self.cb_Playlist, pl_class, self.playList, self.playIdx, self.playMode, listTitle=self.listTitle, plType=self.plType, title_inr=self.title_inr, queue=self.playlistQ, mp_event=self.pl_event, listEntryPar=self.listEntryPar, playFunc=self.playSelectedVideo,playerMode=self.playerMode)
			else:
				self.session.openWithCallback(self.cb_Playlist, pl_class, self.playList2, self.playIdx, self.playMode, listTitle=None, plType=self.plType, title_inr=0, queue=self.playlistQ, mp_event=self.pl_event, listEntryPar=self.listEntryPar,playFunc=self.playSelectedVideo,playerMode=self.playerMode)
		elif not self.playLen:
			self.session.open(MessageBox, _("Keine Einträge in der Playlist vorhanden!"), MessageBox.TYPE_INFO, timeout=5)

	def cb_Playlist(self, data):
		self.pl_open = False

		while not self.playlistQ.empty():
			t = self.playlistQ.get_nowait()

		if data[0] >= 0:
			self.playIdx = data[0]
			if self.plType == 'global':
				if data[1] == 'del':
					self.session.nav.stopService()
					SimplePlaylistIO.delEntry(self.pl_name, self.playList2, self.playIdx)
					self.playLen = len(self.playList2)
					if self.playIdx >= self.playLen:
						self.playIdx -= 1
					if self.playIdx < 0:
						self.close()
					else:
						self.openPlaylist()
			if not self.keyPlayNextLocked:
				self.keyPlayNextLocked = True
				self.playVideo()
		elif data[0] == -1 and self.playerMode in 'MP3':
				self.close()

	def openMediainfo(self):
		if MediainfoPresent:
			url = self.session.nav.getCurrentlyPlayingServiceReference().getPath()
			if url[:4] == "http":
				self.session.open(mediaInfo, True)

	def openMenu(self):
		self.session.openWithCallback(self.cb_Menu, SimplePlayerMenu, self.plType, self.showPlaylist or self.showGlobalPlaylist)

	def cb_Menu(self, data):
		print "cb_Menu:"
		if data != []:
			if data[0] == 1:
				self.playMode[0] = config.supportchannel.sp_playmode.value
				self.configSaver()
				if self.cover or self.cover2:
					self.showCover(self.pl_entry[6])
				self.pl_name = 'mp_global_pl_%02d' % config.supportchannel.sp_pl_number.value
			elif data[0] == 2:
				self.addToPlaylist()

			elif data[0] == 3:
				nm = self.pl_name
				pl_list = SimplePlaylistIO.getPL(nm)
				self.playList2 = pl_list
				playLen = len(self.playList2)
				if playLen > 0:
					self.playIdx = 0
					self.playLen = playLen
					self.plType = 'global'
				self.openPlaylist()

			elif data[0] == 4:
				if self.plType != 'local':
					playLen = len(self.playList)
					if playLen > 0:
						self.playIdx = 0
						self.playLen = playLen
						self.plType = 'local'
						self.playList2 = []
					self.openPlaylist()

			elif data[0] == 6:
				self.mainMenu()

	def addToPlaylist(self):
		if self.plType != 'local':
			self.session.open(MessageBox, _("Fehler: Service darf nur von der lok. PL hinzugefügt werden"), MessageBox.TYPE_INFO, timeout=5)
			return

		if self.pl_entry[4] == 'youtube':
			url = self.playList[self.playIdx][2]
		elif self.pl_entry[4] == 'myvideo':
			url = self.playList[self.playIdx][1]
			self.pl_entry[5] = self.playList[self.playIdx][2]
		elif self.pl_entry[4] == 'mtv':
			url = self.playList[self.playIdx][1]
		elif self.pl_entry[4] == 'putpattv' and self.playList[self.playIdx][2]:
			url = self.playList[self.playIdx][1]
			self.pl_entry[5] = self.playList[self.playIdx][2]
		else:
			url = self.session.nav.getCurrentlyPlayingServiceReference().getPath()

			if re.search('(putpat.tv|/myspass)', url, re.I):
				self.session.open(MessageBox, _("Fehler: URL ist nicht persistent !"), MessageBox.TYPE_INFO, timeout=5)
				return

		self.pl_entry[1] = url
		res = SimplePlaylistIO.addEntry(self.pl_name, self.pl_entry)
		if res == 1:
			self.session.open(MessageBox, _("Eintrag hinzugefügt"), MessageBox.TYPE_INFO, timeout=5)
		elif res == 0:
			self.session.open(MessageBox, _("Eintrag schon vorhanden"), MessageBox.TYPE_INFO, timeout=5)
		else:
			self.session.open(MessageBox, _("Fehler!"), MessageBox.TYPE_INFO, timeout=5)

	def showCover(self, cover):
		#print "showCover:", cover
		if config.supportchannel.sp_infobar_cover_off.value:
			self.hideSPCover()
			self["Cover"].hide()
			return
		if self.coverBGisHidden:
			self.showSPCover()
		self._Cover.getCover(cover)

	def showIcon(self):
		print "showIcon:"
		pm_file = self.wallicon_path + mp_globals.activeIcon + ".png"
		self._Icon.showCoverFile(pm_file)

	def hideSPCover(self):
		#print "hideSPCover:"
		if not self.coverBGisHidden:
			self['spcoverframe'].hide()
			self['spcoverfg'].hide()
			self.coverBGisHidden = True

	def showSPCover(self):
		print "showSPCover:"
		if self.coverBGisHidden:
			self['spcoverframe'].show()
			self['spcoverfg'].show()
			self.coverBGisHidden = False

	#def lockShow(self):
	#	pass

	#def unlockShow(self):
	#	pass

	def configSaver(self):
		print "configSaver:"
		self.scrSaver = config.supportchannel.sp_scrsaver.value
		print "Savermode: ",self.scrSaver
		if self.scrSaver == 'automatic' and self.autoScrSaver or self.scrSaver == 'on':
			if not self.saverActive:
				self.SaverTimer.start(1000*60, True)
				self.saverActive = True
				print "scrsaver timer startet"
		else:
			self.SaverTimer.stop()
			self.saverActive = False

	def openSaver(self):
		print "openSaver:"
		self.session.openWithCallback(self.cb_Saver, SimpleScreenSaver)

	def cb_Saver(self):
		print "cb_Saver:"
		self.saverActive = False
		self.configSaver()

	def createSummary(self):
		print "createSummary"
		return SimplePlayerSummary

	def setActionPrio(self):
		if config.supportchannel.sp_use_number_seek.value:
			self.action_prio = -2
		else:
			self.action_prio = -1

	def runPlugin(self, plugin):
		plugin(session=self.session)

class SimpleConfig(ConfigListScreen, Screen):
	skin = '\n\t\t<screen position="center,center" size="600,400" title="MP Player Konfiguration">\n\t\t\t<widget name="config" position="10,10" size="580,390" scrollbarMode="showOnDemand" />\n\t\t</screen>'

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.list = []
		self.list.append(getConfigListEntry('Glob. playlist number', config.supportchannel.sp_pl_number))
		self.list.append(getConfigListEntry('Playmode', config.supportchannel.sp_playmode))
		self.list.append(getConfigListEntry('Screensaver', config.supportchannel.sp_scrsaver))
		self.list.append(getConfigListEntry('Save resume cache in flash memory', config.supportchannel.sp_save_resumecache))
		self.list.append(getConfigListEntry('Behavior on movie start', config.supportchannel.sp_on_movie_start))
		self.list.append(getConfigListEntry('Behavior on movie stop', config.supportchannel.sp_on_movie_stop))
		self.list.append(getConfigListEntry('Behavior on movie end', config.supportchannel.sp_on_movie_eof))
		self.list.append(getConfigListEntry('Seekbar sensibility', config.supportchannel.sp_seekbar_sensibility))
		self.list.append(getConfigListEntry('Infobar cover always off', config.supportchannel.sp_infobar_cover_off))
		self.list.append(getConfigListEntry('Show errors', config.supportchannel.sp_show_errors))
		self.list.append(getConfigListEntry('Use SP number seek', config.supportchannel.sp_use_number_seek))
		if MediainfoPresent:
			self.list.append(getConfigListEntry('MediaInfo on key', config.supportchannel.sp_mi_key))
		ConfigListScreen.__init__(self, self.list)
		self['setupActions'] = ActionMap(['SetupActions'],
		{
			'ok': 		self.keySave,
			'cancel': 	self.keyCancel
		},-2)

class SimplePlayerMenu(Screen):
	skin = '\n\t\t<screen position="center,center" size="350,200" title="MP Player Menü">\n\t\t\t<widget name="menu" position="10,10" size="340,190" scrollbarMode="showOnDemand" />\n\t\t</screen>'

	def __init__(self, session, pltype, showPlaylist=True):
		Screen.__init__(self, session)
		self.session = session
		self.pltype = pltype
		self['setupActions'] = ActionMap(['SetupActions'],
		{
			'ok': 		self.keyOk,
			'cancel':	self.keyCancel
		}, -2)

		self.liste = []
		if pltype != 'extern':
			self.liste.append(('Configuration', 1))
		if pltype in ('local', 'extern') :
			self.pl_name = 'mp_global_pl_%02d' % config.supportchannel.sp_pl_number.value
			self.liste.append(('Add service to global playlist-%02d' % config.supportchannel.sp_pl_number.value, 2))
			if showPlaylist and pltype == 'local':
				self.liste.append(('Open global playlist-%02d' % config.supportchannel.sp_pl_number.value, 3))
		elif showPlaylist:
			self.liste.append(('Open local playlist', 4))
		if VideoSetupPresent:
			self.liste.append(('A/V Settings', 5))
		self.liste.append(('Mainmenu', 6))
		self['menu'] = MenuList(self.liste)

	def openConfig(self):
		self.session.open(SimpleConfig)
		self.close([1, ''])

	def addToPlaylist(self, id, name):
		self.close([id, name])

	def openPlaylist(self, id, name):
		self.close([id, name])

	def openSetup(self):
		if VideoSetupPresent:
			if is_avSetupScreen:
				self.session.open(avSetupScreen)
			else:
				self.session.open(VideoSetup, video_hw)
		self.close([5, ''])

	def openMainmenu(self, id, name):
		self.close([id, name])

	def keyOk(self):
		choice = self['menu'].l.getCurrentSelection()[1]
		if choice == 1:
			self.openConfig()
		elif choice == 2:
			self.addToPlaylist(2, self.pl_name)
		elif choice == 3:
			self.openPlaylist(3, '')
		elif choice == 4:
			self.openPlaylist(4, '')
		elif choice == 5:
			self.openSetup()
		elif choice == 6:
			self.openMainmenu(6, '')

	def keyCancel(self):
		self.close([])

class SimplePlaylistIO:

	Msgs = [_("Der Verzeichnispfad ended nicht mit '/':\n%s"),
		_("Datei mit gleichen Namen im Verzeichnispfad vorhanden:\n%s"),
		_("Das fehlende Verzeichnis:\n%s konnte nicht angelegt werden!"),
		_("Der Verzeichnispfad:\n%s ist nicht vorhanden!"),
		_("Es existiert schon ein Verzeichnis mit dem Dateinamen:\n%s"),
		_("Der Pfad ist i.O., der Dateiname wurde nicht angegeben:\n%s"),
		_("Der Verzeichnispfad & Dateiname is i.O.:\n%s"),
		_("Der Verzeichnispfad wurde nicht angegeben!"),
		_("Symbolik Link mit gleichen Namen im Verzeichnispfad:\n%s vorhanden!")]

	@staticmethod
	def checkPath(path, pl_name, createPath=False):
		if not path:
			return (0, SimplePlaylistIO.Msgs[7])
		if path[-1] != '/':
			return (0, SimplePlaylistIO.Msgs[0] % path)
		if not os.path.isdir(path):
			if os.path.isfile(path[:-1]):
				return (0, SimplePlaylistIO.Msgs[1] % path)
			if os.path.islink(path[:-1]):
				return (0, SimplePlaylistIO.Msgs[8] % path)
			if createPath:
				if createDir(path, True) == 0:
					return (0, SimplePlaylistIO.Msgs[2] % path)
			else:
				return (0, SimplePlaylistIO.Msgs[3] % path)
		if not pl_name:
			return (1, SimplePlaylistIO.Msgs[5] % path)
		if os.path.isdir(path+pl_name):
			return (0, SimplePlaylistIO.Msgs[4] % (path, pl_name))

		return (1, SimplePlaylistIO.Msgs[6] % (path, pl_name))

	@staticmethod
	def delEntry(pl_name, list, idx):
		print "delEntry:"

		assert pl_name != None
		assert list != []

		pl_path = config.supportchannel.watchlistpath.value + pl_name

		l = len(list)
		if idx in range(0, l):
			del list[idx]
			l = len(list)

		j = 0
		try:
			f1 = open(pl_path, 'w')
			while j < l:
				wdat = '<title>%s</<url>%s</<album>%s</<artist>%s</<ltype %s/><token %s/><img %s/><cflag %s/>\n' % (list[j][1], list[j][2], list[j][3], list[j][4], list[j][5], list[j][6], list[j][7], list[j][8])
				f1.write(wdat)
				j += 1

			f1.close()

		except IOError, e:
			print "Fehler:\n",e
			print "eCode: ",e
			f1.close()

	@staticmethod
	def addEntry(pl_name, entry):
		print "addEntry:"

		cflag = entry[7]
		imgurl = entry[6]
		token = entry[5]
		ltype = entry[4]
		album = entry[3]
		artist = entry[2]
		url = entry[1]
		title = entry[0].replace('\n\t', ' - ')
		title = title.replace('\n', ' - ')

		if token == None:
			token = ''

		if url == None:
			url = ''

		if imgurl == None:
			imgurl = ''

		cmptup = (url, artist, title)

		assert pl_name != None

		pl_path = config.supportchannel.watchlistpath.value + pl_name
		try:
			if fileExists(pl_path):
				f1 = open(pl_path, 'a+')

				data = f1.read()
				m = re.findall('<title>(.*?)</<url>(.*?)</.*?<artist>(.*?)</', data)
				if m:
					found = False
					for (t,u,a) in m:
						if (u,a,t)  == cmptup:
							found = True
							break

					if found:
						f1.close()
						return 0
			else:
				f1 = open(pl_path, 'w')

			wdat = '<title>%s</<url>%s</<album>%s</<artist>%s</<ltype %s/><token %s/><img %s/><cflag %s/>\n' % (title, url, album, artist, ltype, token, imgurl, cflag)
			f1.write(wdat)
			f1.close()
			return 1

		except IOError, e:
			print "Fehler:\n",e
			print "eCode: ",e
			f1.close()
			return -1

	@staticmethod
	def getPL(pl_name):
		print "getPL:"

		list = []

		assert pl_name != None

		pl_path = config.supportchannel.watchlistpath.value + pl_name
		try:
			if not fileExists(pl_path):
				f_new = True
			else:
				f_new = False
				f1 = open(pl_path, 'r')

			if not f_new:
				while True:
					entry = f1.readline().strip()
					if entry == "":
						break
					m = re.search('<title>(.*?)</<url>(.*?)</<album>(.*?)</<artist>(.*?)</<ltype (.*?)/><token (.*?)/><img (.*?)/><cflag (.*?)/>', entry)
					if m:
						titel = m.group(1)
						url = m.group(2)
						album = m.group(3)
						artist = m.group(4)
						ltype = m.group(5)
						token = m.group(6)
						imgurl = m.group(7)
						cflag = m.group(8)

						if artist != '':
							name = "%s - %s" % (artist, titel)
						else:
							name = titel

						list.append((name, titel, url, album, artist, ltype, token, imgurl, cflag))

				f1.close()

			return list

		except IOError, e:
			print "Fehler:\n",e
			print "eCode: ",e
			f1.close()
			return list

class SimpleEvent:
	def __init__(self):
		self._ev_callback = None
		self._ev_on = False

	def genEvent(self):
		#print "genEvent:"
		if self._ev_callback:
			self._ev_on = False
			self._ev_callback()
		else:
			self._ev_on = True

	def addCallback(self, cb):
		#print "addCallback:"
		self._ev_callback=cb
		if self._ev_on:
			self._ev_on = False
			cb()

	def reset(self):
		#print "reset"
		self._ev_callback = None
		self._ev_on = False

class SimpleScreenSaver(Screen):
	skin = """
		<screen position="0,0" size="1280,720" flags="wfNoBorder" zPosition="9" transparent="0">
		</screen>"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SimpleScreenSaver.skin

		self["setupActions"] = ActionMap([ "SetupActions" ],
		{
			"cancel": self.cancel,
			"ok": self.cancel
		})

	def cancel(self):
		self.close()

class SimplePlayerSummary(Screen):

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self.skinName = "InfoBarMoviePlayerSummary"