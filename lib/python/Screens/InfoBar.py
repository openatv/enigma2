from Screen import Screen

from Screens.MovieSelection import MovieSelection
from Screens.MessageBox import MessageBox

from Components.Clock import Clock
from Components.ActionMap import ActionMap
from Components.ServicePosition import ServicePosition

from Screens.InfoBarGenerics import InfoBarVolumeControl, InfoBarShowHide, \
	InfoBarPowerKey, InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, \
	InfoBarEPG, InfoBarEvent, InfoBarServiceName, InfoBarPVR, InfoBarInstantRecord, \
	InfoBarAudioSelection

from enigma import *

import time

class InfoBar(Screen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
	InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection):

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap( [ "InfobarActions" ],
			{
				"showMovies": self.showMovies,
			})
		
		for x in InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
			InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
			InfoBarEvent, InfoBarServiceName, InfoBarInstantRecord, InfoBarAudioSelection:
			x.__init__(self)

		self["CurrentTime"] = Clock()

	def showMovies(self):
		self.session.openWithCallback(self.movieSelected, MovieSelection)
	
	def movieSelected(self, service):
		if service is not None:
			self.session.open(MoviePlayer, service)

class MoviePlayer(Screen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
		InfoBarMenu, \
		InfoBarServiceName, InfoBarPVR, InfoBarAudioSelection):
		
	def __init__(self, session, service):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap( [ "MoviePlayerActions" ],
			{
				"leavePlayer": self.leavePlayer
			})
		
		for x in InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, InfoBarMenu, InfoBarServiceName, InfoBarPVR, InfoBarAudioSelection:
			x.__init__(self)

		self["CurrentTime"] = Clock()
		# ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		
		self.lastservice = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.playService(service)

	def leavePlayer(self):
		self.session.openWithCallback(self.leavePlayerConfirmed, MessageBox, "Stop playing this movie?")
	
	def leavePlayerConfirmed(self, answer):
		if answer == True:
			self.session.nav.playService(self.lastservice)
			self.close()
