from Screen import Screen

from Screens.MovieSelection import MovieSelection
from Screens.MessageBox import MessageBox

from Components.Clock import Clock
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ServicePosition import ServicePosition

from Tools.Notifications import AddNotificationWithCallback

from Screens.InfoBarGenerics import InfoBarVolumeControl, InfoBarShowHide, \
	InfoBarPowerKey, InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, \
	InfoBarEPG, InfoBarEvent, InfoBarServiceName, InfoBarPVR, InfoBarInstantRecord, \
	InfoBarAudioSelection, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, \
	InfoBarSubserviceSelection, InfoBarTuner

from Screens.HelpMenu import HelpableScreen, HelpMenu

from enigma import *

import time

class InfoBar(Screen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey,
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG,
	InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, 
	HelpableScreen, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish,
	InfoBarSubserviceSelection, InfoBarTuner):

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showMovies": (self.showMovies, _("Play recorded movies..."))
			})
		
		for x in HelpableScreen, \
				InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
				InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
				InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection, \
				InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarSubserviceSelection, InfoBarTuner:
			x.__init__(self)

		self.helpList.append((self["actions"], "InfobarActions", [("showMovies", "Watch a Movie...")]))

		self["CurrentTime"] = Clock()

	def showMovies(self):
		self.session.openWithCallback(self.movieSelected, MovieSelection)

	def movieSelected(self, service):
		if service is not None:
			self.session.open(MoviePlayer, service)

class MoviePlayer(Screen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
		InfoBarMenu, \
		InfoBarServiceName, InfoBarPVR, InfoBarAudioSelection, HelpableScreen, InfoBarNotifications):
		
	def __init__(self, session, service):
		Screen.__init__(self, session)
		
		self["actions"] = HelpableActionMap(self, "MoviePlayerActions",
			{
				"leavePlayer": (self.leavePlayer, _("leave movie player..."))
			})
		
		for x in HelpableScreen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, InfoBarMenu, InfoBarServiceName, InfoBarPVR, InfoBarAudioSelection, InfoBarNotifications:
			x.__init__(self)

		self["CurrentTime"] = ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.playService(service)

	def leavePlayer(self):
		self.session.openWithCallback(self.leavePlayerConfirmed, MessageBox, _("Stop playing this movie?"))
	
	def leavePlayerConfirmed(self, answer):
		if answer == True:
			self.session.nav.playService(self.lastservice)
			self.close()
