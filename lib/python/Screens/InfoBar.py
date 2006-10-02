from Screen import Screen

from Screens.MovieSelection import MovieSelection
from Screens.ChannelSelection import ChannelSelectionRadio
from Screens.MessageBox import MessageBox
from Screens.Ci import CiHandler
from ServiceReference import ServiceReference

from Components.Sources.Clock import Clock
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import config

from Tools.Notifications import AddNotificationWithCallback

from Screens.InfoBarGenerics import InfoBarShowHide, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, \
	InfoBarEPG, InfoBarEvent, InfoBarServiceName, InfoBarSeek, InfoBarInstantRecord, \
	InfoBarAudioSelection, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, \
	InfoBarSubserviceSelection, InfoBarTuner, InfoBarShowMovies, InfoBarTimeshift,  \
	InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarSimpleEventView, \
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions, \
	InfoBarSubtitleSupport, InfoBarPiP, InfoBarSubtitles, InfoBarPlugins

from Screens.HelpMenu import HelpableScreen, HelpMenu

from enigma import *

import time

class InfoBar(InfoBarShowHide,
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG,
	InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, 
	HelpableScreen, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish,
	InfoBarSubserviceSelection, InfoBarTuner, InfoBarTimeshift, InfoBarSeek,
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions,
	InfoBarPiP, InfoBarSubtitles, InfoBarPlugins,
	InfoBarSubtitleSupport, Screen):
	
	ALLOW_SUSPEND = True

	def __init__(self, session):
		Screen.__init__(self, session)

		CiHandler.setSession(session)

		self["actions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showMovies": (self.showMovies, _("Play recorded movies...")),
				"showRadio": (self.showRadio, _("Show the radio player...")),
				"showTv": (self.showTv, _("Show the tv player...")),
			}, prio=2)
		
		for x in HelpableScreen, \
				InfoBarShowHide, \
				InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
				InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, \
				InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarSubserviceSelection, \
				InfoBarTuner, InfoBarTimeshift, InfoBarSeek, InfoBarSummarySupport, InfoBarTimeshiftState, \
				InfoBarTeletextPlugin, InfoBarExtensions, InfoBarPiP, InfoBarSubtitles, InfoBarSubtitleSupport, \
				InfoBarPlugins:
			x.__init__(self)

		self.helpList.append((self["actions"], "InfobarActions", [("showMovies", _("view recordings..."))]))
		self.helpList.append((self["actions"], "InfobarActions", [("showRadio", _("hear radio..."))]))

		self["CurrentTime"] = Clock()

	def showTv(self):
		self.showTvChannelList(True)

	def showRadio(self):
		if config.usage.e1like_radio_mode.value:
			self.showRadioChannelList(True)
		else:
			self.session.open(ChannelSelectionRadio)

	def showMovies(self):
		self.session.openWithCallback(self.movieSelected, MovieSelection)

	def movieSelected(self, service):
		if service is not None:
			self.session.open(MoviePlayer, service)

class MoviePlayer(InfoBarShowHide, \
		InfoBarMenu, \
		InfoBarServiceName, InfoBarSeek, InfoBarShowMovies, InfoBarAudioSelection, HelpableScreen, InfoBarNotifications,
		InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarSimpleEventView,
		InfoBarSummarySupport, InfoBarTeletextPlugin, InfoBarSubtitleSupport, Screen):

	ENABLE_RESUME_SUPPORT = True
	ALLOW_SUSPEND = True
		
	def __init__(self, session, service):
		Screen.__init__(self, session)
		
		self["actions"] = HelpableActionMap(self, "MoviePlayerActions",
			{
				"leavePlayer": (self.leavePlayer, _("leave movie player..."))
			})
		
		for x in HelpableScreen, InfoBarShowHide, InfoBarMenu, \
				InfoBarServiceName, InfoBarSeek, InfoBarShowMovies, \
				InfoBarAudioSelection, InfoBarNotifications, InfoBarSimpleEventView, \
				InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, \
				InfoBarSummarySupport, InfoBarTeletextPlugin, InfoBarSubtitleSupport:
			x.__init__(self)

		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.playService(service)

	def leavePlayer(self):
		self.is_closing = True
		self.session.openWithCallback(self.leavePlayerConfirmed, MessageBox, _("Stop playing this movie?"))
	
	def leavePlayerConfirmed(self, answer):
		if answer == True:
			self.session.nav.playService(self.lastservice)
			self.close()
			
	def showMovies(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.openWithCallback(self.movieSelected, MovieSelection, ref)

	def movieSelected(self, service):
		if service is not None:
			self.session.nav.playService(service)
