# 2014.10.12 15:53:57 CEST
import skin
from Components.HTMLComponent import HTMLComponent
from Components.GUIComponent import GUIComponent
from Components.ScrollLabel import ScrollLabel
from enigma import eLabel, eWidget, eSlider, fontRenderClass, ePoint, eSize

class TraceLabel(ScrollLabel):

    def __init__(self, text = ''):
        ScrollLabel.__init__(self)




class TraceLabel_old(HTMLComponent, GUIComponent):

    def __init__(self, text = ''):
        self.message = text
        self.instance = None
        self.long_text = None
        self.scrollbar = None
        self.pages = None
        self.total = None



    def applySkin(self, desktop):
        skin.applyAllAttributes(self.long_text, desktop, self.skinAttributes)
        s = self.long_text.size()
        self.instance.move(self.long_text.position())
        lineheight = fontRenderClass.getInstance().getLineHeight(self.long_text.getFont())
        lines = int(s.height() / lineheight)
        self.pageHeight = int(lines * lineheight)
        self.instance.resize(eSize(s.width(), self.pageHeight + int(lineheight / 6)))
        self.scrollbar.move(ePoint(s.width() - 20, 0))
        self.scrollbar.resize(eSize(20, self.pageHeight + int(lineheight / 6)))
        self.scrollbar.setOrientation(eSlider.orVertical)
        self.scrollbar.setRange(0, 100)
        self.scrollbar.setBorderWidth(1)
        self.long_text.move(ePoint(0, 0))
        self.long_text.resize(eSize(s.width() - 30, self.pageHeight * 16))
        self.setText(self.message)



    def setText(self, text):
        self.message = text
        if self.long_text is not None:
            self.long_text.setText(self.message)
            text_height = self.long_text.calculateSize().height()
            total = self.pageHeight
            pages = 1
            while total < text_height:
                total = total + self.pageHeight
                pages = pages + 1

            if pages > 1:
                self.scrollbar.show()
                self.total = total
                self.pages = pages
                self.updateScrollbar()
            else:
                self.scrollbar.hide()
            self.total = None
            self.pages = None



    def updateScrollbar(self):
        start = -self.long_text.position().y() * 100 / self.total
        vis = self.pageHeight * 100 / self.total
        self.scrollbar.setStartEnd(start, start + vis)



    def getText(self):
        return self.message



    def GUIcreate(self, parent):
        self.instance = eWidget(parent)
        self.scrollbar = eSlider(self.instance)
        self.long_text = eLabel(self.instance)



    def GUIdelete(self):
        self.long_text = None
        self.scrollbar = None
        self.instance = None



    def pageUp(self):
        if self.total is not None:
            curPos = self.long_text.position()
            if curPos.y() < 0:
                self.long_text.move(ePoint(curPos.x(), curPos.y() + self.pageHeight))
                self.updateScrollbar()



    def pageDown(self):
        if self.total is not None:
            curPos = self.long_text.position()
            if self.total - self.pageHeight >= abs(curPos.y() - self.pageHeight):
                self.long_text.move(ePoint(curPos.x(), curPos.y() - self.pageHeight))
                self.updateScrollbar()



    def produceHTML(self):
        return self.getText()


