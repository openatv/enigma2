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

gmenu_extentrys = {}
gmenu_extentrys['id_mainmenu_plugins'] = []
gmenu_extentrys['id_mainmenu_photos'] = []
gmenu_extentrys['id_mainmenu_music'] = []
gmenu_extentrys['id_mainmenu_tv'] = []
gmenu_extentrys['id_mainmenu_movies'] = []
gmenu_extentrys['id_mainmenu_source'] = []
gmenu_extentrys['id_mainmenu_tasks'] = []

config.gmenu = ConfigSubsection()
config.gmenu.ext_sel_id_mainmenu_plugins = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_photos = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_music = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_tv = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_movies = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_source = ConfigNumber(default=-1)
config.gmenu.ext_sel_id_mainmenu_tasks = ConfigNumber(default=-1)


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
	x = 15
	count = 0
	width = 250
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
	for entry in entrys:
		if count == 0 and onLeft:
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_of_left))
		elif count == 4 and onRight:
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_of_right))
		else:
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_of))
		x += width
		count += 1

	x = 15
	count = 0
	for entry in entrys:
		real_width = 100
		if selectedEntry == count and enableEntry == -1:
			if count == 0 and onLeft:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_on_left))
			elif count == 4 and onRight:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_on_right))
			else:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_on))
			if width > real_width:
				res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=16777215, color_sel=16777215))
			else:
				res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=16777215, color_sel=16777215))
		elif selectedEntry == count and enableEntry != -1:
			if count == 0 and onLeft:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_en_left))
			elif count == 4 and onRight:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_en_right))
			else:
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x - 15, 0), size=(width + 30, 76), png=entry_en))
			if width > real_width:
				res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=14540253, color_sel=14540253))
			else:
				res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=14540253, color_sel=14540253))
		elif width > real_width:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=7829367, color_sel=7829367))
		else:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 76), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=7829367, color_sel=7829367))
		x += width
		count += 1
	return res


class GeneralSubMenuList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont('Regular', 22))
		self.l.setItemHeight(50)

def GeneralSubMenuEntryComponent(entry, enableEntry=False, selectedEntry=False, onUp=False, onDown=False):
	x = 0
	width = 250
	res = [entry]
	entry_sl = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'gmenu/gmenu_250x50_on.png'))
	real_width = 100
	if selectedEntry:
		res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 50), png=entry_sl))
		if width > real_width:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=16777215))
		else:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=16777215))
	elif enableEntry:
		if width > real_width:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=10066329))
		else:
			res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=10066329))
	elif width > real_width:
		res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER, color=5592405))
	else:
		res.append(MultiContentEntryText(pos=(x + 15, 0), size=(width - 30, 50), font=0, text=entry.encode('utf-8'), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, color=5592405))
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
			<widget name="frame" position="12,95" size="170,220" zPosition="1" alphatest="on" />

			<widget position="40,25" size="1200,25" name="title" font="Regular;22"  zPosition="2" transparent="1" foregroundColors="#555555,#999999" />

			<widget position="22,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_0" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="200,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_1" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="378,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_2" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="556,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_3" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="734,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_4" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="912,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_5" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />
			<widget position="1090,20" size="150,150" source="id_mainmenu_plugins_tumb_ext_6" render="Micon" pixmap="easy-skin-hd/gmenu/gmenu_plugin_bg.png" alphatest="on" zPosition="2" transparent="1" />

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

		self.pos = {}
		self.pos['id_mainmenu_plugins'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.pos['id_mainmenu_photos'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.pos['id_mainmenu_music'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.pos['id_mainmenu_tv'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.pos['id_mainmenu_movies'] = [
			(12, 95),
			(190, 95),
			(368, 95),
			(546, 95),
			(724, 95),
			(902, 95),
			(1080, 95),
		]

		self.pos['id_mainmenu_source'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.pos['id_mainmenu_tasks'] = [
			(12, 120),
			(190, 120),
			(368, 120),
			(546, 120),
			(724, 120),
			(902, 120),
			(1080, 120),
		]

		self.startSubEntry = {}
		self.selectedSubEntry = {}
		self.selectedExtEntry = {}
		for key in self.pos.keys():
			self.startSubEntry[key] = 0
			self.selectedSubEntry[key] = -1
			self.selectedExtEntry[key] = eval('config.gmenu.ext_sel_%s' % key).value
			if self.selectedExtEntry[key] == -1:
				self.selectedExtEntry[key] = 0

		self.subentrys = self.getSubEntrys()
		self['title'] = MultiColorLabel()
		self.exttitle = {}
		self.exttitle['id_mainmenu_plugins'] = ''
		self.exttitle['id_mainmenu_photos'] = ''
		self.exttitle['id_mainmenu_music'] = ''
		self.exttitle['id_mainmenu_tv'] = ''
		self.exttitle['id_mainmenu_movies'] = ''
		self.exttitle['id_mainmenu_source'] = ''
		self.exttitle['id_mainmenu_tasks'] = ''
		self.extframe = {}
		self.extframe['id_mainmenu_plugins'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_plugin_sl.png'))
		self.extframe['id_mainmenu_photos'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_photo_sl.png'))
		self.extframe['id_mainmenu_music'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_music_sl.png'))
		self.extframe['id_mainmenu_tv'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_tv_sl.png'))
		self.extframe['id_mainmenu_movies'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_movie_sl.png'))
		self.extframe['id_mainmenu_source'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_source_sl.png'))
		self.extframe['id_mainmenu_tasks'] = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, 'easy-skin-hd/gmenu/gmenu_task_sl.png'))
		self.mainmenu_ext = {}
		self.mainmenu_ext['id_mainmenu_plugins'] = 'gmenu_plugin'
		self.mainmenu_ext['id_mainmenu_photos'] = 'gmenu_photo'
		self.mainmenu_ext['id_mainmenu_music'] = 'gmenu_music'
		self.mainmenu_ext['id_mainmenu_tv'] = 'gmenu_tv'
		self.mainmenu_ext['id_mainmenu_movies'] = 'gmenu_movie'
		self.mainmenu_ext['id_mainmenu_source'] = 'gmenu_source'
		self.mainmenu_ext['id_mainmenu_tasks'] = 'gmenu_task'
		self['id_mainmenu_ext'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_0'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_1'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_2'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_3'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_4'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_5'] = StaticText()
		self['id_mainmenu_plugins_tumb_ext_6'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_0'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_1'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_2'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_3'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_4'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_5'] = StaticText()
		self['id_mainmenu_photos_tumb_ext_6'] = StaticText()
		self['id_mainmenu_music_tumb_ext_0'] = StaticText()
		self['id_mainmenu_music_tumb_ext_1'] = StaticText()
		self['id_mainmenu_music_tumb_ext_2'] = StaticText()
		self['id_mainmenu_music_tumb_ext_3'] = StaticText()
		self['id_mainmenu_music_tumb_ext_4'] = StaticText()
		self['id_mainmenu_music_tumb_ext_5'] = StaticText()
		self['id_mainmenu_music_tumb_ext_6'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_0'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_1'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_2'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_3'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_4'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_5'] = StaticText()
		self['id_mainmenu_tv_tumb_ext_6'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_0'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_1'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_2'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_3'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_4'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_5'] = StaticText()
		self['id_mainmenu_movies_tumb_ext_6'] = StaticText()
		self['id_mainmenu_source_tumb_ext_0'] = StaticText()
		self['id_mainmenu_source_tumb_ext_1'] = StaticText()
		self['id_mainmenu_source_tumb_ext_2'] = StaticText()
		self['id_mainmenu_source_tumb_ext_3'] = StaticText()
		self['id_mainmenu_source_tumb_ext_4'] = StaticText()
		self['id_mainmenu_source_tumb_ext_5'] = StaticText()
		self['id_mainmenu_source_tumb_ext_6'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_0'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_1'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_2'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_3'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_4'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_5'] = StaticText()
		self['id_mainmenu_tasks_tumb_ext_6'] = StaticText()
		self['list'] = GeneralMenuList([])
		self['list_sub_0'] = GeneralSubMenuList([])
		self['list_sub_1'] = GeneralSubMenuList([])
		self['list_sub_2'] = GeneralSubMenuList([])
		self['list_sub_3'] = GeneralSubMenuList([])
		self['list_sub_4'] = GeneralSubMenuList([])
		self['up_sub_0'] = Pixmap()
		self['up_sub_1'] = Pixmap()
		self['up_sub_2'] = Pixmap()
		self['up_sub_3'] = Pixmap()
		self['up_sub_4'] = Pixmap()
		self['down_sub_0'] = Pixmap()
		self['down_sub_1'] = Pixmap()
		self['down_sub_2'] = Pixmap()
		self['down_sub_3'] = Pixmap()
		self['down_sub_4'] = Pixmap()
		self['up_sub_0'].hide()
		self['up_sub_1'].hide()
		self['up_sub_2'].hide()
		self['up_sub_3'].hide()
		self['up_sub_4'].hide()
		self['down_sub_0'].hide()
		self['down_sub_1'].hide()
		self['down_sub_2'].hide()
		self['down_sub_3'].hide()
		self['down_sub_4'].hide()
		self['frame'] = MovingPixmap()
		self['frame'].hide()

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
		self.fillExtEntry(self.selectedEntryID)

	def __onShow(self):
		print "__onShow"
		self.buildGeneralMenu()
		self.fillExtEntry(self.selectedEntryID)

	def fillExtEntry(self, menuID):
		extentrys = gmenu_extentrys[menuID]
		countitems = 0
		for extentry in extentrys:
			self[menuID + '_tumb_ext_' + str(countitems)].setText(str(extentry[1]))
			countitems += 1

		for x in range(7 - len(extentrys)):
			self[menuID + '_tumb_ext_' + str(countitems + x)].setText(None)

		gmenu_extentrys[menuID] = self.getExtEntry(menuID)
		if eval('config.gmenu.ext_sel_%s' % menuID).value == -1 and len(gmenu_extentrys[menuID]) > 0:
			self.selectedExtEntry[menuID] = len(gmenu_extentrys[menuID]) // 2
			eval('config.gmenu.ext_sel_%s' % menuID).value = self.selectedExtEntry[menuID]
		if self.selectedExtEntry[menuID] > len(gmenu_extentrys[menuID]) - 1:
			self.selectedExtEntry[menuID] = len(gmenu_extentrys[menuID]) - 1
			eval('config.gmenu.ext_sel_%s' % menuID).value = self.selectedExtEntry[menuID]
		pos = self.pos[menuID][self.selectedExtEntry[menuID]]
		self['frame'].instance.setPixmap(self.extframe[menuID])
		self['frame'].moveTo(pos[0], pos[1], 1)
		self['frame'].startMoving()

	def clearExtEntry(self, menuID):
		for x in range(7):
			self[menuID + '_tumb_ext_' + str(x)].setText(None)

	def getExtEntry(self, menuID):
		self.subentrys = self.getSubEntrys()
		ret_list = []
		if menuID == 'id_mainmenu_plugins2':
			wight = 100
			countitems = 0
			for x in self.subentrys['id_mainmenu_plugins']:
				if countitems == 7:
					break
				ret_list.append((x[0], x[1], x[2], x[3]))
				if self.selectedEntryID == menuID:
					picon = str(x[1]).replace('.png', '_g.png')
					if self[menuID + '_tumb_ext_' + str(countitems)].getText() != picon:
						self[menuID + '_tumb_ext_' + str(countitems)].setText(picon)
				else:
					self[menuID + '_tumb_ext_' + str(countitems)].setText(None)
				countitems += 1
				wight += 1

		elif menuID == 'id_mainmenu_tasks2':
			wight = 100
			countitems = 0
			for x in self.subentrys['id_mainmenu_tasks']:
				if countitems == 7:
					break
				ret_list.append((x[0], x[1], x[2], x[3]))
				if self.selectedEntryID == menuID:
					picon = str(x[1])
					if self[menuID + '_tumb_ext_' + str(countitems)].getText() != picon:
						self[menuID + '_tumb_ext_' + str(countitems)].setText(picon)
				else:
					self[menuID + '_tumb_ext_' + str(countitems)].setText(None)
				countitems += 1
				wight += 1

		return ret_list

	def left(self):
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		#print "ID---------------------------------"
		#print self.selectedEntryID
		#print "ID---------------------------------"
		if selectedSubEntry == -2:
			if len(gmenu_extentrys[self.selectedEntryID]) > 0:
				self.selectedExtEntry[self.selectedEntryID] -= 1
				if self.selectedExtEntry[self.selectedEntryID] < 0:
					self.selectedExtEntry[self.selectedEntryID] = min(6, len(gmenu_extentrys[self.selectedEntryID]) - 1)
					if self.selectedExtEntry[self.selectedEntryID] == -1:
						self.selectedExtEntry[self.selectedEntryID] = 0
			else:
				self.selectedExtEntry[self.selectedEntryID] = 0
				self.selectedSubEntry[self.selectedEntryID] = -1
			eval('config.gmenu.ext_sel_%s' % self.selectedEntryID).value = self.selectedExtEntry[self.selectedEntryID]
			self.buildGeneralMenu()
			return
		self.selectedEntry -= 1
		if self.selectedEntry == -1:
			self.selectedEntry = 0
			self.startEntry = 0
			return
		oldSelectedEntryID = self.selectedEntryID
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
		self.clearExtEntry(oldSelectedEntryID)
		self.fillExtEntry(self.selectedEntryID)

	def right(self):
		selectedSubEntry = self.selectedSubEntry[self.selectedEntryID]
		#print "ID---------------------------------"
		#print self.selectedEntryID
		#print "ID---------------------------------"
		if selectedSubEntry == -2:
			if len(gmenu_extentrys[self.selectedEntryID]) > 0:
				self.selectedExtEntry[self.selectedEntryID] += 1
				if self.selectedExtEntry[self.selectedEntryID] > 6 or self.selectedExtEntry[self.selectedEntryID] == len(gmenu_extentrys[self.selectedEntryID]):
					self.selectedExtEntry[self.selectedEntryID] = 0
			else:
				self.selectedExtEntry[self.selectedEntryID] = 0
				self.selectedSubEntry[self.selectedEntryID] = -1
			eval('config.gmenu.ext_sel_%s' % self.selectedEntryID).value = self.selectedExtEntry[self.selectedEntryID]
			self.buildGeneralMenu()
			return
		self.selectedEntry += 1
		if self.selectedEntry == len(self.entrys):
			self.selectedEntry = len(self.entrys) - 1
			self.startEntry = 2
			return
		oldSelectedEntryID = self.selectedEntryID
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
		self.clearExtEntry(oldSelectedEntryID)
		self.fillExtEntry(self.selectedEntryID)

	def up(self):
		self.selectedSubEntry[self.selectedEntryID] -= 1
		if self.selectedSubEntry[self.selectedEntryID] == -2 and len(gmenu_extentrys[self.selectedEntryID]) == 0:
			self.selectedSubEntry[self.selectedEntryID] = -1
		if self.selectedSubEntry[self.selectedEntryID] == -3:
			self.selectedSubEntry[self.selectedEntryID] = -1
		if self.selectedSubEntry[self.selectedEntryID] > 4:
			self.startSubEntry[self.selectedEntryID] = self.selectedSubEntry[self.selectedEntryID] - 4
		else:
			self.startSubEntry[self.selectedEntryID] = 0
		self.buildGeneralMenu()

	def down(self):
		self.selectedSubEntry[self.selectedEntryID] += 1
		if self.selectedSubEntry[self.selectedEntryID] == len(self.subentrys[self.selectedEntryID]):
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
		if selectedSubEntry == -2:
			index = self.selectedExtEntry[self.selectedEntryID]
			if index != -1 and index < len(gmenu_extentrys[self.selectedEntryID]):
				gmenu_extentrys[self.selectedEntryID][index][2]()

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
		self.exttitle['id_mainmenu_plugins'] = ''
		self.exttitle['id_mainmenu_photos'] = ''
		self.exttitle['id_mainmenu_music'] = ''
		self.exttitle['id_mainmenu_tv'] = ''
		self.exttitle['id_mainmenu_movies'] = ''
		self.exttitle['id_mainmenu_source'] = ''
		self.exttitle['id_mainmenu_tasks'] = ''
		if selectedSubEntry == -2:
			countitem = self.selectedExtEntry[self.selectedEntryID]
			if countitem is None or countitem == -1:
				self['frame'].hide()
				self['title'].setForegroundColorNum(1)
			else:
				pos = self.pos[self.selectedEntryID][countitem]
				self['frame'].instance.setPixmap(self.extframe[self.selectedEntryID])
				self['frame'].moveTo(pos[0], pos[1], 1)
				self['frame'].startMoving()
				self['frame'].show()
				self['title'].setForegroundColorNum(1)
				try:
					selstr = str(gmenu_extentrys[self.selectedEntryID][countitem][0])
				except:
					selstr = ''
				self.exttitle[self.selectedEntryID] += ' >> ' + selstr
		else:
			countitem = self.selectedExtEntry[self.selectedEntryID]
			if countitem is None or countitem == -1:
				self['frame'].hide()
				self['title'].setForegroundColorNum(0)
			else:
				pos = self.pos[self.selectedEntryID][countitem]
				self['frame'].hide()
				self['frame'].instance.setPixmap(self.extframe[self.selectedEntryID])
				self['frame'].moveTo(pos[0], pos[1], 1)
				self['frame'].startMoving()
				self['title'].setForegroundColorNum(0)
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
		elif selectedSubEntry == -2:
			self['list'].selectionEnabled(0)
			self.summaries.setTextTitle(self.entrys[self.selectedEntry][0])
			countitem = self.selectedExtEntry[self.selectedEntryID]
			if countitem is not None and countitem != -1 and countitem < len(gmenu_extentrys[self.selectedEntryID]):
				self.summaries.setTextMenu(gmenu_extentrys[self.selectedEntryID][countitem][0])
			else:
				self.summaries.setTextMenu('')
		else:
			self.summaries.setTextTitle('')
			self.summaries.setTextMenu('')
		self['title'].setText(self.exttitle[self.selectedEntryID])

	def getSubEntrys(self):
		subentrys = {}
		subentrys['id_mainmenu_plugins'] = self.getSubEntry(None, [])

		subentrys['id_mainmenu_photos'] = self.getSubEntry('id_mainmenu_photos', [
			#(_('Albums'),'mainmenu_photos_albums',boundFunction(self.openPicturePlayerAlbum),30),
			#(_('Slideshow'),'mainmenu_photos_playlists',boundFunction(self.openPicturePlayerSlideshow), 40),
			#(_('Thumbnails'),'mainmenu_photos_bouquets',boundFunction(self.openPicturePlayerThumb),50),
			(_('Flickr'), 'mainmenu_photos_playlists', boundFunction(self.openFlickr), 60),
			#(_('Setup'), 'mainmenu_tasks_setup', boundFunction(self.openPicturePlayerSetup), 100),
		])

		subentrys['id_mainmenu_music'] = self.getSubEntry('id_mainmenu_music', [])

		subentrys['id_mainmenu_tv'] = self.getSubEntry('id_mainmenu_tv', [
			(_('History'), 'mainmenu_tv_zaphistory', boundFunction(self.openHisotryChannelSelection), 50),
			(_('Timers'), 'mainmenu_tv_timer', boundFunction(self.openDialog, TimerEditList), 60),
			(_('Program Guide'), 'mainmenu_tv_timer', boundFunction(self.openProgramGuide), 70),
		])

		subentrys['id_mainmenu_movies'] = self.getSubEntry('id_mainmenu_movies', [
			(_('Recordings'), 'mainmenu_tv_recorded', boundFunction(self.openRecordings), 50),
		])

		subentrys['id_mainmenu_source'] = self.getSubEntry('id_mainmenu_source', self.getScart(None, []))

		subentrys['id_mainmenu_tasks'] = self.getSubEntry('id_mainmenu_tasks', [
			(_('Power'), 'mainmenu_tasks_power', boundFunction(self.openMenuID, 'shutdown', _('Power')), 20),
			(_('Information'), 'mainmenu_tasks_info', boundFunction(self.openMenuID, 'id_mainmenu_tasks_info', _('Information')), 30),
			#(_('Setup'), 'mainmenu_tasks_setup', boundFunction(self.openGeneralSetup), 30)
		])
		return subentrys

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
