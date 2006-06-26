from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService

class ServiceInfo(Converter, object):
	HAS_TELETEXT = 0
	IS_MULTICHANNEL = 1
	IS_CRYPTED = 2
	IS_WIDESCREEN = 3
	SUBSERVICES_AVAILABLE = 4

	def __init__(self, type, *args, **kwargs):
		Converter.__init__(self)
		self.type = {
				"HasTelext": self.HAS_TELETEXT,
				"IsMultichannel": self.IS_MULTICHANNEL,
				"IsCrypted": self.IS_CRYPTED,
				"IsWidescreen": self.IS_WIDESCREEN,
				"SubservicesAvailable": self.SUBSERVICES_AVAILABLE,
			}[type]

		self.interesting_events = {
				self.HAS_TELETEXT: [iPlayableService.evEnd, iPlayableService.evUpdatedInfo],
				self.IS_MULTICHANNEL: [iPlayableService.evUpdatedInfo, iPlayableService.evEnd],
				self.IS_CRYPTED: [iPlayableService.evUpdatedInfo, iPlayableService.evEnd],
				self.IS_WIDESCREEN: [iPlayableService.evUpdatedEventInfo, iPlayableService.evEnd],
				self.SUBSERVICES_AVAILABLE: [iPlayableService.evUpdatedEventInfo, iPlayableService.evEnd]
			}[self.type]

	def getServiceInfoValue(self, info, what):
		v = info.getInfo(what)
		if v != -2:
			return "N/A"
		return info.getInfoString(what)

	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return False
		
		if self.type == self.HAS_TELETEXT:
			tpid = info.getInfo(iServiceInformation.sTXTPID)
			return tpid != -1
		elif self.type == self.IS_MULTICHANNEL:
			# FIXME. but currently iAudioTrackInfo doesn't provide more information.
			audio = service.audioTracks()
			if audio:
				n = audio.getNumberOfTracks()
				for x in range(n):
					i = audio.getTrackInfo(x)
					description = i.getDescription();
					if description.find("AC3") != -1 or description.find("DTS") != -1:
						return True
			return False
		elif self.type == self.IS_CRYPTED:
			return info.getInfo(iServiceInformation.sIsCrypted) == 1
		elif self.type == self.IS_WIDESCREEN:
			return info.getInfo(iServiceInformation.sAspect) in [3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]
		elif self.type == self.SUBSERVICES_AVAILABLE:
			subservices = service.subServices()
			return subservices and subservices.getNumberOfSubservices() > 0

	boolean = property(getBoolean)
