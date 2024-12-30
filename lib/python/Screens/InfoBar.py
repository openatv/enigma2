from glob import glob
from os.path import splitext

from enigma import eProfileWrite

# workaround for required config entry dependencies.
import Screens.MovieSelection
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.Label import Label
from Components.Pixmap import MultiPixmap
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Tools.Directories import fileExists
from Screens.ButtonSetup import InfoBarButtonSetup

import enigma
eProfileWrite("LOAD:enigma")

boxtype = BoxInfo.getItem("machinebuild")

eProfileWrite("LOAD:InfoBarGenerics")
from Screens.InfoBarGenerics import InfoBarShowHide, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarRdsDecoder, InfoBarRedButton, InfoBarTimerButton, InfoBarVmodeButton, \
	InfoBarEPG, InfoBarSeek, InfoBarInstantRecord, InfoBarResolutionSelection, InfoBarAspectSelection, \
	InfoBarAudioSelection, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarUnhandledKey, InfoBarLongKeyDetection, \
	InfoBarSubserviceSelection, InfoBarShowMovies, \
	InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarSimpleEventView, InfoBarBuffer, \
	InfoBarSummarySupport, InfoBarMoviePlayerSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions, \
	InfoBarSubtitleSupport, InfoBarPiP, InfoBarPlugins, InfoBarServiceErrorPopupSupport, InfoBarJobman, InfoBarZoom, InfoBarSleepTimer, InfoBarOpenOnTopHelper, InfoBarHandleBsod, \
	InfoBarHdmi, setResumePoint, delResumePoint

eProfileWrite("LOAD:InitBar_Components")
from Components.ActionMap import HelpableActionMap
from Components.Timeshift import InfoBarTimeshift
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase

eProfileWrite("LOAD:InfoBar_Class")


class InfoBar(InfoBarBase, InfoBarShowHide,
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, InfoBarRdsDecoder,
	InfoBarInstantRecord, InfoBarAudioSelection, InfoBarRedButton, InfoBarTimerButton, InfoBarResolutionSelection, InfoBarAspectSelection, InfoBarVmodeButton,
	InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarUnhandledKey, InfoBarLongKeyDetection,
	InfoBarSubserviceSelection, InfoBarTimeshift, InfoBarSeek, InfoBarCueSheetSupport, InfoBarBuffer,
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions,
	InfoBarPiP, InfoBarPlugins, InfoBarSubtitleSupport, InfoBarServiceErrorPopupSupport, InfoBarJobman, InfoBarZoom, InfoBarSleepTimer, InfoBarOpenOnTopHelper, InfoBarHandleBsod,
	InfoBarHdmi, InfoBarButtonSetup, Screen):

	instance = None

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		if config.usage.show_infobar_lite.value and (config.skin.primary_skin.value == "DMConcinnity-HD/skin.xml" or config.skin.primary_skin.value.startswith('MetrixHD/')):
			self.skinName = "InfoBarLite"

		self["actions"] = HelpableActionMap(self, "InfobarActions", {
			"showMovies": (self.showMovies, _("Play recorded movies")),
			"showRadio": (self.showRadioButton, _("Show the radio player")),
			"showTv": (self.showTvButton, _("Show the tv player")),
			"toogleTvRadio": (self.toogleTvRadio, _("Toggles between tv and radio")),
			"openBouquetList": (self.openBouquetList, _("Open bouquetlist")),
			"showMediaPlayer": (self.showMediaPlayer, _("Show the media player")),
			"openTimerList": (self.openTimerList, _("Open Timerlist")),
			"openAutoTimerList": (self.openAutoTimerList, _("Open AutoTimerlist")),
			"openEPGSearch": (self.openEPGSearch, _("Open EPGSearch")),
			"openIMDB": (self.openIMDB, _("Open IMDb")),
			"showMC": (self.showMediaCenter, _("Show the media center")),
			"openSleepTimer": (self.openSleepTimer, _("Show the SleepTimer")),
			"openSchedulerList": (self.openSchedulerList, _("Show the Scheduler")),
			"ZoomInOut": (self.ZoomInOut, _("Zoom In/Out TV")),
			"ZoomOff": (self.ZoomOff, _("Zoom Off")),
			"showWWW": (self.showPORTAL, _("Open MediaStream")),
			"showSetup": (self.showSetup, _("Show setup")),
			"showInformation": (self.showInformation, _("Show Information")),
			"showFormat": (self.showFormat, _("Show Format Setup")),
			"showPluginBrowser": (self.showPluginBrowser, _("Show the plugins")),
			"showBoxPortal": (self.showBoxPortal, _("Show Box Portal")),
			"openSimpleUnmount": (self.openSimpleUnmount, _("Simple umounter mass storage device.")),
			}, prio=2, description=_("Live TV Actions"))

		self["key_red"] = Label()
		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["key_green"] = Label()

		self.allowPiP = True
		self.radioTV = 0

		for x in InfoBarBase, InfoBarShowHide, \
				InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, InfoBarRdsDecoder, \
				InfoBarInstantRecord, InfoBarAudioSelection, InfoBarRedButton, InfoBarTimerButton, InfoBarUnhandledKey, InfoBarLongKeyDetection, InfoBarResolutionSelection, InfoBarVmodeButton, \
				InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarSubserviceSelection, InfoBarAspectSelection, InfoBarBuffer, \
				InfoBarTimeshift, InfoBarSeek, InfoBarCueSheetSupport, InfoBarSummarySupport, InfoBarTimeshiftState, \
				InfoBarTeletextPlugin, InfoBarExtensions, InfoBarPiP, InfoBarSubtitleSupport, InfoBarJobman, InfoBarZoom, InfoBarSleepTimer, InfoBarOpenOnTopHelper, InfoBarHandleBsod, \
				InfoBarHdmi, InfoBarPlugins, InfoBarServiceErrorPopupSupport, InfoBarButtonSetup:
			x.__init__(self)

		self.helpList.append((self["actions"], "InfobarActions", [("showMovies", _("Watch recordings"))]))
		self.helpList.append((self["actions"], "InfobarActions", [("showRadio", _("Listen to the radio"))]))

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				enigma.iPlayableService.evUpdatedEventInfo: self.__eventInfoChanged
			})

		self.current_begin_time = 0
		assert InfoBar.instance is None, "class InfoBar is a singleton class and just one instance of this class is allowed!"
		InfoBar.instance = self

		if config.usage.energyTimer.value:
			self.setEnergyTimer(config.usage.energyTimer.value, showMessage=False)

		if config.misc.initialchannelselection.value:
			self.onShown.append(self.showMenu)

		self.zoomrate = 0
		self.zoomin = 1

		self.onShow.append(self.doButtonsCheck)

	def showMenu(self):
		self.onShown.remove(self.showMenu)
		config.misc.initialchannelselection.value = False
		config.misc.initialchannelselection.save()
		self.showMainMenu()

	def doButtonsCheck(self):
		if config.plisettings.ColouredButtons.value:
			self["key_yellow"].setText(_("Search"))
			self["key_red"].setText(_("Single EPG"))
			if config.usage.subservice.value == 0:
				self["key_green"].setText(_("Timers"))
			elif config.usage.subservice.value == 1:
				self["key_green"].setText(_("Plugins"))
			else:
				self["key_green"].setText(_("Subservices"))
		self["key_blue"].setText(_("Extensions"))

	def __onClose(self):
		InfoBar.instance = None

	def __eventInfoChanged(self):
		if self.execing:
			service = self.session.nav.getCurrentService()
			old_begin_time = self.current_begin_time
			info = service and service.info()
			ptr = info and info.getEvent(0)
			self.current_begin_time = ptr and ptr.getBeginTime() or 0
			if config.usage.show_infobar_on_event_change.value:
				if old_begin_time and old_begin_time != self.current_begin_time:
					self.doShow()

	def __checkServiceStarted(self):
		self.__serviceStarted(True)
		self.onExecBegin.remove(self.__checkServiceStarted)

	def serviceStarted(self):  #override from InfoBarShowHide
		new = self.servicelist.newServicePlayed()
		if self.execing:
			InfoBarShowHide.serviceStarted(self)
			self.current_begin_time = 0
		elif self.__checkServiceStarted not in self.onShown and new:
			self.onShown.append(self.__checkServiceStarted)

	def __checkServiceStarted(self):
		self.serviceStarted()
		self.onShown.remove(self.__checkServiceStarted)

	def openBouquetList(self):
		if config.usage.tvradiobutton_mode.value == "MovieList":
			self.showTvChannelList(True)
			self.showMovies()
		elif config.usage.tvradiobutton_mode.value == "ChannelList":
			self.showTvChannelList(True)
		elif config.usage.tvradiobutton_mode.value == "BouquetList":
			self.showTvChannelList(True)
			self.servicelist.showFavourites()

	def showTvButton(self):
		if boxtype.startswith('gb') or boxtype in ('classm', 'genius', 'evo', 'galaxym6', 'sf8008', 'sf8008m', 'sx988', 'ip8', 'og2ott4k', 'og2s4k', 'sfx6008'):
			self.toogleTvRadio()
		elif boxtype in ('uniboxhd1', 'uniboxhd2', 'uniboxhd3', 'sezam5000hd', 'mbtwin'):
			self.showMovies()
		else:
			self.showTv()

	def showTv(self):
		if config.usage.tvradiobutton_mode.value == "MovieList":
			self.showTvChannelList(True)
			self.showMovies()
		elif config.usage.tvradiobutton_mode.value == "BouquetList":
			self.showTvChannelList(True)
			if config.usage.show_servicelist.value:
				self.servicelist.showFavourites()
		else:
			self.showTvChannelList(True)

	def showRadioButton(self):
		if boxtype.startswith('gb') or boxtype in ('classm', 'genius', 'evo', 'galaxym6', 'uniboxhd1', 'uniboxhd2', 'uniboxhd3', 'sezam5000hd', 'mbtwin', 'beyonwizt3'):
			self.toogleTvRadio()
		else:
			self.showRadio()

	def showRadio(self):
		if config.usage.e1like_radio_mode.value:
			if config.usage.tvradiobutton_mode.value == "BouquetList":
				self.showRadioChannelList(True)
				if config.usage.show_servicelist.value:
					self.servicelist.showFavourites()
			else:
				self.showRadioChannelList(True)
		else:
			self.rds_display.hide()  # in InfoBarRdsDecoder
			from Screens.ChannelSelection import ChannelSelectionRadio
			self.session.openWithCallback(self.ChannelSelectionRadioClosed, ChannelSelectionRadio, self)

	def toogleTvRadio(self):
		if self.radioTV == 1:
			self.radioTV = 0
			self.showTv()
		else:
			self.radioTV = 1
			self.showRadio()

	def ChannelSelectionRadioClosed(self, *arg):
		self.rds_display.show()  # in InfoBarRdsDecoder
		self.radioTV = 0
		self.doShow()

	def showMovies(self, defaultRef=None):
		if BoxInfo.getItem("displaybrand") == 'GI' or boxtype.startswith('ini') or boxtype.startswith('venton'):
			from Screens.BoxPortal import BoxPortal
			self.session.open(BoxPortal)
		else:
		#	self.lastservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		#	if self.lastservice and ':0:/' in self.lastservice.toString():
		#		self.lastservice = enigma.eServiceReference(config.movielist.curentlyplayingservice.value)
		#	self.session.openWithCallback(self.movieSelected, Screens.MovieSelection.MovieSelection, defaultRef, timeshiftEnabled = self.timeshiftEnabled())
			self.showMoviePlayer(defaultRef)

	def showMoviePlayer(self, defaultRef=None):  # for using with hotkeys (ButtonSetup.py) regardless of plugins which overwrite the showMovies function
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if self.lastservice and ':0:/' in self.lastservice.toString():
			self.lastservice = enigma.eServiceReference(config.movielist.curentlyplayingservice.value)
		self.session.openWithCallback(self.movieSelected, Screens.MovieSelection.MovieSelection, defaultRef, timeshiftEnabled=self.timeshiftEnabled())

	def movieSelected(self, service, fromMovieSelection=True):
		ref = self.lastservice
		del self.lastservice
		if service is None:
			if ref and not self.session.nav.getCurrentlyPlayingServiceOrGroup():
				self.session.nav.playService(ref)
		else:
			self.session.open(MoviePlayer, service, slist=self.servicelist, lastservice=ref, fromMovieSelection=fromMovieSelection)

	def showMediaPlayer(self):
		try:
			from Plugins.Extensions.MediaPlayer.plugin import MediaPlayer
			self.session.open(MediaPlayer)
			no_plugin = False
		except Exception as e:
			self.session.open(MessageBox, _("The MediaPlayer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showMediaCenter(self):
		try:
			from Plugins.Extensions.BMediaCenter.plugin import DMC_MainMenu
			self.session.open(DMC_MainMenu)
			no_plugin = False
		except Exception as e:
			self.session.open(MessageBox, _("The MediaCenter plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openSleepTimer(self):
		from Screens.SleepTimer import SleepTimerButton
		self.session.open(SleepTimerButton)

	def openTimerList(self):
		from Screens.Timers import RecordTimerOverview
		self.session.open(RecordTimerOverview)

	def openSchedulerList(self):
		from Screens.Timers import SchedulerOverview
		self.session.open(SchedulerOverview)

	@staticmethod
	def _getAutoTimerPluginFunc():
		# Use the WHERE_MENU descriptor because it's the only
		# AutoTimer plugin descriptor that opens the AutoTimer
		# overview and is always present.

		for l in plugins.getPlugins(PluginDescriptor.WHERE_MENU):
			if l.name == _("Auto Timers"):  # Must use translated name same as in the po of plugin autotimer
				menuEntry = l("timermenu")
				if menuEntry and len(menuEntry[0]) > 1 and callable(menuEntry[0][1]):
					return menuEntry[0][1]
		return None

	def openAutoTimerList(self):
		autotimerFunc = self._getAutoTimerPluginFunc()
		if autotimerFunc is not None:
			autotimerFunc(self.session)
		else:
			self.session.open(MessageBox, _("The AutoTimer plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openEPGSearch(self):
		try:
			for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				if plugin.name == _("EPGSearch") or plugin.name == _("search EPG...") or plugin.name == "Durchsuche EPG...":
					self.runPlugin(plugin)
					break
		except Exception as e:
			self.session.open(MessageBox, _("The EPGSearch plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openIMDB(self):
		try:
			for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				if plugin.name == _("IMDb Details"):
					self.runPlugin(plugin)
					break
		except Exception as e:
			self.session.open(MessageBox, _("The IMDb plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def openSimpleUnmount(self):
		try:
			for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
				if plugin.name == _("SimpleUmount"):
					self.runPlugin(plugin)
					break
		except Exception as e:
			self.session.open(MessageBox, _("The SimpleUmount plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def ZoomInOut(self):
		zoomval = 0
		if self.zoomrate > 3:
			self.zoomin = 0
		elif self.zoomrate < -9:
			self.zoomin = 1
		if self.zoomin == 1:
			self.zoomrate += 1
		else:
			self.zoomrate -= 1
		if self.zoomrate < 0:
			zoomval = abs(self.zoomrate) + 10
		else:
			zoomval = self.zoomrate
		print('zoomRate:', self.zoomrate)
		print('zoomval:', zoomval)
		if fileExists("/proc/stb/vmpeg/0/zoomrate"):
			file = open('/proc/stb/vmpeg/0/zoomrate', 'w')
			file.write('%d' % int(zoomval))
			file.close()

	def ZoomOff(self):
		self.zoomrate = 0
		self.zoomin = 1
		if fileExists("/proc/stb/vmpeg/0/zoomrate"):
			file = open('/proc/stb/vmpeg/0/zoomrate', 'w')
			file.write(str(0))
			file.close()

	def showPORTAL(self):
		try:
			from Plugins.Extensions.MediaStream.plugin import MSmain as MediaStream
			MediaStream(self.session)
			no_plugin = False
		except Exception as e:
			self.session.open(MessageBox, _("The MediaStream plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showSetup(self):
		from Screens.Menu import Menu, findMenu
		menu = findMenu("setup")
		if menu:
			self.session.infobar = self
			self.session.open(Menu, menu)
			return

	def showInformation(self):
		from Screens.Menu import Menu, findMenu
		menu = findMenu("information")
		if menu:
			self.session.infobar = self
			self.session.open(Menu, menu)
			return

	def showFormat(self):
		try:
			from Plugins.SystemPlugins.Videomode.plugin import videoSetupMain
			self.session.instantiateDialog(videoSetupMain)
			no_plugin = False
		except Exception as e:
			self.session.open(MessageBox, _("The VideoMode plugin is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)

	def showPluginBrowser(self):
		from Screens.PluginBrowser import PluginBrowser
		self.session.open(PluginBrowser)

	def showBoxPortal(self):
		if BoxInfo.getItem("displaybrand") == 'GI' or boxtype.startswith('ini') or boxtype.startswith('venton'):
			from Screens.BoxPortal import BoxPortal
			self.session.open(BoxPortal)
		else:
			self.showMovies()


def setAudioTrack(service):
	try:
		from Tools.ISO639 import LanguageCodes as langC
		tracks = service and service.audioTracks()
		nTracks = tracks and tracks.getNumberOfTracks() or 0
		if not nTracks:
			return
		idx = 0
		trackList = []
		for i in list(range(nTracks)):
			audioInfo = tracks.getTrackInfo(i)
			lang = audioInfo.getLanguage()
			if lang in langC:
				lang = langC[lang][0]
			desc = audioInfo.getDescription()
			track = idx, lang, desc
			idx += 1
			trackList += [track]
		seltrack = tracks.getCurrentTrack()
		# we need default selected language from image
		# to set the audiotrack if "config.autolanguage.audio_autoselect...values" are not set
		from Components.International import international
		syslang = international.getLanguage()
		syslang = langC[syslang][0]
		if (config.autolanguage.audio_autoselect1.value or config.autolanguage.audio_autoselect2.value or config.autolanguage.audio_autoselect3.value or config.autolanguage.audio_autoselect4.value) != "---":
			audiolang = [config.autolanguage.audio_autoselect1.value, config.autolanguage.audio_autoselect2.value, config.autolanguage.audio_autoselect3.value, config.autolanguage.audio_autoselect4.value]
			caudiolang = True
		else:
			audiolang = syslang
			caudiolang = False
		useAc3 = config.autolanguage.audio_defaultac3.value
		if useAc3:
			matchedAc3 = tryAudioTrack(tracks, audiolang, caudiolang, trackList, seltrack, useAc3)
			if matchedAc3:
				return
			matchedMpeg = tryAudioTrack(tracks, audiolang, caudiolang, trackList, seltrack, False)
			if matchedMpeg:
				return
			tracks.selectTrack(0)    # fallback to track 1(0)
			return
		else:
			matchedMpeg = tryAudioTrack(tracks, audiolang, caudiolang, trackList, seltrack, False)
			if matchedMpeg:
				return
			matchedAc3 = tryAudioTrack(tracks, audiolang, caudiolang, trackList, seltrack, useAc3)
			if matchedAc3:
				return
			tracks.selectTrack(0)    # fallback to track 1(0)
	except Exception as e:
		print("[MoviePlayer] audioTrack exception:\n" + str(e))


def tryAudioTrack(tracks, audiolang, caudiolang, trackList, seltrack, useAc3):
	for entry in audiolang:
		if caudiolang:
			# we need here more replacing for other language, or new configs with another list !!!
			# choice gives only the value, never the description
			# so we can also make some changes in "config.py" to get the description too, then we dont need replacing here !
			entry = entry.replace('eng qaa Englisch', 'English').replace('deu ger', 'German')
		for x in trackList:
			if entry == x[1] and seltrack == x[0]:
				if useAc3:
					if x[2].startswith('AC'):
						print("[MoviePlayer] audio track is current selected track: " + str(x))
						return True
				else:
					print("[MoviePlayer] audio track is current selected track: " + str(x))
					return True
			elif entry == x[1] and seltrack != x[0]:
				if useAc3:
					if x[2].startswith('AC'):
						print("[MoviePlayer] audio track match: " + str(x))
						tracks.selectTrack(x[0])
						return True
				else:
					print("[MoviePlayer] audio track match: " + str(x))
					tracks.selectTrack(x[0])
					return True
	return False


class MoviePlayer(InfoBarAspectSelection, InfoBarSimpleEventView, InfoBarBase, InfoBarShowHide, InfoBarLongKeyDetection, InfoBarMenu, InfoBarEPG,
		InfoBarSeek, InfoBarShowMovies, InfoBarInstantRecord, InfoBarAudioSelection, InfoBarResolutionSelection, InfoBarNotifications,
		InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport,
		InfoBarMoviePlayerSummarySupport, InfoBarSubtitleSupport, Screen, InfoBarTeletextPlugin,
		InfoBarServiceErrorPopupSupport, InfoBarExtensions, InfoBarPlugins, InfoBarPiP, InfoBarZoom, InfoBarHdmi, InfoBarButtonSetup):

	ENABLE_RESUME_SUPPORT = True

	instance = None

	def __init__(self, session, service, slist=None, lastservice=None, fromMovieSelection=True):
		Screen.__init__(self, session, enableHelp=True)
		self.pts_pvrStateDialog = ""
		self.fromMovieSelection = fromMovieSelection

		self["key_yellow"] = Label()
		self["key_blue"] = Label()
		self["key_green"] = Label()

		self["eventname"] = Label()
		self["state"] = Label()
		self["speed"] = Label()
		self["statusicon"] = MultiPixmap()

		self["actions"] = HelpableActionMap(self, "MoviePlayerActions", {
			"leavePlayer": (self.leavePlayer, _("leave movie player")),
			"leavePlayerOnExit": (self.leavePlayerOnExit, _("leave movie player"))
		}, prio=0, description=_("Movie Player Actions"))

		self.allowPiP = True

		for x in InfoBarAspectSelection, InfoBarShowHide, InfoBarLongKeyDetection, InfoBarMenu, InfoBarEPG, \
				InfoBarBase, InfoBarSeek, InfoBarShowMovies, InfoBarInstantRecord, \
				InfoBarAudioSelection, InfoBarResolutionSelection, InfoBarNotifications, InfoBarSimpleEventView, \
				InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, \
				InfoBarMoviePlayerSummarySupport, InfoBarSubtitleSupport, \
				InfoBarTeletextPlugin, InfoBarServiceErrorPopupSupport, InfoBarExtensions, \
				InfoBarPlugins, InfoBarPiP, InfoBarZoom, InfoBarButtonSetup:
			x.__init__(self)

		self.onChangedEntry = []
		self.servicelist = slist
		self.lastservice = lastservice or session.nav.getCurrentlyPlayingServiceOrGroup()
		path = splitext(service.getPath())[0]
		subs = []
		for sub in ("srt", "ass", "ssa"):
			subs = glob("%s*.%s" % (path, sub))
			if subs:
				break
		if subs:
			service.setSubUri(subs[0])  # Support currently only one external sub

		session.nav.playService(service)
		self.cur_service = service
		self.returning = False
		self.onClose.append(self.__onClose)
		self.onShow.append(self.doButtonsCheck)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				enigma.iPlayableService.evStart: self.__evStart
			})

		assert MoviePlayer.instance is None, "class InfoBar is a singleton class and just one instance of this class is allowed!"
		MoviePlayer.instance = self

		# is needed for every first call of MoviePlayer
		self.__evStart()

	def __evStart(self):
		self.switchAudioTimer = enigma.eTimer()
		self.switchAudioTimer.callback.append(self.switchAudio)
		self.switchAudioTimer.start(750, True)    # 750 is a safe-value

	def switchAudio(self):
		service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if service:
			# we go this way for other extensions as own records(they switch over pmt)
			path = service.getPath()
			import os
			ext = os.path.splitext(path)[1].lower()
			exts = [".mkv", ".avi", ".divx", ".mp4"]      # we need more extensions here ?
			if ext.lower() in exts:
				service = self.session.nav.getCurrentService()
				if service:
					setAudioTrack(service)

	def doButtonsCheck(self):
		if config.plisettings.ColouredButtons.value:
			self["key_yellow"].setText(_("Search"))
			self["key_green"].setText(_("Timers"))
		self["key_blue"].setText(_("Extensions"))

	def __onClose(self):
		MoviePlayer.instance = None
		if self.fromMovieSelection:
			from Screens.MovieSelection import playlist
			del playlist[:]
		Screens.InfoBar.InfoBar.instance.callServiceStarted()
		self.session.nav.playService(self.lastservice)
		if self.fromMovieSelection:
			config.usage.last_movie_played.value = self.cur_service.toString()
			config.usage.last_movie_played.save()

	def handleLeave(self, how):
		self.is_closing = True
		if self.fromMovieSelection:
			if how == "ask":
				if config.usage.setup_level.index < 2:  # -expert
					list = (
						(_("Yes"), "quit"),
						(_("No"), "continue")
					)
				else:
					list = (
						(_("Yes"), "quit"),
						(_("Yes, returning to movie list"), "movielist"),
						(_("Yes, and delete this movie"), "quitanddelete"),
						(_("Yes, delete this movie and return to movie list"), "deleteandmovielist"),
						(_("No"), "continue"),
						(_("No, but restart from begin"), "restart")
					)

				from Screens.ChoiceBox import ChoiceBox
				self.session.openWithCallback(self.leavePlayerConfirmed, ChoiceBox, title=_("Stop playing this movie?"), list=list)
			else:
				self.leavePlayerConfirmed([True, how])
		else:
			self.close()

	def leavePlayer(self):
		setResumePoint(self.session)
		self.handleLeave(config.usage.on_movie_stop.value)

	def leavePlayerOnExit(self):
		if self.shown:
			self.hide()
		elif self.session.pipshown and "popup" in config.usage.pip_hideOnExit.value:
			if config.usage.pip_hideOnExit.value == "popup":
				self.session.openWithCallback(self.hidePipOnExitCallback, MessageBox, _("Disable Picture in Picture"), simple=True)
			else:
				self.hidePipOnExitCallback(True)
		elif config.usage.leave_movieplayer_onExit.value == "popup":
			self.session.openWithCallback(self.leavePlayerOnExitCallback, MessageBox, _("Exit movie player?"), simple=True)
		elif config.usage.leave_movieplayer_onExit.value == "without popup":
			self.leavePlayerOnExitCallback(True)
		elif config.usage.leave_movieplayer_onExit.value == "stop":
			self.leavePlayer()

	def leavePlayerOnExitCallback(self, answer):
		if answer:
			setResumePoint(self.session)
			self.handleLeave("quit")

	def hidePipOnExitCallback(self, answer):
		if answer:
			self.showPiP()

	def deleteConfirmed(self, answer):
		if answer:
			self.leavePlayerConfirmed((True, "quitanddeleteconfirmed"))

	def deleteAndMovielistConfirmed(self, answer):
		if answer:
			self.leavePlayerConfirmed((True, "deleteandmovielistconfirmed"))

	def movielistAgain(self):
		if self.fromMovieSelection:
			from Screens.MovieSelection import playlist
			del playlist[:]
			self.session.nav.playService(self.lastservice)
			self.leavePlayerConfirmed((True, "movielist"))

	def leavePlayerConfirmed(self, answer):
		answer = answer and answer[1]
		if answer is None:
			return
		if answer in ("quitanddelete", "quitanddeleteconfirmed", "deleteandmovielist", "deleteandmovielistconfirmed"):
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			serviceHandler = enigma.eServiceCenter.getInstance()
			if answer in ("quitanddelete", "deleteandmovielist"):
				msg = ''
				if config.usage.movielist_trashcan.value:
					import Tools.Trashcan
					try:
						trash = Tools.Trashcan.createTrashcan(ref.getPath())
						Screens.MovieSelection.moveServiceFiles(ref, trash)
						# Moved to trash, okay
						if answer == "quitanddelete":
							self.close()
						else:
							self.movielistAgain()
						return
					except Exception as e:
						print("[InfoBar] Failed to move to .Trash folder:", e)
						msg = _("Cannot move to trash can") + "\n" + str(e) + "\n"
				info = serviceHandler.info(ref)
				name = info and info.getName(ref) or _("this recording")
				msg += _("Do you really want to delete '%s'?") % name
				if answer == "quitanddelete":
					self.session.openWithCallback(self.deleteConfirmed, MessageBox, msg)
				elif answer == "deleteandmovielist":
					self.session.openWithCallback(self.deleteAndMovielistConfirmed, MessageBox, msg)
				return

			elif answer in ("quitanddeleteconfirmed", "deleteandmovielistconfirmed"):
				offline = serviceHandler.offlineOperations(ref)
				if offline.deleteFromDisk(0):
					self.session.openWithCallback(self.close, MessageBox, _("You cannot delete this!"), MessageBox.TYPE_ERROR)
					if answer == "deleteandmovielistconfirmed":
						self.movielistAgain()
					return

		if answer in ("quit", "quitanddeleteconfirmed"):
			self.close()
		elif answer in ("movielist", "deleteandmovielistconfirmed"):
			if config.movielist.stop_service.value:
				ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			else:
				ref = self.lastservice
			self.returning = True
			self.session.openWithCallback(self.movieSelected, Screens.MovieSelection.MovieSelection, ref)
			self.session.nav.stopService()
			if not config.movielist.stop_service.value:
				self.session.nav.playService(self.lastservice)
		elif answer == "restart":
			self.doSeek(0)
			self.setSeekState(self.SEEK_STATE_PLAY)
		elif answer in ("playlist", "playlistquit", "loop"):
			(next_service, item, length) = self.getPlaylistServiceInfo(self.cur_service)
			if next_service is not None:
				if config.usage.next_movie_msg.value:
					self.displayPlayedName(next_service, item, length)
				self.session.nav.playService(next_service)
				self.cur_service = next_service
			else:
				if answer == "playlist":
					self.leavePlayerConfirmed([True, "movielist"])
				elif answer == "loop" and length > 0:
					self.leavePlayerConfirmed([True, "loop"])
				else:
					self.leavePlayerConfirmed([True, "quit"])
		elif answer in "repeatcurrent":
			if config.usage.next_movie_msg.value:
				(item, length) = self.getPlaylistServiceInfo(self.cur_service)
				self.displayPlayedName(self.cur_service, item, length)
			self.session.nav.stopService()
			self.session.nav.playService(self.cur_service)

	def doEofInternal(self, playing):
		if not self.execing:
			return
		if not playing:
			return
		ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if ref:
			delResumePoint(ref)
		self.handleLeave(config.usage.on_movie_eof.value)

	def up(self):
		slist = self.servicelist
		if slist and slist.dopipzap:
			if "keep" not in config.usage.servicelist_cursor_behavior.value:
				slist.moveUp()
			self.session.execDialog(slist)
		else:
			self.showMovies()

	def down(self):
		slist = self.servicelist
		if slist and slist.dopipzap:
			if "keep" not in config.usage.servicelist_cursor_behavior.value:
				slist.moveDown()
			self.session.execDialog(slist)
		else:
			self.showMovies()

	def right(self):
		# XXX: gross hack, we do not really seek if changing channel in pip :-)
		slist = self.servicelist
		if slist and slist.dopipzap:
			# XXX: We replicate InfoBarChannelSelection.zapDown here - we shouldn't do that
			if slist.inBouquet():
				prev = slist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value and slist.atEnd():
							slist.nextBouquet()
						else:
							slist.moveDown()
						cur = slist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				slist.moveDown()
			slist.zap(enable_pipzap=True)
		else:
			InfoBarSeek.seekFwd(self)

	def left(self):
		slist = self.servicelist
		if slist and slist.dopipzap:
			# XXX: We replicate InfoBarChannelSelection.zapUp here - we shouldn't do that
			if slist.inBouquet():
				prev = slist.getCurrentSelection()
				if prev:
					prev = prev.toString()
					while True:
						if config.usage.quickzap_bouquet_change.value:
							if slist.atBegin():
								slist.prevBouquet()
						slist.moveUp()
						cur = slist.getCurrentSelection()
						if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
							break
			else:
				slist.moveUp()
			slist.zap(enable_pipzap=True)
		else:
			InfoBarSeek.seekBack(self)

	def showPiP(self):
		slist = self.servicelist
		if self.session.pipshown:
			if slist and slist.dopipzap:
				slist.togglePipzap()
			if self.session.pipshown:
				del self.session.pip
				self.session.pipshown = False
		else:
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			xres = str(info.getInfo(enigma.iServiceInformation.sVideoWidth))
			if int(xres) <= 720 or BoxInfo.getItem("model") != 'blackbox7405':
				from Screens.PictureInPicture import PictureInPicture
				self.session.pip = self.session.instantiateDialog(PictureInPicture)
				self.session.pip.show()
				if self.session.pip.playService(slist.getCurrentSelection()):
					self.session.pipshown = True
					self.session.pip.servicePath = slist.getCurrentServicePath()
				else:
					self.session.pipshown = False
					del self.session.pip
			else:
				self.session.open(MessageBox, _("Your %s %s does not support PiP HD") % getBoxDisplayName(), type=MessageBox.TYPE_INFO, timeout=5)

	def movePiP(self):
		if self.session.pipshown:
			InfoBarPiP.movePiP(self)

	def swapPiP(self):
		pass

	def showMovies(self):
		if self.fromMovieSelection:
			ref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if ref and ':0:/' not in ref.toString():
				self.playingservice = ref  # movie list may change the currently playing
			else:
				self.playingservice = enigma.eServiceReference(config.movielist.curentlyplayingservice.value)
			self.session.openWithCallback(self.movieSelected, Screens.MovieSelection.MovieSelection, ref)
		else:
			self.close()

	def movieSelected(self, service):
		if service is not None:
			self.cur_service = service
			self.is_closing = False
			self.session.nav.playService(service)
			self.returning = False
		elif self.returning:
			self.close()
		else:
			self.is_closing = False
			try:
				ref = self.playingservice
				del self.playingservice
				# no selection? Continue where we left off
				if ref and not self.session.nav.getCurrentlyPlayingServiceOrGroup():
					self.session.nav.playService(ref)
			except:
				pass

	def getPlaylistServiceInfo(self, service):
		from Screens.MovieSelection import playlist
		for i, item in enumerate(playlist):
			if item == service:
				if config.usage.on_movie_eof.value == "repeatcurrent":
					return i + 1, len(playlist)
				i += 1
				if i < len(playlist):
					return playlist[i], i + 1, len(playlist)
				elif config.usage.on_movie_eof.value == "loop":
					return playlist[0], 1, len(playlist)
		return None, 0, 0

	def displayPlayedName(self, ref, index, n):
		import Tools.Notifications
		Tools.Notifications.AddPopup(text=_("%s/%s: %s") % (index, n, self.ref2HumanName(ref)), type=MessageBox.TYPE_INFO, timeout=5)

	def ref2HumanName(self, ref):
		return enigma.eServiceCenter.getInstance().info(ref).getName(ref)
