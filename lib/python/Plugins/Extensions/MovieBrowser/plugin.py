# 2013.06.25 13:29:48 CEST
#Embedded file name: /usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/MovieBrowser.py
from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigDirectory, ConfigSlider, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.Sources.List import List
from enigma import eListboxPythonMultiContent, eConsoleAppContainer, ePoint, eServiceReference, eTimer, getDesktop, gFont, loadPic, loadPNG, RT_HALIGN_LEFT
from Plugins.Plugin import PluginDescriptor
from re import findall, search, split, sub
from Screens.ChannelSelection import ChannelSelection
from Screens.InfoBar import MoviePlayer as OrgMoviePlayer
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from string import find
from Tools.Directories import fileExists
from twisted.web import client, error
from twisted.web.client import getPage
from urllib2 import Request, urlopen, URLError, HTTPError
import os, re, statvfs, socket, sys, time, urllib
from os import system, walk
config.plugins.moviebrowser = ConfigSubsection()
config.plugins.moviebrowser.style = ConfigSelection(default='backdrop', choices=[('backdrop', _('Backdrop')), ('posterwall', _('Posterwall'))])
config.plugins.moviebrowser.moviefolder = ConfigDirectory(default='/media/')
config.plugins.moviebrowser.cachefolder = ConfigSelection(default='/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/cache', choices=[('/media/usb/moviebrowser/cache', _('/media/usb')), ('/media/hdd/moviebrowser/cache', _('/media/hdd')), ('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/cache', _('Default'))])
config.plugins.moviebrowser.database = ConfigSelection(default='tmdb', choices=[('tmdb', _('TMDb')), ('imdb', _('IMDb')), ('tvdb', _('TheTVDb'))])
config.plugins.moviebrowser.language = ConfigSelection(default='en', choices=[('de', _('Deutsch')),
 ('en', _('English')),
 ('es', _('Espanol')),
 ('ru', _('P\xd1\x83\xd1\x81\xd1\x81\xd0\xba\xd0\xb8\xd0\xb9'))])
deskWidth = getDesktop(0).size().width()
if deskWidth == 1280:
    config.plugins.moviebrowser.plugin_size = ConfigSelection(default='full', choices=[('full', _('Plugin Full')), ('normal', _('Plugin Normal'))])
else:
    config.plugins.moviebrowser.plugin_size = ConfigSelection(default='normal', choices=[('full', _('Plugin Full')), ('normal', _('Plugin Normal'))])
config.plugins.moviebrowser.filter = ConfigSelection(default=':::', choices=[(':::', _('Movies + Series')), (':::Movie:::', _('Movies')), (':::Series:::', _('Series'))])
config.plugins.moviebrowser.backdrops = ConfigSelection(default='show', choices=[('show', _('Show')), ('hide', _('Hide'))])
config.plugins.moviebrowser.plotfull = ConfigSelection(default='hide', choices=[('show', _('Show')), ('hide', _('Hide'))])
config.plugins.moviebrowser.plotfont = ConfigSelection(default='normal', choices=[('normal', _('Normal')), ('small', _('Small'))])
config.plugins.moviebrowser.sortorder = ConfigSelection(default='name', choices=[('name', _('Movie Title A-Z')),
 ('name_reverse', _('Movie Title Z-A')),
 ('rating', _('Movie Rating 0-10')),
 ('rating_reverse', _('Movie Rating 10-0')),
 ('year', _('Movie Release Date Ascending')),
 ('year_reverse', _('Movie Release Date Descending')),
 ('date', _('File Creation Date Ascending')),
 ('date_reverse', _('File Creation Date Descending')),
 ('folder', _('Movie Folder Ascending')),
 ('folder_reverse', _('Movie Folder Descending'))])
config.plugins.moviebrowser.reset = ConfigSelection(default='no', choices=[('no', _('No')), ('yes', _('Yes'))])
config.plugins.moviebrowser.menu = ConfigSelection(default='no', choices=[('no', _('No')), ('yes', _('Yes'))])
config.plugins.moviebrowser.showtv = ConfigSelection(default='show', choices=[('show', _('Show')), ('hide', _('Hide'))])
config.plugins.moviebrowser.m1v = ConfigSelection(default='no', choices=[('no', _('No')), ('yes', _('Yes'))])
config.plugins.moviebrowser.transparency = ConfigSlider(default=200, limits=(0, 255))
config.plugins.moviebrowser.color = ConfigSelection(default='#007895BC', choices=[('#007895BC', _('Default')),
 ('#00F0A30A', _('Amber')),
 ('#00825A2C', _('Brown')),
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

class MoviePlayer(OrgMoviePlayer):
	def __init__(self, session, service):
		self.session = session
		OrgMoviePlayer.__init__(self, session, service)
		self.skinName = "MoviePlayer"
		OrgMoviePlayer.WithoutStopClose = True

	def doEofInternal(self, playing):
		self.leavePlayer()
			
	def leavePlayer(self):
		self.close()
		
class movieBrowserBackdrop(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="1024,576" flags="wfNoBorder" title="  " >\n\t\t\t\t<widget name="backdrop" position="0,0" size="1024,576" alphatest="on" transparent="0" zPosition="1" />\n\t\t\t\t<widget name="infoback" position="15,15" size="460,400" alphatest="blend" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="plotfullback" position="549,15" size="460,400" alphatest="blend" transparent="1" zPosition="2" />\n\n\t\t\t\t<widget name="name" position="25,16" size="440,55" font="Regular;24" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="3" />\n\t\t\t\t<eLabel text="Rating:" position="25,70" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="4" />\n\t\t\t\t<widget name="ratings" position="25,100" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="5" />\n\t\t\t\t<widget name="ratingsback" position="25,100" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="6" />\n\t\t\t\t<widget name="ratingtext" position="245,100" size="40,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="7" />\n\t\t\t\t<eLabel text="Director:" position="25,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="8" />\n\t\t\t\t<widget name="director" position="25,170" size="285,50" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="9" />\n\t\t\t\t<eLabel text="Country:" position="320,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="10" />\n\t\t\t\t<widget name="country" position="320,170" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="11" />\n\t\t\t\t<eLabel text="Actors:" position="25,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="12" />\n\t\t\t\t<widget name="actors" position="25,240" size="285,95" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="13" />\n\t\t\t\t<eLabel text="Year:" position="320,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t<widget name="year" position="320,240" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="15" />\n\t\t\t\t<eLabel text="Runtime:" position="320,280" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="16" />\n\t\t\t\t<widget name="runtime" position="320,310" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t<eLabel text="Genres:" position="25,350" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t<widget name="genres" position="25,380" size="440,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t<widget name="plotfull" position="559,22" size="440,390" font="{font}" foregroundColor="#FFFFFF" transparent="1" zPosition="20" />\n\t\t\t\t<widget name="eposter" position="25,50" size="440,330" alphatest="on" transparent="1" zPosition="21" />\n\n\t\t\t\t<widget name="poster0" position="-42,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back0" position="-42,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster1" position="55,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back1" position="55,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster2" position="152,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back2" position="152,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster3" position="249,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back3" position="249,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster4" position="346,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back4" position="346,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster5" position="443,352" size="138,207" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster6" position="586,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back6" position="586,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster7" position="683,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back7" position="683,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster8" position="780,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back8" position="780,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster9" position="877,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back9" position="877,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t\t<widget name="poster10" position="974,426" size="92,138" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back10" position="974,426" size="92,138" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_back.png" />\n\t\t\t</screen>'
    skinHD = '\n\t\t\t<screen position="center,center" size="1280,720" flags="wfNoBorder" title="  " >\n\t\t\t\t<widget name="backdrop" position="0,0" size="1280,720" alphatest="on" transparent="0" zPosition="1" />\n\t\t\t\t<widget name="infoback" position="25,25" size="525,430" alphatest="blend" transparent="1" zPosition="2" />\n\t\t\t\t<widget name="plotfullback" position="730,25" size="525,430" alphatest="blend" transparent="1" zPosition="2" />\n\n\t\t\t\t<widget name="name" position="40,30" size="495,70" font="Regular;28" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="3" />\n\t\t\t\t<eLabel text="Rating:" position="40,100" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="4" />\n\t\t\t\t<widget name="ratings" position="40,130" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="5" />\n\t\t\t\t<widget name="ratingsback" position="40,130" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="6" />\n\t\t\t\t<widget name="ratingtext" position="260,130" size="50,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="7" />\n\t\t\t\t<eLabel text="Director:" position="40,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="8" />\n\t\t\t\t<widget name="director" position="40,200" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="9" />\n\t\t\t\t<eLabel text="Country:" position="370,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="10" />\n\t\t\t\t<widget name="country" position="370,200" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="11" />\n\t\t\t\t<eLabel text="Actors:" position="40,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="12" />\n\t\t\t\t<widget name="actors" position="40,270" size="320,102" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="13" />\n\t\t\t\t<eLabel text="Year:" position="370,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t<widget name="year" position="370,270" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="15" />\n\t\t\t\t<eLabel text="Runtime:" position="370,310" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="16" />\n\t\t\t\t<widget name="runtime" position="370,340" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t<eLabel text="Genres:" position="40,380" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t<widget name="genres" position="40,410" size="500,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t<widget name="plotfull" position="745,40" size="495,393" font="{font}" foregroundColor="#FFFFFF" transparent="1" zPosition="20" />\n\t\t\t\t<widget name="eposter" position="37,53" size="500,375" alphatest="on" transparent="1" zPosition="21" />\n\n\t\t\t\t<widget name="poster0" position="-65,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back0" position="-65,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster1" position="40,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back1" position="40,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster2" position="145,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back2" position="145,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster3" position="250,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back3" position="250,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster4" position="355,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back4" position="355,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster5" position="460,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back5" position="460,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster6" position="565,455" size="150,225" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster7" position="720,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back7" position="720,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster8" position="825,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back8" position="825,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster9" position="930,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back9" position="930,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster10" position="1035,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back10" position="1035,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster11" position="1140,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back11" position="1140,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t\t<widget name="poster12" position="1245,535" size="100,150" zPosition="21" transparent="1" alphatest="on" />\n\t\t\t\t<widget name="poster_back12" position="1245,535" size="100,150" zPosition="22" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />\n\t\t\t</screen>'

    def __init__(self, session, index, content, filter):
        if config.plugins.moviebrowser.plugin_size.value == 'full':
            self.xd = False
            color = config.plugins.moviebrowser.color.value
            if config.plugins.moviebrowser.plotfont.value == 'normal':
                font = 'Regular;22'
            else:
                font = 'Regular;20'
            self.dict = {'color': color,
             'font': font}
            self.skin = applySkinVars(movieBrowserBackdrop.skinHD, self.dict)
        else:
            self.xd = True
            color = config.plugins.moviebrowser.color.value
            if config.plugins.moviebrowser.plotfont.value == 'normal':
                font = 'Regular;20'
            else:
                font = 'Regular;18'
            self.dict = {'color': color,
             'font': font}
            self.skin = applySkinVars(movieBrowserBackdrop.skin, self.dict)
        Screen.__init__(self, session)
        self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
        self.hideflag = True
        self.ready = False
        self.renew = False
        self.update = False
        self.tmdbposter = False
        self.content = content
        self.filter = filter
        if config.plugins.moviebrowser.language.value == 'de':
            self.language = '&language=de'
        elif config.plugins.moviebrowser.language.value == 'es':
            self.language = '&language=es'
        elif config.plugins.moviebrowser.language.value == 'ru':
            self.language = '&language=ru'
        else:
            self.language = '&language=en'
        if config.plugins.moviebrowser.database.value == 'tmdb':
            self.firstdatabase = 'tmdb'
        elif config.plugins.moviebrowser.database.value == 'imdb':
            self.firstdatabase = 'imdb'
        else:
            self.firstdatabase = 'tvdb'
        self.namelist = []
        self.movielist = []
        self.datelist = []
        self.infolist = []
        self.plotlist = []
        self.posterlist = []
        self.backdroplist = []
        self.contentlist = []
        self['name'] = Label()
        self['director'] = Label()
        self['actors'] = Label()
        self['year'] = Label()
        self['runtime'] = Label()
        self['country'] = Label()
        self['genres'] = Label()
        self['ratingtext'] = Label()
        self['ratings'] = ProgressBar()
        self['ratings'].hide()
        self['ratingsback'] = Pixmap()
        self['ratingsback'].hide()
        self['infoback'] = Pixmap()
        self['backdrop'] = Pixmap()
        if config.plugins.moviebrowser.backdrops.value == 'show':
            self.backdrops = True
        else:
            self.backdrops = False
        if config.plugins.moviebrowser.plotfull.value == 'show':
            self.plotfull = True
        else:
            self.plotfull = False
        self['plotfull'] = Label()
        self['plotfull'].hide()
        self['plotfullback'] = Pixmap()
        self['plotfullback'].hide()
        self['poster0'] = Pixmap()
        self['poster1'] = Pixmap()
        self['poster2'] = Pixmap()
        self['poster3'] = Pixmap()
        self['poster4'] = Pixmap()
        self['poster5'] = Pixmap()
        self['poster6'] = Pixmap()
        self['poster7'] = Pixmap()
        self['poster8'] = Pixmap()
        self['poster9'] = Pixmap()
        self['poster10'] = Pixmap()
        self['poster_back0'] = Pixmap()
        self['poster_back1'] = Pixmap()
        self['poster_back2'] = Pixmap()
        self['poster_back3'] = Pixmap()
        self['poster_back4'] = Pixmap()
        self['poster_back7'] = Pixmap()
        self['poster_back8'] = Pixmap()
        self['poster_back9'] = Pixmap()
        self['poster_back10'] = Pixmap()
        if self.xd == True:
            self.index = index
            self.posterindex = 5
            self.posterALL = 11
            self['poster_back6'] = Pixmap()
        else:
            self.index = index
            self.posterindex = 6
            self.posterALL = 13
            self['poster11'] = Pixmap()
            self['poster12'] = Pixmap()
            self['poster_back5'] = Pixmap()
            self['poster_back11'] = Pixmap()
            self['poster_back12'] = Pixmap()
        self['eposter'] = Pixmap()
        self['eposter'].hide()
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
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.deleteMovie,
         'yellow': self.renewIMDb,
         'green': self.renewTMDb,
         #'blue': self.hideScreen,
         'contextMenu': self.config,
         'showEventInfo': self.togglePlotFull,
         'startTeletext': self.editDatabase,
         'leavePlayer': self.toggleBackdrops,
         'movieList': self.updateDatabase,
         '1': self.showMovies,
         '2': self.switchView,
         '3': self.showPath,
         '4': self.filterSeasons,
         '5': self.toogleContent,
         #'6': self.wikipedia,
         '7': self.filterDirector,
         '8': self.filterActor,
         '9': self.filterGenre,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
	cmd = "mkdir /usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/;mkdir /usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/cache"
	os.system(cmd) 
        self.updatefile = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/update'
        self.blacklist = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/blacklist'
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/database'
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        if config.plugins.moviebrowser.showtv.value == 'hide':
            self.session.nav.stopService()
        if config.plugins.moviebrowser.m1v.value == 'yes':
            self.session.nav.stopService()
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.plugins.moviebrowser.transparency.value)
            f.close()
        if self.xd == False:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_backHD.png'
            InfoBack = loadPic(self.infoBackPNG, 525, 430, 3, 0, 0, 1)
        else:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_back.png'
            InfoBack = loadPic(self.infoBackPNG, 460, 400, 3, 0, 0, 1)
        if InfoBack != None:
            self['infoback'].instance.setPixmap(InfoBack)
            self['infoback'].show()
        if fileExists(self.database):
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.reset = False
            self.makeMovieBrowserTimer = eTimer()
            self.makeMovieBrowserTimer.callback.append(self.makeMovies(self.filter))
            self.makeMovieBrowserTimer.start(500, True)
        else:
            self.openTimer = eTimer()
            self.openTimer.callback.append(self.openInfo)
            self.openTimer.start(500, True)

    def openInfo(self):
        if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset'):
            self.session.openWithCallback(self.reset_return, MessageBox, _('\nThe Movie Browser Database will be built now. This can take several minutes, depending on how many movies you have.\n\nBuild Movie Browser Database now?'), MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.first_return, MessageBox, _('\nBefore the Movie Browser Database is built for the first time, you should check your Movie Folder settings and change the Cache Folder to a hard drive disk for faster access or to a USB stick.'), MessageBox.TYPE_YESNO)

    def first_return(self, answer):
        if answer is True:
            open('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset', 'w').close()
            self.session.openWithCallback(self.exit, movieBrowserConfig)
        else:
            self.close()

    def reset_return(self, answer):
        if answer is True:
            self.reset = True
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset'):
                os.remove('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset')
            self.resetTimer = eTimer()
            self.resetTimer.callback.append(self.database_return(True))
            self.resetTimer.start(500, True)
        else:
            self.close()

    def makeMovies(self, filter):
        self.namelist = []
        self.movielist = []
        self.datelist = []
        self.infolist = []
        self.plotlist = []
        self.posterlist = []
        self.backdroplist = []
        self.contentlist = []
        self.filter = filter
        if fileExists(self.database):
            f = open(self.database, 'r')
            for line in f:
                if self.content in line and filter in line:
                    movieline = line.split(':::')
                    try:
                        name = movieline[0]
                    except IndexError:
                        name = ' '

                    try:
                        filename = movieline[1]
                    except IndexError:
                        filename = ' '

                    try:
                        date = movieline[2]
                    except IndexError:
                        date = ' '

                    try:
                        runtime = movieline[3]
                    except IndexError:
                        runtime = ' '

                    try:
                        rating = movieline[4]
                    except IndexError:
                        rating = ' '

                    try:
                        director = movieline[5]
                    except IndexError:
                        director = ' '

                    try:
                        actors = movieline[6]
                    except IndexError:
                        actors = ' '

                    try:
                        genres = movieline[7]
                    except IndexError:
                        genres = ' '

                    try:
                        year = movieline[8]
                    except IndexError:
                        year = ' '

                    try:
                        country = movieline[9]
                    except IndexError:
                        country = ' '

                    try:
                        plotfull = movieline[10]
                    except IndexError:
                        plotfull = ' '

                    try:
                        poster = movieline[11]
                    except IndexError:
                        poster = 'http://cf2.imgobject.com/t/p/w154' + '/default_poster.png'

                    try:
                        backdrop = movieline[12]
                    except IndexError:
                        backdrop = 'http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png'

                    try:
                        content = movieline[13]
                    except IndexError:
                        content = 'Series'

                    self.namelist.append(name)
                    self.movielist.append(filename)
                    self.datelist.append(date)
                    res = []
                    res.append(runtime)
                    res.append(rating)
                    res.append(director)
                    res.append(actors)
                    res.append(genres)
                    res.append(year)
                    res.append(country)
                    self.infolist.append(res)
                    self.plotlist.append(plotfull)
                    self.posterlist.append(poster)
                    self.backdroplist.append(backdrop)
                    self.contentlist.append(content)

            f.close()
            self.maxentry = len(self.namelist)
            if self.maxentry == 0:
                self.ready = True
                size = os.path.getsize(self.database)
                if size < 10:
                    os.remove(self.database)
            else:
                self.makePoster()
                if self.backdrops == True:
                    try:
                        self.showBackdrops(self.index)
                    except IndexError:
                        pass

                else:
                    self.hideBackdrops()
                try:
                    self.makeName(self.index)
                except IndexError:
                    pass

                try:
                    self.makeInfo(self.index)
                except IndexError:
                    pass

                if self.plotfull == True:
                    try:
                        self.showPlotFull(self.index)
                    except IndexError:
                        pass

                self.ready = True

    def updateDatabase(self):
        if self.ready == True:
            if os.path.exists(config.plugins.moviebrowser.moviefolder.value):
                self.session.openWithCallback(self.database_return, MessageBox, _('\nUpdate Movie Browser Database?'), MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, _('\nMovie Folder %s not reachable.\nMovie Browser Database Update canceled.') % str(config.plugins.moviebrowser.moviefolder.value), MessageBox.TYPE_ERROR)

    def database_return(self, answer):
        if answer is True:
            open(self.updatefile, 'w').close()
            self.update = True
            self.ready = False
            self.namelist = []
            self.movielist = []
            self.datelist = []
            self.infolist = []
            self.plotlist = []
            self.posterlist = []
            self.backdroplist = []
            self.orphaned = 0
            if fileExists(self.database):
                allfiles = ':::'
                folder = config.plugins.moviebrowser.moviefolder.value
                for root, dirs, files in os.walk(folder, topdown=False):
                    for name in files:
                        filename = os.path.join(root, name)
                        filedate = os.path.getctime(filename)
                        allfiles = allfiles + str(filedate)

                data = open(self.database).read()
                for line in data.split('\n'):
                    movieline = line.split(':::')
                    try:
                        moviefolder = movieline[1]
                        moviedate = movieline[2]
                    except IndexError:
                        moviefolder = ''
                        moviedate = ''

                    if search(config.plugins.moviebrowser.moviefolder.value, moviefolder) is not None and search(moviedate, allfiles) is None:
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
            if fileExists(self.blacklist):
                blacklist = open(self.blacklist).read()
                alldata = data + blacklist
            else:
                alldata = data
            folder = config.plugins.moviebrowser.moviefolder.value
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    movie = sub('\\(', '.', name)
                    movie = sub('\\)', '.', movie)
                    if search(movie, alldata) is None:
                        if name.endswith('.ts') or name.endswith('.avi') or name.endswith('.divx') or name.endswith('.flv') or name.endswith('.iso') or name.endswith('.ISO') or name.endswith('.m2ts') or name.endswith('.mov') or name.endswith('.mp4') or name.endswith('.mpg') or name.endswith('.mpeg') or name.endswith('.mkv') or name.endswith('.vob'):
                            filename = os.path.join(root, name)
                            self.movielist.append(filename)
                            self.datelist.append(os.path.getctime(filename))
                            if name.endswith('.ts'):
                                name = sub('.*? - .*? - ', '', name)
                                name = sub('[.]ts', '', name)
                            else:
                                name = sub('[.]avi', '', name)
                                name = sub('[.]divx', '', name)
                                name = sub('[.]flv', '', name)
                                name = sub('[.]iso', '', name)
                                name = sub('[.]ISO', '', name)
                                name = sub('[.]m2ts', '', name)
                                name = sub('[.]mov', '', name)
                                name = sub('[.]mp4', '', name)
                                name = sub('[.]mpg', '', name)
                                name = sub('[.]mpeg', '', name)
                                name = sub('[.]mkv', '', name)
                                name = sub('[.]vob', '', name)
                            print name
                            self.namelist.append(name)

            self.dbcount = 1
            self.dbcountmax = len(self.movielist)
            if self.dbcountmax == 0:
                self.finished_update(False)
            else:
                self.name = self.namelist[0]
                if config.plugins.moviebrowser.database.value == 'tmdb':
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                    self.firstdatabase = 'tmdb'
                    url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
                    self.getTMDbData(url, 1, '0', False)
                elif config.plugins.moviebrowser.database.value == 'imdb':
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                    self.firstdatabase = 'imdb'
                    url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
                    self.getIMDbData(url, 1)
                else:
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                    self.firstdatabase = 'tvdb'
                    movie = movie + 'FIN'
                    movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
                    movie = sub('FIN', '', movie)
                    url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
                    self.getTVDbData(url, 1, '0')

    def getIMDbData(self, url, runlevel):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            output = output.replace('\\u00e4', '\xc3\xa4').replace('\\u00f6', '\xc3\xb6').replace('\\u00fc', '\xc3\xbc').replace('\\u00c4', '\xc3\x84').replace('\\u00f6', '\xc3\x9f').replace('\\u00dc', '\xc3\x9c').replace('\\u00df', '\xc3\x9f').replace('\\u0026', '&').replace('\\u00e9', '\xc3\xa9').replace('\\u00e5', '\xc3\xa5').replace('\\"', '').replace('&amp;', '&')
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"error":"Film not found"', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'imdb'
            self.translateGoogle(text)
        elif search('"error":"Film not found"', output) is not None and runlevel == 2:
            movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            movie = movie + 'FIN'
            movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
            movie = sub('FIN', '', movie)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 1, '0')
        else:
            name = re.findall('<title>(.*?)</title>', output)
            runtime = re.findall('<runtime><item>.*?([0-9]+ min).*?</item>', output)
            rating = re.findall('<rating>(.*?)</rating>', output)
            director = re.findall('<directors><item>(.*?)</item>', output)
            actors = re.findall('<actors>(.*?)</actors>', output)
            try:
                actor = re.findall('<item>(.*?)</item>', actors[0])
            except IndexError:
                actor = []

            genres = re.findall('<genres>(.*?)</genres>', output)
            try:
                genre = re.findall('<item>(.*?)</item>', genres[0])
            except IndexError:
                genre = []

            year = re.findall('<year>(.*?)</year>', output)
            country = re.findall('<country><item>(.*?)</item>', output)
            plotfull = re.findall('<plot>(.*?)</plot>', output)
            try:
                self.namelist[self.dbcount - 1] = name[0]
            except IndexError:
                self.namelist[self.dbcount - 1] = self.name

            res = []
            try:
                res.append(runtime[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                res.append(director[0])
            except IndexError:
                res.append(' ')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor[1]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[2]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[3]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[4]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[5]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor[6]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre[1]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[2]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[3]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[4]
            except IndexError:
                pass

            try:
                res.append(genres)
            except IndexError:
                res.append(' ')

            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(country[0].replace('Germany', 'GER'))
            except IndexError:
                res.append(' ')

            self.infolist.append(res)
            try:
                self.plotlist.append(plotfull[0].replace('\\', ''))
            except IndexError:
                self.plotlist.append(' ')

            movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbPoster(url, 1)

    def getTMDbPoster(self, url, runlevel):
        self.tmdbposter = True
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"total_results":0', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'tmdbposter'
            self.translateGoogle(text)
        else:
            backdrop = re.findall('"backdrop_path":"(.*?)"', output)
            poster = re.findall('"poster_path":"(.*?)"', output)
            try:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
            except IndexError:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

            try:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
            except IndexError:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            self.tmdbposter = False
            self.makeDataEntry(self.dbcount - 1, True)

    def getTMDbData(self, url, runlevel, tmdbid, renew):
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"total_results":0', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'tmdb'
            self.translateGoogle(text)
        elif search('"total_results":0', output) is not None and runlevel == 2:
            movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            movie = movie + 'FIN'
            movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
            movie = sub('FIN', '', movie)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 1, '0')
        else:
            if tmdbid == '0':
                tmdbid = re.findall('"id":(.*?),', output)
                try:
                    tmdbid = tmdbid[0]
                except IndexError:
                    tmdbid = '0'

                name = re.findall('"title":"(.*?)"', output)
                backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                year = re.findall('"release_date":"(.*?)-', output)
                poster = re.findall('"poster_path":"(.*?)"', output)
                rating = re.findall('"vote_average":(.*?),', output)
                try:
                    self.namelist[self.dbcount - 1] = name[0]
                except IndexError:
                    self.namelist[self.dbcount - 1] = self.name

                try:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
                except IndexError:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

                try:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
                except IndexError:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

                url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid + self.language
                headers = {'Accept': 'application/json'}
                request = Request(url, headers=headers)
                try:
                    output = urlopen(request).read()
                except URLError:
                    output = ''
                except HTTPError:
                    output = ''
                except socket.error:
                    output = ''

            plot = re.findall('"overview":"(.*?)","', output)
            if renew == True:
                output = sub('"belongs_to_collection":{.*?}', '', output)
                name = re.findall('"title":"(.*?)"', output)
                backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                poster = re.findall('"poster_path":"(.*?)"', output)
            url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid
            headers = {'Accept': 'application/json'}
            request = Request(url, headers=headers)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('"belongs_to_collection":{.*?}', '', output)
            if not plot:
                plot = re.findall('"overview":"(.*?)","', output)
            genre = re.findall('"genres":[[]."id":[0-9]+,"name":"(.*?)"', output)
            genre2 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre3 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre4 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre5 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            country = re.findall('"iso_3166_1":"(.*?)"', output)
            runtime = re.findall('"runtime":(.*?),', output)
            if renew == True:
                year = re.findall('"release_date":"(.*?)-', output)
                rating = re.findall('"vote_average":(.*?),', output)
                if not backdrop:
                    backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                if not poster:
                    poster = re.findall('"poster_path":"(.*?)"', output)
                try:
                    self.namelist[self.dbcount - 1] = name[0]
                except IndexError:
                    self.namelist[self.dbcount - 1] = self.name

                try:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
                except IndexError:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

                try:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
                except IndexError:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            url = 'http://api.themoviedb.org/3/movie/%s/casts?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid + self.language
            headers = {'Accept': 'application/json'}
            request = Request(url, headers=headers)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            actor = re.findall('"name":"(.*?)"', output)
            actor2 = re.findall('"name":".*?"name":"(.*?)"', output)
            actor3 = re.findall('"name":".*?"name":".*?"name":"(.*?)"', output)
            actor4 = re.findall('"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor5 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor6 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor7 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            director = re.findall('"([^"]+)","department":"Directing","job":"Director"', output)
            res = []
            try:
                res.append(runtime[0] + ' min')
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                res.append(director[0])
            except IndexError:
                res.append(' ')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor2[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor3[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor4[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor5[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor6[0]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor7[0]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre2[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre3[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre4[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre5[0]
            except IndexError:
                pass

            res.append(genres.replace('Science Fiction', 'Sci-Fi'))
            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(country[0].replace('US', 'USA'))
            except IndexError:
                res.append(' ')

            self.infolist.append(res)
            try:
                self.plotlist.append(plot[0].replace('\\', ''))
            except IndexError:
                self.plotlist.append(' ')

            self.makeDataEntry(self.dbcount - 1, True)

    def translateGoogle(self, text):
        if config.plugins.moviebrowser.language.value == 'de':
            url = 'http://translate.google.com/m?hl=en&sl=de&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'es':
            url = 'http://translate.google.com/m?hl=en&sl=es&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'ru':
            url = 'http://translate.google.com/m?hl=en&sl=ru&q=%s' % text.title()
        else:
            url = 'http://translate.google.com/m?hl=en&sl=en&q=%s' % text.title()
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        before_trans = 'class="t0">'
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            data = output[output.find(before_trans) + len(before_trans):]
            movie = data.split('<')[0]
            print '%s >> %s' % (text, movie)
        except URLError:
            movie = text
        except HTTPError:
            movie = text
        except socket.error:
            movie = text

        if self.trans == 'imdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
            self.getIMDbData(url, 2)
        elif self.trans == 'tmdbposter':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbPoster(url, 2)
        elif self.trans == 'tmdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbData(url, 2, '0', False)
        elif self.trans == 'tvdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 2, '0')

    def getTVDbData(self, url, runlevel, seriesid):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('<Series>', output) is None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            text = text + 'FIN'
            text = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', text)
            text = sub('FIN', '', text)
            self.trans = 'tvdb'
            self.translateGoogle(text)
        elif search('<Series>', output) is None and runlevel == 2:
            self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')
            self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')
            self.namelist[self.dbcount - 1] = self.name
            res = []
            res.append(' ')
            res.append('0.0')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            self.infolist.append(res)
            self.plotlist.append(' ')
            self.makeDataEntry(self.dbcount - 1, False)
        else:
            if seriesid == '0':
                seriesid = re.findall('<seriesid>(.*?)</seriesid>', output)
                try:
                    seriesid = seriesid[0]
                except IndexError:
                    seriesid = '0'

            if search('[Ss][0-9]+[Ee][0-9]+', self.name) is not None:
                data = search('([Ss][0-9]+[Ee][0-9]+)', self.name)
                data = data.group(1)
                season = search('[Ss]([0-9]+)[Ee]', data)
                season = season.group(1).lstrip('0')
                episode = search('[Ss][0-9]+[Ee]([0-9]+)', data)
                episode = episode.group(1).lstrip('0')
                url = 'http://www.thetvdb.com/api/D19315B88B2DE21F/series/' + seriesid + '/default/' + season + '/' + episode + '/' + config.plugins.moviebrowser.language.value + '.xml'
                agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
                request = Request(url, headers=agents)
                try:
                    output = urlopen(request).read()
                except URLError:
                    output = ''
                except HTTPError:
                    output = ''
                except socket.error:
                    output = ''

                output = sub('&amp;', '&', output)
                episode = re.findall('<EpisodeName>(.*?)</EpisodeName>', output)
                year = re.findall('<FirstAired>([0-9]+)-', output)
                guest = re.findall('<GuestStars>[|](.*?)[|]</GuestStars>', output)
                director = re.findall('<Director>[|](.*?)[|]', output)
                if not director:
                    director = re.findall('<Director>(.*?)</Director>', output)
                plotfull = re.findall('<Overview>(.*?)</Overview>', output, re.S)
                rating = re.findall('<Rating>(.*?)</Rating>', output)
                eposter = re.findall('<filename>(.*?)</filename>', output)
            else:
                data = ''
                episode = []
                year = []
                guest = []
                director = []
                plotfull = []
                rating = []
                eposter = []
            url = 'http://www.thetvdb.com/data/series/' + seriesid + '/' + config.plugins.moviebrowser.language.value + '.xml'
            agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
            request = Request(url, headers=agents)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('&amp;', '&', output)
            name = re.findall('<SeriesName>(.*?)</SeriesName>', output)
            runtime = re.findall('<Runtime>(.*?)</Runtime>', output)
            if not rating:
                rating = re.findall('<Rating>(.*?)</Rating>', output)
            actors = re.findall('<Actors>(.*?)</Actors>', output)
            try:
                actor = re.findall('[|](.*?)[|]', actors[0])
            except IndexError:
                actor = []

            try:
                actor2 = re.findall('[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor2 = []

            try:
                actor3 = re.findall('[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor3 = []

            try:
                actor4 = re.findall('[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor4 = []

            try:
                actor5 = re.findall('[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor5 = []

            try:
                actor6 = re.findall('[|].*?[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor6 = []

            try:
                actor7 = re.findall('[|].*?[|].*?[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor7 = []

            genres = re.findall('<Genre>(.*?)</Genre>', output)
            try:
                genre = re.findall('[|](.*?)[|]', genres[0])
            except IndexError:
                genre = []

            try:
                genre2 = re.findall('[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre2 = []

            try:
                genre3 = re.findall('[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre3 = []

            try:
                genre4 = re.findall('[|].*?[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre4 = []

            try:
                genre5 = re.findall('[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre5 = []

            if not year:
                year = re.findall('<FirstAired>([0-9]+)-', output)
            if not plotfull:
                plotfull = re.findall('<Overview>(.*?)</Overview>', output, re.S)
            backdrop = re.findall('<fanart>(.*?)</fanart>', output)
            poster = re.findall('<poster>(.*?)</poster>', output)
            try:
                if not episode:
                    self.namelist[self.dbcount - 1] = name[0].replace('Das n\xc3\xa4chste Jahrhundert', 'TNG')
                else:
                    self.namelist[self.dbcount - 1] = name[0].replace('Das n\xc3\xa4chste Jahrhundert', 'TNG') + ' - (' + data + ') ' + episode[0]
            except IndexError:
                self.namelist[self.dbcount - 1] = self.name

            res = []
            try:
                res.append(runtime[0] + ' min')
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                if not director:
                    res.append('Various')
                else:
                    res.append(director[0])
            except IndexError:
                res.append('Various')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor2[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor3[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor4[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor5[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor6[0]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor7[0]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre2[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre3[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre4[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre5[0]
            except IndexError:
                pass

            try:
                res.append(genres.replace('Science-Fiction', 'Sci-Fi'))
            except IndexError:
                res.append(' ')

            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            if config.plugins.moviebrowser.language.value == 'de':
                country = 'DE'
            elif config.plugins.moviebrowser.language.value == 'es':
                country = 'ES'
            else:
                country = 'USA'
            res.append(country)
            self.infolist.append(res)
            try:
                if not guest:
                    plotfull = plotfull[0].replace('\n', '').replace('&quot;', '"')
                else:
                    plotfull = plotfull[0].replace('\n', '').replace('&quot;', '"')
                    plotfull = plotfull + ' Guest Stars: ' + guest[0].replace('|', ', ') + '.'
                self.plotlist.append(plotfull)
            except IndexError:
                self.plotlist.append(' ')

            try:
                self.backdroplist.append('http://www.thetvdb.com/banners/' + backdrop[0])
            except IndexError:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

            try:
                if not eposter:
                    self.posterlist.append('http://www.thetvdb.com/banners/_cache/' + poster[0])
                else:
                    self.posterlist.append('http://www.thetvdb.com/banners/_cache/' + poster[0] + '<episode>' + 'http://www.thetvdb.com/banners/' + eposter[0] + '<episode>')
            except IndexError:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            self.makeDataEntry(self.dbcount - 1, False)

    def makeDataEntry(self, count, content):
        if self.renew == False:
            f = open(self.database, 'a')
            try:
                if content == True:
                    data = self.namelist[count] + ':::' + self.movielist[count] + ':::' + str(self.datelist[count]) + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Movie:::\n'
                else:
                    data = self.namelist[count] + ':::' + self.movielist[count] + ':::' + str(self.datelist[count]) + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Series:::\n'
                f.write(data)
            except IndexError:
                pass

            f.close()
        else:
            try:
                if content == True:
                    newdata = self.namelist[count] + ':::' + self.movielist[self.index] + ':::' + self.datelist[self.index] + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Movie:::'
                else:
                    newdata = self.namelist[count] + ':::' + self.movielist[self.index] + ':::' + self.datelist[self.index] + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Series:::'
            except IndexError:
                newdata = ''

            data = open(self.database).read()
            movie = self.movielist[self.index]
            movie = sub('\\(', '.', movie)
            movie = sub('\\)', '.', movie)
            if search(movie, data) is not None:
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        data = data.replace(line, newdata)

                f = open(self.database, 'w')
                f.write(data)
                f.close()
        if self.dbcount < self.dbcountmax:
            self.dbcount += 1
            self.name = self.namelist[self.dbcount - 1]
            if self.firstdatabase == 'tmdb':
                movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
                self.getTMDbData(url, 1, '0', False)
            elif self.firstdatabase == 'imdb':
                movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
                self.getIMDbData(url, 1)
            else:
                movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                movie = movie + 'FIN'
                movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
                movie = sub('FIN', '', movie)
                url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
                self.getTVDbData(url, 1, '0')
        elif self.update == True:
            if self.reset == True:
                self.session.openWithCallback(self.exit, movieBrowserBackdrop, self.index, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)
            else:
                self.finished_update(True)
        else:
            self.finished()

    def finished(self):
        if self.renew == False:
            self.index = 0
            if self.xd == True:
                self.posterindex = 5
            else:
                self.posterindex = 6
            self.makeMovies(self.filter)
        else:
            self.renew = False
            self.makeMovies(self.filter)

    def finished_update(self, found):
        if found == False and self.orphaned == 0:
            self.session.open(MessageBox, _('\nNo new Movies found:\nYour Database is up to date.'), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMovies(self.filter)
        elif found == False:
            if self.orphaned == 1:
                self.session.open(MessageBox, _('\nNo new Movies found.\n%s Orphaned Movie deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\nNo new Movies found.\n%s Orphaned Movies deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMovies(self.filter)
        elif self.orphaned == 0:
            if self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMovies(self.filter)
        else:
            if self.dbcountmax == 1 and self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.\n%s Orphaned Movie deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.\n%s Orphaned Movies deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.\n%s Orphaned Movie deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.\n%s Orphaned Movies deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMovies(self.filter)

    def ok(self):
        if self.ready == True:
            try:
                filename = self.movielist[self.index]
                if filename.endswith('.ts'):
                    sref = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + filename)
                    sref.setName(self.namelist[self.index])
                    self.session.open(MoviePlayer, sref)
                elif filename.endswith('.iso') or filename.endswith('.ISO'):
                    if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/DVDPlayer/'):
                        from Plugins.Extensions.DVDPlayer.plugin import DVDPlayer
                        self.session.open(DVDPlayer, dvd_filelist=[filename])
                    else:
                        self.session.open(MessageBox, _('DVD Player Plugin not installed.'), MessageBox.TYPE_ERROR)
                else:
                    sref = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + filename)
                    sref.setName(self.namelist[self.index])
                    self.session.open(MoviePlayer, sref)
            except IndexError:
                pass

    def renewIMDb(self):
        if self.ready == True:
            name = self.movielist[self.index]
            name = sub('.*?[/]', '', name)
            if name.endswith('.ts'):
                name = sub('.*? - .*? - ', '', name)
                name = sub('[.]ts', '', name)
            else:
                name = sub('[.]avi', '', name)
                name = sub('[.]divx', '', name)
                name = sub('[.]flv', '', name)
                name = sub('[.]iso', '', name)
                name = sub('[.]ISO', '', name)
                name = sub('[.]m2ts', '', name)
                name = sub('[.]mov', '', name)
                name = sub('[.]mp4', '', name)
                name = sub('[.]mpg', '', name)
                name = sub('[.]mpeg', '', name)
                name = sub('[.]mkv', '', name)
                name = sub('[.]vob', '', name)
            self.session.openWithCallback(self.renewIMDbReturn, VirtualKeyBoard, title='Update Single Movie Data - IMDb:', text=name)

    def renewIMDbReturn(self, name):
        if name and name != '':
            self.name = name
            name = name.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=10&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % name
            self.getIMDbMovies(url, 1)

    def getIMDbMovies(self, url, runlevel):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        output = sub('</type><imdb_id>', '</type><poster>http://profile.ak.fbcdn.net/hprofile-ak-snc7/373026_15925638948_1021284996_q.jpg</poster><imdb_id>', output)
        rating = re.findall('<rating>(.*?)</rating>', output)
        year = re.findall('<year>(.*?)</year>', output)
        titles = re.findall('<title>(.*?)</title>', output)
        poster = re.findall('<poster>(.*?)</poster>', output)
        id = re.findall('<imdb_id>(.*?)</imdb_id>', output)
        country = re.findall('<country><item>(.*?)</item>', output)
        titel = 'IMDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.transrenew = 'imdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.openWithCallback(self.tvdb_return, MessageBox, _('\nNo IMDb Results - looking for %s on TheTVDb?') % self.name, MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.makeIMDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def makeIMDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'imdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://imdbapi.org/?ids=%s&type=xml&plot=full&episode=0&lang=en-US&aka=simple&release=simple&business=0&tech=0' % id
        self.getIMDbData(url, 1)

    def renewTMDb(self):
        if self.ready == True:
            name = self.movielist[self.index]
            name = sub('.*?[/]', '', name)
            if name.endswith('.ts'):
                name = sub('.*? - .*? - ', '', name)
                name = sub('[.]ts', '', name)
            else:
                name = sub('[.]avi', '', name)
                name = sub('[.]divx', '', name)
                name = sub('[.]flv', '', name)
                name = sub('[.]iso', '', name)
                name = sub('[.]ISO', '', name)
                name = sub('[.]m2ts', '', name)
                name = sub('[.]mov', '', name)
                name = sub('[.]mp4', '', name)
                name = sub('[.]mpg', '', name)
                name = sub('[.]mpeg', '', name)
                name = sub('[.]mkv', '', name)
                name = sub('[.]vob', '', name)
            if config.plugins.moviebrowser.database.value == 'tvdb':
                self.session.openWithCallback(self.renewTMDbReturn, VirtualKeyBoard, title='Update Single Series Data - TheTVDb:', text=name)
            else:
                self.session.openWithCallback(self.renewTMDbReturn, VirtualKeyBoard, title='Update Single Movie Data - TMDb:', text=name)

    def renewTMDbReturn(self, name):
        if name and name != '':
            self.name = name
            if config.plugins.moviebrowser.database.value == 'tmdb':
                name = name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + name + self.language
                self.getTMDbMovies(url, 1)
            else:
                name = name.replace(' ', '+').replace(':', '+').replace('_', '+')
                name = name + 'FIN'
                name = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', name)
                name = sub('FIN', '', name)
                url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + name
                self.getTVDbMovies(url, 1)

    def getTMDbMovies(self, url, runlevel):
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        output = sub('"poster_path":"', '"poster_path":"http://cf2.imgobject.com/t/p/w154', output)
        output = sub('"poster_path":null', '"poster_path":"http://www.themoviedb.org/images/apps/moviebase.png"', output)
        rating = re.findall('"vote_average":(.*?),', output)
        year = re.findall('"release_date":"(.*?)-', output)
        titles = re.findall('"title":"(.*?)"', output)
        poster = re.findall('"poster_path":"(.*?)"', output)
        id = re.findall('"id":(.*?),', output)
        country = re.findall('"backdrop(.*?)_path"', output)
        titel = 'TMDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.transrenew = 'tmdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.openWithCallback(self.tvdb_return, MessageBox, _('\nNo TMDb Results - looking for %s on TheTVDb?') % self.name, MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.makeTMDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def tvdb_return(self, answer):
        if answer is True:
            name = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            name = name + 'FIN'
            name = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', name)
            name = sub('FIN', '', name)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + name
            self.getTVDbMovies(url, 1)

    def getTVDbMovies(self, url, runlevel):
        rating = []
        year = []
        titles = []
        poster = []
        id = []
        country = []
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        seriesid = re.findall('<seriesid>(.*?)</seriesid>', output)
        for x in range(len(seriesid)):
            url = 'http://www.thetvdb.com/data/series/' + seriesid[x] + '/' + config.plugins.moviebrowser.language.value + '.xml'
            agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
            request = Request(url, headers=agents)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('<poster>', '<poster>http://www.thetvdb.com/banners/_cache/', output)
            output = sub('<poster>http://www.thetvdb.com/banners/_cache/</poster>', '<poster>http://www.thetvdb.com/wiki/skins/common/images/wiki.png</poster>', output)
            output = sub('<Rating></Rating>', '<Rating>0.0</Rating>', output)
            output = sub('&amp;', '&', output)
            Rating = re.findall('<Rating>(.*?)</Rating>', output)
            Year = re.findall('<FirstAired>([0-9]+)-', output)
            Added = re.findall('<added>([0-9]+)-', output)
            Titles = re.findall('<SeriesName>(.*?)</SeriesName>', output)
            Poster = re.findall('<poster>(.*?)</poster>', output)
            TVDbid = re.findall('<id>(.*?)</id>', output)
            Country = re.findall('<Status>(.*?)</Status>', output)
            try:
                rating.append(Rating[0])
            except IndexError:
                rating('0.0')

            try:
                year.append(Year[0])
            except IndexError:
                try:
                    year.append(Added[0])
                except IndexError:
                    year.append(' ')

            try:
                titles.append(Titles[0])
            except IndexError:
                titles.append(' ')

            try:
                poster.append(Poster[0])
            except IndexError:
                poster.append('http://www.thetvdb.com/wiki/skins/common/images/wiki.png')

            try:
                id.append(TVDbid[0])
            except IndexError:
                id.append('0')

            try:
                country.append(Country[0])
            except IndexError:
                country.append(' ')

        titel = 'TheTVDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            text = text + 'FIN'
            text = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', text)
            text = sub('FIN', '', text)
            self.transrenew = 'tvdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.open(MessageBox, _('\nNo TheTVDb Results for %s.') % self.name, MessageBox.TYPE_INFO)
        else:
            self.session.openWithCallback(self.makeTVDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def makeTMDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'tmdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % id + self.language
        self.getTMDbData(url, 1, id, True)

    def makeTVDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'tvdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://www.thetvdb.com/data/series/' + id + '/' + config.plugins.moviebrowser.language.value + '.xml'
        self.getTVDbData(url, 1, id)

    def translateRenewGoogle(self, text):
        if config.plugins.moviebrowser.language.value == 'de':
            url = 'http://translate.google.com/m?hl=en&sl=de&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'es':
            url = 'http://translate.google.com/m?hl=en&sl=es&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'ru':
            url = 'http://translate.google.com/m?hl=en&sl=ru&q=%s' % text.title()
        else:
            url = 'http://translate.google.com/m?hl=en&sl=en&q=%s' % text.title()
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        before_trans = 'class="t0">'
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            data = output[output.find(before_trans) + len(before_trans):]
            movie = data.split('<')[0]
            print '%s >> %s' % (text, movie)
        except URLError:
            movie = text
        except HTTPError:
            movie = text
        except socket.error:
            movie = text

        if self.transrenew == 'imdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=10&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
            self.getIMDbMovies(url, 2)
        elif self.transrenew == 'tmdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbMovies(url, 2)
        elif self.transrenew == 'tvdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbMovies(url, 2)

    def deleteMovie(self):
        if self.ready == True:
            try:
                name = self.namelist[self.index]
                self.session.openWithCallback(self.delete_return, MessageBox, _('\nDo you really want to delete %s?') % name, MessageBox.TYPE_YESNO)
            except IndexError:
                pass

    def delete_return(self, answer):
        if answer is True:
            try:
                movie = self.movielist[self.index]
                if fileExists(movie):
                    os.remove(movie)
                if search('[.]ts', movie) is not None:
                    eitfile = sub('[.]ts', '.eit', movie)
                    if fileExists(eitfile):
                        os.remove(eitfile)
                    if fileExists(movie + '.ap'):
                        os.remove(movie + '.ap')
                    if fileExists(movie + '.cuts'):
                        os.remove(movie + '.cuts')
                    if fileExists(movie + '.meta'):
                        os.remove(movie + '.meta')
                    if fileExists(movie + '.sc'):
                        os.remove(movie + '.sc')
                    if fileExists(movie + '_mp.jpg'):
                        os.remove(movie + '_mp.jpg')
                movie = sub('\\(', '.', movie)
                movie = sub('\\)', '.', movie)
                data = open(self.database).read()
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        data = data.replace(line + '\n', '')

                f = open(self.database, 'w')
                f.write(data)
                f.close()
                if self.index == self.maxentry - 1:
                    self.index -= 1
                self.makeMovies(self.filter)
            except IndexError:
                pass

        else:
            self.blacklistMovie()

    def blacklistMovie(self):
        if self.ready == True:
            try:
                name = self.namelist[self.index]
                self.session.openWithCallback(self.blacklist_return, MessageBox, _('\nDo you really want to blacklist %s?') % name, MessageBox.TYPE_YESNO)
            except IndexError:
                pass

    def blacklist_return(self, answer):
        if answer is True:
            self.ready = False
            try:
                movie = self.movielist[self.index]
                movie = sub('\\(', '.', movie)
                movie = sub('\\)', '.', movie)
                if fileExists(self.blacklist):
                    fremove = open(self.blacklist, 'a')
                else:
                    open(self.blacklist, 'w').close()
                    fremove = open(self.blacklist, 'a')
                data = open(self.database).read()
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        fremove.write(line + '\n')
                        fremove.close()
                        data = data.replace(line + '\n', '')

                f = open(self.database, 'w')
                f.write(data)
                f.close()
                if self.index == self.maxentry - 1:
                    self.index -= 1
                self.makeMovies(self.filter)
            except IndexError:
                pass

    def togglePlotFull(self):
        if self.ready == True:
            if self.plotfull == False:
                self.plotfull = True
                try:
                    self.showPlotFull(self.index)
                except IndexError:
                    pass

            else:
                self.plotfull = False
                self.hidePlotFull()

    def showPlotFull(self, index):
        if self.xd == False:
            PlotFull = loadPic(self.infoBackPNG, 525, 430, 3, 0, 0, 1)
        else:
            PlotFull = loadPic(self.infoBackPNG, 460, 400, 3, 0, 0, 1)
        if PlotFull != None:
            self['plotfullback'].instance.setPixmap(PlotFull)
            self['plotfullback'].show()
        try:
            plot = self.plotlist[self.index]
            self['plotfull'].setText(plot)
            self['plotfull'].show()
            self.makeEPoster()
        except IndexError:
            self['plotfull'].hide()
            self.hideEPoster()

    def hidePlotFull(self):
        self.hideEPoster()
        self['plotfull'].hide()
        self['plotfullback'].hide()

    def toggleBackdrops(self):
        if self.ready == True:
            if self.backdrops == True:
                self.backdrops = False
                self.hideBackdrops()
            else:
                self.backdrops = True
                try:
                    self.showBackdrops(self.index)
                except IndexError:
                    pass

    def hideBackdrops(self):
        backdrop = config.plugins.moviebrowser.cachefolder.value + '/default_backdrop.png'
        if fileExists(backdrop):
            if self.xd == False:
                Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
            else:
                Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
            if Backdrop != None:
                self['backdrop'].instance.setPixmap(Backdrop)
                self['backdrop'].show()

    def showBackdrops(self, index):
        try:
            backdropurl = self.backdroplist[index]
            backdrop = sub('http://cf2.imgobject.com/t/p/w1280', '', backdropurl)
            backdrop = sub('http://www.thetvdb.com/banners/fanart/original', '', backdrop)
            backdrop = config.plugins.moviebrowser.cachefolder.value + backdrop
            if config.plugins.moviebrowser.m1v.value == 'yes':
                backdrop_m1v = backdrop.replace('.jpg', '.m1v')
                if fileExists(backdrop_m1v):
                    self['backdrop'].hide()
                    os.system("/usr/bin/showiframe '%s'" % backdrop_m1v)
                elif fileExists(backdrop):
                    if self.xd == False:
                        Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
                    else:
                        Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
                    if Backdrop != None:
                        self['backdrop'].instance.setPixmap(Backdrop)
                        self['backdrop'].show()
                else:
                    getPage(backdropurl).addCallback(self.getBackdrop, backdrop, index).addErrback(self.downloadError)
            elif fileExists(backdrop):
                if self.xd == False:
                    Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
                else:
                    Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
                if Backdrop != None:
                    self['backdrop'].instance.setPixmap(Backdrop)
                    self['backdrop'].show()
            else:
                getPage(backdropurl).addCallback(self.getBackdrop, backdrop, index).addErrback(self.downloadError)
        except IndexError:
            self['backdrop'].hide()

    def getBackdrop(self, output, backdrop, index):
        f = open(backdrop, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
        else:
            Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
        if Backdrop != None:
            self['backdrop'].instance.setPixmap(Backdrop)
            self['backdrop'].show()

    def makePoster(self):
        for x in range(self.posterALL):
            try:
                index = self.index - self.posterindex + x
                if index >= self.maxentry:
                    index = index - self.maxentry
                elif index < 0:
                    index = self.maxentry + index
                posterurl = self.posterlist[index]
                posterurl = sub('<episode>.*?<episode>', '', posterurl)
                poster = sub('http://cf2.imgobject.com/t/p/w154', '', posterurl)
                poster = sub('http://www.thetvdb.com/banners/_cache/posters', '', poster)
                poster = config.plugins.moviebrowser.cachefolder.value + poster
                if fileExists(poster):
                    if self.xd == False:
                        if x == 6:
                            Poster = loadPic(poster, 150, 225, 3, 0, 0, 1)
                        else:
                            Poster = loadPic(poster, 100, 150, 3, 0, 0, 1)
                    elif x == 5:
                        Poster = loadPic(poster, 138, 207, 3, 0, 0, 1)
                    else:
                        Poster = loadPic(poster, 92, 138, 3, 0, 0, 1)
                    if Poster != None:
                        self['poster' + str(x)].instance.setPixmap(Poster)
                        self['poster' + str(x)].show()
                else:
                    getPage(posterurl).addCallback(self.getPoster, x, poster).addErrback(self.downloadError)
            except IndexError:
                self['poster' + str(x)].hide()

    def getPoster(self, output, x, poster):
        f = open(poster, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            if x == 6:
                Poster = loadPic(poster, 150, 225, 3, 0, 0, 1)
            else:
                Poster = loadPic(poster, 100, 150, 3, 0, 0, 1)
        elif x == 5:
            Poster = loadPic(poster, 138, 207, 3, 0, 0, 1)
        else:
            Poster = loadPic(poster, 92, 138, 3, 0, 0, 1)
        if Poster != None:
            self['poster' + str(x)].instance.setPixmap(Poster)
            self['poster' + str(x)].show()

    def makeEPoster(self):
        try:
            posterurl = self.posterlist[self.index]
            if search('<episode>', posterurl) is not None:
                eposterurl = search('<episode>(.*?)<episode>', posterurl)
                eposterurl = eposterurl.group(1)
                eposter = sub('.*?[/]', '', eposterurl)
                eposter = config.plugins.moviebrowser.cachefolder.value + '/' + eposter
                if fileExists(eposter):
                    if self.xd == False:
                        ePoster = loadPic(eposter, 500, 375, 3, 0, 0, 0)
                    else:
                        ePoster = loadPic(eposter, 440, 330, 3, 0, 0, 0)
                    if ePoster != None:
                        self['name'].hide()
                        self['genres'].hide()
                        self['eposter'].instance.setPixmap(ePoster)
                        self['eposter'].show()
                else:
                    getPage(eposterurl).addCallback(self.getEPoster, eposter).addErrback(self.downloadError)
            else:
                self['eposter'].hide()
        except IndexError:
            pass

    def getEPoster(self, output, eposter):
        f = open(eposter, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            ePoster = loadPic(eposter, 500, 375, 3, 0, 0, 0)
        else:
            ePoster = loadPic(eposter, 440, 330, 3, 0, 0, 0)
        if ePoster != None:
            self['name'].hide()
            self['genres'].hide()
            self['eposter'].instance.setPixmap(ePoster)
            self['eposter'].show()

    def hideEPoster(self):
        self['eposter'].hide()
        self['name'].show()
        self['genres'].show()

    def makeName(self, count):
        try:
            name = self.namelist[count]
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

    def makeInfo(self, count):
        try:
            runtime = self.infolist[count][0]
            self['runtime'].setText(runtime)
            self['runtime'].show()
        except IndexError:
            self['runtime'].hide()

        try:
            ratings = self.infolist[count][1]
            try:
                rating = int(10 * round(float(ratings), 1))
            except ValueError:
                ratings = '0.0'
                rating = int(10 * round(float(ratings), 1))

            self['ratings'].setValue(rating)
            self['ratings'].show()
            self['ratingsback'].show()
            self['ratingtext'].setText(ratings)
        except IndexError:
            self['ratings'].hide()

        try:
            director = self.infolist[count][2]
            self['director'].setText(director)
            self['director'].show()
        except IndexError:
            self['director'].hide()

        try:
            actors = self.infolist[count][3]
            self['actors'].setText(actors)
            self['actors'].show()
        except IndexError:
            self['actors'].hide()

        try:
            genres = self.infolist[count][4]
            self['genres'].setText(genres)
            self['genres'].show()
        except IndexError:
            self['genres'].hide()

        try:
            year = self.infolist[count][5]
            self['year'].setText(year)
            self['year'].show()
        except IndexError:
            self['year'].hide()

        try:
            country = self.infolist[count][6]
            self['country'].setText(country)
            self['country'].show()
        except IndexError:
            self['country'].hide()

    def rightDown(self):
        if self.ready == True:
            self.index += 1
            if self.index == self.maxentry:
                self.index = 0
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def down(self):
        if self.ready == True:
            self.index += self.posterALL
            if self.index >= self.maxentry:
                self.index = self.index - self.maxentry
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def leftUp(self):
        if self.ready == True:
            self.index -= 1
            if self.index < 0:
                self.index = self.maxentry - 1
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def up(self):
        if self.ready == True:
            self.index -= self.posterALL
            if self.index < 0:
                self.index = self.maxentry + self.index
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def gotoEnd(self):
        if self.ready == True:
            self.index = self.maxentry - 1
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def showMovies(self):
        if self.ready == True:
            movies = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line and self.filter in line:
                        movieline = line.split(':::')
                        try:
                            movie = movieline[0]
                        except IndexError:
                            movie = ' '

                        if movie != ' ':
                            movies = movies + movie + ':::'

                self.movies = [ i for i in movies.split(':::') ]
                self.movies.pop()
                self.session.openWithCallback(self.gotoMovie, allMovieList, self.movies, self.index, self.content)

    def gotoMovie(self, index):
        if self.ready == True:
            self.index = index
            try:
                self.makePoster()
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
            except IndexError:
                pass

    def filterGenre(self):
        if self.ready == True:
            genres = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            genre = movieline[7]
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
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.session.openWithCallback(self.makeMovies, filterList, self.genres, 'Genre Filter')

    def filterActor(self):
        if self.ready == True:
            actors = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            actor = movieline[6]
                        except IndexError:
                            actor = ' '

                        if actor != ' ':
                            actors = actors + actor + ', '

                self.actors = [ i for i in actors.split(', ') ]
                self.actors.sort()
                self.actors.pop(0)
                try:
                    last = self.actors[-1]
                    for i in range(len(self.actors) - 2, -1, -1):
                        if last == self.actors[i]:
                            del self.actors[i]
                        else:
                            last = self.actors[i]

                except IndexError:
                    pass

                self.index = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.session.openWithCallback(self.makeMovies, filterList, self.actors, 'Actor Filter')

    def filterDirector(self):
        if self.ready == True:
            directors = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            director = movieline[5]
                        except IndexError:
                            director = ' '

                        if director != ' ':
                            directors = directors + director + ', '

                self.directors = [ i for i in directors.split(', ') ]
                self.directors.sort()
                self.directors.pop(0)
                try:
                    last = self.directors[-1]
                    for i in range(len(self.directors) - 2, -1, -1):
                        if last == self.directors[i]:
                            del self.directors[i]
                        else:
                            last = self.directors[i]

                except IndexError:
                    pass

                self.index = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.session.openWithCallback(self.makeMovies, filterList, self.directors, 'Director Filter')

    def filterSeasons(self):
        if self.ready == True:
            self.content = ':::Series:::'
            seasons = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            season = movieline[0]
                            season = season + 'FIN'
                            season = sub('[(]S', 'Season ', season)
                            season = sub('[(]s', 'season ', season)
                            season = sub('[Ee][0-9]+[)].*?FIN', '', season)
                            season = sub('FIN', '', season)
                        except IndexError:
                            season = ' '

                        if season != ' ':
                            seasons = seasons + season + ', '

                self.seasons = [ i for i in seasons.split(', ') ]
                self.seasons.sort()
                self.seasons.pop(0)
                try:
                    last = self.seasons[-1]
                    for i in range(len(self.seasons) - 2, -1, -1):
                        if last == self.seasons[i]:
                            del self.seasons[i]
                        else:
                            last = self.seasons[i]

                except IndexError:
                    pass

                self.index = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.session.openWithCallback(self.makeMovies, filterSeasonList, self.seasons)

    def sortDatabase(self):
        self.sortorder = config.plugins.moviebrowser.sortorder.value
        f = open(self.database, 'r')
        lines = f.readlines()
        f.close()
        if self.sortorder == 'name':
            lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
        elif self.sortorder == 'name_reverse':
            lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
        elif self.sortorder == 'rating':
            lines.sort(key=lambda line: line.split(':::')[4])
        elif self.sortorder == 'rating_reverse':
            lines.sort(key=lambda line: line.split(':::')[4], reverse=True)
        elif self.sortorder == 'year':
            lines.sort(key=lambda line: line.split(':::')[8])
        elif self.sortorder == 'year_reverse':
            lines.sort(key=lambda line: line.split(':::')[8], reverse=True)
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

    def switchView(self):
        if self.ready == True:
            self.session.openWithCallback(self.exit, movieBrowserPosterwall, self.index, self.content, self.filter)

    def toogleContent(self):
        if self.ready == True:
            if self.content == ':::Movie:::' or self.content == ':::':
                self.content = ':::Series:::'
                self.filter = ':::Series:::'
                self.index = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.makeMovies(self.filter)
            else:
                self.content = ':::Movie:::'
                self.filter = ':::Movie:::'
                self.index = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.makeMovies(self.filter)

    def editDatabase(self):
        if self.ready == True:
            self.session.openWithCallback(self.makeMovies, movieDatabase)

    def wikipedia(self):
        if self.ready == True:
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/Wikipedia/plugin.pyo'):
                self.session.open(searchWikipedia, self.namelist[self.index], self.infolist[self.index][2], self.infolist[self.index][3])
            else:
                self.session.open(MessageBox, _('\nThe Wikipedia plugin could not be found.\n\nPlease download and install the plugin from:\nwww.kashmir-plugins.de'), MessageBox.TYPE_INFO)
                return

    def showPath(self):
        if self.ready == True:
            self.session.open(MessageBox, _('\nMovie File:\n%s') % self.movielist[self.index], MessageBox.TYPE_INFO)

    def getIndex(self, list):
        return list.getSelectedIndex()

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def config(self):
        if self.ready == True:
            self.session.openWithCallback(self.exit, movieBrowserConfig)

    def zap(self):
        if self.ready == True:
            servicelist = self.session.instantiateDialog(ChannelSelection)
            self.session.execDialog(servicelist)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            if config.plugins.moviebrowser.m1v.value == 'yes':
                while count > 0:
                    count -= 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.plugins.moviebrowser.transparency.value * count / 40))
                    f.close()

            else:
                while count > 0:
                    count -= 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.av.osd_alpha.value * count / 40))
                    f.close()

        else:
            self.hideflag = True
            count = 0
            if config.plugins.moviebrowser.m1v.value == 'yes':
                while count < 40:
                    count += 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.plugins.moviebrowser.transparency.value * count / 40))
                    f.close()

            else:
                while count < 40:
                    count += 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.av.osd_alpha.value * count / 40))
                    f.close()

    def exit(self):
        if config.plugins.moviebrowser.showtv.value == 'hide' or config.plugins.moviebrowser.m1v.value == 'yes':
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
            self.session.nav.playService(self.oldService)
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        self.close()


class movieBrowserPosterwall(Screen):

    def __init__(self, session, index, content, filter):
        if config.plugins.moviebrowser.plugin_size.value == 'full':
            self.xd = False
            self.spaceTop = 0
            self.spaceLeft = 16
            self.spaceX = 5
            self.spaceY = 5
            self.picX = 133
            self.picY = 200
            self.posterX = 9
            self.posterY = 3
            self.posterALL = 27
            self.posterREST = 0
        else:
            self.xd = True
            self.spaceTop = 0
            self.spaceLeft = 10
            self.spaceX = 5
            self.spaceY = 5
            self.picX = 106
            self.picY = 160
            self.posterX = 9
            self.posterY = 3
            self.posterALL = 27
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
            skincontent += '<widget name="poster_back' + str(x) + '" position="' + str(posX) + ',' + str(posY) + '" size="' + str(self.picX) + ',' + str(self.picY) + '" zPosition="11" transparent="1" alphatest="blend" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/poster_backHD.png" />'

        skin = '\n\t\t\t\t\t<screen position="center,center" size="1024,576" flags="wfNoBorder" title="  " >\n\t\t\t\t\t\t<widget name="backdrop" position="0,0" size="1024,576" alphatest="on" transparent="0" zPosition="1" />\n\t\t\t\t\t\t<widget name="infoback" position="5,500" size="1014,71" alphatest="blend" transparent="1" zPosition="2" />\n\n\t\t\t\t\t\t<widget name="ratings" position="15,524" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="3" />\n\t\t\t\t\t\t<widget name="ratingsback" position="15,524" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="4" />\n\t\t\t\t\t\t<widget name="ratingtext" position="235,500" size="40,71" font="Regular;24" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="5" />\n\t\t\t\t\t\t<widget name="name" position="285,500" size="454,71" font="Regular;26" foregroundColor="#FFFFFF" halign="center" valign="center" transparent="1" zPosition="6" />\n\t\t\t\t\t\t<widget name="runtime" position="764,500" size="120,71" font="Regular;24" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="7" />\n\t\t\t\t\t\t<widget name="country" position="889,500" size="55,71" font="Regular;24" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="8" />\n\t\t\t\t\t\t<widget name="year" position="949,500" size="60,71" font="Regular;24" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="9" />\n\n\t\t\t\t\t\t<widget name="2infoback" position="15,15" size="460,400" alphatest="blend" transparent="1" zPosition="12" />\n\t\t\t\t\t\t<widget name="2name" position="25,16" size="440,55" font="Regular;24" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="13" />\n\t\t\t\t\t\t<widget name="2Rating" position="25,70" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t\t\t<widget name="2ratings" position="25,100" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="15" />\n\t\t\t\t\t\t<widget name="2ratingsback" position="25,100" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="16" />\n\t\t\t\t\t\t<widget name="2ratingtext" position="245,100" size="40,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t\t\t<widget name="2Director" position="25,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t\t\t<widget name="2director" position="25,170" size="285,50" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t\t\t<widget name="2Country" position="320,140" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="20" />\n\t\t\t\t\t\t<widget name="2country" position="320,170" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="21" />\n\t\t\t\t\t\t<widget name="2Actors" position="25,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="22" />\n\t\t\t\t\t\t<widget name="2actors" position="25,240" size="285,95" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="23" />\n\t\t\t\t\t\t<widget name="2Year" position="320,210" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="24" />\n\t\t\t\t\t\t<widget name="2year" position="320,240" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="25" />\n\t\t\t\t\t\t<widget name="2Runtime" position="320,280" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="26" />\n\t\t\t\t\t\t<widget name="2runtime" position="320,310" size="125,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="27" />\n\t\t\t\t\t\t<widget name="2Genres" position="25,350" size="125,25" font="Regular;20" halign="left" foregroundColor="{color}" transparent="1" zPosition="28" />\n\t\t\t\t\t\t<widget name="2genres" position="25,380" size="440,25" font="Regular;20" foregroundColor="#FFFFFF" transparent="1" zPosition="29" />\n\n\t\t\t\t\t\t<widget name="plotfullback" position="549,15" size="460,400" alphatest="blend" transparent="1" zPosition="30" />\n\t\t\t\t\t\t<widget name="plotfull" position="559,22" size="440,390" font="{font}" foregroundColor="#FFFFFF" transparent="1" zPosition="31" />\n\t\t\t\t\t\t<widget name="eposter" position="25,50" size="440,330" alphatest="on" transparent="1" zPosition="32" />\n\n\t\t\t\t\t\t<widget name="frame" position="5,-5" size="126,180" zPosition="12" alphatest="on" />"\n\t\t\t\t\t\t' + skincontent + '\n\t\t\t\t\t</screen>'
        skinHD = '\n\t\t\t\t\t<screen position="center,center" size="1280,720" flags="wfNoBorder" title="  " >\n\t\t\t\t\t\t<widget name="backdrop" position="0,0" size="1280,720" alphatest="on" transparent="0" zPosition="1" />\n\t\t\t\t\t\t<widget name="infoback" position="5,620" size="1270,95" alphatest="blend" transparent="1" zPosition="2" />\n\n\t\t\t\t\t\t<widget name="ratings" position="25,657" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="3" />\n\t\t\t\t\t\t<widget name="ratingsback" position="25,657" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="4" />\n\t\t\t\t\t\t<widget name="ratingtext" position="245,620" size="40,95" font="Regular;26" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="5" />\n\t\t\t\t\t\t<widget name="name" position="295,620" size="690,95" font="Regular;28" foregroundColor="#FFFFFF" valign="center" halign="center" transparent="1" zPosition="6" />\n\t\t\t\t\t\t<widget name="runtime" position="1000,620" size="120,95" font="Regular;26" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="7" />\n\t\t\t\t\t\t<widget name="country" position="1125,620" size="60,95" font="Regular;26" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="8" />\n\t\t\t\t\t\t<widget name="year" position="1190,620" size="65,95" font="Regular;26" foregroundColor="#FFFFFF" halign="right" valign="center" transparent="1" zPosition="9" />\n\n\t\t\t\t\t\t<widget name="2infoback" position="25,25" size="525,430" alphatest="blend" transparent="1" zPosition="12" />\n\t\t\t\t\t\t<widget name="2name" position="40,30" size="495,70" font="Regular;28" foregroundColor="#FFFFFF" valign="center" transparent="1" zPosition="13" />\n\t\t\t\t\t\t<widget name="2Rating" position="40,100" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="14" />\n\t\t\t\t\t\t<widget name="2ratings" position="40,130" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png" borderWidth="0" orientation="orHorizontal" transparent="1" zPosition="15" />\n\t\t\t\t\t\t<widget name="2ratingsback" position="40,130" size="210,21" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png" alphatest="on" zPosition="16" />\n\t\t\t\t\t\t<widget name="2ratingtext" position="260,130" size="50,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="17" />\n\t\t\t\t\t\t<widget name="2Director" position="40,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="18" />\n\t\t\t\t\t\t<widget name="2director" position="40,200" size="320,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="19" />\n\t\t\t\t\t\t<widget name="2Country" position="370,170" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="20" />\n\t\t\t\t\t\t<widget name="2country" position="370,200" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="21" />\n\t\t\t\t\t\t<widget name="2Actors" position="40,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="22" />\n\t\t\t\t\t\t<widget name="2actors" position="40,270" size="320,102" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="23" />\n\t\t\t\t\t\t<widget name="2Year" position="370,240" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="24" />\n\t\t\t\t\t\t<widget name="2year" position="370,270" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="25" />\n\t\t\t\t\t\t<widget name="2Runtime" position="370,310" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="26" />\n\t\t\t\t\t\t<widget name="2runtime" position="370,340" size="125,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="27" />\n\t\t\t\t\t\t<widget name="2Genres" position="40,380" size="125,28" font="Regular;22" halign="left" foregroundColor="{color}" transparent="1" zPosition="28" />\n\t\t\t\t\t\t<widget name="2genres" position="40,410" size="500,28" font="Regular;22" foregroundColor="#FFFFFF" transparent="1" zPosition="29" />\n\n\t\t\t\t\t\t<widget name="plotfullback" position="730,25" size="525,430" alphatest="blend" transparent="1" zPosition="30" />\n\t\t\t\t\t\t<widget name="plotfull" position="745,40" size="495,393" font="{font}" foregroundColor="#FFFFFF" transparent="1" zPosition="31" />\n\t\t\t\t\t\t<widget name="eposter" position="37,53" size="500,375" alphatest="on" transparent="1" zPosition="32" />\n\n\t\t\t\t\t\t<widget name="frame" position="11,-5" size="153,220" zPosition="12" alphatest="on" />"\n\t\t\t\t\t\t' + skincontent + '\n\t\t\t\t\t</screen>'
        if self.xd == False:
            color = config.plugins.moviebrowser.color.value
            if config.plugins.moviebrowser.plotfont.value == 'normal':
                font = 'Regular;22'
            else:
                font = 'Regular;20'
            self.dict = {'color': color,
             'font': font}
            self.skin = applySkinVars(skinHD, self.dict)
        else:
            color = config.plugins.moviebrowser.color.value
            if config.plugins.moviebrowser.plotfont.value == 'normal':
                font = 'Regular;20'
            else:
                font = 'Regular;18'
            self.dict = {'color': color,
             'font': font}
            self.skin = applySkinVars(skin, self.dict)
        Screen.__init__(self, session)
        self.oldService = self.session.nav.getCurrentlyPlayingServiceReference()
        self.hideflag = True
        self.ready = False
        self.renew = False
        self.update = False
        self.infofull = False
        self.plotfull = False
        self.tmdbposter = False
        self.index = index
        self.wallindex = self.index % self.posterALL
        self.pagecount = self.index // self.posterALL + 1
        self.oldindex = 0
        self.pagemax = 1
        self.content = content
        self.filter = filter
        if config.plugins.moviebrowser.language.value == 'de':
            self.language = '&language=de'
        elif config.plugins.moviebrowser.language.value == 'es':
            self.language = '&language=es'
        elif config.plugins.moviebrowser.language.value == 'ru':
            self.language = '&language=ru'
        else:
            self.language = '&language=en'
        if config.plugins.moviebrowser.database.value == 'tmdb':
            self.firstdatabase = 'tmdb'
        elif config.plugins.moviebrowser.database.value == 'imdb':
            self.firstdatabase = 'imdb'
        else:
            self.firstdatabase = 'tvdb'
        if config.plugins.moviebrowser.plotfull.value == 'show':
            self.showplotfull = True
        else:
            self.showplotfull = False
        self.namelist = []
        self.movielist = []
        self.datelist = []
        self.infolist = []
        self.plotlist = []
        self.posterlist = []
        self.backdroplist = []
        self.contentlist = []
        self['name'] = Label()
        self['runtime'] = Label()
        self['country'] = Label()
        self['year'] = Label()
        self['ratingtext'] = Label()
        self['ratings'] = ProgressBar()
        self['ratings'].hide()
        self['ratingsback'] = Pixmap()
        self['ratingsback'].hide()
        self['infoback'] = Pixmap()
        self['frame'] = Pixmap()
        self['backdrop'] = Pixmap()
        if config.plugins.moviebrowser.backdrops.value == 'show':
            self.backdrops = True
        else:
            self.backdrops = False
        for x in range(self.posterALL):
            self['poster' + str(x)] = Pixmap()
            self['poster_back' + str(x)] = Pixmap()

        self['2name'] = Label()
        self['2Director'] = Label()
        self['2director'] = Label()
        self['2Actors'] = Label()
        self['2actors'] = Label()
        self['2Year'] = Label()
        self['2year'] = Label()
        self['2Runtime'] = Label()
        self['2runtime'] = Label()
        self['2Country'] = Label()
        self['2country'] = Label()
        self['2Genres'] = Label()
        self['2genres'] = Label()
        self['2Rating'] = Label()
        self['2ratingtext'] = Label()
        self['2ratings'] = ProgressBar()
        self['2ratings'].hide()
        self['2ratingsback'] = Pixmap()
        self['2ratingsback'].hide()
        self['2infoback'] = Pixmap()
        self['2infoback'].hide()
        self['plotfull'] = Label()
        self['plotfull'].hide()
        self['plotfullback'] = Pixmap()
        self['plotfullback'].hide()
        self['eposter'] = Pixmap()
        self['eposter'].hide()
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
         'nextBouquet': self.zap,
         'prevBouquet': self.zap,
         'red': self.deleteMovie,
         'yellow': self.renewIMDb,
         'green': self.renewTMDb,
         #'blue': self.hideScreen,
         'contextMenu': self.config,
         'showEventInfo': self.toggleInfoFull,
         'startTeletext': self.editDatabase,
         'leavePlayer': self.toggleBackdrops,
         'movieList': self.updateDatabase,
         '1': self.showMovies,
         '2': self.switchView,
         '3': self.showPath,
         '4': self.filterSeasons,
         '5': self.toogleContent,
         #'6': self.wikipedia,
         '7': self.filterDirector,
         '8': self.filterActor,
         '9': self.filterGenre,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
	cmd = "mkdir /usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/;mkdir /usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/cache"
	os.system(cmd) 
        self.updatefile = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/update'
        self.blacklist = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/blacklist'
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/database'
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        if config.plugins.moviebrowser.showtv.value == 'hide':
            self.session.nav.stopService()
        if config.plugins.moviebrowser.m1v.value == 'yes':
            self.session.nav.stopService()
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.plugins.moviebrowser.transparency.value)
            f.close()
        if self.xd == False:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_backHD.png'
            self.infosmallBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_small_backHD.png'
            InfoBack = loadPic(self.infosmallBackPNG, 1270, 95, 3, 0, 0, 1)
        else:
            self.infoBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_back.png'
            self.infosmallBackPNG = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/info_small_back.png'
            InfoBack = loadPic(self.infosmallBackPNG, 1014, 71, 3, 0, 0, 1)
        if InfoBack != None:
            self['infoback'].instance.setPixmap(InfoBack)
            self['infoback'].show()
        if fileExists(self.database):
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.reset = False
            self.makeMovieBrowserTimer = eTimer()
            self.makeMovieBrowserTimer.callback.append(self.makeMovies(self.filter))
            self.makeMovieBrowserTimer.start(500, True)
        else:
            self.openTimer = eTimer()
            self.openTimer.callback.append(self.openInfo)
            self.openTimer.start(500, True)

    def openInfo(self):
        if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset'):
            self.session.openWithCallback(self.reset_return, MessageBox, _('\nThe Movie Browser Database will be build now.\nDepending on the number of your movies this can take several minutes.\n\nBuild Movie Browser Database now?'), MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.first_return, MessageBox, _('\nBefore the Movie Browser Database will be build for the first time,\nyou should check your Movie Folder setting and change the\nCache Folder to a hard drive disk for faster access or to an sub stick.'), MessageBox.TYPE_YESNO)

    def first_return(self, answer):
        if answer is True:
            open('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset', 'w').close()
            self.session.openWithCallback(self.exit, movieBrowserConfig)
        else:
            self.close()

    def reset_return(self, answer):
        if answer is True:
            self.reset = True
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset'):
                os.remove('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset')
            self.resetTimer = eTimer()
            self.resetTimer.callback.append(self.database_return(True))
            self.resetTimer.start(500, True)
        else:
            self.close()

    def makeMovies(self, filter):
        self.namelist = []
        self.movielist = []
        self.datelist = []
        self.infolist = []
        self.plotlist = []
        self.posterlist = []
        self.backdroplist = []
        self.contentlist = []
        self.filter = filter
        if fileExists(self.database):
            f = open(self.database, 'r')
            for line in f:
                if self.content in line and filter in line:
                    movieline = line.split(':::')
                    try:
                        name = movieline[0]
                    except IndexError:
                        name = ' '

                    try:
                        filename = movieline[1]
                    except IndexError:
                        filename = ' '

                    try:
                        date = movieline[2]
                    except IndexError:
                        date = ' '

                    try:
                        runtime = movieline[3]
                    except IndexError:
                        runtime = ' '

                    try:
                        rating = movieline[4]
                    except IndexError:
                        rating = ' '

                    try:
                        director = movieline[5]
                    except IndexError:
                        director = ' '

                    try:
                        actors = movieline[6]
                    except IndexError:
                        actors = ' '

                    try:
                        genres = movieline[7]
                    except IndexError:
                        genres = ' '

                    try:
                        year = movieline[8]
                    except IndexError:
                        year = ' '

                    try:
                        country = movieline[9]
                    except IndexError:
                        country = ' '

                    try:
                        plotfull = movieline[10]
                    except IndexError:
                        plotfull = ' '

                    try:
                        poster = movieline[11]
                    except IndexError:
                        poster = 'http://cf2.imgobject.com/t/p/w154' + '/default_poster.png'

                    try:
                        backdrop = movieline[12]
                    except IndexError:
                        backdrop = 'http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png'

                    try:
                        content = movieline[13]
                    except IndexError:
                        content = 'Series'

                    self.namelist.append(name)
                    self.movielist.append(filename)
                    self.datelist.append(date)
                    res = []
                    res.append(runtime)
                    res.append(rating)
                    res.append(director)
                    res.append(actors)
                    res.append(genres)
                    res.append(year)
                    res.append(country)
                    self.infolist.append(res)
                    self.plotlist.append(plotfull)
                    self.posterlist.append(poster)
                    self.backdroplist.append(backdrop)
                    self.contentlist.append(content)

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
                if self.backdrops == True:
                    try:
                        self.showBackdrops(self.index)
                    except IndexError:
                        pass

                else:
                    self.hideBackdrops()
                try:
                    self.makeName(self.index)
                except IndexError:
                    pass

                try:
                    self.makeInfo(self.index)
                except IndexError:
                    pass

                if self.infofull == True and self.plotfull == False:
                    try:
                        self.showInfoFull(self.index)
                    except IndexError:
                        pass

                elif self.infofull == True and self.plotfull == True:
                    try:
                        self.showPlotFull(self.index)
                    except IndexError:
                        pass

                self.ready = True

    def updateDatabase(self):
        if self.ready == True:
            if os.path.exists(config.plugins.moviebrowser.moviefolder.value):
                self.session.openWithCallback(self.database_return, MessageBox, _('\nUpdate Movie Browser Database?'), MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, _('\nMovie Folder %s not reachable.\nMovie Browser Database Update canceled.') % str(config.plugins.moviebrowser.moviefolder.value), MessageBox.TYPE_ERROR)

    def database_return(self, answer):
        if answer is True:
            open(self.updatefile, 'w').close()
            self.update = True
            self.ready = False
            self.namelist = []
            self.movielist = []
            self.datelist = []
            self.infolist = []
            self.plotlist = []
            self.posterlist = []
            self.backdroplist = []
            self.orphaned = 0
            if fileExists(self.database):
                allfiles = ':::'
                folder = config.plugins.moviebrowser.moviefolder.value
                for root, dirs, files in os.walk(folder, topdown=False):
                    for name in files:
                        filename = os.path.join(root, name)
                        filedate = os.path.getctime(filename)
                        allfiles = allfiles + str(filedate)

                data = open(self.database).read()
                for line in data.split('\n'):
                    movieline = line.split(':::')
                    try:
                        moviefolder = movieline[1]
                        moviedate = movieline[2]
                    except IndexError:
                        moviefolder = ''
                        moviedate = ''

                    if search(config.plugins.moviebrowser.moviefolder.value, moviefolder) is not None and search(moviedate, allfiles) is None:
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
            if fileExists(self.blacklist):
                blacklist = open(self.blacklist).read()
                alldata = data + blacklist
            else:
                alldata = data
            folder = config.plugins.moviebrowser.moviefolder.value
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    movie = sub('\\(', '.', name)
                    movie = sub('\\)', '.', movie)
                    if search(movie, alldata) is None:
                        if name.endswith('.ts') or name.endswith('.avi') or name.endswith('.divx') or name.endswith('.flv') or name.endswith('.iso') or name.endswith('.ISO') or name.endswith('.m2ts') or name.endswith('.mov') or name.endswith('.mp4') or name.endswith('.mpg') or name.endswith('.mpeg') or name.endswith('.mkv') or name.endswith('.vob'):
                            filename = os.path.join(root, name)
                            self.movielist.append(filename)
                            self.datelist.append(os.path.getctime(filename))
                            if name.endswith('.ts'):
                                name = sub('.*? - .*? - ', '', name)
                                name = sub('[.]ts', '', name)
                            else:
                                name = sub('[.]avi', '', name)
                                name = sub('[.]divx', '', name)
                                name = sub('[.]flv', '', name)
                                name = sub('[.]iso', '', name)
                                name = sub('[.]ISO', '', name)
                                name = sub('[.]m2ts', '', name)
                                name = sub('[.]mov', '', name)
                                name = sub('[.]mp4', '', name)
                                name = sub('[.]mpg', '', name)
                                name = sub('[.]mpeg', '', name)
                                name = sub('[.]mkv', '', name)
                                name = sub('[.]vob', '', name)
                            print name
                            self.namelist.append(name)

            self.dbcount = 1
            self.dbcountmax = len(self.movielist)
            if self.dbcountmax == 0:
                self.finished_update(False)
            else:
                self.name = self.namelist[0]
                if config.plugins.moviebrowser.database.value == 'tmdb':
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                    self.firstdatabase = 'tmdb'
                    url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
                    self.getTMDbData(url, 1, '0', False)
                elif config.plugins.moviebrowser.database.value == 'imdb':
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                    self.firstdatabase = 'imdb'
                    url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
                    self.getIMDbData(url, 1)
                else:
                    movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                    self.firstdatabase = 'tvdb'
                    movie = movie + 'FIN'
                    movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
                    movie = sub('FIN', '', movie)
                    url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
                    self.getTVDbData(url, 1, '0')

    def getIMDbData(self, url, runlevel):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            output = output.replace('\\u00e4', '\xc3\xa4').replace('\\u00f6', '\xc3\xb6').replace('\\u00fc', '\xc3\xbc').replace('\\u00c4', '\xc3\x84').replace('\\u00f6', '\xc3\x9f').replace('\\u00dc', '\xc3\x9c').replace('\\u00df', '\xc3\x9f').replace('\\u0026', '&').replace('\\u00e9', '\xc3\xa9').replace('\\u00e5', '\xc3\xa5').replace('\\"', '').replace('&amp;', '&')
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"error":"Film not found"', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'imdb'
            self.translateGoogle(text)
        elif search('"error":"Film not found"', output) is not None and runlevel == 2:
            movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            movie = movie + 'FIN'
            movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
            movie = sub('FIN', '', movie)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 1, '0')
        else:
            name = re.findall('<title>(.*?)</title>', output)
            runtime = re.findall('<runtime><item>.*?([0-9]+ min).*?</item>', output)
            rating = re.findall('<rating>(.*?)</rating>', output)
            director = re.findall('<directors><item>(.*?)</item>', output)
            actors = re.findall('<actors>(.*?)</actors>', output)
            try:
                actor = re.findall('<item>(.*?)</item>', actors[0])
            except IndexError:
                actor = []

            genres = re.findall('<genres>(.*?)</genres>', output)
            try:
                genre = re.findall('<item>(.*?)</item>', genres[0])
            except IndexError:
                genre = []

            year = re.findall('<year>(.*?)</year>', output)
            country = re.findall('<country><item>(.*?)</item>', output)
            plotfull = re.findall('<plot>(.*?)</plot>', output)
            try:
                self.namelist[self.dbcount - 1] = name[0]
            except IndexError:
                self.namelist[self.dbcount - 1] = self.name

            res = []
            try:
                res.append(runtime[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                res.append(director[0])
            except IndexError:
                res.append(' ')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor[1]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[2]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[3]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[4]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor[5]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor[6]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre[1]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[2]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[3]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre[4]
            except IndexError:
                pass

            try:
                res.append(genres)
            except IndexError:
                res.append(' ')

            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(country[0].replace('Germany', 'GER'))
            except IndexError:
                res.append(' ')

            self.infolist.append(res)
            try:
                self.plotlist.append(plotfull[0].replace('\\', ''))
            except IndexError:
                self.plotlist.append(' ')

            movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbPoster(url, 1)

    def getTMDbPoster(self, url, runlevel):
        self.tmdbposter = True
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"total_results":0', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'tmdbposter'
            self.translateGoogle(text)
        else:
            backdrop = re.findall('"backdrop_path":"(.*?)"', output)
            poster = re.findall('"poster_path":"(.*?)"', output)
            try:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
            except IndexError:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

            try:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
            except IndexError:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            self.tmdbposter = False
            self.makeDataEntry(self.dbcount - 1, True)

    def getTMDbData(self, url, runlevel, tmdbid, renew):
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('"total_results":0', output) is not None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.trans = 'tmdb'
            self.translateGoogle(text)
        elif search('"total_results":0', output) is not None and runlevel == 2:
            movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            movie = movie + 'FIN'
            movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
            movie = sub('FIN', '', movie)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 1, '0')
        else:
            if tmdbid == '0':
                tmdbid = re.findall('"id":(.*?),', output)
                try:
                    tmdbid = tmdbid[0]
                except IndexError:
                    tmdbid = '0'

                name = re.findall('"title":"(.*?)"', output)
                backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                year = re.findall('"release_date":"(.*?)-', output)
                poster = re.findall('"poster_path":"(.*?)"', output)
                rating = re.findall('"vote_average":(.*?),', output)
                try:
                    self.namelist[self.dbcount - 1] = name[0]
                except IndexError:
                    self.namelist[self.dbcount - 1] = self.name

                try:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
                except IndexError:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

                try:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
                except IndexError:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

                url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid + self.language
                headers = {'Accept': 'application/json'}
                request = Request(url, headers=headers)
                try:
                    output = urlopen(request).read()
                except URLError:
                    output = ''
                except HTTPError:
                    output = ''
                except socket.error:
                    output = ''

            plot = re.findall('"overview":"(.*?)","', output)
            if renew == True:
                output = sub('"belongs_to_collection":{.*?}', '', output)
                name = re.findall('"title":"(.*?)"', output)
                backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                poster = re.findall('"poster_path":"(.*?)"', output)
            url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid
            headers = {'Accept': 'application/json'}
            request = Request(url, headers=headers)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('"belongs_to_collection":{.*?}', '', output)
            if not plot:
                plot = re.findall('"overview":"(.*?)","', output)
            genre = re.findall('"genres":[[]."id":[0-9]+,"name":"(.*?)"', output)
            genre2 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre3 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre4 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            genre5 = re.findall('"genres":[[]."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":".*?".,."id":[0-9]+,"name":"(.*?)"', output)
            country = re.findall('"iso_3166_1":"(.*?)"', output)
            runtime = re.findall('"runtime":(.*?),', output)
            if renew == True:
                year = re.findall('"release_date":"(.*?)-', output)
                rating = re.findall('"vote_average":(.*?),', output)
                if not backdrop:
                    backdrop = re.findall('"backdrop_path":"(.*?)"', output)
                if not poster:
                    poster = re.findall('"poster_path":"(.*?)"', output)
                try:
                    self.namelist[self.dbcount - 1] = name[0]
                except IndexError:
                    self.namelist[self.dbcount - 1] = self.name

                try:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + backdrop[0])
                except IndexError:
                    self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

                try:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + poster[0])
                except IndexError:
                    self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            url = 'http://api.themoviedb.org/3/movie/%s/casts?api_key=dfc629f7ff6936a269f8c5cdb194c890' % tmdbid + self.language
            headers = {'Accept': 'application/json'}
            request = Request(url, headers=headers)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            actor = re.findall('"name":"(.*?)"', output)
            actor2 = re.findall('"name":".*?"name":"(.*?)"', output)
            actor3 = re.findall('"name":".*?"name":".*?"name":"(.*?)"', output)
            actor4 = re.findall('"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor5 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor6 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            actor7 = re.findall('"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":".*?"name":"(.*?)"', output)
            director = re.findall('"([^"]+)","department":"Directing","job":"Director"', output)
            res = []
            try:
                res.append(runtime[0] + ' min')
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                res.append(director[0])
            except IndexError:
                res.append(' ')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor2[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor3[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor4[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor5[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor6[0]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor7[0]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre2[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre3[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre4[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre5[0]
            except IndexError:
                pass

            res.append(genres.replace('Science Fiction', 'Sci-Fi'))
            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            try:
                res.append(country[0].replace('US', 'USA'))
            except IndexError:
                res.append(' ')

            self.infolist.append(res)
            try:
                self.plotlist.append(plot[0].replace('\\', ''))
            except IndexError:
                self.plotlist.append(' ')

            self.makeDataEntry(self.dbcount - 1, True)

    def translateGoogle(self, text):
        if config.plugins.moviebrowser.language.value == 'de':
            url = 'http://translate.google.com/m?hl=en&sl=de&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'es':
            url = 'http://translate.google.com/m?hl=en&sl=es&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'ru':
            url = 'http://translate.google.com/m?hl=en&sl=ru&q=%s' % text.title()
        else:
            url = 'http://translate.google.com/m?hl=en&sl=en&q=%s' % text.title()
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        before_trans = 'class="t0">'
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            data = output[output.find(before_trans) + len(before_trans):]
            movie = data.split('<')[0]
            print '%s >> %s' % (text, movie)
        except URLError:
            movie = text
        except HTTPError:
            movie = text
        except socket.error:
            movie = text

        if self.trans == 'imdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
            self.getIMDbData(url, 2)
        elif self.trans == 'tmdbposter':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbPoster(url, 2)
        elif self.trans == 'tmdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbData(url, 2, '0', False)
        elif self.trans == 'tvdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbData(url, 2, '0')

    def getTVDbData(self, url, runlevel, seriesid):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        if search('<Series>', output) is None and runlevel == 1:
            text = self.name.replace(' ', '%20')
            text = text + 'FIN'
            text = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', text)
            text = sub('FIN', '', text)
            self.trans = 'tvdb'
            self.translateGoogle(text)
        elif search('<Series>', output) is None and runlevel == 2:
            self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')
            self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')
            self.namelist[self.dbcount - 1] = self.name
            res = []
            res.append(' ')
            res.append('0.0')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            res.append(' ')
            self.infolist.append(res)
            self.plotlist.append(' ')
            self.makeDataEntry(self.dbcount - 1, False)
        else:
            if seriesid == '0':
                seriesid = re.findall('<seriesid>(.*?)</seriesid>', output)
                try:
                    seriesid = seriesid[0]
                except IndexError:
                    seriesid = '0'

            if search('[Ss][0-9]+[Ee][0-9]+', self.name) is not None:
                data = search('([Ss][0-9]+[Ee][0-9]+)', self.name)
                data = data.group(1)
                season = search('[Ss]([0-9]+)[Ee]', data)
                season = season.group(1).lstrip('0')
                episode = search('[Ss][0-9]+[Ee]([0-9]+)', data)
                episode = episode.group(1).lstrip('0')
                url = 'http://www.thetvdb.com/api/D19315B88B2DE21F/series/' + seriesid + '/default/' + season + '/' + episode + '/' + config.plugins.moviebrowser.language.value + '.xml'
                agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
                request = Request(url, headers=agents)
                try:
                    output = urlopen(request).read()
                except URLError:
                    output = ''
                except HTTPError:
                    output = ''
                except socket.error:
                    output = ''

                output = sub('&amp;', '&', output)
                episode = re.findall('<EpisodeName>(.*?)</EpisodeName>', output)
                year = re.findall('<FirstAired>([0-9]+)-', output)
                guest = re.findall('<GuestStars>[|](.*?)[|]</GuestStars>', output)
                director = re.findall('<Director>[|](.*?)[|]', output)
                if not director:
                    director = re.findall('<Director>(.*?)</Director>', output)
                plotfull = re.findall('<Overview>(.*?)</Overview>', output, re.S)
                rating = re.findall('<Rating>(.*?)</Rating>', output)
                eposter = re.findall('<filename>(.*?)</filename>', output)
            else:
                data = ''
                episode = []
                year = []
                guest = []
                director = []
                plotfull = []
                rating = []
                eposter = []
            url = 'http://www.thetvdb.com/data/series/' + seriesid + '/' + config.plugins.moviebrowser.language.value + '.xml'
            agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
            request = Request(url, headers=agents)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('&amp;', '&', output)
            name = re.findall('<SeriesName>(.*?)</SeriesName>', output)
            runtime = re.findall('<Runtime>(.*?)</Runtime>', output)
            if not rating:
                rating = re.findall('<Rating>(.*?)</Rating>', output)
            actors = re.findall('<Actors>(.*?)</Actors>', output)
            try:
                actor = re.findall('[|](.*?)[|]', actors[0])
            except IndexError:
                actor = []

            try:
                actor2 = re.findall('[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor2 = []

            try:
                actor3 = re.findall('[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor3 = []

            try:
                actor4 = re.findall('[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor4 = []

            try:
                actor5 = re.findall('[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor5 = []

            try:
                actor6 = re.findall('[|].*?[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor6 = []

            try:
                actor7 = re.findall('[|].*?[|].*?[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', actors[0])
            except IndexError:
                actor7 = []

            genres = re.findall('<Genre>(.*?)</Genre>', output)
            try:
                genre = re.findall('[|](.*?)[|]', genres[0])
            except IndexError:
                genre = []

            try:
                genre2 = re.findall('[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre2 = []

            try:
                genre3 = re.findall('[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre3 = []

            try:
                genre4 = re.findall('[|].*?[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre4 = []

            try:
                genre5 = re.findall('[|].*?[|].*?[|].*?[|].*?[|](.*?)[|]', genres[0])
            except IndexError:
                genre5 = []

            if not year:
                year = re.findall('<FirstAired>([0-9]+)-', output)
            if not plotfull:
                plotfull = re.findall('<Overview>(.*?)</Overview>', output, re.S)
            backdrop = re.findall('<fanart>(.*?)</fanart>', output)
            poster = re.findall('<poster>(.*?)</poster>', output)
            try:
                if not episode:
                    self.namelist[self.dbcount - 1] = name[0].replace('Das n\xc3\xa4chste Jahrhundert', 'TNG')
                else:
                    self.namelist[self.dbcount - 1] = name[0].replace('Das n\xc3\xa4chste Jahrhundert', 'TNG') + ' - (' + data + ') ' + episode[0]
            except IndexError:
                self.namelist[self.dbcount - 1] = self.name

            res = []
            try:
                res.append(runtime[0] + ' min')
            except IndexError:
                res.append(' ')

            try:
                res.append(rating[0])
            except IndexError:
                res.append('0.0')

            try:
                if not director:
                    res.append('Various')
                else:
                    res.append(director[0])
            except IndexError:
                res.append('Various')

            try:
                actors = actor[0]
            except IndexError:
                actors = ' '

            try:
                actors = actors + ', ' + actor2[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor3[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor4[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor5[0]
            except IndexError:
                pass

            try:
                actors = actors + ', ' + actor6[0]
            except IndexError:
                pass

            if len(actors) < 95:
                try:
                    actors = actors + ', ' + actor7[0]
                except IndexError:
                    pass

            res.append(actors)
            try:
                genres = genre[0]
            except IndexError:
                genres = ' '

            try:
                genres = genres + ', ' + genre2[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre3[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre4[0]
            except IndexError:
                pass

            try:
                genres = genres + ', ' + genre5[0]
            except IndexError:
                pass

            try:
                res.append(genres.replace('Science-Fiction', 'Sci-Fi'))
            except IndexError:
                res.append(' ')

            try:
                res.append(year[0])
            except IndexError:
                res.append(' ')

            if config.plugins.moviebrowser.language.value == 'de':
                country = 'DE'
            elif config.plugins.moviebrowser.language.value == 'es':
                country = 'ES'
            else:
                country = 'USA'
            res.append(country)
            self.infolist.append(res)
            try:
                if not guest:
                    plotfull = plotfull[0].replace('\n', '').replace('&quot;', '"')
                else:
                    plotfull = plotfull[0].replace('\n', '').replace('&quot;', '"')
                    plotfull = plotfull + ' Guest Stars: ' + guest[0].replace('|', ', ') + '.'
                self.plotlist.append(plotfull)
            except IndexError:
                self.plotlist.append(' ')

            try:
                self.backdroplist.append('http://www.thetvdb.com/banners/' + backdrop[0])
            except IndexError:
                self.backdroplist.append('http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png')

            try:
                if not eposter:
                    self.posterlist.append('http://www.thetvdb.com/banners/_cache/' + poster[0])
                else:
                    self.posterlist.append('http://www.thetvdb.com/banners/_cache/' + poster[0] + '<episode>' + 'http://www.thetvdb.com/banners/' + eposter[0] + '<episode>')
            except IndexError:
                self.posterlist.append('http://cf2.imgobject.com/t/p/w154' + '/default_poster.png')

            self.makeDataEntry(self.dbcount - 1, False)

    def makeDataEntry(self, count, content):
        if self.renew == False:
            f = open(self.database, 'a')
            try:
                if content == True:
                    data = self.namelist[count] + ':::' + self.movielist[count] + ':::' + str(self.datelist[count]) + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Movie:::\n'
                else:
                    data = self.namelist[count] + ':::' + self.movielist[count] + ':::' + str(self.datelist[count]) + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Series:::\n'
                f.write(data)
            except IndexError:
                pass

            f.close()
        else:
            try:
                if content == True:
                    newdata = self.namelist[count] + ':::' + self.movielist[self.index] + ':::' + self.datelist[self.index] + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Movie:::'
                else:
                    newdata = self.namelist[count] + ':::' + self.movielist[self.index] + ':::' + self.datelist[self.index] + ':::' + self.infolist[count][0] + ':::' + self.infolist[count][1] + ':::' + self.infolist[count][2] + ':::' + self.infolist[count][3] + ':::' + self.infolist[count][4] + ':::' + self.infolist[count][5] + ':::' + self.infolist[count][6] + ':::' + self.plotlist[count] + ':::' + self.posterlist[count] + ':::' + self.backdroplist[count] + ':::Series:::'
            except IndexError:
                newdata = ''

            data = open(self.database).read()
            movie = self.movielist[self.index]
            movie = sub('\\(', '.', movie)
            movie = sub('\\)', '.', movie)
            if search(movie, data) is not None:
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        data = data.replace(line, newdata)

                f = open(self.database, 'w')
                f.write(data)
                f.close()
        if self.dbcount < self.dbcountmax:
            self.dbcount += 1
            self.name = self.namelist[self.dbcount - 1]
            if self.firstdatabase == 'tmdb':
                movie = self.name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
                self.getTMDbData(url, 1, '0', False)
            elif self.firstdatabase == 'imdb':
                movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=1&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
                self.getIMDbData(url, 1)
            else:
                movie = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
                movie = movie + 'FIN'
                movie = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', movie)
                movie = sub('FIN', '', movie)
                url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
                self.getTVDbData(url, 1, '0')
        elif self.update == True:
            if self.reset == True:
                self.session.openWithCallback(self.exit, movieBrowserPosterwall, self.index, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)
            else:
                self.finished_update(True)
        else:
            self.finished()

    def finished(self):
        if self.renew == False:
            self.index = 0
            self.oldindex = 0
            self.wallindex = 0
            self.pagecount = 1
            self.makeMovies(self.filter)
        else:
            self.renew = False
            self.makeMovies(self.filter)

    def finished_update(self, found):
        if found == False and self.orphaned == 0:
            self.session.open(MessageBox, _('\nNo new Movies found:\nYour Database is up to date.'), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMovies(self.filter)
        elif found == False:
            if self.orphaned == 1:
                self.session.open(MessageBox, _('\nNo new Movies found.\n%s Orphaned Movie deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\nNo new Movies found.\n%s Orphaned Movies deleted from Database.') % str(self.orphaned), MessageBox.TYPE_INFO)
            os.remove(self.updatefile)
            self.makeMovies(self.filter)
        elif self.orphaned == 0:
            if self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.') % str(self.dbcountmax), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMovies(self.filter)
        else:
            if self.dbcountmax == 1 and self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.\n%s Orphaned Movie deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.dbcountmax == 1:
                self.session.open(MessageBox, _('\n%s Movie imported into Database.\n%s Orphaned Movies deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            elif self.orphaned == 1:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.\n%s Orphaned Movie deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            else:
                self.session.open(MessageBox, _('\n%s Movies imported into Database.\n%s Orphaned Movies deleted from Database.') % (str(self.dbcountmax), str(self.orphaned)), MessageBox.TYPE_INFO)
            if fileExists(self.updatefile):
                self.sortDatabase()
                os.remove(self.updatefile)
            self.makeMovies(self.filter)

    def ok(self):
        if self.ready == True:
            try:
                filename = self.movielist[self.index]
                if filename.endswith('.ts'):
                    sref = eServiceReference('1:0:0:0:0:0:0:0:0:0:' + filename)
                    sref.setName(self.namelist[self.index])
                    self.session.open(MoviePlayer, sref)
                elif filename.endswith('.iso') or filename.endswith('.ISO'):
                    if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/DVDPlayer/'):
                        from Plugins.Extensions.DVDPlayer.plugin import DVDPlayer
                        self.session.open(DVDPlayer, dvd_filelist=[filename])
                    else:
                        self.session.open(MessageBox, _('DVD Player Plugin not installed.'), MessageBox.TYPE_ERROR)
                else:
                    sref = eServiceReference('4097:0:0:0:0:0:0:0:0:0:' + filename)
                    sref.setName(self.namelist[self.index])
                    self.session.open(MoviePlayer, sref)
            except IndexError:
                pass

    def renewIMDb(self):
        if self.ready == True:
            name = self.movielist[self.index]
            name = sub('.*?[/]', '', name)
            if name.endswith('.ts'):
                name = sub('.*? - .*? - ', '', name)
                name = sub('[.]ts', '', name)
            else:
                name = sub('[.]avi', '', name)
                name = sub('[.]divx', '', name)
                name = sub('[.]flv', '', name)
                name = sub('[.]iso', '', name)
                name = sub('[.]ISO', '', name)
                name = sub('[.]m2ts', '', name)
                name = sub('[.]mov', '', name)
                name = sub('[.]mp4', '', name)
                name = sub('[.]mpg', '', name)
                name = sub('[.]mpeg', '', name)
                name = sub('[.]mkv', '', name)
                name = sub('[.]vob', '', name)
            self.session.openWithCallback(self.renewIMDbReturn, VirtualKeyBoard, title='Update Single Movie Data - IMDb:', text=name)

    def renewIMDbReturn(self, name):
        if name and name != '':
            self.name = name
            name = name.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=10&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % name
            self.getIMDbMovies(url, 1)

    def getIMDbMovies(self, url, runlevel):
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        output = sub('</type><imdb_id>', '</type><poster>http://profile.ak.fbcdn.net/hprofile-ak-snc7/373026_15925638948_1021284996_q.jpg</poster><imdb_id>', output)
        rating = re.findall('<rating>(.*?)</rating>', output)
        year = re.findall('<year>(.*?)</year>', output)
        titles = re.findall('<title>(.*?)</title>', output)
        poster = re.findall('<poster>(.*?)</poster>', output)
        id = re.findall('<imdb_id>(.*?)</imdb_id>', output)
        country = re.findall('<country><item>(.*?)</item>', output)
        titel = 'IMDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.transrenew = 'imdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.openWithCallback(self.tvdb_return, MessageBox, _('\nNo IMDb Results - looking for %s on TheTVDb?') % self.name, MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.makeIMDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def makeIMDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'imdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://imdbapi.org/?ids=%s&type=xml&plot=full&episode=0&lang=en-US&aka=simple&release=simple&business=0&tech=0' % id
        self.getIMDbData(url, 1)

    def renewTMDb(self):
        if self.ready == True:
            name = self.movielist[self.index]
            name = sub('.*?[/]', '', name)
            if name.endswith('.ts'):
                name = sub('.*? - .*? - ', '', name)
                name = sub('[.]ts', '', name)
            else:
                name = sub('[.]avi', '', name)
                name = sub('[.]divx', '', name)
                name = sub('[.]flv', '', name)
                name = sub('[.]iso', '', name)
                name = sub('[.]ISO', '', name)
                name = sub('[.]m2ts', '', name)
                name = sub('[.]mov', '', name)
                name = sub('[.]mp4', '', name)
                name = sub('[.]mpg', '', name)
                name = sub('[.]mpeg', '', name)
                name = sub('[.]mkv', '', name)
                name = sub('[.]vob', '', name)
            if config.plugins.moviebrowser.database.value == 'tvdb':
                self.session.openWithCallback(self.renewTMDbReturn, VirtualKeyBoard, title='Update Single Series Data - TheTVDb:', text=name)
            else:
                self.session.openWithCallback(self.renewTMDbReturn, VirtualKeyBoard, title='Update Single Movie Data - TMDb:', text=name)

    def renewTMDbReturn(self, name):
        if name and name != '':
            self.name = name
            if config.plugins.moviebrowser.database.value == 'tmdb':
                name = name.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
                url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + name + self.language
                self.getTMDbMovies(url, 1)
            else:
                name = name.replace(' ', '+').replace(':', '+').replace('_', '+')
                name = name + 'FIN'
                name = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', name)
                name = sub('FIN', '', name)
                url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + name
                self.getTVDbMovies(url, 1)

    def getTMDbMovies(self, url, runlevel):
        headers = {'Accept': 'application/json'}
        request = Request(url, headers=headers)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        output = sub('"poster_path":"', '"poster_path":"http://cf2.imgobject.com/t/p/w154', output)
        output = sub('"poster_path":null', '"poster_path":"http://www.themoviedb.org/images/apps/moviebase.png"', output)
        rating = re.findall('"vote_average":(.*?),', output)
        year = re.findall('"release_date":"(.*?)-', output)
        titles = re.findall('"title":"(.*?)"', output)
        poster = re.findall('"poster_path":"(.*?)"', output)
        id = re.findall('"id":(.*?),', output)
        country = re.findall('"backdrop(.*?)_path"', output)
        titel = 'TMDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            self.transrenew = 'tmdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.openWithCallback(self.tvdb_return, MessageBox, _('\nNo TMDb Results - looking for %s on TheTVDb?') % self.name, MessageBox.TYPE_YESNO)
        else:
            self.session.openWithCallback(self.makeTMDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def tvdb_return(self, answer):
        if answer is True:
            name = self.name.replace(' ', '+').replace(':', '+').replace('_', '+')
            name = name + 'FIN'
            name = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', name)
            name = sub('FIN', '', name)
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + name
            self.getTVDbMovies(url, 1)

    def getTVDbMovies(self, url, runlevel):
        rating = []
        year = []
        titles = []
        poster = []
        id = []
        country = []
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
        except URLError:
            output = ''
        except HTTPError:
            output = ''
        except socket.error:
            output = ''

        output = output.replace('&amp;', '&')
        seriesid = re.findall('<seriesid>(.*?)</seriesid>', output)
        for x in range(len(seriesid)):
            url = 'http://www.thetvdb.com/data/series/' + seriesid[x] + '/' + config.plugins.moviebrowser.language.value + '.xml'
            agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
            request = Request(url, headers=agents)
            try:
                output = urlopen(request).read()
            except URLError:
                output = ''
            except HTTPError:
                output = ''
            except socket.error:
                output = ''

            output = sub('<poster>', '<poster>http://www.thetvdb.com/banners/_cache/', output)
            output = sub('<poster>http://www.thetvdb.com/banners/_cache/</poster>', '<poster>http://www.thetvdb.com/wiki/skins/common/images/wiki.png</poster>', output)
            output = sub('<Rating></Rating>', '<Rating>0.0</Rating>', output)
            output = sub('&amp;', '&', output)
            Rating = re.findall('<Rating>(.*?)</Rating>', output)
            Year = re.findall('<FirstAired>([0-9]+)-', output)
            Added = re.findall('<added>([0-9]+)-', output)
            Titles = re.findall('<SeriesName>(.*?)</SeriesName>', output)
            Poster = re.findall('<poster>(.*?)</poster>', output)
            TVDbid = re.findall('<id>(.*?)</id>', output)
            Country = re.findall('<Status>(.*?)</Status>', output)
            try:
                rating.append(Rating[0])
            except IndexError:
                rating('0.0')

            try:
                year.append(Year[0])
            except IndexError:
                try:
                    year.append(Added[0])
                except IndexError:
                    year.append(' ')

            try:
                titles.append(Titles[0])
            except IndexError:
                titles.append(' ')

            try:
                poster.append(Poster[0])
            except IndexError:
                poster.append('http://www.thetvdb.com/wiki/skins/common/images/wiki.png')

            try:
                id.append(TVDbid[0])
            except IndexError:
                id.append('0')

            try:
                country.append(Country[0])
            except IndexError:
                country.append(' ')

        titel = 'TheTVDb Results'
        if not titles and runlevel == 1:
            text = self.name.replace(' ', '%20')
            text = text + 'FIN'
            text = sub('[Ss][0-9]+[Ee][0-9]+.*?FIN', '', text)
            text = sub('FIN', '', text)
            self.transrenew = 'tvdb'
            self.translateRenewGoogle(text)
        elif not titles and runlevel == 2:
            self.session.open(MessageBox, _('\nNo TheTVDb Results for %s.') % self.name, MessageBox.TYPE_INFO)
        else:
            self.session.openWithCallback(self.makeTVDbUpdate, moviesList, titel, rating, year, titles, poster, id, country)

    def makeTMDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'tmdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://api.themoviedb.org/3/movie/%s?api_key=dfc629f7ff6936a269f8c5cdb194c890' % id + self.language
        self.getTMDbData(url, 1, id, True)

    def makeTVDbUpdate(self, id):
        self.renew = True
        self.firstdatabase = 'tvdb'
        self.dbcount = 1
        self.dbcountmax = 1
        self.infolist = []
        self.plotlist = []
        self.backdroplist = []
        self.posterlist = []
        url = 'http://www.thetvdb.com/data/series/' + id + '/' + config.plugins.moviebrowser.language.value + '.xml'
        self.getTVDbData(url, 1, id)

    def translateRenewGoogle(self, text):
        if config.plugins.moviebrowser.language.value == 'de':
            url = 'http://translate.google.com/m?hl=en&sl=de&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'es':
            url = 'http://translate.google.com/m?hl=en&sl=es&q=%s' % text.title()
        elif config.plugins.moviebrowser.language.value == 'ru':
            url = 'http://translate.google.com/m?hl=en&sl=ru&q=%s' % text.title()
        else:
            url = 'http://translate.google.com/m?hl=en&sl=en&q=%s' % text.title()
        agents = {'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)'}
        before_trans = 'class="t0">'
        request = Request(url, headers=agents)
        try:
            output = urlopen(request).read()
            data = output[output.find(before_trans) + len(before_trans):]
            movie = data.split('<')[0]
            print '%s >> %s' % (text, movie)
        except URLError:
            movie = text
        except HTTPError:
            movie = text
        except socket.error:
            movie = text

        if self.transrenew == 'imdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://imdbapi.org/?title=%s&type=xml&plot=full&episode=0&limit=10&yg=0&mt=none&lang=en-US&offset=&aka=simple&release=simple&business=0&tech=0' % movie
            self.getIMDbMovies(url, 2)
        elif self.transrenew == 'tmdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('-', '+').replace('_', '+')
            url = 'http://api.themoviedb.org/3/search/movie?api_key=dfc629f7ff6936a269f8c5cdb194c890&query=' + movie + self.language
            self.getTMDbMovies(url, 2)
        elif self.transrenew == 'tvdb':
            movie = movie.replace(' ', '+').replace(':', '+').replace('_', '+')
            url = 'http://www.thetvdb.com/api/GetSeries.php?seriesname=' + movie
            self.getTVDbMovies(url, 2)

    def deleteMovie(self):
        if self.ready == True:
            try:
                name = self.namelist[self.index]
                self.session.openWithCallback(self.delete_return, MessageBox, _('\nDo you really want to delete %s?') % name, MessageBox.TYPE_YESNO)
            except IndexError:
                pass

    def delete_return(self, answer):
        if answer is True:
            try:
                movie = self.movielist[self.index]
                if fileExists(movie):
                    os.remove(movie)
                if search('[.]ts', movie) is not None:
                    eitfile = sub('[.]ts', '.eit', movie)
                    if fileExists(eitfile):
                        os.remove(eitfile)
                    if fileExists(movie + '.ap'):
                        os.remove(movie + '.ap')
                    if fileExists(movie + '.cuts'):
                        os.remove(movie + '.cuts')
                    if fileExists(movie + '.meta'):
                        os.remove(movie + '.meta')
                    if fileExists(movie + '.sc'):
                        os.remove(movie + '.sc')
                    if fileExists(movie + '_mp.jpg'):
                        os.remove(movie + '_mp.jpg')
                movie = sub('\\(', '.', movie)
                movie = sub('\\)', '.', movie)
                data = open(self.database).read()
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        data = data.replace(line + '\n', '')

                f = open(self.database, 'w')
                f.write(data)
                f.close()
                if self.index == self.maxentry - 1:
                    self.index = 0
                    self.oldindex = self.wallindex
                    self.wallindex = 0
                    self.pagecount = 1
                self.makeMovies(self.filter)
            except IndexError:
                pass

        else:
            self.blacklistMovie()

    def blacklistMovie(self):
        if self.ready == True:
            try:
                name = self.namelist[self.index]
                self.session.openWithCallback(self.blacklist_return, MessageBox, _('\nDo you really want to blacklist %s?') % name, MessageBox.TYPE_YESNO)
            except IndexError:
                pass

    def blacklist_return(self, answer):
        if answer is True:
            self.ready = False
            try:
                movie = self.movielist[self.index]
                movie = sub('\\(', '.', movie)
                movie = sub('\\)', '.', movie)
                if fileExists(self.blacklist):
                    fremove = open(self.blacklist, 'a')
                else:
                    open(self.blacklist, 'w').close()
                    fremove = open(self.blacklist, 'a')
                data = open(self.database).read()
                for line in data.split('\n'):
                    if search(movie, line) is not None:
                        fremove.write(line + '\n')
                        fremove.close()
                        data = data.replace(line + '\n', '')

                f = open(self.database, 'w')
                f.write(data)
                f.close()
                if self.index == self.maxentry - 1:
                    self.index = 0
                    self.oldindex = self.wallindex
                    self.wallindex = 0
                    self.pagecount = 1
                self.makeMovies(self.filter)
            except IndexError:
                pass

    def toggleBackdrops(self):
        if self.ready == True:
            if self.backdrops == True:
                self.backdrops = False
                self.hideBackdrops()
            else:
                self.backdrops = True
                try:
                    self.showBackdrops(self.index)
                except IndexError:
                    pass

    def hideBackdrops(self):
        backdrop = config.plugins.moviebrowser.cachefolder.value + '/default_backdrop.png'
        if fileExists(backdrop):
            if self.xd == False:
                Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
            else:
                Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
            if Backdrop != None:
                self['backdrop'].instance.setPixmap(Backdrop)
                self['backdrop'].show()

    def showBackdrops(self, index):
        try:
            backdropurl = self.backdroplist[index]
            backdrop = sub('http://cf2.imgobject.com/t/p/w1280', '', backdropurl)
            backdrop = sub('http://www.thetvdb.com/banners/fanart/original', '', backdrop)
            backdrop = config.plugins.moviebrowser.cachefolder.value + backdrop
            if config.plugins.moviebrowser.m1v.value == 'yes':
                backdrop_m1v = backdrop.replace('.jpg', '.m1v')
                if fileExists(backdrop_m1v):
                    self['backdrop'].hide()
                    os.system("/usr/bin/showiframe '%s'" % backdrop_m1v)
                elif fileExists(backdrop):
                    if self.xd == False:
                        Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
                    else:
                        Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
                    if Backdrop != None:
                        self['backdrop'].instance.setPixmap(Backdrop)
                        self['backdrop'].show()
                else:
                    getPage(backdropurl).addCallback(self.getBackdrop, backdrop, index).addErrback(self.downloadError)
            elif fileExists(backdrop):
                if self.xd == False:
                    Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
                else:
                    Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
                if Backdrop != None:
                    self['backdrop'].instance.setPixmap(Backdrop)
                    self['backdrop'].show()
            else:
                getPage(backdropurl).addCallback(self.getBackdrop, backdrop, index).addErrback(self.downloadError)
        except IndexError:
            self['backdrop'].hide()

    def getBackdrop(self, output, backdrop, index):
        f = open(backdrop, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            Backdrop = loadPic(backdrop, 1280, 720, 3, 0, 0, 1)
        else:
            Backdrop = loadPic(backdrop, 1024, 576, 3, 0, 0, 1)
        if Backdrop != None:
            self['backdrop'].instance.setPixmap(Backdrop)
            self['backdrop'].show()

    def makePoster(self, page):
        for x in range(self.posterALL):
            try:
                index = x + page * self.posterALL
                posterurl = self.posterlist[index]
                posterurl = sub('<episode>.*?<episode>', '', posterurl)
                poster = sub('http://cf2.imgobject.com/t/p/w154', '', posterurl)
                poster = sub('http://www.thetvdb.com/banners/_cache/posters', '', poster)
                poster = config.plugins.moviebrowser.cachefolder.value + poster
                if fileExists(poster):
                    if self.xd == False:
                        Poster = loadPic(poster, 133, 200, 3, 0, 0, 1)
                    else:
                        Poster = loadPic(poster, 106, 160, 3, 0, 0, 1)
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
            Poster = loadPic(poster, 133, 200, 3, 0, 0, 1)
        else:
            Poster = loadPic(poster, 106, 160, 3, 0, 0, 1)
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
            poster = sub('http://cf2.imgobject.com/t/p/w154', '', posterurl)
            poster = sub('http://www.thetvdb.com/banners/_cache/posters', '', poster)
            poster = sub('<episode>.*?<episode>', '', poster)
            poster = config.plugins.moviebrowser.cachefolder.value + poster
            if fileExists(poster):
                if self.xd == False:
                    Poster = loadPic(poster, 153, 220, 3, 0, 0, 1)
                else:
                    Poster = loadPic(poster, 126, 180, 3, 0, 0, 1)
                if Poster != None:
                    self['frame'].instance.setPixmap(Poster)
        except IndexError:
            pass

    def makeEPoster(self):
        try:
            posterurl = self.posterlist[self.index]
            if search('<episode>', posterurl) is not None:
                eposterurl = search('<episode>(.*?)<episode>', posterurl)
                eposterurl = eposterurl.group(1)
                eposter = sub('.*?[/]', '', eposterurl)
                eposter = config.plugins.moviebrowser.cachefolder.value + '/' + eposter
                if fileExists(eposter):
                    if self.xd == False:
                        ePoster = loadPic(eposter, 500, 375, 3, 0, 0, 0)
                    else:
                        ePoster = loadPic(eposter, 440, 330, 3, 0, 0, 0)
                    if ePoster != None:
                        self['2name'].hide()
                        self['2genres'].hide()
                        self['eposter'].instance.setPixmap(ePoster)
                        self['eposter'].show()
                else:
                    getPage(eposterurl).addCallback(self.getEPoster, eposter).addErrback(self.downloadError)
            else:
                self['eposter'].hide()
        except IndexError:
            pass

    def getEPoster(self, output, eposter):
        f = open(eposter, 'wb')
        f.write(output)
        f.close()
        if self.xd == False:
            ePoster = loadPic(eposter, 500, 375, 3, 0, 0, 0)
        else:
            ePoster = loadPic(eposter, 440, 330, 3, 0, 0, 0)
        if ePoster != None:
            self['2name'].hide()
            self['2genres'].hide()
            self['eposter'].instance.setPixmap(ePoster)
            self['eposter'].show()

    def makeName(self, count):
        try:
            name = self.namelist[count]
            if self.xd == True:
                if len(name) > 64:
                    if name[63:64] == ' ':
                        name = name[0:63]
                    else:
                        name = name[0:64] + 'FIN'
                        name = sub(' \\S+FIN', '', name)
                    name = name + '...'
            elif len(name) > 137:
                if name[136:137] == ' ':
                    name = name[0:136]
                else:
                    name = name[0:137] + 'FIN'
                    name = sub(' \\S+FIN', '', name)
                name = name + '...'
            self['name'].setText(name)
            self['name'].show()
        except IndexError:
            self['name'].hide()

    def makeInfo(self, count):
        try:
            runtime = '(' + self.infolist[count][0] + ')'
            self['runtime'].setText(runtime)
            self['runtime'].show()
        except IndexError:
            self['runtime'].hide()

        try:
            ratings = self.infolist[count][1]
            try:
                rating = int(10 * round(float(ratings), 1))
            except ValueError:
                ratings = '0.0'
                rating = int(10 * round(float(ratings), 1))

            self['ratings'].setValue(rating)
            self['ratings'].show()
            self['ratingsback'].show()
            self['ratingtext'].setText(ratings)
        except IndexError:
            self['ratings'].hide()

        try:
            year = self.infolist[count][5]
            self['year'].setText(year)
            self['year'].show()
        except IndexError:
            self['year'].hide()

        try:
            country = self.infolist[count][6]
            self['country'].setText(country)
            self['country'].show()
        except IndexError:
            self['country'].hide()

    def toggleInfoFull(self):
        if self.ready == True:
            if self.showplotfull == False:
                if self.infofull == False and self.plotfull == False:
                    self.infofull = True
                    try:
                        self.showInfoFull(self.index)
                    except IndexError:
                        pass

                elif self.infofull == True and self.plotfull == False:
                    self.infofull = True
                    self.plotfull = True
                    try:
                        self.showPlotFull(self.index)
                    except IndexError:
                        pass

                elif self.infofull == True and self.plotfull == True:
                    self.infofull = False
                    self.plotfull = False
                    self.hideInfoFull()
                    self.hidePlotFull()
            elif self.plotfull == False:
                self.infofull = True
                self.plotfull = True
                try:
                    self.showInfoFull(self.index)
                    self.showPlotFull(self.index)
                except IndexError:
                    pass

            elif self.plotfull == True:
                self.infofull = False
                self.plotfull = False
                self.hideInfoFull()
                self.hidePlotFull()

    def showInfoFull(self, count):
        if self.xd == False:
            InfoFull = loadPic(self.infoBackPNG, 525, 430, 3, 0, 0, 1)
        else:
            InfoFull = loadPic(self.infoBackPNG, 460, 400, 3, 0, 0, 1)
        if InfoFull != None:
            self['2infoback'].instance.setPixmap(InfoFull)
            self['2infoback'].show()
        try:
            name = self.namelist[count]
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
            self['2name'].setText(name)
            self['2name'].show()
        except IndexError:
            self['2name'].hide()

        try:
            runtime = self.infolist[count][0]
            self['2runtime'].setText(runtime)
            self['2runtime'].show()
            self['2Runtime'].setText('Runtime:')
            self['2Runtime'].show()
        except IndexError:
            self['2runtime'].hide()
            self['2Runtime'].hide()

        try:
            ratings = self.infolist[count][1]
            try:
                rating = int(10 * round(float(ratings), 1))
            except ValueError:
                ratings = '0.0'
                rating = int(10 * round(float(ratings), 1))

            self['2ratings'].setValue(rating)
            self['2ratings'].show()
            self['2ratingsback'].show()
            self['2ratingtext'].setText(ratings)
            self['2ratingtext'].show()
            self['2Rating'].setText('Rating:')
            self['2Rating'].show()
        except IndexError:
            self['2ratings'].hide()
            self['2ratingsback'].hide()
            self['2ratingtext'].hide()
            self['2Rating'].hide()

        try:
            director = self.infolist[count][2]
            self['2director'].setText(director)
            self['2director'].show()
            self['2Director'].setText('Director:')
            self['2Director'].show()
        except IndexError:
            self['2director'].hide()
            self['2Director'].hide()

        try:
            actors = self.infolist[count][3]
            self['2actors'].setText(actors)
            self['2actors'].show()
            self['2Actors'].setText('Actors:')
            self['2Actors'].show()
        except IndexError:
            self['2actors'].hide()
            self['2Actors'].hide()

        try:
            genres = self.infolist[count][4]
            self['2genres'].setText(genres)
            self['2genres'].show()
            self['2Genres'].setText('Genres:')
            self['2Genres'].show()
        except IndexError:
            self['2genres'].hide()
            self['2Genres'].hide()

        try:
            year = self.infolist[count][5]
            self['2year'].setText(year)
            self['2year'].show()
            self['2Year'].setText('Year:')
            self['2Year'].show()
        except IndexError:
            self['2year'].hide()
            self['2Year'].hide()

        try:
            country = self.infolist[count][6]
            self['2country'].setText(country)
            self['2country'].show()
            self['2Country'].setText('Country:')
            self['2Country'].show()
        except IndexError:
            self['2country'].hide()
            self['2Country'].hide()

    def hideInfoFull(self):
        self['2name'].hide()
        self['2runtime'].hide()
        self['2Runtime'].hide()
        self['2ratings'].hide()
        self['2ratingsback'].hide()
        self['2ratingtext'].hide()
        self['2Rating'].hide()
        self['2director'].hide()
        self['2Director'].hide()
        self['2actors'].hide()
        self['2Actors'].hide()
        self['2genres'].hide()
        self['2Genres'].hide()
        self['2year'].hide()
        self['2Year'].hide()
        self['2country'].hide()
        self['2Country'].hide()
        self['2infoback'].hide()

    def showPlotFull(self, index):
        if self.xd == False:
            PlotFull = loadPic(self.infoBackPNG, 525, 430, 3, 0, 0, 1)
        else:
            PlotFull = loadPic(self.infoBackPNG, 460, 400, 3, 0, 0, 1)
        if PlotFull != None:
            self['plotfullback'].instance.setPixmap(PlotFull)
            self['plotfullback'].show()
        try:
            plot = self.plotlist[self.index]
            self['plotfull'].setText(plot)
            self['plotfull'].show()
            self.makeEPoster()
        except IndexError:
            self['plotfull'].hide()
            self['eposter'].hide()

    def hidePlotFull(self):
        self['eposter'].hide()
        self['plotfull'].hide()
        self['plotfullback'].hide()

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
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                if self.infofull == True:
                    self.showInfoFull(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
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
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                if self.infofull == True:
                    self.showInfoFull(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
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
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                if self.infofull == True:
                    self.showInfoFull(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
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
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                if self.infofull == True:
                    self.showInfoFull(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
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
                if self.backdrops == True:
                    self.showBackdrops(self.index)
                if self.infofull == True:
                    self.showInfoFull(self.index)
                if self.plotfull == True:
                    self.showPlotFull(self.index)
                self.makeName(self.index)
                self.makeInfo(self.index)
            except IndexError:
                pass

    def showMovies(self):
        if self.ready == True:
            movies = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line and self.filter in line:
                        movieline = line.split(':::')
                        try:
                            movie = movieline[0]
                        except IndexError:
                            movie = ' '

                        if movie != ' ':
                            movies = movies + movie + ':::'

                self.movies = [ i for i in movies.split(':::') ]
                self.movies.pop()
                self.session.openWithCallback(self.gotoMovie, allMovieList, self.movies, self.index, self.content)

    def gotoMovie(self, index):
        self.index = index
        self.oldindex = self.wallindex
        self.wallindex = self.index % self.posterALL
        self.pagecount = self.index // self.posterALL + 1
        self.makePoster(self.pagecount - 1)
        self.paintFrame()
        try:
            if self.backdrops == True:
                self.showBackdrops(self.index)
            if self.infofull == True:
                self.showInfoFull(self.index)
            if self.plotfull == True:
                self.showPlotFull(self.index)
            self.makeName(self.index)
            self.makeInfo(self.index)
        except IndexError:
            pass

    def filterGenre(self):
        if self.ready == True:
            genres = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            genre = movieline[7]
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
                self.session.openWithCallback(self.makeMovies, filterList, self.genres, 'Genre Filter')

    def filterActor(self):
        if self.ready == True:
            actors = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            actor = movieline[6]
                        except IndexError:
                            actor = ' '

                        if actor != ' ':
                            actors = actors + actor + ', '

                self.actors = [ i for i in actors.split(', ') ]
                self.actors.sort()
                self.actors.pop(0)
                try:
                    last = self.actors[-1]
                    for i in range(len(self.actors) - 2, -1, -1):
                        if last == self.actors[i]:
                            del self.actors[i]
                        else:
                            last = self.actors[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.session.openWithCallback(self.makeMovies, filterList, self.actors, 'Actor Filter')

    def filterDirector(self):
        if self.ready == True:
            directors = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            director = movieline[5]
                        except IndexError:
                            director = ' '

                        if director != ' ':
                            directors = directors + director + ', '

                self.directors = [ i for i in directors.split(', ') ]
                self.directors.sort()
                self.directors.pop(0)
                try:
                    last = self.directors[-1]
                    for i in range(len(self.directors) - 2, -1, -1):
                        if last == self.directors[i]:
                            del self.directors[i]
                        else:
                            last = self.directors[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.session.openWithCallback(self.makeMovies, filterList, self.directors, 'Director Filter')

    def filterSeasons(self):
        if self.ready == True:
            self.content = ':::Series:::'
            seasons = ''
            if fileExists(self.database):
                f = open(self.database, 'r')
                for line in f:
                    if self.content in line:
                        movieline = line.split(':::')
                        try:
                            season = movieline[0]
                            season = season + 'FIN'
                            season = sub('[(]S', 'Season ', season)
                            season = sub('[(]s', 'season ', season)
                            season = sub('[Ee][0-9]+[)].*?FIN', '', season)
                            season = sub('FIN', '', season)
                        except IndexError:
                            season = ' '

                        if season != ' ':
                            seasons = seasons + season + ', '

                self.seasons = [ i for i in seasons.split(', ') ]
                self.seasons.sort()
                self.seasons.pop(0)
                try:
                    last = self.seasons[-1]
                    for i in range(len(self.seasons) - 2, -1, -1):
                        if last == self.seasons[i]:
                            del self.seasons[i]
                        else:
                            last = self.seasons[i]

                except IndexError:
                    pass

                self.index = 0
                self.wallindex = 0
                if self.xd == True:
                    self.posterindex = 5
                else:
                    self.posterindex = 6
                self.session.openWithCallback(self.makeMovies, filterSeasonList, self.seasons)

    def sortDatabase(self):
        self.sortorder = config.plugins.moviebrowser.sortorder.value
        f = open(self.database, 'r')
        lines = f.readlines()
        f.close()
        if self.sortorder == 'name':
            lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
        elif self.sortorder == 'name_reverse':
            lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
        elif self.sortorder == 'rating':
            lines.sort(key=lambda line: line.split(':::')[4])
        elif self.sortorder == 'rating_reverse':
            lines.sort(key=lambda line: line.split(':::')[4], reverse=True)
        elif self.sortorder == 'year':
            lines.sort(key=lambda line: line.split(':::')[8])
        elif self.sortorder == 'year_reverse':
            lines.sort(key=lambda line: line.split(':::')[8], reverse=True)
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

    def switchView(self):
        if self.ready == True:
            self.session.openWithCallback(self.exit, movieBrowserBackdrop, self.index, self.content, self.filter)

    def toogleContent(self):
        if self.ready == True:
            if self.content == ':::Movie:::' or self.content == ':::':
                self.content = ':::Series:::'
                self.filter = ':::Series:::'
                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.makeMovies(self.filter)
            else:
                self.content = ':::Movie:::'
                self.filter = ':::Movie:::'
                self.index = 0
                self.wallindex = 0
                self.pagecount = 1
                self.oldindex = 0
                self.pagemax = 1
                self.makeMovies(self.filter)

    def editDatabase(self):
        if self.ready == True:
            self.session.openWithCallback(self.makeMovies, movieDatabase)

    def wikipedia(self):
        if self.ready == True:
            if fileExists('/usr/lib/enigma2/python/Plugins/Extensions/Wikipedia/plugin.pyo'):
                self.session.open(searchWikipedia, self.namelist[self.index], self.infolist[self.index][2], self.infolist[self.index][3])
            else:
                self.session.open(MessageBox, _('\nThe Wikipedia plugin could not be found.\n\nPlease download and install the plugin from:\nwww.kashmir-plugins.de'), MessageBox.TYPE_INFO)
                return

    def showPath(self):
        if self.ready == True:
            self.session.open(MessageBox, _('\nMovie File:\n%s') % self.movielist[self.index], MessageBox.TYPE_INFO)

    def getIndex(self, list):
        return list.getSelectedIndex()

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def config(self):
        if self.ready == True:
            self.session.openWithCallback(self.exit, movieBrowserConfig)

    def zap(self):
        if self.ready == True:
            servicelist = self.session.instantiateDialog(ChannelSelection)
            self.session.execDialog(servicelist)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            if config.plugins.moviebrowser.m1v.value == 'yes':
                while count > 0:
                    count -= 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.plugins.moviebrowser.transparency.value * count / 40))
                    f.close()

            else:
                while count > 0:
                    count -= 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.av.osd_alpha.value * count / 40))
                    f.close()

        else:
            self.hideflag = True
            count = 0
            if config.plugins.moviebrowser.m1v.value == 'yes':
                while count < 40:
                    count += 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.plugins.moviebrowser.transparency.value * count / 40))
                    f.close()

            else:
                while count < 40:
                    count += 1
                    f = open('/proc/stb/video/alpha', 'w')
                    f.write('%i' % (config.av.osd_alpha.value * count / 40))
                    f.close()

    def exit(self):
        if config.plugins.moviebrowser.showtv.value == 'hide' or config.plugins.moviebrowser.m1v.value == 'yes':
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
            self.session.nav.playService(self.oldService)
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        self.close()


class movieDatabase(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,523" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<widget name="list2" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'green': self.infoScreen,
         #'blue': self.hideScreen,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/database'
        self.onLayoutFinish.append(self.makeList)

    def makeList(self):
        self.namelist = []
        self.datelist = []
        self.runtimelist = []
        self.ratinglist = []
        self.directorlist = []
        self.actorslist = []
        self.genreslist = []
        self.yearlist = []
        self.countrylist = []
        self.posterlist = []
        self.backdroplist = []
        self.list = []
        if fileExists(self.database):
            f = open(self.database, 'r')
            for line in f:
                movieline = line.split(':::')
                try:
                    name = movieline[0]
                except IndexError:
                    name = ' '

                try:
                    date = movieline[2]
                except IndexError:
                    date = ' '

                try:
                    runtime = movieline[3]
                except IndexError:
                    runtime = ' '

                try:
                    rating = movieline[4]
                except IndexError:
                    rating = ' '

                try:
                    director = movieline[5]
                except IndexError:
                    director = ' '

                try:
                    actors = movieline[6]
                except IndexError:
                    actors = ' '

                try:
                    genres = movieline[7]
                except IndexError:
                    genres = ' '

                try:
                    year = movieline[8]
                except IndexError:
                    year = ' '

                try:
                    country = movieline[9]
                except IndexError:
                    country = ' '

                try:
                    poster = movieline[11]
                except IndexError:
                    poster = 'http://cf2.imgobject.com/t/p/w154' + '/default_poster.png'

                try:
                    backdrop = movieline[12]
                except IndexError:
                    backdrop = 'http://cf2.imgobject.com/t/p/w1280' + '/default_backdrop.png'

                self.namelist.append(name)
                self.datelist.append(date)
                self.runtimelist.append(runtime)
                self.ratinglist.append(rating)
                self.directorlist.append(director)
                self.actorslist.append(actors)
                self.genreslist.append(genres)
                self.yearlist.append(year)
                self.countrylist.append(country)
                self.posterlist.append(poster)
                self.backdroplist.append(backdrop)
                self.list.append(name)
                self['list'].l.setList(self.list)
                self['list'].moveToIndex(self.index)
                self.selectList()
                self.ready = True
                totalMovies = len(self.list)
                if os.path.exists(config.plugins.moviebrowser.moviefolder.value):
                    movieFolder = os.statvfs(config.plugins.moviebrowser.moviefolder.value)
                    freeSize = movieFolder[statvfs.F_BSIZE] * movieFolder[statvfs.F_BFREE] / 1024 / 1024 / 1024
                    title = 'Database Editor: %s Movies (Movie Folder: %s GB free)' % (str(totalMovies), str(freeSize))
                    self.setTitle(title)
                else:
                    title = 'Database Editor: %s Movies (Movie Folder: offline)' % str(totalMovies)
                    self.setTitle(title)

    def makeList2(self):
        self.list2 = []
        self.list2.append('Movie: ' + self.namelist[self.index])
        self.list2.append('Rating: ' + self.ratinglist[self.index])
        self.list2.append('Director: ' + self.directorlist[self.index])
        self.list2.append('Country: ' + self.countrylist[self.index])
        self.list2.append('Actors: ' + self.actorslist[self.index])
        self.list2.append('Year: ' + self.yearlist[self.index])
        self.list2.append('Runtime: ' + self.runtimelist[self.index])
        self.list2.append('Genres: ' + self.genreslist[self.index])
        self.list2.append('Poster: ' + self.posterlist[self.index])
        self.list2.append('Backdrop: ' + self.backdroplist[self.index])
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
                    self.data = self.namelist[self.index]
                elif index == 1:
                    self.data = self.ratinglist[self.index]
                elif index == 2:
                    self.data = self.directorlist[self.index]
                elif index == 3:
                    self.data = self.countrylist[self.index]
                elif index == 4:
                    self.data = self.actorslist[self.index]
                elif index == 5:
                    self.data = self.yearlist[self.index]
                elif index == 6:
                    self.data = self.runtimelist[self.index]
                elif index == 7:
                    self.data = self.genreslist[self.index]
                elif index == 8:
                    self.data = self.posterlist[self.index]
                elif index == 9:
                    self.data = self.backdroplist[self.index]
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

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        if self.actlist == 'list':
            self.close(':::')
        elif self.actlist == 'list2':
            self.selectList()


class moviesList(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,538" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="poster1" position="10,33" size="80,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster2" position="10,158" size="80,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster3" position="10,283" size="80,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="poster4" position="10,408" size="80,120" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="list" position="100,33" size="620,500" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, titel, rating, year, titles, poster, id, country):
        Screen.__init__(self, session)
        self.titel = titel
        self.rating = rating
        self.year = year
        self.titles = titles
        self.poster = poster
        self.id = id
        self.country = country
        self.movielist = []
        self.poster1 = '/tmp/moviebrowser1.jpg'
        self.poster2 = '/tmp/moviebrowser2.jpg'
        self.poster3 = '/tmp/moviebrowser3.jpg'
        self.poster4 = '/tmp/moviebrowser4.jpg'
        self['poster1'] = Pixmap()
        self['poster2'] = Pixmap()
        self['poster3'] = Pixmap()
        self['poster4'] = Pixmap()
        self.ready = False
        self.hideflag = True
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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'blue': self.hideScreen,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
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

        for x in range(len(self.titles)):
            res = ['']
            try:
                res.append(MultiContentEntryText(pos=(5, 13), size=(610, 30), font=24, color=16777215, color_sel=16777215, flags=RT_HALIGN_LEFT, text=self.titles[x]))
            except IndexError:
                pass

            try:
                res.append(MultiContentEntryText(pos=(5, 48), size=(50, 25), font=20, color=16777215, color_sel=16777215, flags=RT_HALIGN_LEFT, text=self.year[x]))
            except IndexError:
                pass

            try:
                res.append(MultiContentEntryText(pos=(55, 48), size=(560, 25), font=20, color=16777215, color_sel=16777215, flags=RT_HALIGN_LEFT, text=self.country[x]))
            except IndexError:
                pass

            try:
                rating = int(10 * round(float(self.rating[x]), 1)) * 2 + int(10 * round(float(self.rating[x]), 1)) // 10
            except IndexError:
                rating = 0

            png = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings_back.png'
            if fileExists(png):
                res.append(MultiContentEntryPixmapAlphaTest(pos=(5, 84), size=(210, 21), png=loadPNG(png)))
            png2 = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/ratings.png'
            if fileExists(png2):
                res.append(MultiContentEntryPixmapAlphaTest(pos=(5, 84), size=(rating, 21), png=loadPNG(png2)))
            try:
                res.append(MultiContentEntryText(pos=(225, 84), size=(50, 25), font=20, color=16777215, color_sel=16777215, flags=RT_HALIGN_LEFT, text=self.rating[x]))
            except IndexError:
                pass

            self.movielist.append(res)

        self['list'].l.setList(self.movielist)
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
            current = self.id[c]
            self.close(current)

    def down(self):
        if self.ready == True:
            try:
                c = self['list'].getSelectedIndex()
            except IndexError:
                pass

            self['list'].down()
            if c + 1 == len(self.titles):
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
                l = len(self.titles)
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
            l = len(self.titles)
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
            end = len(self.titles) - 1
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
        currPic = loadPic(poster1, 80, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster1'].instance.setPixmap(currPic)

    def getPoster2(self, output):
        f = open(self.poster2, 'wb')
        f.write(output)
        f.close()
        self.showPoster2(self.poster2)

    def showPoster2(self, poster2):
        currPic = loadPic(poster2, 80, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster2'].instance.setPixmap(currPic)

    def getPoster3(self, output):
        f = open(self.poster3, 'wb')
        f.write(output)
        f.close()
        self.showPoster3(self.poster3)

    def showPoster3(self, poster3):
        currPic = loadPic(poster3, 80, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster3'].instance.setPixmap(currPic)

    def getPoster4(self, output):
        f = open(self.poster4, 'wb')
        f.write(output)
        f.close()
        self.showPoster4(self.poster4)

    def showPoster4(self, poster4):
        currPic = loadPic(poster4, 80, 120, 3, 0, 0, 1)
        if currPic != None:
            self['poster4'].instance.setPixmap(currPic)

    def download(self, link, name):
        getPage(link).addCallback(name).addErrback(self.downloadError)

    def downloadError(self, output):
        pass

    def zap(self):
        servicelist = self.session.instantiateDialog(ChannelSelection)
        self.session.execDialog(servicelist)

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        if fileExists(self.poster1):
            os.remove(self.poster1)
        if fileExists(self.poster2):
            os.remove(self.poster2)
        if fileExists(self.poster3):
            os.remove(self.poster3)
        if fileExists(self.poster4):
            os.remove(self.poster4)
        c = self['list'].getSelectedIndex()
        current = self.id[c]
        self.close(current)


class filterList(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="270,523" title=" ">\n\t\t\t\t<ePixmap position="-230,0" size="500,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="250,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'green': self.infoScreen,
         #'blue': self.hideScreen,
         '7': self.resetFilter,
         '8': self.resetFilter,
         '9': self.resetFilter,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self['list'].l.setList(self.list)

    def ok(self):
        current = self['list'].getCurrent()
        self.close(current)

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

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        self.close(':::')


class filterSeasonList(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="530,523" title=" ">\n\t\t\t\t<ePixmap position="-100,0" size="630,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="510,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, list):
        Screen.__init__(self, session)
        self.list = list
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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'green': self.infoScreen,
         #'blue': self.hideScreen,
         '4': self.resetFilter,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self['list'].l.setList(self.list)
        totalSeasons = len(self.list)
        if os.path.exists(config.plugins.moviebrowser.moviefolder.value):
            movieFolder = os.statvfs(config.plugins.moviebrowser.moviefolder.value)
            freeSize = movieFolder[statvfs.F_BSIZE] * movieFolder[statvfs.F_BFREE] / 1024 / 1024 / 1024
            title = '%s Series Seasons (Movie Folder: %s GB free)' % (str(totalSeasons), str(freeSize))
            self.setTitle(title)
        else:
            title = '%s Series Seasons (Movie Folder: offline)' % str(totalSeasons)
            self.setTitle(title)

    def ok(self):
        current = self['list'].getCurrent()
        current = sub('Season ', '(S', current)
        current = sub('season ', '(s', current)
        self.close(current)

    def resetFilter(self):
        self.close(':::Series:::')

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

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        self.close(':::Series:::')


class allMovieList(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="730,523" title=" ">\n\t\t\t\t<ePixmap position="0,0" size="730,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,38" size="710,475" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, list, index, content):
        Screen.__init__(self, session)
        self.list = list
        self.index = index
        self.content = content
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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'green': self.infoScreen,
         #'blue': self.hideScreen,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self['list'].l.setList(self.list)
        try:
            self['list'].moveToIndex(self.index)
        except IndexError:
            pass

        totalMovies = len(self.list)
        if os.path.exists(config.plugins.moviebrowser.moviefolder.value):
            movieFolder = os.statvfs(config.plugins.moviebrowser.moviefolder.value)
            freeSize = movieFolder[statvfs.F_BSIZE] * movieFolder[statvfs.F_BFREE] / 1024 / 1024 / 1024
            if self.content == ':::Movie:::':
                title = '%s Movies (Movie Folder: %s GB free)' % (str(totalMovies), str(freeSize))
            elif self.content == ':::Series:::':
                title = '%s Series (Movie Folder: %s GB free)' % (str(totalMovies), str(freeSize))
            else:
                title = '%s Movies & Series (Movie Folder: %s GB free)' % (str(totalMovies), str(freeSize))
            self.setTitle(title)
        else:
            if self.content == ':::Movie:::':
                title = '%s Movies (Movie Folder: offline)' % str(totalMovies)
            elif self.content == ':::Series:::':
                title = '%s Series (Movie Folder: offline)' % str(totalMovies)
            else:
                title = '%s Movies & Series (Movie Folder: offline)' % str(totalMovies)
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

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        index = self['list'].getSelectedIndex()
        self.close(index)


class searchWikipedia(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="550,295" title="Wikipedia - Search for Movie, Director or Actor">\n\t\t\t\t<ePixmap position="0,0" size="550,50" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/Wikipedia/pic/wiki.png" zPosition="1"/>\n\t\t\t\t<widget name="list" position="10,60" size="530,225" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session, movie, director, actors):
        Screen.__init__(self, session)
        self.hideflag = True
        self.movie = movie
        self.director = director
        self.actors = actors
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
         #'red': self.infoScreen,
         #'yellow': self.infoScreen,
         #'green': self.infoScreen,
         #'blue': self.hideScreen,
         '0': self.gotoEnd,
         #'displayHelp': self.infoScreen
         }, -1)
        self.onLayoutFinish.append(self.onLayoutFinished)

    def onLayoutFinished(self):
        self.list.append('Movie: ' + self.movie)
        self.list.append('Director: ' + self.director)
        self.actor = [ i for i in self.actors.split(', ') ]
        idx = 0
        for x in self.actor:
            idx += 1

        for i in range(idx):
            self.list.append('Actor: ' + self.actor[i])

        self['list'].l.setList(self.list)

    def ok(self):
        index = self['list'].getSelectedIndex()
        if index == 0:
            name = self.movie
        elif index == 1:
            name = self.director
        elif index == 2:
            name = self.actor[0]
        elif index == 3:
            name = self.actor[1]
        elif index == 4:
            name = self.actor[2]
        elif index == 5:
            name = self.actor[3]
        elif index == 6:
            name = self.actor[4]
        elif index == 7:
            name = self.actor[5]
        elif index == 8:
            name = self.actor[6]

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

    def hideScreen(self):
        if self.hideflag == True:
            self.hideflag = False
            count = 40
            while count > 0:
                count -= 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

        else:
            self.hideflag = True
            count = 0
            while count < 40:
                count += 1
                f = open('/proc/stb/video/alpha', 'w')
                f.write('%i' % (config.av.osd_alpha.value * count / 40))
                f.close()

    def exit(self):
        if self.hideflag == False:
            f = open('/proc/stb/video/alpha', 'w')
            f.write('%i' % config.av.osd_alpha.value)
            f.close()
        self.close()


class ItemList(MenuList):
    def __init__(self, items, enableWrapAround = True):
        MenuList.__init__(self, items, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(24, gFont('Regular', 24))
        self.l.setFont(22, gFont('Regular', 22))
        self.l.setFont(20, gFont('Regular', 20))

class movieBrowserConfig(ConfigListScreen, Screen):
    skin = '\n\t\t\t<screen position="center,center" size="530,500" backgroundColor="#20000000" title="Movie Browser Setup">\n\t\t\t\t<ePixmap position="-100,0" size="630,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="9,37" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<widget name="config" position="9,38" size="512,125" itemHeight="25" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<ePixmap position="9,164" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<eLabel position="150,173" size="125,20" font="Regular;18" halign="left" text="Save" transparent="1" zPosition="1" />\n\t\t\t\t<eLabel position="365,173" size="125,20" font="Regular;18" halign="left" text="Cancel" transparent="1" zPosition="1" />\n\t\t\t\t<ePixmap position="125,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/green.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="340,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/red.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="plugin" position="9,203" size="512,288" alphatest="blend" zPosition="1" />\n\t\t\t</screen>'

    def __init__(self, session):
        Screen.__init__(self, session)
        self['plugin'] = Pixmap()
        self.sortorder = config.plugins.moviebrowser.sortorder.value
        self.cachefolder = config.plugins.moviebrowser.cachefolder.value
        self.database = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/database'
        self.ready = True
        list = []
        list.append(getConfigListEntry(_('Plugin Style:'), config.plugins.moviebrowser.style))
        self.foldername = getConfigListEntry(_('Movie Folder:'), config.plugins.moviebrowser.moviefolder)
        list.append(self.foldername)
        #list.append(getConfigListEntry(_('Cache Folder:'), config.plugins.moviebrowser.cachefolder))
        list.append(getConfigListEntry(_('Default Database:'), config.plugins.moviebrowser.database))
        list.append(getConfigListEntry(_('TMDb/TheTVDb Language:'), config.plugins.moviebrowser.language))
        #list.append(getConfigListEntry(_('Plugin Size:'), config.plugins.moviebrowser.plugin_size))
        list.append(getConfigListEntry(_('Show Content:'), config.plugins.moviebrowser.filter))
        #list.append(getConfigListEntry(_('Show Backdrops:'), config.plugins.moviebrowser.backdrops))
        #list.append(getConfigListEntry(_('Show Plot Full:'), config.plugins.moviebrowser.plotfull))
        #list.append(getConfigListEntry(_('Plot Full Font Size:'), config.plugins.moviebrowser.plotfont))
        #list.append(getConfigListEntry(_('Headline Color:'), config.plugins.moviebrowser.color))
        list.append(getConfigListEntry(_('Sort Order:'), config.plugins.moviebrowser.sortorder))
        #list.append(getConfigListEntry(_('Support m1v Backdrops:'), config.plugins.moviebrowser.m1v))
        #list.append(getConfigListEntry(_('m1v Transparency:'), config.plugins.moviebrowser.transparency))
        #list.append(getConfigListEntry(_('Show TV on Plugin Start:'), config.plugins.moviebrowser.showtv))
        #list.append(getConfigListEntry(_('Show Plugin in Main Menu:'), config.plugins.moviebrowser.menu))
        list.append(getConfigListEntry(_('Reset Database:'), config.plugins.moviebrowser.reset))
        ConfigListScreen.__init__(self, list, on_change=self.UpdateComponents)
        self['key_red'] = Label(_('Cancel'))
        self['key_green'] = Label(_('Save'))          
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'ok': self.save,
         'cancel': self.cancel,
         'red': self.cancel,
         'green': self.save}, -1)
        self.onLayoutFinish.append(self.UpdateComponents)

    def UpdateComponents(self):
        png = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/' + config.plugins.moviebrowser.style.value + '.png'
        if fileExists(png):
            PNG = loadPic(png, 512, 288, 3, 0, 0, 1)
            if PNG != None:
                self['plugin'].instance.setPixmap(PNG)
        current = self['config'].getCurrent()
        if current == self.foldername:
            self.session.openWithCallback(self.folderSelected, FolderSelection, config.plugins.moviebrowser.moviefolder.value)

    def folderSelected(self, folder):
        if folder is not None:
            config.plugins.moviebrowser.moviefolder.value = folder
            config.plugins.moviebrowser.moviefolder.save()

    def save(self):
        if self.ready == True:
            self.ready = False
            if config.plugins.moviebrowser.sortorder.value != self.sortorder:
                if fileExists(self.database):
                    f = open(self.database, 'r')
                    lines = f.readlines()
                    f.close()
                    if config.plugins.moviebrowser.sortorder.value == 'name':
                        lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower())
                    elif config.plugins.moviebrowser.sortorder.value == 'name_reverse':
                        lines.sort(key=lambda line: line.split(':::')[0].replace('Der ', '').replace('Die ', '').replace('Das ', '').replace('The ', '').lower(), reverse=True)
                    elif config.plugins.moviebrowser.sortorder.value == 'rating':
                        lines.sort(key=lambda line: line.split(':::')[4])
                    elif config.plugins.moviebrowser.sortorder.value == 'rating_reverse':
                        lines.sort(key=lambda line: line.split(':::')[4], reverse=True)
                    elif config.plugins.moviebrowser.sortorder.value == 'year':
                        lines.sort(key=lambda line: line.split(':::')[8])
                    elif config.plugins.moviebrowser.sortorder.value == 'year_reverse':
                        lines.sort(key=lambda line: line.split(':::')[8], reverse=True)
                    elif config.plugins.moviebrowser.sortorder.value == 'date':
                        lines.sort(key=lambda line: line.split(':::')[2])
                    elif config.plugins.moviebrowser.sortorder.value == 'date_reverse':
                        lines.sort(key=lambda line: line.split(':::')[2], reverse=True)
                    elif config.plugins.moviebrowser.sortorder.value == 'folder':
                        lines.sort(key=lambda line: line.split(':::')[1])
                    elif config.plugins.moviebrowser.sortorder.value == 'folder_reverse':
                        lines.sort(key=lambda line: line.split(':::')[1], reverse=True)
                    fsorted = open(self.database + '.sorted', 'w')
                    fsorted.writelines(lines)
                    fsorted.close()
                    os.rename(self.database + '.sorted', self.database)
            if config.plugins.moviebrowser.reset.value == 'yes':
                if fileExists(self.database):
                    os.rename(self.database, self.database + '-backup')
                open('/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/db/reset', 'w').close()
                config.plugins.moviebrowser.reset.value = 'no'
                config.plugins.moviebrowser.reset.save()
            if config.plugins.moviebrowser.cachefolder.value != self.cachefolder:
                self.container = eConsoleAppContainer()
                self.container.appClosed.append(self.finished)
                newcache = sub('/cache', '', config.plugins.moviebrowser.cachefolder.value)
                self.container.execute("mkdir -p '%s' && cp -r '%s' '%s' && rm -rf '%s'" % (config.plugins.moviebrowser.cachefolder.value,
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
        if config.plugins.moviebrowser.style.value == 'backdrop':
            self.session.openWithCallback(self.close, movieBrowserBackdrop, 0, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)
        elif config.plugins.moviebrowser.style.value == 'posterwall':
            self.session.openWithCallback(self.close, movieBrowserPosterwall, 0, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)


class FolderSelection(Screen):
    skin = '\n\t\t\t<screen position="center,center" size="530,500" backgroundColor="#20000000" title="Movie Browser Setup">\n\t\t\t\t<ePixmap position="-100,0" size="630,28" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/logo.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="9,37" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<widget name="folderlist" position="9,38" size="512,125" itemHeight="25" scrollbarMode="showOnDemand" zPosition="1" />\n\t\t\t\t<ePixmap position="9,164" size="512,1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/seperator.png" alphatest="off" zPosition="1" />\n\t\t\t\t<eLabel position="150,173" size="125,20" font="Regular;18" halign="left" text="Save" transparent="1" zPosition="1" />\n\t\t\t\t<eLabel position="365,173" size="125,20" font="Regular;18" halign="left" text="Cancel" transparent="1" zPosition="1" />\n\t\t\t\t<ePixmap position="125,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/green.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<ePixmap position="340,174" size="18,18" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/red.png" alphatest="blend" zPosition="1" />\n\t\t\t\t<widget name="plugin" position="9,203" size="512,288" alphatest="blend" zPosition="1" />\n\t\t\t</screen>'

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
        png = '/usr/lib/enigma2/python/Plugins/Extensions/MovieBrowser/pic/' + config.plugins.moviebrowser.style.value + '.png'
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
    if config.plugins.moviebrowser.style.value == 'backdrop':
        session.open(movieBrowserBackdrop, 0, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)
    elif config.plugins.moviebrowser.style.value == 'posterwall':
        session.open(movieBrowserPosterwall, 0, config.plugins.moviebrowser.filter.value, config.plugins.moviebrowser.filter.value)


def menu(menuid, **kwargs):
    if menuid == 'mainmenu':
        return [(_('Movie Browser'),
          main,
          'moviebrowser',
          42)]
    return []


def Plugins(**kwargs):
        return []