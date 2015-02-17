# 2014.10.12 15:52:54 CEST
from Imports import *
import Imports
from CardItems import CardItem
from CardItems import CardDisplayItem
from GboxSuiteUtils import *
from ShowFile import *
from OnlineCardInfo import *

class OnlineCardInfo(Screen):
    skin = '\n\t\t<screen position="center,center" size="580,420" title="Online Cards" >\n\t\t\t<widget name="cardAmountLabel" position="10,10" size="560,30" font="Regular;17" />\n\t\t\t<widget name="list" position="10,40" size="560,350" scrollbarMode="showOnDemand" />\n\t\t</screen>'

    def __init__(self, session, args = None):
        self.skin = OnlineCardInfo.skin
        Screen.__init__(self, session)
        self.newtitle = 'Online Cards'
        if args is not None:
            self.newtitle = 'Online Cards from ' + args[0]
        self.list = []
        self.cardItemDict = {}
        self.cardCount = 0
        self.onShown.append(self.updateTitle)
        try:
            fp = open(config.plugins.gs.infoDir.value + '/share.info', 'r')
            while 1:
                currentLine = fp.readline()
                if currentLine == '':
                    break
                currentLine = currentLine.replace(':', ' ')
                currentInfoList = currentLine.split(' ')
                currentProvId = currentInfoList[5]
                if args is None or args[0] == currentInfoList[3]:
                    self.cardCount += 1
                    if self.cardItemDict.has_key(currentProvId):
                        self.cardItemDict[currentProvId].addItem(CardItem(currentInfoList))
                    else:
                        self.cardItemDict[currentProvId] = CardDisplayItem(CardItem(currentInfoList))

            fp.close()
        except IOError:
            self.list.append((_(config.plugins.gs.infoDir.value + '/share.info' + ' not found!'), 'ERROR'))
        for x in self.cardItemDict:
            self.list.append((str(self.cardItemDict[x].count) + 'x ' + getProviderName(x), x))

        self.list.sort(providCompare)
        self.cardAmountLabel = Label(str(self.cardCount) + _(' Cards overall (') + str(len(self.cardItemDict)) + _(' providers)'))
        self['cardAmountLabel'] = self.cardAmountLabel
        self['list'] = MenuList(self.list)
        self['actions'] = ActionMap(['WizardActions', 'DirectionActions'], {'ok': self.go,
         'back': self.close}, -1)



    def go(self):
        currentProvid = self['list'].l.getCurrentSelection()[1]
        output = _('Card Details for Provider ') + getProviderName(currentProvid) + ':\n\n'
        if len(self.cardItemDict) > 0:
            for x in self.cardItemDict[currentProvid].cardList:
                output += _('- Card provided by ') + x.dyndns + _(' from boxid ') + x.boxid + _('   The Level of this card is ') + x.level + _(" and it's in distance ") + x.dist + '\n' + _('   The Card is inserted in slot ') + x.slot + '.\n\n'

            self.session.open(ShowFile, [_('Details for ') + currentProvid, output])



    def updateTitle(self):
        self.setTitle(self.newtitle)




def providCompare(i, j):
    if i[1] < j[1]:
        return -1
    else:
        if i[1] > j[1]:
            return 1
        return 0


