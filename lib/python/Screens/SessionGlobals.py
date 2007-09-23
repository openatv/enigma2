from Screens.Screen import Screen
from Components.Sources.CurrentService import CurrentService
from Components.Sources.EventInfo import EventInfo
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.Source import Source

class SessionGlobals(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["CurrentService"] = CurrentService(self.session.nav)
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.NOW)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.NEXT)
		self["FrontendStatus"] = FrontendStatus(service_source = self.session.nav.getCurrentService)
		self["VideoPicture"] = Source()
