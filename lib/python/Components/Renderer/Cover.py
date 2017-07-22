from Renderer import Renderer
from enigma import ePixmap, ePicLoad
from Components.AVSwitch import AVSwitch
from Components.Pixmap import Pixmap
from Components.config import config
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.CurrentService import CurrentService
from os import path as os_path

class Cover(Renderer):
    exts = ('.jpg', '.png', '.jpeg')

    def __init__(self):
        Renderer.__init__(self)
        self.nameCache = {}
        self.picname = ''

    GUI_WIDGET = ePixmap

    def changed(self, what):
        if not self.instance:
            return
        else:
            picname = ''
            sname = ''
            if what[0] != self.CHANGED_CLEAR:
                service = None
                if isinstance(self.source, ServiceEvent):
                    service = self.source.getCurrentService()
                elif isinstance(self.source, CurrentService):
                    service = self.source.getCurrentServiceReference()
                if service:
                    sname = service.getPath()
                else:
                    return
                picname = self.nameCache.get(sname, '')
                if picname == '':
                    picname = self.findCover(sname)[1]
                if picname == '':
                    path = sname
                    if service.toString().endswith == '..':
                        path = config.movielist.last_videodir.value
                    for ext in self.exts:
                        p = os_path.dirname(path) + '/folder' + ext
                        picname = os_path.exists(p) and p or ''
                        if picname:
                            break

                if picname != '':
                    self.nameCache[sname] = picname
                if picname == self.picname:
                    return
                self.picname = picname
                if picname != '' and os_path.exists(picname):
                    sc = AVSwitch().getFramebufferScale()
                    size = self.instance.size()
                    self.picload = ePicLoad()
                    self.picload.PictureData.get().append(self.showCoverCallback)
                    if self.picload:
                        self.picload.setPara((size.width(),
                         size.height(),
                         sc[0],
                         sc[1],
                         False,
                         1,
                         '#00000000'))
                        if self.picload.startDecode(picname) != 0:
                            del self.picload
                else:
                    self.instance.hide()
            return

    def showCoverCallback(self, picInfo = None):
        if self.picload:
            ptr = self.picload.getData()
            if ptr != None:
                self.instance.setPixmap(ptr)
                self.instance.show()
            del self.picload
        return

    def findCover(self, path):
        fpath = p1 = p2 = p3 = ''
        name, ext = os_path.splitext(path)
        ext = ext.lower()
        if os_path.isfile(path):
            dir = os_path.dirname(path)
            p1 = name
            p2 = os_path.join(dir, os_path.basename(dir))
        elif os_path.isdir(path):
            if path.lower().endswith('/bdmv'):
                dir = path[:-5]
                if dir.lower().endswith('/brd'):
                    dir = dir[:-4]
            elif path.lower().endswith('video_ts'):
                dir = path[:-9]
                if dir.lower().endswith('/dvd'):
                    dir = dir[:-4]
            else:
                dir = path
                p2 = os_path.join(dir, 'folder')
            prtdir, dirname = os_path.split(dir)
            p1 = os_path.join(dir, dirname)
            p3 = os_path.join(prtdir, dirname)
        pathes = (p1, p2, p3)
        for p in pathes:
            for ext in self.exts:
                path = p + ext
                if os_path.exists(path):
                    break

            if os_path.exists(path):
                fpath = path
                break

        return (p1, fpath)
