from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached

WIDESCREEN = [3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]

class ServiceInfo(Converter, object):
	HAS_TELETEXT = 0
	IS_MULTICHANNEL = 1
	IS_CRYPTED = 2
	IS_WIDESCREEN = 3
	SUBSERVICES_AVAILABLE = 4
	XRES = 5
	YRES = 6
	APID = 7
	VPID = 8
	PCRPID = 9
	PMTPID = 10
	TXTPID = 11
	TSID = 12
	ONID = 13
	SID = 14
	FRAMERATE = 15
	TRANSFERBPS = 16
	HAS_HBBTV = 17
	AUDIOTRACKS_AVAILABLE = 18
	SUBTITLES_AVAILABLE = 19
	EDITMODE = 20
	IS_STREAM = 21
	IS_SD = 22
	IS_HD = 23
	IS_SD_AND_WIDESCREEN = 24
	IS_SD_AND_NOT_WIDESCREEN = 25

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
				"HasTelext": (self.HAS_TELETEXT, (iPlayableService.evUpdatedInfo,)),
				"IsMultichannel": (self.IS_MULTICHANNEL, (iPlayableService.evUpdatedInfo,)),
				"IsCrypted": (self.IS_CRYPTED, (iPlayableService.evUpdatedInfo,)),
				"IsWidescreen": (self.IS_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
				"SubservicesAvailable": (self.SUBSERVICES_AVAILABLE, (iPlayableService.evUpdatedEventInfo,)),
				"VideoWidth": (self.XRES, (iPlayableService.evVideoSizeChanged,)),
				"VideoHeight": (self.YRES, (iPlayableService.evVideoSizeChanged,)),
				"AudioPid": (self.APID, (iPlayableService.evUpdatedInfo,)),
				"VideoPid": (self.VPID, (iPlayableService.evUpdatedInfo,)),
				"PcrPid": (self.PCRPID, (iPlayableService.evUpdatedInfo,)),
				"PmtPid": (self.PMTPID, (iPlayableService.evUpdatedInfo,)),
				"TxtPid": (self.TXTPID, (iPlayableService.evUpdatedInfo,)),
				"TsId": (self.TSID, (iPlayableService.evUpdatedInfo,)),
				"OnId": (self.ONID, (iPlayableService.evUpdatedInfo,)),
				"Sid": (self.SID, (iPlayableService.evUpdatedInfo,)),
				"Framerate": (self.FRAMERATE, (iPlayableService.evVideoSizeChanged,iPlayableService.evUpdatedInfo,)),
				"TransferBPS": (self.TRANSFERBPS, (iPlayableService.evUpdatedInfo,)),
				"HasHBBTV": (self.HAS_HBBTV, (iPlayableService.evUpdatedInfo,iPlayableService.evHBBTVInfo,)),
				"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
				"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
				"Editmode": (self.EDITMODE, (iPlayableService.evUpdatedInfo,)),
				"IsStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo,)),
				"IsSD": (self.IS_SD, (iPlayableService.evVideoSizeChanged,)),
				"IsHD": (self.IS_HD, (iPlayableService.evVideoSizeChanged,)),
				"IsSDAndWidescreen": (self.IS_SD_AND_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
				"IsSDAndNotWidescreen": (self.IS_SD_AND_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
			}[type]

	def getServiceInfoString(self, info, what, convert = lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return "N/A"
		if v == -2:
			return info.getInfoString(what)
		return convert(v)

	@cached
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
				idx = 0
				while idx < n:
					i = audio.getTrackInfo(idx)
					description = i.getDescription();
					if "AC3" in description or "AC-3" in description or "DTS" in description:
						return True
					idx += 1
			return False
		elif self.type == self.IS_CRYPTED:
			return info.getInfo(iServiceInformation.sIsCrypted) == 1
		elif self.type == self.IS_WIDESCREEN:
			return info.getInfo(iServiceInformation.sAspect) in WIDESCREEN
		elif self.type == self.SUBSERVICES_AVAILABLE:
			subservices = service.subServices()
			return subservices and subservices.getNumberOfSubservices() > 0
		elif self.type == self.HAS_HBBTV:
			return info.getInfoString(iServiceInformation.sHBBTVUrl) != ""
		elif self.type == self.AUDIOTRACKS_AVAILABLE:
			audio = service.audioTracks()
			return audio and audio.getNumberOfTracks() > 1
		elif self.type == self.SUBTITLES_AVAILABLE:
			subtitle = service and service.subtitle()
			subtitlelist = subtitle and subtitle.getSubtitleList()
			if subtitlelist:
				return len(subtitlelist) > 0
			return False
		elif self.type == self.EDITMODE:
			return hasattr(self.source, "editmode") and not not self.source.editmode
		elif self.type == self.IS_STREAM:
			return service.streamed() is not None
		elif self.type == self.IS_SD:
			return info.getInfo(iServiceInformation.sVideoHeight) < 720
		elif self.type == self.IS_HD:
			return info.getInfo(iServiceInformation.sVideoHeight) >= 720
		elif self.type == self.IS_SD_AND_WIDESCREEN:
			return info.getInfo(iServiceInformation.sVideoHeight) < 720 and info.getInfo(iServiceInformation.sAspect) in WIDESCREEN
		elif self.type == self.IS_SD_AND_NOT_WIDESCREEN:
			return info.getInfo(iServiceInformation.sVideoHeight) < 720 and info.getInfo(iServiceInformation.sAspect) not in WIDESCREEN
		return False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

		if self.type == self.XRES:
			return self.getServiceInfoString(info, iServiceInformation.sVideoWidth)
		elif self.type == self.YRES:
			return self.getServiceInfoString(info, iServiceInformation.sVideoHeight)
		elif self.type == self.APID:
			return self.getServiceInfoString(info, iServiceInformation.sAudioPID)
		elif self.type == self.VPID:
			return self.getServiceInfoString(info, iServiceInformation.sVideoPID)
		elif self.type == self.PCRPID:
			return self.getServiceInfoString(info, iServiceInformation.sPCRPID)
		elif self.type == self.PMTPID:
			return self.getServiceInfoString(info, iServiceInformation.sPMTPID)
		elif self.type == self.TXTPID:
			return self.getServiceInfoString(info, iServiceInformation.sTXTPID)
		elif self.type == self.TSID:
			return self.getServiceInfoString(info, iServiceInformation.sTSID)
		elif self.type == self.ONID:
			return self.getServiceInfoString(info, iServiceInformation.sONID)
		elif self.type == self.SID:
			return self.getServiceInfoString(info, iServiceInformation.sSID)
		elif self.type == self.FRAMERATE:
			return self.getServiceInfoString(info, iServiceInformation.sFrameRate, lambda x: "%d fps" % ((x+500)/1000))
		elif self.type == self.TRANSFERBPS:
			return self.getServiceInfoString(info, iServiceInformation.sTransferBPS, lambda x: "%d kB/s" % (x/1024))
		elif self.type == self.HAS_HBBTV:
			return info.getInfoString(iServiceInformation.sHBBTVUrl)
		return ""

	text = property(getText)

	@cached
	def getValue(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return -1

		if self.type == self.XRES:
			return info.getInfo(iServiceInformation.sVideoWidth)
		if self.type == self.YRES:
			return info.getInfo(iServiceInformation.sVideoHeight)
		if self.type == self.FRAMERATE:
			return info.getInfo(iServiceInformation.sFrameRate)

		return -1

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
