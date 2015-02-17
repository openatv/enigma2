# 2014.10.12 15:53:35 CEST
from Imports import *
from GboxSuiteUtils import *

class ShowFile(Screen):
    skin = '\n\t\t<screen position="center, center" size="520,420" title="Showing File" >\n\t\t\t<widget name="text" position="10,10" size="500,400" font="Regular;17" />\n\t\t</screen>'

    def __init__(self, session, args):
        self.skin = ShowFile.skin
        Screen.__init__(self, session)
        self.newtitle = _('Showing ') + args[0]
        self.onShown.append(self.updateTitle)
        output = readTextFile([args[0], args[1]])
        self['text'] = ScrollLabel(output)
        self['actions'] = NumberActionMap(['WizardActions', 'DirectionActions'], {'ok': self.close,
         'back': self.close,
         'up': self['text'].pageUp,
         'left': self['text'].pageUp,
         'down': self['text'].pageDown,
         'right': self['text'].pageDown}, -1)



    def updateTitle(self):
        self.setTitle(self.newtitle)



