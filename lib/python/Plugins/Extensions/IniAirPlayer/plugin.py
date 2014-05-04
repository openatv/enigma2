# 2013.05.22 08:35:25 UTC
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/plugin.py
import os
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from mediabackends.E2MediaBackend import E2MediaBackend
from protocol_handler import AirplayProtocolHandler
from AirTunes import AirtunesProtocolHandler
from Components.config import config
from Components.config import ConfigSelection
from Components.config import getConfigListEntry
from Components.config import ConfigInteger
from Components.config import ConfigText
from Components.config import ConfigYesNo
from Components.Network import iNetwork
from Screens.MessageBox import MessageBox
from Components.Label import Label
from updater import Updater, getBoxType
from Tools import Notifications
currentVersion = '0.3.9'
currentArch = 'mips32el'

def getDefaultMediaBackend():
    mbe = 'proxy'
    model = getBoxType()
    if model[:3] == 'vu+':
        return 'alsa'
    return mbe


def getDefaultDelayAudioPlayback():
    default = False
    if currentArch == 'sh4' or currentArch == 'sh4p27':
        default = True
    model = getBoxType()
    if model[:2] == 'et':
        default = True
    return default


defaultMediaBackend = getDefaultMediaBackend()
defaultDelayAudioPlayback = getDefaultDelayAudioPlayback()
config.plugins.airplayer.startuptype = ConfigYesNo(default=False)
config.plugins.airplayer.name = ConfigText(default='STB AirPlayer', fixed_size=False)
config.plugins.airplayer.path = ConfigText(default='/tmp/', fixed_size=False)
config.plugins.airplayer.audioBackend = ConfigSelection(default=defaultMediaBackend, choices={'proxy': _('proxy'),
 'alsa': _('ALSA')})
config.plugins.airplayer.setSeekOnStart = ConfigYesNo(default=True)
config.plugins.airplayer.version = ConfigText(default=currentVersion)
config.plugins.airplayer.arch = ConfigText(default=currentArch)
config.plugins.airplayer.boxID = ConfigText(default='')
config.plugins.airplayer.premiuimKey = ConfigText(default='', fixed_size=False)
config.plugins.airplayer.validationKey = ConfigText(default='', fixed_size=False)
config.plugins.airplayer.stopTVOnPicture = ConfigYesNo(default=True)
config.plugins.airplayer.allowiOSVolumeControl = ConfigYesNo(default=True)
config.plugins.airplayer.showStartUpInfo = ConfigYesNo(default=False)
config.plugins.airplayer.useProxyIfPossible = ConfigYesNo(default=False)
config.plugins.airplayer.allowWakeupFromStandby = ConfigYesNo(default=True)
config.plugins.airplayer.screensaverEnabled = ConfigYesNo(default=True)
config.plugins.airplayer.autoUpdate = ConfigYesNo(default=False)
config.plugins.airplayer.cacheMbBeforePlayback = ConfigInteger(default=5)
config.plugins.airplayer.cacheMbBeforeLivePlayback = ConfigInteger(default=5)
config.plugins.airplayer.delayAudioPlayback = ConfigYesNo(default=defaultDelayAudioPlayback)
config.plugins.airplayer.save()
global_session = None
global_protocol_handler = None
global_media_backend = None
global_airtunes_protocol_handler = None

class AP_MainMenu(Screen, ConfigListScreen):
    skin = '''<screen name="AP_MainMenu" title="AirPlayer Settings" position="center,center" size="565,370">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="text" position="5,50" size="555,250" halign="center" valign="center" font="Regular;20" />
	      </screen>'''

    def __init__(self, session, args = None):
        self.skin = AP_MainMenu.skin
        Screen.__init__(self, session)
        self._session = session
        self._hasChanged = False
        self['key_red'] = StaticText(_('Settings'))
        self['key_green'] = StaticText(_('Update'))
        self['key_yellow'] = StaticText(_('Start Service'))
        self['key_blue'] = StaticText(_('Stop Service'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'red': self.keySettings,
         'green': self.keyUpdate,
         'blue': self.keyStop,
         'yellow': self.keyStart,
         'cancel': self.close}, -2)
        self['text'] = Label()
        self['text'].setText('AirPlayer Enigma2 Plugin\nVersion: %s\n\nThis Plugin is based on AirPlayer from PascalW(https://github.com/PascalW/Airplayer)\n\nPlease visit our Support-Board at http://www.airplayer.biz\n\nIf you like this Project and want to support it\n please consider donating via PayPal to\ntoeppe@t-online.de' % config.plugins.airplayer.version.value)
        self.onLayoutFinish.append(self.setCustomTitle)

    def _changed(self):
        self._hasChanged = True

    def keyStart(self):
        global global_session
        print '[AirPlayer] pressed start'
        print '[AirPlayer] trying to stop if running'
        stopWebserver(global_session)
        print '[AirPlayer] trying to start'
        startWebserver(global_session)
        self.session.openWithCallback(self.close, MessageBox, _('Service successfully started'), MessageBox.TYPE_INFO, timeout=5)

    def keyStop(self):
        print '[AirPlayer] pressed stop'
        stopWebserver(global_session)
        self.session.openWithCallback(self.close, MessageBox, _('Service successfully stoped'), MessageBox.TYPE_INFO, timeout=5)

    def keySettings(self):
        print '[AirPlayer] open Settings'
        self.session.open(AP_ConfigScreen)

    def keyUpdate(self):
        print '[AirPlayer] open Update Screen'
        self.session.open(AP_UpdateScreen)

    def setCustomTitle(self):
        self.setTitle(_('AirPlayer'))


class AP_UpdateScreen(Screen, ConfigListScreen):
    skin = '<screen name="AP_MainMenu" title="AirPlayer Settings" position="center,center" size="565,370">\n\t\t<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />\n\t\t<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />\n\t\t<widget name="info" position="5,50" size="555,45" halign="center" valign="center" font="Regular;20" />\n\t\t<ePixmap pixmap="skin_default/div-h.png" position="0,95" zPosition="1" size="565,2" />\n\t\t<widget name="changelog" position="5,100" size="555,250" halign="top" valign="left" font="Regular;20" />\n\t</screen>'

    def __init__(self, session, args = None):
        self.skin = AP_UpdateScreen.skin
        Screen.__init__(self, session)
        self._session = session
        self._hasChanged = False
        self.updater = Updater(session)
        self['key_red'] = StaticText(_('Start Update'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'red': self.keyStartUpdate,
         'cancel': self.close}, -2)
        self['info'] = Label()
        self['info'].setText('AirPlayer Enigma2 Plugin\nyou are on Version: %s\n' % config.plugins.airplayer.version.value)
        self.onLayoutFinish.append(self.setCustomTitle)
        self['changelog'] = Label()
        self['changelog'].setText('searching for updates...\n')
        link = self.updater.checkForUpdate('', 0)
        if link != '' and link != 'up to date':
            self['changelog'].setText('Update Available:\n\n' + self.updater.getChangeLog())
        else:
            self['changelog'].setText('no Updates available you are \nup to date\n')
        self.onLayoutFinish.append(self.setCustomTitle)

    def keyStartUpdate(self):
        self.updater.startUpdate()

    def _changed(self):
        self._hasChanged = True

    def setCustomTitle(self):
        self.setTitle(_('AirPlayer Updates'))


class AP_ConfigScreen(Screen, ConfigListScreen):
    skin = '<screen name="AP_ConfigScreen" title="AirPlayer Settings" position="center,center" size="565,370">\n\t\t<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />\n\t\t<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />\n\t\t<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />\n\t\t<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />\n\t\t<widget name="config" position="5,50" size="555,250" scrollbarMode="showOnDemand" />\n\t\t<ePixmap pixmap="skin_default/div-h.png" position="0,301" zPosition="1" size="565,2" />\n\t</screen>'

    def __init__(self, session, args = None):
        self.skin = AP_ConfigScreen.skin
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [getConfigListEntry(_('Autostart'), config.plugins.airplayer.startuptype, _('Should the airplayer start automatically on startup?')),
         getConfigListEntry(_('Interface'), config.plugins.airplayer.interface, _('Which interface should be used for the airport service?')),
         getConfigListEntry(_('Service name'), config.plugins.airplayer.name, _('Which name should be used to identify the device with active airport service?')),
         #getConfigListEntry(_('Skin'), config.plugins.airplayer.skin, _('Skin')),
         #getConfigListEntry(_('Path'), config.plugins.airplayer.path, _('Path for the temp files.')),
         #getConfigListEntry(_('Play Audio-Stream via'), config.plugins.airplayer.audioBackend, _('Play Audio-Stream via')),
         getConfigListEntry(_('Set start position'), config.plugins.airplayer.setSeekOnStart, _('Set Start Position of stream')),
         getConfigListEntry(_('Stop TV while displaying pictures'), config.plugins.airplayer.stopTVOnPicture, _('Stop TV while displaying Pictures')),
         #getConfigListEntry(_('Premium-Key'), config.plugins.airplayer.premiuimKey, _('Premium Key')),
         getConfigListEntry(_('Allow volume-control from iOS device'), config.plugins.airplayer.allowiOSVolumeControl, _('Allow Volume-Control from iOS Device')),
         #getConfigListEntry(_('Show startup info'), config.plugins.airplayer.showStartUpInfo, _('Show StartUp Info')),
         #getConfigListEntry(_('Use built-In Proxy'), config.plugins.airplayer.useProxyIfPossible, _('Use Built-in Proxy')),
         #getConfigListEntry(_('Start playback on MB cached'), config.plugins.airplayer.cacheMbBeforePlayback, _('Start Playback on percent cached')),
         #getConfigListEntry(_('Start live-Stream on MB cached'), config.plugins.airplayer.cacheMbBeforeLivePlayback, _('Start Live-Stream on seconds cached')),
         getConfigListEntry(_('Allow wakeup from standby'), config.plugins.airplayer.allowWakeupFromStandby, _('Allow wakeup from Standby')),
         getConfigListEntry(_('Enable screensaver'), config.plugins.airplayer.screensaverEnabled, _('Enable screensaver')),
         #getConfigListEntry(_('Check for updates on startup'), config.plugins.airplayer.autoUpdate, _('Check for updates on startup')),
         #getConfigListEntry(_('Async start of Audioplayer (Workaround)'), config.plugins.airplayer.delayAudioPlayback, _('Async start of Audioplayer (Workaround)'))
         ], session=session, on_change=self._changed)
        self._session = session
        self._hasChanged = False
        self['key_red'] = StaticText(_('Cancel'))
        self['key_green'] = StaticText(_('Save'))
        self['setupActions'] = ActionMap(['SetupActions', 'ColorActions'], {'green': self.keySave,
         'cancel': self.keyCancel}, -2)
        self.onLayoutFinish.append(self.setCustomTitle)

    def _changed(self):
        self._hasChanged = True

    def keySave(self):
        print '[AirPlayer] pressed save'
        self.saveAll()
        if self._hasChanged:
            self.session.openWithCallback(self.restartGUI, MessageBox, _('Some settings may need a GUI restart\nDo you want to Restart the GUI now?'), MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.quitPlugin, MessageBox, _('Nothing was changed. Do you want to quit?'), MessageBox.TYPE_YESNO)

    def quitPlugin(self, answer):
        if answer is True:
            self.close()

    def restartGUI(self, answer):
        if answer is True:
            from Screens.Standby import TryQuitMainloop
            stopWebserver(global_session)
            self.session.open(TryQuitMainloop, 3)
        else:
            self.close()

    def setCustomTitle(self):
        self.setTitle(_('Settings for Airplayer'))


def stopWebserver(session):
    os.system('killall zeroconfig &')
    print '[AirPlayer] service stopped'


def startWebserver(session):
    global global_airtunes_protocol_handler
    global global_protocol_handler
    global global_media_backend
    config.plugins.airplayer.version.value = currentVersion
    config.plugins.airplayer.arch.value = currentArch
    print '[AirPlayer] starting AirPlayer version', config.plugins.airplayer.version.value, ' on ', config.plugins.airplayer.arch.value
    print '[AirPlayer] starting webserver'
    print '[AirPlayer] init Backend'
    media_backend = E2MediaBackend(session)
    print '[AirPlayer] init protocol handler'
    protocol_handler = AirplayProtocolHandler(6002, media_backend)
    aitrunes_ph = AirtunesProtocolHandler(media_backend)
    global_protocol_handler = protocol_handler
    global_media_backend = media_backend
    global_airtunes_protocol_handler = aitrunes_ph
    #if config.plugins.airplayer.autoUpdate.value:
        #print '[AirPlayer] check for updates'
        #link = media_backend.updater.checkForUpdate('', 0)
        #print '[AirPlayer] update: ', link
        #if link != '' and link != 'up to date':
            #Notifications.AddNotificationWithCallback(media_backend.updater.startUpdateCallback, MessageBox, _('A new Version of AirPlayer is available! Update AirPlayer now?'), MessageBox.TYPE_YESNO, timeout=10)
    print '[AirPlayer] starting protocol hadler'
    protocol_handler.start()
    aitrunes_ph.start()
    print '[AirPlayer] starting webserver done'
    print '[AirPlayer] starting zeroconf'
    os.system('killall zeroconfig')
    os.system('/usr/lib/enigma2/python/Plugins/Extensions/IniAirPlayer/zeroconfig "' + config.plugins.airplayer.name.value + '" ' + config.plugins.airplayer.interface.value + ' &')
    print '[AirPlayer] starting zeroconf done'
    #if config.plugins.airplayer.showStartUpInfo.value:
        #Notifications.AddNotification(MessageBox, _('AirPlayer %s started!\nIf you have any problems with this plugin, please visit the Support-Board at www.airplayer.biz') % config.plugins.airplayer.version.value, type=MessageBox.TYPE_INFO, timeout=20)


def sessionstart(reason, session):
    global global_session
    global_session = session


def networkstart(reason, **kwargs):
    interfaces = []
    for i in iNetwork.getAdapterList():
        interfaces.append((i, i))
        print '[AirPlayer] found network dev', i

    config.plugins.airplayer.interface = ConfigSelection(choices=interfaces, default='eth0')
    if reason == 1 and config.plugins.airplayer.startuptype.value:
        startWebserver(global_session)
    elif reason == 0:
        stopWebserver(global_session)


def main(session, **kwargs):
    #session.open(AP_MainMenu)
    session.open(AP_ConfigScreen)

def Plugins(**kwargs):
    return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=sessionstart), PluginDescriptor(where=[PluginDescriptor.WHERE_NETWORKCONFIG_READ], fnc=networkstart), 
  PluginDescriptor(name='AirPlayer', description='AirPlayer', where=PluginDescriptor.WHERE_PLUGINMENU, icon='plugin.png', fnc=main)]