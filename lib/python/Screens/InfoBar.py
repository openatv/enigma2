from Tools.Profile import profile
from Tools.BoundFunction import boundFunction

# workaround for required config entry dependencies.
import Screens.MovieSelection

from Screen import Screen
from Screens.MessageBox import MessageBox

profile("LOAD:enigma")
import enigma

profile("LOAD:InfoBarGenerics")
from Screens.InfoBarGenerics import InfoBarShowHide, \
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarRdsDecoder, \
	InfoBarEPG, InfoBarSeek, InfoBarInstantRecord, InfoBarRedButton, InfoBarTimerButton, InfoBarVmodeButton, \
	InfoBarAudioSelection, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarUnhandledKey, \
	InfoBarSubserviceSelection, InfoBarShowMovies, InfoBarTimeshift,  \
	InfoBarServiceNotifications, InfoBarPVRState, InfoBarCueSheetSupport, InfoBarSimpleEventView, \
	InfoBarSummarySupport, InfoBarMoviePlayerSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions, \
	InfoBarSubtitleSupport, InfoBarPiP, InfoBarPlugins, InfoBarServiceErrorPopupSupport, InfoBarJobman, InfoBarPowersaver, \
	setResumePoint, delResumePoint

profile("LOAD:InitBar_Components")
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase

profile("LOAD:HelpableScreen")
from Screens.HelpMenu import HelpableScreen

class InfoBar(InfoBarBase, InfoBarShowHide,
	InfoBarNumberZap, InfoBarChannelSelection, InfoBarMenu, InfoBarEPG, InfoBarRdsDecoder,
	InfoBarInstantRecord, InfoBarAudioSelection, InfoBarRedButton, InfoBarTimerButton, InfoBarVmodeButton,
	HelpableScreen, InfoBarAdditionalInfo, InfoBarNotifications, InfoBarDish, InfoBarUnhandledKey,
	InfoBarSubserviceSelection, InfoBarTimeshift, InfoBarSeek, InfoBarCueSheetSupport,
	InfoBarSummarySupport, InfoBarTimeshiftState, InfoBarTeletextPlugin, InfoBarExtensions,
	InfoBarPiP, InfoBarPlugins, InfoBarSubtitleSupport, InfoBarServiceErrorPopupSupport, InfoBarJobman, InfoBarPowersaver,
	Screen):
	
	ALLOW_SUSPEND = True
	instance = None

	def __init__(self, session):
		Screen.__init__(self, session)
		self["actions"] = HelpableActionMap(self, "InfobarActions",
			{
				"showMovies": (self.showMovies, _("Play recorded movies...")),
				"toogleTvRadio": (self.toogleTvRadio, _("toggels betwenn tv and radio...")),
				"openTimerList": (self.openTimerList, _("Show the tv player...")),
				"showMediaPlayer": (self.showMediaPlayer, _("Show the med
