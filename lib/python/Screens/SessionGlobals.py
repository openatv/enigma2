from enigma import iPlayableService
from Screens.Screen import Screen
from Components.Sources.CurrentService import CurrentService
from Components.Sources.EventInfo import EventInfo
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.FrontendInfo import FrontendInfo
from Components.Sources.Source import Source
from Components.Sources.Misc import Misc

class SessionGlobals(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["CurrentService"] = CurrentService(session.nav)
		self["Event_Now"] = EventInfo(session.nav, EventInfo.NOW)
		self["Event_Next"] = EventInfo(session.nav, EventInfo.NEXT)
		self["FrontendStatus"] = FrontendStatus(service_source = session.nav.getCurrentService)
		self["FrontendInfo"] = FrontendInfo(service_source = session.nav.getCurrentService)
		self["VideoPicture"] = Source()
		self["GlobalInfo"] = Misc(session)
		session.nav.event.append(self.serviceEvent)
		self.service_state = 0

	def serviceEvent(self, evt):
		if evt == iPlayableService.evStart:
			self.service_state = 1
		elif evt == iPlayableService.evEnd:
			self.service_state = 0
		elif evt == iPlayableService.evUpdatedInfo and self.service_state == 1:
			self.service_state = 2
			self["FrontendInfo"].updateFrontendData()
