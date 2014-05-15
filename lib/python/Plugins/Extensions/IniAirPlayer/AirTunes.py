# 2013.05.22 08:34:12 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/AirTunes.py
from rtsp import RTSPSite, RTSPResource
from twisted.internet import reactor
import os
import base64
import subprocess
from ctypes import *
from Components.config import config
from Tools import Notifications
from Screens.MessageBox import MessageBox
from enigma import eTimer
from thread import start_new_thread
import time
from mediabackends.helper import blockingCallFromMainThread
HAIRTUNES_BINARY = '/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/hairtunes'
AIRTUNES_PROXY_BINARY = '/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/atproxy'

class AirtunesProtocolHandler(RTSPResource):

    def __init__(self, media_backend):
        self._http_server = None
        self.backend = media_backend
        self.aesiv = None
        self.rsaaeskey = None
        self.fmtp = None
        self.process = None
        self.validationMessage = ''
        try:
            self.libairtunes = cdll.LoadLibrary('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/libairtunes.so.0')
            print '[AirTunes] loading lib done'
        except Exception as e:
            print '[AirTunes] loading lib failed'
            print e
            self.libairtunes = None

    def start(self):
        try:
            site = RTSPSite(self)
            reactor.listenTCP(5000, site, interface='0.0.0.0')
        except Exception as ex:
            print ('Exception(Can be ignored): ' + str(ex), __name__, 'W')

    def handleChallengeResponse(self, request):
        response = create_string_buffer(1024)
        if request.getHeader('Apple-Challenge'):
            if self.libairtunes is not None:
                self.libairtunes.createAppleResponse(request.getHeader('Apple-Challenge'), response, config.plugins.airplayer.interface.value)
                if response.value is not None and response.value != '':
                    request.setHeader('Apple-Response', response.value)
                else:
                    Notifications.AddNotification(MessageBox, _("Apple Response can't be calculated, AirTunes Audio-Streaming is not possible"), type=MessageBox.TYPE_INFO, timeout=10)
            else:
                Notifications.AddNotification(MessageBox, _('AirTunes Audio-Streaming is not implemented for this Boxtype'), type=MessageBox.TYPE_INFO, timeout=10)

    def render_OPTIONS(self, request):
        try:
            from Screens.Standby import inStandby
            if inStandby != None and config.plugins.airplayer.allowWakeupFromStandby.value:
                inStandby.Power()
        except Exception:
            pass

        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] render OPTIONS'
        request.setHeader('Public', 'ANNOUNCE, SETUP, RECORD, PAUSE, FLUSH, TEARDOWN, OPTIONS, GET_PARAMETER, SET_PARAMETER')
        request.setHeader('Audio-Jack-Status', 'connected; type=analog')
        self.handleChallengeResponse(request)
        return ''

    def render_ANNOUNCE(self, request):
        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] render ANNOUNCE'
        self.handleChallengeResponse(request)
        self.backend.updater.checkPremiumValidation()
        content = request.content.read()
        for row in content.split('\n'):
            row = row.strip()
            if row[:2] != 'a=':
                continue
            row = row[2:]
            seppos = row.find(':')
            key = row[:seppos].strip()
            value = row[seppos + 1:].strip()
            if key == 'aesiv' or key == 'rsaaeskey':
                if value[-2:] != '==':
                    value += '=='
            if key == 'aesiv':
                self.aesiv = value
                print 'aesiv: ', self.aesiv
            elif key == 'rsaaeskey':
                print 'decrypt rsaaeskey', value
                response = create_string_buffer(1024)
                self.libairtunes.decryptRSAAESKey(value, response)
                self.rsaaeskey = response.value
                print 'rsaaeskey: ', self.rsaaeskey
            elif key == 'fmtp':
                self.fmtp = value

        print 'announce finish'
        return ''

    def render_SETUP(self, request):
        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] render SETUP'
        self.handleChallengeResponse(request)
        if self.aesiv is not None and self.rsaaeskey is not None and self.fmtp is not None and 'transport' in request.received_headers:
            print '[AirTunes] alles da'
            if self.process is not None:
                print '[AirTunes] killing old instance of hairtunes'
                self.process.kill()
                self.process = None
            data_port = 0
            timing_port = 59010
            control_port = 59012
            response = create_string_buffer(1024)
            if not os.path.exists(HAIRTUNES_BINARY) and not os.path.exists(AIRTUNES_PROXY_BINARY):
                Notifications.AddNotification(MessageBox, _('AirTunes Audio-Streaming is not available on this Boxtype'), type=MessageBox.TYPE_INFO, timeout=10)
                return
            for row in request.received_headers['transport'].split(';'):
                row = row.strip()
                seppos = row.find('=')
                if seppos == -1:
                    continue
                key = row[:seppos].strip()
                value = row[seppos + 1:].strip()
                if key == 'timing_port':
                    timing_port = int(value)
                elif key == 'control_port':
                    control_port = int(value)

            aesiv_plain = base64.b64decode(self.aesiv)
            aesiv = ''
            for ch in aesiv_plain:
                aesiv += '%02X' % ord(ch)

            try:
                print '[AirTunes] setting downmix'
                blockingCallFromMainThread(self.backend.setDownmix)
            except Exception as e:
                print '[AirTunes] setting downmix failed: ', e

            if config.plugins.airplayer.audioBackend.value == 'proxy':
                binary = AIRTUNES_PROXY_BINARY
            else:
                binary = HAIRTUNES_BINARY
            args = [binary,
             'aesiv',
             aesiv,
             'aeskey',
             self.rsaaeskey,
             'valid',
             config.plugins.airplayer.validationKey.value,
             'fmtp',
             self.fmtp,
             'cport',
             str(control_port),
             'tport',
             str(timing_port),
             'dport',
             '0']
            print '[AirTunes] starting AirTunes reciever'
            print args[0], ' ', args[1], ' ', args[2], ' ', args[3], ' ', args[4], ' ', args[5], ' ', args[6], ' ', args[7], ' ', args[8], ' ', args[9], ' ', args[10], ' ', args[11], ' ', args[12]
            self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            while self.process.poll() == None:
                buff = self.process.stdout.readline()
                if len(buff) > 0:
                    if buff[:6] == 'port: ':
                        data_port = buff[6:-1]
                        break

            if data_port != 0:
                request.setHeader('transport', request.received_headers['transport'] + ';server_port=' + str(data_port))
                request.setHeader('session', 'DEADBEEF')
                if config.plugins.airplayer.delayAudioPlayback.value:
                    print '[AirTunes] starting AudioPlayer in one sec'
                    start_new_thread(self.playerStarter, (self,))
                else:
                    print '[AirTunes] starting AudioPlayer now'
                print 'player started: '
            else:
                request.setHeader('transport', request.received_headers['transport'] + ';server_port=' + str(9999))
                request.setHeader('session', 'DEADBEEF')
                Notifications.AddNotification(MessageBox, _('AirTunes Audio-Streaming is not possible on this Boxtype'), type=MessageBox.TYPE_INFO, timeout=10)
        else:
            print '[AirTunes] missing some parameters'
            if self.aesiv is not None:
                print '[AirTunes] aesiv:', self.aesiv
            if self.rsaaeskey is not None:
                print '[AirTunes] rsaaeskey:', self.rsaaeskey
            if self.fmtp is not None:
                print '[AirTunes] fmtp:', self.fmtp
            if 'transport' in request.received_headers:
                print '[AirTunes] transport:', request.received_headers['transport']
        print '[AirTunes] setup done'
        return ''

    def playerStarter(self, *args):
        time.sleep(1)

    def render_RECORD(self, request):
        self.render_startCSeqDate(request, request.method)
        self.handleChallengeResponse(request)
        print '[AirTunes] render RECORD'
        request.setHeader('Audio-Jack-Status', 'connected; type=analog')
        return ''

    def render_SET_PARAMETER(self, request):
        self.render_startCSeqDate(request, request.method)
        self.handleChallengeResponse(request)
        print '[AirTunes] render SET_PARAMETER'
        try:
            contentType = request.getHeader('Content-Type')
            if contentType == 'image/jpeg':
                print '[AirTunes] Got Cover'
                request.content.seek(0)
                file(config.plugins.airplayer.path.value + '/cover.jpg', 'wb').write(request.content.read())
                blockingCallFromMainThread(self.backend.updateAirTunesCover)
            elif contentType == 'application/x-dmap-tagged':
                print '[AirTunes] Got MetaData'
                file(config.plugins.airplayer.path.value + '/metadata.bin', 'wb').write(request.content.read())
                blockingCallFromMainThread(self.backend.updateAirTunesMetadata)
            else:
                content = request.content.read()
                if content[:7] == 'volume:':
                    value = content[8:]
                    print '[AirTunes] Got Volue: ', value
                    vol = 100 - int(float(value) * -3.3333333333)
                    if vol < 0:
                        vol = 0
                    blockingCallFromMainThread(self.backend.setVolume, vol)
                elif content[:9] == 'progress:':
                    value = content[9:]
                    print '[AirTunes] Got Progress: ', value
                    try:
                        nums = value.split('/')
                        start = int(nums[0])
                        runtime = (int(nums[2]) - start) / 44100
                        seconds = (int(nums[1]) - start) / 44100
                        blockingCallFromMainThread(self.backend.updateAirTunesProgress, seconds, runtime)
                    except Exception as ex:
                        print ('Exception during progress calc: ' + str(ex), __name__, 'W')

        except Exception as ex:
            print ('Exception during Volume calc: ' + str(ex), __name__, 'W')

        request.setHeader('Audio-Jack-Status', 'connected; type=analog')
        return ''

    def render_GET_PARAMETER(self, request):
        self.handleChallengeResponse(request)
        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] render GET_PARAMETER'
        content = request.content.read()
        print '[AirTunes] content: ', content
        request.setHeader('Audio-Jack-Status', 'connected; type=analog')
        return ''

    def render_FLUSH(self, request):
        self.handleChallengeResponse(request)
        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] FLUSH'
        if self.process is not None and self.process.poll() is None:
            self.process.stdin.write('flush\n')
        return ''

    def render_TEARDOWN(self, request):
        self.handleChallengeResponse(request)
        self.render_startCSeqDate(request, request.method)
        print '[AirTunes] TEARDOWN'
        if self.process != None and self.process.poll() == None:
            self.process.stdin.write('exit\n')
            self.process.wait()
        self.process = None
        request.setHeader('connection', 'close')
        blockingCallFromMainThread(self.backend.stop_airtunes)
        return ''