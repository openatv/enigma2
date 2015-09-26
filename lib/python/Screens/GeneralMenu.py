from boxbranding import getMachineBrand

from Screens.Screen import Screen
from Screens.Menu import UserMenu, UserMenuID
from Screens.PluginBrowser import PluginBrowser
from Screens.TimerEdit import TimerEditList
from Screens.InfoBar import InfoBar
from Screens.ChannelSelection import ChannelSelection
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Plugins.Extensions.FileCommander.plugin import FileCommanderScreen
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_WRAP
import os
from Components.SystemInfo import SystemInfo
from Components.MenuList import MenuList
from Components.Label import Label, MultiColorLabel
from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import *
from Components.ActionMap import ActionMap
from Components.MultiContent import MultiContentEntryPixmapAlphaTest, MultiContentEntryText
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from Components.ParentalControl import parentalControl
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Plugins.Plugin import PluginDescriptor


class boundFunction:
	def __init__(self, fnc, *args):
		self.fnc = fnc
		self.args = args

	def __call__(self):
		self.fnc(*self.args)

class GeneralMenuList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont('Regular', 23))
		self.l.setItemHeight(76)

def GeneralMenuEntryComponent(entrys, enableEntry, selectedEntry, onLeft=False, onRight=False):
	res = [entrys]
	entry_of = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_280x76_off.png'))
	entry_en = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_280x76_en.png'))
	entry_on = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_280x76_on.png'))
	entry_of_left = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_al_off.png'))
	entry_en_left = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_al_en.png'))
	entry_on_left = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_al_on.png'))
	entry_of_right = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_ar_off.png'))
	entry_en_right = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_ar_en.png'))
	entry_on_right = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_ar_on.png'))

	entry_pixmaps = (
		(entry_of_left, entry_of, entry_of_right),  # Not selected
		(entry_en_left, entry_en, entry_en_right),  # Selected, enabled != -1
		(entry_on_left, entry_on, entry_on_right),  # Selected, enabled == -1
	)
	colors = (
		0x00777777,  # Not selected
		0x00dddddd,  # Selected, enabled != -1
		0x00ffffff,  # Selected, enabled == -1
	)

	def sel3(first, second):
		return 0 if first else 2 if second else 1

	def select_pixmap(sel, enabled, left, right):
		return entry_pixmaps[sel3(sel, enabled)][sel3(left, right)]

	width = 250
	real_width = 100
	x_off = 15

	align = (RT_HALIGN_CENTER if width > real_width else RT_HALIGN_LEFT) | RT_VALIGN_CENTER

	x = x_off
	for count, entry in enumerate(entrys):
		if selectedEntry != count:
			pixmap = select_pixmap(True, False, count == 0 and onLeft, count == 4 and onRight)
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x - x_off, 0), size=(width + x_off * 2, 76), png=pixmap))
		x += width

	x = x_off
	for count, entry in enumerate(entrys):
		if selectedEntry == count:
			pixmap = select_pixmap(False, enableEntry == -1, count == 0 and onLeft, count == 4 and onRight)
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x - x_off, 0), size=(width + x_off * 2, 76), png=pixmap))

		color = colors[sel3(selectedEntry != count, enableEntry == -1)]

		res.append(MultiContentEntryText(pos=(x + x_off, 0), size=(width - x_off * 2, 76), font=0, text=entry.encode('utf-8'), flags=align, color=color, color_sel=color))
		x += width
	return res


class GeneralSubMenuList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont('Regular', 22))
		self.l.setItemHeight(50)

def GeneralSubMenuEntryComponent(entry, enableEntry=False, selectedEntry=False, onUp=False, onDown=False):
	x = 0
	x_off = 15
	width = 250
	res = [entry]
	entry_sl = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_250x50_on.png'))
	real_width = 100

	align = (RT_HALIGN_CENTER if width > real_width else RT_HALIGN_LEFT) | RT_VALIGN_CENTER
	color = 0x00ffffff if selectedEntry else 0x00999999 if enableEntry else 0x00555555

	if selectedEntry:
		res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 50), png=entry_sl))
	res.append(MultiContentEntryText(pos=(x + x_off, 0), size=(width - x_off * 2, 50), font=0, text=entry.encode('utf-8'), flags=align, color=color))
	return res

class GeneralMenuSummary(Screen):
	skin = '''<screen name="GeneralMenuSummary" position="0,0" size="255,64" >
				<widget name="mTitle" position="0,0" size="255,32" font="FdLcD;28" halign="center"/>
				<widget name="mMenu" position="0,41" size="255,50" font="FdLcD;24" halign="center"/>
			</screen>'''

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self['mTitle'] = Label()
		self['mMenu'] = Label()

	def setTextTitle(self, text):
		text = text.strip()
		if self['mTitle'].getText() != text:
			self['mTitle'].setText(text)

	def setTextMenu(self, text):
		text = text.strip()
		if self['mMenu'].getText() != text:
			self['mMenu'].setText(text)

class GeneralMenu(Screen):
	skin = '''
		<screen position="0,150" size="1280,570" flags="wfNoBorder" name="GeneralMenu">
			<widget position="0,10" size="1280,180" source="id_mainmenu_ext" render="Micon" path="easy-skin-hd/gmenu/" alphatest="on" zPosition="2" transparent="1" />
			<widget position="0,210" size="1280,76" name="list" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>

			<widget position="15,290" size="250,250" name="list_sub_0" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>
			<widget position="265,290" size="250,250" name="list_sub_1" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>
			<widget position="515,290" size="250,250" name="list_sub_2" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>
			<widget position="765,290" size="250,250" name="list_sub_3" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>
			<widget position="1015,290" size="250,250" name="list_sub_4" transparent="1"  backgroundColorSelected="#41000000" enableWrapAround="1"/>

			<widget position="122,280" size="35,10" name="up_sub_0" pixmap="easy-skin-hd/gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="372,280" size="35,10" name="up_sub_1" pixmap="easy-skin-hd/gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="622,280" size="35,10" name="up_sub_2" pixmap="easy-skin-hd/gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="872,280" size="35,10" name="up_sub_3" pixmap="easy-skin-hd/gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="1122,290" size="35,10" name="up_sub_4" pixmap="easy-skin-hd/gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>

			<widget position="122,540" size="35,10" name="down_sub_0" pixmap="easy-skin-hd/gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="372,540" size="35,10" name="down_sub_1" pixmap="easy-skin-hd/gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="622,540" size="35,10" name="down_sub_2" pixmap="easy-skin-hd/gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="872,540" size="35,10" name="down_sub_3" pixmap="easy-skin-hd/gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="1122,540" size="35,10" name="down_sub_4" pixmap="easy-skin-hd/gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
		</screen>'''

	ALLOW_SUSPEND = True

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.thread = None
		self.startEntry = 1
		self.selectedEntry = 3
		self.selectedEntryID = 'id_mainmenu_tv'

		if SystemInfo["IPTVSTB"]:
			tvEntryTitle = 'IPTV Channels'
		else:
			tvEntryTitle = 'TV / RADIO'

		self.entrys = [
			(_('Plugins'), 'id_mainmenu_plugins', boundFunction(self.openDialog, PluginBrowser)),
			(_('Photos'), 'id_mainmenu_photos', boundFunction(self.openPicturePlayer)),
			(_('Music'), 'id_mainmenu_music', boundFunction(self.openMediaPlayer)),
			(_(tvEntryTitle), 'id_mainmenu_tv', boundFunction(self.openChannelSelection)),
			(_('Videos'), 'id_mainmenu_movies', boundFunction(self.openRecordings)),
			(_('Sources'), 'id_mainmenu_source', boundFunction(self.openMediaScanner)),
			(_('Setup'), 'id_mainmenu_tasks', boundFunction(self.openGeneralSetup)),
		]

		self.startSubEntry = {}
		self.selectedSubEntry = {}
		for key in [k[1] for k in self.entrys]:
			self.startSubEntry[key] = 0
			self.selectedSubEntry[key] = -1

		self.subentrys = self.getSubEntrys()
		self.mainmenu_ext = {
			'id_mainmenu_plugins': 'gmenu_plugin',
			'id_mainmenu_photos': 'gmenu_photo',
			'id_mainmenu_music': 'gmenu_music',
			'id_mainmenu_tv': 'gmenu_tv',
			'id_mainmenu_movies': 'gmenu_movie',
			'id_mainmenu_source': 'gmenu_source',
			'id_mainmenu_tasks': 'gmenu_task',
		}
		self['id_mainmenu_ext'] = StaticText()
		self['list'] = GeneralMenuList([])
		for i in range(5):
			self['list_sub_%d' % i] = GeneralSubMenuList([])
			self['up_sub_%d' % i] = Pixmap()
			self['down_sub_%d' % i] = Pixmap()
			self['up_sub_%d' % i].hide()
			self['down_sub_%d' % i].hide()

		self['actions'] = ActionMap(['OkCancelActions', 'DirectionActions'], {
			'ok': self.keyOK,
			'cancel': self.hideMenuIfServiceRunning,
			'up': self.up,
			'upRepeated': self.up,
			'down': self.down,
			'downRepeated': self.down,
			'left': self.left,
			'leftRepeated': self.left,
			'right': self.right,
			'rightRepeated': self.right
		}, -2)

		from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
		hotplugNotifier.append(self.hotplugCB)
		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onShow.append(self.__onShow)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		print "__onClose"
		from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier
		hotplugNotifier.remove(self.hotplugCB)

	def __onFirstExecBegin(self):
		print "__onFirstExecBegin"
		self.buildGeneralMenu()

	def __onShow(self):
		print "__onShow"
		self.buildGeneralMenu()

	def left(self):
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		#print "ID---------------------------------"
		#print self.selectedEntryID
		#print "ID---------------------------------"
		self.selectedEntry -= 1
		if self.selectedEntry == -1:
			self.selectedEntry = 0
			self.startEntry = 0
			return
		if self.selectedEntry == 0:
			self.startEntry = 0
		else:
			self.startEntry = 1
		self.selectedEntryID = self.entrys[self.selectedEntry][1]
		if selectedSubEntry > len(self.subentrys[self.selectedEntryID]) - 1:
			self.selectedSubEntry[self.selectedEntryID] = len(self.subentrys[self.selectedEntryID]) - 1
		else:
			self.selectedSubEntry[self.selectedEntryID] = selectedSubEntry
		if self.selectedSubEntry[self.selectedEntryID] > 4:
			self.startSubEntry[self.selectedEntryID] = self.selectedSubEntry[self.selectedEntryID] - 4
		else:
			self.startSubEntry[self.selectedEntryID] = 0
		self.buildGeneralMenu()

	def right(self):
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		#print "ID---------------------------------"
		#print self.selectedEntryID
		#print "ID---------------------------------"
		self.selectedEntry += 1
		if self.selectedEntry == len(self.entrys):
			self.selectedEntry = len(self.entrys) - 1
			self.startEntry = 2
			return
		if self.selectedEntry == 6:
			self.startEntry = 2
		else:
			self.startEntry = 1
		self.selectedEntryID = self.entrys[self.selectedEntry][1]
		if selectedSubEntry > len(self.subentrys[self.selectedEntryID]) - 1:
			self.selectedSubEntry[self.selectedEntryID] = len(self.subentrys[self.selectedEntryID]) - 1
		else:
			self.selectedSubEntry[self.selectedEntryID] = selectedSubEntry
		if self.selectedSubEntry[self.selectedEntryID] > 4:
			self.startSubEntry[self.selectedEntryID] = self.selectedSubEntry[self.selectedEntryID] - 4
		else:
			self.startSubEntry[self.selectedEntryID] = 0
		self.buildGeneralMenu()

	def up(self):
		self.selectedSubEntry[self.selectedEntryID] -= 1
		if self.selectedSubEntry[self.selectedEntryID] < -1:
			self.selectedSubEntry[self.selectedEntryID] = len(self.subentrys[self.selectedEntryID]) - 1
		if self.selectedSubEntry[self.selectedEntryID] > 4:
			self.startSubEntry[self.selectedEntryID] = self.selectedSubEntry[self.selectedEntryID] - 4
		else:
			self.startSubEntry[self.selectedEntryID] = 0
		self.buildGeneralMenu()

	def down(self):
		self.selectedSubEntry[self.selectedEntryID] += 1
		if self.selectedSubEntry[self.selectedEntryID] >= len(self.subentrys[self.selectedEntryID]):
			self.selectedSubEntry[self.selectedEntryID] = -1
		if self.selectedSubEntry[self.selectedEntryID] > 4:
			self.startSubEntry[self.selectedEntryID] = self.selectedSubEntry[self.selectedEntryID] - 4
		else:
			self.startSubEntry[self.selectedEntryID] = 0
		self.buildGeneralMenu()

	def keyOK(self):
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		if selectedSubEntry == -1:
			self.entrys[self.selectedEntry][2]()
		if selectedSubEntry > -1:
			if selectedSubEntry < len(self.subentrys[self.selectedEntryID]):
				self.subentrys[self.selectedEntryID][selectedSubEntry][2]()

	def hideMenuIfServiceRunning(self):
		self.close()

	def openMenuID(self, menuID, menuName):
		menu_screen = self.session.openWithCallback(self.menuClosed, UserMenuID, menuID=menuID)
		menu_screen.setTitle(menuName)

	def openMenu(self, menuID, menuName):
		menu_screen = self.session.openWithCallback(self.menuClosed, UserMenu, menuID=menuID)
		menu_screen.setTitle(menuName)

	def openDialog(self, dialog):
		self.session.openWithCallback(self.menuClosed, dialog)

	def buildGeneralMenu(self):
		list = []
		extlist = []
		entrys = []
		count = 0
		self.selectedEntryID = self.entrys[self.selectedEntry][1]
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		for x in self.entrys:
			if count >= self.startEntry and count < self.startEntry + 5:
				entrys.append(x[0])
				sublist = []
				subcount = 0
				for y in self.subentrys[x[1]]:
					if subcount >= self.startSubEntry[x[1]] and subcount < self.startSubEntry[x[1]] + 5:
						if count == self.selectedEntry:
							sublist.append(GeneralSubMenuEntryComponent(y[0], enableEntry=True, selectedEntry=selectedSubEntry == subcount))
							# self['list_sub_' + str(count - self.startEntry)].show() ## for show only current sublist
						else:
							sublist.append(GeneralSubMenuEntryComponent(y[0], enableEntry=False, selectedEntry=False))
							# self['list_sub_' + str(count - self.startEntry)].hide() ## for show only current sublist
					subcount += 1

				self['list_sub_' + str(count - self.startEntry)].setList(sublist)

				if count == self.selectedEntry and selectedSubEntry > -1 and len(sublist) > 0:
					self['list_sub_' + str(count - self.startEntry)].selectionEnabled(1)
					self['list_sub_' + str(count - self.startEntry)].moveToIndex(selectedSubEntry - self.startSubEntry[x[1]])
					# print '[LINE MENU] start sub entry:', str(self.startSubEntry[x[1]])
					# print '[LINE MENU] select sub entry:', str(selectedSubEntry - self.startSubEntry[x[1]])
				else:
					self['list_sub_' + str(count - self.startEntry)].selectionEnabled(0)
				if self.startSubEntry[x[1]] > 0:
					self['up_sub_' + str(count - self.startEntry)].show()
				else:
					self['up_sub_' + str(count - self.startEntry)].hide()
				if len(self.subentrys[x[1]]) > 5 and self.selectedSubEntry[x[1]] != len(self.subentrys[x[1]]) - 1:
					self['down_sub_' + str(count - self.startEntry)].show()
				else:
					self['down_sub_' + str(count - self.startEntry)].hide()
			count += 1

		onLeft = self.startEntry > 0
		onRight = self.startEntry + 5 < len(self.entrys)
		list.append(GeneralMenuEntryComponent(entrys, selectedSubEntry, self.selectedEntry - self.startEntry, onLeft, onRight))
		self['list'].setList(list)
		self['id_mainmenu_ext'].setText(self.mainmenu_ext[self.selectedEntryID])
		if selectedSubEntry > -1:
			self['list'].selectionEnabled(0)
			self.summaries.setTextTitle(self.entrys[self.selectedEntry][0])
			if selectedSubEntry < len(self.subentrys[self.selectedEntryID]):
				self.summaries.setTextMenu(self.subentrys[self.selectedEntryID][selectedSubEntry][0])
			else:
				self.summaries.setTextMenu('')
		elif selectedSubEntry == -1:
			self['list'].selectionEnabled(1)
			self.summaries.setTextTitle('')
			self.summaries.setTextMenu(self.entrys[self.selectedEntry][0])
		else:
			self.summaries.setTextTitle('')
			self.summaries.setTextMenu('')

	def getSubEntrys(self):
		return {
			'id_mainmenu_plugins': self.getSubEntry(None, []),

			'id_mainmenu_photos': self.getSubEntry('id_mainmenu_photos', [
				#(_('Albums'),'mainmenu_photos_albums',boundFunction(self.openPicturePlayerAlbum),30),
				#(_('Slideshow'),'mainmenu_photos_playlists',boundFunction(self.openPicturePlayerSlideshow), 40),
				#(_('Thumbnails'),'mainmenu_photos_bouquets',boundFunction(self.openPicturePlayerThumb),50),
				(_('Flickr'), 'mainmenu_photos_playlists', boundFunction(self.openFlickr), 60),
				#(_('Setup'), 'mainmenu_tasks_setup', boundFunction(self.openPicturePlayerSetup), 100),
			]),

			'id_mainmenu_music': self.getSubEntry('id_mainmenu_music', []),

			'id_mainmenu_tv': self.getSubEntry('id_mainmenu_tv', [
				(_('History'), 'mainmenu_tv_zaphistory', boundFunction(self.openHisotryChannelSelection), 50),
				(_('Timers'), 'mainmenu_tv_timer', boundFunction(self.openDialog, TimerEditList), 60),
				(_('Program Guide'), 'mainmenu_tv_timer', boundFunction(self.openProgramGuide), 70),
			]),

			'id_mainmenu_movies': self.getSubEntry('id_mainmenu_movies', [
				(_('Recordings'), 'mainmenu_tv_recorded', boundFunction(self.openRecordings), 50),
			]),

			'id_mainmenu_source': self.getSubEntry('id_mainmenu_source', self.getScart(None, [])),

			'id_mainmenu_tasks': self.getSubEntry('id_mainmenu_tasks', [
				(_('Power'), 'mainmenu_tasks_power', boundFunction(self.openMenuID, 'shutdown', _('Power')), 20),
				(_('Information'), 'mainmenu_tasks_info', boundFunction(self.openMenuID, 'information', _('Information')), 30),
				#(_('Setup'), 'mainmenu_tasks_setup', boundFunction(self.openGeneralSetup), 30),
			]),
		}

	def openGeneralSetup(self):
		from Screens.GeneralSetup import GeneralSetup
		self.session.open(GeneralSetup)

	def notReadyMessage(self):
		self.session.open(MessageBox, _('This part is not ready yet!'), MessageBox.TYPE_INFO)

	def openFileManager(self, path):
		self.session.open(FileCommanderScreen, path)

	# sources
	def getScart(self, menuID, list):
		list = []
		i = 0
		if menuID is None:
			from Components.Harddisk import harddiskmanager
			for r in harddiskmanager.getMountedPartitions(onlyhotplug=False):
				menuitem = [r.tabbedShortDescription().split('\t')[0], r.mountpoint, boundFunction(self.openFileManager, r.mountpoint), i + 10]
				if menuitem[0] in ((_("Internal Flash")), _(".message")):  # , _("DLNA")):
					print "[MENU] Skip source:", menuitem[0]
				else:
					list.append(tuple(menuitem))
				"""
				deviceList = [ name for name in os.listdir("/media/upnp/") if os.path.isdir(os.path.join("/media/upnp/", name)) ]
				deviceList.sort()
				for d in deviceList:
					if d[0] in ('.', '_'): continue
					menuitem = [(_(d)), d, boundFunction(self.openFileManager, "/media/upnp/"+d+"/"), i+10]
					list.append(tuple(menuitem))
				"""
		#if SystemInfo.get('ScartMenu', True):
		#	     menuitem = [(_('Scart')), 'mainmenu_source_scart', boundFunction(self.openScart),1]
		#	     list.append(tuple(menuitem))
		#
		return list

	def openScart(self):
		self.session.scart.VCRSbChanged(3)

	# tv
	def openChannelSelection(self):
		self.hide()
		if InfoBar.instance.servicelist is None:
			InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
		InfoBar.instance.showTv()
		self.close(1)

	def openHisotryChannelSelection(self):
		self.hide()
		if InfoBar.instance.servicelist is None:
			InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
		InfoBar.instance.servicelist.historyZap(0)
		self.close(1)

	def openLiveTV(self):
		self.hide()
		if InfoBar.instance.servicelist is None:
			InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
		InfoBar.instance.servicelist.setModeTv()
		InfoBar.instance.servicelist.zap()
		self.close(1)

	def openLiveRadio(self):
		self.hide()
		if InfoBar.instance.servicelist is None:
			InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
		InfoBar.instance.showRadio()
		self.close(1)

	def openRecordings(self):
		InfoBar.instance.showMovies()

	def openProgramGuide(self):
		#InfoBar.instance.openMultiServiceEPG()
		InfoBar.instance.openGraphEPG()

	# Photos
	def openPicturePlayer(self):
		from Plugins.Extensions.PicturePlayer.ui import picshow
		self.session.open(picshow)

	# Photos Albums
	def openPicturePlayerAlbum(self):
		parts = [(r.tabbedDescription() + "photos/", r.mountpoint + "photos/", self.session) for r in harddiskmanager.getMountedPartitions(onlyhotplug=False) if os.access(r.mountpoint, os.F_OK | os.R_OK)]
		parts.append((_("Other") + "\t/media", "/media", self.session))
		self.session.openWithCallback(self.openPicturePlayerAlbumDevice, ChoiceBox, title=_("Please select device for albums"), list=parts)

	def openPicturePlayerAlbumDevice(self, option):
		if option is None:
			return
		parts = []
		for f in os.listdir(option[1]):
			if os.path.isdir(os.path.join(option[1], f)):
				parts.append((f, os.path.join(option[1], f), self.session))

		self.session.openWithCallback(self.openPicturePlayerAlbumDir, ChoiceBox, title=_("Please select album"), list=parts)

	def openPicturePlayerAlbumDir(self, option):
		if option is None:
			return
		path = option[1] + "/"
		from Plugins.Extensions.PicturePlayer.ui import config, picshow
		try:
			config.pic.lastDir.setValue(path)
		except:
			pass
		self.session.open(picshow)

	# Photos SlideShow
	def openPicturePlayerSlideshow(self):
		parts = [(r.tabbedDescription() + "photos/", r.mountpoint + "photos/", self.session) for r in harddiskmanager.getMountedPartitions(onlyhotplug=False) if os.access(r.mountpoint, os.F_OK | os.R_OK)]
		parts.append((_("Other") + "\t/media", "/media", self.session))
		self.session.openWithCallback(self.openPicturePlayerSlideDevice, ChoiceBox, title=_("Please select device for slideshow"), list=parts)

	def openPicturePlayerSlideDevice(self, option):
		if option is None:
			return
		parts = []
		for f in os.listdir(option[1]):
			if os.path.isdir(os.path.join(option[1], f)):
				parts.append((f, os.path.join(option[1], f), self.session))

		self.session.openWithCallback(self.openPicturePlayerSlideDir, ChoiceBox, title=_("Please select album for slideshow"), list=parts)

	def openPicturePlayerSlideDir(self, option):
		if option is None:
			return
		from Plugins.Extensions.PicturePlayer.ui import Pic_Full_View
		from Components.FileList import FileList
		path = option[1] + "/"
		filelist = FileList(path, matchingPattern="(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif)")
		self.session.open(Pic_Full_View, filelist.getFileList(), 0, filelist.getCurrentDirectory())

	# Photos Thumb
	def openPicturePlayerThumb(self):
		parts = [(r.tabbedDescription() + "photos/", r.mountpoint + "photos/", self.session) for r in harddiskmanager.getMountedPartitions(onlyhotplug=False) if os.access(r.mountpoint, os.F_OK | os.R_OK)]
		parts.append((_("Other") + "\t/media", "/media", self.session))
		self.session.openWithCallback(self.openPicturePlayerThumbDevice, ChoiceBox, title=_("Please select device for thumbnails"), list=parts)

	def openPicturePlayerThumbDevice(self, option):
		if option is None:
			return
		parts = []
		for f in os.listdir(option[1]):
			if os.path.isdir(os.path.join(option[1], f)):
				parts.append((f, os.path.join(option[1], f), self.session))

		self.session.openWithCallback(self.openPicturePlayerThumbDir, ChoiceBox, title=_("Please select album"), list=parts)

	def openPicturePlayerThumbDir(self, option):
		if option is None:
			return
		from Plugins.Extensions.PicturePlayer.ui import Pic_Thumb
		from Components.FileList import FileList
		path = option[1] + "/"
		filelist = FileList(path, matchingPattern="(?i)^.*\.(jpeg|jpg|jpe|png|bmp|gif)")
		self.session.open(Pic_Thumb, filelist.getFileList(), 0, filelist.getCurrentDirectory())

	def openPicturePlayerSetup(self):
		from Plugins.Extensions.PicturePlayer.ui import Pic_Setup
		self.session.open(Pic_Setup)

	def openFlickr(self):
		from Plugins.Extensions.IniEcasa.EcasaGui import EcasaOverview
		self.session.open(EcasaOverview)

	# Music
	def openMediaPlayer(self):
		from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
		self.session.open(MediaPlayer)

	def openMediaPlayerSetup(self):
		from Plugins.Extensions.MediaPlayer.settings import MediaPlayerSettings
		self.session.open(MediaPlayerSettings, self)

	# Sources
	def openMediaScanner(self):
		from Plugins.Extensions.MediaScanner.plugin import main
		main(self.session)

	def getSubEntry(self, menuID, list):
		if menuID is None:
			for l in plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU):
				if isinstance(l.iconstr, str):
					menuitem = [l.name, '/'.join((l.path, l.iconstr)), boundFunction(self.runPlugin, (l, None)), l.weight]
				else:
					menuitem = [l.name, '', boundFunction(self.runPlugin, (l, None)), l.weight]
				if l.name in [
					_("Front Panel Update"),
					_("CrossEPG Downloader"),
					_("OpenWebif"),
					_("Software management"),
					_("MediaPortal"),
					_("AutoTimer"),
					_("Picture player"),
					_("YouTube TV Settings")]:
					print "Skip =>", l.name
				else:
					list.append(tuple(menuitem))
		else:
			for l in plugins.getPluginsForMenu(menuID):
				if len(l) > 5:
					menuitem = [l[0], l[2], boundFunction(self.runPlugin, (l[1], l[6])), l[3] or 50]
				else:
					menuitem = [l[0], l[2], boundFunction(self.runPlugin, (l[1], None)), l[3] or 50]
				if l[0] in [
					_("Front Panel Update"),
					_("CrossEPG Downloader"),
					_("OpenWebif"),
					_("Software management"),
					_("MediaPortal"),
					_("Picture player"),
					_("YouTube TV Settings")]:
					print "Skip =>", l.name
				else:
					list.append(tuple(menuitem))
			# This is little HACK to show AutoTimer in TV section, as We do not want to clone AutTimer git and reqwrite it to show in our section
			for l in plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU):
				if l.name == _("AutoTimer"):
					if menuID == "id_mainmenu_tv":
						if isinstance(l.iconstr, str):
							menuitem = [l.name, '/'.join((l.path, l.iconstr)), boundFunction(self.runPlugin, (l, None)), 60]
						else:
							menuitem = [l.name, '', boundFunction(self.runPlugin, (l, None)), 60]
						list.append(tuple(menuitem))
		try:
			list.sort(key=lambda x: int(x[3]))
		except:
			list.sort(key=lambda x: x[3])

		return list

	def runPlugin(self, arg):
		arg[0](session=self.session, callback=self.menuClosed, extargs=arg[1])

	def menuClosed(self, *res):
		if res and res[0]:
			if len(res) == 1:
				self.close(True)
				return
			if len(res) == 2:
				if res[1] is None:
					self.close()
					return

	def createSummary(self):
		return GeneralMenuSummary

	def hotplugCB(self, dev, media_state):
		print "hotplugCB"
		self.subentrys = self.getSubEntrys()
		self.buildGeneralMenu()
