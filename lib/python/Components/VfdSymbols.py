from os.path import exists, join
from twisted.internet import threads

from enigma import eTimer, iPlayableService, iServiceInformation, getVFDSymbolsPoll

from Components.config import config
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
import Screens.Standby
from Tools.Directories import fileWriteLine

MODULE_NAME = __name__.split(".")[-1]

BOX_TYPE = BoxInfo.getItem("machinebuild")
MODEL = BoxInfo.getItem("model")


class VFDSymbolsUpdater:
	def __init__(self, session):
		self.session = session
		self.blink = False
		self.led = False
		self.ledConfig = self.findProcFiles()
		self.recMode, self.recPath = self.getRecModes()
		self.onClose = []  # This is needed for ServiceEventTracker
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evUpdatedInfo: self.evUpdatedInfo,
		})
		self.pollTime = getVFDSymbolsPoll()  # In seconds.
		self.timer = eTimer()
		self.timer.callback.append(self.updateSymbols)
		self.timer.startLongTimer(0)

	def findProcFiles(self):
		ledConfig = {}
		for file in ("symbol_timer", "symbol_dolby_audio", "symbol_epg", "symbol_teletext", "symbol_scrambled", "symbol_hd", "symbol_power", "symbol_pause", "symbol_play", "symbol_parent_rating", "symbol_subtitle", "symbol_smartcard"):
			path = join("/proc/stb/lcd", file)
			if exists(path):
				ledConfig[file] = path
		return ledConfig

	def getRecModes(self):
		if exists("/proc/stb/lcd/symbol_circle"):
			mode = 1
			path = "/proc/stb/lcd/symbol_circle"
		elif BOX_TYPE in ("alphatriple", "sf3038") and exists("/proc/stb/lcd/symbol_recording"):
			mode = 2
			path = "/proc/stb/lcd/symbol_recording"
		elif MODEL == "u41" and exists("/proc/stb/lcd/symbol_pvr2"):
			mode = 2
			path = "/proc/stb/lcd/symbol_pvr2"
		elif BOX_TYPE in ("osninopro", "9910lx", "9911lx", "osnino", "osninoplus", "9920lx") and exists("/proc/stb/lcd/powerled"):
			mode = 3
			path = "/proc/stb/lcd/powerled"
		elif BOX_TYPE in ("mbmicrov2", "mbmicro", "e4hd", "e4hdhybrid") and exists("/proc/stb/lcd/powerled"):
			mode = 4
			path = "/proc/stb/lcd/powerled"
		elif BOX_TYPE in ("dm7020hd", "dm7020hdv2") and exists("/proc/stb/fp/led_set"):
			mode = 5
			path = "/proc/stb/fp/led_set"
		elif MODEL in ("dags7362", "dags73625", "dags5") or BOX_TYPE in ("tmtwin4k", "revo4k", "force3uhd") and exists("/proc/stb/lcd/symbol_rec"):
			mode = 3
			path = "/proc/stb/lcd/symbol_rec"
		elif MODEL in ("sf8008", "sf8008m", "ustym4kpro", "ustym4ks2ottx", "beyonwizv2", "viper4k", "dagsmv200", "sfx6008", "sx88v2", "sx888") and exists("/proc/stb/fp/ledpowercolor"):
			mode = 6
			path = "/proc/stb/fp/ledpowercolor"
		elif exists("/proc/stb/lcd/symbol_recording") and exists("/proc/stb/lcd/symbol_record_1") and exists("/proc/stb/lcd/symbol_record_2"):
			mode = 7
			path = ""
		elif MODEL in ("h7", "h17") and exists("/proc/stb/power/vfd"):
			mode = 8
			path = "/proc/stb/power/vfd"
		else:
			mode = 0
			path = ""
		return mode, path

	def evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		if MODEL == "u41":
			self.setAudio()
			self.setCrypted()
			self.setHBBTV()
			self.setPauseSymbol()
			self.setPlaySymbol()
			self.setPowerSymbol()
			self.setResolution()
			self.setTeletext()
			self.setTimer()
		self.setParentalControl()
		self.setSubtitle()
		del self.service

	def updateSymbols(self):
		def jobTask():
			self.setRecording()
			self.setPlaySymbol()
			self.timer.startLongTimer(self.pollTime)

		threads.deferToThread(jobTask)

	def setAudio(self):
		path = self.ledConfig.get("symbol_dolby_audio")
		if path:
			audio = self.service.audioTracks()
			if audio:
				tracks = audio.getNumberOfTracks()
				value = "0"
				for index in range(tracks):
					info = audio.getTrackInfo(index)
					description = info.getDescription()
					if any(x in description for x in ("AC3", "AC-3", "DTS")):
						value = "1"
						break
				fileWriteLine(path, value, source=MODULE_NAME)

	def setCrypted(self):
		path = self.ledConfig.get("symbol_scrambled")
		if path:
			info = self.service and self.service.info()
			if info:
				fileWriteLine(path, "1" if info.getInfo(iServiceInformation.sIsCrypted) == 1 else "0", source=MODULE_NAME)

	def setHBBTV(self):
		path = self.ledConfig.get("symbol_epg")
		if path:
			info = self.service and self.service.info()
			if info:
				fileWriteLine(path, "1" if info.getInfoString(iServiceInformation.sHBBTVUrl) != "" else "0", source=MODULE_NAME)

	def setParentalControl(self):
		path = self.ledConfig.get("symbol_parent_rating")
		if path:
			service = self.session.nav.getCurrentlyPlayingServiceReference()
			fileWriteLine(path, "1" if service and parentalControl.getProtectionLevel(service.toCompareString()) != -1 else "0", source=MODULE_NAME)

	def setPauseSymbol(self):
		path = self.ledConfig.get("symbol_pause")
		if path:
			fileWriteLine(path, "0" if BoxInfo.getItem("StatePlayPause") else "1", source=MODULE_NAME)

	def setPlaySymbol(self):
		path = self.ledConfig.get("symbol_play")
		if path:
			fileWriteLine(path, "1" if BoxInfo.getItem("SeekStatePlay") else "0", source=MODULE_NAME)

	def setPowerSymbol(self):
		path = self.ledConfig.get("symbol_power", None)
		if path:
			fileWriteLine(path, "0" if BoxInfo.getItem("StandbyState") else "1", source=MODULE_NAME)

	def setRecording(self):
		if self.recMode:
			recordings = self.session.nav.getIndicatorRecordingsCount()
			match self.recMode:
				case 1:
					value = "3" if recordings else "0"
					fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 2:
					value = "1" if recordings else "0"
					fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 3:
					self.blink = not self.blink
					value = ""
					if recordings:
						if self.blink:
							value = "1"
							self.led = True
						else:
							value = "0"
							self.led = False
					elif self.led:
						value = "0"
					if value:
						fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 4 | 8:
					self.blink = not self.blink
					value = ""
					if recordings:
						if self.blink:
							value = "0"
							self.led = True
						else:
							value = "1"
							self.led = False
					elif self.led:
						value = "1"
					if value:
						fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 5:
					self.blink = not self.blink
					value = "0xffffffff"
					if recordings:
						if self.blink:
							value = "0x00000000"
							self.led = True
						else:
							self.led = False
					fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 6:
					self.blink = not self.blink
					if recordings:
						if self.blink:
							value = "0"
							self.led = True
						else:
							value = config.usage.lcd_ledstandbycolor.value if Screens.Standby.inStandby else config.usage.lcd_ledpowercolor.value
							self.led = False
					else:
						value = config.usage.lcd_ledstandbycolor.value if Screens.Standby.inStandby else config.usage.lcd_ledpowercolor.value
					fileWriteLine(self.recPath, value, source=MODULE_NAME)
				case 7:
					if recordings:
						fileWriteLine("/proc/stb/lcd/symbol_recording", "1", source=MODULE_NAME)
						fileWriteLine("/proc/stb/lcd/symbol_record_1", "1", source=MODULE_NAME)
						if recordings == 1:
							fileWriteLine("/proc/stb/lcd/symbol_record_2", "0", source=MODULE_NAME)
						elif recordings >= 2:
							fileWriteLine("/proc/stb/lcd/symbol_record_2", "1", source=MODULE_NAME)
					else:
						fileWriteLine("/proc/stb/lcd/symbol_recording", "0", source=MODULE_NAME)
						fileWriteLine("/proc/stb/lcd/symbol_record_1", "0", source=MODULE_NAME)
						fileWriteLine("/proc/stb/lcd/symbol_record_2", "0", source=MODULE_NAME)

	def setResolution(self):
		path = self.ledConfig.get("symbol_hd")
		if path:
			info = self.service and self.service.info()
			if info:
				fileWriteLine(path, "1" if int(info.getInfo(iServiceInformation.sVideoWidth)) >= 1280 else "0", source=MODULE_NAME)

	def setSubtitle(self):
		subtitlePath = self.ledConfig.get("symbol_subtitle")
		smartcardPath = self.ledConfig.get("symbol_smartcard")
		if subtitlePath or smartcardPath:
			subtitle = self.service and self.service.subtitle()
			subtitleList = subtitle and subtitle.getSubtitleList()
			if subtitleList:
				subtitles = len(subtitleList)
				if subtitlePath:
					fileWriteLine(subtitlePath, "1" if subtitles else "0", source=MODULE_NAME)
				else:
					fileWriteLine(smartcardPath, "1" if subtitles else "0", source=MODULE_NAME)
			else:
				if subtitlePath:
					fileWriteLine(subtitlePath, "0", source=MODULE_NAME)
				else:
					fileWriteLine(smartcardPath, "0", source=MODULE_NAME)

	def setTeletext(self):
		path = self.ledConfig.get("symbol_teletext")
		if path:
			info = self.service and self.service.info()
			if info:
				fileWriteLine(path, "1" if int(info.getInfo(iServiceInformation.sTXTPID)) != -1 else "0", source=MODULE_NAME)

	def setTimer(self):
		path = self.ledConfig.get("symbol_timer")
		if path:
			fileWriteLine(path, "1" if self.session.nav.RecordTimer.getNextRecordingTime() > 0 else "0", source=MODULE_NAME)


def SymbolsCheck(session, **kwargs):
	global vfdSymbolsUpdater
	vfdSymbolsUpdater = VFDSymbolsUpdater(session)
