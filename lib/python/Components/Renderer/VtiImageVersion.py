from enigma import eLabel
from Components.Renderer.Renderer import Renderer
from Components.SystemInfo import BoxInfo
from Components.VariableText import VariableText


class VtiImageVersion(VariableText, Renderer):

    GUI_WIDGET = eLabel

    def __init__(self):
        Renderer.__init__(self)
        VariableText.__init__(self)

    def connect(self, source):
        Renderer.connect(self, source)
        self.changed((self.CHANGED_DEFAULT,))

    def changed(self, what):
        if what[0] != self.CHANGED_CLEAR:
            self.text = self.ATVImageVersion()

    def ATVImageVersion(self):
        atvversion = BoxInfo.getItem("imageversion")
        return f"OpenATV Image Release v. {atvversion}"
