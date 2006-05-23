from Screen import Screen

from Screens.MovieSelection import MovieSelection
from Screens.ChannelSelection import ChannelSelectionRadio
from Screens.MessageBox import MessageBox
from Screens.Ci import CiHandler
from ServiceReference import ServiceReference

from Components.Clock import Clock
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ServicePosition import ServicePosition, ServicePositionGauge

from Tools.Notifications import AddNotificationWithCallback

from Screens.InfoBarGenerics import InfoBarShowHide, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, \
	InfoBarEPG, InfoBarEvent, InfoBarServiceName, InfoBarSeek, InfoBarInstantRecord, \
	InfoBarAudioSelection, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, \
	InfoBarSubserviceSelection, InfoBarTuner, InfoBarShowMovies, InfoBarTimeshift,  \
	InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarSimpleEventView, \
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions

from Screens.HelpMenu import HelpableScreen, HelpMenu

from enigma import *

import time

class InfoBar(InfoBarShowHide,
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG,
	InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, 
	HelpableScreen, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish,
	InfoBarSubserviceSelection, InfoBarTuner, InfoBarTimeshift, InfoBarSeek,
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions, Screen):

	def __init__(self, session):
		Screen.__init__(self, session)

		CiHandler.setSession(session)

		self["actions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showMovies": (self.showMovies, _("Play recorded movies...")),
				"showRadio": (self.showRadio, _("Show the radio player..."))
			})
		
		for x in HelpableScreen, \
				InfoBarShowHide, \
				InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
				InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, \
				InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarSubserviceSelection, \
				InfoBarTuner, InfoBarTimeshift, InfoBarSeek, InfoBarSummarySupport, InfoBarTimeshiftState, \
				InfoBarTeletextPlugin, InfoBarExtensions:
			x.__init__(self)

		self.helpList.append((self["actions"], "InfobarActions", [("showMovies", "Watch a Movie...")]))
		self.helpList.append((self["actions"], "InfobarActions", [("showRadio", "Hear Radio...")]))

		self["CurrentTime"] = Clock()
		# ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)

	def showRadio(self):
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
		InfoBarSummarySupport, InfoBarTeletextPlugin, Screen):
		
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
				InfoBarSummarySupport, InfoBarTeletextPlugin:
			x.__init__(self)

		self["CurrentTime"] = ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		self["ElapsedTime"] = ServicePosition(self.session.nav, ServicePosition.TYPE_POSITION)
		self["PositionGauge"] = ServicePositionGauge(self.session.nav)
		
		# TYPE_LENGTH?
		
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.playService(service)

	def leavePlayer(self):
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
