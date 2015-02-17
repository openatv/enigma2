# 2014.10.12 15:53:24 CEST
from Imports import *
import Imports
from PeerList import *
from GboxSuiteUtils import *
from OnlineCardInfo import *

class PeerStatus(Screen):
    skin = '\n\t\t<screen position="center,center" size="580,420" title="Peer Status" >\n\t\t\t<widget name="list" position="10,10" size="380,400" scrollbarMode="showOnDemand" />\n\t\t\t<widget name="text" position="400,10" size="180,400" font="Regular;16" />\n\t\t</screen>'

    def __init__(self, session, args = None):
        self.skin = PeerStatus.skin
        Screen.__init__(self, session)
        self.list = []
        self.onlineList = []
        self.noCardsList = []
        self.offlineList = []
        try:
            temp = readTextFile((config.plugins.gs.infoDir.value + '/share.info', config.plugins.gs.infoDir.value + '/share.info not found'))
            fp = open(config.plugins.gs.infoDir.value + '/share.onl', 'r')
            while 1:
                currentLine = fp.readline()
                if currentLine == '':
                    break
                currentInfoList = currentLine.split(' ')
                currentDyndns = currentInfoList[1]
                if currentInfoList[0] == '0':
                    self.offlineList.append(PeerEntryComponent(currentDyndns, currentDyndns, 1))
                else:
                    findRes = temp.count(currentDyndns)
                    if findRes <= 0:
                        self.noCardsList.append(PeerEntryComponent(currentDyndns, currentDyndns, 2))
                    else:
                        self.onlineList.append(PeerEntryComponent(currentDyndns + ' - ' + str(findRes) + ' Cards', currentDyndns, 0))

            fp.close()
        except IOError:
            self.list.append(PeerEntryComponent('File Not Found:', config.plugins.gs.infoDir.value + '/share.onl', 1))
        for x in self.offlineList:
            self.list.append(x)

        for x in self.noCardsList:
            self.list.append(x)

        for x in self.onlineList:
            self.list.append(x)

        self['list'] = PeerList(self.list)
        self['text'] = ScrollLabel('Total Peers in cwshare: ' + str(len(self.offlineList) + len(self.onlineList) + len(self.noCardsList)) + '\n\nOnline Peers: ' + str(len(self.onlineList) + len(self.noCardsList)) + '\n\nOffline Peers: ' + str(len(self.offlineList)) + '\n\nPeers not sharing any cards: ' + str(len(self.noCardsList)))
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.go,
         'back': self.close}, -1)



    def go(self):
        currentDyndns = self['list'].l.getCurrentSelection()[3]
        if self['list'].l.getCurrentSelection()[0] == 0:
            self.session.open(OnlineCardInfo, [currentDyndns])


