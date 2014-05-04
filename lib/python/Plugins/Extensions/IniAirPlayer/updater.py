# 2013.05.22 08:34:58 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/updater.py
from urllib2 import urlopen
import urllib2
from Components.config import config
from Screens.Console import Console as SConsole
import time
from Screens.MessageBox import MessageBox
from Components.Network import iNetwork
from ctypes import create_string_buffer, cdll

def getBoxType():
    model = None
    try:
        fd = open('/proc/stb/info/model', 'r')
        model = fd.readline().strip()
        fd.close()
    except Exception:
        pass

    try:
        fd = open('/proc/stb/info/vumodel', 'r')
        model = 'vu+' + fd.readline().strip()
        fd.close()
        print '[AirPlayUpdater] vumodel:', model
    except Exception:
        pass

    try:
        fd = open('/proc/stb/info/boxtype', 'r')
        model = fd.readline().strip()
        fd.close()
        print '[AirPlayUpdater] boxtype:', model
    except Exception:
        pass

    print '[AirPlayUpdater] model:', model
    return model


class Updater(object):

    def __init__(self, session = None):
        self.model = ''
        self.token = None
        self.readMac()
        self.readBoxType()
        self.checkBoxID()
        self.checkPremiumValidation()
        self.link = ''
        self.session = session

    def readMac(self):
        print '[AirPlayUpdater] reading interface'
        self.token = iNetwork.getAdapterAttribute('eth0', 'mac')
        if self.token is None or self.token == '':
            self.token = self.readMacFromLib()
        print '[AirPlayUpdater] running on interface ', self.token

    def readMacFromLib(self):
        try:
            self.libairtunes = cdll.LoadLibrary('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/libairtunes.so.0')
            print '[AirPlayUpdater] loading lib done'
            response = create_string_buffer(1024)
            self.libairtunes.getMACAddr('eth0', response)
            print '[AirPlayUpdater] reading from lib done'
            if response.value is not None and response.value != '':
                print '[AirPlayUpdater] interface was read'
                return response.value
        except Exception as e:
            print '[AirPlayUpdater] reading from lib failed ', e
            return

    def readBoxType(self):
        try:
            self.model = getBoxType()
            print '[AirPlayUpdater] running on model:', self.model
        except Exception as e:
            print '[AirPlayUpdater] error ocurred:', e

    def readBoxID(self):
        try:
            if self.token is None:
                self.readMac()
            url = 'http://airplayer.toeppe.com/boxid.php?model=' + urllib2.quote(self.model)
            url += '&version=' + config.plugins.airplayer.version.value
            if self.token != None:
                url += '&token=' + urllib2.quote(self.token)
            fd = urlopen(url)
            data = fd.read()
            fd.close()
            config.plugins.airplayer.boxID.value = data
            config.plugins.airplayer.save()
            print '[AirPlayUpdater] BoxID is', config.plugins.airplayer.boxID.value
        except Exception as e:
            print '[AirPlayUpdater] error ocurred:', e

    def isAzBox(self):
        if self.model == 'premium':
            return True
        if self.model == 'premium+':
            return True
        if self.model == 'ultra':
            return True
        if self.model == 'me':
            return True
        if self.model == 'minime':
            return True
        return False

    def checkForUpdate(self, url, stype, token = None):
        try:
            if self.token is None:
                self.readMac()
            tokenStr = ''
            if token is not None:
                tokenStr = '&token=' + urllib2.quote(token)
            elif self.token is not None:
                tokenStr = '&token=' + urllib2.quote(self.token)
            url = 'http://airplayer.toeppe.com/update.php?model=' + urllib2.quote(self.model)
            url += '&version=' + config.plugins.airplayer.version.value
            url += '&boxid=' + config.plugins.airplayer.boxID.value
            url += '&type=' + str(stype)
            url += '&url=' + urllib2.quote(url)
            url += '&arch=' + urllib2.quote(config.plugins.airplayer.arch.value)
            url += tokenStr
            fd = urlopen(url)
            data = fd.read()
            fd.close()
            self.link = data
            return data
        except Exception as e:
            print '[AirPlayUpdater] error ocurred:', e
            return ''

    def checkPremiumValidation(self):
        try:
            print '[AirPlayUpdater] check validation'
            if self.token is None:
                self.readMac()
            url = 'http://airplayer.toeppe.com/validate.php?model=' + urllib2.quote(self.model)
            url += '&version=' + config.plugins.airplayer.version.value
            url += '&boxid=' + config.plugins.airplayer.boxID.value
            if self.token != None:
                url += '&token=' + urllib2.quote(self.token)
            url += '&key=' + urllib2.quote(config.plugins.airplayer.premiuimKey.value)
            fd = urlopen(url)
            data = fd.read()
            fd.close()
            if data is not None:
                config.plugins.airplayer.validationKey.value = data
                print '[AirPlayUpdater] validationKey', config.plugins.airplayer.validationKey.value
            self.link = data
            return data
        except Exception as e:
            print '[AirPlayUpdater] error ocurred:', e
            return ''

    def getChangeLog(self):
        try:
            if self.token is None:
                self.readMac()
            url = 'http://airplayer.toeppe.com/changelog.php?model=' + urllib2.quote(self.model)
            url += '&version=' + config.plugins.airplayer.version.value
            url += '&boxid=' + config.plugins.airplayer.boxID.value
            if self.token != None:
                url += '&token=' + urllib2.quote(self.token)
            fd = urlopen(url)
            data = fd.read()
            fd.close()
            return data
        except Exception as e:
            print '[AirPlayUpdater] error ocurred:', e
            return ''

    def checkBoxID(self):
        if config.plugins.airplayer.boxID.value == '':
            self.readBoxID()
        else:
            self.checkForUpdate('', 0, self.token)

    def startUpdateCallback(self, answer = True):
        if answer:
            self.startUpdate()

    def startUpdate(self):
        print '[AirPlayUpdater] starting update'
        if self.link[:7] == 'http://' or self.link[:8] == 'https://':
            cmd = '\nBIN=""\nopkg > /dev/null 2>/dev/null\nif [ $? == "1" ]; then\n BIN="opkg"\nelse\n ipkg > /dev/null 2>/dev/null\n if [ $? == "1" ]; then\n  BIN="ipkg"\n fi\nfi\necho "Binary: $BIN"\n\nif [ $BIN != "" ]; then\n $BIN update\n killall zeroconfig\n killall hairtunes\n killall proxy\n $BIN remove enigma2-plugin-extensions-airplayer\n if [ $BIN == "opkg" ]; then\n   OPARAM="--force-overwrite --force-downgrade --force-reinstall"\n else\n   OPARAM="-force-overwrite -force-downgrade -force-reinstall"\n fi\n ( $BIN install %s $OPARAM; )\nfi' % str(self.link)
            self.session.open(SConsole, 'Excecuting command:', [cmd], self.finishupdate)
        else:
            print '[AirPlayUpdater] invalid link skipping update url ', self.link

    def finishupdate(self):
        time.sleep(10)
        self.session.openWithCallback(self.e2restart, MessageBox, _('Enigma2 must be restarted!\nShould Enigma2 now restart?'), MessageBox.TYPE_YESNO, timeout=5)

    def e2restart(self, answer):
        if answer is True:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)
        else:
            self.close()