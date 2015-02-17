# 2014.10.12 15:51:48 CEST
from Screens.Screen import Screen
from Imports import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.Label import Label

class Settings(ConfigListScreen, Screen):
    skin = '\n        <screen position="center,center" size="500,280" title="Gbox Suite2 Settings">\n            <widget name="config" position="10,50" size="480,175" scrollbarMode="showOnDemand" />\n            <widget name="introduction" position="10,230" size="400,30" font="Regular;23" />\n        </screen>'

    def __init__(self, session):
        Screen.__init__(self, session)
        self.newtitle = 'Gbox Suite\xb2 Settings'
        self['setupActions'] = ActionMap(['SetupActions'], {'ok': self.keySave,
         'cancel': self.keyCancel}, -1)
        self.list = []
        ConfigListScreen.__init__(self, self.list)
        self['config'] = ConfigList(self.list)
        self.loadSettings()
        self.onShown.append(self.updateTitle)
        self['introduction'] = Label(_('Press OK to activate the settings.'))



    def updateTitle(self):
        self.setTitle(self.newtitle)



    def loadSettings(self):
        self.list = []
        self.list.append(getConfigListEntry(_('Infofile directory'), config.plugins.gs.infoDir))
        self.list.append(getConfigListEntry(_('Configfile directory'), config.plugins.gs.configDir))
        self['config'] = ConfigList(self.list)



    def keySave(self):
        for x in self['config'].list:
            print '[GboxSuite]saving/keySave x:',
            print str(x[1].value)
            x[1].save()

        self.close()



    def keyCancel(self):
        self.close()

