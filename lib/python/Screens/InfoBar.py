from Screen import Screen

from Components.Clock import Clock
from Components.ActionMap import ActionMap
from Screens.AudioSelection import AudioSelection

from Screens.InfoBarGenerics import InfoBarVolumeControl, InfoBarShowHide, \
	InfoBarPowerKey, InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, \
	InfoBarEPG, InfoBarEvent, InfoBarServiceName, InfoBarPVR, InfoBarInstantRecord

from enigma import *

import time

class InfoBar(Screen, InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
	InfoBarEvent, InfoBarServiceName, InfoBarPVR, InfoBarInstantRecord):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		for x in InfoBarVolumeControl, InfoBarShowHide, InfoBarPowerKey, \
			InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, \
			InfoBarEvent, InfoBarServiceName, InfoBarPVR, InfoBarInstantRecord:
			x.__init__(self)

		self["actions"] = ActionMap( [ "InfobarActions" ], 
			{
				"showMovies": self.showMovies,
				#"quit": self.quit,
				"audioSelection": self.audioSelection,
			})

		self["CurrentTime"] = Clock()
		# ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		# Clock()

	def showMovies(self):
		self.session.open(MovieSelection)

	def audioSelection(self):
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		n = audio.getNumberOfTracks()
		if n > 0:
			self.session.open(AudioSelection, audio)
