from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.SelectionList import SelectionList
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.ActionMap import ActionMap
import xml.dom.minidom
from urllib import quote
from urllib2 import Request, URLError, urlopen
from httplib import HTTPException
from enigma import eDVBDB
import urllib
import urllib2
import os
import os.path
from xml.dom.minidom import parse, parseString
STREAM = 1

class IPTVStreams(Screen):
    LIST_NAME = 0
    LIST_CAT = 1
    LIST_TYPE = 2
    LIST_URL = 3
    LEVEL_FILES = 0
    LEVEL_XML = 1
    DIR_ENIGMA2 = '/etc/enigma2/'
    url2 = 'http://et-live-links.googlecode.com/svn/trunk/'
    
    main1 = 'http://'
    main2 = 'livestream'
    main3 = '.et-view-support.com'
    main4 = '/testing/'
    
    skin = '''<screen position="c-300,c-210" size="600,420" title="">
	    <widget name="list" position="10,10" size="e-20,210" scrollbarMode="showOnDemand" />
	    <widget source="info" render="Label" position="10,250" size="e-20,80" halign="center" valign="top" font="Regular;17" />
	    <ePixmap pixmap="skin_default/buttons/green.png" position="c-150,e-45" size="140,40" alphatest="on" />
	    <ePixmap pixmap="skin_default/buttons/yellow.png" position="c-0,e-45" size="140,40" alphatest="on" />
	    <ePixmap pixmap="skin_default/buttons/red.png" position="c-300,e-45" size="140,40" alphatest="on" />
	    <widget source="key_green" render="Label" position="c-150,e-45" zPosition="1" size="140,40" font="Regular;16" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
	    <widget source="key_red" render="Label" position="c-300,e-45" zPosition="1" size="140,40" font="Regular;16" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
	    <widget source="key_yellow" render="Label" position="c-0,e-45" zPosition="1" size="140,40" font="Regular;16" halign="center" valign="center" backgroundColor="#a58b00" transparent="1" />
	    </screen>'''
    

    def __init__(self, session):
        self.skin = IPTVStreams.skin
        Screen.__init__(self, session)
        self['key_red'] = StaticText(_('Cancel'))
        self['key_yellow'] = StaticText(_('Change\nStreams'))
        self['key_green'] = StaticText(_('Download'))
        self['actions'] = ActionMap(['SetupActions', 'NumberActions', 'ColorActions'], {'ok': self.keyOk,
         'save': self.keyGo,
         'cancel': self.keyCancel,
         'yellow': self.changeMenu,
         'green': self.keyGo,
         'red': self.keyCancel}, -2)
        self.list = SelectionList()
        self['list'] = self.list
        self['info'] = StaticText('')
        self.doExit = False
        self.level = self.LEVEL_FILES
        self.subMenuName = ''
        self.subMenuDescrName = ''
        self.xmlFiles = []
        self.xmlCategories = []
        self.lastchanged = ''
        self.lastchanges = ''
        self.onLayoutFinish.append(self.createTopMenu)

    def changeMenu(self):
        global STREAM
        if STREAM == 1:
            self.createTopMenu2()
        elif STREAM == 2:
            self.createTopMenu3()
        elif STREAM == 3:
            self.createTopMenu()

    def initSelectionList(self):
        list = []
        self.list.setList(list)

    def createTopMenu(self):
        global STREAM
        STREAM = 1
        self.setTitle(_('IPTV Streams'))
        self.initSelectionList()
        self.subMenuName = ''
        self.subMenuDescrName = ''
        self.level = self.LEVEL_FILES
        self.readMainXml()
        count = 0
        for x in self.xmlFiles:
            self.list.addSelection(x[self.LIST_CAT], x[self.LIST_NAME], count, False)
            count += 1

        self['info'].setText('Streamlinks 1')

    def createTopMenu2(self):
        global STREAM
        STREAM = 2
        self.setTitle(_('IPTV Streams'))
        self.initSelectionList()
        self.subMenuName = ''
        self.subMenuDescrName = ''
        self.level = self.LEVEL_FILES
        self.readMainXml2()
        count = 0
        for x in self.xmlFiles:
            self.list.addSelection(x[self.LIST_CAT], x[self.LIST_NAME], count, False)
            count += 1

        self['info'].setText('Streamslinks 2')

    def createTopMenu3(self):
        global STREAM
        STREAM = 3
        self.setTitle(_('My Local Streams'))
        self.initSelectionList()
        self.subMenuName = ''
        self.subMenuDescrName = ''
        self.level = self.LEVEL_FILES
        self.readMainXml3()
        count = 0
        for x in self.xmlFiles:
            self.list.addSelection(x[self.LIST_CAT], x[self.LIST_NAME], count, False)
            count += 1

        self['info'].setText('Streamlinks Local:\n/usr/lib/enigma2/python/Plugins/Extensions/IPTVStreams/url/')

    

    def readXmlSubFile(self, fileName, descrName):
        self.initSelectionList()
        self.xmlList = []
        self.subMenuName = fileName
        self.subMenuDescrName = descrName
        self.level = self.LEVEL_XML
        print 'self.LEVEL_XML =', self.LEVEL_XML
        print 'fileName =', fileName
        print 'descrName =', descrName
        print 'self.xmlList =', self.xmlList
        if STREAM == 1:
            self.readChannelXml(self.xmlList, fileName)
            print 'self.xmlList 1=', self.xmlList
        elif STREAM == 2:
            self.readChannelXml2(self.xmlList, fileName)
            print 'self.xmlList 2=', self.xmlList
        elif STREAM == 3:
            self.readChannelXml3(self.xmlList, fileName)
            print 'self.xmlList 3=', self.xmlList
        tmp = _('Last update') + ': %s\n\n%s' % (self.lastchanged, self.lastchanges)
        self['info'].setText(tmp)
        count = 0
        for x in self.xmlCategories:
            self.list.addSelection(x, x, count, False)
            count += 1

    def readXmlSubFile2(self, fileName, descrName):
        self.initSelectionList()
        self.xmlList = []
        self.subMenuName = fileName
        self.subMenuDescrName = descrName
        self.level = self.LEVEL_XML
        self.readChannelXml3(self.xmlList, fileName)
        tmp = _('Last update') + ': %s\n\n%s' % (self.lastchanged, self.lastchanges)
        self['info'].setText(tmp)
        count = 0
        for x in self.xmlCategories:
            self.list.addSelection(x, x, count, False)
            count += 1

    def wgetUrl2(self, url2):
        std_headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.6) Gecko/20100627 Firefox/3.6.6',
         'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
         'Accept-Language': 'en-us,en;q=0.5'}
        outtxt = Request(url2, None, std_headers)
        try:
            outtxt = urlopen(url2).read()
        except (URLError, HTTPException) as err:
            return ''

        return outtxt

    def keyOk(self):
        if self.level == self.LEVEL_FILES:
            print 'in Keyok 1'
            self.keyGo()
        elif self.level == self.LEVEL_XML:
            print 'in Keyok 2'
            if len(self.xmlCategories) > 0:
                self.list.toggleSelection()

    def keyGo(self):
        if self.level == self.LEVEL_FILES:
            self.readXmlSubFile(self.xmlFiles[self.list.getSelectedIndex()][self.LIST_NAME], self.xmlFiles[self.list.getSelectedIndex()][self.LIST_CAT])
            return
        self.doExit = False
        tmpList = []
        tmpList = self.list.getSelectionsList()
        if len(tmpList) == 0:
            self.session.openWithCallback(self.infoCallback, MessageBox, _('Nothing selected'), MessageBox.TYPE_INFO)
            return
        self.xmlList.sort()
        tvFileList = []
        radioFileList = []
        for item in tmpList:
            if self.createUserBouquetFile(item[1], 'tv') > 0:
                tvFileList.append(item[1])
            if self.createUserBouquetFile(item[1], 'radio') > 0:
                radioFileList.append(item[1])

        if len(tvFileList) > 0:
            self.createBouquetFile(tvFileList, 'tv')
        if len(radioFileList) > 0:
            self.createBouquetFile(radioFileList, 'radio')
        db = eDVBDB.getInstance()
        db.reloadServicelist()
        db.reloadBouquets()
        self.doExit = True
        self.session.openWithCallback(self.infoCallback, MessageBox, _('Successfully Imported:\nChannels Now Available in your bouquet/Favorite list'), MessageBox.TYPE_INFO)

    def infoCallback(self, confirmed):
        if self.doExit:
            self.createTopMenu()

    def createBouquetFile(self, catNames, fileType):
        newFileContent = ''
        fileContent = self.readFile(self.DIR_ENIGMA2 + 'bouquets.' + fileType)
        if fileContent == '':
            return
        for x in fileContent:
            x = self.stripLineEndings(x)
            isFound = False
            for cat in catNames:
                if '"userbouquet.streams_' + self.convertToFileName(self.subMenuName + cat) in x:
                    isFound = True
                    break

            if not isFound:
                newFileContent += x + '\n'

        for cat in catNames:
            newFileContent += '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.streams_' + self.convertToFileName(self.subMenuName + cat) + '.' + fileType + '" ORDER BY bouquet\n'

        fp = open(self.DIR_ENIGMA2 + 'bouquets.' + fileType, 'w')
        fp.write(newFileContent)
        fp.close()

    def createUserBouquetFile(self, catName, fileType):
        ret = 0
        newChannelList = []
        newChannelList.append('#NAME Stream ' + self.subMenuDescrName + ' ' + catName)
        for x in self.xmlList:
            if x[self.LIST_CAT] == catName and x[self.LIST_TYPE] == fileType:
                newChannelList.append('#SERVICE 4097:0:0:0:0:0:0:0:0:0:%s:%s' % (quote(x[self.LIST_URL]), quote(x[self.LIST_NAME])))
                ret += 1

        if ret > 0:
            fp = open(self.DIR_ENIGMA2 + 'userbouquet.streams_' + self.convertToFileName(self.subMenuName + catName) + '.' + fileType, 'w')
            for x in newChannelList:
                fp.write(x + '\n')

            fp.close()
        return ret

    def keyCancel(self):
        if self.level == self.LEVEL_FILES:
            self.close()
        elif self.level == self.LEVEL_XML:
            self.createTopMenu()

    def wgetUrl(self, url):
        std_headers = {'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.6) Gecko/20100627 Firefox/3.6.6',
         'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
         'Accept-Language': 'en-us,en;q=0.5'}
        outtxt = Request(url, None, std_headers)
        try:
            mickey = 'live'
            mouse = 'balu'
            skin = urllib2.HTTPPasswordMgrWithDefaultRealm()
            skin.add_password(None, url, mickey, mouse)
            skinner = urllib2.HTTPBasicAuthHandler(skin)
            opener = urllib2.build_opener(skinner)
            urllib2.install_opener(opener)
            outtxt = urllib2.urlopen(url).read()
        except (URLError, HTTPException) as err:
            return ''

        return outtxt

    def readFile(self, name):
        try:
            lines = open(name).readlines()
            return lines
        except:
            return ''

    def convertToFileName(self, name):
        return name.replace(' ', '_')

    def stripLineEndings(self, buf):
        return buf.strip('\r\n').strip('\n').strip('\t')

    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
            return str(''.join(rc))

    def readMainXml(self):
        xmlnode = []
        pro = self.main1 + self.main2 + self.main3 + self.main4 + 'livestreams.xml'
        print pro
        lines = self.wgetUrl(pro)
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlFiles = []
        tmp = xmlnode.getElementsByTagName('xmlfile')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('descr')[0].childNodes))
            self.xmlFiles.append((name, cat))

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))

    

    def readMainXml2(self):
        xmlnode = []
        pro2 = self.url2 + 'livestreams.xml'
        print pro2
        lines = self.wgetUrl2(pro2)
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlFiles = []
        tmp = xmlnode.getElementsByTagName('xmlfile')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('descr')[0].childNodes))
            self.xmlFiles.append((name, cat))

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))

    def readMainXml3(self):
        xmlnode = []
        path = '/usr/lib/enigma2/python/Plugins/Extensions/IPTVStreams/url/main.xml'
        pro2 = open(path).read()
        lines = pro2
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlFiles = []
        tmp = xmlnode.getElementsByTagName('xmlfile')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('descr')[0].childNodes))
            self.xmlFiles.append((name, cat))

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))

    def readChannelXml(self, tmpList, fileName):
        xmlnode = []
        pro = self.main1 + self.main2 + self.main3 + self.main4 + fileName + '.xml'
        lines = self.wgetUrl(pro)
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlCategories = []
        tmp = xmlnode.getElementsByTagName('stream')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            url = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('url')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('cat')[0].childNodes))
            type = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('type')[0].childNodes))
            tmpList.append((name,
             cat,
             type,
             url))
            foundCat = False
            for x in self.xmlCategories:
                if x == cat:
                    foundCat = True
                    break

            if not foundCat:
                self.xmlCategories.append(cat)

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))

    def readChannelXml2(self, tmpList, fileName):
        xmlnode = []
        pro = self.url2 + fileName + '.xml'
        lines = self.wgetUrl2(pro)
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlCategories = []
        tmp = xmlnode.getElementsByTagName('stream')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            url = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('url')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('cat')[0].childNodes))
            type = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('type')[0].childNodes))
            tmpList.append((name,
             cat,
             type,
             url))
            foundCat = False
            for x in self.xmlCategories:
                if x == cat:
                    foundCat = True
                    break

            if not foundCat:
                self.xmlCategories.append(cat)

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))

    def readChannelXml3(self, tmpList, fileName):
        xmlnode = []
        PATH = '/usr/lib/enigma2/python/Plugins/Extensions/IPTVStreams/url/'
        lines = open(PATH + fileName + '.xml').read()
        print 'lines 3=', lines
        if lines == '':
            return
        xmlnode = parseString(lines)
        self.xmlCategories = []
        tmp = xmlnode.getElementsByTagName('stream')
        for i in range(len(tmp)):
            name = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('name')[0].childNodes))
            url = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('url')[0].childNodes))
            cat = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('cat')[0].childNodes))
            type = self.stripLineEndings(self.getText(tmp[i].getElementsByTagName('type')[0].childNodes))
            tmpList.append((name,
             cat,
             type,
             url))
            foundCat = False
            for x in self.xmlCategories:
                if x == cat:
                    foundCat = True
                    break

            if not foundCat:
                self.xmlCategories.append(cat)

        tmp = xmlnode.getElementsByTagName('comments')
        if len(tmp) == 1:
            self.lastchanged = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('lastchange')[0].childNodes))
            self.lastchanges = self.stripLineEndings(self.getText(tmp[0].getElementsByTagName('description')[0].childNodes))


def main(session, **kwargs):
    session.open(IPTVStreams)


def Plugins(**kwargs):
    list = [PluginDescriptor(name=_('IPTV Streams'), description=_('Streams in Bouquets'), where=[PluginDescriptor.WHERE_PLUGINMENU], icon='plugin.png', fnc=main)]
    list.append(PluginDescriptor(name=_('IPTV Streams'), description=_('Streams in Bouquets'), where=PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=main))
    return list
