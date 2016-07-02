from Components.config import config
from Renderer import Renderer
from enigma import eLabel, eTimer
from Components.VariableText import VariableText

class RollerCharLCDLong(VariableText, Renderer):

    def __init__(self):
        Renderer.__init__(self)
        VariableText.__init__(self)
        self.stringlength = 36
        self.moveTimerText = None
        self.delayTimer = None

    def applySkin(self, desktop, parent):
        attribs = []
        width = None
        fontsize = None
        for attrib, value in self.skinAttributes:
            if attrib == 'size':
                width = float(value.split(',')[0])
            elif attrib == 'font':
                fontsize = float(value.split(';')[1])
            attribs.append((attrib, value))

        self.skinAttributes = attribs
        if width and fontsize:
            self.stringlength = int(width / fontsize * 1.9)
        return Renderer.applySkin(self, desktop, parent)

    GUI_WIDGET = eLabel

    def connect(self, source):
        Renderer.connect(self, source)
        self.changed((self.CHANGED_DEFAULT,))

    def changed(self, what):
        if what[0] == self.CHANGED_CLEAR:
            if self.moveTimerText:
                self.moveTimerText.stop()
            if self.delayTimer:
                self.delayTimer.stop()
            self.text = ''
        else:
            self.text = self.source.text
        if len(self.text) > self.stringlength:
            end_text = self.source.text[:self.stringlength + 1]
            self.text = self.source.text + ' ' * (self.stringlength + 5) + end_text
            self.x = len(self.text) - self.stringlength
            self.idx = 0
            self.backtext = self.text
            self.status = 'start'
            self.moveTimerText = eTimer()
            self.moveTimerText.timeout.get().append(self.moveTimerTextRun)
            self.moveTimerText.start(2000)
        else:
            self.text = self.source.text
            self.x = len(self.text)
            self.idx = 0
            self.backtext = self.text

    def moveTimerTextRun(self):
        self.moveTimerText.stop()
        if self.x > 0:
            txttmp = self.backtext[self.idx:]
            self.text = txttmp
            str_length = 1
            accents = self.text[:2]
            if accents in ('\xc3\xbc', '\xc3\xa4', '\xc3\xb6', '\xc3\x84', '\xc3\x9c', '\xc3\x96', '\xc3\x9f'):
                str_length = 2
            self.idx = self.idx + str_length
            self.x = self.x - str_length
        if self.x == 0:
            self.status = 'end'
            self.text = self.backtext
        if self.status != 'end':
            self.scrollspeed = int(config.lcd.scroll_speed.value)
            self.moveTimerText.start(self.scrollspeed)
        if config.lcd.scroll_delay.value != 'noscrolling':
            self.scrolldelay = int(config.lcd.scroll_delay.value)
            self.delayTimer = eTimer()
            self.delayTimer.timeout.get().append(self.delayTimergo)
            self.delayTimer.start(self.scrolldelay)

    def delayTimergo(self):
        self.delayTimer.stop()
        self.changed((self.CHANGED_DEFAULT,))