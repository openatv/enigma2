# 2014.10.12 15:53:07 CEST
from Imports import *
import Imports

def PeerEntryComponent(text, dyndns, type):
    res = [type]
    res.append((eListboxPythonMultiContent.TYPE_TEXT,
     35,
     Imports.RT_VALIGN_CENTER,
     400,
     20,
     0,
     Imports.RT_HALIGN_LEFT,
     text))
    if type == 0:
        png = loadPNG('/usr/lib/enigma2/python/Plugins/Extensions/GboxSuite/green.png')
    elif type == 1:
        png = loadPNG('/usr/lib/enigma2/python/Plugins/Extensions/GboxSuite/red.png')
    elif type == 2:
        png = loadPNG('/usr/lib/enigma2/python/Plugins/Extensions/GboxSuite/yellow.png')
    if png is not None:
        res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST,
         10,
         Imports.RT_VALIGN_CENTER,
         30,
         30,
         png))
    res.append(dyndns)
    return res



class PeerList(GUIComponent):

    def __init__(self, list):
        GUIComponent.__init__(self)
        self.l = eListboxPythonMultiContent()
        self.l.setList(list)
        self.l.setFont(0, gFont('Regular', 18))



    def getSelection(self):
        return self.l.getCurrentSelection()



    def GUIdelete(self):
        self.instance.setContent(None)
        self.instance = None



    def GUIcreate(self, parent):
        self.instance = eListbox(parent)
        self.instance.setContent(self.l)
        self.instance.setItemHeight(30)

