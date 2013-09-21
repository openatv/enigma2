try:
    from __init__ import _
except:
    pass

from Screens.Screen import Screen
from Screens.Setup import Setup, getSetupTitle
from Components.Sources.List import List
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Sources.StaticText import StaticText
from Components.PluginComponent import plugins
from Components.config import config, configfile
from Components.SystemInfo import SystemInfo
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.MultiContent import MultiContentEntryText
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_WRAP
from enigma import eServiceReference, iServiceInformation
from os import system
from Tools.Directories import fileExists, resolveFilename, SCOPE_SKIN, SCOPE_ACTIVE_SKIN
import xml.etree.cElementTree
MENU_MAIN = 0
MENU_UP = 1
MENU_DOWN = 2
mdom = xml.etree.cElementTree.parse(resolveFilename(SCOPE_SKIN, 'menu.xml'))

class boundFunction():

    def __init__(self, fnc, *args):
        self.fnc = fnc
        self.args = args

    def __call__(self):
        self.fnc(*self.args)


class MenuUpdater():

    def __init__(self):
        self.updatedMenuItems = {}

    def addMenuItem(self, id, pos, text, module, screen, weight, endtext = '>'):
        if not self.updatedMenuAvailable(id):
            self.updatedMenuItems[id] = []
        self.updatedMenuItems[id].append([text, pos, module, screen, weight, endtext])

    def delMenuItem(self, id, pos, text, module, screen, weight, endtext = '>'):
        self.updatedMenuItems[id].remove([text, pos, module, screen, weight, endtext])

    def updatedMenuAvailable(self, id):
        return self.updatedMenuItems.has_key(id)

    def getUpdatedMenu(self, id):
        return self.updatedMenuItems[id]


menuupdater = MenuUpdater()

def CharEntryComponent(char):
    return [char, MultiContentEntryText(pos=(0, 0), size=(40, 50), font=1, flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, text=char)]


class CharList(MenuList):

    def __init__(self, list, enableWrapAround = False):
        MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
        self.l.setFont(0, gFont('Regular', 22))
        self.l.setFont(1, gFont('Regular', 18))
        self.l.setItemHeight(50)


class MenuSummary(Screen):
    pass


class Menu(Screen):
    ALLOW_SUSPEND = True
    MENU_LIST = 0
    CHAR_LIST = 1

    def okbuttonClick(self):
        print 'okbuttonClick'
        if self.currentlist == self.MENU_LIST:
            selection = self['menu'].getCurrent()
            if selection is not None:
                selection[1]()
        elif self.findmenu == 1 and self.currentlist == self.CHAR_LIST:
            if len(self.charlist) == 0:
                self.selList()
                return
            if self['charlist'].l.getCurrentSelection() is None:
                self.selList()
                return
            f_char = self['charlist'].l.getCurrentSelection()[0]
            self.leftMenu()
            if len(self.list) == 0:
                return
            if self['menu'].getCurrent() is None:
                return
            currindex = self['menu'].getIndex()
            index = currindex + 1
            count = len(self.list)
            if index == count:
                index = 0
            while index != currindex:
                title = self.list[index][0].decode('UTF-8', 'ignore')
                if len(title) > 0:
                    if len(title) > 3 and title[2:4] == '. ' and title[:2].isdigit():
                        char = title[4].upper()
                    else:
                        char = title[0].upper()
                    if char == f_char:
                        self.setDefault(index)
                        break
                index += 1
                if index == count:
                    index = 0

    def menubuttonClick(self):
        print 'menubuttonClick'
        selection = self['menu'].getCurrent()
        if selection is not None:
            if len(selection) > 5 and selection[5] is not None:
                selection[5]()

    def execText(self, text):
        exec text.strip()

    def runScreen(self, arg):
        if arg[0] != '':
            exec 'from ' + arg[0] + ' import *'
        self.openDialog(*eval(arg[1]))

    def runPlugin(self, arg):
        arg[0](session=self.session, callback=self.menuClosed, extargs=arg[1])

    def nothing(self):
        pass

    def openDialog(self, *dialog):
        self.session.openWithCallback(self.menuClosed, *dialog)

    def openSetup(self, dialog):
        self.session.openWithCallback(self.menuClosed, Setup, dialog)

    def addMenu(self, destList, node):
        requires = node.get('requires')
        if requires:
            if requires.startswith('config.'):
                if configfile.getResolvedKey(requires) == 'False':
                    return
            elif requires[0] == '!':
                if SystemInfo.get(requires[1:], False):
                    return
            elif not SystemInfo.get(requires, False):
                return
        MenuTitle = _(node.get('text', '??').encode('UTF-8'))
        entryID = node.get('entryID', 'undefined')
        weight = node.get('weight', 50)
        end_text = node.get('endtext', '>').encode('UTF-8')
        x = node.get('flushConfigOnClose')
        if x:
            a = boundFunction(self.session.openWithCallback, self.menuClosedWithConfigFlush, Menu, node)
        else:
            a = boundFunction(self.session.openWithCallback, self.menuClosed, Menu, node)
        destList.append((MenuTitle, a, entryID, weight, end_text))

    def menuClosedWithConfigFlush(self, *res):
        configfile.save()
        self.menuClosed(*res)

    def menuClosed(self, *res):
        print '[MENU] close res:', res, ', id_mainmenu:', str(self.id_mainmenu)
        if res and res[0]:
            if len(res) == 1:
                self.close(True)
                return
            if len(res) == 2:
                if res[1] is None:
                    self.close()
                    return
                if res[1] == MENU_MAIN and not self.id_mainmenu:
                    print '[MENU] close not MENU_MAIN'
                    self.close(True, MENU_MAIN)
                    return
        if self.update:
            lenmenu = len(self['menu'].list)
            index = self['menu'].getIndex()
            self.reloadMenu()
            self.setDefault(index + len(self['menu'].list) - lenmenu)
        if self.id_mainmenu:
            self.setTitle("Main Menu")
        elif res and res[0] and len(res) == 2 and res[1] == MENU_UP:
            self['menu'].selectPrevious()
        elif res and res[0] and len(res) == 2 and res[1] == MENU_DOWN:
            self['menu'].selectNext()

    def addItem(self, destList, node):
        requires = node.get('requires')
        if requires:
            if requires.startswith('config.'):
                if configfile.getResolvedKey(requires) == 'False':
                    return
            elif requires[0] == '!':
                if SystemInfo.get(requires[1:], False):
                    return
            elif not SystemInfo.get(requires, False):
                return
        item_text = node.get('text', '').encode('UTF-8')
        entryID = node.get('entryID', 'undefined')
        weight = node.get('weight', 50)
        end_text = node.get('endtext', '>').encode('UTF-8')
        for x in node:
            if x.tag == 'screen':
                module = x.get('module')
                screen = x.get('screen')
                if screen is None:
                    screen = module
                print module, screen
                if module:
                    if module.find('.') == -1:
                        module = 'Screens.' + module
                    else:
                        try:
                            exec 'from ' + module + ' import *'
                        except:
                            module = None

                else:
                    module = ''
                args = x.text or ''
                screen += ', ' + args
                if module is not None:
                    destList.append((_(item_text or '??'), boundFunction(self.runScreen, (module, screen)), entryID, weight, end_text))
                return
            if x.tag == 'code':
                destList.append((_(item_text or '??'), boundFunction(self.execText, x.text), entryID, weight, end_text))
                return
            if x.tag == 'setup':
                id = x.get('id')
                if item_text == '':
                    item_text = getSetupTitle(id)
                destList.append((_(item_text), boundFunction(self.openSetup, id), entryID, weight, end_text))
                return

        destList.append((_(item_text), self.nothing, entryID, weight, end_text))

    def __init__(self, session, parent, menuID = None, default = 0, update = 0, overrides = 1, endtext = '>', sort = 'sort', findmenu = 0):
        Screen.__init__(self, session)
        self.currentlist = self.MENU_LIST
        self.parent = parent
        self.menuID = menuID
        self.findmenu = findmenu
        self.default = str(default)
        self.update = update
        self.overrides = overrides
        self.endtext = endtext
        self.sort = sort
        self.menu_title = ''
        self['charframe'] = Pixmap()
        self['charframe'].hide()
        self.charlist = {}
        self['charlist'] = CharList([])
        self['charlist'].selectionEnabled(0)
        self['menu'] = List()
        self['title'] = StaticText('')
        self.reloadMenu()
        self.skinName = []
        if self.menuID is not None:
            self.skinName.append('menu_' + self.menuID)
        self.skinName.append('Menu')
        self.id_mainmenu = False
        if self.menuID is not None:
            if self.menuID == 'id_mainmenu':
                self.id_mainmenu = True
                self.setTitle("Main Menu")

        class MenuSelectionActionMap(NumberActionMap):

            def __init__(self, menu, contexts = [], actions = {}, prio = -1):
                NumberActionMap.__init__(self, contexts, actions, prio)
                self.menu = menu

            def action(self, contexts, action):
                print '[MENU][MenuSelectionActionMap] action:', action
                if action == 'up' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'down' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'left' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'right' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'upRepeated' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'downRepeated' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'leftRepeated' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                elif action == 'rightRepeated' and self.menu.currentlist == self.menu.MENU_LIST:
                    return 0
                else:
                    return NumberActionMap.action(self, contexts, action)

	self["actions"] = NumberActionMap(["OkCancelActions", "MenuActions", "NumberActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.closeNonRecursive,
				"menu": self.closeRecursive,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal
			})
			
        if self.parent is not None:
            a = self.parent.get('title', '').encode('UTF-8') or None
            a = a and _(a)
            if a is None:
                a = _(self.parent.get('text', '').encode('UTF-8'))
            self.menu_title = a
            self.setTitle(a)
        self.onFirstExecBegin.append(self.setDefault)

    def reloadMenu(self):
        self.list = []
        count = 0
        if self.parent is not None:
            for x in self.parent:
                if x.tag == 'item':
                    item_level = int(x.get('level', 0))
                    if item_level <= config.usage.setup_level.index:
                        self.addItem(self.list, x)
                        count += 1
                elif x.tag == 'menu':
                    item_level = int(x.get('level', 0))
                    if item_level <= config.usage.setup_level.index:
                        self.addMenu(self.list, x)
                        count += 1
                elif x.tag == 'id':
                    self.menuID = x.get('val')
                    self.default = str(x.get('default', 0))
                    self.update = int(x.get('update', 0))
                    self.overrides = int(x.get('overrides', 1))
                    self.findmenu = int(x.get('findmenu', self.findmenu))
                    self.endtext = str(x.get('endtext', '>'))
                    count = 0
                if self.menuID is not None:
                    if menuupdater.updatedMenuAvailable(self.menuID):
                        for x in menuupdater.getUpdatedMenu(self.menuID):
                            if x[1] == count:
                                self.list.append((x[0],
                                 boundFunction(self.runScreen, (x[2], x[3] + ', ')), x[4], '>'))
                                count += 1

        if self.menuID is not None:
            for l in plugins.getPluginsForMenu(self.menuID):
                if self.overrides:
                    plugin_menuid = l[2]
                    for x in self.list:
                        if x[2] == plugin_menuid:
                            self.list.remove(x)
                            break

                endtext = self.endtext
                if len(l) > 4:
                    endtext = l[4]
                if len(l) > 5:
                    if l[5] is None:
                        menuitem = [l[0], boundFunction(self.runPlugin, (l[1], l[6])), l[2], l[3] or 50, endtext, None]
                    else:
                        menuitem = [l[0], boundFunction(self.runPlugin, (l[1], l[6])), l[2], l[3] or 50, endtext, boundFunction(self.runPlugin, (l[5], l[6]))]
                    for x in range(7, len(l)):
                        menuitem.append(l[x])

                else:
                    menuitem = [l[0], boundFunction(self.runPlugin, (l[1], None)), l[2], l[3] or 50, endtext, None]
                self.list.append(tuple(menuitem))

        try:
            if self.sort == 'sort':
                self.list.sort(key=lambda x: int(x[3]))
            if self.sort == 'reverse':
                self.list.sort(key=lambda x: int(x[3]))
                self.list.reverse()
        except:
            if self.sort == 'sort':
                self.list.sort(key=lambda x: x[3])
            if self.sort == 'reverse':
                self.list.sort(key=lambda x: x[3])
                self.list.reverse()

        if self.findmenu == 1:
            self.charlist = {}
            for x in self.list:
                title = x[0].decode('UTF-8', 'ignore')
                if len(title) > 0:
                    if len(title) > 3 and title[2:4] == '. ' and title[:2].isdigit():
                        char = title[4].upper()
                    else:
                        char = title[0].upper()
                    self.charlist[char] = CharEntryComponent(char.encode('UTF-8'))

        self['menu'].setList(self.list)

    def rightMenu(self):
        if self.findmenu == 1 and self.currentlist == self.MENU_LIST:
            self.currentlist = self.CHAR_LIST
            self['charframe'].show()
            self['charlist'].selectionEnabled(1)
            charlist = []
            char_keys = self.charlist.keys()
            char_keys.sort()
            for x in char_keys:
                print '[MENU][rightMenu] add char:', x
                charlist.append(self.charlist[x])

            self['charlist'].l.setList(charlist)

    def leftMenu(self):
        if self.findmenu == 1 and self.currentlist == self.CHAR_LIST:
            self.currentlist = self.MENU_LIST
            self['charlist'].selectionEnabled(0)
            self['charlist'].l.setList([])
            self['charframe'].hide()

    def goLeft(self):
        self['charlist'].pageUp()

    def goRight(self):
        self['charlist'].pageDown()

    def goUp(self):
        self['charlist'].up()

    def goDown(self):
        self['charlist'].down()

    def setTitle(self, text):
        self['title'].text = text
        self.menu_title = text

    def setDefault(self, index = None):
        lenmenu = len(self['menu'].list)
        if lenmenu == 0:
            return
        if index is not None:
            if lenmenu > index:
                self['menu'].setIndex(index)
            else:
                self['menu'].setIndex(lenmenu - 1)
        elif self.default.isdigit():
            default = int(self.default)
            if lenmenu > default:
                self['menu'].setIndex(default)
            else:
                self['menu'].setIndex(0)
        else:
            for x in range(0, lenmenu):
                y = self['menu'].list[x]
                if len(y) > 4 and y[4] == self.default:
                    self['menu'].setIndex(x)
                    break
            else:
                self['menu'].setIndex(0)

    def keyNumberGlobal(self, number):
        print 'menu keyNumber:', number
        number -= 1
        if len(self['menu'].list) > number:
            self['menu'].setIndex(number)
            self.okbuttonClick()

    def closeNonRecursive(self):
        if self.currentlist == self.MENU_LIST:
            if not self.id_mainmenu:
                self.close(False)
        else:
            self.leftMenu()

    def closeRecursive(self):
        self.close(True)

    def createSummary(self):
        return MenuSummary

class MainMenu(Menu):

    def __init__(self, *x):
        self.skinName = 'Menu'
        Menu.__init__(self, *x)
        self.setTitle("Main Menu")


class MainMenuID(Menu):

    def __init__(self, session, menuID = None):
        self.skinName = 'Menu'
        Menu.__init__(self, session, self.getParentMenuID(menuID))
        self.setTitle("Main Menu")

    def getParentMenuID(self, menuID, root = None):
        if root is None:
            root = mdom.getroot()
        for menu in root.findall('menu'):
            id = menu.find('id')
            if id is not None:
                get_id = id.get('val')
                if get_id and get_id == menuID:
                    return menu
            ret = self.getParentMenuID(menuID, root=menu)
            if ret is not None:
                return ret


class UserMenu(Menu):

    def __init__(self, session, parent = None, menuID = None, default = 0, update = 0, overrides = 1, sort = 'sort', findmenu = 0):
        self.skinName = 'Menu'
        Menu.__init__(self, session, parent, menuID=menuID, default=default, update=update, overrides=overrides, sort=sort, findmenu=findmenu)


class UserMenuID(Menu):

    def __init__(self, session, parent = None, menuID = None, default = 0, update = 0, overrides = 1, sort = 'sort', findmenu = 0):
        self.skinName = 'Menu'
        parent = self.getParentMenuID(menuID)
        if parent is not None:
            menuID = None
        Menu.__init__(self, session, parent, menuID=menuID, default=default, update=update, overrides=overrides, sort=sort, findmenu=findmenu)

    def getParentMenuID(self, menuID, root = None):
        if root is None:
            root = mdom.getroot()
        for menu in root.findall('menu'):
            id = menu.find('id')
            if id is not None:
                get_id = id.get('val')
                if get_id and get_id == menuID:
                    return menu
            ret = self.getParentMenuID(menuID, root=menu)
            if ret is not None:
                return ret
