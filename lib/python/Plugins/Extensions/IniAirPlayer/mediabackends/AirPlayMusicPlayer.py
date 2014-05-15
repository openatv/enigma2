# 2013.05.22 09:49:41 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/mediabackends/AirPlayMusicPlayer.py
"""
Created on 17.04.2013

@author: matthias
"""
from Components.AVSwitch import AVSwitch
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.Sources.StaticText import StaticText
from Components.config import config
from Screens.Screen import Screen
from enigma import ePoint, eServiceReference, getDesktop, ePicLoad, eTimer, eBackgroundFileEraser
from thread import start_new_thread
import os
from ctypes import *
from helper import blockingCallFromMainThread

class AirPlayMusicPlayer(Screen):

    def __init__(self, session, backend, message, lastservice = None):
        self.backend = backend
        backend.MusicWindow = self
        self.session = session
        self.skinName = 'AirPlayMusicPlayer'
        print '[AirPlayMusicPlayer] starting AirTunesPlayer'
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['OkCancelActions', 'MoviePlayerActions'], {'cancel': self.Exit,
         'leavePlayer': self.Exit}, -1)
        self['label_update'] = StaticText('')
        self['label_message'] = Label()
        self['label_message'].setText(message)
        self['label_title'] = Label()
        self['label_album'] = Label()
        self['label_interpret'] = Label()
        self['label_title'].setText('No')
        self['label_album'].setText('Metadata')
        self['label_interpret'].setText('')
        self.progress = Slider(0, 100)
        self.progress.setValue(0)
        self['progress'] = self.progress
        self['progress'].setValue(0)
        self.runtime = None
        self.seconds = None
        self.libairtunes = None
        self.lastservice = lastservice or self.session.nav.getCurrentlyPlayingServiceReference()
        self.session.nav.stopService()
        if config.plugins.airplayer.audioBackend.value == 'proxy':
            if self.backend.ENIGMA_SERVICE_ID == self.backend.ENIGMA_SERVICEAZ_ID:
                self.session.nav.stopService()
                open('/proc/player', 'w').write('0')
                open('/proc/player', 'w').write('2')
            sref = eServiceReference(self.backend.ENIGMA_SERVICE_ID, 0, 'http://127.0.0.1:7098/stream.wav')
            sref.setName('AirTunes')
            self.session.nav.playService(sref)
        start_new_thread(self.checkForUpdate, (self,))
        self.x_pos = None
        self.y_pos = None
        self.x_dir = 5
        self.y_dir = 5
        self.WindowMoveTimer = eTimer()
        self.WindowMoveTimer.timeout.get().append(self.moveWindow)
        if config.plugins.airplayer.screensaverEnabled.value:
            self.WindowMoveTimer.start(10000, True)
        self['cover'] = Pixmap()
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.finish_decode)
        self.onLayoutFinish.append(self.setPicloadConf)
        self.bgcolor = '#00000000'
        self.progressTimer = eTimer()
        self.progressTimer.timeout.get().append(self.progressCallback)
        self.parseMetadata()

    def moveWindow(self):
        try:
            if self.x_pos is None or self.y_pos is None:
                self.x_pos = self.instance.position().x()
                self.y_pos = self.instance.position().y()
            if self.instance.size().width() + 20 >= getDesktop(0).size().width() and self.instance.size().height() + 20 >= getDesktop(0).size().height():
                return
            self.x_pos += self.x_dir
            self.y_pos += self.y_dir
            if self.x_dir > 0 and self.x_pos + self.instance.size().width() >= getDesktop(0).size().width():
                self.x_dir = -self.x_dir
            elif self.x_dir < 0 and self.x_pos <= 0:
                self.x_dir = -self.x_dir
            if self.y_dir > 0 and self.y_pos + self.instance.size().height() >= getDesktop(0).size().height():
                self.y_dir = -self.y_dir
            elif self.y_dir < 0 and self.y_pos <= 0:
                self.y_dir = -self.y_dir
            self.instance.move(ePoint(self.x_pos, self.y_pos))
        except Exception:
            pass

        try:
            self.WindowMoveTimer.start(150, True)
        except Exception:
            pass

    def getScale(self):
        return AVSwitch().getFramebufferScale()

    def parseMetadata(self):
        try:
            if not os.path.exists(config.plugins.airplayer.path.value + '/metadata.bin'):
                print '[AirPlayMusicPlayer] No Metadata found'
                return
            if self.libairtunes is None:
                self.libairtunes = cdll.LoadLibrary('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/libairtunes.so.0')
                print '[AirPlayMusicPlayer] loading lib done'
            response = create_string_buffer(1024)
            self.libairtunes.getMetadata('asal', config.plugins.airplayer.path.value + '/metadata.bin', response)
            if response.value is not None and response.value != '':
                self['label_album'].setText(response.value)
                print '[AirPlayMusicPlayer] album: ', response.value
            self.libairtunes.getMetadata('minm', config.plugins.airplayer.path.value + '/metadata.bin', response)
            if response.value is not None and response.value != '':
                self['label_title'].setText(response.value)
                print '[AirPlayMusicPlayer] title: ', response.value
            self.libairtunes.getMetadata('asar', config.plugins.airplayer.path.value + '/metadata.bin', response)
            if response.value is not None and response.value != '':
                self['label_interpret'].setText(response.value)
                print '[AirPlayMusicPlayer] artist: ', response.value
        except Exception as e:
            print '[AirPlayMusicPlayer] loading lib failed'
            print e
            self.libairtunes = None
            return False

    def setProgress(self, seconds, runtime = None):
        self.seconds = seconds
        if runtime is not None:
            self.runtime = runtime
        if self.runtime is not None and self.runtime != 0:
            self.progress.setValue(100 * seconds / self.runtime)
        else:
            self.progress.setValue(0)
        self.progressTimer.stop()
        self.progressTimer.start(1000, True)

    def progressCallback(self):
        if self.seconds is not None:
            self.setProgress(self.seconds + 1)

    def setPicloadConf(self):
        sc = self.getScale()
        self.picload.setPara([self['cover'].instance.size().width(),
         self['cover'].instance.size().height(),
         sc[0],
         sc[1],
         0,
         1,
         self.bgcolor])
        if os.path.exists(config.plugins.airplayer.path.value + '/cover.jpg'):
            self.start_decode()
        else:
            self.start_decode('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/cover.png')

    def ShowCover(self):
        if self.currPic != None:
            self['cover'].instance.setPixmap(self.currPic.__deref__())

    def finish_decode(self, picInfo = ''):
        ptr = self.picload.getData()
        if ptr != None:
            self.currPic = ptr
            self.ShowCover()

    def start_decode(self, filename = None):
        if filename is None or filename == '':
            filename = config.plugins.airplayer.path.value + '/cover.jpg'
        self.picload.startDecode(filename)

    def checkForUpdate(self, *args):
        url = self.backend.updater.checkForUpdate('AirTunes', 3)
        if url != '' and url != 'up to date':
            blockingCallFromMainThread(self['label_update'].setText, 'Update Available')

    def leavePlayer(self):
        self.leavePlayerConfirmed(True)

    def leavePlayerConfirmed(self, answer):
        if answer:
            self.Exit()

    def Exit(self):
        print '[AirPlayMusicPlayer] stopping AirTunesPlayer'
        self.backend.MusicWindow = None
        if self.lastservice and self.lastservice is not None:
            self.backend.updateEventInfo('stopped')
        else:
            print '[AirPlayMusicPlayer] lastService is None, not sending stop command'
        os.system('killall hairtunes')
        os.system('killall atproxy')
        try:
            config.av.downmix_ac3.value = self.backend.downmix_ac3
            config.av.downmix_ac3.save()
        except Exception as e:
            print '[AirPlayMusicPlayer] rest downmix failed: ', e

        if self.backend.ENIGMA_SERVICE_ID == self.backend.ENIGMA_SERVICEAZ_ID:
            self.session.nav.stopService()
            open('/proc/player', 'w').write('1')
            import time
            time.sleep(2)
        if self.lastservice and self.lastservice is not None:
            self.session.nav.playService(self.lastservice)
        eBackgroundFileEraser.getInstance().erase(config.plugins.airplayer.path.value + '/cover.jpg')
        eBackgroundFileEraser.getInstance().erase(config.plugins.airplayer.path.value + '/metadata.bin')
        self.close()
