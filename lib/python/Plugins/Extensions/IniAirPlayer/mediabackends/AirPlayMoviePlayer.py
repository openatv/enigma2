# 2013.05.22 09:49:34 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/mediabackends/AirPlayMoviePlayer.py
"""
Created on 17.04.2013

@author: matthias
"""
from Components.ActionMap import ActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Slider import Slider
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.config import config
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Tools import Notifications
from Tools.Directories import fileExists
from ctypes import *
from enigma import eServiceReference, iServiceInformation, eConsoleAppContainer, eTimer, eBackgroundFileEraser, iPlayableService
from thread import start_new_thread
from time import sleep
from urllib2 import Request, urlopen
import os
import subprocess
from helper import blockingCallFromMainThread
import traceback
PROXY_BINARY = '/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/proxy'

class AirPlayMoviePlayer(MoviePlayer):

    def __init__(self, session, service, backend, start = None, lastservice = None):
        self.backend = backend
        self.startNewServiceOnPlay = False
        self.start = start
        self.service = service
        self.session = session
        self.useProxy = False
        self.url = self.service.getPath()
        self.proxyReady = False
        self.proxyError = False
        self['useProxy'] = Boolean(False)
        self['premiumUser'] = Boolean(False)
        self.azBoxLastService = None
        self.proxyCaching = False
        print '[AirPlayMoviePlayer] MoviePlayer play url: ', self.url
        if self.url[:7] == 'http://' or self.url[:8] == 'https://':
            print '[AirPlayMoviePlayer] found http(s) link'
            if self.checkProxyUsable() and config.plugins.airplayer.useProxyIfPossible.value:
                print '[AirPlayMoviePlayer] using proxy'
                self.service = None
                self.startNewServiceOnPlay = True
                self.proxyCaching = True
                self.useProxy = True
                self['useProxy'] = Boolean(True)
        if 'm3u8' in self.url and self.useProxy == False:
            Notifications.AddNotification(MessageBox, _('You are trying to play an m3u8 stream. Playing m3u8 streams requires a Premium-Key to use the embedded proxy or a very new version of GStreamer and the gst-fragmented plugin. Otherwise the playback might not work!'), type=MessageBox.TYPE_INFO, timeout=10)
        if self.backend.ENIGMA_SERVICE_ID == self.backend.ENIGMA_SERVICEAZ_ID:
            self.azBoxLastService = lastservice or self.session.nav.getCurrentlyPlayingServiceReference()
            self.session.nav.stopService()
            open('/proc/player', 'w').write('0')
            open('/proc/player', 'w').write('2')
        MoviePlayer.__init__(self, session, self.service)
        if self.backend.ENIGMA_SERVICE_ID == self.backend.ENIGMA_SERVICEAZ_ID:
            self.lastservice = self.azBoxLastService
        backend.MovieWindow = self
        self.skinName = 'AirPlayerMoviePlayer'
        if lastservice is not None:
            self.lastservice = lastservice
        self.bufferslider = Slider(0, 100)
        self.bufferslider.setValue(0)
        self['bufferslider'] = self.bufferslider
        self['bufferslider'].setValue(0)
        self['label_speed'] = StaticText('DL-Speed: N/A')
        self['label_update'] = StaticText('')
        self['label_cache'] = StaticText('Cache: N/A')
        self.endReached = False
        self.localCache = False
        self.dlactive = False
        self.localsize = 0
        self.proxyProcess = None
        self.liveStream = False
        self.m3u8Stream = False
        self['actions'] = ActionMap(['InfobarInstantRecord', 'MoviePlayerActions'], {'instantRecord': self.keyStartLocalCache,
         'leavePlayer': self.leavePlayer}, -2)
        if config.plugins.airplayer.setSeekOnStart.value and self.start != None and self.start > 0.0:
            start_new_thread(self.seekWatcher, (self,))
        start_new_thread(self.checkForUpdate, (self,))
        self.__event_tracker = ServiceEventTracker(screen=self, eventmap={iPlayableService.evUser + 10: self.__evAudioDecodeError,
         iPlayableService.evUser + 11: self.__evVideoDecodeError,
         iPlayableService.evUser + 12: self.__evPluginError,
         iPlayableService.evEOF: self.__evEOF})
        if self.useProxy:
            start_new_thread(self.proxyWatcher, (self,))
            self.backend.updateEventInfo('loading')
            self.onHide.append(self.lockInfoBar)
            self.proxyCaching = True
            self.checkProxyTimer = eTimer()
            self.checkProxyTimer.timeout.get().append(self.checkProxyStatus)
            self.checkProxyTimer.start(500, True)

    def checkProxyUsable(self):
        if not os.path.exists(PROXY_BINARY):
            return False
        try:
            self.libairtunes = cdll.LoadLibrary('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/libairtunes.so.0')
            print '[AirPlayMoviePlayer] loading lib done'
            self.validationMessage = ''
            response = create_string_buffer(1024)
            if self.libairtunes.checkValidation(config.plugins.airplayer.validationKey.value, response) < 0:
                return False
            print '[AirPlayMoviePlayer] valid premium user'
            self['premiumUser'] = Boolean(True)
        except Exception as e:
            print '[AirPlayMoviePlayer] loading lib failed'
            print e
            self.libairtunes = None
            return False

        if not os.path.isdir(config.plugins.airplayer.path.value):
            Notifications.AddNotification(MessageBox, _('The path for temp files that you entered in the settings (%s) does not exist! Please set up a propper path in the Settings. The Path is needed for the built in proxy. The proxy was therefore disabled!') % config.plugins.airplayer.path.value, type=MessageBox.TYPE_INFO, timeout=10)
            return False
        if not os.access(config.plugins.airplayer.path.value, os.W_OK):
            Notifications.AddNotification(MessageBox, _('The path for temp files that you entered in the settings (%s) is not writeable! Please set up a propper path in the Settings. The Path is needed for the built in proxy. The proxy was therefore disabled!') % config.plugins.airplayer.path.value, type=MessageBox.TYPE_INFO, timeout=10)
            return False
        stat = os.statvfs(config.plugins.airplayer.path.value)
        free = stat.f_bfree * stat.f_bsize / 1024 / 1024
        print '[AirPlayMoviePlayer] free blocks:', stat.f_bfree, ' block size:', stat.f_bsize
        if free < 128:
            Notifications.AddNotification(MessageBox, _('The path for temp files that you entered in the settings (%s) has only %d MB left. The proxy was therefore disabled!') % (config.plugins.airplayer.path.value, free), type=MessageBox.TYPE_INFO, timeout=10)
            return False
        return True

    def keyStartLocalCache(self):
        if self.useProxy:
            print '[AirPlayMoviePlayer] Proxy is in user, no neef for downloading the file'
            return
        print '[AirPlayMoviePlayer] start local file caheing'
        if '.m3u8' in self.url:
            self.session.open(MessageBox, _('This stream can not get saved on HDD\nm3u8 streams are not supported'), MessageBox.TYPE_INFO)
            return
        if self.localCache == True:
            return
        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.DLfinished)
        self.container.setCWD(config.plugins.airplayer.path.value)
        self.startDL()

    def startDL(self):
        self.filename = 'test.mov'
        try:
            req = Request(self.url)
            req.add_header('User-agent', 'QuickTime/7.6.2 (verqt=7.6.2;cpu=IA32;so=Mac 10.5.8)')
            usock = urlopen(req)
            self.filesize = usock.info().get('Content-Length')
        except Exception as e:
            print e
            self.filesize = 0

        if self.url[0:4] == 'http' or self.url[0:3] == 'ftp':
            useragentcmd = "--header='User-Agent: %s'" % 'QuickTime/7.6.2 (verqt=7.6.2;cpu=IA32;so=Mac 10.5.8)'
            cmd = "wget %s -q '%s' -O '%s/%s' &" % (useragentcmd,
             self.url,
             config.plugins.airplayer.path.value,
             self.filename)
        else:
            self.session.open(MessageBox, _('This stream can not get saved on HDD\nProtocol %s not supported') % self.service.getPath()[0:5], MessageBox.TYPE_ERROR)
            return
        self.setSeekState(self.SEEK_STATE_PAUSE)
        self.localCache = True
        self.startNewServiceOnPlay = True
        self.StatusTimer = eTimer()
        self.StatusTimer.callback.append(self.UpdateStatus)
        self.StatusTimer.start(1000, True)
        self.dlactive = True
        self.backend.updateEventInfo('loading')
        print '[AirPlayMoviePlayer] execute command: ' + cmd
        self.container.execute(cmd)
        self.session.open(MessageBox, _('The Video will be downloaded to %s\n\nPlease wait until some MB are cached before hitting PLAY\nRecorded Videos from an iPhone/iPad need to be downloaded completely before playback is possible') % config.plugins.airplayer.path.value, type=MessageBox.TYPE_INFO, timeout=10)

    def UpdateStatus(self):
        if not self.dlactive:
            return
        lastSize = 0
        if fileExists(config.plugins.airplayer.path.value + self.filename, 'r'):
            lastSize = self.localsize
            self.localsize = os.path.getsize(config.plugins.airplayer.path.value + self.filename)
        else:
            self.localsize = 0
        if self.localsize > 0 and self.filesize > 0:
            percent = float(float(self.localsize) / float(self.filesize))
            percent = percent * 100.0
            self['bufferslider'].setValue(int(percent))
            if self.localsize - lastSize > 0:
                self['label_speed'].setText('DL-Speed: ' + self.formatKBits(self.localsize - lastSize))
        self.StatusTimer.start(1000, True)

    def DLfinished(self, retval):
        self.dlactive = False
        print '[AirPlayMoviePlayer] DL done'
        self['bufferslider'].setValue(int(100))
        self.setSeekState(self.SEEK_STATE_PLAY)

    def __evAudioDecodeError(self):
        try:
            currPlay = self.session.nav.getCurrentService()
            sTagAudioCodec = currPlay.info().getInfoString(iServiceInformation.sTagAudioCodec)
            print "[AirPlayMoviePlayer] audio-codec %s can't be decoded by hardware" % sTagAudioCodec
            Notifications.AddNotification(MessageBox, _("This Box can't decode %s streams!") % sTagAudioCodec, type=MessageBox.TYPE_INFO, timeout=10)
        except Exception:
            pass

    def __evVideoDecodeError(self):
        try:
            currPlay = self.session.nav.getCurrentService()
            sTagVideoCodec = currPlay.info().getInfoString(iServiceInformation.sTagVideoCodec)
            print "[AirPlayMoviePlayer] video-codec %s can't be decoded by hardware" % sTagVideoCodec
            Notifications.AddNotification(MessageBox, _("This Box can't decode %s streams!") % sTagVideoCodec, type=MessageBox.TYPE_INFO, timeout=10)
        except Exception:
            pass

    def __evPluginError(self):
        try:
            currPlay = self.session.nav.getCurrentService()
            message = currPlay.info().getInfoString(iServiceInformation.sUser + 12)
            print '[AirPlayMoviePlayer] PluginError ', message
            Notifications.AddNotification(MessageBox, _("Your Box can't decode this video stream!\n%s") % message, type=MessageBox.TYPE_INFO, timeout=10)
        except Exception:
            pass

    def __evEOF(self):
        print '[AirPlayMoviePlayer] got evEOF'
        try:
            err = self.session.nav.getCurrentService().info().getInfoString(iServiceInformation.sUser + 12)
            print '[AirPlayMoviePlayer] Error: ', err
            if err != '':
                Notifications.AddNotification(MessageBox, _("Your Box can't decode this video stream!\n%s") % err, type=MessageBox.TYPE_INFO, timeout=10)
        except Exception as e:
            print '[AirPlayMoviePlayer] Exception: ', e

    def seekWatcher(self, *args):
        print '[AirPlayMoviePlayer] seekWatcher started'
        try:
            while self is not None and self.start is not None:
                self.seekToStartPos()
                sleep(0.2)

        except Exception:
            pass

        print '[AirPlayMoviePlayer] seekWatcher finished'

    def startServiceOfUri(self, uri, useTsService = False):
        self.startNewServiceOnPlay = False
        if useTsService:
            sref = eServiceReference(1, 0, uri)
        else:
            sref = eServiceReference(self.backend.ENIGMA_SERVICE_ID, 0, uri)
        sref.setName('AirPlay')
        self.session.nav.playService(sref)

    def startServiceOfProxy(self, useTsService = False):
        if useTsService:
            self.startServiceOfUri('http://127.0.0.1:7099', True)
        else:
            self.startServiceOfUri('http://127.0.0.1:7099', False)

    def startServiceOfLocalFile(self):
        self.startServiceOfUri(config.plugins.airplayer.path.value + self.filename)

    def lockInfoBar(self):
        print '[AirPlayMoviePlayer] InfoBar is hiding ....'
        if self.startNewServiceOnPlay:
            self.doShow()

    def checkProxyStatus(self):
        print '[AirPlayMoviePlayer] checking prxy caching : ', self.proxyCaching, ' start new Service: ', self.startNewServiceOnPlay
        if self.proxyCaching == False:
            if self.proxyError:
                self.startServiceOfUri(self.url)
                return
            else:
                self.startServiceOfProxy(self.liveStream)
                return
        self.checkProxyTimer.start(500, True)

    def proxyWatcher(self, *args):
        print '[AirPlayMoviePlayer] proxy starting ....'
        self.liveStream = False
        self.m3u8Stream = False
        try:
            args = [PROXY_BINARY,
             self.url,
             config.plugins.airplayer.validationKey.value,
             config.plugins.airplayer.path.value]
            print 'starting proxy'
            print args[0], args[1]
            self.proxyProcess = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            print '[AirPlayMoviePlayer] proxy started ....'
            while self.proxyProcess.poll() == None:
                buff = self.proxyProcess.stdout.readline()
                self.proxyReady = True
                if len(buff) > 0:
                    if buff[:6] == 'rpos: ':
                        percent = int(buff[6:])
                        blockingCallFromMainThread(self['bufferslider'].setValue, percent)
                        if not self.liveStream and percent == 100:
                            self.proxyCaching = False
                    elif buff[:7] == 'cache: ':
                        kb = int(buff[7:])
                        mb = kb / 1024
                        blockingCallFromMainThread(self['label_cache'].setText, 'Cache: ' + self.formatKB(kb * 1024, 'B', 1))
                        print '[AirPlayMoviePlayer] cache is at ', mb, ' MB'
                        if self.liveStream == True and mb >= config.plugins.airplayer.cacheMbBeforeLivePlayback.value and self.startNewServiceOnPlay:
                            self.proxyCaching = False
                        if self.liveStream == False and mb >= config.plugins.airplayer.cacheMbBeforePlayback.value and self.startNewServiceOnPlay:
                            self.proxyCaching = False
                    elif buff[:19] == 'playing livestream!':
                        self.liveStream = True
                        print '[AirPlayMoviePlayer] playing livestream!'
                    elif buff[:13] == 'playing m3u8!':
                        self.m3u8Stream = True
                        print '[AirPlayMoviePlayer] playing m3u8 stream!'
                    elif buff[:8] == 'rspeed: ':
                        rspeed = int(buff[8:]) * 1000
                        blockingCallFromMainThread(self['label_speed'].setText, 'DL-Speed: ' + self.formatKBits(rspeed))
                    elif buff[:7] == 'Error: ':
                        blockingCallFromMainThread(Notifications.AddNotification, MessageBox, _('The Proxy encountered an Error: %s, starting direct playback now!') % buff[7:], type=MessageBox.TYPE_INFO, timeout=10)
                        self.proxyError = True
                        self.proxyCaching = False
                    else:
                        print '[AirPlayMoviePlayer] Proxy: ', buff

            print '[AirPlayMoviePlayer] proxy done'
        except Exception as e:
            print '[AirPlayMoviePlayer] error in proxy: ', e
            traceback.print_exc()
            if self.proxyCaching == True:
                blockingCallFromMainThread(Notifications.AddNotification, MessageBox, _('Starting the Proxy failed: %s, starting direct playback now!') % e, type=MessageBox.TYPE_INFO, timeout=10)
                self.proxyError = True
                self.proxyCaching = False
            else:
                print '[AirPlayMoviePlayer] assume error comes from killing process after eof '

        print '[AirPlayMoviePlayer] proxy thread done'

    def seekToStartPos(self):
        time = 0
        try:
            if self.start is not None and config.plugins.airplayer.setSeekOnStart.value:
                service = self.session.nav.getCurrentService()
                seek = service and service.seek()
                if seek != None:
                    r = seek.getLength()
                    if not r[0]:
                        print '[AirPlayMoviePlayer] got duration'
                        if r[1] == 0:
                            print '[AirPlayMoviePlayer] duration 0'
                            return
                        length = r[1]
                        r = seek.getPlayPosition()
                        if not r[0]:
                            print 'playbacktime ', r[1]
                            if r[1] < 90000:
                                print 'do not seek yet', r[1]
                                return
                        else:
                            return
                        time = length * self.start
                        print '[AirPlayMoviePlayer] seeking to', time, ' length ', length, ''
                        self.start = None
                        if time < 2700000:
                            print '[AirPlayMoviePlayer] skip seeking < 30s'
                            return
                        blockingCallFromMainThread(self.doSeek, int(time))
        except Exception:
            pass

    def formatKBits(self, value, ending = 'Bit/s', roundNumbers = 2):
        bits = value * 8
        if bits > 1048576:
            return str(round(float(bits) / float(1048576), roundNumbers)) + ' M' + ending
        elif bits > 1024:
            return str(round(float(bits) / float(1024), roundNumbers)) + ' K' + ending
        else:
            return str(bits) + ' ' + ending

    def formatKB(self, value, ending = 'B', roundNumbers = 2):
        byte = value
        if byte > 1048576:
            return str(round(float(byte) / float(1048576), roundNumbers)) + ' M' + ending
        elif byte > 1024:
            return str(round(float(byte) / float(1024), roundNumbers)) + ' K' + ending
        else:
            return str(byte) + ' ' + ending

    def checkForUpdate(self, *args):
        url = self.backend.updater.checkForUpdate(self.url, 1)
        if url != '' and url != 'up to date':
            blockingCallFromMainThread(self['label_update'].setText, 'Update Available')

    def setSeekState(self, state, dummy = False):
        if self.startNewServiceOnPlay and state == self.SEEK_STATE_PLAY:
            if self.useProxy:
                if self.proxyCaching == False:
                    print '[AirPlayMoviePlayer] start Proxy cache now'
                    self.startServiceOfProxy(self.liveStream)
            else:
                print '[AirPlayMoviePlayer] start downloaded file now'
                self.startServiceOfLocalFile()
            super(AirPlayMoviePlayer, self).setSeekState(self.SEEK_STATE_PLAY)
        else:
            super(AirPlayMoviePlayer, self).setSeekState(state)
        try:
            if state == self.SEEK_STATE_PAUSE:
                if self.useProxy:
                    self.backend.updateEventInfo('loading')
                else:
                    self.backend.updateEventInfo('paused')
            if state == self.SEEK_STATE_PLAY:
                self.backend.updateEventInfo('playing')
        except Exception as e:
            print e

    def processPlayerStop(self):
        try:
            self.backend.updateEventInfo('stopped')
            self.session.openWithCallback(self.leavePlayerConfirmed, MessageBox, _('Stop AirPlayer playback?'), MessageBox.TYPE_YESNO, timeout=10)
        except Exception:
            self.leavePlayerConfirmed(True)

    def leavePlayer(self):
        self.leavePlayerConfirmed(True)

    def leavePlayerConfirmed(self, answer):
        if answer:
            print '[AirPlayMoviePlayer] stopping MoviePlayer'
            self.backend.MovieWindow = None
            if self.localCache:
                self.container.kill()
                eBackgroundFileEraser.getInstance().erase(config.plugins.airplayer.path.value + self.filename)
                self.StatusTimer.stop()
            if self.lastservice and self.lastservice is not None:
                self.backend.updateEventInfo('stopped')
            else:
                print '[AirPlayMoviePlayer] lastService is None, not sending stop command'
            self.backend.updateEventInfo('stopped')
            if self.backend.ENIGMA_SERVICE_ID == self.backend.ENIGMA_SERVICEAZ_ID:
                self.session.nav.stopService()
                open('/proc/player', 'w').write('1')
                import time
                time.sleep(2)
            try:
                print '[AirPlayMoviePlayer] try to remove proxy cache'
                os.system('rm %s/AirPlayerChunk* &' % config.plugins.airplayer.path.value)
            except Exception:
                pass

            if self.proxyProcess != None:
                try:
                    self.proxyProcess.kill()
                except Exception:
                    pass

            self.close()

    def doEofInternal(self, playing):
        print '[AirPlayMoviePlayer] doEofInternal'
        if self.liveStream:
            print '[AirPlayMoviePlayer] got evEOF in live-stream ignoreing'
            return
        print '[AirPlayMoviePlayer] super.doEofInternal'
        self.backend.updateEventInfo('stopped')
        self.backend.stop_playing()

    def isPlaying(self):
        try:
            if self.seekstate != self.SEEK_STATE_PLAY:
                return False
            return True
        except Exception:
            return False

    def showMovies(self):
        pass