from Renderer import Renderer
from enigma import ePixmap
from Tools.Directories import fileExists, SCOPE_CURRENT_SKIN, resolveFilename

class Micon(Renderer):

    def __init__(self):
        Renderer.__init__(self)
        self.path = ''
        self.nameCache = {}
        self.noCoverFile = ''
        self.pngname = ''

    def applySkin(self, desktop, parent):
        attribs = []
        for attrib, value in self.skinAttributes:
            if attrib == 'path':
                self.path = value
            elif attrib == 'pixmap':
                self.noCoverFile = value
            else:
                attribs.append((attrib, value))

        self.skinAttributes = attribs
        ret = Renderer.applySkin(self, desktop, parent)
        return ret

    GUI_WIDGET = ePixmap

    def changed(self, what):
        if self.instance:
            pngname = ''
            if what[0] != self.CHANGED_CLEAR:
                mname = self.source.text
                if mname is None:
                    self.hide()
                    return
                pngname = self.nameCache.get(mname, '')
                if pngname == '':
                    pngname = self.findMicon(mname)
                    if pngname != '':
                        self.nameCache[mname] = pngname
                if pngname == '':
                    self.hide()
                else:
                    self.show()
                    if self.pngname != pngname:
                        self.instance.setPixmapFromFile(pngname)
                        self.pngname = pngname

    def findMicon(self, menuID):
        if menuID.lower().endswith('.png'):
            if menuID.startswith('file://'):
                menuID = menuID[7:]
            if fileExists(menuID):
                return menuID
        elif self.path == '':
            pngname = resolveFilename(SCOPE_CURRENT_SKIN, 'easy-skin-hd/menu/' + menuID + '.png')
            if fileExists(pngname):
                return pngname
        else:
            pngname = resolveFilename(SCOPE_CURRENT_SKIN, self.path + menuID + '.png')
            if fileExists(pngname):
                return pngname
        return self.noCoverFile
