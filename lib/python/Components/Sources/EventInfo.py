from __future__ import absolute_import
from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService, iServiceInformation, eServiceReference, eEPGCache
from Components.Sources.Source import Source

# Fake eServiceEvent to fill EPG data for Streams
class eServiceEvent(object):
	def __init__(self, info):
		EventName = info.getInfoString(iServiceInformation.sTagTitle)
		self.m_EventName = None
		if EventName:
			self.m_EventName = EventName
		self.m_ShortDescription = ""
		self.m_ExtendedDescriptionation = ""

	def getEventName(self):
		return self.m_EventName
	
	def getShortDescription(self):
		return self.m_ShortDescription

	def getExtendedDescriptionation(self):
		return self.m_ExtendedDescriptionation

	def getBeginTime(self):
		return 0

	def getEndTime(self):
		return 0

	def getDuration(self):
		return 0

	def getEventId(self):
		return 0

	def getExtraEventData(self):
		return None

	def getBeginTimeString(self):
		return ""

class EventInfo(PerServiceBase, Source, object):
	NOW = 0
	NEXT = 1

	def __init__(self, navcore, now_or_next):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedEventInfo: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)
		self.now_or_next = now_or_next
		self.epgQuery = eEPGCache.getInstance().lookupEventTime

	@cached
	def getEvent(self):
		service = self.navcore.getCurrentService()
		info = service and service.info()
		ret = info and info.getEvent(self.now_or_next)
		if info:
			if not ret or ret.getEventName() == "":
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				ret = self.epgQuery(eServiceReference(refstr), -1, self.now_or_next and 1 or 0)
				if self.now_or_next == 0 and not ret and refstr.split(':')[0] in ['4097', '5001', '5002', '5003']: # No EPG Try to get Meta
					ev = eServiceEvent(info)
					if ev.getEventName:
						return ev
		return ret

	event = property(getEvent)

	def gotEvent(self, what):
		if what == iPlayableService.evEnd:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))

	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)
