# 2014.10.12 15:51:05 CEST
from Imports import *
import Imports
from ShowFile import *
from PeerStatus import *
from Screens.Console import *
from OnlineCardInfo import *
from Filecheck import *
from GboxTrace import *
from GboxSuiteSettings import *

class GboxSuiteMainMenu(Screen):
    skin = '\n\t\t<screen position="center,center" size="580,420"  title="Gbox Suite - 0 Cards" >\n\t\t\t<widget name="menu" position="10,10" size="180,400" scrollbarMode="showOnDemand" />\n\t\t\t<widget name="text" position="200,10" size="370,400" font="Regular;16" />\n\t\t</screen>'

    def __init__(self, session, args = 0):
        Screen.__init__(self, session)
        self.menu = args
        fillProviderTable()
        list = []
        self.count = 0
        self.newtitle = 'Gbox Suite\xb2'
        if self.menu == 0:
            list.append((_('Share Info Menu'), ('shareInfoMenu', _('Press OK to enter the Share Info Menu, where you will be able to see further information about the sharing functionality of gbox, such as:\n\n- Online Cards\n\n- Peer Status etc.'))))
            list.append((_('Emu Info Menu'), ('emuInfoMenu', _('Press OK to enter the Emu Info Menu, where you will be able to see further information about the emulation functionality of gbox\n\nTo scroll the output of the info file, use the left, right key on your remote'))))
            list.append((_('Card Info Menu'), ('cardInfoMenu', _('Press OK to enter the Card Info Menu, where you will be able to see further information about the cards, inserted into the slots of your dreambox\n\nTo scroll the output of the info file, use the left, right key on your remote'))))
            list.append((_('Gbox Tools'), ('toolMenu', _('Press OK to enter the Gbox Tool Menu, where you will be able to access\n\n- Gbox Filecheck and\n\n- Gbox Trace'))))
            list.append((_('Settings'), ('settings', _('Press OK to enter the Gbox Suite\xb2 Settings'))))
            gboxVersion = readTextFile([config.plugins.gs.infoDir.value + '/gbox.ver', _('Gbox is not running')])
            gboxSuiteVersion = '1.6.2 (OE2.0)'
            gboxSuiteDate = 'Date: 2012/05/06 17:04:00 '
            list.append((_('About'), ('about', _('Gbox Suite\xb2 Version ' + gboxSuiteVersion + '\n\n(c) by zg0re/nightmann,\n ' + gboxSuiteDate + '\n\nYou are running Gbox version: ') + gboxVersion)))
        if self.menu == 1:
            self.newtitle = _('Share Info Menu')
            list.append((_('Online Cards'), ('onlineCards', _('Press OK to enter the Online Card Info, where you will be able to see detailed information about all the cards you are accessing by share'))))
            list.append((_('Peer Status'), ('peerStatus', _('Press OK to enter Peer Status, where you will be able to see information about peers connected to you.\n\n- A yellow icon means that the peer is online, but does not share any cards\n\n- A red icon means that the peer is offline\n\n- A Green icon means that a peer is online and does share cards'))))
        if self.menu == 2:
            self.newtitle = _('Emu Info Menu')
            list.append((_('ECM-Info'), ('ecmInfo', readTextFile([config.plugins.gs.infoDir.value + '/ecm.info', _("ECM-Information file is not available.\n\nThis means that either gbox can't decode, or the current channel is FTA.")]))))
            list.append((_('PID-Info'), ('pidInfo', readTextFile([config.plugins.gs.infoDir.value + '/pid.info', _('PID Information is not available. Usually this means that the channel is FTA.')]))))
            list.append((_('EMM-Info'), ('emmInfo', readTextFile([config.plugins.gs.infoDir.value + '/emm.info', _('No new keys have been found by gbox.')]))))
        if self.menu == 3:
            self.newtitle = _('Card Info Menu')
            list.append((_('Upper Slot Info'), ('upperSlot', readTextFile([config.plugins.gs.infoDir.value + '/sc02.info', _('No Card found in the upper Slot')]))))
            list.append((_('Lower Slot Info'), ('lowerSlot', readTextFile([config.plugins.gs.infoDir.value + '/sc01.info', _('No Card found in the lower Slot')]))))
            list.append((_('General Card Info'), ('generalCardInfo', readTextFile([config.plugins.gs.infoDir.value + '/sc.info', _('No Cards found')]))))
        if self.menu == 4:
            self.newtitle = _('Gbox Tools')
            list.append((_('Filecheck'), ('filecheck', _('Press OK to enter the Gbox Filecheck, where you will be able to see whether all the files needed by gbox ar properly installed'))))
            list.append((_('Trace'), ('trace', _('Press OK to enter & start Gbox Trace.\n\nYou have to change your gbox_cfg to make this work. Change Option Z, to look like this: Z: { 00 12 } 192.168.0.11 8024\n\nYou need to replace 192.168.0.11 with the IP of your dreambox'))))
        self.onShown.append(self.updateTitle)
        self['menu'] = MenuList(list)
        self['text'] = ScrollLabel(list[0][1][1])
        self['actions'] = ActionMap(['DirectionActions', 'WizardActions'], {'ok': self.go,
         'back': self.close,
         'right': self['text'].pageDown,
         'left': self['text'].pageUp,
         'up': self.myUp,
         'down': self.myDown}, -1)



    def updateTitle(self):
        try:
            fp = open(config.plugins.gs.infoDir.value + '/share.info', 'r')
            self.newtitle = 'Gbox Suite\xb2 - ' + str(len(fp.readlines())) + ' Cards'
            fp.close()
        except IOError:
            self.newtitle = 'Gbox Suite\xb2 - 0 Cards'
        self.setTitle(self.newtitle)



    def myUp(self):
        self['menu'].up()
        self['text'].setText(self['menu'].l.getCurrentSelection()[1][1])



    def myDown(self):
        self['menu'].down()
        self['text'].setText(self['menu'].l.getCurrentSelection()[1][1])



    def go(self):
        if self.menu == 0:
            if self['menu'].l.getCurrentSelection()[1][0] == 'shareInfoMenu':
                self.session.open(GboxSuiteMainMenu, 1)
            if self['menu'].l.getCurrentSelection()[1][0] == 'emuInfoMenu':
                self.session.open(GboxSuiteMainMenu, 2)
            if self['menu'].l.getCurrentSelection()[1][0] == 'cardInfoMenu':
                self.session.open(GboxSuiteMainMenu, 3)
            if self['menu'].l.getCurrentSelection()[1][0] == 'toolMenu':
                self.session.open(GboxSuiteMainMenu, 4)
            if self['menu'].l.getCurrentSelection()[1][0] == 'settings':
                self.session.open(Settings)
        if self.menu == 1:
            if self['menu'].l.getCurrentSelection()[1][0] == 'onlineCards':
                self.session.open(OnlineCardInfo)
            if self['menu'].l.getCurrentSelection()[1][0] == 'peerStatus':
                self.session.open(PeerStatus)
        if self.menu == 4:
            if self['menu'].l.getCurrentSelection()[1][0] == 'trace':
                self.session.open(GboxTrace)
            if self['menu'].l.getCurrentSelection()[1][0] == 'filecheck':
                self.session.open(Filecheck)

