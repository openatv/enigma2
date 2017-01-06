from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached
from Tools.Transponder import ConvertToHumanReadable

WIDESCREEN = [3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]

class ServiceInfo(Converter, object):
	HAS_TELETEXT = 1
	IS_MULTICHANNEL = 2
	AUDIO_STEREO = 3
	IS_CRYPTED = 4
	IS_WIDESCREEN = 5
	IS_NOT_WIDESCREEN = 6
	SUBSERVICES_AVAILABLE = 7
	XRES = 8
	YRES = 9
	APID = 10
	VPID = 11
	PCRPID = 12
	PMTPID = 13
	TXTPID = 14
	TSID = 15
	ONID = 16
	SID = 17
	FRAMERATE = 18
	TRANSFERBPS = 19
	HAS_HBBTV = 20
	AUDIOTRACKS_AVAILABLE = 21
	SUBTITLES_AVAILABLE = 22
	EDITMODE = 23
	IS_STREAM = 24
	IS_SD = 25
	IS_HD = 26
	IS_1080 = 27
	IS_720 = 28
	IS_576 = 29
	IS_480 = 30
	IS_4K = 31
	FREQ_INFO = 32
	PROGRESSIVE = 33
	VIDEO_INFO = 34

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
			"HasTelext": (self.HAS_TELETEXT, (iPlayableService.evUpdatedInfo,)),
			"IsMultichannel": (self.IS_MULTICHANNEL, (iPlayableService.evUpdatedInfo,)),
			"IsStereo": (self.AUDIO_STEREO, (iPlayableService.evUpdatedInfo,)),
			"IsCrypted": (self.IS_CRYPTED, (iPlayableService.evUpdatedInfo,)),
			"IsWidescreen": (self.IS_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
			"IsNotWidescreen": (self.IS_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
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
			"Framerate": (self.FRAMERATE, (iPlayableService.evVideoFramerateChanged, iPlayableService.evUpdatedInfo,)),
			"Progressive": (self.PROGRESSIVE, (iPlayableService.evVideoProgressiveChanged, iPlayableService.evUpdatedInfo,)),
			"VideoInfo": (self.VIDEO_INFO, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoFramerateChanged, iPlayableService.evVideoProgressiveChanged, iPlayableService.evUpdatedInfo,)),
			"TransferBPS": (self.TRANSFERBPS, (iPlayableService.evUpdatedInfo,)),
			"HasHBBTV": (self.HAS_HBBTV, (iPlayableService.evUpdatedInfo, iPlayableService.evHBBTVInfo,)),
			"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			"Freq_Info": (self.FREQ_INFO, (iPlayableService.evUpdatedInfo,)),
			"Editmode": (self.EDITMODE, (iPlayableService.evUpdatedInfo,)),
			"IsStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo,)),
			"IsSD": (self.IS_SD, (iPlayableService.evVideoSizeChanged,)),
			"IsHD": (self.IS_HD, (iPlayableService.evVideoSizeChanged,)),
			"Is1080": (self.IS_1080, (iPlayableService.evVideoSizeChanged,)),
			"Is720": (self.IS_720, (iPlayableService.evVideoSizeChanged,)),
			"Is576": (self.IS_576, (iPlayableService.evVideoSizeChanged,)),
			"Is480": (self.IS_480, (iPlayableService.evVideoSizeChanged,)),
			"Is4K": (self.IS_4K, (iPlayableService.evVideoSizeChanged,)),
		}[type]

	def getServiceInfoString(self, info, what, convert=lambda x: "%d" % x):
		v = info.getInfo(what)
		if v == -1:
			return "N/A"
		if v == -2:
			return info.getInfoString(what)
		return convert(v)

	def _getProcVal(self, pathname, base=10):
		val = None
		try:
			f = open(pathname, "r")
			val = int(f.read(), base)
			f.close()
			if val >= 2 ** 31:
				val -= 2 ** 32
		except Exception, e:
			pass
		return val

	def _getVal(self, pathname, info, infoVal, base=10):
		val = self._getProcVal(pathname, base=base)
		return val if val is not None else info.getInfo(infoVal)

	def _getValInt(self, pathname, info, infoVal, base=10, default=-1):
		val = self._getVal(pathname, info, infoVal, base)
		return val if val is not None else default

	def _getValStr(self, pathname, info, infoVal, base=10, convert=lambda x: "%d" % x):
		val = self._getProcVal(pathname, base=base)
		return convert(val) if val is not None else self.getServiceInfoString(info, infoVal, convert)

	def _getVideoHeight(self, info):
		return self._getValInt("/proc/stb/vmpeg/0/yres", info, iServiceInformation.sVideoHeight, base=16)

	def _getVideoHeightStr(self, info, convert=lambda x: "%d" % x if x > 0 else "?"):
		return self._getValStr("/proc/stb/vmpeg/0/yres", info, iServiceInformation.sVideoHeight, base=16, convert=convert)

	def _getVideoWidth(self, info):
		return self._getValInt("/proc/stb/vmpeg/0/xres", info, iServiceInformation.sVideoWidth, base=16)

	def _getVideoWidthStr(self, info, convert=lambda x: "%d" % x if x > 0 else "?"):
		return self._getValStr("/proc/stb/vmpeg/0/xres", info, iServiceInformation.sVideoWidth, base=16, convert=convert)

	def _getFrameRate(self, info):
		return self._getValInt("/proc/stb/vmpeg/0/framerate", info, iServiceInformation.sFrameRate)

	def _getFrameRateStr(self, info, convert=lambda x: "%d" % x if x > 0 else ""):
		return self._getValStr("/proc/stb/vmpeg/0/framerate", info, iServiceInformation.sFrameRate, convert=convert)

	def _getProgressive(self, info):
		return self._getValInt("/proc/stb/vmpeg/0/progressive", info, iServiceInformation.sProgressive, default=0)

	def _getProgressiveStr(self, info, convert=lambda x: "" if x else "i"):
		return self._getValStr("/proc/stb/vmpeg/0/progressive", info, iServiceInformation.sProgressive, convert=convert)

	@cached
	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return False
		video_height = None
		video_aspect = None
		video_height = self._getVideoHeight(info)
		video_aspect = info.getInfo(iServiceInformation.sAspect)
		if self.type == self.HAS_TELETEXT:
			tpid = info.getInfo(iServiceInformation.sTXTPID)
			return tpid != -1
		elif self.type in (self.IS_MULTICHANNEL, self.AUDIO_STEREO):
			# FIXME. but currently iAudioTrackInfo doesn't provide more information.
			audio = service.audioTracks()
			if audio:
				n = audio.getNumberOfTracks()
				idx = 0
				while idx < n:
					i = audio.getTrackInfo(idx)
					description = i.getDescription()
					if description in ("AC3", "AC-3", "DTS"):
						if self.type == self.IS_MULTICHANNEL:
							return True
						elif self.type == self.AUDIO_STEREO:
							return False
					idx += 1
				if self.type == self.IS_MULTICHANNEL:
					return False
				elif self.type == self.AUDIO_STEREO:
					return True
			return False
		elif self.type == self.IS_CRYPTED:
			return info.getInfo(iServiceInformation.sIsCrypted) == 1
		elif self.type == self.IS_WIDESCREEN:
			return video_aspect in WIDESCREEN
		elif self.type == self.IS_NOT_WIDESCREEN:
			return video_aspect not in WIDESCREEN
		elif self.type == self.SUBSERVICES_AVAILABLE:
			subservices = service.subServices()
			return bool(subservices) and subservices.getNumberOfSubservices() > 0
		elif self.type == self.HAS_HBBTV:
			return info.getInfoString(iServiceInformation.sHBBTVUrl) != ""
		elif self.type == self.AUDIOTRACKS_AVAILABLE:
			audio = service.audioTracks()
			return bool(audio) and audio.getNumberOfTracks() > 1
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
			return video_height < 720
		elif self.type == self.IS_HD:
			return video_height >= 720 and video_height < 2160
		elif self.type == self.IS_1080:
			return video_height > 1000 and video_height <= 1080
		elif self.type == self.IS_720:
			return video_height > 700 and video_height <= 720
		elif self.type == self.IS_576:
			return video_height > 500 and video_height <= 576
		elif self.type == self.IS_480:
			return video_height > 0 and video_height <= 480
		elif self.type == self.IS_4K:
			return video_height >= 2100
		elif self.PROGRESSIVE:
			return bool(self._getProgressive(info))
		return False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""
		if self.type == self.XRES:
			return self._getVideoWidthStr(info)
		elif self.type == self.YRES:
			return self._getVideoHeightStr(info)
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
			return self._getFrameRateStr(info, convert=lambda x: "%d fps" % ((x + 500) / 1000))
		elif self.type == self.PROGRESSIVE:
			return self._getProgressiveStr(info)
		elif self.type == self.TRANSFERBPS:
			return self.getServiceInfoString(info, iServiceInformation.sTransferBPS, lambda x: "%d kB/s" % (x / 1024))
		elif self.type == self.HAS_HBBTV:
			return info.getInfoString(iServiceInformation.sHBBTVUrl)
		elif self.type == self.FREQ_INFO:
			feinfo = service.frontendInfo()
			if feinfo is None:
				return ""
			feraw = feinfo.getAll(False)
			if feraw is None:
				return ""
			fedata = ConvertToHumanReadable(feraw)
			if fedata is None:
				return ""
			frequency = fedata.get("frequency")
			sr_txt = "Sr:"
			polarization = fedata.get("polarization_abbreviation")
			if polarization is None:
				polarization = ""
			symbolrate = str(int(fedata.get("symbol_rate", 0)))
			if symbolrate == "0":
				sr_txt = ""
				symbolrate = ""
			fec = fedata.get("fec_inner")
			if fec is None:
				fec = ""
			out = "Freq: %s %s %s %s %s" % (frequency, polarization, sr_txt, symbolrate, fec)
			return out
		elif self.type == self.VIDEO_INFO:
			progressive = self._getProgressiveStr(info)
			fieldrate = self._getFrameRate(info)
			if fieldrate > 0:
				if progressive == 'i':
					fieldrate *= 2
				fieldrate = "%dHz" % ((fieldrate + 500) / 1000,)
			else:
				fieldrate = ""
			return "%sx%s%s %s" % (self._getVideoWidthStr(info), self._getVideoHeightStr(info), progressive, fieldrate)
		return ""

	text = property(getText)

	@cached
	def getValue(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return -1
		if self.type == self.XRES:
			return str(self._getVideoWidth(info))
		elif self.type == self.YRES:
			return str(self._getVideoHeight(info))
		elif self.type == self.FRAMERATE:
			return str(self._getFrameRate(self, info))
		return -1

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
