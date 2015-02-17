# 2014.10.12 15:50:30 CEST
from Imports import *
import Imports
from PeerList import *
from GboxSuiteUtils import *
from OnlineCardInfo import *
from Imports import *
import os

class Filecheck(Screen):
    skin = '\n\t\t<screen position="center,center" size="580,420" title="Filecheck" >\n\t\t\t<widget name="list" position="10,10" size="560,400" scrollbarMode="showOnDemand" />\n\t\t</screen>'

    def __init__(self, session, args = None):
        self.skin = Filecheck.skin
        Screen.__init__(self, session)
        self.list = []
        self.filelist = [config.plugins.gs.configDir.value + '/gbox_cfg',
         config.plugins.gs.configDir.value + '/cwshare.cfg',
         config.plugins.gs.configDir.value + '/softcam.cfg',
         config.plugins.gs.configDir.value + '/conax',
         config.plugins.gs.configDir.value + '/irdeto',
         config.plugins.gs.configDir.value + '/nagra',
         config.plugins.gs.configDir.value + '/seca',
         config.plugins.gs.configDir.value + '/via',
         config.plugins.gs.configDir.value + '/nagra.txt',
         config.plugins.gs.configDir.value + '/ignore.list',
         config.plugins.gs.configDir.value + '/knowns.ini',
         config.plugins.gs.configDir.value + '/rom02.b',
         config.plugins.gs.configDir.value + '/rom02eep.b',
         config.plugins.gs.configDir.value + '/rom02ram.b',
         config.plugins.gs.configDir.value + '/rom03.b',
         config.plugins.gs.configDir.value + '/rom03eep.b',
         config.plugins.gs.configDir.value + '/rom03ram.b',
         config.plugins.gs.configDir.value + '/rom07.b',
         config.plugins.gs.configDir.value + '/rom07eep.b',
         config.plugins.gs.configDir.value + '/rom07ram.b',
         config.plugins.gs.configDir.value + '/rom10.b',
         config.plugins.gs.configDir.value + '/rom10eep.b',
         config.plugins.gs.configDir.value + '/rom10ram.b',
         config.plugins.gs.configDir.value + '/rom11.b',
         config.plugins.gs.configDir.value + '/rom11eep.b',
         config.plugins.gs.configDir.value + '/rom11ram.b',
         config.plugins.gs.configDir.value + '/s2issuer.b',
         config.plugins.gs.configDir.value + '/s2provid.b']
        for element in self.filelist:
            if os.path.isfile(element) == True:
                self.list.append(PeerEntryComponent(element, '', 0))
            else:
                self.list.append(PeerEntryComponent(element, '', 1))

        self['list'] = PeerList(self.list)
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.close,
         'back': self.close}, -1)


