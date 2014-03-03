from Components.ActionMap import ActionMap
from Components.config import config, ConfigInteger, ConfigSubsection, getConfigListEntry, ConfigYesNo
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import ChannelSelection
from Screens.Screen import Screen
from Tools.Directories import resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor
from enigma import eListboxPythonMultiContent, eServiceCenter, gFont, fontRenderClass, RT_HALIGN_LEFT, RT_VALIGN_CENTER
from os import environ
config.plugins.ZapHistoryConfigurator = ConfigSubsection()
config.plugins.ZapHistoryConfigurator.enable_zap_history = ConfigYesNo(default=True)
config.plugins.ZapHistoryConfigurator.maxEntries_zap_history = ConfigInteger(default=20, limits=(1, 60))

def addToHistory(instance, ref):
    if not config.plugins.ZapHistoryConfigurator.enable_zap_history.value:
        return
    if instance.servicePath is not None:
        if instance.history_pos < len(instance.history):
            path = instance.history[instance.history_pos][:]
            historyref = path.pop()
            if historyref == ref:
                return
        if instance.servicePath is not None:
            tmp = instance.servicePath[:]
            tmp.append(ref)
            try:
                del instance.history[instance.history_pos + 1:]
            except:
                pass

            instance.history.append(tmp)
            hlen = len(instance.history)
            if hlen > config.plugins.ZapHistoryConfigurator.maxEntries_zap_history.value:
                del instance.history[0]
                hlen -= 1
            instance.history_pos = hlen - 1


ChannelSelection.addToHistory = addToHistory

class ZapHistoryConfigurator(ConfigListScreen, Screen):
    skin = '''
	    <screen name="ZapHistoryConfigurator" position="90,90" size="1100,576" title="Zap-History Browser">
	      <eLabel position="800, 25" size="300, 22" text="ZapHistory Browser" halign="right" font="Regular; 20" transparent="1" zPosition="2"/>
	      <widget name="config" position="335, 95" size="540, 410" scrollbarMode="showOnDemand" transparent="1"/>
	    </screen>'''
	    
    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self['title'] = Label(_('Zap history'))
        self['key_red'] = Label(_('Cancel'))
        self['key_green'] = Label(_('Save'))        
        self.onShown.append(boundFunction(self.setTitle, _('Zap history')))
        ConfigListScreen.__init__(self, [getConfigListEntry(_('Enable zap history:'), config.plugins.ZapHistoryConfigurator.enable_zap_history), getConfigListEntry(_('Maximum zap history entries:'), config.plugins.ZapHistoryConfigurator.maxEntries_zap_history)])
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], 
        {
	 'ok': self.save,
         'cancel': self.exit, 
         'green': self.save,
         'red': self.exit,
        }, -2)

    def save(self):
        for x in self['config'].list:
            x[1].save()

        self.close()

    def exit(self):
        for x in self['config'].list:
            x[1].cancel()

        self.close()


class ZapHistoryBrowserList(MenuList):

    def __init__(self, list, enableWrapAround = False):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setItemHeight(50)
        self.l.setFont(0, gFont('Regular', 22))
        self.l.setFont(1, gFont('Regular', 18))


def ZapHistoryBrowserListEntry(index, ref, serviceName, eventName):
    res = [(index, ref)]
    if len(eventName.strip()) != 0:
        eventName = '(' + eventName + ')'
    width = 170
    serviceNameWidth = len(serviceName)
    res.append(MultiContentEntryText(pos=(10, 0), size=(465, 50), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=serviceName))
    res.append(MultiContentEntryText(pos=(width + 20, 0), size=(435 - width, 50), font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=10066329, color_sel=11184810, text=eventName))
    return res


class ZapHistoryBrowser(Screen):
    skin = '''
	    <screen name="ZapHistoryBrowser" position="90,90" size="1100,576" title="Zap-History Browser">
	      <eLabel position="800, 25" size="300, 22" text="ZapHistory Browser" halign="right" font="Regular; 20" transparent="1" zPosition="2"/>
	      <widget name="list" position="335, 95" size="540, 410" scrollbarMode="showOnDemand" transparent="1"/>
	      <widget position="240, 535" size="200,36" name="key_red" font="Regular;20" foregroundColor="red" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3"/>
	      <widget position="520, 535" size="200,36" name="key_green" font="Regular;20" foregroundColor="green" halign="center" valign="center" backgroundColor="black" transparent="1" zPosition="3"/>
	    </screen>'''
 
    def __init__(self, session, servicelist):
        Screen.__init__(self, session)
        self.session = session
        self.servicelist = servicelist
        self.serviceHandler = eServiceCenter.getInstance()
        self.allowChanges = True
        self['title'] = Label(_('Zap history'))
        self.onShown.append(boundFunction(self.setTitle, _('Zap history')))
        self['picon'] = StaticText('')
        self['list'] = ZapHistoryBrowserList([])
        self['list'].onSelectionChanged.append(self.selectionChanged)
        self['key_red'] = Label(_('Zap'))
        self['key_green'] = Label(_('Clear'))
        self['key_yellow'] = Label(_('Delete'))
        self['key_blue'] = Label('')
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'ok': self.zapAndClose,
         'cancel': self.close,
         'red': self.zap,
         'green': self.clear,
         'yellow': self.delete}, prio=-1)
        self.onLayoutFinish.append(self.buildList)

    def selectionChanged(self):
        if self['list'].l.getCurrentSelection() is None:
            return
        ref = self['list'].l.getCurrentSelection()[0][1]
        self['picon'].setText(ref.toString())

    def buildList(self):
        from Components.ParentalControl import parentalControl
        list = []
        index = len(self.servicelist.history) - 1
        for x in self.servicelist.history:
            ref = x[len(x) - 1]
            info = self.serviceHandler.info(ref)
            if info:
                name = info.getName(ref).replace('\xc2\x86', '').replace('\xc2\x87', '')
                event = info.getEvent(ref)
                if event is not None:
                    eventName = event.getEventName()
                    if eventName is None:
                        eventName = ''
                else:
                    eventName = ''
            else:
                name = 'N/A'
                eventName = ''
            if ref is not None:
                if not parentalControl.getProtectionLevel(ref.toCompareString()) == -1:
                    pass
                else:
                    list.append(ZapHistoryBrowserListEntry(index, ref, name, eventName))
            index -= 1

        list.reverse()
        self['list'].setList(list)

    def zap(self):
        length = len(self.servicelist.history)
        if length > 0:
            index = self['list'].getCurrent()[0][0]
            self.servicelist.history_pos = length - index - 1
            self.servicelist.setHistoryPath()

    def clear(self):
        if self.allowChanges:
            for i in range(0, len(self.servicelist.history)):
                del self.servicelist.history[0]

            self.buildList()
            self.servicelist.history_pos = 0

    def delete(self):
        if self.allowChanges:
            length = len(self.servicelist.history)
            if length > 0:
                idx = length - self['list'].getSelectionIndex() - 1
                del self.servicelist.history[idx]
                self.buildList()
                currRef = self.session.nav.getCurrentlyPlayingServiceReference()
                idx = 0
                for x in self.servicelist.history:
                    ref = x[len(x) - 1]
                    if currRef is not None and currRef == ref:
                        self.servicelist.history_pos = idx
                        break
                    else:
                        idx += 1

    def zapAndClose(self):
        self.zap()
        self.close(True)


def main(session, callback, **kwargs):
    from Screens.InfoBar import InfoBar
    from Screens.ChannelSelection import ChannelSelection
    if InfoBar.instance.servicelist is None:
        InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
    session.openWithCallback(callback, ZapHistoryBrowser, InfoBar.instance.servicelist)


def menu(menuid, **kwargs):
    if menuid == 'id_mainmenu_tv':
        return [(_('History'), main, 'mainmenu_tv_zaphistory', 50)]
    return []


def setup(session, **kwargs):
    session.open(ZapHistoryConfigurator)


def mainSetup(menuid, **kwargs):
    if menuid == 'id_mainmenu_tasks_setup_tv':
        return [(_('History'), setup, 'mainmenu_tasks_setup_tv_zaphistory', 70)]
    return []


def Plugins(**kwargs):
    list = [PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=menu), PluginDescriptor(where=PluginDescriptor.WHERE_MENU, fnc=mainSetup)]
    return list
