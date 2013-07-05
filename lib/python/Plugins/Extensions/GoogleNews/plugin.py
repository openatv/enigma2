import urllib2
from Tools.Directories import fileExists
from urllib2 import URLError
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Input import Input
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.LoadPixmap import LoadPixmap
from xml.dom.minidom import parse, getDOMImplementation
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, loadPNG, eTimer, getDesktop
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
myname = 'Google News'

def main(session, **kwargs):
    session.open(GnewsFeedScreenList)


def autostart(reason, **kwargs):
    pass


def Plugins(**kwargs):
    return PluginDescriptor(name=myname, description='Google News', icon='gnews.png', where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main)


class GnewsFeedScreenList(Screen):
    global HD_Res
    try:
        sz_w = getDesktop(0).size().width()
        if sz_w > 1200:
            HD_Res = True
        else:
            HD_Res = False
    except:
        HD_Res = False

    if HD_Res == True:
        skin = '\n        \t\n                <screen  position="center,center" size="920,600" title="GoogleNews reader"  >\n                \n                <widget name="info" position="10,10" zPosition="4" size="900,55" font="Regular;22" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />\n                <ePixmap position="15,65" size="890,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                <widget name="mylist" position="20,70" size="880,511" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />\n\n\t\t\n\t\t\n\t\t\n      \n\n                        \n                \n                \n                </screen>'
    else:
        skin = '\n        \t\n         \n        \t\n                <screen  position="center,center" size="580,450" title="GoogleNews reader"   >\n                \n                <widget name="info" position="10,5" zPosition="4" size="560,30" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />\n                <ePixmap position="15,35" size="550,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                <widget name="mylist" position="10,40" size="560,399" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />\n\n\t\t\n\n\n                \n                </screen>'

    def __init__(self, session, args = 0):
        self.skin = GnewsFeedScreenList.skin
        self.session = session
        Screen.__init__(self, session)
        self.menu = args
        self.config = FeedreaderConfig()
        self['mylist'] = MenuList([], True, eListboxPythonMultiContent)
        self['mylist'].l.setItemHeight(56)
        self['mylist'].l.setFont(0, gFont('Regular', 22))
        self['info'] = Label('GoogleNews Reader')
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions', 'MenuActions'], {'ok': self.go,
         'back': self.close}, -1)
        self.timer = eTimer()
        self.timer.callback.append(self.getFeedList)
        self.timer.start(200, 1)
        self.onClose.append(self.cleanup)

    def cleanup(self):
        if self.config:
            self.config.cleanup()

    def go(self):
        try:
            i = 1
            i = self['mylist'].getSelectedIndex()
            feed = self.feedlist[i][1]
            if feed:
                self.showFeed(feed)
            else:
                print '[' + myname + '] section in config not found'
        except:
            self['info'].setText('sorry, no feeds available,try later')

    def showFeed(self, feed):
        try:
            self.session.open(GnewsFeedScreenContent, feed)
        except IOError as e:
            self['info'].setText('loading feeddata failed!')
        except:
            print 'no feed data'
            self['info'].setText('sorry feeds not available')

    def getFeedList(self):
        list = []
        feedlist = []
        try:
            for feed in self.config.getFeeds():
                res = []
                feedname = feed.getName()
                fedname = 'defualt'
                try:
                    a = []
                    a = feedname.split('-')
                    fedname = a[0]
                    fedname = fedname.strip()
                    fedname = fedname.lower()
                except:
                    fedname = 'defualt'

                pngfile = '/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/' + fedname + '.png'
                if fileExists(pngfile):
                    png = pngfile
                else:
                    png = '/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/default.png'
                res.append(MultiContentEntryText(pos=(0, 5), size=(5, 30), font=0, flags=RT_HALIGN_LEFT, text='', color=16777215, color_sel=16777215))
                #res.append(MultiContentEntryPixmapAlphaTest(pos=(0, 10), size=(70, 70), png=loadPNG(png)))
                res.append(MultiContentEntryText(pos=(120, 5), size=(500, 70), font=0, flags=RT_HALIGN_LEFT, text=feedname, color=10025880, color_sel=10025880))
                feedlist.append((feed.getName(), feed))
                list.append(res)
                res = []

            self.feedlist = feedlist
            self['mylist'].l.setList(list)
            self['mylist'].show()
        except:
            self['info'].setText('error in parsing feed xml')


class FeedreaderConfig:
    configfile = '/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/feeds.xml'

    def __init__(self):
        self.node = None
        self.feeds = []
        self.readConfig()

    def cleanup(self):
        if self.node:
            self.node.unlink()
            del self.node
            self.node = None
            self.feeds = []

    def readConfig(self):
        self.cleanup()
        try:
            self.node = parse(self.configfile)
        except:
            print 'Illegal xml file'
            print self.configfile
            return

        self.node = self.node.documentElement
        self.getFeeds()

    def writeConfig(self):
        impl = getDOMImplementation()
        newdoc = impl.createDocument(None, 'feeds', None)
        for feed in self.feeds:
            node = newdoc.createElement('feed')
            name = newdoc.createElement('name')
            name.appendChild(newdoc.createTextNode(feed.getName()))
            node.appendChild(name)
            url = newdoc.createElement('url')
            url.appendChild(newdoc.createTextNode(feed.getURL()))
            node.appendChild(url)
            if feed.getDescription():
                description = newdoc.createElement('description')
                description.appendChild(newdoc.createTextNode(feed.getDescription()))
                node.appendChild(description)
            newdoc.documentElement.appendChild(node)

        newdoc.writexml(file(self.configfile, 'w'))

    def getFeeds(self):
        if self.feeds:
            return self.feeds
        for node in self.node.getElementsByTagName('feed'):
            name = ''
            description = ''
            url = ''
            nodes = node.getElementsByTagName('name')
            if nodes and nodes[0].childNodes:
                name = str(nodes[0].childNodes[0].data)
            nodes = node.getElementsByTagName('description')
            if nodes and nodes[0].childNodes:
                description = str(nodes[0].childNodes[0].data)
            nodes = node.getElementsByTagName('url')
            if nodes and nodes[0].childNodes:
                url = str(nodes[0].childNodes[0].data)
            self.feeds.append(Feed(name, description, url, True))

        return self.feeds

    def isFeed(self, feedname):
        for feed in self.feeds:
            if feed.getName() == feedname:
                return True

        return False

    def getFeedByName(self, feedname):
        for feed in self.feeds:
            if feed.getName() == feedname:
                return feed

    def getProxysettings(self):
        proxynodes = self.node.getElementsByTagName('proxy')
        for node in proxynodes:
            if self.node.getElementsByTagName('useproxy'):
                proxysettings = {}
                httpnodes = node.getElementsByTagName('http')
                if httpnodes and httpnodes[0].childNodes:
                    proxysettings['http'] = str(httpnodes[0].childNodes[0].data)
                ftpnodes = node.getElementsByTagName('ftp')
                if ftpnodes and ftpnodes[0].childNodes:
                    proxysettings['ftp'] = str(ftpnodes[0].childNodes[0].data)
                return proxysettings

    def addFeed(self, feed):
        if self.isFeed(feed.getName()):
            return (False, _('Feed already exists!'))
        feed.setFavorite()
        self.feeds.append(feed)
        self.writeConfig()
        return (True, _('Feed added'))

    def changeFeed(self, feedold, feednew):
        for index in range(0, len(self.feeds)):
            if self.feeds[index].getName() == feedold.getName():
                self.feeds[index] = feednew
                self.writeConfig()
                return (True, _('Feed updated'))

        return (False, _('Feed not found in config'))

    def deleteFeedWithName(self, feedname):
        for index in range(0, len(self.feeds)):
            if self.feeds[index].getName() == feedname:
                self.feeds.pop(index)
                self.writeConfig()
                break


class Feed:
    isfavorite = False

    def __init__(self, name, description, url, isfavorite = False):
        self.name = name
        self.description = description
        self.url = url
        self.isfavorite = isfavorite

    def getName(self):
        return self.name

    def getDescription(self):
        return self.description

    def getURL(self):
        self.url = self.url.replace('zz', '&')
        return self.url

    def setName(self, name):
        self.name = name

    def setDescription(self, description):
        self.description = description

    def setURL(self, url):
        self.url = url

    def setFavorite(self):
        self.isfavorite = True

    def isFavorite(self):
        return self.isfavorite


class GnewsFeedreaderMenuMain(Screen):

    def __init__(self, session, config, selectedfeed):
        self.config = config
        self.selectedfeed = selectedfeed
        self.skin = '\n\t\t\t\t<screen position="center,center" size="630,440" title="GoogleNews reader" >\n\t\t\t\t\t<widget name="menu" position="0,0" size="620,480" scrollbarMode="showOnDemand" />\n\t\t\t\t</screen>'
        self.session = session
        Screen.__init__(self, session)
        list = []
        list.append((_('change feed'), 'feed_change'))
        list.append((_('add new feed'), 'feed_add'))
        list.append((_('delete feed'), 'feed_delete'))
        self['menu'] = MenuList(list)
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.go,
         'back': self.close}, -1)

    def go(self):
        selection = self['menu'].getCurrent()
        if selection is not None:
            cmd = selection[1]
            if cmd is 'feed_delete':
                if self.selectedfeed:
                    WizzardDeleteFeed(self.session, self, self.config, self.selectedfeed.getName())
            elif cmd is 'feed_add':
                WizzardAddFeed(self.session, self.config)
            elif cmd is 'feed_change':
                if self.selectedfeed:
                    WizzardAddFeed(self.session, self.config, [self.selectedfeed.getName(),
                     self.selectedfeed.getDescription(),
                     self.selectedfeed.getURL(),
                     True])


class WizzardAddFeed(Screen):
    name = ''
    description = ''
    url = 'http://'
    changefeed = False

    def __init__(self, session, config, args = 0):
        if args is not 0:
            self.name = args[0].rstrip()
            self.description = args[1]
            self.url = args[2]
            self.changefeed = args[3]
            self.feedold = Feed(self.name, self.description, self.url)
        self.session = session
        self.config = config
        self.session.openWithCallback(self.name_entered, InputBox, title=_('Please enter a name for the new feed'), text=self.name, maxSize=False, type=Input.TEXT)

    def name_entered(self, feedname):
        if feedname is None:
            self.cancelWizzard()
        else:
            self.name = feedname
            self.session.openWithCallback(self.url_entered, InputBox, title=_('Please enter a url for the new feed'), text=self.url, maxSize=False, type=Input.TEXT)

    def url_entered(self, feedurl):
        if feedurl is None:
            self.cancelWizzard()
        else:
            self.url = feedurl
            self.session.openWithCallback(self.description_entered, InputBox, title=_('Please enter a description for the new feed'), text=self.description, maxSize=False, type=Input.TEXT)

    def description_entered(self, feeddescription):
        if feeddescription is None:
            self.cancelWizzard()
        else:
            self.description = feeddescription
            feednew = Feed(self.name.rstrip(), self.description, self.url)
            if self.changefeed is True:
                result, text = self.config.changeFeed(self.feedold, feednew)
                if result is False:
                    self.session.open(MessageBox, _('changing feed failed!\n\n%s' % text), MessageBox.TYPE_WARNING)
            else:
                result, text = self.config.addFeed(feednew)
                if result is False:
                    self.session.open(MessageBox, _('adding feed failed!\n\n%s' % text), MessageBox.TYPE_WARNING)

    def cancelWizzard(self):
        pass


class WizzardDeleteFeed(Screen):

    def __init__(self, session, menu, config, feedname):
        self.session = session
        self.config = config
        self.menu = menu
        self.feedname2delete = feedname
        self.session.openWithCallback(self.userIsSure, MessageBox, _('are you sure to delete this feed?\n\n%s' % self.feedname2delete), MessageBox.TYPE_YESNO)

    def userIsSure(self, answer):
        if answer is None:
            self.cancelWizzard()
        if answer is False:
            self.cancelWizzard()
        else:
            self.config.deleteFeedWithName(self.feedname2delete)
            self.menu.close()

    def cancelWizzard(self):
        pass


class GnewsFeedScreenContent(Screen):
    if HD_Res == True:
        skin = '\n        \t\n                <screen  position="center,center" size="920,600" title="GoogleNews reader"  >\n                \t\n                <widget name="info" position="10,10" zPosition="4" size="560,55" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />\n                <ePixmap position="15,65" size="890,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                <widget name="mylist" position="20,80" size="880,490" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />\n                 \n                        \n                \n                \n                </screen>'
    else:
        skin = '\n        \t\n         \n        \t\n                <screen  position="center,center" size="580,450" title="GoogleNews reader"   >\n               \n                <widget name="info" position="2,5" zPosition="4" size="580,30" font="Regular;20" foregroundColor="#ffffff" transparent="1" halign="center" valign="center" />\n                <ePixmap position="15,35" size="550,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                <widget name="mylist" position="10,40" size="560,390" scrollbarMode="showOnDemand" transparent="1" zPosition="2" />\n\n\t\t\n\n\n                \n                </screen>'

    def __init__(self, session, args = 0):
        self.feed = args
        self.skin = GnewsFeedScreenContent.skin
        self.session = session
        Screen.__init__(self, session)
        self.feedname = self.feed.getName()
        self['info'] = Label()
        self['mylist'] = MenuList([], True, eListboxPythonMultiContent)
        self['mylist'].l.setItemHeight(35)
        self['mylist'].l.setFont(0, gFont('Regular', 22))
        self.menu = args
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.go,
         'back': self.close}, -1)
        self['info'].setText('Loading feed titles')
        self.timer = eTimer()
        self.timer.callback.append(self.filllist)
        self.timer.start(200, 1)

    def filllist(self):
        list = []
        self.itemlist = []
        newlist = []
        itemnr = 0
        for item in self.getFeedContent(self.feed):
            list.append((item['title'], itemnr))
            self.itemlist.append(item)
            itemnr = itemnr + 1
            res = []
            if HD_Res == True:
                res.append(MultiContentEntryText(pos=(0, 5), size=(5, 30), font=0, flags=RT_HALIGN_CENTER, text='', color=16777215, color_sel=16777215))
                res.append(MultiContentEntryText(pos=(5, 5), size=(820, 30), font=0, flags=RT_HALIGN_CENTER, text=item['title'], color=16770229, color_sel=16770229))
            else:
                res.append(MultiContentEntryText(pos=(0, 5), size=(5, 30), font=0, flags=RT_HALIGN_CENTER, text='', color=16777215, color_sel=16777215))
                res.append(MultiContentEntryText(pos=(5, 5), size=(550, 30), font=0, flags=RT_HALIGN_CENTER, text=item['title'], color=16770229, color_sel=16770229))
            newlist.append(res)
            res = []

        self['info'].setText(self.feedname)
        if len(self.itemlist) == 0:
            self['info'].setText('sorry no feeds available')
        else:
            self['mylist'].l.setList(newlist)
            self['mylist'].show()

    def getFeedContent(self, feed):
        print '[' + myname + "] reading feedurl '%s' ..." % feed.getURL()
        try:
            self.rss = RSS()
            self.feedc = self.rss.getList(feed.getURL())
            print '[' + myname + '] have got %i items in newsfeed ' % len(self.feedc)
            return self.feedc
        except IOError:
            print '[' + myname + '] IOError by loading the feed! feed adress correct?'
            self['info'].setText('IOError by loading the feed! feed adress correct')
            return []
        except:
            self['info'].setText('loading feeddata failed!')
            return []

    def go(self):
        i = self['mylist'].getSelectedIndex()
        self.currentindex = i
        selection = self['mylist'].l.getCurrentSelection()
        if selection is not None:
            item = self.itemlist[i]
            if item['type'].startswith('folder') is True:
                newitem = Feed(item['title'], item['desc'], item['link'])
                self.session.open(GnewsFeedScreenContent, newitem)
            elif item['type'].startswith('pubfeed') is True:
                newitem = Feed(item['title'], item['desc'], item['link'])
                self.session.open(GnewsFeedScreenContent, newitem)
            else:
                try:
                    self.session.open(GnewsFeedScreenItemviewer, [self.feed,
                     item,
                     self.currentindex,
                     self.itemlist])
                except AssertionError:
                    self.session.open(MessageBox, _('Error processing feeds'), MessageBox.TYPE_ERROR)


class GnewsFeedScreenItemviewer(Screen):
    skin = ''

    def __init__(self, session, args = 0):
        global HD_Res
        self.feed = args[0]
        self.item = args[1]
        self.itemlist = args[3]
        xtitle = self.item['title'].replace('"', "'")
        self.url = self.item['link']
        self.currentindex = args[2]
        try:
            sz_w = getDesktop(0).size().width()
            if sz_w == 1280:
                HD_Res = True
            else:
                HD_Res = False
        except:
            HD_Res = False

        if HD_Res == True:
            self.skin = '\n                <screen name="FMenusimple" position="center,center" size="920,600" title="%s"  flags="wfNoBorder" >\n                \n\t\t\t\t        <widget name="titel" position="20,0" zPosition="1" size="560,130" font="Regular;24" transparent="1"  backgroundColor="#00000000" foregroundColor="yellow" valign="center" halign="left" />\n\t\t\t\t        <widget name="leagueNumberWidget" position="830,60" size="90,30" transparent="1" halign="left" font="Regular;20" foregroundColor="yellow"/>\n                                        <ePixmap position="830,20" zPosition="4" size="60,40" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/arrows.png" transparent="1" alphatest="on" />\n\t\t\t\t        <ePixmap position="15,88" size="890,12" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n\t\t\t\t\t<widget name="text" position="20,100" size="880,400" font="Regular;22" />\n\t\t\t\t         <ePixmap position="15,510" size="890,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                                        \n                                </screen>' % self.feed.getName()
        else:
            self.skin = '\n                <screen name="FMenusimple" position="center,center" size="580,450" title="%s"  flags="wfNoBorder" >\n                \n\t\t\t\t        <widget name="titel" position="10,0" zPosition="1" size="490,130" font="Regular;24" transparent="1"  backgroundColor="#00000000" foregroundColor="yellow" valign="center" halign="left" />\n\t\t\t\t        <widget name="leagueNumberWidget" position="520,60" size="70,30" transparent="1" halign="left" font="Regular;20" foregroundColor="yellow"/>\n                                        <ePixmap position="520,20" zPosition="4" size="60,40" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/arrows.png" transparent="1" alphatest="on" />\n\t\t\t\t        <ePixmap position="15,88" size="550,12" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n\t\t\t\t\t<widget name="text" position="10,100" size="560,300" font="Regular;22" />\n\t\t\t\t         <ePixmap position="15,400" size="550,5" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/GoogleNews/images/slider.png" alphatest="blend" transparent="1" backgroundColor="transparent"/>\n                                        \n                                </screen>' % self.feed.getName()
        Screen.__init__(self, session)
        self.itemscount = len(self.itemlist)
        self['leagueNumberWidget'] = Label(str(self.currentindex + 1) + '/' + str(self.itemscount))
        self['titel'] = Label(self.item['title'])
        self['text'] = ScrollLabel(self.item['desc'] + '\n\n' + self.item['date'])
        self['actions'] = ActionMap(['PiPSetupActions', 'WizardActions', 'ColorActions'], {'size-': self.previousitem,
         'size+': self.nextitem,
         'ok': self.close,
         'back': self.close,
         'up': self['text'].pageUp,
         'down': self['text'].pageDown}, -1)

    def gofill(self):
        i = self.currentindex
        selection = self.itemlist
        if selection is not None:
            item = self.itemlist[i]
            self.item = item
            self.filllist()

    def filllist(self):
        self.itemscount = len(self.itemlist)
        self['leagueNumberWidget'].setText(str(self.currentindex + 1) + '/' + str(self.itemscount))
        self['titel'].setText(self.item['title'])
        self['text'].setText(self.item['desc'] + '\n\n' + self.item['date'])

    def nextitem(self):
        currentindex = int(self.currentindex) + 1
        if currentindex == self.itemscount:
            currentindex = 0
        self.currentindex = currentindex
        self.gofill()

    def previousitem(self):
        currentindex = int(self.currentindex) - 1
        if currentindex < 0:
            currentindex = self.itemscount - 1
        self.currentindex = currentindex
        self.gofill()


def convertHTMLTags(text_with_html):
    """
    removes all undisplayable things from text
    """
    charlist = []
    charlist.append(('&#224;', '\xc3\xa0'))
    charlist.append(('&agrave;', '\xc3\xa0'))
    charlist.append(('&#225;', '\xc3\xa1'))
    charlist.append(('&aacute;', '\xc3\xa1'))
    charlist.append(('&#226;', '\xc3\xa2'))
    charlist.append(('&acirc;', '\xc3\xa2'))
    charlist.append(('&#228;', '\xc3\xa4'))
    charlist.append(('&auml;', '\xc3\xa4'))
    charlist.append(('&#249;', '\xc3\xb9'))
    charlist.append(('&ugrave;', '\xc3\xb9'))
    charlist.append(('&#250;', '\xc3\xba'))
    charlist.append(('&uacute;', '\xc3\xba'))
    charlist.append(('&#251;', '\xc3\xbb'))
    charlist.append(('&ucirc;', '\xc3\xbb'))
    charlist.append(('&#252;', '\xc3\xbc'))
    charlist.append(('&uuml;', '\xc3\xbc'))
    charlist.append(('&#242;', '\xc3\xb2'))
    charlist.append(('&ograve;', '\xc3\xb2'))
    charlist.append(('&#243;', '\xc3\xb3'))
    charlist.append(('&oacute;', '\xc3\xb3'))
    charlist.append(('&#244;', '\xc3\xb4'))
    charlist.append(('&ocirc;', '\xc3\xb4'))
    charlist.append(('&#246;', '\xc3\xb6'))
    charlist.append(('&ouml;', '\xc3\xb6'))
    charlist.append(('&#236;', '\xc3\xac'))
    charlist.append(('&igrave;', '\xc3\xac'))
    charlist.append(('&#237;', '\xc3\xad'))
    charlist.append(('&iacute;', '\xc3\xad'))
    charlist.append(('&#238;', '\xc3\xae'))
    charlist.append(('&icirc;', '\xc3\xae'))
    charlist.append(('&#239;', '\xc3\xaf'))
    charlist.append(('&iuml;', '\xc3\xaf'))
    charlist.append(('&#232;', '\xc3\xa8'))
    charlist.append(('&egrave;', '\xc3\xa8'))
    charlist.append(('&#233;', '\xc3\xa9'))
    charlist.append(('&eacute;', '\xc3\xa9'))
    charlist.append(('&#234;', '\xc3\xaa'))
    charlist.append(('&ecirc;', '\xc3\xaa'))
    charlist.append(('&#235;', '\xc3\xab'))
    charlist.append(('&euml;', '\xc3\xab'))
    charlist.append(('&#192;', '\xc3\x80'))
    charlist.append(('&Agrave;', '\xc3\x80'))
    charlist.append(('&#193;', '\xc3\x81'))
    charlist.append(('&Aacute;', '\xc3\x81'))
    charlist.append(('&#194;', '\xc3\x82'))
    charlist.append(('&Acirc;', '\xc3\x82'))
    charlist.append(('&#196;', '\xc3\x84'))
    charlist.append(('&Auml;', '\xc3\x84'))
    charlist.append(('&#217;', '\xc3\x99'))
    charlist.append(('&Ugrave;', '\xc3\x99'))
    charlist.append(('&#218;', '\xc3\x9a'))
    charlist.append(('&Uacute;', '\xc3\x9a'))
    charlist.append(('&#219;', '\xc3\x9b'))
    charlist.append(('&Ucirc;', '\xc3\x9b'))
    charlist.append(('&#220;', '\xc3\x9c'))
    charlist.append(('&Uuml;', '\xc3\x9c'))
    charlist.append(('&#210;', '\xc3\x92'))
    charlist.append(('&Ograve;', '\xc3\x92'))
    charlist.append(('&#211;', '\xc3\x93'))
    charlist.append(('&Oacute;', '\xc3\x93'))
    charlist.append(('&#212;', '\xc3\x94'))
    charlist.append(('&Ocirc;', '\xc3\x94'))
    charlist.append(('&#214;', '\xc3\x96'))
    charlist.append(('&Ouml;', '\xc3\x96'))
    charlist.append(('&#204;', '\xc3\x8c'))
    charlist.append(('&Igrave;', '\xc3\x8c'))
    charlist.append(('&#205;', '\xc3\x8d'))
    charlist.append(('&Iacute;', '\xc3\x8d'))
    charlist.append(('&#206;', '\xc3\x8e'))
    charlist.append(('&Icirc;', '\xc3\x8e'))
    charlist.append(('&#207;', '\xc3\x8f'))
    charlist.append(('&Iuml;', '\xc3\x8f'))
    charlist.append(('&#223;', '\xc3\x9f'))
    charlist.append(('&szlig;', '\xc3\x9f'))
    charlist.append(('&#038;', '&'))
    charlist.append(('&#38;', '&'))
    charlist.append(('&#8230;', '...'))
    charlist.append(('&#8211;', '-'))
    charlist.append(('&#160;', ' '))
    charlist.append(('&#039;', "'"))
    charlist.append(('&#39;', "'"))
    charlist.append(('&lt;', '<'))
    charlist.append(('&gt;', '>'))
    charlist.append(('&nbsp;', ' '))
    charlist.append(('&amp;', '&'))
    charlist.append(('&quot;', '"'))
    charlist.append(('&apos;', "'"))
    charlist.append(('&#8216;', "'"))
    charlist.append(('&#8217;', "'"))
    charlist.append(('&8221;', '\xe2\x80\x9d'))
    charlist.append(('&8482;', '\xe2\x84\xa2'))
    for repl in charlist:
        text_with_html = text_with_html.replace(repl[0], repl[1])

    from re import sub as re_sub
    text_with_html = re_sub('<(.*?)>(?uism)', '', text_with_html)
    return text_with_html


class RSS:
    DEFAULT_NAMESPACES = (None, 'http://purl.org/rss/1.0/', 'http://my.netscape.com/rdf/simple/0.9/')
    DUBLIN_CORE = ('http://purl.org/dc/elements/1.1/',)

    def getElementsByTagName(self, node, tagName, possibleNamespaces = DEFAULT_NAMESPACES):
        for namespace in possibleNamespaces:
            children = node.getElementsByTagNameNS(namespace, tagName)
            if len(children):
                return children

        return []

    def node_data(self, node, tagName, possibleNamespaces = DEFAULT_NAMESPACES):
        children = self.getElementsByTagName(node, tagName, possibleNamespaces)
        node = len(children) and children[0] or None
        return node and ''.join([ child.data.encode('utf-8') for child in node.childNodes ]) or None

    def get_txt(self, node, tagName, default_txt = ''):
        """
        Liefert den Inhalt >tagName< des >node< zurueck, ist dieser nicht
        vorhanden, wird >default_txt< zurueck gegeben.
        """
        return self.node_data(node, tagName) or self.node_data(node, tagName, self.DUBLIN_CORE) or default_txt

    def print_txt(self, node, tagName, print_string):
        """
        Formatierte Ausgabe
        """
        item_data = self.get_txt(node, tagName)
        if item_data == '':
            return
        print print_string % {'tag': tagName,
         'data': item_data}

    def print_rss(self, url):
        from urllib import urlopen
        configproxies = FeedreaderConfig().getProxysettings()
        if configproxies:
            rssDocument = parse(urlopen(url, proxies=configproxies))
        else:
            rssDocument = parse(urlopen(url))
        for node in self.getElementsByTagName(rssDocument, 'item'):
            print '<ul class="RSS">'
            print '<li><h1><a href="%s">' % self.get_txt(node, 'link', '#')
            print self.get_txt(node, 'title', '<no title>')
            print '</a></h1></li>'
            self.print_txt(node, 'date', '<li><small>%(data)s</li>')
            self.print_txt(node, 'description', '<li>%(data)s</li>')
            print '</ul>'

    def getList(self, url):
        """
        returns the content of the given URL as array
        """
        from urllib import urlopen
        configproxies = FeedreaderConfig().getProxysettings()
        if configproxies:
            rssDocument = parse(urlopen(url, proxies=configproxies))
        else:
            rssDocument = parse(urlopen(url))
        channelname = self.get_txt(rssDocument, 'title', 'no channelname')
        data = []
        for node in self.getElementsByTagName(rssDocument, 'item'):
            nodex = {}
            nodex['channel'] = channelname
            nodex['type'] = self.get_txt(node, 'type', 'feed')
            nodex['link'] = self.get_txt(node, 'link', '')
            nodex['title'] = self.convertHTMLTags(self.get_txt(node, 'title', '<no title>'))
            nodex['date'] = self.get_txt(node, 'pubDate', self.get_txt(node, 'date', ''))
            nodex['desc'] = self.convertHTMLTags(self.get_txt(node, 'description', ''))
            data.append(nodex)

        return data

    def convertHTMLTags(self, text_with_html):
        """
        removes all undisplayable things from text
        """
        charlist = []
        charlist.append(('&#224;', '\xc3\xa0'))
        charlist.append(('&agrave;', '\xc3\xa0'))
        charlist.append(('&#225;', '\xc3\xa1'))
        charlist.append(('&aacute;', '\xc3\xa1'))
        charlist.append(('&#226;', '\xc3\xa2'))
        charlist.append(('&acirc;', '\xc3\xa2'))
        charlist.append(('&#228;', '\xc3\xa4'))
        charlist.append(('&auml;', '\xc3\xa4'))
        charlist.append(('&#249;', '\xc3\xb9'))
        charlist.append(('&ugrave;', '\xc3\xb9'))
        charlist.append(('&#250;', '\xc3\xba'))
        charlist.append(('&uacute;', '\xc3\xba'))
        charlist.append(('&#251;', '\xc3\xbb'))
        charlist.append(('&ucirc;', '\xc3\xbb'))
        charlist.append(('&#252;', '\xc3\xbc'))
        charlist.append(('&uuml;', '\xc3\xbc'))
        charlist.append(('&#242;', '\xc3\xb2'))
        charlist.append(('&ograve;', '\xc3\xb2'))
        charlist.append(('&#243;', '\xc3\xb3'))
        charlist.append(('&oacute;', '\xc3\xb3'))
        charlist.append(('&#244;', '\xc3\xb4'))
        charlist.append(('&ocirc;', '\xc3\xb4'))
        charlist.append(('&#246;', '\xc3\xb6'))
        charlist.append(('&ouml;', '\xc3\xb6'))
        charlist.append(('&#236;', '\xc3\xac'))
        charlist.append(('&igrave;', '\xc3\xac'))
        charlist.append(('&#237;', '\xc3\xad'))
        charlist.append(('&iacute;', '\xc3\xad'))
        charlist.append(('&#238;', '\xc3\xae'))
        charlist.append(('&icirc;', '\xc3\xae'))
        charlist.append(('&#239;', '\xc3\xaf'))
        charlist.append(('&iuml;', '\xc3\xaf'))
        charlist.append(('&#232;', '\xc3\xa8'))
        charlist.append(('&egrave;', '\xc3\xa8'))
        charlist.append(('&#233;', '\xc3\xa9'))
        charlist.append(('&eacute;', '\xc3\xa9'))
        charlist.append(('&#234;', '\xc3\xaa'))
        charlist.append(('&ecirc;', '\xc3\xaa'))
        charlist.append(('&#235;', '\xc3\xab'))
        charlist.append(('&euml;', '\xc3\xab'))
        charlist.append(('&#192;', '\xc3\x80'))
        charlist.append(('&Agrave;', '\xc3\x80'))
        charlist.append(('&#193;', '\xc3\x81'))
        charlist.append(('&Aacute;', '\xc3\x81'))
        charlist.append(('&#194;', '\xc3\x82'))
        charlist.append(('&Acirc;', '\xc3\x82'))
        charlist.append(('&#196;', '\xc3\x84'))
        charlist.append(('&Auml;', '\xc3\x84'))
        charlist.append(('&#217;', '\xc3\x99'))
        charlist.append(('&Ugrave;', '\xc3\x99'))
        charlist.append(('&#218;', '\xc3\x9a'))
        charlist.append(('&Uacute;', '\xc3\x9a'))
        charlist.append(('&#219;', '\xc3\x9b'))
        charlist.append(('&Ucirc;', '\xc3\x9b'))
        charlist.append(('&#220;', '\xc3\x9c'))
        charlist.append(('&Uuml;', '\xc3\x9c'))
        charlist.append(('&#210;', '\xc3\x92'))
        charlist.append(('&Ograve;', '\xc3\x92'))
        charlist.append(('&#211;', '\xc3\x93'))
        charlist.append(('&Oacute;', '\xc3\x93'))
        charlist.append(('&#212;', '\xc3\x94'))
        charlist.append(('&Ocirc;', '\xc3\x94'))
        charlist.append(('&#214;', '\xc3\x96'))
        charlist.append(('&Ouml;', '\xc3\x96'))
        charlist.append(('&#204;', '\xc3\x8c'))
        charlist.append(('&Igrave;', '\xc3\x8c'))
        charlist.append(('&#205;', '\xc3\x8d'))
        charlist.append(('&Iacute;', '\xc3\x8d'))
        charlist.append(('&#206;', '\xc3\x8e'))
        charlist.append(('&Icirc;', '\xc3\x8e'))
        charlist.append(('&#207;', '\xc3\x8f'))
        charlist.append(('&Iuml;', '\xc3\x8f'))
        charlist.append(('&#223;', '\xc3\x9f'))
        charlist.append(('&szlig;', '\xc3\x9f'))
        charlist.append(('&#038;', '&'))
        charlist.append(('&#38;', '&'))
        charlist.append(('&#8230;', '...'))
        charlist.append(('&#8211;', '-'))
        charlist.append(('&#160;', ' '))
        charlist.append(('&#039;', "'"))
        charlist.append(('&#39;', "'"))
        charlist.append(('&lt;', '<'))
        charlist.append(('&gt;', '>'))
        charlist.append(('&nbsp;', ' '))
        charlist.append(('&amp;', '&'))
        charlist.append(('&quot;', '"'))
        charlist.append(('&apos;', "'"))
        charlist.append(('&#8216;', "'"))
        charlist.append(('&#8217;', "'"))
        charlist.append(('&8221;', '\xe2\x80\x9d'))
        charlist.append(('&8482;', '\xe2\x84\xa2'))
        for repl in charlist:
            text_with_html = text_with_html.replace(repl[0], repl[1])

        from re import sub as re_sub
        text_with_html = re_sub('<(.*?)>(?uism)', '', text_with_html)
        return text_with_html
