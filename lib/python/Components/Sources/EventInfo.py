from __future__ import absolute_import
from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService, iServiceInformation, eServiceReference, eEPGCache
from Components.Sources.Source import Source

# Fake eServiceEvent to fill Event_Now and Event_Next in Infobar for Streams
#
# from enigma import eServiceEvent
class pServiceEvent(object):
	NOW = 0
	NEXT = 1

	def __init__(self, info, now_or_next):
		self.now_or_next = now_or_next

		self.m_EventNameNow = ""
		self.m_EventNameNext = ""
		self.m_ShortDescriptionNow = ""
		self.m_ShortDescriptionNext = ""
		self.m_ExtendedDescriptionNow = ""
		self.m_ExtendedDescriptionNext = ""
		
		sTagTitle = info.getInfoString(iServiceInformation.sTagTitle)
		if sTagTitle:
			sTagTitleList = sTagTitle.split(" - ")
			element1 = sTagTitleList[0] if len(sTagTitleList) >= 1 else ""
			element2 = sTagTitleList[1] if len(sTagTitleList) >= 2 else ""
			element3 = sTagTitleList[2] if len(sTagTitleList) >= 3 else ""
			if element3 == "":
				self.m_EventNameNow = element1
				self.m_EventNameNext = element2
			if element3 != "":
				self.m_EventNameNow = element1 + " - " + element2
				self.m_EventNameNext = element3

		sTagGenre = info.getInfoString(iServiceInformation.sTagGenre)
		if sTagGenre:
			element4 = sTagGenre
			self.m_ShortDescriptionNow = element4

		sTagOrganization = info.getInfoString(iServiceInformation.sTagOrganization)
		if sTagOrganization:
			element5 = sTagOrganization
			self.m_ExtendedDescriptionNow = element5

		sTagLocation = info.getInfoString(iServiceInformation.sTagLocation)
		if sTagLocation:
			element6 = sTagLocation
			self.m_ExtendedDescriptionNow += "\n\n" + element6


	def getEventName(self):
		return self.m_EventNameNow if self.now_or_next == self.NOW else self.m_EventNameNext
	
	def getShortDescription(self):
		return self.m_ShortDescriptionNow if self.now_or_next == self.NOW else self.m_ShortDescriptionNext

	def getExtendedDescription(self):
		return self.m_ExtendedDescriptionNow if self.now_or_next == self.NOW else self.m_ExtendedDescriptionNext

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
				if not ret and refstr.split(':')[0] in ['4097', '5001', '5002', '5003']: # No EPG Try to get Meta
					ev = pServiceEvent(info, self.now_or_next)
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
