from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Tools.LoadPixmap import LoadPixmap
import xml.etree.cElementTree
from twisted.internet import reactor, defer
from twisted.web import client
import urllib
from Components.Pixmap import Pixmap
from enigma import ePicLoad
import string
import os
import time
from enigma import getDesktop
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.AVSwitch import AVSwitch
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import ConfigSubsection, ConfigSubList, ConfigText, ConfigInteger, config
from setup import initConfig, initConfigacu, WeatherPluginEntriesListConfigScreen, WeatherPluginEntriesListConfigScreenacu, initConfigfore, WeatherPluginEntriesListConfigScreenfore
from string import upper
from Screens.ChoiceBox import ChoiceBox
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_WRAP, RT_VALIGN_CENTER
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from os import environ
import gettext
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE, fileExists

lang = language.getLanguage()
environ['LANGUAGE'] = lang[:2]
lenguaje = str(lang[:2])
gettext.bindtextdomain('enigma2', resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain('enigma2')
gettext.bindtextdomain('AccuWeather', '%s%s' % (resolveFilename(SCOPE_PLUGINS), 'Extensions/AccuWeather/locale/'))

def _(txt):
    t = gettext.dgettext('AccuWeather', txt)
    if t == txt:
        t = gettext.gettext(txt)
    return t


config.plugins.AccuWeatherPlugin = ConfigSubsection()
config.plugins.AccuWeatherPlugin.entriescount = ConfigInteger(0)
config.plugins.AccuWeatherPlugin.default = ConfigInteger(1)
config.plugins.AccuWeatherPlugin.Entries = ConfigSubList()
config.plugins.AccuWeatherPlugin.acuentriescount = ConfigInteger(0)
config.plugins.AccuWeatherPlugin.acuEntries = ConfigSubList()
config.plugins.AccuWeatherPlugin.foreentriescount = ConfigInteger(0)
config.plugins.AccuWeatherPlugin.foreEntries = ConfigSubList()
initConfig()
initConfigacu()
initConfigfore()
UserAgent = 'Mozilla/5.0 (X11; U; Linux x86_64; de; rv:1.9.0.15) Gecko/2009102815 Ubuntu/9.04 (jaunty) Firefox/3.'

from enigma import eSize, ePoint
from Tools.Directories import fileExists, resolveFilename, SCOPE_SKIN
from Components.config import config

def weatherScrollBar(objectoself, nombrelista = 'lista', barra = 'barrascroll', altoitem = 25, imagen = None):
    nombrebarraArr = barra + '_arr'
    nombrebarraAbj = barra + '_abj'
    numele = 999
    if nombrelista == barra:
        nombrelista = nombrebarraArr
    elif not barra == 'servicelist':
        try:
            numele = len(objectoself[nombrelista].list)
        except:
            pass

    try:
        alto = objectoself[nombrelista].instance.size().height()
        elepag = int(alto / altoitem)
        if numele > elepag:
            pass
        else:
            objectoself[nombrebarraArr].hide()
            objectoself[nombrebarraAbj].hide()
            return
        ancho = objectoself[nombrelista].instance.size().width()
        if ancho > 20:
            if imagen:
                nomskin = str(config.skin.primary_skin.value).split('/')[0]
                rutaSkin = resolveFilename(SCOPE_SKIN) + nomskin + '/'
                if fileExists(rutaSkin + 'scroll.png'):
                    laimagen = rutaSkin + 'scroll.png'
                    objectoself[nombrebarraArr].instance.setPixmapFromFile(laimagen)
                else:
                    return
                if fileExists(rutaSkin + 'scrollb.png'):
                    laimagen = laimagen = rutaSkin + '/scrollb.png'
                    objectoself[nombrebarraAbj].instance.setPixmapFromFile(laimagen)
                else:
                    return
            posx = objectoself[nombrelista].instance.position().x()
            posy = objectoself[nombrelista].instance.position().y()
            wsize = (20, alto - 30)
            asizex = objectoself[nombrebarraArr].instance.size().width()
            asizey = objectoself[nombrebarraArr].instance.size().height()
            if not asizex == 20 or not asizey == alto - 30:
                objectoself[nombrebarraArr].instance.resize(eSize(*wsize))
            wsize = (20, 30)
            asizex = objectoself[nombrebarraAbj].instance.size().width()
            asizey = objectoself[nombrebarraAbj].instance.size().height()
            if not asizex == 20 or not asizey == 30:
                objectoself[nombrebarraAbj].instance.resize(eSize(*wsize))
            ax = objectoself[nombrebarraArr].instance.position().x()
            ay = objectoself[nombrebarraArr].instance.position().y()
            if not ax == posx + ancho - 20 or not ay == posy:
                objectoself[nombrebarraArr].instance.move(ePoint(posx + ancho - 20, posy))
            ax = objectoself[nombrebarraAbj].instance.position().x()
            ay = objectoself[nombrebarraAbj].instance.position().y()
            if not ax == posx + ancho - 20 or not ay == posy + alto - 30:
                objectoself[nombrebarraAbj].instance.move(ePoint(posx + ancho - 20, posy + alto - 30))
            objectoself[nombrebarraArr].show()
            objectoself[nombrebarraAbj].show()
    except:
        pass

def devimagentemperatura(temperatura):
    if temperatura <= 3:
        laimagen = 't0-fs8.png'
    elif temperatura <= 10:
        laimagen = 't1-fs8.png'
    elif temperatura <= 19:
        laimagen = 't2-fs8.png'
    elif temperatura <= 28:
        laimagen = 't3-fs8.png'
    elif temperatura <= 36:
        laimagen = 't4-fs8.png'
    else:
        laimagen = 't5-fs8.png'
    return laimagen


def equivnoche(imagen):
    listaequi = {'21': '43',
     '14': '39',
     '17': '41',
     '13': '40',
     '5': '37',
     '3': '35',
     '4': '36',
     '6': '38',
     '1': '33',
     '2': '34',
     '16': '42',
     '20': '44',
     '23': '44'}
    if imagen not in listaequi:
        return imagen
    return listaequi[imagen]


def devgificono(imagen, actual = False):
    listaimagenes = {'chance_of_rain.gif': '14',
     'chance_of_snow.gif': '21',
     'chance_of_storm.gif': '17',
     'cloudy.gif': '7',
     'dusty.gif': '11',
     'flurries.gif': '13',
     'fog.gif': '5',
     'foggy.gif': '5',
     'hazy.gif': '5',
     'icy.gif': '31',
     'mist.gif': '18',
     'mostly_cloudy.gif': '6',
     'mostly_sunny.gif': '4',
     'partly_cloudy.gif': '3',
     'rain.gif': '12',
     'rain_snow.gif': '26',
     'showers.gif': '14',
     'sleet.gif': '29',
     'smoke.gif': '8',
     'snow.gif': '22',
     'storm.gif': '15',
     'sunny.gif': '1',
     'thunderstorm.gif': '99'}
    if imagen not in listaimagenes:
        return '14_int-fs8.png'
    valor = listaimagenes[imagen]
    if actual:
        t2 = time.localtime()
        chora = int(time.strftime('%H', t2))
        valornoche = equivnoche(valor)
        if valornoche and (chora >= 21 or chora < 7):
            valor = valornoche
    return valor + '_int-fs8.png'


def devImagen(cadena, etiqueta):
    tempcad = devStrTm(cadena, etiqueta, '')
    devcad = devStrTm(tempcad, 'src="', '"')
    return devcad


def devHtml(cadena, etiqueta):
    tempcad = devStrTm(cadena, etiqueta, '')
    devcad = devStrTm(tempcad, '>', '<')
    return devcad.replace('&deg;', '\xc2\xba')


def devStrTm(cadena, inicio, fin):
    try:
        if inicio not in cadena:
            return ''
        str = cadena.split(inicio)[1]
        if not fin == '':
            str = str.split(fin)[0]
        return str
    except:
        return ''


class WeatherIconItem():

    def __init__(self, url = '', filename = '', descarga = None, index = -1, error = False):
        self.url = url
        self.filename = filename
        self.index = index
        self.error = error
        self.cancel = False
        self.descarga = descarga


def getXML(url):
    return client.getPage(url, agent=UserAgent)


def download(item):
    return client.downloadPage(item.url, file(item.filename, 'wb'), agent=UserAgent)


def main(session, **kwargs):
        #config.plugins.AccuWeatherPlugin.default.value = 1
        #config.plugins.AccuWeatherPlugin.default.save()
        #config.plugins.AccuWeatherPlugin.save()
        #session.open(ForecaWeatherPlugin)
	from xbmc import MeteoMain
	session.open(MeteoMain)

def Plugins(**kwargs):
    list = [PluginDescriptor(name=_('Weather Info'), description=_('Weather info Plugin'), where=[PluginDescriptor.WHERE_PLUGINMENU], fnc=main)]
    return list


class IniciaSelDetalle(MenuList):

    def __init__(self, list, enableWrapAround = False):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setItemHeight(66)
        self.l.setFont(0, gFont('Regular', 28))
        self.l.setFont(1, gFont('Regular', 21))
        self.l.setFont(2, gFont('Regular', 25))
        self.l.setFont(3, gFont('Regular', 18))
        self.l.setFont(4, gFont('Regular', 19))


def IniciaSelDetalleEntry(texto, hora = None, iconotiempo = None, temperatura = None, iconoviento = None, viento = None, descripcion = None):
    res = [texto]
    if hora == None:
        res.append(MultiContentEntryText(pos=(0, 0), size=(970, 66), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=texto))
    else:
        res.append(MultiContentEntryText(pos=(0, 0), size=(74, 66), flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, font=1, text=hora))
        png = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/' + iconotiempo
        if fileExists(png):
            fpng = LoadPixmap(png)
            res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
             85,
             -4,
             74,
             66,
             fpng))
        tempimagen = None
        try:
            tempimagen = devimagentemperatura(int(temperatura.strip().split('\xc2\xba')[0]))
        except:
            pass

        if not tempimagen == None:
            png = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/p' + tempimagen
            if fileExists(png):
                fpng = LoadPixmap(png)
                res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
                 157,
                 18,
                 18,
                 27,
                 fpng))
        res.append(MultiContentEntryText(pos=(173, 0), size=(140, 66), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=temperatura))
        png = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/' + iconoviento
        if fileExists(png):
            fpng = LoadPixmap(png)
            res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
             276,
             13,
             29,
             40,
             fpng))
        res.append(MultiContentEntryText(pos=(310, 0), size=(140, 66), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=3, text=viento))
        res.append(MultiContentEntryText(pos=(422, 0), size=(530, 66), flags=RT_HALIGN_LEFT | RT_WRAP | RT_VALIGN_CENTER, font=4, text=descripcion))
    return res


class IniciaSelList2(MenuList):

    def __init__(self, list, enableWrapAround = False):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setItemHeight(70)
        self.l.setFont(0, gFont('Regular', 21))
        self.l.setFont(1, gFont('Regular', 17))


def IniciaSelListEntry2(numero):
    res = [numero]
    if numero == 0:
        texto = _('google.com API Wheater')
    elif numero == 1:
        texto = _('foreca.com Wheater Information')
    else:
        texto = _('accuWheater.com Information')
    res.append(MultiContentEntryText(pos=(150, 0), size=(620, 70), flags=RT_HALIGN_LEFT | RT_WRAP | RT_VALIGN_CENTER, font=0, text=texto))
    png = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/icono' + str(numero) + '-fs8.png'
    if fileExists(png):
        fpng = LoadPixmap(png)
        res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
         30,
         3,
         107,
         64,
         fpng))
    if numero == config.plugins.AccuWeatherPlugin.default.value:
        png = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/checkok.png'
        fpng = LoadPixmap(png)
        res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
         1,
         18,
         24,
         24,
         fpng))
    return res


class MainWheaterPlugin(Screen):
    skin = '''<screen name="MainWheaterPlugin" position="center,center" size="660,258" title="%s %s">
	  <widget name="list" position="9,29" size="642,140" scrollbarMode="showOnDemand" />
	  <widget name="key_green" position="345,209" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	  <ePixmap name="green" position="346,209" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	  <widget name="key_yellow" position="510,209" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	  <ePixmap name="chekgreen" position="323,218" zPosition="4" size="24,24" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/checkok.png" transparent="1" alphatest="on" />
	  <ePixmap name="yellow" position="511,209" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	  </screen>''' % (_('AccuWeatherWeatherPlugin: Select Source'), ' ')

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['key_green'] = Button(_('Default'))
        self['key_yellow'] = Button(_('Setup'))
        self['list'] = IniciaSelList2([])
        self['actions'] = ActionMap(['WizardActions', 'MenuActions', 'ShortcutActions'], {'ok': self.keyOK,
         'back': self.keyClose,
         'green': self.keyGreen,
         'yellow': self.keyYellow}, -1)
        self.onLayoutFinish.append(self.buildList)

    def buildList(self):
        nlista = []
        nlista.append(IniciaSelListEntry2(0))
        nlista.append(IniciaSelListEntry2(1))
        self['list'].setList(nlista)
        self['list'].moveToIndex(config.plugins.AccuWeatherPlugin.default.value)

    def updateList(self):
        self.buildList()

    def keyClose(self):
        self.close()

    def keyGreen(self):
        indice = self['list'].getSelectionIndex()
        config.plugins.AccuWeatherPlugin.default.value = indice
        config.plugins.AccuWeatherPlugin.default.save()
        os.system('rm -f /tmp/wf_acuspz.xml')
        os.system('rm -f /tmp/wf_forespz.xml')
        os.system('rm -f /tmp/wf_spz.xml')
        self.updateList()

    def keyOK(self):
        indice = self['list'].getSelectionIndex()
        if indice == 0:
            self.session.open(AccuWeatherPlugin)
        elif indice == 1:
            self.session.open(ForecaWeatherPlugin)

    def keyYellow(self):
        indice = self['list'].getSelectionIndex()
        if indice == 0:
            self.session.openWithCallback(self.setupFinished, WeatherPluginEntriesListConfigScreen)
        elif indice == 1:
            self.session.openWithCallback(self.setupFinished, WeatherPluginEntriesListConfigScreenfore)

    def setupFinished(self, asnw, ans2):
        pass


class ForecaWeatherPlugin(Screen):
    skin = '''<screen name="ForecaWeatherPlugin" position="center,65" size="970,625" title="AccuWeather - foreca.com">
	      <widget name="lugar" position="36,3" zPosition="2" size="512,28" font="Regular;23" transparent="1" valign="center" backgroundColor="#000000" />
	      <widget name="info_entradas" position="753,3" zPosition="3" size="166,22" font="Regular; 16" transparent="1" halign="right" backgroundColor="#000000" />
	      <widget name="current_icon" position="7,46" zPosition="1" size="74,74" alphatest="blend" />\n
	      <widget name="temperatura" position="98,79" zPosition="3" size="98,30" font="Regular; 26" transparent="1" noWrap="1" halign="left" backgroundColor="#000000" />
	      <widget name="condicion" position="201,48" zPosition="1" size="270,225" font="Regular; 18" transparent="1" backgroundColor="#000000" valign="top" />
	      <widget name="viento" position="7,147" zPosition="1" size="191,65" font="Regular;17" transparent="1" backgroundColor="#000000" valign="top" />
	      <eLabel name="lin0" position="473,25" size="1,250" zPosition="1" backgroundColor="#05303030" />
	      <widget name="dia1" position="561,29" zPosition="1" size="400,25" halign="left" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia1" position="479,29" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia1" position="561,53" zPosition="1" size="412,55" halign="left" valign="top" font="Regular; 17" transparent="1" backgroundColor="#000000" />
	      <widget name="dia2" position="561,112" zPosition="1" size="400,25" halign="left" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia2" position="479,112" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia2" position="561,136" zPosition="1" size="412,55" halign="left" valign="top" font="Regular; 17" transparent="1" backgroundColor="#000000" />
	      <widget name="dia3" position="561,194" zPosition="1" size="400,25" halign="left" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia3" position="479,194" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia3" position="561,218" zPosition="1" size="412,55" halign="left" valign="top" font="Regular; 17" transparent="1" backgroundColor="#000000" />
	      <widget name="statustext" position="0,23" zPosition="2" size="970,605" font="Regular;20" halign="center" valign="center" transparent="1" backgroundColor="#10bfbfbf" />
	      <widget name="ico_left" position="15,3" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_left-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="ico_right" position="930,3" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_right-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="ico_menu" position="750,355" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/menu.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_menu" position="786,356" size="182,25" transparent="1" font="Regular; 16" zPosition="1" noWrap="1" />
	      <widget name="ico_l" position="750,413" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/izq-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_l" position="786,414" size="182,25" transparent="1" font="Regular; 16" zPosition="1" noWrap="1" />
	      <widget name="ico_r" position="750,444" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/dch-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_r" position="786,445" size="181,25" transparent="1" font="Regular; 16" zPosition="1" noWrap="1" />
	      <eLabel name="lin1" position="10,278" size="951,1" zPosition="1" backgroundColor="#05303030" />
	      <eLabel name="lin2" position="726,288" size="1,330" zPosition="1" backgroundColor="#05303030" />
	      <widget name="ico_blue" position="750,544" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/green.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_blue" position="786,545" size="182,25" transparent="1" font="Regular; 16" zPosition="1" noWrap="1" />

	      <widget name="satelite" position="132,59" size="720,480" alphatest="blend" zPosition="10" transparent="1" />
	      <widget name="statustext2" position="0,3" zPosition="8" size="970,627" font="Regular;20" halign="center" valign="center" transparent="0" />
	      <widget name="barra" position="11,288" zPosition="2" size="702,330" alphatest="blend" />
	      <widget name="info_barra" position="62,308" zPosition="1" size="600,290" font="Regular;20" halign="center" valign="center" transparent="0" />
	      <ePixmap name="logofuente" position="10,213" size="107,63" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/icono1-fs8.png" transparent="1" alphatest="blend" />
	      <widget name="le_barra" position="132,542" zPosition="10" size="600,35" alphatest="blend" />
	      <widget name="ico_temp" position="59,46" zPosition="2" size="74,74" alphatest="blend" />

	      <widget name="fondo_detalle" position="0,31" size="948,594" alphatest="blend" zPosition="10" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/fondolista-fs8.png"/>
	      <widget name="detallado" position="0,31" zPosition="8" size="970,594" scrollbarMode="showOnDemand" />

	      <widget name="ico_red" position="750,504" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/red.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_red" position="786,505" size="182,25" transparent="1" font="Regular; 16" zPosition="1" noWrap="1" />
	      <widget name="ico_vie" position="5,132" zPosition="2" size="29,40" alphatest="blend" />
	      <widget name="barrapix_arr" position="0,31" zPosition="9" size="970,594" alphatest="blend" transparent="1" />
	      <widget name="barrapix_abj" position="0,0" zPosition="9" size="20,20" alphatest="blend" transparent="1" />
	      </screen>'''

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['WizardActions',
         'DirectionActions',
         'ColorActions',
         'EPGSelectActions',
         'MenuActions'], {'back': self.exit,
         'input_date_time': self.config,
         'menu': self.config,
         'right': self.nextItem,
         'left': self.previousItem,
         'up': self.kup,
         'down': self.kdown,
         'green': self.selimagen,
         'red': self.pronostico}, -1)
        self.sisat = False
        self.listatitulos = []
        self['statustext'] = Label()
        self['statustext2'] = Label()
        self['detallado'] = IniciaSelDetalle([])
        self['fondo_detalle'] = Pixmap()
        self.detalle = False
        self['barrapix_arr'] = Pixmap()
        self['barrapix_abj'] = Pixmap()
        self['infosat'] = Pixmap()
        self['barra'] = WeatherIcon()
        self['ico_temp'] = Pixmap()
        self['ico_vie'] = Pixmap()
        self['le_barra'] = Pixmap()
        self['ico_menu'] = Pixmap()
        self['ico_left'] = Pixmap()
        self['ico_right'] = Pixmap()
        self['ico_r'] = Pixmap()
        self['ico_l'] = Pixmap()
        self['texto_menu'] = Label(_('List'))
        self['texto_l'] = Label(_('Previous'))
        self['texto_r'] = Label(_('Next'))
        self['current_icon'] = WeatherIcon()
        self['satelite'] = WeatherIcon()
        self['lugar'] = Label()
        self['info_barra'] = Label(_('Downloading Detailed image 5 day forecast'))
        self['info_entradas'] = Label()
        self['temperatura'] = Label()
        self['condicion'] = Label()
        self['viento'] = Label()
        self.descargaactiva = None
        self['texto_blue'] = Label(_('Images satellite') + '...')
        self['texto_red'] = Label(_('Detailed forecast'))
        self['ico_blue'] = Pixmap()
        self['ico_red'] = Pixmap()
        for i in range(1, 4):
            self['dia%s' % i] = Label()
            self['icono_dia%s' % i] = WeatherIcon()
            self['info_dia%s' % i] = Label()

        self.appdir = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/'
        if not os.path.exists(self.appdir):
            os.mkdir(self.appdir)
        self.maxdetalle = 3
        self.inidetalle = 3
        self.weatherPluginEntryIndex = -1
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.foreentriescount.value
        if self.weatherPluginEntryCount >= 1:
            self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.foreEntries[0]
            self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
        self.descargando = False
        self.diadetalle = 0
        self.onLayoutFinish.append(self.startRun)
        self.chequeado = False
        self.onShow.append(self.chequeaVacio)

    def chequeaVacio(self):
        if not self.chequeado and config.plugins.AccuWeatherPlugin.foreentriescount.value == 0:
            self.chequeado = True
            self.config()
            return
        if config.plugins.AccuWeatherPlugin.foreentriescount.value == 0:
            self.exit()

    def actualizaScrolls(self, forzar = False):
        if self.detalle and not forzar:
            weatherScrollBar(objectoself=self, nombrelista='barrapix', barra='barrapix', altoitem=25, imagen=True)
            self['barrapix_arr'].show()
            self['barrapix_abj'].show()
        else:
            self['barrapix_arr'].hide()
            self['barrapix_abj'].hide()

    def xmlCallbackPro(self, xmlstring, num):
        self.setalle = True
        xmlstring = devStrTm(xmlstring, '<h4>', '<div class="datecopy">').replace('<strong>', '').replace('</strong>', '').replace('\t', '').replace('   ', '').replace('  ', '').replace('<br /><br />', '<br />').replace('<br /> <br />', '<br />').replace('\n', '').replace('&deg;', '\xc2\xbaC')
        if num == 0:
            self.listatitulos = []
            lista = []
        else:
            lista = self['detallado'].list
        lafecha = devStrTm(xmlstring, '<h6>', '</h6>').replace('<span>', '').replace('</span>', '').strip()
        if num == 0:
            lafecha = _('Today') + ', ' + lafecha
        elif num == 1:
            lafecha = _('Tomorrow') + ', ' + lafecha
        lista.append(IniciaSelDetalleEntry('--- ' + lafecha + ' ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------'))
        self.listatitulos.append(lafecha)
        arrlista = xmlstring.split('<div class="row')
        for ele in arrlista:
            hora = devHtml(ele, 'class="c0"').replace('\t', '').replace('\n', '').replace('<span>', '').replace('</span>', '').strip()
            if len(hora) > 3:
                texto = hora
                iconotiempo = devStrTm(ele, '<div class="c1">', '</div>').replace('\t', '').replace('\n', '').replace('<span>', '').replace('</span>', '').strip()
                iconotiempo = self.gesImagenLista(iconotiempo)
                temperatura = devStrTm(ele, '<div class="c4">', '</div>')
                if '<span' in temperatura:
                    temperatura = devHtml(temperatura, 'span')
                temperatura = temperatura.replace('\t', '').replace('<br />', '').replace('\n', '').replace('<span>', '').replace('</span>', '').strip()
                viento = devHtml(ele, 'class="c2"').replace('\t', '').replace('\n', '').replace('<span>', '').replace('</span>', '').strip()
                iconoviento = devStrTm(ele, '<img src="/img/symb-wind/', '.gif') + '-fs8.png'
                viento = devHtml(ele, 'img src').replace('\t', '').replace('\n', '').replace('<span class="warm">', '').replace('<span>', '').replace('</span>', '').strip()
                descripcion = devStrTm(ele, '<div class="c3">', '</div>').replace('\t', '').replace('\n', '').replace('<span>', '').replace('</span>', '').replace('<br />', 'x$x').replace('%x$x', '%, ').replace('x$x', '\n').strip()[:-1]
                lista.append(IniciaSelDetalleEntry(texto, hora, iconotiempo, temperatura, iconoviento, viento, descripcion))
                self.listatitulos.append(lafecha)

        self['detallado'].setList(lista)
        if num == 0:
            try:
                self.setTitle(self['lugar'].getText() + ' - ' + lafecha)
            except:
                pass

            self['detallado'].moveToIndex(0)
        if num >= self.maxdetalle - 1:
            self['statustext2'].hide()
            self.detalle = True
            self['detallado'].show()
            self['fondo_detalle'].show()
            self.actualizaScrolls()
            if num < self.maxdetalle and self.maxdetalle != self.inidetalle:
                try:
                    self['detallado'].moveToIndex(self['detallado'].getSelectionIndex() + 1)
                except:
                    pass

                try:
                    self.setTitle(self['lugar'].getText() + ' - ' + self.listatitulos[self['detallado'].getSelectionIndex()])
                except:
                    pass

        if num >= self.maxdetalle:
            pass
        else:
            self.devPro(num + 1)

    def devPro(self, num = 0):
        ciudad = self.weatherPluginEntry.city.value
        dominio = self.weatherPluginEntry.dominio.value
        pais = self.weatherPluginEntry.pais.value
        t2 = time.localtime()
        dia = int(time.strftime('%d', t2)) + num
        cdia = str(dia)
        if len(cdia) == 1:
            cdia = '0' + cdia
        cmes = str(time.strftime('%m', t2))
        cano = str(time.strftime('%Y', t2))
        cfecha = cano + cmes + cdia
        asp = '?details=' + cfecha
        url = 'http://www.foreca.%s/%s/%s%s' % (dominio,
         pais,
         ciudad,
         asp)
        txt = '...'
        self['statustext2'].setText(_('Downloading') + ' ' + _('Detailed forecast') + '\n' + _('Wait') + txt + '[' + str(self.maxdetalle - num) + ']')
        try:
            self.setTitle(self['lugar'].getText() + ' - ' + _('Detailed forecast'))
        except:
            pass

        self.actualizaScrolls(True)
        getXML(url).addCallback(self.xmlCallbackPro, num).addErrback(self.error)

    def pronostico(self):
        if self.detalle:
            self.desdet()
            return
        if self.sisat:
            self.dessat()
            return
        if self.diadetalle > 0:
            self['statustext2'].setText(_('Downloading') + ' ' + _('Detailed forecast') + '\n' + _('Wait') + '')
            self['statustext2'].show()
            self.detalle = True
            if self.weatherPluginEntry is not None:
                self.maxdetalle = self.inidetalle
                self.devPro()

    def selimagen(self):
        if self.detalle:
            return
        if self.sisat:
            return
        contextFileList = [(_('Satellite'), 'sat'),
         (_('Temperature'), 'temp'),
         (_('Cloudiness'), 'cloud'),
         (_('Amount of Precipitacion'), 'rain')]
        dei = self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_('Select satellite image') + ':', list=contextFileList)

    def SysExecution(self, answer):
        answer = answer and answer[1]
        asp = None
        numero = None
        if answer:
            if answer == 'temp':
                numero = '1'
            elif answer == 'rain' or answer == 'pressure':
                numero = '2'
            asp = '?map=' + answer
        if asp:
            self.muestrasat(asp, numero)

    def desdet(self):
        self['detallado'].hide()
        self['fondo_detalle'].hide()
        self.detalle = False
        self['statustext2'].hide()
        self.actualizaScrolls(True)
        self.setTitle(_('AccuWeatherWeatherPlugin') + ' (foreca.com)')

    def exit(self):
        if self.detalle:
            self.desdet()
            return
        if self.sisat:
            self.dessat()
            return
        self.close()

    def kup(self):
        if self.detalle:
            self['detallado'].pageUp()
            self.actualizapos()
            return

    def kdown(self):
        if self.detalle:
            self['detallado'].pageDown()
            self.actualizapos()
            return

    def muestrasat(self, asp, numero):
        if self.sisat:
            self.dessat()
            return
        appimagedir = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/'
        if numero:
            self['le_barra'].instance.setPixmapFromFile(appimagedir + 'barrafore' + numero + '.png')
            self['le_barra'].show()
        else:
            self['le_barra'].hide()
        self['statustext2'].setText(_('Downloading') + ' ' + _('Images satellite') + '\n' + _('Wait') + '...')
        self['statustext2'].show()
        self.sisat = True
        if self.weatherPluginEntry is not None:
            ciudad = self.weatherPluginEntry.city.value
            dominio = self.weatherPluginEntry.dominio.value
            pais = self.weatherPluginEntry.pais.value
            url = 'http://www.foreca.%s/%s/%s%s' % (dominio,
             pais,
             ciudad,
             asp)
            getXML(url).addCallback(self.xmlCallbackSat).addErrback(self.error)

    def startRun(self):
        self['detallado'].hide()
        self['fondo_detalle'].hide()
        self.descargaactiva = None
        self.diadetalle = 0
        self.detalle = False
        self['infosat'].hide()
        self['satelite'].hide()
        self['barra'].hide()
        self['le_barra'].hide()
        self['info_barra'].hide()
        self['ico_temp'].hide()
        self['ico_vie'].hide()
        if self.weatherPluginEntry is not None:
            ciudad = self.weatherPluginEntry.city.value
            dominio = self.weatherPluginEntry.dominio.value
            pais = self.weatherPluginEntry.pais.value
            self['ico_menu'].hide()
            self['texto_menu'].hide()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
            self['texto_blue'].hide()
            self['ico_blue'].hide()
            self['ico_red'].hide()
            self['texto_red'].hide()
            self['statustext2'].hide()
            self['statustext'].setText(_('Getting weather information...') + '\n[' + ciudad + ', ' + ' - ' + pais + ']')
            cana = ''
            if self.weatherPluginEntryIndex == 1:
                cana = '(' + _('Default') + ') '
            self['info_entradas'].setText(cana + str(self.weatherPluginEntryIndex) + ' ' + _('of') + ' ' + str(self.weatherPluginEntryCount))
            url = 'http://www.foreca.%s/%s/%s' % (dominio, pais, ciudad)
            self.descargando = True
            getXML(url).addCallback(self.xmlCallback).addErrback(self.error)
        else:
            self['statustext'].setText(_("No locations defined...\nPress 'Menu' to do that."))
            self['ico_menu'].show()
            self['texto_menu'].show()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
            self['texto_blue'].hide()
            self['ico_red'].hide()
            self['texto_red'].hide()
            self['ico_blue'].hide()
        self['statustext'].show()

    def dessat(self):
        os.system('rm /tmp/foreca/*')
        self['satelite'].hide()
        self['statustext2'].hide()
        self['infosat'].hide()
        self['le_barra'].hide()
        self.sisat = False

    def actualizapos(self):
        numero = len(self['detallado'].list)
        if numero <= 0:
            return
        indice = self['detallado'].getSelectionIndex()
        try:
            self.setTitle(self['lugar'].getText() + ' - ' + self.listatitulos[indice])
        except:
            pass

        if numero == indice + 1:
            if self.maxdetalle == self.inidetalle:
                self.session.openWithCallback(self.cerrarcb, MessageBox, _('Want to download forecast of the next 4 days?'), default=True)
            else:
                self['detallado'].moveToIndex(0)
                try:
                    self.setTitle(self['lugar'].getText() + ' - ' + self.listatitulos[0])
                except:
                    pass

    def cerrarcb(self, respuesta):
        if respuesta:
            self.maxdetalle = self.maxdetalle + 4
            self['detallado'].hide()
            self['fondo_detalle'].hide()
            self['statustext2'].show()
            self.devPro(self.inidetalle + 1)
        else:
            self['detallado'].moveToIndex(0)
            try:
                self.setTitle(self['lugar'].getText() + ' - ' + self.listatitulos[0])
            except:
                pass

    def nextItem(self):
        if self.detalle:
            self['detallado'].pageDown()
            self.actualizapos()
            return
        if self.descargando:
            return
        if self.sisat:
            self.dessat()
            return
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex < self.weatherPluginEntryCount:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex + 1
            else:
                self.weatherPluginEntryIndex = 1
            self.setItem()

    def previousItem(self):
        if self.detalle:
            self['detallado'].pageUp()
            self.actualizapos()
            return
        if self.descargando:
            return
        if self.sisat:
            self.dessat()
            return
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex >= 2:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex - 1
            else:
                self.weatherPluginEntryIndex = self.weatherPluginEntryCount
            self.setItem()

    def setItem(self):
        self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.foreEntries[self.weatherPluginEntryIndex - 1]
        self.clearFields()
        self.startRun()

    def clearFields(self):
        self['le_barra'].hide()
        self['lugar'].setText('')
        self['info_entradas'].setText('')
        self['temperatura'].setText('')
        self['condicion'].setText('')
        self['viento'].setText('')
        self['info_barra'].hide()
        self['barra'].hide()
        self['texto_blue'].hide()
        self['ico_blue'].hide()
        self['ico_temp'].hide()
        self['ico_vie'].hide()
        self['ico_red'].hide()
        self['texto_red'].hide()
        for i in range(1, 4):
            self['dia%s' % i].setText('')
            self['icono_dia%s' % i].hide()
            self['info_dia%s' % i].setText('')

        self['current_icon'].hide()
        self['ico_menu'].hide()
        self['texto_menu'].hide()
        self['ico_left'].hide()
        self['ico_right'].hide()
        self['ico_l'].hide()
        self['ico_r'].hide()
        self['texto_l'].hide()
        self['texto_r'].hide()

    def errorIconDownload(self, error = None, item = None):
        item.error = True

    def finishedIconDownload(self, result, item):
        if not item.error:
            if item.descarga == None or item.descarga == self.descargaactiva:
                self.showIcon(item.index, item.filename)

    def showIcon(self, nombre, filename):
        self[nombre].updateIcon(filename)
        self[nombre].show()
        self[nombre].cancel = False

    def xmlCallbackSat(self, xmlstring):
        self['statustext2'].show()
        laimagen = devImagen(xmlstring, '<div id="symb_clipcontainer"')
        if len(laimagen) <= 2:
            laimagen = devImagen(xmlstring, 'id="animap"')
        url = laimagen
        nombre = 'satelite'
        if 'http://' not in url:
            url = 'http://www.foreca.' + self.weatherPluginEntry.dominio.value + url
        parts = string.split(url, '/')
        os.system('mkdir /tmp/foreca')
        filename = '/tmp/foreca/' + devStrTm('*' + parts[-1], '*', '?')
        IconDownloadList = []
        IconDownloadList.append(WeatherIconItem(url=url, filename=filename, index=nombre))
        if len(IconDownloadList) != 0:
            ds = defer.DeferredSemaphore(tokens=len(IconDownloadList))
            downloads = [ ds.run(download, item).addErrback(self.errorIconDownload, item).addCallback(self.finishedIconDownload, item) for item in IconDownloadList ]
            finished = defer.DeferredList(downloads).addErrback(self.error)

    def xmlCallback(self, xmlstring):
        self.descargando = False
        self['statustext'].hide()
        self['ico_menu'].show()
        self['texto_menu'].show()
        self['texto_blue'].show()
        self['ico_blue'].show()
        self['info_barra'].show()
        self['ico_red'].show()
        self['texto_red'].show()
        if self.weatherPluginEntryCount > 1:
            self['ico_left'].show()
            self['ico_right'].show()
            self['ico_l'].show()
            self['ico_r'].show()
            self['texto_l'].show()
            self['texto_r'].show()
        self['lugar'].show()
        self['temperatura'].show()
        self['condicion'].show()
        self['viento'].show()
        for i in range(1, 4):
            self['dia%s' % i].show()
            self['info_dia%s' % i].show()

        xmlstring = devStrTm(xmlstring, '<h1 class="entry-title"', '<div class="datecopy">').replace('<strong>', '').replace('</strong>', '').replace('\t', '').replace('   ', '').replace('  ', '').replace('<br /><br />', '<br />').replace('<br /> <br />', '<br />').replace('\n', '').replace('&deg;', '\xc2\xbaC')
        self['lugar'].setText(devStrTm(xmlstring, '>', '<').strip())
        tempact = devHtml(xmlstring, 'warm txt-xxlarge').replace('\t', '').replace('\n', '').strip()
        self['temperatura'].setText(tempact)
        lacondicion = devStrTm(xmlstring, '<div class="right txt-tight">', '</div>').replace('<br />', '\n').replace('\n ', '\n')
        self['condicion'].setText(lacondicion)
        simirar = False
        itemp = None
        if 'cc_symb">' not in xmlstring:
            simirar = True
        try:
            tempact = tempact.split(' ')[0]
            itemp = int(tempact)
        except:
            pass

        if not itemp == None and not simirar:
            self['ico_temp'].show()
            filenamepng = self.appdir + devimagentemperatura(itemp)
            self['ico_temp'].instance.setPixmapFromFile(filenamepng)
        if not simirar:
            itemp = None
        temp = self.gesImagen('current_icon', xmlstring, simirar, itemp)
        tempviento = devStrTm(xmlstring, '/img/symb-wind', '<br />')
        dirviento = devStrTm(tempviento, 'alt="', '"')
        dirviento = dirviento.replace('N', _('North')).replace('S', _('South')).replace('E', _('East')).replace('W', _('West')).replace('NorteOeste', 'NorOeste').replace('NorteEste', 'NorEste')
        iviento = devStrTm(tempviento, '/>', '').replace('<br />', '')
        if len(dirviento + ' ' + iviento) > 2:
            self['viento'].setText('        ' + _('Wind') + ':\n' + dirviento + ' ' + iviento)
            ivien = devStrTm(xmlstring, '/img/symb-wind/', '.gif') + '-fs8.png'
            filenamepng = self.appdir + ivien
            self['ico_vie'].instance.setPixmapFromFile(filenamepng)
            self['ico_vie'].show()
        else:
            self['viento'].setText(' ')
        tempdias = devStrTm(xmlstring, '<div class="c2">', '').replace('<br />', '')
        arrdias = tempdias.split('<div class="c2_a">')
        self.diadetalle = []
        for i in range(1, len(arrdias)):
            if i >= 4:
                break
            eltexto = arrdias[i]
            texto = devStrTm(eltexto, 'title="', '"')
            temp1 = devStrTm(eltexto, '<span>', '</span>')
            temp2 = devStrTm(eltexto, '</span>', '</span>')
            temp2 = devStrTm(temp2, '<span>', '</span>')
            texto = texto + '\n' + temp1 + ' / ' + temp2
            nombre = devHtml(eltexto, 'a href="')
            self['dia%s' % i].setText(nombre)
            temp = self.gesImagen('icono_dia%s' % i, eltexto)
            self['info_dia%s' % i].setText(texto)

        self['info_barra'].show()
        self['barra'].hide()
        laimagen = devImagen(xmlstring, '"meteogram"')
        nombre = 'barra'
        url = 'http://www.foreca.' + self.weatherPluginEntry.dominio.value + laimagen
        os.system('mkdir /tmp/foreca')
        os.system('rm /tmp/foreca/barra*.png')
        erid = devStrTm(url, 'loc_id=', '&')
        self.descargaactiva = erid
        t2 = time.localtime()
        chora = str(time.strftime('%H%M', t2))
        filename = '/tmp/foreca/barra_' + erid + '_' + chora + '.png'
        IconDownloadList = []
        IconDownloadList.append(WeatherIconItem(url=url.replace('&amp;', '&'), filename=filename, index=nombre, descarga=erid))
        if len(IconDownloadList) != 0:
            ds = defer.DeferredSemaphore(tokens=len(IconDownloadList))
            downloads = [ ds.run(download, item).addErrback(self.errNada, item).addCallback(self.finishedIconDownload, item) for item in IconDownloadList ]
            finished = defer.DeferredList(downloads).addErrback(self.errNada)
        if self.weatherPluginEntryIndex == 1:
            try:
                ertexto = xmlstring
                sourceEncoding = 'utf-8'
                targetEncoding = 'iso-8859-1'
                f = open('/tmp/wf_forespz.xml', 'w')
                f.write(ertexto)
                f.close()
            except:
                pass

    def errNada(self, error = None, item = None):
        self['info_barra'].hide()

    def getImagen(self, codigo, mirarnoche = False):
        listaimagenes = {'111': '5',
         '000': '1',
         '100': '2',
         '200': '3',
         '210': '14',
         '211': '21',
         '212': '21',
         '220': '13',
         '221': '20',
         '222': '20',
         '240': '17',
         '300': '6',
         '310': '13',
         '311': '23',
         '312': '23',
         '320': '13',
         '321': '20',
         '322': '20',
         '340': '16',
         '400': '7',
         '410': '8',
         '411': '24',
         '412': '24',
         '420': '18',
         '421': '26',
         '422': '19',
         '430': '12',
         '431': '29',
         '432': '22',
         '440': '15'}
        imagen = codigo[1:]
        if imagen not in listaimagenes:
            valor = '5'
        else:
            valor = listaimagenes[imagen]
        if codigo[0] == 'n' or mirarnoche:
            valor = equivnoche(valor)
        return valor + '_int-fs8.png'

    def gesImagenLista(self, xmlstring, mirarnoche = False, temperatura = None):
        if temperatura == None:
            tempxml = devStrTm(xmlstring, '<div class="symbol_', '"')
            tempxml = devStrTm(tempxml, 'symbol_', '_')
            if mirarnoche:
                t2 = time.localtime()
                chora = int(time.strftime('%H', t2))
                if chora >= 21 or chora < 7:
                    mirarnoche = True
                else:
                    mirarnoche = False
            if len(tempxml) <= 2:
                laimagen = self.getImagen('d111', mirarnoche)
            else:
                laimagen = self.getImagen(tempxml, mirarnoche)
        else:
            laimagen = devimagentemperatura(temperatura)
        filename = laimagen
        filenamepng = filename.replace('.jpg', '-fs8.png')
        return filenamepng

    def gesImagen(self, nombre, xmlstring, mirarnoche = False, temperatura = None):
        if temperatura == None:
            tempxml = devStrTm(xmlstring, '<div class="symbol_', '</div>')
            tempxml = devStrTm(tempxml, 'symbol_', '_')
            if mirarnoche:
                t2 = time.localtime()
                chora = int(time.strftime('%H', t2))
                if chora >= 21 or chora < 7:
                    mirarnoche = True
                else:
                    mirarnoche = False
            if len(tempxml) <= 2:
                laimagen = self.getImagen('d111', mirarnoche)
            else:
                laimagen = self.getImagen(tempxml, mirarnoche)
        else:
            laimagen = devimagentemperatura(temperatura)
        filename = self.appdir + laimagen
        filenamepng = filename.replace('.jpg', '-fs8.png')
        if os.path.exists(filenamepng):
            self[nombre].instance.setPixmapFromFile(filenamepng)
            self[nombre].show()
            return
        else:
            self[nombre].hide()
            return

    def devsem(self, dia):
        ret = dia
        if self.weatherPluginEntry.language.value == 'es':
            if dia == 'lun':
                ret = 'Lunes'
            elif dia == 'mar':
                ret = 'Martes'
            elif dia == 'mi\xc3\xa9':
                ret = 'Mi\xc3\xa9rcoles'
            elif dia == 'jue':
                ret = 'Jueves'
            elif dia == 'vie':
                ret = 'Viernes'
            elif dia == 's\xc3\xa1b':
                ret = 'S\xc3\xa1bado'
            elif dia == 'dom':
                ret = 'Domingo'
            else:
                ret = upper(ret)
        else:
            ret = upper(ret)
        return ret

    def config(self):
        if self.detalle:
            self.desdet()
            return
        if self.sisat:
            self.dessat()
            return
        self.session.openWithCallback(self.setupFinished, WeatherPluginEntriesListConfigScreenfore)

    def setupFinished(self, index, entry = None):
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.foreentriescount.value
        if self.weatherPluginEntryCount >= 1:
            if entry is not None:
                self.weatherPluginEntry = entry
                self.weatherPluginEntryIndex = index + 1
            if self.weatherPluginEntry is None:
                self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.foreEntries[0]
                self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
            self.weatherPluginEntryIndex = -1
        self.clearFields()
        self.startRun()

    def error(self, error = None):
        self.descargando = False
        if error is not None:
            self.clearFields()
            self['statustext'].setText(str(error.getErrorMessage()))
            self['statustext'].show()
            self['statustext2'].hide()


class AccuWeatherPlugin(Screen):
    skin = '''<screen name="AccuWeatherPlugin" position="center,center" size="970,560" title="AccuWeather - accuwheater.com">
	      <widget name="lugar" position="36,3" zPosition="2" size="512,28" font="Regular;23" transparent="1" valign="center" backgroundColor="#000000" />
	      <widget name="info_entradas" position="753,3" zPosition="3" size="166,22" font="Regular; 16" transparent="1" halign="right" backgroundColor="#000000" />
	      <widget name="current_icon" position="32,46" zPosition="1" size="74,74" alphatest="blend" />
	      <widget name="temperatura" position="100,61" zPosition="1" size="78,30" font="Regular; 26" transparent="1" noWrap="1" halign="right" backgroundColor="#000000" />
	      <widget name="condicion" position="201,63" zPosition="1" size="360,20" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="viento" position="201,90" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="humedad" position="201,115" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="rocio" position="201,140" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="presion" position="201,165" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="tendencia" position="201,190" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="visibilidad" position="201,215" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <widget name="sol" position="201,240" zPosition="1" size="360,20" font="Regular;18" transparent="1" backgroundColor="#000000" />
	      <eLabel name="lin0" position="573,25" size="1,255" zPosition="1" backgroundColor="#10404040" />
	      <widget name="icono1" position="584,30" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="hora1" position="673,38" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="temperatura1" position="673,57" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="condicion1" position="673,76" zPosition="1" size="295,22" halign="left" valign="center" font="Regular; 16" transparent="1" noWrap="1" backgroundColor="#000000" />
	      <widget name="icono2" position="584,115" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="hora2" position="673,123" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="temperatura2" position="673,143" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="condicion2" position="673,163" zPosition="1" size="295,22" halign="left" valign="center" font="Regular; 16" transparent="1" noWrap="1" backgroundColor="#000000" />
	      <widget name="icono3" position="584,200" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="hora3" position="673,208" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="temperatura3" position="673,228" zPosition="1" size="180,22" halign="left" valign="center" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="condicion3" position="673,248" zPosition="1" size="295,22" halign="left" valign="center" font="Regular; 16" transparent="1" noWrap="1" backgroundColor="#000000" />
	      <widget name="dia1" position="24,297" zPosition="1" size="280,26" halign="center" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia1" position="124,326" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia1" position="24,409" zPosition="1" size="280,90" halign="center" valign="top" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="dia2" position="342,297" zPosition="1" size="280,26" halign="center" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia2" position="442,327" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia2" position="342,409" zPosition="1" size="280,90" halign="center" valign="bottom" font="Regular; 18" transparent="1" backgroundColor="#000000" />
	      <widget name="dia3" position="655,296" zPosition="1" size="280,26" halign="center" valign="center" font="Regular; 22" transparent="1" backgroundColor="#000000" />
	      <widget name="icono_dia3" position="755,327" zPosition="1" size="79,79" alphatest="blend" />
	      <widget name="info_dia3" position="655,409" zPosition="1" size="280,90" halign="center" valign="bottom" font="Regular; 18" transparent="1" backgroundColor="#000000" />

	      <widget name="statustext" position="0,23" zPosition="0" size="570,261" font="Regular;20" halign="center" valign="center" transparent="1" backgroundColor="#10bfbfbf" />
	      <widget name="ico_left" position="15,3" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_left-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="ico_right" position="930,3" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_right-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="ico_menu" position="775,527" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/menu.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_menu" position="811,528" size="141,25" transparent="1" font="Regular; 16" zPosition="1" />
	      <widget name="ico_l" position="8,527" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/izq-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_l" position="43,528" size="117,25" transparent="1" font="Regular; 16" zPosition="1" />
	      <widget name="ico_r" position="170,527" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/dch-fs8.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_r" position="206,528" size="141,25" transparent="1" font="Regular; 16" zPosition="1" />
	      <eLabel name="lin1" position="10,288" size="951,1" zPosition="1" backgroundColor="#10444444" />
	      <eLabel name="lin2" position="10,510" size="951,1" zPosition="1" backgroundColor="#10444444" />
	      <eLabel name="lin3" position="323,297" size="1,200" zPosition="1" backgroundColor="#10404040" />
	      <eLabel name="lin4" position="636,297" size="1,200" zPosition="1" backgroundColor="#10404040" />

	      <widget name="hora" position="100,90" zPosition="1" size="78,20" font="Regular; 18" transparent="1" halign="right" backgroundColor="#000000" />
	      <widget name="ico_blue" position="350,527" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/green.png" alphatest="blend" zPosition="1" />
	      <widget name="texto_blue" position="385,528" size="241,25" transparent="1" font="Regular; 16" zPosition="1" />

	      <widget name="satelite" position="180,20" size="640,480" alphatest="blend" zPosition="9" transparent="1" />
	      <widget name="statustext2" position="0,0" zPosition="8" size="970,560" font="Regular;20" halign="center" valign="center" transparent="0" />
	      <widget name="barra" position="301,507" zPosition="10" size="406,45" alphatest="blend" />
	      <ePixmap name="logofuente" position="10,213" size="107,63" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/icono1-fs8.png" transparent="1" alphatest="blend" />
	      </screen>'''

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['WizardActions',
         'DirectionActions',
         'ColorActions',
         'EPGSelectActions',
         'MenuActions'], {'back': self.exit,
         'input_date_time': self.config,
         'menu': self.config,
         'right': self.nextItem,
         'left': self.previousItem,
         'green': self.selimagen}, -1)
        self.sisat = False
        self['statustext'] = Label()
        self['statustext2'] = Label()
        self['infosat'] = Pixmap()
        self['barra'] = Pixmap()
        self['ico_menu'] = Pixmap()
        self['ico_left'] = Pixmap()
        self['ico_right'] = Pixmap()
        self['ico_r'] = Pixmap()
        self['ico_l'] = Pixmap()
        self['texto_menu'] = Label(_('Setup'))
        self['texto_l'] = Label(_('Previous'))
        self['texto_r'] = Label(_('Next'))
        self['current_icon'] = WeatherIcon()
        self['satelite'] = WeatherIcon()
        self['lugar'] = Label()
        self['info_entradas'] = Label()
        self['temperatura'] = Label()
        self['condicion'] = Label()
        self['viento'] = Label()
        self['humedad'] = Label()
        self['rocio'] = Label()
        self['presion'] = Label()
        self['tendencia'] = Label()
        self['visibilidad'] = Label()
        self['sol'] = Label()
        self['hora'] = Label()
        self['texto_blue'] = Label(_('Images satellite') + '...')
        self['ico_blue'] = Pixmap()
        for i in range(1, 4):
            self['dia%s' % i] = Label()
            self['icono_dia%s' % i] = WeatherIcon()
            self['info_dia%s' % i] = Label()

        for i in range(1, 4):
            self['hora%s' % i] = Label()
            self['icono%s' % i] = WeatherIcon()
            self['temperatura%s' % i] = Label()
            self['condicion%s' % i] = Label()

        self.appdir = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/'
        if not os.path.exists(self.appdir):
            os.mkdir(self.appdir)
        self.weatherPluginEntryIndex = -1
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.acuentriescount.value
        if self.weatherPluginEntryCount >= 1:
            self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.acuEntries[0]
            self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
        self.onLayoutFinish.append(self.startRun)

    def selimagen(self):
        contextFileList = [(_('Satellite'), 'sat'),
         (_('High Temperature'), 'hig'),
         (_('Low Temperature'), 'low'),
         (_('UV Index'), 'uv'),
         (_('Wind Speed'), 'win'),
         (_('Amount of Precipitacion'), 'pre')]
        dei = self.session.openWithCallback(self.SysExecution, ChoiceBox, title=_('Select satellite image') + ':', list=contextFileList)

    def SysExecution(self, answer):
        answer = answer and answer[1]
        asp = None
        if answer == 'sat':
            asp = 'satellite.aspx'
        elif answer == 'hig':
            asp = 'high-temperature.aspx'
        elif answer == 'low':
            asp = 'low-temperature.aspx'
        elif answer == 'uv':
            asp = 'uv-index.aspx'
        elif answer == 'win':
            asp = 'wind-speed.aspx'
        elif answer == 'pre':
            asp = 'precipitation-amount.aspx'
        if asp:
            self.muestrasat(asp, answer)

    def exit(self):
        if self.sisat:
            self.dessat()
            return
        self.close()

    def muestrasat(self, asp, sufijo):
        if self.sisat:
            self.dessat()
            return
        appimagedir = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/'
        self['barra'].instance.setPixmapFromFile(appimagedir + 'b' + sufijo + '-fs8.png')
        self['barra'].show()
        self['statustext2'].setText(_('Downloading') + ' ' + _('Images satellite') + '\n' + _('Wait') + '...')
        self['statustext2'].show()
        self.sisat = True
        if self.weatherPluginEntry is not None:
            ciudad = self.weatherPluginEntry.city.value
            comunidad = self.weatherPluginEntry.comunity.value
            if len(comunidad) > 0:
                comunidad = comunidad + '/'
            idioma = self.weatherPluginEntry.language.value
            pais = self.weatherPluginEntry.pais.value
            url = 'http://www.accuweather.com/%s/%s/%s%s/%s' % (idioma,
             pais,
             comunidad,
             ciudad,
             asp)
            getXML(url).addCallback(self.xmlCallbackSat).addErrback(self.error)

    def startRun(self):
        self['infosat'].hide()
        self['satelite'].hide()
        self['barra'].hide()
        if self.weatherPluginEntry is not None:
            ciudad = self.weatherPluginEntry.city.value
            comunidad = self.weatherPluginEntry.comunity.value
            idioma = self.weatherPluginEntry.language.value
            pais = self.weatherPluginEntry.pais.value
            self['ico_menu'].hide()
            self['texto_menu'].hide()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
            self['texto_blue'].hide()
            self['ico_blue'].hide()
            self['statustext2'].hide()
            self['statustext'].setText(_('Getting weather information...') + '\n[' + ciudad + ', ' + comunidad + ' - ' + pais + ']')
            if len(comunidad) > 0:
                comunidad = comunidad + '/'
            cana = ''
            if self.weatherPluginEntryIndex == 1:
                cana = '(' + _('Default') + ') '
            self['info_entradas'].setText(cana + str(self.weatherPluginEntryIndex) + ' ' + _('of') + ' ' + str(self.weatherPluginEntryCount))
            url = 'http://www.accuweather.com/%s/%s/%s%s/quick-look.aspx' % (idioma,
             pais,
             comunidad,
             ciudad)
            getXML(url).addCallback(self.xmlCallback).addErrback(self.error)
        else:
            self['statustext'].setText(_("No locations defined...\nPress 'Menu' to do that."))
            self['ico_menu'].show()
            self['texto_menu'].show()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
            self['texto_blue'].hide()
            self['ico_blue'].hide()
        self['statustext'].show()

    def dessat(self):
        os.system('rm /tmp/sp_*.gif;rm /tmp/iseur3.jpg')
        self['satelite'].hide()
        self['statustext2'].hide()
        self['infosat'].hide()
        self['barra'].hide()
        self.sisat = False

    def nextItem(self):
        if self.sisat:
            self.dessat()
            return
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex < self.weatherPluginEntryCount:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex + 1
            else:
                self.weatherPluginEntryIndex = 1
            self.setItem()

    def previousItem(self):
        if self.sisat:
            self.dessat()
            return
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex >= 2:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex - 1
            else:
                self.weatherPluginEntryIndex = self.weatherPluginEntryCount
            self.setItem()

    def setItem(self):
        self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.acuEntries[self.weatherPluginEntryIndex - 1]
        self.clearFields()
        self.startRun()

    def clearFields(self):
        self['lugar'].setText('')
        self['info_entradas'].setText('')
        self['temperatura'].setText('')
        self['condicion'].setText('')
        self['viento'].setText('')
        self['humedad'].setText('')
        self['rocio'].setText('')
        self['presion'].setText('')
        self['tendencia'].setText('')
        self['visibilidad'].setText('')
        self['sol'].setText('')
        self['hora'].setText('')
        self['texto_blue'].hide()
        self['ico_blue'].hide()
        for i in range(1, 4):
            self['dia%s' % i].setText('')
            self['icono_dia%s' % i].hide()
            self['info_dia%s' % i].setText('')

        for i in range(1, 4):
            self['hora%s' % i].setText('')
            self['icono%s' % i].hide()
            self['temperatura%s' % i].setText('')
            self['condicion%s' % i].setText('')

        self['current_icon'].hide()
        self['ico_menu'].hide()
        self['texto_menu'].hide()
        self['ico_left'].hide()
        self['ico_right'].hide()
        self['ico_l'].hide()
        self['ico_r'].hide()
        self['texto_l'].hide()
        self['texto_r'].hide()

    def errorIconDownload(self, error = None, item = None):
        item.error = True

    def finishedIconDownload(self, result, item):
        if not item.error:
            self.showIcon(item.index, item.filename)

    def showIcon(self, nombre, filename):
        self[nombre].updateIcon(filename)
        self[nombre].show()

    def xmlCallbackSat(self, xmlstring):
        self['statustext2'].show()
        laimagen = devImagen(xmlstring, 'ctl00_cphContent_imgMap')
        url = laimagen
        nombre = 'satelite'
        parts = string.split(url, '/')
        filename = '/tmp/' + parts[-1]
        IconDownloadList = []
        IconDownloadList.append(WeatherIconItem(url=url, filename=filename, index=nombre))
        if len(IconDownloadList) != 0:
            ds = defer.DeferredSemaphore(tokens=len(IconDownloadList))
            downloads = [ ds.run(download, item).addErrback(self.errorIconDownload, item).addCallback(self.finishedIconDownload, item) for item in IconDownloadList ]
            finished = defer.DeferredList(downloads).addErrback(self.error)

    def xmlCallback(self, xmlstring):
        self['statustext'].hide()
        self['ico_menu'].show()
        self['texto_menu'].show()
        self['texto_blue'].show()
        self['ico_blue'].show()
        if self.weatherPluginEntryCount > 1:
            self['ico_left'].show()
            self['ico_right'].show()
            self['ico_l'].show()
            self['ico_r'].show()
            self['texto_l'].show()
            self['texto_r'].show()
        IconDownloadList = []
        self['lugar'].show()
        self['temperatura'].show()
        self['condicion'].show()
        self['viento'].show()
        self['humedad'].show()
        self['rocio'].show()
        self['presion'].show()
        self['tendencia'].show()
        self['visibilidad'].show()
        self['sol'].show()
        for i in range(1, 4):
            self['dia%s' % i].show()
            self['info_dia%s' % i].show()

        for i in range(1, 4):
            self['hora%s' % i].show()
            self['temperatura%s' % i].show()
            self['condicion%s' % i].show()

        self['lugar'].setText(devHtml(xmlstring, 'ctl00_LocationHeader_lnkLocation'))
        self['temperatura'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblCurrentTemp'))
        self['condicion'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblCurrentText'))
        self['hora'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblCurrentTime'))
        temp = self.gesImagen('current_icon', xmlstring, 'ctl00_cphContent_imgCurConCondition')
        if temp:
            IconDownloadList.append(temp)
        self['viento'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblWindsName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblWindsValue'))
        self['humedad'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblHumidityName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblHumidityValue'))
        self['rocio'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblDewPointName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblDewPointValue'))
        self['presion'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblPressureName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblPressureValue'))
        self['tendencia'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblPressureTenName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblPressureTenValue'))
        self['visibilidad'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblVisibilityName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblVisibilityValue'))
        self['sol'].setText(devHtml(xmlstring, 'ctl00_cphContent_lblSunRiseName') + ': ' + devHtml(xmlstring, 'ctl00_cphContent_lblSunRiseValue') + ' - ' + devHtml(xmlstring, 'ctl00_cphContent_lblSunSetValue'))
        for i in range(1, 4):
            self['dia%s' % i].setText(devHtml(xmlstring, 'ctl00_cphContent_lblDayName%s' % i))
            temp = self.gesImagen('icono_dia%s' % i, xmlstring, 'ctl00_cphContent_imgDay%sIcon' % i)
            if temp:
                IconDownloadList.append(temp)
            self['info_dia%s' % i].setText(devHtml(xmlstring, 'ctl00_cphContent_lblTxtForecast%s' % i) + '\n' + devHtml(xmlstring, 'ctl00_cphContent_lblHigh%s' % i) + '\n' + devHtml(xmlstring, 'ctl00_cphContent_lblLow%s' % i))

        for i in range(1, 4):
            self['hora%s' % i].setText(devHtml(xmlstring, 'ctl00_cphContent_lblHbhHour%s' % i))
            temp = self.gesImagen('icono%s' % i, xmlstring, 'ctl00_cphContent_imgHbhCond%s' % i)
            if temp:
                IconDownloadList.append(temp)
            self['temperatura%s' % i].setText(devHtml(xmlstring, 'ctl00_cphContent_lblHbhTemp%s' % i))
            self['condicion%s' % i].setText(devHtml(xmlstring, 'ctl00_cphContent_lblHbhText%s' % i))

        if len(IconDownloadList) != 0:
            ds = defer.DeferredSemaphore(tokens=len(IconDownloadList))
            downloads = [ ds.run(download, item).addErrback(self.errorIconDownload, item).addCallback(self.finishedIconDownload, item) for item in IconDownloadList ]
            finished = defer.DeferredList(downloads).addErrback(self.error)
        if self.weatherPluginEntryIndex == 1:
            if 'ctl00_LocationHeader_debug' in xmlstring and 'ctl00_cphContent_lnkHbhDetails3' in xmlstring:
                try:
                    ertexto = devStrTm(xmlstring, 'ctl00_LocationHeader_debug', 'ctl00_cphContent_lnkHbhDetails3') + ' (from plugin)'
                    sourceEncoding = 'utf-8'
                    targetEncoding = 'iso-8859-1'
                    f = open('/tmp/wf_acuspz.xml', 'w')
                    f.write(ertexto)
                    f.close()
                except:
                    pass

    def gesImagen(self, nombre, xmlstring, etiqueta):
        laimagen = devImagen(xmlstring, etiqueta)
        url = laimagen
        parts = string.split(url, '/')
        filename = self.appdir + parts[-1]
        filenamepng = filename.replace('.jpg', '-fs8.png')
        if os.path.exists(filenamepng):
            self[nombre].instance.setPixmapFromFile(filenamepng)
            self[nombre].show()
            return None
        if not os.path.exists(filename):
            return WeatherIconItem(url=url, filename=filename, index=nombre)
        self.showIcon(nombre, filename)

    def devsem(self, dia):
        ret = dia
        if self.weatherPluginEntry.language.value == 'es':
            if dia == 'lun':
                ret = 'Lunes'
            elif dia == 'mar':
                ret = 'Martes'
            elif dia == 'mi\xc3\xa9':
                ret = 'Mi\xc3\xa9rcoles'
            elif dia == 'jue':
                ret = 'Jueves'
            elif dia == 'vie':
                ret = 'Viernes'
            elif dia == 's\xc3\xa1b':
                ret = 'S\xc3\xa1bado'
            elif dia == 'dom':
                ret = 'Domingo'
            else:
                ret = upper(ret)
        else:
            ret = upper(ret)
        return ret

    def config(self):
        if self.sisat:
            self.dessat()
            return
        self.session.openWithCallback(self.setupFinished, WeatherPluginEntriesListConfigScreenacu)

    def setupFinished(self, index, entry = None):
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.acuentriescount.value
        if self.weatherPluginEntryCount >= 1:
            if entry is not None:
                self.weatherPluginEntry = entry
                self.weatherPluginEntryIndex = index + 1
            if self.weatherPluginEntry is None:
                self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.acuEntries[0]
                self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
            self.weatherPluginEntryIndex = -1
        self.clearFields()
        self.startRun()

    def error(self, error = None):
        if error is not None:
            self.clearFields()
            self['statustext'].setText(str(error.getErrorMessage()))
            self['statustext'].show()
            self['ico_menu'].show()
            self['texto_menu'].show()


class GoogleWeatherPlugin(Screen):
    skin = '''<screen name="GoogleWeatherPlugin" position="center,center" size="770,470" title="Weather Info - google.com">
	  <ePixmap name="logofuente" position="655,94" size="107,63" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/icono0-fs8.png" transparent="1" alphatest="blend" />
	  <widget name="caption" position="36,21" zPosition="2" size="526,28" font="Regular;22" transparent="1" valign="center" />
	  <widget name="info_entradas" position="566,23" zPosition="3" size="166,28" font="Regular; 16" transparent="1" halign="right" />
	  <widget name="currentTemp" position="115,66" zPosition="3" size="78,30" font="Regular; 26" transparent="1" noWrap="1" />
	  <widget name="condition" position="201,63" zPosition="1" size="536,20" font="Regular; 18" transparent="1" />
	  <widget name="wind_condition" position="201,85" zPosition="1" size="536,20" font="Regular;18" transparent="1" />
	  <widget name="weekday1" position="9,187" zPosition="1" size="180,22" halign="center" valign="center" font="Regular; 20" transparent="1" />
	  <widget name="weekday1_icon" position="56,211" zPosition="1" size="74,74" alphatest="blend" />
	  <widget name="weekday1_temp" position="9,285" zPosition="1" size="180,130" halign="center" valign="top" font="Regular;16" transparent="1" />
	  <widget name="weekday2" position="199,187" zPosition="1" size="180,22" halign="center" valign="center" font="Regular; 20" transparent="1" />
	  <widget name="weekday2_icon" position="252,211" zPosition="1" size="74,74" alphatest="blend" />
	  <widget name="weekday2_temp" position="199,285" zPosition="1" size="180,130" halign="center" valign="bottom" font="Regular;16" transparent="1" />
	  <widget name="weekday3" position="389,187" zPosition="1" size="180,22" halign="center" valign="center" font="Regular; 20" transparent="1" />
	  <widget name="weekday3_icon" position="445,211" zPosition="1" size="74,74" alphatest="blend" />
	  <widget name="weekday3_temp" position="389,285" zPosition="1" size="180,130" halign="center" valign="bottom" font="Regular;16" transparent="1" />
	  <widget name="weekday4" position="579,187" zPosition="1" size="180,22" halign="center" valign="center" font="Regular; 20" transparent="1" />
	  <widget name="weekday4_icon" position="628,211" zPosition="1" size="74,74" alphatest="blend" />
	  <widget name="weekday4_temp" position="579,285" zPosition="1" size="180,130" halign="center" valign="bottom" font="Regular;16" transparent="1" />
	  <widget name="statustext" position="0,23" zPosition="0" size="768,140" font="Regular;20" halign="center" valign="center" transparent="1" />
	  <widget name="ico_left" position="10,21" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_left-fs8.png" alphatest="blend" zPosition="1" />
	  <widget name="ico_right" position="743,21" size="16,26" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/nm_right-fs8.png" alphatest="blend" zPosition="1" />
	  <widget name="current_icon" position="8,50" zPosition="1" size="74,74" alphatest="blend" />
	  <widget name="ico_menu" position="584,434" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/menu.png" alphatest="blend" zPosition="1" />
	  <widget name="texto_menu" position="619,438" size="141,25" transparent="1" font="Regular; 16" zPosition="1" />
	  <widget name="ico_l" position="5,434" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/izq-fs8.png" alphatest="blend" zPosition="1" />
	  <widget name="texto_l" position="40,438" size="117,25" transparent="1" font="Regular; 16" zPosition="1" />
	  <widget name="ico_r" position="160,434" size="35,25" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/image/dch-fs8.png" alphatest="blend" zPosition="1" />
	  <widget name="texto_r" position="195,438" size="141,25" transparent="1" font="Regular; 16" zPosition="1" />
	  <eLabel name="lin1" position="10,164" size="751,1" zPosition="1" backgroundColor="#10444444" />
	  <eLabel name="lin2" position="10,420" size="751,1" zPosition="1" backgroundColor="#10444444" />
	  <eLabel name="lin3" position="193,185" size="1,210" zPosition="1" backgroundColor="#10404040" />
	  <eLabel name="lin4" position="383,185" size="1,210" zPosition="1" backgroundColor="#10404040" />
	  <eLabel name="lin5" position="573,185" size="1,210" zPosition="1" backgroundColor="#10404040" />
	  <widget name="ico_temp" position="59,50" zPosition="2" size="74,74" alphatest="blend" />
	  </screen>'''

    def __init__(self, session):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['WizardActions',
         'DirectionActions',
         'ColorActions',
         'EPGSelectActions',
         'MenuActions'], {'back': self.close,
         'input_date_time': self.config,
         'menu': self.config,
         'right': self.nextItem,
         'left': self.previousItem,
         'blue': self.acuInfo}, -1)
        self['statustext'] = Label()
        self['caption'] = Label()
        self['info_entradas'] = Label()
        self['currentTemp'] = Label()
        self['condition'] = Label()
        self['wind_condition'] = Label()
        self['current_icon'] = WeatherIcon()
        self['ico_menu'] = Pixmap()
        self['ico_left'] = Pixmap()
        self['ico_temp'] = Pixmap()
        self['ico_right'] = Pixmap()
        self['ico_r'] = Pixmap()
        self['ico_l'] = Pixmap()
        self['texto_menu'] = Label(_('Setup'))
        self['texto_l'] = Label(_('Previous'))
        self['texto_r'] = Label(_('Next'))
        for i in range(1, 5):
            self['weekday%s' % i] = Label()
            self['weekday%s_icon' % i] = WeatherIcon()
            self['weekday%s_temp' % i] = Label()

        self.appdir = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/wheathericons/'
        self.rutapng = '/usr/lib/enigma2/python/Plugins/Extensions/AccuWeather/acuwheathericons/'
        if not os.path.exists(self.appdir):
            os.mkdir(self.appdir)
        self.weatherPluginEntryIndex = -1
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.entriescount.value
        if self.weatherPluginEntryCount >= 1:
            self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.Entries[0]
            self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
        self.onLayoutFinish.append(self.startRun)

    def acuInfo(self):
        self.session.open(AccuWeatherPlugin)

    def startRun(self):
        if self.weatherPluginEntry is not None:
            self['ico_menu'].hide()
            self['texto_menu'].hide()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
            self['ico_temp'].hide()
            self['statustext'].setText(_('Getting weather information...') + '\n[' + self.weatherPluginEntry.city.value + ']')
            cana = ''
            if self.weatherPluginEntryIndex == 1:
                cana = '(' + _('Default') + ') '
            self['info_entradas'].setText(cana + str(self.weatherPluginEntryIndex) + ' ' + _('of') + ' ' + str(self.weatherPluginEntryCount))
            url = 'http://www.google.com/ig/api?weather=%s&hl=%s' % (urllib.quote(self.weatherPluginEntry.city.value), self.weatherPluginEntry.language.value)
            getXML(url).addCallback(self.xmlCallback).addErrback(self.error)
        else:
            self['statustext'].setText(_("No locations defined...\nPress 'Menu' to do that."))
            self['ico_menu'].show()
            self['texto_menu'].show()
            self['ico_left'].hide()
            self['ico_right'].hide()
            self['ico_l'].hide()
            self['ico_r'].hide()
            self['texto_l'].hide()
            self['texto_r'].hide()
        self['statustext'].show()

    def nextItem(self):
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex < self.weatherPluginEntryCount:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex + 1
            else:
                self.weatherPluginEntryIndex = 1
            self.setItem()

    def previousItem(self):
        if self.weatherPluginEntryCount != 0:
            if self.weatherPluginEntryIndex >= 2:
                self.weatherPluginEntryIndex = self.weatherPluginEntryIndex - 1
            else:
                self.weatherPluginEntryIndex = self.weatherPluginEntryCount
            self.setItem()

    def setItem(self):
        self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.Entries[self.weatherPluginEntryIndex - 1]
        self.clearFields()
        self.startRun()

    def clearFields(self):
        self['caption'].setText('')
        self['currentTemp'].setText('')
        self['condition'].setText('')
        self['wind_condition'].setText('')
        self['current_icon'].hide()
        self['ico_menu'].hide()
        self['texto_menu'].hide()
        self['ico_left'].hide()
        self['ico_right'].hide()
        self['ico_l'].hide()
        self['ico_r'].hide()
        self['texto_l'].hide()
        self['texto_r'].hide()
        self['ico_temp'].hide()
        for i in range(1, 5):
            self['weekday%s' % i].setText('')
            self['weekday%s_icon' % i].hide()
            self['weekday%s_temp' % i].setText('')

    def errorIconDownload(self, error = None, item = None):
        item.error = True

    def finishedIconDownload(self, result, item):
        if not item.error:
            self.showIcon(item.index, item.filename)

    def showIcon(self, index, filename):
        if index == None:
            self['current_icon'].updateIcon(filename)
            self['current_icon'].show()
        else:
            self['weekday%s_icon' % index].updateIcon(filename)
            self['weekday%s_icon' % index].show()

    def xmlCallback(self, xmlstring):
        self['statustext'].hide()
        self['ico_menu'].show()
        self['texto_menu'].show()
        if self.weatherPluginEntryCount > 1:
            self['ico_left'].show()
            self['ico_right'].show()
            self['ico_l'].show()
            self['ico_r'].show()
            self['texto_l'].show()
            self['texto_r'].show()
        metric = 0
        index = 0
        UnitSystemText = 'F'
        IconDownloadList = []
        root = xml.etree.cElementTree.fromstring(xmlstring)
        for childs in root.findall('weather'):
            for items in childs:
                if items.tag == 'problem_cause':
                    self['statustext'].setText(items.attrib.get('data').encode('utf-8', 'ignore'))
                    self['statustext'].show()
                if items.tag == 'forecast_information':
                    for items2 in items:
                        if items2.tag == 'city':
                            self['caption'].setText(items2.attrib.get('data').encode('utf-8', 'ignore'))
                        elif items2.tag == 'unit_system':
                            if items2.attrib.get('data').encode('utf-8', 'ignore') == 'SI':
                                metric = 1
                                UnitSystemText = 'C'

                elif items.tag == 'current_conditions':
                    erhum = ''
                    for items2 in items:
                        if items2.tag == 'condition':
                            self['condition'].setText(items2.attrib.get('data').encode('utf-8', 'ignore'))
                        elif items2.tag == 'temp_f' and metric == 0:
                            self['currentTemp'].setText('%s \xc2\xb0F' % items2.attrib.get('data').encode('utf-8', 'ignore'))
                        elif items2.tag == 'temp_c' and metric == 1:
                            itemp = None
                            try:
                                itemp = int(items2.attrib.get('data').encode('utf-8', 'ignore').strip())
                            except:
                                pass

                            if not itemp == None:
                                self['ico_temp'].show()
                                filenamepng = self.rutapng + devimagentemperatura(itemp)
                                self['ico_temp'].instance.setPixmapFromFile(filenamepng)
                            self['currentTemp'].setText('%s \xc2\xb0C' % items2.attrib.get('data').encode('utf-8', 'ignore'))
                        elif items2.tag == 'humidity':
                            erhum = items2.attrib.get('data').encode('utf-8', 'ignore')
                        elif items2.tag == 'wind_condition':
                            self['wind_condition'].setText(erhum + ', ' + items2.attrib.get('data').encode('utf-8', 'ignore'))
                        elif items2.tag == 'icon':
                            url = 'http://www.google.com%s' % items2.attrib.get('data').encode('utf-8', 'ignore')
                            parts = string.split(url, '/')
                            filename = self.appdir + parts[-1]
                            pngname = self.rutapng + devgificono(parts[-1], actual=True)
                            if os.path.exists(pngname):
                                self['current_icon'].instance.setPixmapFromFile(pngname)
                                self['current_icon'].show()
                            elif not os.path.exists(filename):
                                IconDownloadList.append(WeatherIconItem(url=url, filename=filename, index=index))
                            else:
                                self.showIcon(None, filename)

                elif items.tag == 'forecast_conditions':
                    index = index + 1
                    lowTemp = ''
                    highTemp = ''
                    icon = ''
                    textowek = ''
                    for items2 in items:
                        if items2.tag == 'day_of_week':
                            self['weekday%s' % index].setText(self.devsem(items2.attrib.get('data').encode('utf-8', 'ignore')))
                        if items2.tag == 'low':
                            lowTemp = items2.attrib.get('data').encode('utf-8', 'ignore')
                        if items2.tag == 'high':
                            highTemp = items2.attrib.get('data').encode('utf-8', 'ignore')
                        if items2.tag == 'condition':
                            lacond = items2.attrib.get('data').encode('utf-8', 'ignore')
                            self['weekday%s_temp' % index].setText((_('Max') + ':%s\xc2\xb0%s \n' + _('Min') + ':%s\xc2\xb0%s\n%s') % (highTemp,
                             UnitSystemText,
                             lowTemp,
                             UnitSystemText,
                             lacond))
                        if items2.tag == 'icon':
                            url = 'http://www.google.com%s' % items2.attrib.get('data').encode('utf-8', 'ignore')
                            parts = string.split(url, '/')
                            filename = self.appdir + parts[-1]
                            pngname = self.rutapng + devgificono(parts[-1])
                            if os.path.exists(pngname):
                                self['weekday%s_icon' % index].instance.setPixmapFromFile(pngname)
                                self['weekday%s_icon' % index].show()
                            elif not os.path.exists(filename):
                                IconDownloadList.append(WeatherIconItem(url=url, filename=filename, index=index))
                            else:
                                self.showIcon(index, filename)

        if len(IconDownloadList) != 0:
            ds = defer.DeferredSemaphore(tokens=len(IconDownloadList))
            downloads = [ ds.run(download, item).addErrback(self.errorIconDownload, item).addCallback(self.finishedIconDownload, item) for item in IconDownloadList ]
            finished = defer.DeferredList(downloads).addErrback(self.error)
        if self.weatherPluginEntryIndex == 1:
            if '</weather>' in xmlstring and '<forecast_information>' in xmlstring:
                try:
                    sourceEncoding = 'utf-8'
                    targetEncoding = 'iso-8859-1'
                    ret = unicode(xmlstring, sourceEncoding).encode(targetEncoding)
                    f = open('/tmp/wf_spz.xml', 'w')
                    f.write(ret)
                    f.close()
                except:
                    pass

    def devsem(self, dia):
        ret = dia
        if self.weatherPluginEntry.language.value == 'es':
            if dia == 'lun':
                ret = 'Lunes'
            elif dia == 'mar':
                ret = 'Martes'
            elif dia == 'mi\xc3\xa9':
                ret = 'Mi\xc3\xa9rcoles'
            elif dia == 'jue':
                ret = 'Jueves'
            elif dia == 'vie':
                ret = 'Viernes'
            elif dia == 's\xc3\xa1b':
                ret = 'S\xc3\xa1bado'
            elif dia == 'dom':
                ret = 'Domingo'
            else:
                ret = upper(ret)
        else:
            ret = upper(ret)
        return ret

    def config(self):
        self.session.openWithCallback(self.setupFinished, WeatherPluginEntriesListConfigScreen)

    def setupFinished(self, index, entry = None):
        self.weatherPluginEntryCount = config.plugins.AccuWeatherPlugin.entriescount.value
        if self.weatherPluginEntryCount >= 1:
            if entry is not None:
                self.weatherPluginEntry = entry
                self.weatherPluginEntryIndex = index + 1
            if self.weatherPluginEntry is None:
                self.weatherPluginEntry = config.plugins.AccuWeatherPlugin.Entries[0]
                self.weatherPluginEntryIndex = 1
        else:
            self.weatherPluginEntry = None
            self.weatherPluginEntryIndex = -1
        self.clearFields()
        self.startRun()

    def error(self, error = None):
        if error is not None:
            self.clearFields()
            self['statustext'].setText(str(error.getErrorMessage()))
            self['statustext'].show()
            self['ico_menu'].show()
            self['texto_menu'].show()


class WeatherIcon(Pixmap):

    def __init__(self):
        Pixmap.__init__(self)
        self.IconFileName = ''
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintIconPixmapCB)

    def reinicia(self):
        self.picload = None
        self.IconFileName = ''
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.paintIconPixmapCB)

    def onShow(self):
        Pixmap.onShow(self)
        try:
            sc = AVSwitch().getFramebufferScale()
            self.picload.setPara((self.instance.size().width(),self.instance.size().height(),sc[0],sc[0],0,0,'#00000000'))
        except:
            pass

    def paintIconPixmapCB(self, picInfo = None):
        ptr = self.picload.getData()
        if ptr != None:
            self.instance.setPixmap(ptr.__deref__())

    def updateIcon(self, filename):
        new_IconFileName = filename
        if self.IconFileName != new_IconFileName:
            self.IconFileName = new_IconFileName
            self.picload.startDecode(self.IconFileName)
