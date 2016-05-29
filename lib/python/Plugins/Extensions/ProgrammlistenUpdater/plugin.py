from Components.ConfigList import ConfigListScreen, ConfigList
from Components.config import ConfigSubsection, ConfigYesNo, ConfigText, config, configfile
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from enigma import *
from downloader import DownloadSetting, ConverDate
from settinglist import *
from restore import *
from history import *
import os


config.pud = ConfigSubsection()
config.pud.autocheck = ConfigYesNo(default=False)
config.pud.showmessage = ConfigYesNo(default=True)
config.pud.lastdate = ConfigText(visible_width = 200)
config.pud.satname = ConfigText(visible_width = 200, default='Enigma2 D 19E FTA')
config.pud.update_question = ConfigYesNo(default=False)
config.pud.just_update = ConfigYesNo(default=False)

URL = 'http://www.sattechnik.de/programmlisten-update/asd.php'
Version = '1.2'

class MenuListSetting(MenuList):

    def __init__(self, list):
        MenuList.__init__(self, list, True, eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', 25))
        self.l.setItemHeight(45)

class Programmlisten_Updater(Screen,ConfigListScreen):

    skin =  """
        <screen name="Programmlisten_Updater" position="center,center" size="600,470">
            <ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
            <widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
            <widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
            <widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
            <widget name="MenuListSetting" position="25,70" size="560,350" scrollbarMode="showOnDemand" />
            <widget name="description" position="20,430" size="540,25" font="Regular;22" halign="center" valign="center" />
            <widget name="update" position="380,5" size="200,25" font="Regular;22" halign="center" valign="center" />
        </screen>
        """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["description"] = Label("description")
        self['MenuListSetting'] = MenuListSetting([])
        self.skinName = "Programmlisten_Updater"
        self.setup_title = _("Programmlisten-Updater from DXAndy")
        self.setTitle(self.setup_title)
        self["description"] = Label(_("Current installed") + ":\n" + "n/a")
        self["update"] = Label(_("disabled"))

        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText(_("Install"))
        self["key_yellow"] = StaticText(_("AutoUpdate"))


        self["ColorActions"] = ActionMap(['OkCancelActions', 'MenuActions', 'ShortcutActions',"ColorActions","InfobarEPGActions"],
            {
            "red": self.keyCancel,
            "green": self.keyOk,
            "yellow" : self.keyAutoUpdate,
            "cancel" : self.keyCancel,
            "ok" : self.keyOk,
            "menu" : self.keyMenu,
            "InfoPressed" : self.keyHistory,
            })

        self.List = DownloadSetting(URL)
        self.SettingsMenu()
        self.onShown.append(self.Info)
        config.pud.showmessage.value = True

    def keyMenu(self):
        if os.path.exists(Directory + '/Settings/enigma2'):
            self.session.open(PU_Restore)

    def keyHistory(self):
        self.session.open(PU_History)

    def keyCancel(self):
        configfile.save()
        self.close()

    def keyAutoUpdate(self):
        iTimerClass.StopTimer()
        if config.pud.autocheck.value and config.pud.just_update.value:
            self['update'].setText(_("disabled"))
            config.pud.autocheck.value = False
        else:
            if config.pud.just_update.value:
                self['update'].setText(_("enabled"))
                config.pud.just_update.value = False               
            else:
                self['update'].setText(_("update"))
                config.pud.just_update.value = True 
            if config.pud.lastdate.value == '':
                self.session.open(MessageBox, _('No Settings loaded !!\n\nPlease install first a settinglist'), MessageBox.TYPE_INFO, timeout=15)
            config.pud.autocheck.value = True
            iTimerClass.TimerSetting()
        
        config.pud.save()

    def keyOk(self):
        self.name = self['MenuListSetting'].getCurrent()[0][3]
        self.date = self['MenuListSetting'].getCurrent()[0][4]
        self.link = self['MenuListSetting'].getCurrent()[0][2]
        self.session.openWithCallback(self.CBselect, MessageBox, _('Selected settingslist:\n\nSetting: %s\nDate: %s\n\nDo you want to install this settinglist?') % (self.name, self.date), MessageBox.TYPE_YESNO)

    def CBselect(self, req):
        if req:
            iTimerClass.startDownload(self.name, self.link, self.date)
        

    def Info(self):
        if not os.path.exists(Directory + '/Settings/enigma2'):
            os.system('mkdir -p ' + Directory + '/Settings/enigma2')

        if config.pud.autocheck.value:
            if config.pud.just_update.value:
                self['update'].setText(_("update"))
            else:
                self['update'].setText(_("enabled"))
        else:
            self['update'].setText(_("disabled"))
        if config.pud.lastdate.value == '':
            self["description"].setText(_("Current installed") + ":\n" + "n/a")
        else:
            self["description"].setText(_("Current installed") + ":\n" + config.pud.satname.value + " " + config.pud.lastdate.value)

    def ListEntryMenuSettings(self, name, date, link, name1, date1):
        res = [(name, date, link, name1, date1)]
        res.append(MultiContentEntryText(pos=(15, 7), size=(435, 40), font=0, text=name, flags=RT_HALIGN_LEFT))
        res.append(MultiContentEntryText(pos=(420, 7), size=(210, 40), font=0, text=date1, color=16777215, flags=RT_HALIGN_LEFT))
        res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=link, flags=RT_HALIGN_LEFT))
        res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=name1, flags=RT_HALIGN_LEFT))
        res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=date, flags=RT_HALIGN_LEFT))
        return res

    def SettingsMenu(self):
        self.listB = []        
        for date, name, link in self.List:
            self.listB.append(self.ListEntryMenuSettings(str(name.title()), str(date), str(link), str(name), ConverDate(str(date))))
        if not self.listB:
            self.listB.append(self.ListEntryMenuSettings(_('Server down'), '', '', '', ''))
        self['MenuListSetting'].setList(self.listB)

jsession = None

def SessionStart(reason, **kwargs):
    if reason == 0:
        iTimerClass.gotSession(kwargs['session'], URL)
    jsession = kwargs['session']

iTimerClass = CheckTimer(jsession)

def AutoStart(reason, **kwargs):
    if reason == 1:
        iTimerClass.StopTimer()

def Main(session, **kwargs):
    session.open(Programmlisten_Updater)

def Plugins(**kwargs):
    return [
    PluginDescriptor(name="Programmlisten-Updater V" + Version, description=_("Programmlisten-Updater from DXAndy"), icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=Main),
    PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=SessionStart),
    PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=AutoStart)]