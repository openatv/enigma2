from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigDirectory, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from enigma import eListboxPythonMultiContent, eConsoleAppContainer, ePoint, eServiceReference, eTimer, getDesktop, gFont, loadPic, loadPNG, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_WRAP
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3
from Plugins.Plugin import PluginDescriptor
from re import findall, search, split, sub
from Screens.ChannelSelection import ChannelSelection
from Screens.InfoBar import MoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from string import find
from Tools.Directories import fileExists
from twisted.web import client, error
from twisted.web.client import getPage
from urllib2 import Request, urlopen, URLError, HTTPError
import datetime, os, re, statvfs, socket, sys, time, urllib
from os import system, walk
config.plugins.mp3browser = ConfigSubsection()
config.plugins.mp3browser.mp3folder = ConfigDirectory(default='/media/usb/')
config.plugins.mp3browser.cachefolder = ConfigSelection(default='/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/cache', choices=[('/media/usb/mp3browser/cache', _('/media/usb')), ('/media/hdd/mp3browser/cache', _('/media/hdd')), ('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/cache', _('Default'))])
deskWidth = getDesktop(0).size().width()
if deskWidth == 1280:
    config.plugins.mp3browser.plugin_size = ConfigSelection(default='full', choices=[('full', _('Plugin Full')), ('normal', _('Plugin Normal'))])
else:
    config.plugins.mp3browser.plugin_size = ConfigSelection(default='normal', choices=[('full', _('Plugin Full')), ('normal', _('Plugin Normal'))])
config.plugins.mp3browser.searchby = ConfigSelection(default='track', choices=[('track', _('Track Name')), ('album', _('Album Name'))])
config.plugins.mp3browser.sortorder = ConfigSelection(default='artist', choices=[('artist', _('MP3 Artist A-Z')),
 ('artist_reverse', _('MP3 Artist Z-A')),
 ('album', _('MP3 Album Title A-Z')),
 ('album_reverse', _('MP3 Album Title Z-A')),
 ('track', _('MP3 Track Title A-Z')),
 ('track_reverse', _('MP3 Track Title Z-A')),
 ('genre', _('MP3 Genre A-Z')),
 ('genre_reverse', _('MP3 Genre Z-A')),
 ('year', _('MP3 Release Date Ascending')),
 ('year_reverse', _('MP3 Release Date Descending')),
 ('date', _('File Creation Date Ascending')),
 ('date_reverse', _('File Creation Date Descending')),
 ('folder', _('MP3 Folder Ascending')),
 ('folder_reverse', _('MP3 Folder Descending'))])
config.plugins.mp3browser.background = ConfigSelection(default='yes', choices=[('no', _('No')), ('yes', _('Yes'))])
config.plugins.mp3browser.language = ConfigSelection(default='en', choices=[('de', _('Deutsch')), ('en', _('English')), ('es', _('Espanol'))])
config.plugins.mp3browser.reset = ConfigSelection(default='no', choices=[('no', _('No')), ('yes', _('Yes'))])
config.plugins.mp3browser.color = ConfigSelection(default='#00C3461B', choices=[('#00F0A30A', _('Amber')),
 ('#00825A2C', _('Brown')),
 ('#007895BC', _('Camouflage')),
 ('#000050EF', _('Cobalt')),
 ('#00911D10', _('Crimson')),
 ('#001BA1E2', _('Cyan')),
 ('#00008A00', _('Emerald')),
 ('#0070AD11', _('Green')),
 ('#006A00FF', _('Indigo')),
 ('#00A4C400', _('Lime')),
 ('#00A61D4D', _('Magenta')),
 ('#0076608A', _('Mauve')),
 ('#006D8764', _('Olive')),
 ('#00C3461B', _('Orange')),
 ('#00F472D0', _('Pink')),
 ('#00E51400', _('Red')),
 ('#007A3B3F', _('Sienna')),
 ('#00647687', _('Steel')),
 ('#00149BAF', _('Teal')),
 ('#006C0AAB', _('Violet')),
 ('#00BF9217', _('Yellow'))])

def applySkinVars(skin, dict):
    for key in dict.keys():
        try:
            skin = skin.replace('{' + key + '}', dict[key])
        except Exception as e:
            print e, '@key=', key

    return skin


def transHTML(text):
    text = text.replace('&nbsp;', ' ').replace('&szlig;', 'ss').replace('&quot;', '"').replace('&ndash;', '-').replace('&Oslash;', '').replace('&bdquo;', '"').replace('&ldquo;', '"').replace('&rsquo;', "'").replace('&gt;', '>').replace('&lt;', '<')
    text = text.replace('&copy;.*', ' ').replace('&amp;', '&').replace('&uuml;', '\xc3\x83\xc2\xbc').replace('&auml;', '\xc3\x83\xc2\xa4').replace('&ouml;', '\xc3\x83\xc2\xb6').replace('&eacute;', '\xc3\xa9').replace('&hellip;', '...').replace('&egrave;', '\xc3\xa8').replace('&agrave;', '\xc3\xa0')
    text = text.replace('&Uuml;', 'Ue').replace('&Auml;', 'Ae').replace('&Ouml;', 'Oe').replace('&#034;', '"').replace('&#34;', '"').replace('&#38;', 'und').replace('&#039;', "'").replace('&#39;', "'").replace('&#133;', '...').replace('&#196;', '\xc3\x83\xe2\x80\x9e').replace('&#214;', '\xc3\x83-').replace('&#220;', '\xc3\x83\xc5\x93').replace('&#223;', '\xc3\x83\xc5\xb8').replace('&#228;', '\xc3\x83\xc2\xa4').replace('&#246;', '\xc3\x83\xc2\xb6').replace('&#252;', '\xc3\x83\xc2\xbc')
    return text


class mp3Browser(Screen):

    def __init__(self, session):
        if config.plugins.mp3browser.plugin_size.value == 'full':
            self.xd = False
            self.spaceTop = 4
            self.spaceLeft = 0
            self.spaceX = 2
            self.spaceY = 2
            self.picX = 140
            self.picY = 140
            self.posterX = 9
            self.posterY = 5
            self.posterALL = 45
            self.posterREST = 0
        else:
            self.xd = True
            self.spaceTop = 1
            self.spaceLeft = -3
            self.spaceX = 4
            self.spaceY = 4
            self.picX = 110
            self.picY = 110
            self.posterX = 9
            self.posterY = 5
            self.posterALL = 45
            self.posterREST = 0
        self.positionlist = []
        skincontent = ''
        numX = -1
        for x in range(self.posterALL):
            numY = x // self.posterX
            numX += 1
            if numX >= self.posterX:
                numX = 0
            posX = self.spaceLeft + self.spaceX + numX * (self.spaceX + self.picX)
            posY = self.spaceTop + self.spaceY + numY * (self.spaceY + self.picY)
            self.positionlist.append((posX - 10, posY - 10))
            skincontent += '<widget name="poster' + str(x) + '" position="' + str(posX) + ',' + str(posY) + '" size="' + str(self.picX) + ',' + str(self.picY) + '" zPosition="10" transparent="1" alphatest="on" />'
            skincontent += '<widget name="poster_back' + str(x) + '" position="' + str(posX) + ',' + str(posY) + '" size="' + str(self.picX) + ',' + str(self.picY) + '" zPosition="11" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/poster_backHD.png" />'

        skin = '\n\t\t\t\t\t<screen position="center,center" size="1024,576" flags="wfNoBorder" title="  " >\n\n\t\t\t\t\t\t<widget name="infoback" position="15,15" size="460,400" alphatest="blend" transparent="1" zPosition="12" />\n\t\t\t\t\t\t<widget name="name" position="25,16" size="440,55" font="Regular;24" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="13" />\n\t\t\t\t\t\t<widget name="Artist" position="25,70" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t\t\t<widget name="artist" position="25,100" size="285,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="15" />\n\t\t\t\t\t\t<widget name="Album" position="25,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="16" />\n\t\t\t\t\t\t<widget name="album" position="25,170" size="285,50" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t\t\t<widget name="Year" position="320,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t\t\t<widget name="year" position="320,170" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t\t\t<widget name="Track" position="25,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="20" />\n\t\t\t\t\t\t<widget name="track" position="25,240" size="285,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="21" />\n\t\t\t\t\t\t<widget name="Number" position="320,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="22" />\n\t\t\t\t\t\t<widget name="number" position="320,240" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="23" />\n\t\t\t\t\t\t<widget name="Runtime" position="25,280" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="24" />\n\t\t\t\t\t\t<widget name="runtime" position="25,310" size="285,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="25" />\n\t\t\t\t\t\t<widget name="Bitrate" position="320,280" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="26" />\n\t\t\t\t\t\t<widget name="bitrate" position="320,310" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="27" />\n\t\t\t\t\t\t<widget name="Genre" position="25,350" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="28" />\n\t\t\t\t\t\t<widget name="genre" position="25,380" size="440,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="29" />\n\n\t\t\t\t\t\t<widget name="frame" position="-9,-5" size="130,130" zPosition="12" alphatest="on" />"\n\t\t\t\t\t\t' + skincontent + '\n\t\t\t\t\t</screen>'
        skinHD = '\n\t\t\t\t\t<screen position="center,center" size="1280,720" flags="wfNoBorder" title="  " >\n\n\t\t\t\t\t\t<widget name="infoback" position="25,25" size="525,430" alphatest="blend" transparent="1" zPosition="12" />\n\t\t\t\t\t\t<widget name="name" position="40,30" size="495,70" font="Regular;28" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="13" />\n\t\t\t\t\t\t<widget name="Artist" position="40,100" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t\t\t<widget name="artist" position="40,130" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="15" />\n\t\t\t\t\t\t<widget name="Album" position="40,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="16" />\n\t\t\t\t\t\t<widget name="album" position="40,200" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t\t\t<widget name="Year" position="370,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t\t\t<widget name="year" position="370,200" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t\t\t<widget name="Track" position="40,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="20" />\n\t\t\t\t\t\t<widget name="track" position="40,270" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="21" />\n\t\t\t\t\t\t<widget name="Number" position="370,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="22" />\n\t\t\t\t\t\t<widget name="number" position="370,270" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="23" />\n\t\t\t\t\t\t<widget name="Runtime" position="40,310" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="24" />\n\t\t\t\t\t\t<widget name="runtime" position="40,340" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="25" />\n\t\t\t\t\t\t<widget name="Bitrate" position="370,310" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="26" />\n\t\t\t\t\t\t<widget name="bitrate" position="370,340" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="27" />\n\t\t\t\t\t\t<widget name="Genre" position="40,380" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="28" />\n\t\t\t\t\t\t<widget name="genre" position="40,410" size="500,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="29" />\n\n\t\t\t\t\t\t<widget name="frame" position="-8,-4" size="160,160" zPosition="12" alphatest="on" />"\n\t\t\t\t\t\t' + skincontent + '\n\t\t\t\t\t</screen>'
        if self.xd == False:
            color = config.plugins.mp3browser.color.value
            self.dict = {'color': color}
            self.skin = applySkinVars(skinHD, self.dict)
        else:
            color = config.plugins.mp3browser.color.value
            self.dict = {'color': color}
            self.skin = applySkinVars(skin, self.dict)
        Screen.__init__(self, session)
        self.hideflag = True
        self.fav = False
        self.ready = False
        self.infofull = False
        self.update = False
        self.index = 0
        self.wallindex = self.index % self.posterALL
        self.pagecount = self.index // self.posterALL + 1
        self.oldindex = 0
        self.pagemax = 1
        self.filter = ':::'
        if config.plugins.mp3browser.background.value == 'yes':
            self.background = True
            self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
        else:
            self.background = False
        self.namelist = []
        self.mp3list = []
        self.datelist = []
        self.artistlist = []
        self.albumlist = []
        self.numberlist = []
        self.tracklist = []
        self.yearlist = []
        self.runtimelist = []
        self.bitratelist = []
        self.genrelist = []
        self.posterlist = []
        self['frame'] = Pixmap()
        for x in range(self.posterALL):
            self['poster' + str(x)] = Pixmap()
            self['poster_back' + str(x)] = Pixmap()

        self['name'] = Label()
        self['Artist'] = Label()
        self['artist'] = Label()
        self['Album'] = Label()
        self['album'] = Label()
        self['Number'] = Label()
        self['number'] = Label()
        self['Track'] = Label()
        self['track'] = Label()
        self['Year'] = Label()
        self['year'] = Label()
        self['Runtime'] = Label()
        self['runtime'] = Label()
        self['Bitrate'] = Label()
        self['bitrate'] = Label()
        self['Genre'] = Label()
        self['genre'] = Label()
        self['infoback'] = Pixmap()
        self['infoback'].hide()
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'InfobarMovieListActions',
         'InfobarTeletextActions',
         'MovieSelectionActions',
         'MoviePlayerActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'right': self.rightDown,
         'left': self.leftUp,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.PageUp,
         'prevBouquet': self.PageDown,
         'red': self.addFav,
         'yellow': self.infoScreen,
         'green': self.renewCoverByAlbum,
         'yellow': self.renewCoverByTrack,
         'blue': self.hideScreen,
         'contextMenu': self.config,
         'showEventInfo': self.toggleInfoFull,
         'startTeletext': self.editDatabase,
         'movieList': self.updateDatabase,
         'leavePlayer': self.stop,
         '1': self.showMP3,
         '2': self.showFav,
         '3': self.showPath,
         '4': self.infoScreen,
         '5': self.playList,
         '6': self.wikipedia,
         '7': self.filterArtist,
         '8': self.filterAlbum,
         '9': self.filterGenre,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
	cmd = "mkdir /usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/;mkdir /usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/cache"
	os.system(cmd) 
        self.updatefile = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/update'
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/database'
        self.favorites = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/favorites'
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        if self.xd == False:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/info_backHD.png'
        else:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/info_back.png'
        if fileExists(self.database):
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.reset = False
            self.makeMP3BrowserTimer = eTimer()
            self.makeMP3BrowserTimer.callback.append(self.makeMP3(self.filter))
            self.makeMP3BrowserTimer.start(500, True)
        else:
            self.openTimer = eTimer()
            self.openTimer.callback.append(self.openInfo)
            self.openTimer.start(500, True)

    def openInfo(self):
        if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/reset'):
            self.session.openWithCallback(self.reset_return, MessageBox, _('\nThe MP3 Browser Database will be built now. This can take several minutes, depending on how many mp3s you have.\n\nBuild MP3 Browser Database now?'), MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.first_return, MessageBox, _('\nBefore the MP3 Browser Database is built for the first time, you should check your MP3 Folder settings and change the Cache Folder to a hard drive disk for faster access or to a USB stick.'), MessageBox.TYPE_YESNO)

    def first_return(self, answer):
        if answer is True:
            open('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/reset', 'w').close()
            self.session.openWithCallback(self.exit, mp3BrowserConfig)
        else:
            self.close()

    def reset_return(self, answer):
        if answer is True:
            self.reset = True
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/reset'):
                os.remove('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/reset')
            self.resetTimer = eTimer()
            self.resetTimer.callback.append(self.database_return(True))
            self.resetTimer.start(500, True)
        else:
            self.close()

    def makeMP3(self, filter):
        self.namelist = []
        self.mp3list = []
        self.datelist = []
        self.artistlist = []
        self.albumlist = []
        self.numberlist = []
        self.tracklist = []
        self.yearlist = []
        self.runtimelist = []
        self.bitratelist = []
        self.genrelist = []
        self.posterlist = []
        self.filter = filter
        if fileExists(self.database):
            f = open(self.database, 'r')
            for line in f:
                if filter in line:
                    mp3line = line.split(':::')
                    try:
                        name = mp3line[0]
                    except IndexError:
                        name = ' '

                    try:
                        filename = mp3line[1]
                    except IndexError:
                        filename = ' '

                    try:
                        date = mp3line[2]
                    except IndexError:
                        date = ' '

                    try:
                        artist = mp3line[3]
                    except IndexError:
                        artist = ' '

                    try:
                        album = mp3line[4]
                    except IndexError:
                        album = ' '

                    try:
                        number = mp3line[5]
                    except IndexError:
                        number = ' '

                    try:
                        track = mp3line[6]
                    except IndexError:
                        track = ' '

                    try:
                        year = mp3line[7]
                    except IndexError:
                        year = ' '

                    try:
                        genre = mp3line[8]
                    except IndexError:
                        genre = ' '

                    try:
                        runtime = mp3line[9]
                    except IndexError:
                        runtime = ' '

                    try:
                        bitrate = mp3line[10]
                    except IndexError:
                        bitrate = ' '

                    try:
                        poster = mp3line[11]
                    except IndexError:
                        poster = 'http://www.kashmir-plugins.de/default.png'

                    self.namelist.append(name)
                    self.mp3list.append(filename)
                    self.datelist.append(date)
                    self.artistlist.append(artist)
                    self.albumlist.append(album)
                    self.numberlist.append(number)
                    self.tracklist.append(track)
                    self.yearlist.append(year)
                    self.genrelist.append(genre)
                    self.runtimelist.append(runtime)
                    self.bitratelist.append(bitrate)
                    self.posterlist.append(poster)

            f.close()
            self.maxentry = len(self.namelist)
            if self.maxentry == 0:
                size = os.path.getsize(self.database)
                self.ready = True
                if size < 10:
                    os.remove(self.database)
            else:
                self.posterREST = self.maxentry % self.posterALL
                if self.posterREST == 0:
                    self.posterREST = self.posterALL
                self.pagemax = self.maxentry // self.posterALL
                if self.maxentry % self.posterALL > 0:
                    self.pagemax += 1
                self.makePoster(self.pagecount - 1)
                self.paintFrame()
                if self.infofull == True:
                    try:
                        self.showInfoFull(self.index)
                    except IndexError:
                        pass

                self.ready = True

    def updateDatabase(self):
        if self.ready == True:
            if os.path.exists(config.plugins.mp3browser.mp3folder.value):
                self.session.openWithCallback(self.database_return, MessageBox, _('\nUpdate MP3 Browser Database?'), MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, _('\nMP3 Folder %s not reachable.\nMP3 Browser Database Update canceled.') % str(config.plugins.mp3browser.mp3folder.value), MessageBox.TYPE_ERROR)

    def database_return(self, answer):
        if answer is True:
            open(self.updatefile, 'w').close()
            self.update = True
            self.ready = False
            self.namelist = []
            self.mp3list = []
            self.datelist = []
            self.artistlist = []
            self.albumlist = []
            self.numberlist = []
            self.tracklist = []
            self.yearlist = []
            self.runtimelist = []
            self.bitratelist = []
            self.genrelist = []
            self.posterlist = []
            self.orphaned = 0
            if self.fav == True:
                self.fav = False
                self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/database'
            if fileExists(self.database):
                allfiles = ':::'
                folder = config.plugins.mp3browser.mp3folder.value
                for root, dirs, files in os.walk(folder, topdown=False):
                    for name in files:
                        if name.lower().endswith('.mp3'):
                            filename = os.path.join(root, name)
                            filedate = os.path.getctime(filename)
                            allfiles = allfiles + str(filedate)

                data = open(self.database).read()
                for line in data.split('\n'):
                    mp3line = line.split(':::')
                    try:
                        mp3folder = mp3line[1]
                        mp3date = mp3line[2]
                    except IndexError:
                        mp3folder = ''
                        mp3date = ''

                    if search(config.plugins.mp3browser.mp3folder.value, mp3folder) is not None and search(mp3date, allfiles) is None:
                        self.orphaned += 1
                        data = data.replace(line + '\n', '')

                os.rename(self.database, self.database + '-backup')
                f = open(self.database, 'w')
                f.write(data)
                f.close()
                del allfiles
                data = open(self.database).read()
            else:
                open(self.database, 'w').close()
                data = ''
            folder = config.plugins.mp3browser.mp3folder.value
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    mp3 = sub('\\(', '.', name)
                    mp3 = sub('\\)', '.', mp3)
                    if search(mp3, data) is None:
                        if name.lower().endswith('.mp3'):
                            filename = os.path.join(root, name)
                            self.mp3list.append(filename)
                            self.datelist.append(os.path.getctime(filename))
                            name = sub('[.]mp3', '', name)
                            self.namelist.append(name)
                            audio = None
                            album = ''
                            artist = ''
                            number = ''
                            track = ''
                            genre = ''
                            year = ''
                            runtime = ''
                            bitrate = ''
                            audio = MP3(filename, ID3=EasyID3)
                            if audio is not None:
                                album = audio.get('album', ['n/a'])[0]
                                artist = audio.get('artist', ['n/a'])[0]
                                number = audio.get('tracknumber', ['n/a'])[0].split('/')[0]
                                track = audio.get('title', [name])[0]
                                genre = audio.get('genre', ['n/a'])[0]
                                year = audio.get('date', ['n/a'])[0]
                                runtime = str(datetime.timedelta(seconds=int(audio.info.length)))
                                bitrate = str(audio.info.bitrate // 1000)
                                bitrate = bitrate + ' kbit/s'
                            self.albumlist.append(album)
                            self.artistlist.append(artist)
                            self.numberlist.append(number)
                            self.tracklist.append(track)
                            self.genrelist.append(genre)
                            self.yearlist.append(year)
                            self.runtimelist.append(runtime)
                            self.bitratelist.append(bitrate)

            self.dbcount = 1
            self.dbcountmax = len(self.mp3list)
            if self.dbcountmax == 0:
                self.finished_update(False)
            else:
                if config.plugins.mp3browser.searchby.value == 'track':
                    mp3 = self.artistlist[self.dbcount - 1] + '+' + self.tracklist[self.dbcount - 1]
                else:
                    mp3 = self.artistlist[self.dbcount - 1] + '+' + self.albumlist[self.dbcount - 1]
                mp3 = mp3.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+').replace('&', 'and')
                url = 'http://images.google.de/images?q=%s&btnG=Bilder-Suche' % mp3
                self.getMP3Poster(url)

    def getMP3Poster(self, url):
        headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        poster = re.findall('imgurl=(.*?)&amp;', output)
        try:
            self.posterlist.append(poster[0])
        except IndexError:
            self.posterlist.append('http://www.kashmir-plugins.de/default.png')

        self.makeDataEntry(self.dbcount - 1)

    def makeDataEntry(self, count):
        f = open(self.database, 'a')
        try:
            data = self.namelist[count] + ':::' + self.mp3list[count] + ':::' + str(self.datelist[count]) + ':::' + self.artistlist[count] + ':::' + self.albumlist[count] + ':::' + self.numberlist[count] + ':::' + self.tracklist[count] + ':::' + self.yearlist[count] + ':::' + self.genrelist[count] + ':::' + self.runtimelist[count] + ':::' + self.bitratelist[count] + ':::' + self.posterlist[count] + ':::\n'
            f.write(data)
        except IndexError:
            pass

        f.close()
        if self.dbcount < self.dbcountmax:
            self.dbcount += 1
            if config.plugins.mp3browser.searchby.value == 'track':
                mp3 = self.artistlist[self.dbcount - 1] + '+' + self.tracklist[self.dbcount - 1]
            else:
                mp3 = self.artistlist[self.dbcount - 1] + '+' + self.albumlist[self.dbcount - 1]
            mp3 = mp3.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+').replace('&', 'and')
            url = 'http://images.google.de/images?q=%s&btnG=Bilder-Suche' % mp3
            self.getMP3Poster(url)
        elif self.update == True:
            if self.reset == True:
                self.session.openWithCallback(self.exit, mp3Browser)
            else:
                self.finished_update(True)
        else:
            self.finished()

    def finished(self):
        self.index = 0
        self.oldindex = 0
        self.wallindex = 0
        self.pagecount = 1
        self.makeMP3(self.filter)

    def finished_update(self, found):
        if found == False and self.orphaned == 0:
            self.session.open(MessageBox, _('\nNo new MP3 found:\nYour Database is up to date.'), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMP3(self.filter)
        elif found == False:
            if self.orphaned == 1:
                self.session.open(MessageBox, _('\nNo new MP3 found.\n%s Orphaned MP3 deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\nNo new MP3 found.\n%s Orphaned MP3 deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMP3(self.filter)
        elif self.orphaned == 0:
            if self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMP3(self.filter)
        else:
            if self.dbcountmax == 1 and self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.\n%s Orphaned MP3 deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.\n%s Orphaned MP3 deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.\n%s Orphaned MP3 deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s MP3 imported into Database.\n%s Orphaned MP3 deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMP3(self.filter)

    def ok(self):
        if self.ready == True:
            try:
                filename = self.mp3list[self.index]
                sref = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + filename)
                sref.setName(self.artistlist[self.index] + ' - ' + self.tracklist[self.index])
                if self.background == True:
                    self.session.nav.stopService()
                    self.session.nav.playService(sref)
                else:
                    self.session.open(MoviePlayer, sref)
            except IndexError:
                pass

    def playList(self):
        if self.ready == True:
            try:
                filename = self.mp3list[self.index]
                sref = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + filename)
                if self.background == True:
                    self.session.open(MessageBox, '\nPlaylist not possible in Background Mode.', MessageBox.TYPE_INFO, timeout=5)
                else:
                    self.playready = True
                    self.session.openWithCallback(self.nextMP3, MoviePlayer, sref)
            except IndexError:
                pass

    def nextMP3(self):
        if self.playready == True:
            self.rightDown()
            self.ok()

    def renewCoverByTrack(self):
        if self.ready == True:
            mp3 = self.artistlist[self.index] + ' - ' + self.tracklist[self.index]
            self.session.openWithCallback(self.renewByTrackReturn, VirtualKeyBoard, title='Update Cover by Track Name:', text=mp3)

    def renewByTrackReturn(self, mp3):
        if mp3 and mp3 != '':
            mp3 = mp3.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+').replace('&', 'and')
            url = 'http://images.google.de/images?q=%s&btnG=Bilder-Suche' % mp3
            self.newMP3Poster(url, mp3)

    def renewCoverByAlbum(self):
        if self.ready == True:
            mp3 = self.artistlist[self.index] + ' - ' + self.albumlist[self.index]
            self.session.openWithCallback(self.renewByAlbumReturn, VirtualKeyBoard, title='Update Cover by Album Name:', text=mp3)

    def renewByAlbumReturn(self, mp3):
        if mp3 and mp3 != '':
            mp3 = mp3.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+').replace('&', 'and')
            url = 'http://images.google.de/images?q=%s&btnG=Bilder-Suche' % mp3
            self.newMP3Poster(url, mp3)

    def newMP3Poster(self, url, titel):
        headers = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        poster = re.findall('imgurl=(.*?)&amp;', output)
        try:
            self.session.openWithCallback(self.makeMP3Poster, mp3List, poster, titel)
        except IndexError:
            pass

    def makeMP3Poster(self, poster):
        if poster != 'none':
            newdata = self.namelist[self.index] + ':::' + self.mp3list[self.index] + ':::' + str(self.datelist[self.index]) + ':::' + self.artistlist[self.index] + ':::' + self.albumlist[self.index] + ':::' + self.numberlist[self.index] + ':::' + self.tracklist[self.index] + ':::' + self.yearlist[self.index] + ':::' + self.genrelist[self.index] + ':::' + self.runtimelist[self.index] + ':::' + self.bitratelist[self.index] + ':::' + poster + ':::'
            data = open(self.database).read()
            mp3 = self.mp3list[self.index]
            mp3 = sub('\\(', '.', mp3)
            mp3 = sub('\\)', '.', mp3)
            if search(mp3, data) is not None:
                for line in data.split('\n'):
                    if search(mp3, line) is not None:
                        data = data.replace(line, newdata)

                f = open(self.database, 'w')
                f.write(data)
                f.close()
                self.makeMP3(self.filter)

    def addFav(self):
        if self.ready == True:
            try:
                artist = self.artistlist[self.index]
                track = self.tracklist[self.index]
                self.session.openWithCallback(self.fav_return, MessageBox, _("\nAdd MP3 '%s' to Favorites?") % (artist + ' - ' + track), MessageBox.TYPE_YESNO)
            except IndexError:
                pass

    def fav_return(self, answer):
        if answer is True:
            f = open(self.favorites, 'a')
            data = self.namelist[self.index] + ':::' + self.mp3list[self.index] + ':::' + str(self.datelist[self.index]) + ':::' + self.artistlist[self.index] + ':::' + self.albumlist[self.index] + ':::' + self.numberlist[self.index] + ':::' + self.tracklist[self.index] + ':::' + self.yearlist[self.index] + ':::' + self.genrelist[self.index] + ':::' + self.runtimelist[self.index] + ':::' + self.bitratelist[self.index] + ':::' + self.posterlist[self.index] + ':::'
            f.write(data)
            f.write(os.linesep)
            f.close()
            self.session.open(mp3Fav)

    def showFav(self):
        if self.fav == False:
            self.fav = True
            self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/favorites'
            self.makeMP3(self.filter)
        else:
            self.fav = False
            self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/database'
            self.makeMP3(self.filter)

    def makePoster(self, page):
        for x in range(self.posterALL):
            try:
                index = x + page * self.posterALL
                posterurl = self.posterlist[index]
                poster = sub('.*?[/]', '', posterurl)
                poster = config.plugins.mp3browser.cachefolder.value + '/' + poster
                if fileExists(poster):
                    if self.xd == False:
                        Poster = loadPic(poster, 140, 140, 3, 0, 0, 1)
                    else:
                        Poster = loadPic(poster, 110, 110, 3, 0, 0, 1)
                    if Poster != None:
                        self['poster' + str(x)].instance.setPixmap(Poster)
                        self['poster' + str(x)].show()
                else:
                    getPage(posterurl).addCallback(self.getPoster, x, poster).addErrback(self.downloadError)
            except IndexError:
                self['poster' + str(x)].hide()

        self['poster_back' + str(self.wallindex)].hide()

    def getPoster(self, output, x, poster):
        f = open(poster, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            Poster = loadPic(poster, 140, 140, 3, 0, 0, 1)
        else:
            Poster = loadPic(poster, 110, 110, 3, 0, 0, 1)
        if Poster != None:
            self['poster' + str(x)].instance.setPixmap(Poster)
            self['poster' + str(x)].show()

    def paintFrame(self):
        try:
            pos = self.positionlist[self.wallindex]
            self['frame'].instance.move(ePoint(pos[0], pos[1]))
            self['poster_back' + str(self.oldindex)].show()
            self['poster_back' + str(self.wallindex)].hide()
            posterurl = self.posterlist[self.index]
            poster = sub('.*?[/]', '', posterurl)
            poster = config.plugins.mp3browser.cachefolder.value + '/' + poster
            if fileExists(poster):
                if self.xd == False:
                    Poster = loadPic(poster, 160, 160, 3, 0, 0, 1)
                else:
                    Poster = loadPic(poster, 130, 130, 3, 0, 0, 1)
                if Poster != None:
                    self['frame'].instance.setPixmap(Poster)
        except IndexError:
            pass

    def toggleInfoFull(self):
        if self.ready == True:
            if self.infofull == False:
                self.infofull = True
                try:
                    self.showInfoFull(self.index)
                except IndexError:
                    pass

            else:
                self.infofull = False
                self.hideInfoFull()

    def showInfoFull(self, count):
        if self.xd == False:
            InfoFull = loadPic(self.infoBackPNG, 525, 430, 3, 0, 0, 1)
        else:
            InfoFull = loadPic(self.infoBackPNG, 460, 400, 3, 0, 0, 1)
        if InfoFull != None:
            self['infoback'].instance.setPixmap(InfoFull)
            self['infoback'].show()
        try:
            name = self.artistlist[count] + ' - ' + self.tracklist[count]
            if self.xd == True:
                if len(name) > 66:
                    if name[65:66] == ' ':
                        name = name[0:65]
                    else:
                        name = name[0:66] + 'FIN'
                        name = sub(' \\S+FIN', '', name)
                    name = name + '...'
            elif len(name) > 63:
                if name[62:63] == ' ':
                    name = name[0:62]
                else:
                    name = name[0:63] + 'FIN'
                    name = sub(' \\S+FIN', '', name)
                name = name + '...'
            self['name'].setText(name)
            self['name'].show()
        except IndexError:
            self['name'].hide()

        try:
            artist = self.artistlist[count]
            self['artist'].setText(artist)
            self['artist'].show()
            self['Artist'].setText('Artist:')
            self['Artist'].show()
        except IndexError:
            self['artist'].hide()
            self['Artist'].hide()

        try:
            album = self.albumlist[count]
            self['album'].setText(album)
            self['album'].show()
            self['Album'].setText('Album:')
            self['Album'].show()
        except IndexError:
            self['album'].hide()
            self['Album'].hide()

        try:
            number = self.numberlist[count]
            self['number'].setText(number)
            self['number'].show()
            self['Number'].setText('Track-Nr:')
            self['Number'].show()
        except IndexError:
            self['number'].hide()
            self['Number'].hide()

        try:
            track = self.tracklist[count]
            self['track'].setText(track)
            self['track'].show()
            self['Track'].setText('Track:')
            self['Track'].show()
        except IndexError:
            self['track'].hide()
            self['Track'].hide()

        try:
            year = self.yearlist[count]
            self['year'].setText(year)
            self['year'].show()
            self['Year'].setText('Year:')
            self['Year'].show()
        except IndexError:
            self['year'].hide()
            self['Year'].hide()

        try:
            runtime = self.runtimelist[count]
            self['runtime'].setText(runtime)
            self['runtime'].show()
            self['Runtime'].setText('Runtime:')
            self['Runtime'].show()
        except IndexError:
            self['runtime'].hide()
            self['Runtime'].hide()

        try:
            bitrate = self.bitratelist[count]
            self['bitrate'].setText(bitrate)
            self['bitrate'].show()
            self['Bitrate'].setText('Bitrate:')
            self['Bitrate'].show()
        except IndexError:
            self['bitrate'].hide()
            self['Bitrate'].hide()

        try:
            genres = self.genrelist[count]
            self['genre'].setText(genres)
            self['genre'].show()
            self['Genre'].setText('Genre:')
            self['Genre'].show()
        except IndexError:
            self['genre'].hide()
            self['Genre'].hide()

    def hideInfoFull(self):
        self['name'].hide()
        self['artist'].hide()
        self['Artist'].hide()
        self['album'].hide()
        self['Album'].hide()
        self['number'].hide()
        self['Number'].hide()
        self['track'].hide()
        self['Track'].hide()
        self['year'].hide()
        self['Year'].hide()
        self['runtime'].hide()
        self['Runtime'].hide()
        self['bitrate'].hide()
        self['Bitrate'].hide()
        self['genre'].hide()
        self['Genre'].hide()
        self['infoback'].hide()

    def rightDown(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex += 1
            if self.pagecount == self.pagemax and self.wallindex > self.posterREST - 1:
                self.wallindex = 0
                self.pagecount = 1
                self.makePoster(self.pagecount - 1)
            elif self.wallindex == self.posterALL:
                self.wallindex = 0
                self.pagecount += 1
                self.makePoster(self.pagecount - 1)
            self.index += 1
            if self.index == self.maxentry:
                self.index = 0
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def down(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex += self.posterX
            if self.pagecount == self.pagemax - 1 and self.wallindex > self.posterALL + self.posterREST - 2:
                self.wallindex = self.posterREST - 1
                self.pagecount += 1
                self.makePoster(self.pagecount - 1)
                self.index = self.maxentry - 1
            elif self.pagecount == self.pagemax and self.wallindex > self.posterREST - 1:
                if self.wallindex >= self.posterX:
                    self.wallindex = self.wallindex % self.posterX
                self.pagecount = 1
                self.makePoster(self.pagecount - 1)
                if self.wallindex >= self.maxentry % self.posterX:
                    self.index = self.index + (self.posterX + self.maxentry % self.posterX)
                    if self.index >= self.maxentry:
                        self.index = self.index - self.maxentry
                else:
                    self.index = self.index + self.maxentry % self.posterX
                    if self.index >= self.maxentry:
                        self.index = self.index - self.maxentry
            elif self.wallindex > self.posterALL - 1:
                self.wallindex = self.wallindex - self.posterALL
                self.pagecount += 1
                self.makePoster(self.pagecount - 1)
                self.index = self.index + self.posterX
                if self.index >= self.maxentry:
                    self.index = self.index - self.maxentry
            else:
                self.index = self.index + self.posterX
                if self.index >= self.maxentry:
                    self.index = self.index - self.maxentry
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def PageDown(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex += self.posterALL
            if self.pagecount == self.pagemax - 1 and self.wallindex > self.posterALL + self.posterREST - 2:
                self.wallindex = self.posterREST - 1
                self.pagecount += 1
                self.makePoster(self.pagecount - 1)
                self.index = self.maxentry - 1
            elif self.pagecount == self.pagemax and self.wallindex > self.posterREST - 1:
                if self.wallindex >= self.posterX:
                    self.wallindex = self.wallindex % self.posterX
                self.pagecount = 1
                self.makePoster(self.pagecount - 1)
                if self.wallindex >= self.maxentry % self.posterX:
                    self.index = self.wallindex
                    if self.index >= self.maxentry:
                        self.index = self.index - self.maxentry
                else:
                    self.index = self.index + self.maxentry % self.posterX
                    if self.index >= self.maxentry:
                        self.index = self.index - self.maxentry
            elif self.wallindex > self.posterALL - 1:
                self.wallindex = self.wallindex - self.posterALL
                self.pagecount += 1
                self.makePoster(self.pagecount - 1)
                self.index = self.index + self.posterALL
                if self.index >= self.maxentry:
                    self.index = self.index - self.maxentry
            else:
                self.index = self.index + self.posterALL
                if self.index >= self.maxentry:
                    self.index = self.index - self.maxentry
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def leftUp(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex -= 1
            if self.wallindex < 0:
                if self.pagecount == 1:
                    self.wallindex = self.posterREST - 1
                    self.pagecount = self.pagemax
                else:
                    self.wallindex = self.posterALL - 1
                    self.pagecount -= 1
                if self.wallindex < 0:
                    self.wallindex = 0
                self.makePoster(self.pagecount - 1)
            self.index -= 1
            if self.index < 0:
                self.index = self.maxentry - 1
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def up(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex -= self.posterX
            if self.wallindex < 0:
                if self.pagecount == 1:
                    if self.oldindex < self.posterREST % self.posterX:
                        self.wallindex = self.posterREST // self.posterX * self.posterX + self.oldindex
                        if self.wallindex < 0:
                            self.wallindex = 0
                        self.index = self.index - self.posterREST % self.posterX
                        if self.index < 0:
                            self.index = self.maxentry + self.index
                    else:
                        self.wallindex = self.posterREST - 1
                        self.index = self.maxentry - 1
                    self.pagecount = self.pagemax
                    self.makePoster(self.pagecount - 1)
                else:
                    self.wallindex = self.posterALL + self.wallindex
                    self.pagecount -= 1
                    if self.wallindex < 0:
                        self.wallindex = 0
                    self.makePoster(self.pagecount - 1)
                    self.index = self.index - self.posterX
                    if self.index < 0:
                        self.index = self.maxentry + self.index
            else:
                self.index = self.index - self.posterX
                if self.index < 0:
                    self.index = self.maxentry + self.index
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def PageUp(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex -= self.posterALL
            if self.wallindex < 0:
                if self.pagecount == 1:
                    if self.oldindex < self.posterREST % self.posterX:
                        self.wallindex = self.posterREST // self.posterX * self.posterX + self.oldindex
                        if self.wallindex < 0:
                            self.wallindex = 0
                        self.index = self.index - self.posterREST % self.posterX
                        if self.index < 0:
                            self.index = self.maxentry + self.index
                    else:
                        self.wallindex = self.posterREST - 1
                        self.index = self.maxentry - 1
                    self.pagecount = self.pagemax
                    self.makePoster(self.pagecount - 1)
                else:
                    self.wallindex = self.posterALL + self.wallindex
                    self.pagecount -= 1
                    if self.wallindex < 0:
                        self.wallindex = 0
                    self.makePoster(self.pagecount - 1)
                    self.index = self.index - self.posterALL
                    if self.index < 0:
                        self.index = self.maxentry + self.index
            else:
                self.index = self.index - self.posterALL
                if self.index < 0:
                    self.index = self.maxentry + self.index
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def gotoEnd(self):
        if self.ready == True:
            self.oldindex = self.wallindex
            self.wallindex = self.posterREST - 1
            self.pagecount = self.pagemax
            self.makePoster(self.pagecount - 1)
            self.index = self.maxentry - 1
            self.paintFrame()
            try:
                if self.infofull == True:
                    self.showInfoFull(self.index)
            except IndexError:
                pass

    def showMP3(self):
        if self.ready == True:
            mp3s = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.filter in line:
                        mp3line = line.split(':::')
                        try:
                            mp3 = mp3line[3] + ' - ' + mp3line[6]
                        except IndexError:
                            mp3 = ' '

                        if mp3 != ' ':
                            mp3s = mp3s + mp3 + ':::'

                self.mp3s = [ i for i in mp3s.split(':::') ]
                self.mp3s.pop()
                self.session.openWithCallback(self.gotoMP3, allMP3List, self.mp3s, self.index)

    def gotoMP3(self, index):
        self.index = index
        self.oldindex = self.wallindex
        self.wallindex = self.index % self.posterALL
        self.pagecount = self.index // self.posterALL + 1
        self.makePoster(self.pagecount - 1)
        self.paintFrame()
        try:
            if self.infofull == True:
                self.showInfoFull(self.index)
        except IndexError:
            pass

    def filterArtist(self):
        if self.ready == True:
            artists = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    mp3line = line.split(':::')
                    try:
                        artist = mp3line[3]
                    except IndexError:
                        artist = ' '

                    if artist != ' ':
                        artists = artists + artist + ', '

                self.artists = [ i for i in artists.split(', ') ]
                self.artists.sort()
                self.artists.pop(0)
                try:
                    last = self.artists[-1]
                    for i in range(len(self.artists) - 2, -1, -1):
                        if last == self.artists[i]:
                            del self.artists[i]
                        else:
                            last = self.artists[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.session.openWithCallback(self.makeMP3, filterList, self.artists, 'Artist Filter')

    def filterAlbum(self):
        if self.ready == True:
            albums = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    mp3line = line.split(':::')
                    try:
                        album = mp3line[4]
                    except IndexError:
                        album = ' '

                    if album != ' ':
                        albums = albums + album + ', '

                self.albums = [ i for i in albums.split(', ') ]
                self.albums.sort()
                self.albums.pop(0)
                try:
                    last = self.albums[-1]
                    for i in range(len(self.albums) - 2, -1, -1):
                        if last == self.albums[i]:
                            del self.albums[i]
                        else:
                            last = self.albums[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.session.openWithCallback(self.makeMP3, filterList, self.albums, 'Album Filter')

    def filterGenre(self):
        if self.ready == True:
            genres = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    mp3line = line.split(':::')
                    try:
                        genre = mp3line[8]
                    except IndexError:
                        genre = ' '

                    if genre != ' ':
                        genres = genres + genre + ', '

                self.genres = [ i for i in genres.split(', ') ]
                self.genres.sort()
                self.genres.pop(0)
                try:
                    last = self.genres[-1]
                    for i in range(len(self.genres) - 2, -1, -1):
                        if last == self.genres[i]:
                            del self.genres[i]
                        else:
                            last = self.genres[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.session.openWithCallback(self.makeMP3, filterList, self.genres, 'Genre Filter')

    def sortDatabase(self):
        self.sortorder = config.plugins.mp3browser.sortorder.value
        f = open(self.database, 'r')
        lines = f.readlines()
        f.close()
        if self.sortorder == 'artist':
            lines.sort(key=lambda line: line.split(':::')[3].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
        elif self.sortorder == 'artist_reverse':
            lines.sort(key=lambda line: line.split(':::')[3].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
        elif self.sortorder == 'album':
            lines.sort(key=lambda line: line.split(':::')[4].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
        elif self.sortorder == 'album_reverse':
            lines.sort(key=lambda line: line.split(':::')[4].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
        elif self.sortorder == 'track':
            lines.sort(key=lambda line: line.split(':::')[6].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
        elif self.sortorder == 'track_reverse':
            lines.sort(key=lambda line: line.split(':::')[6].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
        elif self.sortorder == 'genre':
            lines.sort(key=lambda line: line.split(':::')[8])
        elif self.sortorder == 'genre_reverse':
            lines.sort(key=lambda line: line.split(':::')[8], reverse=True)
        elif self.sortorder == 'year':
            lines.sort(key=lambda line: line.split(':::')[7])
        elif self.sortorder == 'year_reverse':
            lines.sort(key=lambda line: line.split(':::')[7], reverse=True)
        elif self.sortorder == 'date':
            lines.sort(key=lambda line: line.split(':::')[2])
        elif self.sortorder == 'date_reverse':
            lines.sort(key=lambda line: line.split(':::')[2], reverse=True)
        elif self.sortorder == 'folder':
            lines.sort(key=lambda line: line.split(':::')[1])
        elif self.sortorder == 'folder_reverse':
            lines.sort(key=lambda line: line.split(':::')[1], reverse=True)
        fsorted = open(self.database + '.sorted', 'w')
        fsorted.writelines(lines)
        fsorted.close()
        os.rename(self.database + '.sorted', self.database)

    def editDatabase(self):
        if self.ready == True:
            self.session.openWithCallback(self.makeMP3, mp3Database)

    def wikipedia(self):
        if self.ready == True:
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/Wikipedia/plugin.pyo'):
                self.session.open(searchWikipedia, self.artistlist[self.index], self.tracklist[self.index], self.albumlist[self.index])
            else:
                self.session.open(MessageBox, _('\nThe Wikipedia plugin could not be found.\n\nPlease download and install the plugin from:\nwww.kashmir-plugins.de'), MessageBox.TYPE_INFO)
                return

    def showPath(self):
        if self.ready == True:
            self.session.open(MessageBox, _('\nMP3 File:\n%s') % self.mp3list[self.index], MessageBox.TYPE_INFO)

    def getIndex(self, list):
        return list.getSelectedIndex()

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def config(self):
        if self.ready == True:
            self.session.openWithCallback(self.exit, mp3BrowserConfig)

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def stop(self):
        self.playready = False
        if self.background == True:
            self.session.nav.stopService()
            self.session.nav.playService(self.oldService)

    def exit(self):
        self.playready = False
        if self.background == True and self.session.nav.getCurrentlyPlayingServiceReference() != self.oldService:
            self.session.nav.stopService()
            self.session.nav.playService(self.oldService)
        self.close()


class mp3Database(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,523" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<widget name="list2" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session):
        Screen.__init__(self, session)
        self.hideflag = True
        self.ready = False
        self.index = 0
        self['list'] = MenuList([])
        self['list2'] = MenuList([])
        self.actlist = 'list'
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'right': self.rightDown,
         'left': self.leftUp,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.infoScreen,
         'yellow': self.infoScreen,
         'green': self.infoScreen,
         'blue': self.hideScreen,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/database'
        self.onLayoutFinish.append(self.makeList)

    def makeList(self):
        self.datelist = []
        self.artistlist = []
        self.albumlist = []
        self.numberlist = []
        self.tracklist = []
        self.yearlist = []
        self.runtimelist = []
        self.bitratelist = []
        self.genrelist = []
        self.posterlist = []
        self.list = []
        if fileExists(self.database):
            f = open(self.database, 'r')
            for line in f:
                mp3line = line.split(':::')
                try:
                    date = mp3line[2]
                except IndexError:
                    date = ' '

                try:
                    artist = mp3line[3]
                except IndexError:
                    artist = ' '

                try:
                    album = mp3line[4]
                except IndexError:
                    album = ' '

                try:
                    number = mp3line[5]
                except IndexError:
                    number = ' '

                try:
                    track = mp3line[6]
                except IndexError:
                    track = ' '

                try:
                    year = mp3line[7]
                except IndexError:
                    year = ' '

                try:
                    genre = mp3line[8]
                except IndexError:
                    genre = ' '

                try:
                    runtime = mp3line[9]
                except IndexError:
                    runtime = ' '

                try:
                    bitrate = mp3line[10]
                except IndexError:
                    bitrate = ' '

                try:
                    poster = mp3line[11]
                except IndexError:
                    poster = 'http://www.kashmir-plugins.de/default.png'

                self.datelist.append(date)
                self.artistlist.append(artist)
                self.albumlist.append(album)
                self.numberlist.append(number)
                self.tracklist.append(track)
                self.yearlist.append(year)
                self.genrelist.append(genre)
                self.runtimelist.append(runtime)
                self.bitratelist.append(bitrate)
                self.posterlist.append(poster)
                self.list.append(artist + ' - ' + track)
                self['list'].l.setList(self.list)
                self['list'].moveToIndex(self.index)
                self.selectList()
                self.ready = True
                totalMP3 = len(self.list)
                if os.path.exists(config.plugins.mp3browser.mp3folder.value):
                    mp3Folder = os.statvfs(config.plugins.mp3browser.mp3folder.value)
                    freeSize = mp3Folder[statvfs.F_BSIZE] * mp3Folder[statvfs.F_BFREE] / 1024 / 1024 / 1024
                    title = 'Database Editor: %s MP3s (MP3 Folder: %s GB free)' % (str(totalMP3), str(freeSize))
                    self.setTitle(title)
                else:
                    title = 'Database Editor: %s MP3s (MP3 Folder: offline)' % str(totalMP3)
                    self.setTitle(title)

    def makeList2(self):
        self.list2 = []
        self.list2.append('Artist: ' + self.artistlist[self.index])
        self.list2.append('Album: ' + self.albumlist[self.index])
        self.list2.append('Year: ' + self.yearlist[self.index])
        self.list2.append('Track: ' + self.tracklist[self.index])
        self.list2.append('Number: ' + self.numberlist[self.index])
        self.list2.append('Runtime: ' + self.runtimelist[self.index])
        self.list2.append('Bitrate: ' + self.bitratelist[self.index])
        self.list2.append('Genre: ' + self.genrelist[self.index])
        self.list2.append('Cover: ' + self.posterlist[self.index])
        self['list2'].l.setList(self.list2)
        self.selectList2()

    def ok(self):
        if self.ready == True:
            if self.actlist == 'list':
                self.index = self['list'].getSelectedIndex()
                self.date = self.datelist[self.index]
                self.makeList2()
            elif self.actlist == 'list2':
                index = self['list2'].getSelectedIndex()
                if index == 0:
                    self.data = self.artistlist[self.index]
                elif index == 1:
                    self.data = self.albumlist[self.index]
                elif index == 2:
                    self.data = self.yearlist[self.index]
                elif index == 3:
                    self.data = self.tracklist[self.index]
                elif index == 4:
                    self.data = self.numberlist[self.index]
                elif index == 5:
                    self.data = self.runtimelist[self.index]
                elif index == 6:
                    self.data = self.bitratelist[self.index]
                elif index == 7:
                    self.data = self.genrelist[self.index]
                elif index == 8:
                    self.data = self.posterlist[self.index]
                self.session.openWithCallback(self.changeData, VirtualKeyBoard, title='Database Editor:', text=self.data)

    def changeData(self, newdata):
        if newdata and newdata != '' and newdata != self.data:
            newdata = ':::' + newdata + ':::'
            olddata = ':::' + self.data + ':::'
            database = open(self.database).read()
            for line in database.split('\n'):
                if search(self.date, line) is not None:
                    newline = line.replace(olddata, newdata)
                    database = database.replace(line, newline)

            f = open(self.database + '.new', 'w')
            f.write(database)
            f.close()
            os.rename(self.database, self.database + '-backup')
            os.rename(self.database + '.new', self.database)
            self.makeList()
            self.makeList2()

    def selectList(self):
        self.actlist = 'list'
        self['list'].show()
        self['list2'].hide()
        self['list'].selectionEnabled(1)
        self['list2'].selectionEnabled(0)

    def selectList2(self):
        self.actlist = 'list2'
        self['list'].hide()
        self['list2'].show()
        self['list'].selectionEnabled(0)
        self['list2'].selectionEnabled(1)

    def up(self):
        self[self.actlist].up()

    def down(self):
        self[self.actlist].down()

    def leftUp(self):
        self[self.actlist].pageUp()

    def rightDown(self):
        self[self.actlist].pageDown()

    def gotoEnd(self):
        end = len(self.list) - 1
        self['list'].moveToIndex(end)

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        if self.actlist == 'list':
            self.close(':::')
        elif self.actlist == 'list2':
            self.selectList()


class filterList(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="270,523" title=" ">\n\t\t\t\t<ePixmap position="-230,0" size="500,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="250,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, list, titel):
        Screen.__init__(self, session)
        self.list = list
        self.hideflag = True
        self.setTitle(titel)
        self['list'] = MenuList([])
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.infoScreen,
         'yellow': self.infoScreen,
         'green': self.infoScreen,
         'blue': self.hideScreen,
         '7': self.resetFilter,
         '8': self.resetFilter,
         '9': self.resetFilter,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self['list'].l.setList(self.list)

    def ok(self):
        current = self['list'].getCurrent()
        self.close(':::' + current + ':::')

    def resetFilter(self):
        self.close(':::')

    def down(self):
        self['list'].down()

    def up(self):
        self['list'].up()

    def gotoEnd(self):
        end = len(self.list) - 1
        self['list'].moveToIndex(end)

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        self.close(':::')


class allMP3List(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,523" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, list, index):
        Screen.__init__(self, session)
        self.list = list
        self.index = index
        self.hideflag = True
        self['list'] = MenuList([])
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.infoScreen,
         'yellow': self.infoScreen,
         'green': self.infoScreen,
         'blue': self.hideScreen,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self['list'].l.setList(self.list)
        try:
            self['list'].moveToIndex(self.index)
        except IndexError:
            pass

        totalMP3 = len(self.list)
        if os.path.exists(config.plugins.mp3browser.mp3folder.value):
            mp3Folder = os.statvfs(config.plugins.mp3browser.mp3folder.value)
            freeSize = mp3Folder[statvfs.F_BSIZE] * mp3Folder[statvfs.F_BFREE] / 1024 / 1024 / 1024
            title = '%s MP3s (MP3 Folder: %s GB free)' % (str(totalMP3), str(freeSize))
            self.setTitle(title)
        else:
            title = '%s MP3s (MP3 Folder: offline)' % str(totalMP3)
            self.setTitle(title)

    def ok(self):
        index = self['list'].getSelectedIndex()
        self.close(index)

    def down(self):
        self['list'].down()

    def up(self):
        self['list'].up()

    def gotoEnd(self):
        end = len(self.list) - 1
        self['list'].moveToIndex(end)

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        index = self['list'].getSelectedIndex()
        self.close(index)


class mp3List(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,538" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="poster1" position="10,33" size="120,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster2" position="10,158" size="120,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster3" position="10,283" size="120,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster4" position="10,408" size="120,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="list" position="140,33" size="580,500" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, poster, titel):
        Screen.__init__(self, session)
        self.poster = poster
        self.poster1 = '/tmp/mp3browser1.jpg'
        self.poster2 = '/tmp/mp3browser2.jpg'
        self.poster3 = '/tmp/mp3browser3.jpg'
        self.poster4 = '/tmp/mp3browser4.jpg'
        self['poster1'] = Pixmap()
        self['poster2'] = Pixmap()
        self['poster3'] = Pixmap()
        self['poster4'] = Pixmap()
        self.ready = False
        self.hideflag = True
        self.mp3list = []
        self.setTitle(titel)
        self['list'] = ItemList([])
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'right': self.rightDown,
         'left': self.leftUp,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.infoScreen,
         'yellow': self.infoScreen,
         'blue': self.hideScreen,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        try:
            poster1 = self.poster[0]
            self.download(poster1, self.getPoster1)
            self['poster1'].show()
        except IndexError:
            self['poster1'].hide()

        try:
            poster2 = self.poster[1]
            self.download(poster2, self.getPoster2)
            self['poster2'].show()
        except IndexError:
            self['poster2'].hide()

        try:
            poster3 = self.poster[2]
            self.download(poster3, self.getPoster3)
            self['poster3'].show()
        except IndexError:
            self['poster3'].hide()

        try:
            poster4 = self.poster[3]
            self.download(poster4, self.getPoster4)
            self['poster4'].show()
        except IndexError:
            self['poster4'].hide()

        idx = 0
        for x in self.poster:
            idx += 1

        for i in range(idx):
            res = ['']
            poster = sub('.*?[/]', '', self.poster[i])
            try:
                res.append(MultiContentEntryText(pos=(5, 5), size=(570, 115), font=26, color=16777215, color_sel=16777215, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP, text=poster))
            except IndexError:
                pass

            self.mp3list.append(res)

        self['list'].l.setList(self.mp3list)
        self['list'].l.setItemHeight(125)
        self.ready = True

    def ok(self):
        if self.ready == True:
            if fileExists(self.poster1):
                os.remove(self.poster1)
            if fileExists(self.poster2):
                os.remove(self.poster2)
            if fileExists(self.poster3):
                os.remove(self.poster3)
            if fileExists(self.poster4):
                os.remove(self.poster4)
            c = self['list'].getSelectedIndex()
            current = self.poster[c]
            self.close(current)

    def down(self):
        if self.ready == True:
            try:
                c = self['list'].getSelectedIndex()
            except IndexError:
                pass

            self['list'].down()
            if c + 1 == len(self.poster):
                try:
                    poster1 = self.poster[0]
                    self.download(poster1, self.getPoster1)
                    self['poster1'].show()
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[1]
                    self.download(poster2, self.getPoster2)
                    self['poster2'].show()
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[2]
                    self.download(poster3, self.getPoster3)
                    self['poster3'].show()
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[3]
                    self.download(poster4, self.getPoster4)
                    self['poster4'].show()
                except IndexError:
                    self['poster4'].hide()

            elif c % 4 == 3:
                try:
                    poster1 = self.poster[c + 1]
                    self.download(poster1, self.getPoster1)
                    self['poster1'].show()
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c + 2]
                    self.download(poster2, self.getPoster2)
                    self['poster2'].show()
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c + 3]
                    self.download(poster3, self.getPoster3)
                    self['poster3'].show()
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c + 4]
                    self.download(poster4, self.getPoster4)
                    self['poster4'].show()
                except IndexError:
                    self['poster4'].hide()

    def up(self):
        if self.ready == True:
            try:
                c = self['list'].getSelectedIndex()
            except IndexError:
                pass

            self['list'].up()
            if c == 0:
                l = len(self.poster)
                d = l % 4
                if d == 0:
                    d = 4
                try:
                    poster1 = self.poster[l - d]
                    self.download(poster1, self.getPoster1)
                    self['poster1'].show()
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[l - d + 1]
                    self.download(poster2, self.getPoster2)
                    self['poster2'].show()
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[l - d + 2]
                    self.download(poster3, self.getPoster3)
                    self['poster3'].show()
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[l - d + 3]
                    self.download(poster4, self.getPoster4)
                    self['poster4'].show()
                except IndexError:
                    self['poster4'].hide()

            elif c % 4 == 0:
                try:
                    poster1 = self.poster[c - 4]
                    self.download(poster1, self.getPoster1)
                    self['poster1'].show()
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c - 3]
                    self.download(poster2, self.getPoster2)
                    self['poster2'].show()
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c - 2]
                    self.download(poster3, self.getPoster3)
                    self['poster3'].show()
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c - 1]
                    self.download(poster4, self.getPoster4)
                    self['poster4'].show()
                except IndexError:
                    self['poster4'].hide()

    def rightDown(self):
        if self.ready == True:
            try:
                c = self['list'].getSelectedIndex()
            except IndexError:
                pass

            self['list'].pageDown()
            l = len(self.poster)
            d = c % 4
            e = l % 4
            if e == 0:
                e = 4
            if c + e >= l:
                pass
            elif d == 0:
                try:
                    poster1 = self.poster[c + 4]
                    self.download(poster1, self.getPoster1)
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c + 5]
                    self.download(poster2, self.getPoster2)
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c + 6]
                    self.download(poster3, self.getPoster3)
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c + 7]
                    self.download(poster4, self.getPoster4)
                except IndexError:
                    self['poster4'].hide()

            elif d == 1:
                try:
                    poster1 = self.poster[c + 3]
                    self.download(poster1, self.getPoster1)
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c + 4]
                    self.download(poster2, self.getPoster2)
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c + 5]
                    self.download(poster3, self.getPoster3)
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c + 6]
                    self.download(poster4, self.getPoster4)
                except IndexError:
                    self['poster4'].hide()

            elif d == 2:
                try:
                    poster1 = self.poster[c + 2]
                    self.download(poster1, self.getPoster1)
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c + 3]
                    self.download(poster2, self.getPoster2)
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c + 4]
                    self.download(poster3, self.getPoster3)
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c + 5]
                    self.download(poster4, self.getPoster4)
                except IndexError:
                    self['poster4'].hide()

            elif d == 3:
                try:
                    poster1 = self.poster[c + 1]
                    self.download(poster1, self.getPoster1)
                except IndexError:
                    self['poster1'].hide()

                try:
                    poster2 = self.poster[c + 2]
                    self.download(poster2, self.getPoster2)
                except IndexError:
                    self['poster2'].hide()

                try:
                    poster3 = self.poster[c + 3]
                    self.download(poster3, self.getPoster3)
                except IndexError:
                    self['poster3'].hide()

                try:
                    poster4 = self.poster[c + 4]
                    self.download(poster4, self.getPoster4)
                except IndexError:
                    self['poster4'].hide()

    def leftUp(self):
        if self.ready == True:
            try:
                c = self['list'].getSelectedIndex()
                self['list'].pageUp()
                d = c % 4
                if c < 4:
                    pass
                elif d == 0:
                    try:
                        poster1 = self.poster[c - 4]
                        self.download(poster1, self.getPoster1)
                        poster2 = self.poster[c - 3]
                        self.download(poster2, self.getPoster2)
                        poster3 = self.poster[c - 2]
                        self.download(poster3, self.getPoster3)
                        poster4 = self.poster[c - 1]
                        self.download(poster4, self.getPoster4)
                    except IndexError:
                        pass

                elif d == 1:
                    try:
                        poster1 = self.poster[c - 5]
                        self.download(poster1, self.getPoster1)
                        poster2 = self.poster[c - 4]
                        self.download(poster2, self.getPoster2)
                        poster3 = self.poster[c - 3]
                        self.download(poster3, self.getPoster3)
                        poster4 = self.poster[c - 2]
                        self.download(poster4, self.getPoster4)
                    except IndexError:
                        pass

                elif d == 2:
                    try:
                        poster1 = self.poster[c - 6]
                        self.download(poster1, self.getPoster1)
                        poster2 = self.poster[c - 5]
                        self.download(poster2, self.getPoster2)
                        poster3 = self.poster[c - 4]
                        self.download(poster3, self.getPoster3)
                        poster4 = self.poster[c - 3]
                        self.download(poster4, self.getPoster4)
                    except IndexError:
                        pass

                elif d == 3:
                    try:
                        poster1 = self.poster[c - 7]
                        self.download(poster1, self.getPoster1)
                        poster2 = self.poster[c - 6]
                        self.download(poster2, self.getPoster2)
                        poster3 = self.poster[c - 5]
                        self.download(poster3, self.getPoster3)
                        poster4 = self.poster[c - 4]
                        self.download(poster4, self.getPoster4)
                    except IndexError:
                        pass

                self['poster1'].show()
                self['poster2'].show()
                self['poster3'].show()
                self['poster4'].show()
            except IndexError:
                pass

    def gotoEnd(self):
        if self.ready == True:
            end = len(self.poster) - 1
            if end > 4:
                self['list'].moveToIndex(end)
                self.leftUp()
                self.rightDown()

    def getPoster1(self, output):
        f = open(self.poster1, 'wb')
        f.write(output)
        f.close()
        self.showPoster1(self.poster1)

    def showPoster1(self, poster1):
        currPic = loadPic(poster1, 120, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster1'].instance.setPixmap(currPic)

    def getPoster2(self, output):
        f = open(self.poster2, 'wb')
        f.write(output)
        f.close()
        self.showPoster2(self.poster2)

    def showPoster2(self, poster2):
        currPic = loadPic(poster2, 120, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster2'].instance.setPixmap(currPic)

    def getPoster3(self, output):
        f = open(self.poster3, 'wb')
        f.write(output)
        f.close()
        self.showPoster3(self.poster3)

    def showPoster3(self, poster3):
        currPic = loadPic(poster3, 120, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster3'].instance.setPixmap(currPic)

    def getPoster4(self, output):
        f = open(self.poster4, 'wb')
        f.write(output)
        f.close()
        self.showPoster4(self.poster4)

    def showPoster4(self, poster4):
        currPic = loadPic(poster4, 120, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster4'].instance.setPixmap(currPic)

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMovieBrowser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        if fileExists(self.poster1):
            os.remove(self.poster1)
        if fileExists(self.poster2):
            os.remove(self.poster2)
        if fileExists(self.poster3):
            os.remove(self.poster3)
        if fileExists(self.poster4):
            os.remove(self.poster4)
        self.close('none')


class searchWikipedia(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="550,145" title="Wikipedia - Search for Artist, Track or Album">\n\t\t\t\t<ePixmap position="0,0" size="550,50" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Wikipedia/pic/wiki.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,60" size="530,75" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, artist, track, album):
        Screen.__init__(self, session)
        self.hideflag = True
        self.artist = artist
        self.track = track
        self.album = album
        self.list = []
        self['list'] = MenuList([])
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'ChannelSelectBaseActions',
         'HelpActions',
         'NumberActions'], {'ok': self.ok,
         'cancel': self.exit,
         'down': self.down,
         'up': self.up,
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.infoScreen,
         'yellow': self.infoScreen,
         'green': self.infoScreen,
         'blue': self.hideScreen,
         '0': self.gotoEnd,
         'displayHelp': self.infoScreen}, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self.list.append('Artist: ' + self.artist)
        self.list.append('Track: ' + self.track)
        self.list.append('Album: ' + self.album)
        self['list'].l.setList(self.list)

    def ok(self):
        index = self['list'].getSelectedIndex()
        if index == 0:
            name = self.artist
        elif index == 1:
            name = self.track
        elif index == 2:
            name = self.album
        if config.plugins.mp3browser.language.value == 'de':
            from Plugins.Extensions.Wikipedia.plugin import wikiSearch
            self.session.open(wikiSearch, name)
        elif config.plugins.mp3browser.language.value == 'es':
            from Plugins.Extensions.Wikipedia.plugin import wikiSearch_es
            self.session.open(wikiSearch_es, name)
        else:
            from Plugins.Extensions.Wikipedia.plugin import wikiSearch_en
            self.session.open(wikiSearch_en, name)

    def down(self):
        self['list'].down()

    def up(self):
        self['list'].up()

    def gotoEnd(self):
        end = len(self.list) - 1
        self['list'].moveToIndex(end)

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        self.close()


class mp3Fav(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="520,495" title=" ">\n\t\t\t\t<ePixmap position="-105,0" size="625,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<ePixmap position="10,5" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/red.png" alphatest="blend" zPosition="2" />\n\t\t\t\t<widget name="label" position="34,5" size="250,20" font="Regular;16" foregroundColor="#697279" backgroundColor="#FFFFFF" halign="left" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="label2" position="310,5" size="200,20" font="Regular;16" foregroundColor="#697279" backgroundColor="#FFFFFF" halign="right" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="favmenu" position="10,60" size="500,425" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'
    skinHD = '\n\t\t\t<screen position="center,center" size="620,605" title=" ">\n\t\t\t\t<ePixmap position="-55,0" size="675,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<ePixmap position="10,5" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/red.png" alphatest="blend" zPosition="2" />\n\t\t\t\t<widget name="label" position="34,4" size="250,22" font="Regular;18" foregroundColor="#697279" backgroundColor="#FFFFFF" halign="left" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="label2" position="360,4" size="250,22" font="Regular;18" foregroundColor="#697279" backgroundColor="#FFFFFF" halign="right" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="favmenu" position="10,70" size="600,525" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session):
        deskWidth = getDesktop(0).size().width()
        if deskWidth == 1280:
            self.skin = mp3Fav.skinHD
            self.xd = False
        else:
            self.skin = mp3Fav.skin
            self.xd = True
        self.session = session
        Screen.__init__(self, session)
        self.ready = False
        self.hideflag = True
        self.count = 0
        self.favmp3 = []
        self.favlist = []
        self['favmenu'] = MenuList([])
        self['label'] = Label('= Remove Favorit')
        self['label2'] = Label('0/1 = Move to End/First')
        self['actions'] = ActionMap(['OkCancelActions',
         'DirectionActions',
         'ColorActions',
         'HelpActions',
         'NumberActions'], {'ok': self.exit,
         'cancel': self.exit,
         'right': self.rightDown,
         'left': self.leftUp,
         'down': self.down,
         'up': self.up,
         'red': self.red,
         'yellow': self.infoScreen,
         'green': self.infoScreen,
         'blue': self.hideScreen,
         '0': self.move2end,
         '1': self.move2first,
         'displayHelp': self.infoScreen}, -1)
        self.makeFav()

    def makeFav(self):
        self.setTitle('MP3 Browser:::Favorites')
        self.favorites = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/favorites'
        if fileExists(self.favorites):
            f = open(self.favorites, 'r')
            for line in f:
                self.count += 1
                favline = line.split(':::')
                titel = str(favline[3] + ' - ' + favline[6])
                mp3 = favline[1]
                self.favlist.append(titel)
                self.favmp3.append(mp3)

            f.close()
            self['favmenu'].l.setList(self.favlist)
            self.ready = True

    def red(self):
        if len(self.favlist) > 0:
            try:
                c = self.getIndex(self['favmenu'])
                name = self.favlist[c]
            except IndexError:
                name = ''

            self.session.openWithCallback(self.red_return, MessageBox, _("\nDelete MP3 '%s' from Favorites?") % name, MessageBox.TYPE_YESNO)

    def red_return(self, answer):
        if answer is True:
            c = self.getIndex(self['favmenu'])
            try:
                mp3 = self.favmp3[c]
            except IndexError:
                mp3 = 'NONE'

            data = ''
            f = open(self.favorites, 'r')
            for line in f:
                if mp3 not in line and line != '\n':
                    data = data + line

            f.close()
            fnew = open(self.favorites + '.new', 'w')
            fnew.write(data)
            fnew.close()
            os.rename(self.favorites + '.new', self.favorites)
            self.favlist = []
            self.favmp3 = []
            self.makeFav()

    def move2first(self):
        try:
            c = self.getIndex(self['favmenu'])
            fav = self.favmp3[c]
            f = open(self.favorites, 'r')
            for line in f:
                if fav in line:
                    favdata = line

            f.close()
            fnew = open(self.favorites + '.new', 'w')
            fnew.write(favdata)
            fnew.close()
            data = ''
            f = open(self.favorites, 'r')
            for line in f:
                if fav not in line and line != '\n':
                    data = data + line

            f.close()
            fnew = open(self.favorites + '.new', 'a')
            fnew.write(data)
            fnew.close()
            os.rename(self.favorites + '.new', self.favorites)
            self.favlist = []
            self.favmp3 = []
            self.makeFav()
        except IndexError:
            pass

    def move2end(self):
        try:
            c = self.getIndex(self['favmenu'])
            fav = self.favmp3[c]
            f = open(self.favorites, 'r')
            for line in f:
                if fav in line:
                    favdata = line

            f.close()
            data = ''
            f = open(self.favorites, 'r')
            for line in f:
                if fav not in line and line != '\n':
                    data = data + line

            f.close()
            fnew = open(self.favorites + '.new', 'w')
            fnew.write(data)
            fnew.close()
            fnew = open(self.favorites + '.new', 'a')
            fnew.write(favdata)
            fnew.close()
            os.rename(self.favorites + '.new', self.favorites)
            self.favlist = []
            self.favmp3 = []
            self.makeFav()
        except IndexError:
            pass

    def getIndex(self, list):
        return list.getSelectedIndex()

    def down(self):
        self['favmenu'].down()

    def up(self):
        self['favmenu'].up()

    def rightDown(self):
        self['favmenu'].pageDown()

    def leftUp(self):
        self['favmenu'].pageUp()

    def infoScreen(self):
        self.session.open(infoScreenMP3Browser)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            self.hide()
        else:
            self.hideflag = True
            self.show()

    def exit(self):
        self.close()


class ItemList(MenuList):

    def __init__(self, items, enableWrapAround = True):
        MenuList.__init__(self, items, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(26, gFont('Regular', 26))
        self.l.setFont(24, gFont('Regular', 24))
        self.l.setFont(22, gFont('Regular', 22))
        self.l.setFont(20, gFont('Regular', 20))


class infoScreenMP3Browser(Screen):
    skin = '''<screen position="center,center" size="425,425" backgroundColor="#FFFFFF" title="MP3 Browser Key Assignment" >
	      <widget name="info" position="0,0" size="425,425" zPosition="1"/>
	      <widget name="greenbutton" position="10,7" size="18,18" alphatest="blend" zPosition="3" />
	      <widget name="yellowbutton" position="10,28" size="18,18" alphatest="blend" zPosition="3" />
	      <widget name="redbutton" position="10,49" size="18,18" alphatest="blend" zPosition="3" />
	      <widget name="bluebutton" position="10,70" size="18,18" alphatest="blend" zPosition="3" />
	      <widget name="label" position="10,5" size="415,420" font="Regular;18" foregroundColor="#6B6B6B" backgroundColor="#FFFFFF" transparent="1" zPosition="2" />
	      <widget name="donate" position="0,72" size="425,350" font="Regular;18" foregroundColor="#6B6B6B" backgroundColor="#FFFFFF" halign="center" valign="center" transparent="1" zPosition="2" />
	      </screen>'''

    def __init__(self, session):
        self.skin = infoScreenMP3Browser.skin
        Screen.__init__(self, session)
        self.first = True
        self.version = '0.3rc1'
        self.link = 'http://sites.google.com/site/kashmirplugins/home/mp3-browser'
        self.lang = language.getLanguage()[:2]
        self['label'] = Label('     : Update Cover by Album Title\n     : Update Cover by Track Title\n     : Add MP3 to Favorites\n     : Toggle hide / show Plugin\n\nText Button: Edit Database\nVideo/PVR/Filelist Button: Update Database\nInfo/EPG Button: Toggle show / hide Infos\nStop Button: Stop Playlist / Background Play\nBouquet Button +-: Next / Previous Page\n\nButton 1: Show list of all MP3\nButton 2: Show MP3 Favorites\nButton 3: Show path to MP3 file\nButton 5: Play (all filtered MP3) list\nButton 6: Wikipedia information\nButton 7: Filter list for Artist\nButton 8: Filter list for Album\nButton 9: Filter list for Genre\nButton 0: Go to end of list')
        self['donate'] = Label()
        self['info'] = Pixmap()
        self['greenbutton'] = Pixmap()
        self['yellowbutton'] = Pixmap()
        self['redbutton'] = Pixmap()
        self['bluebutton'] = Pixmap()
        self['actions'] = ActionMap(['OkCancelActions'], {'ok': self.exit,
         'cancel': self.exit}, -1)
        self.onLayoutFinish.append(self.makeCheck)

    def makeCheck(self):
        self.showGreenButton()
        self.showYellowButton()
        self.showRedButton()
        self.showBlueButton()

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def showGreenButton(self):
        currPic = loadPic('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/green.png', 18, 18, 3, 0, 0, 1)
        if currPic != None:
            self['greenbutton'].instance.setPixmap(currPic)
            self['greenbutton'].show()

    def showYellowButton(self):
        currPic = loadPic('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/yellow.png', 18, 18, 3, 0, 0, 1)
        if currPic != None:
            self['yellowbutton'].instance.setPixmap(currPic)
            self['yellowbutton'].show()

    def showRedButton(self):
        currPic = loadPic('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/red.png', 18, 18, 3, 0, 0, 1)
        if currPic != None:
            self['redbutton'].instance.setPixmap(currPic)
            self['redbutton'].show()

    def showBlueButton(self):
        currPic = loadPic('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/blue.png', 18, 18, 3, 0, 0, 1)
        if currPic != None:
            self['bluebutton'].instance.setPixmap(currPic)
            self['bluebutton'].show()

    def exit(self):
        if self.first == True:
            self.first = False
            self.setTitle('MP3 Browser ' + self.version)
            self['label'].hide()
            self['greenbutton'].hide()
            self['yellowbutton'].hide()
            self['redbutton'].hide()
            self['bluebutton'].hide()
            png = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/info.png'
            if fileExists(png):
                PNG = loadPic(png, 425, 425, 3, 0, 0, 1)
                if PNG != None:
                    self['info'].instance.setPixmap(PNG)
        else:
            self.close()


class mp3BrowserConfig(ConfigListScreen, Screen):
    skin = '\n\t\t\t<screen position="center,center" size="530,500" backgroundColor="#20000000" title="MP3 Browser Setup">\n\t\t\t\t<ePixmap position="-100,0" size="630,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="9,37" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<widget name="config" position="9,38" size="512,125" itemHeight="25" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<ePixmap position="9,164" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<eLabel position="150,173" size="125,20" font="Regular;18" halign="left" text="Save" transparent="1" zPosition="1" />\n\t\t\t\t<eLabel position="365,173" size="125,20" font="Regular;18" halign="left" text="Cancel" transparent="1" zPosition="1" />\n\t\t\t\t<ePixmap position="125,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/green.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="340,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/red.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="plugin" position="9,203" size="512,288" alphatest="blend" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session):
        Screen.__init__(self, session)
        self['plugin'] = Pixmap()
        self.sortorder = config.plugins.mp3browser.sortorder.value
        self.cachefolder = config.plugins.mp3browser.cachefolder.value
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/database'
        self.ready = True
        list = []
        list.append(getConfigListEntry(_('Plugin Size:'), config.plugins.mp3browser.plugin_size))
        self.foldername = getConfigListEntry(_('MP3 Folder:'), config.plugins.mp3browser.mp3folder)
        list.append(self.foldername)
        list.append(getConfigListEntry(_('Cache Folder:'), config.plugins.mp3browser.cachefolder))
        list.append(getConfigListEntry(_('Search Cover by:'), config.plugins.mp3browser.searchby))
        list.append(getConfigListEntry(_('Sort Order:'), config.plugins.mp3browser.sortorder))
        list.append(getConfigListEntry(_('Headline Color:'), config.plugins.mp3browser.color))
        list.append(getConfigListEntry(_('Wikipedia Language:'), config.plugins.mp3browser.language))
        list.append(getConfigListEntry(_('Play in Background:'), config.plugins.mp3browser.background))
        list.append(getConfigListEntry(_('Reset Database:'), config.plugins.mp3browser.reset))
        ConfigListScreen.__init__(self, list, on_change=self.UpdateComponents)
        self['key_red'] = Label(_('Cancel'))
        self['key_green'] = Label(_('Save'))           
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'ok': self.save,
         'cancel': self.cancel,
         'red': self.cancel,
         'green': self.save}, -1)
        self.onLayoutFinish.append(self.UpdateComponents)

    def UpdateComponents(self):
        png = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/' + str(config.plugins.mp3browser.plugin_size.value) + '.png'
        if fileExists(png):
            PNG = loadPic(png, 512, 288, 3, 0, 0, 1)
            if PNG != None:
                self['plugin'].instance.setPixmap(PNG)
        current = self['config'].getCurrent()
        if current == self.foldername:
            self.session.openWithCallback(self.folderSelected, FolderSelection, config.plugins.mp3browser.mp3folder.value)

    def folderSelected(self, folder):
        if folder is not None:
            config.plugins.mp3browser.mp3folder.value = folder
            config.plugins.mp3browser.mp3folder.save()

    def save(self):
        if self.ready == True:
            self.ready = False
            if config.plugins.mp3browser.sortorder.value != self.sortorder:
                if fileExists(self.database):
                    f = open(self.database, 'r')
                    lines = f.readlines()
                    f.close()
                    if config.plugins.mp3browser.sortorder.value == 'artist':
                        lines.sort(key=lambda line: line.split(':::')[3].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
                    elif config.plugins.mp3browser.sortorder.value == 'artist_reverse':
                        lines.sort(key=lambda line: line.split(':::')[3].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'album':
                        lines.sort(key=lambda line: line.split(':::')[4].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
                    elif config.plugins.mp3browser.sortorder.value == 'album_reverse':
                        lines.sort(key=lambda line: line.split(':::')[4].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'track':
                        lines.sort(key=lambda line: line.split(':::')[6].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
                    elif config.plugins.mp3browser.sortorder.value == 'track_reverse':
                        lines.sort(key=lambda line: line.split(':::')[6].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'genre':
                        lines.sort(key=lambda line: line.split(':::')[8])
                    elif config.plugins.mp3browser.sortorder.value == 'genre_reverse':
                        lines.sort(key=lambda line: line.split(':::')[8], reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'year':
                        lines.sort(key=lambda line: line.split(':::')[7])
                    elif config.plugins.mp3browser.sortorder.value == 'year_reverse':
                        lines.sort(key=lambda line: line.split(':::')[7], reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'date':
                        lines.sort(key=lambda line: line.split(':::')[2])
                    elif config.plugins.mp3browser.sortorder.value == 'date_reverse':
                        lines.sort(key=lambda line: line.split(':::')[2], reverse=True)
                    elif config.plugins.mp3browser.sortorder.value == 'folder':
                        lines.sort(key=lambda line: line.split(':::')[1])
                    elif config.plugins.mp3browser.sortorder.value == 'folder_reverse':
                        lines.sort(key=lambda line: line.split(':::')[1], reverse=True)
                    fsorted = open(self.database + '.sorted', 'w')
                    fsorted.writelines(lines)
                    fsorted.close()
                    os.rename(self.database + '.sorted', self.database)
            if config.plugins.mp3browser.reset.value == 'yes':
                if fileExists(self.database):
                    os.rename(self.database, self.database + '-backup')
                open('/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/db/reset', 'w').close()
                config.plugins.mp3browser.reset.value = 'no'
                config.plugins.mp3browser.reset.save()
            if config.plugins.mp3browser.cachefolder.value != self.cachefolder:
                self.container = eConsoleAppContainer()
                self.container.appClosed.append(self.finished)
                newcache = sub('/cache', '', config.plugins.mp3browser.cachefolder.value)
                self.container.execute("mkdir -p '%s' && cp -r '%s' '%s' && rm -rf '%s'" % (config.plugins.mp3browser.cachefolder.value,
                 self.cachefolder,
                 newcache,
                 self.cachefolder))
            else:
                for x in self['config'].list:
                    x[1].save()
                    configfile.save()

                self.exit()

    def finished(self, retval):
        del self.container.appClosed[:]
        del self.container
        for x in self['config'].list:
            x[1].save()
            configfile.save()

        self.exit()

    def cancel(self):
        for x in self['config'].list:
            x[1].cancel()

        self.exit()

    def exit(self):
        self.session.openWithCallback(self.close, mp3Browser)


class FolderSelection(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="530,500" backgroundColor="#20000000" title="MP3 Browser Setup">\n\t\t\t\t<ePixmap position="-100,0" size="630,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/logo.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="9,37" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<widget name="folderlist" position="9,38" size="512,125" itemHeight="25" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<ePixmap position="9,164" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<eLabel position="150,173" size="125,20" font="Regular;18" halign="left" text="Save" transparent="1" zPosition="1" />\n\t\t\t\t<eLabel position="365,173" size="125,20" font="Regular;18" halign="left" text="Cancel" transparent="1" zPosition="1" />\n\t\t\t\t<ePixmap position="125,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/green.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="340,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/red.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="plugin" position="9,203" size="512,288" alphatest="blend" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, folder):
        Screen.__init__(self, session)
        self['plugin'] = Pixmap()
        noFolder = ['/bin',
         '/boot',
         '/dev',
         '/etc',
         '/lib',
         '/proc',
         '/sbin',
         '/sys']
        self['folderlist'] = FileList(folder, showDirectories=True, showFiles=False, inhibitDirs=noFolder)
        self['actions'] = ActionMap(['OkCancelActions', 'DirectionActions', 'ColorActions'], {'ok': self.ok,
         'cancel': self.cancel,
         'right': self.right,
         'left': self.left,
         'down': self.down,
         'up': self.up,
         'red': self.cancel,
         'green': self.green}, -1)
        self.onLayoutFinish.append(self.pluginPic)

    def pluginPic(self):
        png = '/usr/lib/enigma2/python/Plugins/Extensions/MP3Browser/pic/' + str(config.plugins.mp3browser.plugin_size.value) + '.png'
        if fileExists(png):
            PNG = loadPic(png, 512, 288, 3, 0, 0, 1)
            if PNG != None:
                self['plugin'].instance.setPixmap(PNG)

    def ok(self):
        if self['folderlist'].canDescent():
            self['folderlist'].descent()

    def right(self):
        self['folderlist'].pageDown()

    def left(self):
        self['folderlist'].pageUp()

    def down(self):
        self['folderlist'].down()

    def up(self):
        self['folderlist'].up()

    def green(self):
        self.close(self['folderlist'].getSelection()[0])

    def cancel(self):
        self.close(None)


def main(session, **kwargs):
    session.open(mp3Browser)


def Plugins(**kwargs):
    return []