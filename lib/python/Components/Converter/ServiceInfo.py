
from enigma import eAVControl, iPlayableService, iServiceInformation

from Components.Element import cached
from Components.Converter.Converter import Converter
# from Components.Converter.Poll import Poll
from Tools.Transponder import ConvertToHumanReadable

MODULE_NAME = __name__.split(".")[-1]
WIDESCREEN = [1, 3, 4, 7, 8, 11, 12, 15, 16]  # This is imported into InfoBarGenerics.py!


class ServiceInfo(Converter):
	APID = 0
	AUDIOTRACKS_AVAILABLE = 1
	EDITMODE = 2
	FRAMERATE = 3
	FREQUENCY_INFORMATION = 4
	HAS_HBBTV = 5
	HAS_TELETEXT = 6
	IS_1080 = 7
	IS_480 = 8
	IS_4K = 9
	IS_576 = 10
	IS_720 = 11
	IS_CRYPTED = 12
	IS_HD = 13
	IS_HDHDR = 14
	IS_HDR = 15
	IS_HDR10 = 16
	IS_HLG = 17
	IS_MULTICHANNEL = 18
	IS_NOT_WIDESCREEN = 19
	IS_SD = 20
	IS_SDR = 21
	IS_SD_AND_NOT_WIDESCREEN = 22
	IS_SD_AND_WIDESCREEN = 23
	IS_STEREO = 24
	IS_STREAM = 25
	IS_VIDEO_AVC = 26
	IS_VIDEO_HEVC = 27
	IS_VIDEO_MPEG2 = 28
	IS_WIDESCREEN = 29
	ONID = 30
	PCRPID = 31
	PMTPID = 32
	PROGRESSIVE = 33
	PROVIDER = 34
	REFERENCE = 35
	SID = 36
	SUBSERVICES_AVAILABLE = 37
	SUBTITLES_AVAILABLE = 38
	TRANSFERBPS = 39
	TSID = 40
	TXTPID = 41
	VIDEO_INFORMATION = 42
	VIDEO_SIZE = 43  # Temporary.
	VPID = 44
	XRES = 45
	YRES = 46

	VIDEO_INFO_WIDTH = 0
	VIDEO_INFO_HEIGHT = 1
	VIDEO_INFO_FRAME_RATE = 2
	VIDEO_INFO_PROGRESSIVE = 3
	VIDEO_INFO_ASPECT = 4
	VIDEO_INFO_GAMMA = 5

	def __init__(self, argument):
		Converter.__init__(self, argument)
		# Poll.__init__(self)
		# self.poll_interval = 10000
		# self.poll_enabled = True
		self.argument = argument
		self.token, self.interestingEvents = {
			"AudioPid": (self.APID, (iPlayableService.evUpdatedInfo,)),
			"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			"EditMode": (self.EDITMODE, (iPlayableService.evUpdatedInfo,)),
			"Editmode": (self.EDITMODE, (iPlayableService.evUpdatedInfo,)),
			"FrameRate": (self.FRAMERATE, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
			"Framerate": (self.FRAMERATE, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
			"FrequencyInfo": (self.FREQUENCY_INFORMATION, (iPlayableService.evUpdatedInfo,)),
			"Freq_Info": (self.FREQUENCY_INFORMATION, (iPlayableService.evUpdatedInfo,)),
			"HasHBBTV": (self.HAS_HBBTV, (iPlayableService.evUpdatedInfo, iPlayableService.evHBBTVInfo,)),
			"HasTeletext": (self.HAS_TELETEXT, (iPlayableService.evUpdatedInfo,)),
			"HasTelext": (self.HAS_TELETEXT, (iPlayableService.evUpdatedInfo,)),
			"Is1080": (self.IS_1080, (iPlayableService.evVideoSizeChanged,)),
			"Is480": (self.IS_480, (iPlayableService.evVideoSizeChanged,)),
			"Is4K": (self.IS_4K, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"Is576": (self.IS_576, (iPlayableService.evVideoSizeChanged,)),
			"Is720": (self.IS_720, (iPlayableService.evVideoSizeChanged,)),
			"IsCrypted": (self.IS_CRYPTED, (iPlayableService.evUpdatedInfo,)),
			"IsHD": (self.IS_HD, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsHDHDR": (self.IS_HDHDR, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsHDR": (self.IS_HDR, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsHDR10": (self.IS_HDR10, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsHLG": (self.IS_HLG, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsIPStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo,)),
			"IsMultichannel": (self.IS_MULTICHANNEL, (iPlayableService.evUpdatedInfo,)),
			"IsNotWidescreen": (self.IS_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
			"IsSD": (self.IS_SD, (iPlayableService.evVideoSizeChanged,)),
			# "IsSDAndNotWidescreen": (self.IS_SD_AND_NOT_WIDESCREEN, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
			# "IsSDAndWidescreen": (self.IS_SD_AND_WIDESCREEN, (iPlayableService.evVideoSizeChanged, iPlayableService.evUpdatedInfo)),
			"IsSDR": (self.IS_SDR, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoGammaChanged)),
			"IsStereo": (self.IS_STEREO, (iPlayableService.evUpdatedInfo,)),
			"IsStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo,)),
			# "IsVideoAVC": (self.IS_VIDEO_AVC, (iPlayableService.evUpdatedInfo,)),
			# "IsVideoHEVC": (self.IS_VIDEO_HEVC, (iPlayableService.evUpdatedInfo,)),
			# "IsVideoMPEG2": (self.IS_VIDEO_MPEG2, (iPlayableService.evUpdatedInfo,)),
			"IsWidescreen": (self.IS_WIDESCREEN, (iPlayableService.evVideoSizeChanged,)),
			"OnId": (self.ONID, (iPlayableService.evUpdatedInfo,)),
			"PcrPid": (self.PCRPID, (iPlayableService.evUpdatedInfo,)),
			"PmtPid": (self.PMTPID, (iPlayableService.evUpdatedInfo,)),
			"Progressive": (self.PROGRESSIVE, (iPlayableService.evVideoProgressiveChanged, iPlayableService.evUpdatedInfo)),
			# "Provider": (self.PROVIDER, self.getTextItem, (iPlayableService.evStart,)),
			# "Reference": (self.REFERENCE, self.getTextItem, (iPlayableService.evStart,)),
			"Sid": (self.SID, (iPlayableService.evUpdatedInfo,)),
			"SubservicesAvailable": (self.SUBSERVICES_AVAILABLE, (iPlayableService.evUpdatedEventInfo,)),
			"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
			"TransferBPS": (self.TRANSFERBPS, (iPlayableService.evUpdatedInfo,)),
			"TsId": (self.TSID, (iPlayableService.evUpdatedInfo,)),
			"TxtPid": (self.TXTPID, (iPlayableService.evUpdatedInfo,)),
			"VideoHeight": (self.YRES, (iPlayableService.evVideoSizeChanged,)),
			"VideoInfo": (self.VIDEO_INFORMATION, (iPlayableService.evVideoSizeChanged, iPlayableService.evVideoFramerateChanged, iPlayableService.evVideoProgressiveChanged, iPlayableService.evUpdatedInfo)),
			"VideoPid": (self.VPID, (iPlayableService.evUpdatedInfo,)),
			# "VideoSize": (self.VIDEO_SIZE, (iPlayableService.evVideoSizeChanged,)),
			"VideoWidth": (self.XRES, (iPlayableService.evVideoSizeChanged,)),
		}.get(argument)
		self.instanceInfoBarSubserviceSelection = None

	@cached
	def getBoolean(self):
		def isMultichannelAudio(invert):
			audio = service.audioTracks()
			if audio and audio.getNumberOfTracks():
				currentTrack = audio.getCurrentTrack()
				if currentTrack > -1:
					description = audio.getTrackInfo(currentTrack).getDescription()  # Some audio descriptions have 'audio' as additional value (e.g. "AC-3 audio").
					result = bool(description and description.split()[0] in ("AC3", "AC3+", "DTS", "DTS-HD", "AC4", "LPCM", "Dolby", "HE-AAC", "AAC+", "WMA"))
					if invert:
						result = not result
				else:
					result = False
			else:
				result = False
			return result

		result = False
		service = self.source.service
		info = service and service.info()
		if info:
			videoData = info.getInfoString(iServiceInformation.sVideoInfo) or "-1|-1|-1|-1|-1|-1"
			videoData = [int(x) for x in videoData.split("|")]
			videoWidth = videoData[self.VIDEO_INFO_WIDTH] if videoData[self.VIDEO_INFO_WIDTH] != -1 else eAVControl.getInstance().getResolutionX(0)
			videoHeight = videoData[self.VIDEO_INFO_HEIGHT] if videoData[self.VIDEO_INFO_HEIGHT] != -1 else eAVControl.getInstance().getResolutionY(0)
			videoAspect = videoData[self.VIDEO_INFO_ASPECT] if videoData[self.VIDEO_INFO_ASPECT] != -1 else eAVControl.getInstance().getAspect(0)
			videoGamma = videoData[self.VIDEO_INFO_GAMMA]
			match self.token:
				case self.AUDIOTRACKS_AVAILABLE:
					audio = service.audioTracks()
					result = audio and audio.getNumberOfTracks() > 1
				case self.EDITMODE:
					result = bool(hasattr(self.source, "editmode") and self.source.editmode)
				case self.HAS_HBBTV:
					result = info.getInfoString(iServiceInformation.sHBBTVUrl) != ""
				case self.HAS_TELETEXT:
					result = info.getInfo(iServiceInformation.sTXTPID) != -1
				case self.IS_1080:
					result = videoHeight > 1000 and videoHeight <= 1080
				case self.IS_480:
					result = videoHeight > 0 and videoHeight <= 480
				case self.IS_4K:
					result = videoHeight > 1500 and videoWidth <= 3840 and videoGamma < 1
				case self.IS_576:
					result = videoHeight > 500 and videoHeight <= 576
				case self.IS_720:
					result = videoHeight > 700 and videoHeight <= 720
				case self.IS_CRYPTED:
					result = info.getInfo(iServiceInformation.sIsCrypted) == 1
				case self.IS_HD:
					result = videoHeight > 700 and videoHeight <= 1080 and videoGamma < 1
				case self.IS_HDHDR:
					result = videoWidth > 720 and videoWidth < 1980 and videoGamma > 0
				case self.IS_HDR:
					result = videoWidth > 2160 and videoWidth <= 3840 and videoGamma == 1
				case self.IS_HDR10:
					result = videoWidth > 2160 and videoWidth <= 3840 and videoGamma == 2
				case self.IS_HLG:
					result = videoWidth > 2160 and videoWidth <= 3840 and videoGamma == 3
				case self.IS_MULTICHANNEL:
					result = isMultichannelAudio(False)
				case self.IS_NOT_WIDESCREEN:
					result = videoAspect not in WIDESCREEN
				case self.IS_SD:
					result = videoHeight < 720
				case self.IS_SDR:
					result = videoWidth > 2160 and videoWidth <= 3840 and videoGamma < 1
				case self.IS_SD_AND_NOT_WIDESCREEN:
					result = videoHeight < 720 and videoAspect not in WIDESCREEN
				case self.IS_SD_AND_WIDESCREEN:
					result = videoHeight < 720 and videoAspect in WIDESCREEN
				case self.IS_STEREO:
					result = isMultichannelAudio(True)
				case self.IS_STREAM:
					result = service.streamed() is not None
				case self.IS_VIDEO_AVC:
					result = info.getInfo(iServiceInformation.sVideoType) == 1
				case self.IS_VIDEO_HEVC:
					result = info.getInfo(iServiceInformation.sVideoType) == 7
				case self.IS_VIDEO_MPEG2:
					result = info.getInfo(iServiceInformation.sVideoType) == 0
				case self.IS_WIDESCREEN:
					result = videoAspect in WIDESCREEN
				case self.PROGRESSIVE:
					result = videoData[self.VIDEO_INFO_PROGRESSIVE] if videoData[self.VIDEO_INFO_PROGRESSIVE] != -1 else eAVControl.getInstance().getProgressive()
				case self.SUBSERVICES_AVAILABLE:
					if self.instanceInfoBarSubserviceSelection is None:
						from Screens.InfoBarGenerics import instanceInfoBarSubserviceSelection  # This must be here as the class won't be initialized at module load time.
						self.instanceInfoBarSubserviceSelection = instanceInfoBarSubserviceSelection
					if self.instanceInfoBarSubserviceSelection:
						result = self.instanceInfoBarSubserviceSelection.hasActiveSubservicesForCurrentService(info.getInfoString(iServiceInformation.sServiceref))
				case self.SUBTITLES_AVAILABLE:
					subtitle = service and service.subtitle()
					result = bool(subtitle and subtitle.getSubtitleList())
		# print(f"[ServiceInfo] DEBUG: Converter Boolean argument '{self.argument}' result is '{result}'{"." if isinstance(result, bool) else " TYPE MISMATCH!"}")
		return result

	boolean = property(getBoolean)

	@cached
	def getText(self):
		result = ""
		service = self.source.service
		info = service and service.info()
		if info:
			videoData = info.getInfoString(iServiceInformation.sVideoInfo) or "-1|-1|-1|-1|-1|-1"
			videoData = [int(x) for x in videoData.split("|")]
			videoWidth = videoData[self.VIDEO_INFO_WIDTH] if videoData[self.VIDEO_INFO_WIDTH] != -1 else eAVControl.getInstance().getResolutionX(0)
			videoHeight = videoData[self.VIDEO_INFO_HEIGHT] if videoData[self.VIDEO_INFO_HEIGHT] != -1 else eAVControl.getInstance().getResolutionY(0)
			frameRate = videoData[self.VIDEO_INFO_FRAME_RATE] if videoData[self.VIDEO_INFO_FRAME_RATE] != -1 else eAVControl.getInstance().getFrameRate(0)
			progressive = videoData[self.VIDEO_INFO_PROGRESSIVE] if videoData[self.VIDEO_INFO_PROGRESSIVE] != -1 else eAVControl.getInstance().getProgressive()
			progressive = "p" if progressive else "i"
			match self.token:
				case self.APID:
					result = info.getInfoString(iServiceInformation.sAudioPID)
				case self.FRAMERATE:
					result = f"{(frameRate + 500) // 1000} fps" if frameRate else _("N/A")
				case self.FREQUENCY_INFORMATION:
					feInfo = service.frontendInfo()
					if feInfo:
						feRaw = feInfo.getAll(False)
						if feRaw:
							feData = ConvertToHumanReadable(feRaw)
							if feData:
								srText = "Sr:"
								symbolRate = int(feData.get("symbol_rate", 0))
								if symbolRate == 0:
									srText = ""
									symbolRate = ""
								result = f"Freq: {feData.get("frequency")} {feData.get("polarization_abbreviation") or ""} {srText} {symbolRate} {feData.get("fec_inner") or ""}"
				case self.HAS_HBBTV:
					result = info.getInfoString(iServiceInformation.sHBBTVUrl)
				case self.ONID:
					result = info.getInfoString(iServiceInformation.sONID)
				case self.PCRPID:
					result = info.getInfoString(iServiceInformation.sPCRPID)
				case self.PMTPID:
					result = info.getInfoString(iServiceInformation.sPMTPID)
				case self.PROGRESSIVE:
					result = progressive
				case self.SID:
					result = f"{info.getInfo(iServiceInformation.sSID):04X}"
				case self.TRANSFERBPS:
					result = info.getInfoString(iServiceInformation.sTransferBPS, lambda x: f"{x // 1024} kB/s")
				case self.TSID:
					result = info.getInfoString(iServiceInformation.sTSID)
				case self.TXTPID:
					result = info.getInfoString(iServiceInformation.sTXTPID)
				case self.VIDEO_INFORMATION:
					if frameRate > 0:
						if progressive == "i":
							frameRate *= 2
						frameRate = f" {(frameRate + 500) // 1000}Hz"
					else:
						frameRate = ""
					result = f"{videoWidth}x{videoHeight}{progressive}{frameRate}" if videoWidth != -1 and videoHeight != -1 else ""
				case self.VPID:
					result = info.getInfoString(iServiceInformation.sVideoPID)
				case self.XRES:
					result = f"{videoWidth}"
				case self.YRES:
					result = f"{videoHeight}"
		# print(f"[ServiceInfo] DEBUG: Converter string argument '{self.argument}' result is '{result}'{"." if isinstance(result, str) else " TYPE MISMATCH!"}")
		return result

	text = property(getText)

	@cached
	def getValue(self):
		result = -1
		service = self.source.service
		info = service and service.info()
		if info:
			match self.token:
				case self.FRAMERATE:
					result = info.getInfo(iServiceInformation.sFrameRate)
					if result == -1:
						result = eAVControl.getInstance().getFrameRate(0)
				case self.XRES:
					result = info.getInfo(iServiceInformation.sVideoWidth)
					if result == -1:
						result = eAVControl.getInstance().getResolutionX(0)
				case self.YRES:
					result = info.getInfo(iServiceInformation.sVideoHeight)
					if result == -1:
						result = eAVControl.getInstance().getResolutionY(0)
		# print(f"[ServiceInfo] DEBUG: Converter value argument '{self.argument}' result is '{result}'{"." if isinstance(result, int) else " TYPE MISMATCH!"}")
		return result

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interestingEvents:
			Converter.changed(self, what)
