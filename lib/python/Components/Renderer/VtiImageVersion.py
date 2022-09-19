from Components.VariableText import VariableText
from Components.Renderer.Renderer import Renderer
from Components.SystemInfo import BoxInfo
from enigma import eLabel


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
        atvversion = BoxInfo.getItem("imageversion")
        return 'openATV Image Release v. %s' % atvversion
