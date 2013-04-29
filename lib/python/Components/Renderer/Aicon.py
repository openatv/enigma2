from Renderer import Renderer
from enigma import ePixmap, ePicLoad, eTimer
from Tools.Directories import fileExists, SCOPE_CURRENT_SKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.Downloader import downloadWithProgress
from Components.AVSwitch import AVSwitch

class Aicon(Renderer):

    def __init__(self):
        Renderer.__init__(self)
        self.noCoverPixmap = None
        self.countTumbLoad = 0
        self.nameCache = {}
        self.setpara = False
        self.picon = False
        self.picartname = ''
        self.picload = ePicLoad()
        self.picload.PictureData.get().append(self.showPic)
        self.ThumbTimer = eTimer()
        self.ThumbTimer.callback.append(self.showThumb)
        self.use_cache = '1'
        self.filename = None

    def applySkin(self, desktop, parent):
        attribs = []
        for attrib, value in self.skinAttributes:
            if attrib == 'pixmap':
                self.noCoverPixmap = LoadPixmap(value)
            elif attrib == 'useCache':
                self.use_cache = value
            else:
                attribs.append((attrib, value))

        self.skinAttributes = attribs
        ret = Renderer.applySkin(self, desktop, parent)
        return ret

    def showPic(self, picInfo = None):
        ptr = self.picload.getData()
        if ptr != None:
            self.instance.setPixmap(ptr.__deref__())
            if self.picon:
                self.show()

    def showThumb(self):
        if self.filename is None:
            return
        if self.picload.getThumbnail(self.picartname) == 1:
            if self.countTumbLoad < 50:
                self.ThumbTimer.start(1000, True)
                self.countTumbLoad += 1
            elif self.noCoverPixmap is not None:
                self.picartname = ''
                self.instance.setPixmap(self.noCoverPixmap)
                self.show()

    GUI_WIDGET = ePixmap

    def changed(self, what):
        if self.instance:
            if not self.setpara:
                self.setpara = True
                sc = AVSwitch().getFramebufferScale()
                self.picload.setPara((self.instance.size().width(),
                 self.instance.size().height(),
                 sc[0],
                 sc[1],
                 self.use_cache == '1',
                 1,
                 '#00000000'))
            if what[0] != self.CHANGED_CLEAR:
                pathdir = ''
                picartname = ''
                filename = self.source.text
                if filename is None:
                    self.picon = False
                    self.hide()
                    return
                if self.filename == filename:
                    self.picon = True
                    self.show()
                    return
                self.filename = filename
                if self.filename[:7] == 'path://':
                    pos = self.filename.rfind('/')
                    if pos != -1:
                        path = self.filename[7:pos]
                        name = self.filename[pos + 1:]
                        if path.lower().endswith('video_ts'):
                            path = path[:-8]
                        picartname = self.findAicon(path, name)
                elif self.filename[:7] == 'file://':
                    picartname = self.filename[7:]
                elif self.filename[:7] == 'http://':
                    pos = self.filename.rfind('/')
                    if pos != -1:
                        self.picartname = '/tmp/.' + self.filename[pos + 1:]
                    else:
                        self.picartname = '/tmp/.httpcoverart'
                    self.download = downloadWithProgress(self.filename, self.picartname)
                    if self.filename.find('tvChannel.') != -1 and self.filename.endswith('.png'):
                        self.download.start().addCallback(self.http_finished_png).addErrback(self.http_failed)
                    else:
                        self.download.start().addCallback(self.http_finished).addErrback(self.http_failed)
                    return
                if picartname == '':
                    if self.noCoverPixmap is None:
                        self.picon = False
                        self.hide()
                    else:
                        self.picartname = picartname
                        self.instance.setPixmap(self.noCoverPixmap)
                        self.show()
                else:
                    self.picon = True
                    if picartname != self.picartname:
                        self.hide()
                        self.picartname = picartname
                    else:
                        self.show()
                    self.countTumbLoad = 0
                    self.ThumbTimer.start(500, True)

    def http_finished(self, string = ''):
        if self.filename is None:
            return
        self.countTumbLoad = 0
        self.picon = True
        self.hide()
        self.ThumbTimer.start(500, True)

    def http_finished_png(self, string = ''):
        if self.filename is None:
            return
        self.instance.setPixmapFromFile(self.picartname)
        self.show()

    def http_failed(self, failure_instance = None, error_message = ''):
        if self.filename is None:
            return
        if error_message == '' and failure_instance is not None:
            error_message = failure_instance.getErrorMessage()
            print '[http_failed] ' + error_message
        if self.noCoverPixmap is None:
            self.picon = False
            self.hide()
        else:
            self.picartname = ''
            self.instance.setPixmap(self.noCoverPixmap)
            self.show()

    def findAicon(self, path, filename):
        if fileExists(path + '/' + filename + '.jpg'):
            return path + '/' + filename + '.jpg'
        if fileExists(path + '/' + filename + '.png'):
            return path + '/' + filename + '.png'
        if fileExists(path + '/' + filename + '.JPG'):
            return path + '/' + filename + '.JPG'
        if fileExists(path + '/' + filename + '.PNG'):
            return path + '/' + filename + '.PNG'
        if fileExists(path + '/folder.jpg'):
            return path + '/folder.jpg'
        if fileExists(path + '/folder.png'):
            return path + '/folder.png'
        if fileExists(path + '/.folder.jpg'):
            return path + '/.folder.jpg'
        if fileExists(path + '/.folder.png'):
            return path + '/.folder.png'
        return ''
