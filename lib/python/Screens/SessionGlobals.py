from Screens.Screen import Screen
from Components.Sources.CurrentService import CurrentService
from Components.Sources.EventInfo import EventInfo
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.FrontendInfo import FrontendInfo
from Components.Sources.Source import Source
from Components.Sources.TunerInfo import TunerInfo
from Components.Sources.RecordState import RecordState
from Components.Renderer.FrontpanelLed import FrontpanelLed

class SessionGlobals(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["CurrentService"] = CurrentService(session.nav)
		self["Event_Now"] = EventInfo(session.nav, EventInfo.NOW)
		self["Event_Next"] = EventInfo(session.nav, EventInfo.NEXT)
		self["FrontendStatus"] = FrontendStatus(service_source = session.nav.getCurrentService)
		self["FrontendInfo"] = FrontendInfo(navcore = session.nav)
		self["VideoPicture"] = Source()
		self["TunerInfo"] = TunerInfo()
		self["RecordState"] = RecordState(session)
		FrontpanelLed().connect(self["RecordState"])
