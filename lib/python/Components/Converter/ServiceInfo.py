from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService
from Components.Element import cached

from os import path

WIDESCREEN = [1, 3, 4, 7, 8, 0xB, 0xC, 0xF, 0x10]

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
				"Framerate": (self.FRAMERATE, (iPlayableService.evVideoSizeChanged,iPlayableService.evUpdatedInfo,)),
				"TransferBPS": (self.TRANSFERBPS, (iPlayableService.evUpdatedInfo,)),
				"HasHBBTV": (self.HAS_HBBTV, (iPlayableService.evUpdatedInfo,iPlayableService.evHBBTVInfo,)),
				"AudioTracksAvailable": (self.AUDIOTRACKS_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
				"SubtitlesAvailable": (self.SUBTITLES_AVAILABLE, (iPlayableService.evUpdatedInfo,)),
				"Editmode": (self.EDITMODE, (iPlayableService.evUpdatedInfo,)),
				"IsStream": (self.IS_STREAM, (iPlayableService.evUpdatedInfo,)),
				"IsSD": (self.IS_SD, (iPlayableService.evVideoSizeChanged,)),
				"IsHD": (self.IS_HD, (iPlayableService.evVideoSizeChanged,)),
				"Is1080": (self.IS_1080, (iPlayableService.evVideoSizeChanged,)),
				"Is720": (self.IS_720, (iPlayableService.evVideoSizeChanged,)),
				"Is576": (self.IS_576, (iPlayableService.evVideoSizeChanged,)),
				"Is480": (self.IS_480, (iPlayableService.evVideoSizeChanged,)),
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

		video_height = None
		video_aspect = None
		if path.exists("/proc/stb/vmpeg/0/yres"):
			f = open("/proc/stb/vmpeg/0/yres", "r")
			try:
				video_height = int(f.read(),16)
			except:
				pass
			f.close()

		if path.exists("/proc/stb/vmpeg/0/aspect"):
			f = open("/proc/stb/vmpeg/0/aspect", "r")
			try:
				video_aspect = int(f.read())
			except:
				pass
			f.close()
		if not video_height:
			video_height = int(info.getInfo(iServiceInformation.sVideoHeight))
		if not video_aspect:
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
			return video_height < 720
		elif self.type == self.IS_HD:
			return video_height >= 720
		elif self.type == self.IS_1080:
			return video_height > 1000 and video_height <= 1080
		elif self.type == self.IS_720:
			return video_height > 700 and video_height <= 720
		elif self.type == self.IS_576:
			return video_height > 500 and video_height <= 576
		elif self.type == self.IS_480:
			return video_height > 0 and video_height <= 480
		return False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

		if self.type == self.XRES:
			video_width = None
			if path.exists("/proc/stb/vmpeg/0/xres"):
				f = open("/proc/stb/vmpeg/0/xres", "r")
				try:
					video_width = int(f.read(),16)
				except:
					pass
				f.close()
			if not video_width:
				try:
					video_width = int(self.getServiceInfoString(info, iServiceInformation.sVideoWidth))
				except:
					return ""
			return "%d" % video_width
		elif self.type == self.YRES:
			video_height = None
			if path.exists("/proc/stb/vmpeg/0/yres"):
				f = open("/proc/stb/vmpeg/0/yres", "r")
				try:
					video_height = int(f.read(),16)
				except:
					pass
				f.close()
			if not video_height:
				try:
					video_height = int(self.getServiceInfoString(info, iServiceInformation.sVideoHeight))
				except:
					return ""
			return "%d" % video_height
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
			video_rate = None
			if path.exists("/proc/stb/vmpeg/0/framerate"):
				f = open("/proc/stb/vmpeg/0/framerate", "r")
				try:
					video_rate = int(f.read())
				except:
					pass
				f.close()
			if not video_rate:
				video_rate = int(self.getServiceInfoString(info, iServiceInformation.sFrameRate))
			return video_rate, lambda x: "%d fps" % ((x+500)/1000)
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
			video_width = None
			if path.exists("/proc/stb/vmpeg/0/xres"):
				f = open("/proc/stb/vmpeg/0/xres", "r")
				try:
					video_width = int(f.read(),16)
				except:
					video_width = None
				f.close()
			if not video_width:
				video_width = info.getInfo(iServiceInformation.sVideoWidth)
			return str(video_width)
		elif self.type == self.YRES:
			video_height = None
			if path.exists("/proc/stb/vmpeg/0/yres"):
				f = open("/proc/stb/vmpeg/0/yres", "r")
				try:
					video_height = int(f.read(),16)
				except:
					video_height = None
				f.close()
			if not video_height:
				video_height = info.getInfo(iServiceInformation.sVideoHeight)
			return str(video_height)
		elif self.type == self.FRAMERATE:
			video_rate = None
			if path.exists("/proc/stb/vmpeg/0/framerate"):
				f = open("/proc/stb/vmpeg/0/framerate", "r")
				try:
					video_rate = f.read()
				except:
					pass
				f.close()
			if not video_rate:
				video_rate = info.getInfo(iServiceInformation.sFrameRate)
			return str(video_rate)

		return -1

	value = property(getValue)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)
