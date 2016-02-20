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
from enigma import eListboxPythonMultiContent, gRGB, gFont, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER
import os
from Components.SystemInfo import SystemInfo
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config
from Components.ActionMap import ActionMap
from Components.MultiContent import MultiContentEntryPixmapAlphaTest, MultiContentEntryText
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.ExtraAttributes import applyExtraSkinAttributes
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor


class GeneralSubMenuList(MenuList):
	attribMap = {
		# Plain ints
		"itemHeight": ("int", "itemHeight"),
		# Fonts
		"font": ("font", "fontName", "fontSize"),
		# Colors
		"offColor": ("color", "offColor"),
		"enabledColor": ("color", "enabledColor"),
		"selectedColor": ("color", "selectedColor"),
	}

	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.selectedColor = 0x00ffffff
		self.enabledColor = 0x00999999
		self.offColor = 0x00555555
		self.fontName = "Regular"
		self.fontSize = 22
		self.itemHeight = 50

	def applySkin(self, desktop, screen):
		self.skinAttributes = applyExtraSkinAttributes(self, self.skinAttributes, self.attribMap)
		rc = super(GeneralSubMenuList, self).applySkin(desktop, screen)

		self.l.setFont(0, gFont(self.fontName, self.fontSize))
		self.l.setItemHeight(self.itemHeight)

		return rc

def GeneralSubMenuEntryComponent(entry, subMenulist, enableEntry=False, selectedEntry=False, onUp=False, onDown=False):
	x = 0
	x_off = 15
	width = 250
	res = [entry]
	real_width = 100

	align = (RT_HALIGN_CENTER if width > real_width else RT_HALIGN_LEFT) | RT_VALIGN_CENTER
	color = subMenulist.selectedColor if selectedEntry else subMenulist.enabledColor if enableEntry else subMenulist.offColor

	res.append(MultiContentEntryText(pos=(x + x_off, 0), size=(width - x_off * 2, subMenulist.itemHeight), font=0, text=entry.encode('utf-8'), flags=align, color=color, color_sel=color))
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
			<widget position="0,10" size="1280,180" source="id_mainmenu_ext" render="Micon" path="gmenu/" alphatest="on" zPosition="2" transparent="1" />

			<widget position="122,190" size="35,10" name="up_sub_0" pixmap="gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="372,190" size="35,10" name="up_sub_1" pixmap="gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="622,190" size="35,10" name="up_sub_2" pixmap="gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="872,190" size="35,10" name="up_sub_3" pixmap="gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>
			<widget position="1122,190" size="35,10" name="up_sub_4" pixmap="gmenu/gmenu_up.png" alphatest="on" zPosition="2"/>

			<widget position="15,200" size="250,300" name="list_sub_0" transparent="1" enableWrapAround="1"/>
			<widget position="265,200" size="250,300" name="list_sub_1" transparent="1" enableWrapAround="1"/>
			<widget position="515,200" size="250,300" name="list_sub_2" transparent="1" enableWrapAround="1"/>
			<widget position="765,200" size="250,300" name="list_sub_3" transparent="1" enableWrapAround="1"/>
			<widget position="1015,200" size="250,300" name="list_sub_4" transparent="1" enableWrapAround="1"/>

			<widget position="122,500" size="35,10" name="down_sub_0" pixmap="gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="372,500" size="35,10" name="down_sub_1" pixmap="gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="622,500" size="35,10" name="down_sub_2" pixmap="gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="872,500" size="35,10" name="down_sub_3" pixmap="gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
			<widget position="1122,500" size="35,10" name="down_sub_4" pixmap="gmenu/gmenu_down.png" alphatest="on" zPosition="2"/>
		</screen>'''

	ALLOW_SUSPEND = True

	COLUMNS = 5
	ROWS = 6

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.thread = None
		self.selectedColumn = 2
		self.selectedColumnID = 'id_mainmenu_tv'

		# Hardcoded to 5 columns
		self.columns = [
			(_('Plugins'), 'id_mainmenu_plugins'),
			(_('Media'), 'id_mainmenu_media'),
			(_('Channels'), 'id_mainmenu_tv'),
			(_('Internet'), 'id_mainmenu_internet'),
			(_('Tasks'), 'id_mainmenu_tasks'),
		]
		self.mainmenu_ext = {
			'id_mainmenu_plugins': 'gmenu_plugin',
			'id_mainmenu_media': 'gmenu_media',
			'id_mainmenu_tv': 'gmenu_tv',
			'id_mainmenu_internet': 'gmenu_internet',
			'id_mainmenu_tasks': 'gmenu_task',
		}

		self.startRow = {}
		self.selectedRow = {}
		for key in [k[1] for k in self.columns]:
			self.startRow[key] = 0
			self.selectedRow[key] = 0

		self.subentrys = self.getSubEntrys()
		self['id_mainmenu_ext'] = StaticText()
		for i in range(self.COLUMNS):
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

		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onShow.append(self.__onShow)

	def __onFirstExecBegin(self):
		self.buildGeneralMenu()

	def __onShow(self):
		self.buildGeneralMenu()

	def left(self):
		selectedRow = self.selectedRow[self.selectedColumnID]
		self.selectedColumn = (self.selectedColumn - 1) % self.COLUMNS
		self.selectedColumnID = self.columns[self.selectedColumn][1]
		if selectedRow > len(self.subentrys[self.selectedColumnID]) - 1:
			self.selectedRow[self.selectedColumnID] = len(self.subentrys[self.selectedColumnID]) - 1
		else:
			self.selectedRow[self.selectedColumnID] = selectedRow
		if self.selectedRow[self.selectedColumnID] > (self.ROWS - 1):
			self.startRow[self.selectedColumnID] = self.selectedRow[self.selectedColumnID] - (self.ROWS - 1)
		else:
			self.startRow[self.selectedColumnID] = 0
		self.buildGeneralMenu()

	def right(self):
		selectedRow = self.selectedRow[self.selectedColumnID]
		self.selectedColumn = (self.selectedColumn + 1) % self.COLUMNS
		self.selectedColumnID = self.columns[self.selectedColumn][1]
		if selectedRow > len(self.subentrys[self.selectedColumnID]) - 1:
			self.selectedRow[self.selectedColumnID] = len(self.subentrys[self.selectedColumnID]) - 1
		else:
			self.selectedRow[self.selectedColumnID] = selectedRow
		if self.selectedRow[self.selectedColumnID] > (self.ROWS - 1):
			self.startRow[self.selectedColumnID] = self.selectedRow[self.selectedColumnID] - (self.ROWS - 1)
		else:
			self.startRow[self.selectedColumnID] = 0
		self.buildGeneralMenu()

	def up(self):
		self.selectedRow[self.selectedColumnID] = (self.selectedRow[self.selectedColumnID] - 1) % len(self.subentrys[self.selectedColumnID])
		if self.selectedRow[self.selectedColumnID] > (self.ROWS - 1):
			self.startRow[self.selectedColumnID] = self.selectedRow[self.selectedColumnID] - (self.ROWS - 1)
		else:
			self.startRow[self.selectedColumnID] = 0
		self.buildGeneralMenu()

	def down(self):
		self.selectedRow[self.selectedColumnID] = (self.selectedRow[self.selectedColumnID] + 1) % len(self.subentrys[self.selectedColumnID])
		if self.selectedRow[self.selectedColumnID] > (self.ROWS - 1):
			self.startRow[self.selectedColumnID] = self.selectedRow[self.selectedColumnID] - (self.ROWS - 1)
		else:
			self.startRow[self.selectedColumnID] = 0
		self.buildGeneralMenu()

	def keyOK(self):
		selectedRow = self.selectedRow[self.selectedColumnID]
		if selectedRow < len(self.subentrys[self.selectedColumnID]):
			self.subentrys[self.selectedColumnID][selectedRow][2]()

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
		extlist = []
		columns = []
		self.selectedColumnID = self.columns[self.selectedColumn][1]
		selectedRow = self.selectedRow[self.selectedColumnID]
		for count, x in enumerate(self.columns):
			columns.append(x[0])
			sublist = []

			widgetPos = str(count)
			sublistWidget = 'list_sub_' + widgetPos
			upWidget = 'up_sub_' + widgetPos
			downWidget = 'down_sub_' + widgetPos

			for subcount, y in enumerate(self.subentrys[x[1]]):
				if subcount >= self.startRow[x[1]] and subcount < self.startRow[x[1]] + self.ROWS:
					if count == self.selectedColumn:
						sublist.append(GeneralSubMenuEntryComponent(y[0], self[sublistWidget], enableEntry=True, selectedEntry=selectedRow == subcount))
						# self[sublistWidget].show() ## for show only current sublist
					else:
						sublist.append(GeneralSubMenuEntryComponent(y[0], self[sublistWidget], enableEntry=False, selectedEntry=False))
						# self[sublistWidget].hide() ## for show only current sublist

			self[sublistWidget].setList(sublist)

			if count == self.selectedColumn and selectedRow > -1 and len(sublist) > 0:
				self[sublistWidget].selectionEnabled(1)
				self[sublistWidget].moveToIndex(selectedRow - self.startRow[x[1]])
			else:
				self[sublistWidget].selectionEnabled(0)
			if self.startRow[x[1]] > 0:
				self[upWidget].show()
			else:
				self[upWidget].hide()
			if len(self.subentrys[x[1]]) > self.ROWS and self.selectedRow[x[1]] != len(self.subentrys[x[1]]) - 1:
				self[downWidget].show()
			else:
				self[downWidget].hide()

		self['id_mainmenu_ext'].setText(self.mainmenu_ext[self.selectedColumnID])
		self.summaries.setTextTitle(self.columns[self.selectedColumn][0])
		if selectedRow < len(self.subentrys[self.selectedColumnID]):
			self.summaries.setTextMenu(self.subentrys[self.selectedColumnID][selectedRow][0])
		else:
			self.summaries.setTextMenu('')

	def getSubEntrys(self):
		return {
			'id_mainmenu_plugins': self.getSubEntry(None, [
				(_('Plugins'), 'mainmenu_plugins_browser', boundFunction(self.openDialog, PluginBrowser), -10),
			]),

			'id_mainmenu_media': self.getSubEntry('mainmenu', [
				(_('Recordings'), 'mainmenu_tv_recorded', boundFunction(self.openRecordings), 0),
				(_('Music'), 'mainmenu_music', boundFunction(self.openMediaPlayer), 1),
				(_('Photos'), 'mainmenu_photos', boundFunction(self.openPicturePlayer), 2),
			]),

			'id_mainmenu_tv': self.getSubEntry('id_mainmenu_tv', [
				(_('Channels'), 'mainmenu_tv_channels', boundFunction(self.openChannelSelection), 0),
				(_('Program Guide'), 'mainmenu_tv_timer', boundFunction(self.openProgramGuide), 10),
				(_('History'), 'mainmenu_tv_zaphistory', boundFunction(self.openHistoryChannelSelection), 50),
				(_('Timers'), 'mainmenu_tv_timer', boundFunction(self.openDialog, TimerEditList), 60),
			]),

			'id_mainmenu_internet': self.getSubEntry('id_mainmenu_music', self.getSubEntry('id_mainmenu_photos', self.getSubEntry('id_mainmenu_movies', [
				(_('Flickr'), 'mainmenu_photos_playlists', boundFunction(self.openFlickr), 60),
			]))),

			'id_mainmenu_tasks': self.getSubEntry('id_mainmenu_tasks', [
				(_('Setup'), 'mainmenu_tasks_setup', boundFunction(self.openGeneralSetup), 0),
				(_('Sources / Files'), 'mainmenu_tasks_filemanager', boundFunction(self.openFileManager), 10),
				(_('Power'), 'mainmenu_tasks_power', boundFunction(self.openMenuID, 'shutdown', _('Power')), 20),
				(_('Information'), 'mainmenu_tasks_info', boundFunction(self.openMenuID, 'information', _('Information')), 30),
			]),
		}

	def openGeneralSetup(self):
		from Screens.GeneralSetup import GeneralSetup
		self.session.open(GeneralSetup)

	def notReadyMessage(self):
		self.session.open(MessageBox, _('This part is not ready yet!'), MessageBox.TYPE_INFO)

	def doNothingAtAll(self):
		pass

	def openFileManager(self, path=None):
		self.session.open(FileCommanderScreen, path)

	# tv
	def openChannelSelection(self):
		self.hide()
		if InfoBar.instance.servicelist is None:
			InfoBar.instance.servicelist = InfoBar.instance.session.instantiateDialog(ChannelSelection)
		InfoBar.instance.showTv()
		self.close(1)

	def openHistoryChannelSelection(self):
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
		# InfoBar.instance.openMultiServiceEPG()
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
		from Plugins.Extensions.PicturePlayer.ui import picshow
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
					_("Media Player"),
					_("Picture player"),
					_("YouTube TV Settings")]:
					print "Skip plugin =>", l.name
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
					_("Media Player"),
					_("Picture player"),
					_("YouTube TV Settings")]:
					print "Skip menu =>", l[0]
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
