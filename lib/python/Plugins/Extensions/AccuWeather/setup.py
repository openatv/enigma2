from enigma import eListboxPythonMultiContent, eListbox, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.MenuList import MenuList
from Components.Button import Button
from Components.config import config
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import ConfigSubsection, ConfigSubList, ConfigIP, ConfigInteger, ConfigSelection, ConfigText, ConfigYesNo, getConfigListEntry, configfile
from os import environ
import gettext
from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE

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


def initWeatherPluginEntryConfig():
    config.plugins.AccuWeatherPlugin.Entries.append(ConfigSubsection())
    i = len(config.plugins.AccuWeatherPlugin.Entries) - 1
    config.plugins.AccuWeatherPlugin.Entries[i].city = ConfigText(default='Berlin', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.Entries[i].language = ConfigText(default='de', visible_width=50, fixed_size=False)
    return config.plugins.AccuWeatherPlugin.Entries[i]


def initWeatherPluginEntryConfigacu():
    config.plugins.AccuWeatherPlugin.acuEntries.append(ConfigSubsection())
    i = len(config.plugins.AccuWeatherPlugin.acuEntries) - 1
    config.plugins.AccuWeatherPlugin.acuEntries[i].city = ConfigText(default='Berlin', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.acuEntries[i].comunity = ConfigText(default='Germany', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.acuEntries[i].pais = ConfigText(default='de', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.acuEntries[i].language = ConfigText(default='de', visible_width=50, fixed_size=False)
    return config.plugins.AccuWeatherPlugin.acuEntries[i]


def initWeatherPluginEntryConfigfore():
    config.plugins.AccuWeatherPlugin.foreEntries.append(ConfigSubsection())
    i = len(config.plugins.AccuWeatherPlugin.foreEntries) - 1
    config.plugins.AccuWeatherPlugin.foreEntries[i].city = ConfigText(default='Berlin', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.foreEntries[i].pais = ConfigText(default='Germany', visible_width=50, fixed_size=False)
    config.plugins.AccuWeatherPlugin.foreEntries[i].dominio = ConfigText(default='de', visible_width=50, fixed_size=False)
    return config.plugins.AccuWeatherPlugin.foreEntries[i]


def initConfig():
    count = config.plugins.AccuWeatherPlugin.entriescount.value
    if count != 0:
        i = 0
        while i < count:
            initWeatherPluginEntryConfig()
            i += 1


def initConfigacu():
    count = config.plugins.AccuWeatherPlugin.acuentriescount.value
    if count != 0:
        i = 0
        while i < count:
            initWeatherPluginEntryConfigacu()
            i += 1


def initConfigfore():
    count = config.plugins.AccuWeatherPlugin.foreentriescount.value
    if count != 0:
        i = 0
        while i < count:
            initWeatherPluginEntryConfigfore()
            i += 1


class WeatherPluginEntriesListConfigScreenfore(Screen):
    skin = '''<screen position="center,center" size="750,400" title="WeatherPlugin: List of Entries (foreca.com)" >
	      <widget name="city" position="5,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="language" position="155,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="entrylist" position="0,50" size="750,300" scrollbarMode="showOnDemand"/>
	      <widget name="key_red" position="0,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_green" position="140,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_yellow" position="280,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_blue" position="420,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <ePixmap name="red" position="0,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	      <ePixmap name="green" position="140,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	      <ePixmap name="yellow" position="280,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	      <ePixmap name="blue" position="420,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	      </screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['city'] = Button(_('City'))
        self['language'] = Button(_('Country'))
        self['key_red'] = Button(_('Add'))
        self['key_green'] = Button(_('Default'))
        self['key_yellow'] = Button(_('Edit'))
        self['key_blue'] = Button(_('Delete'))
        self['entrylist'] = WeatherPluginEntryListfore([])
        self['actions'] = ActionMap(['WizardActions', 'MenuActions', 'ShortcutActions'], {'ok': self.keyOK,
         'back': self.keyClose,
         'green': self.keyGreen,
         'red': self.keyRed,
         'yellow': self.keyYellow,
         'blue': self.keyDelete}, -1)
        self.updateList()

    def updateList(self):
        self['entrylist'].buildList()

    def keyClose(self):
        self.close(-1, None)

    def keyRed(self):
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreenfore, None)

    def keyGreen(self):
        if len(self['entrylist'].list) <= 0:
            return
        sel = self['entrylist'].getCurrentIndex()
        defacity = config.plugins.AccuWeatherPlugin.foreEntries[sel].city.value
        defapais = config.plugins.AccuWeatherPlugin.foreEntries[sel].pais.value
        defacom = config.plugins.AccuWeatherPlugin.foreEntries[sel].dominio.value
        config.plugins.AccuWeatherPlugin.foreEntries[sel].city.value = config.plugins.AccuWeatherPlugin.foreEntries[0].city.value
        config.plugins.AccuWeatherPlugin.foreEntries[sel].pais.value = config.plugins.AccuWeatherPlugin.foreEntries[0].pais.value
        config.plugins.AccuWeatherPlugin.foreEntries[sel].dominio.value = config.plugins.AccuWeatherPlugin.foreEntries[0].dominio.value
        config.plugins.AccuWeatherPlugin.foreEntries[0].city.value = defacity
        config.plugins.AccuWeatherPlugin.foreEntries[0].pais.value = defapais
        config.plugins.AccuWeatherPlugin.foreEntries[0].dominio.value = defacom
        config.plugins.AccuWeatherPlugin.foreentriescount.save()
        config.plugins.AccuWeatherPlugin.foreEntries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()

    def keyOK(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        self.close(self['entrylist'].getCurrentIndex(), sel)

    def keyYellow(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreenfore, sel)

    def keyDelete(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        sel = self['entrylist'].l.getCurrentSelection()[0]
        config.plugins.AccuWeatherPlugin.foreentriescount.value = config.plugins.AccuWeatherPlugin.foreentriescount.value - 1
        config.plugins.AccuWeatherPlugin.foreentriescount.save()
        config.plugins.AccuWeatherPlugin.foreEntries.remove(sel)
        config.plugins.AccuWeatherPlugin.foreEntries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()


class WeatherPluginEntryListfore(MenuList):

    def __init__(self, list, enableWrapAround = True):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', 20))
        self.l.setFont(1, gFont('Regular', 18))

    def postWidgetCreate(self, instance):
        MenuList.postWidgetCreate(self, instance)
        instance.setItemHeight(50)

    def getCurrentIndex(self):
        return self.instance.getCurrentIndex()

    def buildList(self):
        self.list = []
        for c in config.plugins.AccuWeatherPlugin.foreEntries:
            res = [c]
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             15,
             0,
             150,
             50,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             str(c.city.value)))
            tvalor = str(c.pais.value) + ' (.' + str(c.dominio.value) + ')'
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             165,
             0,
             150,
             50,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             tvalor))
            self.list.append(res)

        self.l.setList(self.list)
        self.moveToIndex(0)


class WeatherPluginEntryConfigScreenfore(ConfigListScreen, Screen):
    skin = '''<screen name="WeatherPluginEntryConfigScreen" position="center,center" size="750,276" title="WeatherPlugin: Edit Entry (foreca.com)">
	      <widget name="config" position="20,10" size="720,200" scrollbarMode="showOnDemand" />
	      <ePixmap name="red" position="10,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	      <ePixmap name="green" position="167,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	      <ePixmap name="blue" position="319,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	      <widget name="key_red" position="10,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_green" position="166,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_blue" position="319,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      </screen>'''

    def __init__(self, session, entry):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'green': self.keySave,
         'red': self.keyCancel,
         'blue': self.keyDelete,
         'cancel': self.keyCancel}, -2)
        self['key_red'] = Button(_('Cancel'))
        self['key_green'] = Button(_('Save'))
        self['key_blue'] = Button(_('Delete'))
        if entry is None:
            self.newmode = 1
            self.current = initWeatherPluginEntryConfigfore()
        else:
            self.newmode = 0
            self.current = entry
        cfglist = [getConfigListEntry(_('City'), self.current.city), getConfigListEntry(_('Country'), self.current.pais), getConfigListEntry(_('Domain') + ' (' + _('Language') + ')', self.current.dominio)]
        ConfigListScreen.__init__(self, cfglist, session)

    def keySave(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.foreentriescount.value = config.plugins.AccuWeatherPlugin.foreentriescount.value + 1
            config.plugins.AccuWeatherPlugin.foreentriescount.save()
        ConfigListScreen.keySave(self)
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.close()

    def keyCancel(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.foreEntries.remove(self.current)
        ConfigListScreen.cancelConfirm(self, True)

    def keyDelete(self):
        if self.newmode == 1:
            self.keyCancel()
        else:
            self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        config.plugins.AccuWeatherPlugin.foreentriescount.value = config.plugins.AccuWeatherPlugin.foreentriescount.value - 1
        config.plugins.AccuWeatherPlugin.foreentriescount.save()
        config.plugins.AccuWeatherPlugin.foreEntries.remove(self.current)
        config.plugins.AccuWeatherPlugin.foreEntries.save()
        config.plugins.AccuWeatherPlugin.foresave()
        configfile.save()
        self.close()


class WeatherPluginEntriesListConfigScreenacu(Screen):
    skin = '''<screen position="center,center" size="750,400" title="%s %s" >
	      <widget name="city" position="5,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="language" position="155,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="entrylist" position="0,50" size="750,300" scrollbarMode="showOnDemand"/>
	      <widget name="key_red" position="0,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_green" position="140,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_yellow" position="280,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_blue" position="420,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <ePixmap name="red" position="0,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	      <ePixmap name="green" position="140,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	      <ePixmap name="yellow" position="280,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	      <ePixmap name="blue" position="420,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	      </screen>''' % (_('WeatherPlugin: List of Entries'), '(accuwheater.com)')

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['city'] = Button(_('City'))
        self['language'] = Button(_('Language'))
        self['key_red'] = Button(_('Add'))
        self['key_green'] = Button(_('Default'))
        self['key_yellow'] = Button(_('Edit'))
        self['key_blue'] = Button(_('Delete'))
        self['entrylist'] = WeatherPluginEntryListacu([])
        self['actions'] = ActionMap(['WizardActions', 'MenuActions', 'ShortcutActions'], {'ok': self.keyOK,
         'back': self.keyClose,
         'green': self.keyGreen,
         'red': self.keyRed,
         'yellow': self.keyYellow,
         'blue': self.keyDelete}, -1)
        self.updateList()

    def updateList(self):
        self['entrylist'].buildList()

    def keyClose(self):
        self.close(-1, None)

    def keyRed(self):
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreenacu, None)

    def keyGreen(self):
        if len(self['entrylist'].list) <= 0:
            return
        sel = self['entrylist'].getCurrentIndex()
        defacity = config.plugins.AccuWeatherPlugin.acuEntries[sel].city.value
        defacomu = config.plugins.AccuWeatherPlugin.acuEntries[sel].comunity.value
        defapais = config.plugins.AccuWeatherPlugin.acuEntries[sel].pais.value
        defalan = config.plugins.AccuWeatherPlugin.acuEntries[sel].language.value
        config.plugins.AccuWeatherPlugin.acuEntries[sel].city.value = config.plugins.AccuWeatherPlugin.acuEntries[0].city.value
        config.plugins.AccuWeatherPlugin.acuEntries[sel].pais.value = config.plugins.AccuWeatherPlugin.acuEntries[0].pais.value
        config.plugins.AccuWeatherPlugin.acuEntries[sel].comunity.value = config.plugins.AccuWeatherPlugin.acuEntries[0].comunity.value
        config.plugins.AccuWeatherPlugin.acuEntries[sel].language.value = config.plugins.AccuWeatherPlugin.acuEntries[0].language.value
        config.plugins.AccuWeatherPlugin.acuEntries[0].city.value = defacity
        config.plugins.AccuWeatherPlugin.acuEntries[0].pais.value = defapais
        config.plugins.AccuWeatherPlugin.acuEntries[0].comunity.value = defacomu
        config.plugins.AccuWeatherPlugin.acuEntries[0].language.value = defalan
        config.plugins.AccuWeatherPlugin.acuentriescount.save()
        config.plugins.AccuWeatherPlugin.acuEntries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()

    def keyOK(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        self.close(self['entrylist'].getCurrentIndex(), sel)

    def keyYellow(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreenacu, sel)

    def keyDelete(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        sel = self['entrylist'].l.getCurrentSelection()[0]
        config.plugins.AccuWeatherPlugin.acuentriescount.value = config.plugins.AccuWeatherPlugin.acuentriescount.value - 1
        config.plugins.AccuWeatherPlugin.acuentriescount.save()
        config.plugins.AccuWeatherPlugin.acuEntries.remove(sel)
        config.plugins.AccuWeatherPlugin.acuEntries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()


class WeatherPluginEntriesListConfigScreen(Screen):
    skin = '''<screen position="center,center" size="750,400" title="%s %s" >
	      <widget name="city" position="5,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="language" position="155,0" size="150,50" font="Regular;20" halign="left"/>
	      <widget name="entrylist" position="0,50" size="750,300" scrollbarMode="showOnDemand"/>
	      <widget name="key_red" position="0,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_green" position="140,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="red" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_yellow" position="280,350" size="140,40" zPosition="5" valign="center" halign="center" backgroundColor="yellow" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <widget name="key_blue" position="420,350" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	      <ePixmap name="red" position="0,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	      <ePixmap name="green" position="140,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	      <ePixmap name="yellow" position="280,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
	      <ePixmap name="blue" position="420,350" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	      </screen>''' % (_('WeatherPlugin: List of Entries'), '(google.com)')

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['city'] = Button(_('City'))
        self['language'] = Button(_('Language'))
        self['key_red'] = Button(_('Add'))
        self['key_green'] = Button(_('Default'))
        self['key_yellow'] = Button(_('Edit'))
        self['key_blue'] = Button(_('Delete'))
        self['entrylist'] = WeatherPluginEntryList([])
        self['actions'] = ActionMap(['WizardActions', 'MenuActions', 'ShortcutActions'], {'ok': self.keyOK,
         'back': self.keyClose,
         'green': self.keyGreen,
         'red': self.keyRed,
         'yellow': self.keyYellow,
         'blue': self.keyDelete}, -1)
        self.updateList()

    def updateList(self):
        self['entrylist'].buildList()

    def keyClose(self):
        self.close(-1, None)

    def keyRed(self):
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreen, None)

    def keyGreen(self):
        if len(self['entrylist'].list) <= 0:
            return
        sel = self['entrylist'].getCurrentIndex()
        defacity = config.plugins.AccuWeatherPlugin.Entries[sel].city.value
        defalan = config.plugins.AccuWeatherPlugin.Entries[sel].language.value
        config.plugins.AccuWeatherPlugin.Entries[sel].city.value = config.plugins.AccuWeatherPlugin.Entries[0].city.value
        config.plugins.AccuWeatherPlugin.Entries[sel].language.value = config.plugins.AccuWeatherPlugin.Entries[0].language.value
        config.plugins.AccuWeatherPlugin.Entries[0].city.value = defacity
        config.plugins.AccuWeatherPlugin.Entries[0].language.value = defalan
        config.plugins.AccuWeatherPlugin.entriescount.save()
        config.plugins.AccuWeatherPlugin.Entries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()

    def keyOK(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        self.close(self['entrylist'].getCurrentIndex(), sel)

    def keyYellow(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.updateList, WeatherPluginEntryConfigScreen, sel)

    def keyDelete(self):
        try:
            sel = self['entrylist'].l.getCurrentSelection()[0]
        except:
            sel = None

        if sel is None:
            return
        self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        sel = self['entrylist'].l.getCurrentSelection()[0]
        config.plugins.AccuWeatherPlugin.entriescount.value = config.plugins.AccuWeatherPlugin.entriescount.value - 1
        config.plugins.AccuWeatherPlugin.entriescount.save()
        config.plugins.AccuWeatherPlugin.Entries.remove(sel)
        config.plugins.AccuWeatherPlugin.Entries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.updateList()


class WeatherPluginEntryList(MenuList):

    def __init__(self, list, enableWrapAround = True):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', 20))
        self.l.setFont(1, gFont('Regular', 18))

    def postWidgetCreate(self, instance):
        MenuList.postWidgetCreate(self, instance)
        instance.setItemHeight(20)

    def getCurrentIndex(self):
        return self.instance.getCurrentIndex()

    def buildList(self):
        self.list = []
        for c in config.plugins.AccuWeatherPlugin.Entries:
            res = [c]
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             5,
             0,
             150,
             20,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             str(c.city.value)))
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             155,
             0,
             150,
             20,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             str(c.language.value)))
            self.list.append(res)

        self.l.setList(self.list)
        self.moveToIndex(0)


class WeatherPluginEntryListacu(MenuList):

    def __init__(self, list, enableWrapAround = True):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', 20))
        self.l.setFont(1, gFont('Regular', 18))

    def postWidgetCreate(self, instance):
        MenuList.postWidgetCreate(self, instance)
        instance.setItemHeight(20)

    def getCurrentIndex(self):
        return self.instance.getCurrentIndex()

    def buildList(self):
        self.list = []
        for c in config.plugins.AccuWeatherPlugin.acuEntries:
            res = [c]
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             5,
             0,
             150,
             20,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             str(c.city.value)))
            res.append((eListboxPythonMultiContent.TYPE_TEXT,
             155,
             0,
             150,
             20,
             1,
             RT_HALIGN_LEFT | RT_VALIGN_CENTER,
             str(c.language.value)))
            self.list.append(res)

        self.l.setList(self.list)
        self.moveToIndex(0)


class WeatherPluginEntryConfigScreenacu(ConfigListScreen, Screen):
    skin = '''<screen name="WeatherPluginEntryConfigScreenacu" position="center,center" size="750,276" title="%s %s">
	    <widget name="config" position="20,10" size="720,200" scrollbarMode="showOnDemand" />
	    <ePixmap name="red" position="10,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	    <ePixmap name="green" position="167,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	    <ePixmap name="blue" position="319,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	    <widget name="key_red" position="10,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    <widget name="key_green" position="166,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    <widget name="key_blue" position="319,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    </screen>''' % (_('WeatherPlugin: Edit Entry'), '(accuwheater.com)')

    def __init__(self, session, entry):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'green': self.keySave,
         'red': self.keyCancel,
         'blue': self.keyDelete,
         'cancel': self.keyCancel}, -2)
        self['key_red'] = Button(_('Cancel'))
        self['key_green'] = Button(_('Save'))
        self['key_blue'] = Button(_('Delete'))
        if entry is None:
            self.newmode = 1
            self.current = initWeatherPluginEntryConfigacu()
        else:
            self.newmode = 0
            self.current = entry
        cfglist = [getConfigListEntry(_('City'), self.current.city),
         getConfigListEntry(_('Comunity'), self.current.comunity),
         getConfigListEntry(_('Country'), self.current.pais),
         getConfigListEntry(_('Language'), self.current.language)]
        ConfigListScreen.__init__(self, cfglist, session)

    def keySave(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.acuentriescount.value = config.plugins.AccuWeatherPlugin.acuentriescount.value + 1
            config.plugins.AccuWeatherPlugin.acuentriescount.save()
        ConfigListScreen.keySave(self)
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.close()

    def keyCancel(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.acuEntries.remove(self.current)
        ConfigListScreen.cancelConfirm(self, True)

    def keyDelete(self):
        if self.newmode == 1:
            self.keyCancel()
        else:
            self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        config.plugins.AccuWeatherPlugin.acuentriescount.value = config.plugins.AccuWeatherPlugin.acuentriescount.value - 1
        config.plugins.AccuWeatherPlugin.acuentriescount.save()
        config.plugins.AccuWeatherPlugin.acuEntries.remove(self.current)
        config.plugins.AccuWeatherPlugin.acuEntries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.close()


class WeatherPluginEntryConfigScreen(ConfigListScreen, Screen):
    skin = '''<screen name="WeatherPluginEntryConfigScreen" position="center,center" size="750,276" title="%s%s">
	    <widget name="config" position="20,10" size="720,200" scrollbarMode="showOnDemand" />
	    <ePixmap name="red" position="10,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
	    <ePixmap name="green" position="167,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
	    <ePixmap name="blue" position="319,225" zPosition="4" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
	    <widget name="key_red" position="10,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    <widget name="key_green" position="166,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    <widget name="key_blue" position="319,225" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
	    </screen>''' % (_('WeatherPlugin: Edit Entry'), '(google.com)')

    def __init__(self, session, entry):
        self.session = session
        Screen.__init__(self, session)
        self['actions'] = ActionMap(['SetupActions', 'ColorActions'], {'green': self.keySave,
         'red': self.keyCancel,
         'blue': self.keyDelete,
         'cancel': self.keyCancel}, -2)
        self['key_red'] = Button(_('Cancel'))
        self['key_green'] = Button(_('Save'))
        self['key_blue'] = Button(_('Delete'))
        if entry is None:
            self.newmode = 1
            self.current = initWeatherPluginEntryConfig()
        else:
            self.newmode = 0
            self.current = entry
        cfglist = [getConfigListEntry(_('City or Postal Code'), self.current.city), getConfigListEntry(_('Language'), self.current.language)]
        ConfigListScreen.__init__(self, cfglist, session)

    def keySave(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.entriescount.value = config.plugins.AccuWeatherPlugin.entriescount.value + 1
            config.plugins.AccuWeatherPlugin.entriescount.save()
        ConfigListScreen.keySave(self)
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.close()

    def keyCancel(self):
        if self.newmode == 1:
            config.plugins.AccuWeatherPlugin.Entries.remove(self.current)
        ConfigListScreen.cancelConfirm(self, True)

    def keyDelete(self):
        if self.newmode == 1:
            self.keyCancel()
        else:
            self.session.openWithCallback(self.deleteConfirm, MessageBox, _('Really delete this WeatherPlugin Entry?'))

    def deleteConfirm(self, result):
        if not result:
            return
        config.plugins.AccuWeatherPlugin.entriescount.value = config.plugins.AccuWeatherPlugin.entriescount.value - 1
        config.plugins.AccuWeatherPlugin.entriescount.save()
        config.plugins.AccuWeatherPlugin.Entries.remove(self.current)
        config.plugins.AccuWeatherPlugin.Entries.save()
        config.plugins.AccuWeatherPlugin.save()
        configfile.save()
        self.close()
