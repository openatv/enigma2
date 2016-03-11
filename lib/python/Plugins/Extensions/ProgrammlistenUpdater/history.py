from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
import re, os, urllib2, sys

URL ='http://www.sattechnik.de/programmlisten-update/history.txt'

def DownloadInfo(url):
    text = ""
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        link = response.read().decode("windows-1252")
        response.close()
        text = link.encode("utf-8")

    except:
        print"ERROR Download History %s" %(url)

    return text



class PU_History(Screen):

    skin =  """
        <screen name="PU_History" position="center,center" size="600,470">
            <ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
            <widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
            <widget name="History" position="25,70" size="560,350" scrollbarMode="showOnDemand" />
        </screen>
        """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.skinName = "PU_History"
        self.setup_title = _("Programmlisten-Updater History")
        self.setTitle(self.setup_title)
        
        self["key_red"] = StaticText(_("Exit"))
        self["History"] = ScrollLabel()


        self["Actions"] = ActionMap(['OkCancelActions', 'ShortcutActions',"ColorActions","DirectionActions"],
            {
            "red": self.keyOk,
            "cancel" : self.keyOk,
            "ok" : self.keyOk,
            "up": self["History"].pageUp,
            "down": self["History"].pageDown,
            "left": self["History"].pageUp,
            "right": self["History"].pageDown,
            })
        self['History'].setText(DownloadInfo(URL))

    def keyOk(self):
        self.close()

