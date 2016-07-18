from Components.VariableText import VariableText
from Renderer import Renderer
from enigma import eLabel
from boxbranding import getImageVersion

class VtiImageVersion(VariableText, Renderer):

    def __init__(self):
        Renderer.__init__(self)
        VariableText.__init__(self)

    GUI_WIDGET = eLabel

    def connect(self, source):
        Renderer.connect(self, source)
        self.changed((self.CHANGED_DEFAULT,))

    def changed(self, what):
        if what[0] != self.CHANGED_CLEAR:
            self.text = self.ATVImageVersion()

    def ATVImageVersion(self):
        atvversion = getImageVersion()
        return 'openATV Image Release v. %s' % atvversion