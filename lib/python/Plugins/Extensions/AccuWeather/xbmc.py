from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox
from Plugins.Plugin import PluginDescriptor
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.About import about

from Tools.Directories import fileExists
from urllib import quote
from urllib2 import Request, urlopen, URLError, HTTPError
from xml.dom import minidom, Node
from enigma import loadPic, eTimer

class MeteoMain(Screen):
    skin = '''<screen position="center,center" size="1280,720" title="Weather" flags="wfNoBorder">
	  <ePixmap position="0,0" size="1280,720" zPosition="0" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/xbmcweather/100.png" />
	  <!--<widget source="global.CurrentTime" render="Label" position="1180,5" size="80,22" zPosition="1" font="Regular;16" valign="top" halign="left" foregroundColor="white" backgroundColor="transparent" transparent="1">
	  <convert type="ClockToText">Default</convert>
	  </widget>-->
	  <widget name="lab1" position="150,100" halign="right" size="220,20" zPosition="1" font="Regular;16" foregroundColor="#dcdcdc" backgroundColor="transparent" valign="top"  transparent="1" />
	  <widget name="lab1b" position="373,100" halign="left" size="210,20" zPosition="1" font="Regular;16" foregroundColor="#ffa500" backgroundColor="transparent" valign="top"  transparent="1" />
	  <widget name="lab2" position="150,120" halign="center" size="440,26" zPosition="1" font="Regular;24" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1" />
	  <widget name="lab3" position="150,146" halign="center" size="440,20" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab4" position="140,220" halign="right" size="180,80" zPosition="1" font="Regular;80" foregroundColor="white" backgroundColor="transparent" valign="top"  transparent="1" />
	  <widget name="lab4b" position="310,220" halign="right" size="40,30" zPosition="1" font="Regular;24" foregroundColor="white" backgroundColor="transparent" valign="top"  transparent="1" />
	  <widget name="lab5" position="350,185" size="250,180" zPosition="3" transparent="1" alphatest="blend"/>
	  <widget name="lab6" position="150,367" halign="center" size="440,30" zPosition="1" font="Regular;23" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1" />
	  <widget name="lab7" position="140,420" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab7b" position="305,420" halign="left" size="280,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab8" position="140,450" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab8b" position="305,450" halign="left" size="285,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab9" position="140,480" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab9b" position="305,480" halign="left" size="285,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab10" position="140,510" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab10b" position="305,510" halign="left" size="285,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab11" position="140,540" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab11b" position="305,540" halign="left" size="285,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab12" position="140,570" halign="right" size="150,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab12b" position="305,570" halign="left" size="285,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab13" position="700,120" halign="center" size="430,26" zPosition="1" font="Regular;24" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1"  />
	  <widget name="lab14" position="730,170" halign="left" size="65,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab14b" position="795,170" halign="left" size="90,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab15" position="895,170" halign="left" size="60,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab15b" position="955,170" halign="left" size="60,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab16" position="730,200" halign="left" size="220,26" zPosition="1" font="Regular;22" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1"  />
	  <widget name="lab17" position="1010,150" size="100,100" zPosition="1" alphatest="blend" transparent="1" />
	  <widget name="lab18" position="700,300" halign="center" size="430,26" zPosition="1" font="Regular;24" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1"  />
	  <widget name="lab19" position="730,350" halign="left" size="65,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab19b" position="795,350" halign="left" size="90,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab20" position="895,350" halign="left" size="60,24" zPosition="1" font="Regular;19" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab20b" position="955,350" halign="left" size="60,24" zPosition="1" font="Regular;19" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab21" position="730,380" halign="left" size="220,26" zPosition="1" font="Regular;22" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1"  />
	  <widget name="lab22" position="1010,320" size="100,100" zPosition="1" alphatest="blend" transparent="1" />
	  <widget name="lab23" position="700,470" halign="center" size="430,26" zPosition="1" font="Regular;24" valign="top" foregroundColor="white" backgroundColor="transparent" transparent="1" />
	  <widget name="lab24" position="730,510" halign="right" size="90,22" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab24b" position="830,510" halign="left" size="100,22" zPosition="1" font="Regular;18" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab25" position="930,510" halign="left" size="100,22" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab25b" position="1040,510" halign="left" size="115,22" zPosition="1" font="Regular;18" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab26" position="730,535" halign="right" size="90,22" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab26b" position="830,535" halign="left" size="330,22" zPosition="1" font="Regular;18" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab27" position="730,560" halign="right" size="90,22" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab27b" position="830,560" halign="left" size="330,22" zPosition="1" font="Regular;18" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  <widget name="lab28" position="790,595" size="16,16" zPosition="1" alphatest="blend" transparent="1" />
	  <widget name="lab28a" position="800,590" halign="right" size="20,20" zPosition="1" font="Regular;18" valign="top" foregroundColor="#8F8F8F" backgroundColor="transparent" transparent="1" />
	  <widget name="lab28b" position="830,590" halign="left" size="330,22" zPosition="1" font="Regular;18" foregroundColor="white" backgroundColor="transparent" valign="top" transparent="1" />
	  </screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self['lab1'] = Label(_('Retrieving data ...'))
        self['lab1b'] = Label('')
        self['lab2'] = Label('')
        self['lab3'] = Label('')
        self['lab4'] = Label('')
        self['lab4b'] = Label('')
        self['lab5'] = Pixmap()
        self['lab6'] = Label('')
        self['lab7'] = Label('')
        self['lab7b'] = Label('')
        self['lab8'] = Label('')
        self['lab8b'] = Label('')
        self['lab9'] = Label('')
        self['lab9b'] = Label('')
        self['lab10'] = Label('')
        self['lab10b'] = Label('')
        self['lab11'] = Label('')
        self['lab11b'] = Label('')
        self['lab12'] = Label('')
        self['lab12b'] = Label('')
        self['lab13'] = Label('')
        self['lab14'] = Label('')
        self['lab14b'] = Label('')
        self['lab15'] = Label('')
        self['lab15b'] = Label('')
        self['lab16'] = Label('')
        self['lab17'] = Pixmap()
        self['lab18'] = Label('')
        self['lab19'] = Label('')
        self['lab19b'] = Label('')
        self['lab20'] = Label('')
        self['lab20b'] = Label('')
        self['lab21'] = Label('')
        self['lab22'] = Pixmap()
        self['lab23'] = Label('')
        self['lab24'] = Label('')
        self['lab24b'] = Label('')
        self['lab25'] = Label('')
        self['lab25b'] = Label('')
        self['lab26'] = Label('')
        self['lab26b'] = Label('')
        self['lab27'] = Label('')
        self['lab27b'] = Label('')
        self['lab28'] = Pixmap()
        self['lab28a'] = Label('')
        self['lab28b'] = Label('')
        self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'red': self.key_red,
         'back': self.close,
         'ok': self.close})
        self.activityTimer = eTimer()
        self.activityTimer.timeout.get().append(self.startConnection)
        self.onShow.append(self.startShow)
        self.onClose.append(self.delTimer)
        self.bhv = 0

    def startShow(self):
        self.activityTimer.start(10)

    def startConnection(self):
        self.activityTimer.stop()
        self.updateInfo()

    def updateInfo(self):
        myurl = self.get_Url()
        req = Request(myurl)
        try:
            handler = urlopen(req)
        except HTTPError as e:
            maintext = 'Error: connection failed !'
        except URLError as e:
            maintext = 'Error: Page not available !'
        else:
            dom = minidom.parse(handler)
            handler.close()
            maintext = ''
            tmptext = ''
            if dom:
                weather_data = {}
                weather_data['title'] = dom.getElementsByTagName('title')[0].firstChild.data
                txt = str(weather_data['title'])
                if txt.find('Error') != -1:
                    self['lab1'].setText(_('Sorry, wrong WOEID'))
                    return
                ns_data_structure = {'location': ('city', 'region', 'country'),
                 'units': ('temperature', 'distance', 'pressure', 'speed'),
                 'wind': ('chill', 'direction', 'speed'),
                 'atmosphere': ('humidity', 'visibility', 'pressure', 'rising'),
                 'astronomy': ('sunrise', 'sunset'),
                 'condition': ('text', 'code', 'temp', 'date')}
                for tag, attrs in ns_data_structure.items():
                    weather_data[tag] = self.xml_get_ns_yahoo_tag(dom, 'http://xml.weather.yahoo.com/ns/rss/1.0', tag, attrs)

                weather_data['geo'] = {}
                weather_data['geo']['lat'] = dom.getElementsByTagName('geo:lat')[0].firstChild.data
                weather_data['geo']['long'] = dom.getElementsByTagName('geo:long')[0].firstChild.data
                weather_data['condition']['title'] = dom.getElementsByTagName('item')[0].getElementsByTagName('title')[0].firstChild.data
                weather_data['html_description'] = dom.getElementsByTagName('item')[0].getElementsByTagName('description')[0].firstChild.data
                forecasts = []
                for forecast in dom.getElementsByTagNameNS('http://xml.weather.yahoo.com/ns/rss/1.0', 'forecast'):
                    forecasts.append(self.xml_get_attrs(forecast, ('day', 'date', 'low', 'high', 'text', 'code')))

                weather_data['forecasts'] = forecasts
                dom.unlink()
                maintext = _('Data provider: ')
                self['lab1b'].setText(_('Yahoo Weather'))
                city = '%s' % str(weather_data['location']['city'])
                self['lab2'].setText(city)
                txt = str(weather_data['condition']['date'])
                parts = txt.strip().split(' ')
                txt = 'Last Updated: %s %s %s %s %s' % (parts[1],
                 parts[2],
                 parts[3],
                 parts[4],
                 parts[5])
                self['lab3'].setText(txt)
                txt = str(weather_data['condition']['temp'])
                self['lab4'].setText(txt)
                self['lab4b'].setText('\xc2\xb0C')
                icon = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/xbmcweather/%s.png' % str(weather_data['condition']['code'])
                myicon = self.checkIcon(icon)
                png = loadPic(myicon, 250, 180, 0, 0, 0, 0)
                self['lab5'].instance.setPixmap(png)
                txt = str(weather_data['condition']['text'])
                self['lab6'].setText(txt)
                self['lab7'].setText(_('Humidity :'))
                txt = str(weather_data['atmosphere']['humidity']) + ' %'
                self['lab7b'].setText(txt)
                self['lab8'].setText(_('Pressure :'))
                txt = str(weather_data['atmosphere']['pressure']) + ' mb'
                self['lab8b'].setText(txt)
                self['lab9'].setText(_('Visibility :'))
                txt = str(weather_data['atmosphere']['visibility']) + ' km'
                self['lab9b'].setText(txt)
                self['lab10'].setText(_('Sunrise :'))
                txt = str(weather_data['astronomy']['sunrise'])
                self['lab10b'].setText(txt)
                self['lab11'].setText(_('Sunset :'))
                txt = str(weather_data['astronomy']['sunset'])
                self['lab11b'].setText(txt)
                self['lab12'].setText(_('Wind :'))
                direction = self.wind_direction(str(weather_data['wind']['direction']))
                txt = _('From') +  direction + _('at') + str(weather_data['wind']['speed']) + _('kmh')
                self['lab12b'].setText(txt)
                txt = self.extend_day(str(weather_data['forecasts'][0]['day']))
                self['lab13'].setText(txt)
                self['lab14'].setText(_('High :'))
                txt = str(weather_data['forecasts'][0]['high']) + '\xc2\xb0C'
                self['lab14b'].setText(txt)
                self['lab15'].setText(_('Low :'))
                txt = str(weather_data['forecasts'][0]['low']) + '\xc2\xb0C'
                self['lab15b'].setText(txt)
                txt = str(weather_data['forecasts'][0]['text'])
                self['lab16'].setText(txt)
                icon = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/xbmcweather/small/%s.png' % str(weather_data['forecasts'][0]['code'])
                myicon = self.checkIcon(icon)
                png = loadPic(myicon, 100, 100, 0, 0, 0, 0)
                self['lab17'].instance.setPixmap(png)
                txt = self.extend_day(str(weather_data['forecasts'][1]['day']))
                self['lab18'].setText(txt)
                self['lab19'].setText(_('High :'))
                txt = str(weather_data['forecasts'][1]['high']) + '\xc2\xb0C'
                self['lab19b'].setText(txt)
                self['lab20'].setText(_('Low :'))
                txt = str(weather_data['forecasts'][1]['low']) + '\xc2\xb0C'
                self['lab20b'].setText(txt)
                txt = str(weather_data['forecasts'][1]['text'])
                self['lab21'].setText(txt)
                icon = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/xbmcweather/small/%s.png' % str(weather_data['forecasts'][1]['code'])
                myicon = self.checkIcon(icon)
                png = loadPic(myicon, 100, 100, 0, 0, 0, 0)
                self['lab22'].instance.setPixmap(png)
                self['lab23'].setText(city)
                self['lab24'].setText(_('Latitude :'))
                txt = str(weather_data['geo']['lat']) + '\xc2\xb0'
                self['lab24b'].setText(txt)
                self['lab25'].setText(_('Longitude :'))
                txt = str(weather_data['geo']['long']) + '\xc2\xb0'
                self['lab25b'].setText(txt)
                self['lab26'].setText(_('Region :'))
                txt = str(weather_data['location']['region'])
                self['lab26b'].setText(txt)
                self['lab27'].setText(_('Country :'))
                txt = str(weather_data['location']['country'])
                self['lab27b'].setText(txt)
                myicon = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/xbmcweather/red.png'
                png = loadPic(myicon, 16, 16, 0, 0, 0, 0)
                self['lab28'].instance.setPixmap(png)
                self['lab28a'].setText(':')
                self['lab28b'].setText(_('Change city'))
            else:
                maintext = 'Error getting XML document!'

        self['lab1'].setText(maintext)

    def xml_get_ns_yahoo_tag(self, dom, ns, tag, attrs):
        element = dom.getElementsByTagNameNS(ns, tag)[0]
        return self.xml_get_attrs(element, attrs)

    def xml_get_attrs(self, xml_element, attrs):
        result = {}
        for attr in attrs:
            result[attr] = xml_element.getAttribute(attr)

        return result

    def wind_direction(self, degrees):
        try:
            degrees = int(degrees)
        except ValueError:
            return ''

        if degrees < 23 or degrees >= 338:
            return 'North'
        if degrees < 68:
            return 'NEast'
        if degrees < 113:
            return 'East'
        if degrees < 158:
            return 'SEast'
        if degrees < 203:
            return 'South'
        if degrees < 248:
            return 'SWest'
        if degrees < 293:
            return 'West'
        if degrees < 338:
            return 'NWest'

    def extend_day(self, day):
        if day == 'Mon':
            return _('Monday')
        elif day == 'Tue':
            return _('Tuesday')
        elif day == 'Wed':
            return _('Wednesday')
        elif day == 'Thu':
            return _('Thursday')
        elif day == 'Fri':
            return _('Friday')
        elif day == 'Sat':
            return _('Saturday')
        elif day == 'Sun':
            return _('Sunday')
        else:
            return day

    def checkIcon(self, localfile):
        if fileExists(localfile):
            pass
        else:
            url = localfile.replace('/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather', 'http://www.vuplus-community.net/bhaddons')
            handler = urlopen(url)
            if handler:
                content = handler.read()
                fileout = open(localfile, 'wb')
                fileout.write(content)
                handler.close()
                fileout.close()
        return localfile

    def get_Url(self):
        url = 'http://weather.yahooapis.com/forecastrss?w='
        if about.getHardwareTypeString() == "INI-5000SV":
		url2 = '906057' # Stockholm
	elif about.getHardwareTypeString() == "INI-5000R":
		url2 = '2122265' # Moskwa
	else:
		url2 = '638242' # Berlin
	    
        cfgfile = '/etc/meteo.cfgg'
        if fileExists(cfgfile):
            f = open(cfgfile, 'r')
            line = f.readline()
            url2 = line.strip()
            f.close()
        url3 = '&u=c'
        url = url + url2 + url3
        url = url.replace(' ', '%20')
        return url

    def delTimer(self):
        del self.activityTimer

    def key_red(self):
        msg = _('Enter the city name:')
        city = ''
        if about.getHardwareTypeString() == "INI-5000SV":
		city ="Stockholm"
	elif about.getHardwareTypeString() == "INI-5000R":
		city = "Moscow"
	else:
		city = "Berlin"
        self.session.openWithCallback(self.goSelect, InputBox, title=msg, windowTitle=_('Change city'), text=city)

    def goSelect(self, city):
        if city is not None:
            self.session.openWithCallback(self.updateInfo, MeteoSelectCity, city)


class MeteoSelectCity(Screen):
    skin = '''<screen position="center,center" size="620,500" title="Select city">
	  <widget source="list" render="Listbox" position="10,20" zPosition="1" size="580,430" scrollbarMode="showOnDemand" transparent="1" >
	  <convert type="StringList" />
	  </widget>
	  <widget name="lab1" position="10,470" halign="center" size="580,30" zPosition="1" font="Regular;24" valign="top" transparent="1" />
	  </screen>'''

    def __init__(self, session, city):
        Screen.__init__(self, session)
        self.city = quote(city)
        self.flist = []
        self['list'] = List(self.flist)
        self['lab1'] = Label(_('Sorry no matches found'))
        self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'back': self.close,
         'ok': self.saveCfg})
        self.onLayoutFinish.append(self.queryStart)

    def queryStart(self):
        url = 'http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20geo.places%20where%20text=%22' + self.city + '%22&format=xml'
        req = Request(url)
        handler = urlopen(req)
        xml_response = handler.read()
        dom = minidom.parseString(xml_response)
        handler.close()
        if dom:
            city_list = dom.getElementsByTagName('place')
            if len(city_list) > 0:
                self['lab1'].setText(_('Press ok to confirm'))
            for city_element in city_list:
                txt = ''
                woeid = ''
                woeids = city_element.getElementsByTagName('woeid')[0]
                woeid = str(self.getText(woeids.childNodes))
                names = city_element.getElementsByTagName('name')[0]
                name = self.getText(names.childNodes)
                txt += str(name) + '   '
                locations = city_element.getElementsByTagName('admin1')[0]
                location = self.getText(locations.childNodes)
                txt += str(location) + '   '
                countries = city_element.getElementsByTagName('country')[0]
                country = self.getText(countries.childNodes)
                txt += str(country)
                res = (txt, woeid)
                self.flist.append(res)

            dom.unlink()
        self['list'].list = self.flist

    def getText(self, nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)

        return ''.join(rc)

    def saveCfg(self):
        mysel = self['list'].getCurrent()
        if mysel:
            pin = mysel[1]
            cfgfile = '/etc/meteo.cfgg'
            out = open(cfgfile, 'w')
            out.write(pin)
            out.close()
            self.close()
            