# -*- coding: utf-8 -*-

#This plugin is free software, you are allowed to
#modify it (if you keep the license),
#but you are not allowed to distribute/publish
#it without source code (this version and your modifications).
#This means you also have to distribute
#source code of your modifications.

from __future__ import print_function
from enigma import eTimer
from Components.ActionMap import ActionMap
from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigSelection, ConfigYesNo, NoSave, ConfigNothing, ConfigNumber
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.SkinSelector import SkinSelector
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop
from Tools.Directories import *
from Tools.LoadPixmap import LoadPixmap
from Tools.WeatherID import get_woeid_from_yahoo
import Tools.Notifications
from os import listdir, remove, rename, system, path, symlink, chdir, makedirs, mkdir
import shutil

cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')

# Atile
config.plugins.AtileHD = ConfigSubsection()
config.plugins.AtileHD.refreshInterval = ConfigNumber(default=10)
config.plugins.AtileHD.woeid = ConfigNumber(default=638242)
config.plugins.AtileHD.tempUnit = ConfigSelection(default="Celsius", choices=[
				("Celsius", _("Celsius")),
				("Fahrenheit", _("Fahrenheit"))
				])


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("%s Setup") % cur_skin, description=_("Personalize your Skin"), where=PluginDescriptor.WHERE_MENU, icon="plugin.png", fnc=menu)]


def menu(menuid, **kwargs):
	exclude = ["MetrixHD/skin.MySkin.xml", "MetrixHD/skin.xml", "SevenHD/skin.xml", "KravenVB/skin.xml", "OverlayHD/skin.xml"]
	if menuid == "system" and config.skin.primary_skin.value not in exclude:
		return [(_("Setup - %s") % cur_skin, main, "atilehd_setup", None)]
	else:
		pass
	return []


def main(session, **kwargs):
	print("[%s]: Config ..." % cur_skin)
	session.open(AtileHD_Config)


def isInteger(s):
	try:
		int(s)
		return True
	except ValueError:
		return False


class WeatherLocationChoiceList(Screen):
	skin = """
		<screen name="WeatherLocationChoiceList" position="center,center" size="1280,720" title="Location list" >
			<widget source="Title" render="Label" position="70,47" size="950,43" font="Regular;35" transparent="1" />
			<widget name="choicelist" position="70,115" size="700,480" scrollbarMode="showOnDemand" scrollbarWidth="6" transparent="1" />
			<eLabel position=" 55,675" size="290, 5" zPosition="-10" backgroundColor="red" />
			<eLabel position="350,675" size="290, 5" zPosition="-10" backgroundColor="green" />
			<eLabel position="645,675" size="290, 5" zPosition="-10" backgroundColor="yellow" />
			<eLabel position="940,675" size="290, 5" zPosition="-10" backgroundColor="blue" />
			<widget name="key_red" position="70,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
			<widget name="key_green" position="365,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
		</screen>
		"""

	def __init__(self, session, location_list):
		self.location_list = location_list
		list = []
		Screen.__init__(self, session)
		self.title = _("Location list")
		self["choicelist"] = MenuList(list)
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["myActionMap"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"ok": self.keyOk,
			"green": self.keyOk,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
		}, -1)
		self.createChoiceList()

	def createChoiceList(self):
		list = []
		print(self.location_list)
		for x in self.location_list:
			list.append((str(x[1]), str(x[0])))
		self["choicelist"].l.setList(list)

	def keyOk(self):
		returnValue = self["choicelist"].l.getCurrentSelection()[1]
		if returnValue is not None:
			self.close(returnValue)
		else:
			self.keyCancel()

	def keyCancel(self):
		self.close(None)


class AtileHD_Config(Screen, ConfigListScreen):

	skin = """
		<screen name="AtileHD_Config" position="center,center" size="1280,720" title="AtileHD Setup" >
			<widget source="Title" render="Label" position="70,47" size="950,43" font="Regular;35" transparent="1" />
			<widget name="config" position="70,115" size="700,480" scrollbarMode="showOnDemand" scrollbarWidth="6" transparent="1" />
			<widget name="Picture" position="808,342" size="400,225" alphatest="on" />
			<eLabel position=" 55,675" size="290, 5" zPosition="-10" backgroundColor="red" />
			<eLabel position="350,675" size="290, 5" zPosition="-10" backgroundColor="green" />
			<eLabel position="645,675" size="290, 5" zPosition="-10" backgroundColor="yellow" />
			<eLabel position="940,675" size="290, 5" zPosition="-10" backgroundColor="blue" />
			<widget name="key_red" position="70,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
			<widget name="key_green" position="365,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
			<widget name="key_yellow" position="660,635" size="260,25" zPosition="1" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
			<widget name="key_blue" position="955,635" size="260,25" zPosition="0" font="Regular;20" halign="left" foregroundColor="foreground" transparent="1" />
		</screen>
	"""

	def __init__(self, session, args=0):
		self.skin_lines = []
		self.changed_screens = False
		Screen.__init__(self, session)

		self.start_skin = config.skin.primary_skin.value

		if self.start_skin != "skin.xml":
			self.getInitConfig()

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))
		self["key_yellow"] = Label()
		self["key_blue"] = Label(_("About"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"green": self.keyGreen,
				"red": self.cancel,
				"yellow": self.keyYellow,
				"blue": self.about,
				"cancel": self.cancel,
				"ok": self.keyOk,
				"menu": self.setWeather,
			}, -2)

		self["Picture"] = Pixmap()

		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)

		if self.start_skin == "skin.xml":
			self.onLayoutFinish.append(self.openSkinSelectorDelayed)
		else:
			self.createConfigList()

	def setWeather(self):
		try:
			from Plugins.Extensions.WeatherPlugin.setup import MSNWeatherPluginEntriesListConfigScreen
			self.session.open(MSNWeatherPluginEntriesListConfigScreen)
		except:
			self.session.open(MessageBox, _("'WeatherPlugin' is not installed!"), MessageBox.TYPE_INFO)

	def getInitConfig(self):
		global cur_skin
		self.is_atile = False
		if cur_skin == 'AtileHD':
			self.is_atile = True
		self.title = _("%s - Setup") % cur_skin
		self.skin_base_dir = "/usr/share/enigma2/%s/" % cur_skin
		if self.is_atile:
			self.default_font_file = "font_atile_Roboto.xml"
			self.default_color_file = "colors_atile_Grey_transparent.xml"
		else:
			self.default_font_file = "font_Original.xml"
			self.default_color_file = "colors_Original.xml"

		self.default_background_file = "background_Original.xml"
		self.default_sb_file = "sb_Original.xml"
		self.default_infobar_file = "infobar_Original.xml"
		self.default_sib_file = "sib_Original.xml"
		self.default_ch_se_file = "ch_se_Original.xml"
		self.default_ev_file = "ev_Original.xml"
		self.default_clock_file = "clock_Original.xml"
		self.default_ul_file = "ul_Original.xml"

		self.color_file = "skin_user_colors.xml"
		self.font_file = "skin_user_header.xml"
		self.background_file = "skin_user_background.xml"
		self.sb_file = "skin_user_sb.xml"
		self.infobar_file = "skin_user_infobar.xml"
		self.sib_file = "skin_user_sib.xml"
		self.ch_se_file = "skin_user_ch_se.xml"
		self.ev_file = "skin_user_ev.xml"
		self.clock_file = "skin_user_clock.xml"
		self.ul_file = "skin_user_ul.xml"

		# color
		current, choices = self.getSettings(self.default_color_file, self.color_file)
		self.myAtileHD_color = NoSave(ConfigSelection(default=current, choices=choices))
		# font
		current, choices = self.getSettings(self.default_font_file, self.font_file)
		self.myAtileHD_font = NoSave(ConfigSelection(default=current, choices=choices))
		# background
		current, choices = self.getSettings(self.default_background_file, self.background_file)
		self.myAtileHD_background = NoSave(ConfigSelection(default=current, choices=choices))
		# sb
		current, choices = self.getSettings(self.default_sb_file, self.sb_file)
		self.myAtileHD_sb = NoSave(ConfigSelection(default=current, choices=choices))
		# infobar
		current, choices = self.getSettings(self.default_infobar_file, self.infobar_file)
		self.myAtileHD_infobar = NoSave(ConfigSelection(default=current, choices=choices))
		# sib
		current, choices = self.getSettings(self.default_sib_file, self.sib_file)
		self.myAtileHD_sib = NoSave(ConfigSelection(default=current, choices=choices))
		# ch_se
		current, choices = self.getSettings(self.default_ch_se_file, self.ch_se_file)
		self.myAtileHD_ch_se = NoSave(ConfigSelection(default=current, choices=choices))
		# ev
		current, choices = self.getSettings(self.default_ev_file, self.ev_file)
		self.myAtileHD_ev = NoSave(ConfigSelection(default=current, choices=choices))
		# clock
		current, choices = self.getSettings(self.default_clock_file, self.clock_file)
		self.myAtileHD_clock = NoSave(ConfigSelection(default=current, choices=choices))
		# ul
		current, choices = self.getSettings(self.default_ul_file, self.ul_file)
		self.myAtileHD_ul = NoSave(ConfigSelection(default=current, choices=choices))
		# myatile
		myatile_active = self.getmyAtileState()
		self.myAtileHD_active = NoSave(ConfigYesNo(default=myatile_active))
		self.myAtileHD_fake_entry = NoSave(ConfigNothing())

	def getSettings(self, default_file, user_file):
		# default setting
		default = ("default", _("Default"))

		# search typ
		styp = default_file.replace('_Original.xml', '')
		if self.is_atile:
			search_str = '%s_atile_' % styp
		else:
			search_str = '%s_' % styp

		# possible setting
		choices = []
		files = listdir(self.skin_base_dir)
		if path.exists(self.skin_base_dir + 'allScreens/%s/' % styp):
			files += listdir(self.skin_base_dir + 'allScreens/%s/' % styp)
		for f in sorted(files, key=str.lower):
			if f.endswith('.xml') and f.startswith(search_str):
				friendly_name = f.replace(search_str, "").replace(".xml", "").replace("_", " ")
				if path.exists(self.skin_base_dir + 'allScreens/%s/%s' % (styp, f)):
					choices.append((self.skin_base_dir + 'allScreens/%s/%s' % (styp, f), friendly_name))
				else:
					choices.append((self.skin_base_dir + f, friendly_name))
		choices.append(default)

		# current setting
		myfile = self.skin_base_dir + user_file
		current = ''
		if not path.exists(myfile):
			if path.exists(self.skin_base_dir + default_file):
				if path.islink(myfile):
					remove(myfile)
				chdir(self.skin_base_dir)
				symlink(default_file, user_file)
			elif path.exists(self.skin_base_dir + 'allScreens/%s/%s' % (styp, default_file)):
				if path.islink(myfile):
					remove(myfile)
				chdir(self.skin_base_dir)
				symlink(self.skin_base_dir + 'allScreens/%s/%s' % (styp, default_file), user_file)
			else:
				current = None
		if current is None:
			current = default
		else:
			filename = path.realpath(myfile)
			friendly_name = path.basename(filename).replace(search_str, "").replace(".xml", "").replace("_", " ")
			current = (filename, friendly_name)

		return current[0], choices

	def createConfigList(self):
		self.set_color = getConfigListEntry(_("Style:"), self.myAtileHD_color)
		self.set_font = getConfigListEntry(_("Font:"), self.myAtileHD_font)
		self.set_background = getConfigListEntry(_("Background:"), self.myAtileHD_background)
		self.set_sb = getConfigListEntry(_("Background selected:"), self.myAtileHD_sb)
		self.set_infobar = getConfigListEntry("%s:" % _("InfoBar"), self.myAtileHD_infobar)
		self.set_sib = getConfigListEntry("%s:" % _("2nd InfoBar"), self.myAtileHD_sib)
		self.set_ch_se = getConfigListEntry(_("Channel selection:"), self.myAtileHD_ch_se)
		self.set_ev = getConfigListEntry(_("Event view:"), self.myAtileHD_ev)
		self.set_clock = getConfigListEntry(_("Clock:"), self.myAtileHD_clock)
		self.set_ul = getConfigListEntry(_("User logo:"), self.myAtileHD_ul)
		self.set_myatile = getConfigListEntry(_("Enable %s pro:") % cur_skin, self.myAtileHD_active)
		self.set_new_skin = getConfigListEntry(_("Change skin"), ConfigNothing())
		self.find_woeid = getConfigListEntry(_("Search weather location ID"), ConfigNothing())
		self.list = []
		self.list.append(self.set_myatile)
		if len(self.myAtileHD_color.choices) > 1:
			self.list.append(self.set_color)
		if len(self.myAtileHD_font.choices) > 1:
			self.list.append(self.set_font)
		if len(self.myAtileHD_background.choices) > 1:
			self.list.append(self.set_background)
		if len(self.myAtileHD_sb.choices) > 1:
			self.list.append(self.set_sb)
		if len(self.myAtileHD_infobar.choices) > 1:
			self.list.append(self.set_infobar)
		if len(self.myAtileHD_sib.choices) > 1:
			self.list.append(self.set_sib)
		if len(self.myAtileHD_ch_se.choices) > 1:
			self.list.append(self.set_ch_se)
		if len(self.myAtileHD_ev.choices) > 1:
			self.list.append(self.set_ev)
		if len(self.myAtileHD_clock.choices) > 1:
			self.list.append(self.set_clock)
		if len(self.myAtileHD_ul.choices) > 1:
			self.list.append(self.set_ul)
		self.list.append(self.set_new_skin)
		#if not config.skin.primary_skin.value == "iFlatFHD/skin.xml":
		#	self.list.append(getConfigListEntry(_("---Weather---"), self.myAtileHD_fake_entry))
		#	self.list.append(getConfigListEntry(_("Refresh interval in minutes:"), config.plugins.AtileHD.refreshInterval))
		#	self.list.append(getConfigListEntry(_("Temperature unit:"), config.plugins.AtileHD.tempUnit))
		#	self.list.append(self.find_woeid)
		#	self.list.append(getConfigListEntry(_("Location # (http://weather.yahoo.com/):"), config.plugins.AtileHD.woeid))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if self.myAtileHD_active.value:
			self["key_yellow"].setText("%s pro" % cur_skin)
		else:
			self["key_yellow"].setText("")

	def changedEntry(self):
		if self["config"].getCurrent() == self.set_color:
			self.setPicture(self.myAtileHD_color.value)
		elif self["config"].getCurrent() == self.set_font:
			self.setPicture(self.myAtileHD_font.value)
		elif self["config"].getCurrent() == self.set_background:
			self.setPicture(self.myAtileHD_background.value)
		elif self["config"].getCurrent() == self.set_infobar:
			self.setPicture(self.myAtileHD_infobar.value)
		elif self["config"].getCurrent() == self.set_sib:
			self.setPicture(self.myAtileHD_sib.value)
		elif self["config"].getCurrent() == self.set_ch_se:
			self.setPicture(self.myAtileHD_ch_se.value)
		elif self["config"].getCurrent() == self.set_ev:
			self.setPicture(self.myAtileHD_ev.value)
		elif self["config"].getCurrent() == self.set_clock:
			self.setPicture(self.myAtileHD_clock.value)
		elif self["config"].getCurrent() == self.set_ul:
			self.setPicture(self.myAtileHD_ul.value)
		elif self["config"].getCurrent() == self.set_myatile:
			if self.myAtileHD_active.value:
				self["key_yellow"].setText("%s pro" % cur_skin)
			else:
				self["key_yellow"].setText("")

	def selectionChanged(self):
		if self["config"].getCurrent() == self.set_color:
			self.setPicture(self.myAtileHD_color.value)
		elif self["config"].getCurrent() == self.set_font:
			self.setPicture(self.myAtileHD_font.value)
		elif self["config"].getCurrent() == self.set_background:
			self.setPicture(self.myAtileHD_background.value)
		elif self["config"].getCurrent() == self.set_sb:
			self.setPicture(self.myAtileHD_sb.value)
		elif self["config"].getCurrent() == self.set_infobar:
			self.setPicture(self.myAtileHD_infobar.value)
		elif self["config"].getCurrent() == self.set_sib:
			self.setPicture(self.myAtileHD_sib.value)
		elif self["config"].getCurrent() == self.set_ch_se:
			self.setPicture(self.myAtileHD_ch_se.value)
		elif self["config"].getCurrent() == self.set_ev:
			self.setPicture(self.myAtileHD_ev.value)
		elif self["config"].getCurrent() == self.set_clock:
			self.setPicture(self.myAtileHD_clock.value)
		elif self["config"].getCurrent() == self.set_ul:
			self.setPicture(self.myAtileHD_ul.value)
		else:
			self["Picture"].hide()

	def cancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, default=False)
		else:
			for x in self["config"].list:
				x[1].cancel()
			if self.changed_screens:
				self.restartGUI()
			else:
				self.close()

	def cancelConfirm(self, result):
		if result is None or result is False:
			print("[%s]: Cancel confirmed." % cur_skin)
		else:
			print("[%s]: Cancel confirmed. Config changes will be lost." % cur_skin)
			for x in self["config"].list:
				x[1].cancel()
			self.close()

	def getmyAtileState(self):
		chdir(self.skin_base_dir)
		if path.exists("mySkin"):
			return True
		else:
			return False

	def setPicture(self, f):
		pic = f.split('/')[-1].replace(".xml", ".png")
		preview = self.skin_base_dir + "preview/preview_" + pic
		if path.exists(preview):
			self["Picture"].instance.setPixmapFromFile(preview)
			self["Picture"].show()
		else:
			self["Picture"].hide()

	def keyYellow(self):
		if self.myAtileHD_active.value:
			self.session.openWithCallback(self.AtileHDScreenCB, AtileHDScreens)
		else:
			self["config"].setCurrentIndex(0)

	def keyOk(self):
		sel = self["config"].getCurrent()
		if sel is not None and sel == self.set_new_skin:
			self.openSkinSelector()
		elif sel is not None and sel == self.find_woeid:
			self.session.openWithCallback(self.search_weather_id_callback, InputBox, title=_("Please enter search string for your location"), text="")
		else:
			self.keyGreen()

	def openSkinSelector(self):
		self.session.openWithCallback(self.skinChanged, SkinSelector)

	def openSkinSelectorDelayed(self):
		self.delaytimer = eTimer()
		self.delaytimer.callback.append(self.openSkinSelector)
		self.delaytimer.start(200, True)

	def search_weather_id_callback(self, res):
		if res:
			id_dic = get_woeid_from_yahoo(res)
			if 'error' in id_dic:
				error_txt = id_dic['error']
				self.session.open(MessageBox, _("Sorry, there was a problem:") + "\n%s" % error_txt, MessageBox.TYPE_ERROR)
			elif 'count' in id_dic:
				result_no = int(id_dic['count'])
				location_list = []
				for i in list(range(0, result_no)):
					location_list.append(id_dic[i])
				self.session.openWithCallback(self.select_weather_id_callback, WeatherLocationChoiceList, location_list)

	def select_weather_id_callback(self, res):
		if res and isInteger(res):
			print(res)
			config.plugins.AtileHD.woeid.value = int(res)

	def skinChanged(self, ret=None):
		global cur_skin
		cur_skin = config.skin.primary_skin.value.replace('/skin.xml', '')
		if cur_skin == "skin.xml":
			self.restartGUI()
		else:
			self.getInitConfig()
			self.createConfigList()

	def keyGreen(self):
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].save()
			chdir(self.skin_base_dir)

			# color
			self.makeSettings(self.myAtileHD_color, self.color_file)
			# font
			self.makeSettings(self.myAtileHD_font, self.font_file)
			# background
			self.makeSettings(self.myAtileHD_background, self.background_file)
			# sb
			self.makeSettings(self.myAtileHD_sb, self.sb_file)
			# infobar
			self.makeSettings(self.myAtileHD_infobar, self.infobar_file)
			# sib
			self.makeSettings(self.myAtileHD_sib, self.sib_file)
			# ch_se
			self.makeSettings(self.myAtileHD_ch_se, self.ch_se_file)
			# ev
			self.makeSettings(self.myAtileHD_ev, self.ev_file)
			# clock
			self.makeSettings(self.myAtileHD_clock, self.clock_file)
			# ul
			self.makeSettings(self.myAtileHD_ul, self.ul_file)

			if not path.exists("mySkin_off"):
				mkdir("mySkin_off")
				print("makedir mySkin_off")
			if self.myAtileHD_active.value:
				if not path.exists("mySkin") and path.exists("mySkin_off"):
					symlink("mySkin_off", "mySkin")
			else:
				if path.exists("mySkin"):
					if path.exists("mySkin_off"):
						if path.islink("mySkin"):
							remove("mySkin")
						else:
							shutil.rmtree("mySkin")
					else:
						rename("mySkin", "mySkin_off")
			self.restartGUI()
		elif config.skin.primary_skin.value != self.start_skin:
			self.restartGUI()
		else:
			if self.changed_screens:
				self.restartGUI()
			else:
				self.close()

	def makeSettings(self, config_entry, user_file):
		if path.exists(user_file) or path.islink(user_file):
			remove(user_file)
		if config_entry.value != 'default':
			symlink(config_entry.value, user_file)

	def AtileHDScreenCB(self):
		self.changed_screens = True
		self["config"].setCurrentIndex(0)

	def restartGUI(self):
		restartbox = self.session.openWithCallback(self.restartGUIcb, MessageBox, _("Restart necessary, restart GUI now?"), MessageBox.TYPE_YESNO)
		restartbox.setTitle(_("Message"))

	def about(self):
		self.session.open(AtileHD_About)

	def restartGUIcb(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 3)
		else:
			self.close()


class AtileHD_About(Screen):

	def __init__(self, session, args=0):
		Screen.__init__(self, session)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.keyOk,
			}, -2)

	def keyOk(self):
		self.close()

	def cancel(self):
		self.close()


class AtileHDScreens(Screen):

	skin = """
		<screen name="AtileHDScreens" position="center,center" size="1280,720" title="AtileHD Setup">
			<widget source="Title" render="Label" position="70,47" size="950,43" font="Regular;35" transparent="1" />
			<widget source="menu" render="Listbox" position="70,115" size="700,480" scrollbarMode="showOnDemand" scrollbarWidth="6" scrollbarSliderBorderWidth="1" enableWrapAround="1" transparent="1">
				<convert type="TemplatedMultiContent">
					{"template":
						[
							MultiContentEntryPixmapAlphaTest(pos = (2, 2), size = (25, 24), png = 2),
							MultiContentEntryText(pos = (35, 4), size = (500, 24), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER, text = 1),
						],
						"fonts": [gFont("Regular", 22),gFont("Regular", 16)],
						"itemHeight": 30
					}
				</convert>
			</widget>
			<widget name="Picture" position="808,342" size="400,225" alphatest="on" />
			<eLabel position=" 55,675" size="290, 5" zPosition="-10" backgroundColor="red" />
			<eLabel position="350,675" size="290, 5" zPosition="-10" backgroundColor="green" />
			<widget source="key_red" render="Label" position="70,635" size="260,25" zPosition="1" font="Regular;20" halign="left" transparent="1" />
			<widget source="key_green" render="Label" position="365,635" size="260,25" zPosition="1" font="Regular;20" halign="left" transparent="1" />
		</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)

		global cur_skin
		self.is_atile = False
		if cur_skin == 'AtileHD':
			self.is_atile = True

		self.title = _("%s additional screens") % cur_skin
		try:
			self["title"] = StaticText(self.title)
		except:
			print('self["title"] was not found in skin')

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("On"))

		self["Picture"] = Pixmap()

		menu_list = []
		self["menu"] = List(menu_list)

		self["shortcuts"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
		{
			"ok": self.runMenuEntry,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.runMenuEntry,
		}, -2)

		self.skin_base_dir = "/usr/share/enigma2/%s/" % cur_skin
		self.screen_dir = "allScreens"
		self.skinparts_dir = "skinparts"
		self.file_dir = "mySkin_off"
		my_path = resolveFilename(SCOPE_SKINS, "%s/icons/lock_on.png" % cur_skin)
		if not path.exists(my_path):
			my_path = resolveFilename(SCOPE_SKINS, "skin_default/icons/lock_on.png")
		self.enabled_pic = LoadPixmap(cached=True, path=my_path)
		my_path = resolveFilename(SCOPE_SKINS, "%s/icons/lock_off.png" % cur_skin)
		if not path.exists(my_path):
			my_path = resolveFilename(SCOPE_SKINS, "skin_default/icons/lock_off.png")
		self.disabled_pic = LoadPixmap(cached=True, path=my_path)

		if not self.selectionChanged in self["menu"].onSelectionChanged:
			self["menu"].onSelectionChanged.append(self.selectionChanged)

		self.onLayoutFinish.append(self.createMenuList)

	def selectionChanged(self):
		sel = self["menu"].getCurrent()
		if sel is not None:
			self.setPicture(sel[0])
			if sel[2] == self.enabled_pic:
				self["key_green"].setText(_("Off"))
			elif sel[2] == self.disabled_pic:
				self["key_green"].setText(_("On"))

	def createMenuList(self):
		chdir(self.skin_base_dir)
		f_list = []
		dir_path = self.skin_base_dir + self.screen_dir
		if not path.exists(dir_path):
			makedirs(dir_path)
		dir_skinparts_path = self.skin_base_dir + self.skinparts_dir
		if not path.exists(dir_skinparts_path):
			makedirs(dir_skinparts_path)
		file_dir_path = self.skin_base_dir + self.file_dir
		if not path.exists(file_dir_path):
			makedirs(file_dir_path)
		dir_global_skinparts = resolveFilename(SCOPE_SKINS, "skinparts")
		if path.exists(dir_global_skinparts):
			for pack in listdir(dir_global_skinparts):
				if path.isdir(dir_global_skinparts + "/" + pack):
					for f in listdir(dir_global_skinparts + "/" + pack):
						if path.exists(dir_global_skinparts + "/" + pack + "/" + f + "/" + f + "_Atile.xml"):
							if not path.exists(dir_path + "/skin_" + f + ".xml"):
								symlink(dir_global_skinparts + "/" + pack + "/" + f + "/" + f + "_Atile.xml", dir_path + "/skin_" + f + ".xml")
							if not path.exists(dir_skinparts_path + "/" + f):
								symlink(dir_global_skinparts + "/" + pack + "/" + f, dir_skinparts_path + "/" + f)
		list_dir = sorted(listdir(dir_path), key=str.lower)
		for f in list_dir:
			if f.endswith('.xml') and f.startswith('skin_'):
				if (not path.islink(dir_path + "/" + f)) or os.path.exists(os.readlink(dir_path + "/" + f)):
					friendly_name = f.replace("skin_", "")
					friendly_name = friendly_name.replace(".xml", "")
					friendly_name = friendly_name.replace("_", " ")
					linked_file = file_dir_path + "/" + f
					if path.exists(linked_file):
						if path.islink(linked_file):
							pic = self.enabled_pic
						else:
							remove(linked_file)
							symlink(dir_path + "/" + f, file_dir_path + "/" + f)
							pic = self.enabled_pic
					else:
						pic = self.disabled_pic
					f_list.append((f, friendly_name, pic))
				else:
					if path.islink(dir_path + "/" + f):
						remove(dir_path + "/" + f)
		menu_list = []
		for entry in f_list:
			menu_list.append((entry[0], entry[1], entry[2]))
		self["menu"].updateList(menu_list)
		self.selectionChanged()

	def setPicture(self, f):
		pic = f.replace(".xml", ".png")
		preview = self.skin_base_dir + "preview/preview_" + pic
		if path.exists(preview):
			self["Picture"].instance.setPixmapFromFile(preview)
			self["Picture"].show()
		else:
			self["Picture"].hide()

	def keyCancel(self):
		self.close()

	def runMenuEntry(self):
		sel = self["menu"].getCurrent()
		if sel is not None:
			if sel[2] == self.enabled_pic:
				remove(self.skin_base_dir + self.file_dir + "/" + sel[0])
			elif sel[2] == self.disabled_pic:
				symlink(self.skin_base_dir + self.screen_dir + "/" + sel[0], self.skin_base_dir + self.file_dir + "/" + sel[0])
			self.createMenuList()
