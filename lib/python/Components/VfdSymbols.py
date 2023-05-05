from os.path import exists
from twisted.internet import threads
from enigma import eTimer, iPlayableService, iServiceInformation

from Components.config import config
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
import Components.RecordingConfig
import NavigationInstance

POLLTIME = 5  # seconds

BOX_TYPE = BoxInfo.getItem("machinebuild")
MODEL = BoxInfo.getItem("model")


def SymbolsCheck(session, **kwargs):
	global symbolspoller, POLLTIME
	if BoxInfo.getItem("VFDSymbolsPoll1"):
		POLLTIME = 1
	symbolspoller = SymbolsCheckPoller(session)
	symbolspoller.start()


class SymbolsCheckPoller:
	def __init__(self, session):
		self.session = session
		self.blink = False
		self.led = "0"
		self.timer = eTimer()
		self.onClose = []
		self.ledConfig = self.createConfig()
		self.recMode, self.recFile = self.createRecConfig()

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
			})

	def __onClose(self):
		pass

	def start(self):
		if self.symbolscheck not in self.timer.callback:
			self.timer.callback.append(self.symbolscheck)
		self.timer.startLongTimer(0)

	def stop(self):
		if self.symbolscheck in self.timer.callback:
			self.timer.callback.remove(self.symbolscheck)
		self.timer.stop()

	def symbolscheck(self):
		threads.deferToThread(self.JobTask)
		self.timer.startLongTimer(POLLTIME)

	def JobTask(self):
		self.Recording()
		self.PlaySymbol()
		self.timer.startLongTimer(POLLTIME)

	def __evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		if MODEL == 'u41':
			self.Resolution()
			self.Audio()
			self.Crypted()
			self.Teletext()
			self.Hbbtv()
			self.PauseSymbol()
			self.PlaySymbol()
			self.PowerSymbol()
			self.Timer()
		self.Subtitle()
		self.ParentalControl()
		del self.service

	def Recording(self):
		if self.recMode == 0:
			return
		recordings = len(NavigationInstance.instance.getRecordings(False, Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))

		if self.recMode == 1:
			value = "3" if recordings > 0 else "0"
			open(self.recFile, "w").write(value)
		elif self.recMode == 2:
			value = "1" if recordings > 0 else "0"
			open(self.recFile, "w").write(value)
		elif self.recMode == 3:
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open(self.recFile, "w").write("1")
					self.led = "1"
				else:
					open(self.recFile, "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open(self.recFile, "w").write("0")
		elif self.recMode == 4:
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open(self.recFile, "w").write("0")
					self.led = "1"
				else:
					open(self.recFile, "w").write("1")
					self.led = "0"
			elif self.led == "1":
				open(self.recFile, "w").write("1")
		elif self.recMode == 5:
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open(self.recFile, "w").write("0x00000000")
					self.led = "1"
				else:
					open(self.recFile, "w").write("0xffffffff")
					self.led = "0"
			else:
				open(self.recFile, "w").write("0xffffffff")
		elif self.recMode == 6:
			import Screens.Standby
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open(self.recFile, "w").write("0")
					self.led = "1"
				else:
					value = config.usage.lcd_ledstandbycolor.value if Screens.Standby.inStandby else config.usage.lcd_ledpowercolor.value
					open(self.recFile, "w").write(value)
					self.led = "0"
			else:
				value = config.usage.lcd_ledstandbycolor.value if Screens.Standby.inStandby else config.usage.lcd_ledpowercolor.value
				open(self.recFile, "w").write(value)
		elif self.recMode == 7:
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
				if recordings == 1:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("0")
				elif recordings >= 2:
					open("/proc/stb/lcd/symbol_record_1", "w").write("1")
					open("/proc/stb/lcd/symbol_record_2", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
				open("/proc/stb/lcd/symbol_record_1", "w").write("0")
				open("/proc/stb/lcd/symbol_record_2", "w").write("0")

	def Subtitle(self):
		subfilename = self.ledConfig.get("symbol_subtitle", None)
		smartfilename = self.ledConfig.get("symbol_smartcard", None)
		if not subfilename and not smartfilename:
			return

		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()

		if subtitlelist:
			subtitles = len(subtitlelist)
			if subfilename:
				if subtitles > 0:
					open(subfilename, "w").write("1")
				else:
					open(subfilename, "w").write("0")
			else:
				if subtitles > 0:
					open(smartfilename, "w").write("1")
				else:
					open(smartfilename, "w").write("0")
		else:
			if subfilename:
				open(subfilename, "w").write("0")
			else:
				open(smartfilename, "w").write("0")

	def ParentalControl(self):
		filename = self.ledConfig.get("symbol_parent_rating", None)
		if not filename:
			return

		service = self.session.nav.getCurrentlyPlayingServiceReference()

		if service:
			if parentalControl.getProtectionLevel(service.toCompareString()) == -1:
				open(filename, "w").write("0")
			else:
				open(filename, "w").write("1")
		else:
			open(filename, "w").write("0")

	def PlaySymbol(self):
		filename = self.ledConfig.get("symbol_play", None)
		if not filename:
			return

		value = "1" if BoxInfo.getItem("SeekStatePlay") else "0"
		open(filename, "w").write(value)

	def PauseSymbol(self):
		filename = self.ledConfig.get("symbol_pause", None)
		if not filename:
			return

		value = "0" if BoxInfo.getItem("StatePlayPause") else "1"
		open(filename, "w").write(value)

	def PowerSymbol(self):
		filename = self.ledConfig.get("symbol_power", None)
		if not filename:
			return

		value = "0" if BoxInfo.getItem("StandbyState") else "1"
		open(filename, "w").write(value)

	def Resolution(self):
		filename = self.ledConfig.get("symbol_hd", None)
		if not filename:
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		value = "1" if int(info.getInfo(iServiceInformation.sVideoWidth)) >= 1280 else "0"
		open(filename, "w").write(value)

	def Crypted(self):
		filename = self.ledConfig.get("symbol_scrambled", None)
		if not filename:
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		value = "1" if info.getInfo(iServiceInformation.sIsCrypted) == 1 else "0"
		open(filename, "w").write(value)

	def Teletext(self):
		filename = self.ledConfig.get("symbol_teletext", None)
		if not filename:
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		value = "1" if int(info.getInfo(iServiceInformation.sTXTPID)) != -1 else "0"
		open(filename, "w").write(value)

	def Hbbtv(self):
		filename = self.ledConfig.get("symbol_epg", None)
		if not filename:
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		value = "1" if info.getInfoString(iServiceInformation.sHBBTVUrl) != "" else "0"
		open(filename, "w").write(value)

	def Audio(self):
		filename = self.ledConfig.get("symbol_dolby_audio", None)
		if not filename:
			return

		audio = self.service.audioTracks()
		if audio:
			n = audio.getNumberOfTracks()
			idx = 0
			while idx < n:
				i = audio.getTrackInfo(idx)
				description = i.getDescription()
				if "AC3" in description or "AC-3" in description or "DTS" in description:
					open(filename, "w").write("1")
					return
				idx += 1
			open(filename, "w").write("0")

	def Timer(self):
		filename = self.ledConfig.get("symbol_timer", None)
		if filename:
			value = "1" if NavigationInstance.instance.RecordTimer.getNextRecordingTime() > 0 else "0"
			open(filename, "w").write(value)

	def createConfig(self):
		ret = {}
		for file in ("symbol_timer", "symbol_dolby_audio", "symbol_epg", "symbol_teletext", "symbol_scrambled", "symbol_hd", "symbol_power", "symbol_pause", "symbol_play", "symbol_parent_rating", "symbol_subtitle", "symbol_smartcard"):
			filename = "/proc/stb/lcd/%s" % file
			if exists(filename):
				ret[file] = filename
		return ret

	def createRecConfig(self):
		mode = 0
		filename = ""
		if exists("/proc/stb/lcd/symbol_circle"):
			mode = 1
			filename = "/proc/stb/lcd/symbol_circle"
		elif BOX_TYPE in ('alphatriple', 'sf3038') and exists("/proc/stb/lcd/symbol_recording"):
			mode = 2
			filename = "/proc/stb/lcd/symbol_recording"
		elif MODEL == 'u41' and exists("/proc/stb/lcd/symbol_pvr2"):
			mode = 2
			filename = "/proc/stb/lcd/symbol_pvr2"
		elif BOX_TYPE in ('osninopro', '9910lx', '9911lx', 'osnino', 'osninoplus', '9920lx') and exists("/proc/stb/lcd/powerled"):
			mode = 3
			filename = "/proc/stb/lcd/powerled"
		elif BOX_TYPE in ('mbmicrov2', 'mbmicro', 'e4hd', 'e4hdhybrid') and exists("/proc/stb/lcd/powerled"):
			mode = 4
			filename = "/proc/stb/lcd/powerled"
		elif BOX_TYPE in ('dm7020hd', 'dm7020hdv2') and exists("/proc/stb/fp/led_set"):
			mode = 5
			filename = "/proc/stb/fp/led_set"
		elif MODEL in ('dags7362', 'dags73625', 'dags5') or BOX_TYPE in ('tmtwin4k', 'revo4k', 'force3uhd') and exists("/proc/stb/lcd/symbol_rec"):
			mode = 3
			filename = "/proc/stb/lcd/symbol_rec"
		elif MODEL in ('sf8008', 'sf8008m', 'ustym4kpro', 'ustym4ks2ottx', 'beyonwizv2', 'viper4k', 'dagsmv200', 'sfx6008', 'sx88v2', 'sx888') and exists("/proc/stb/fp/ledpowercolor"):
			mode = 6
			filename = "/proc/stb/fp/ledpowercolor"
		elif exists("/proc/stb/lcd/symbol_recording") and exists("/proc/stb/lcd/symbol_record_1") and exists("/proc/stb/lcd/symbol_record_2"):
			mode = 7

		return mode, filename
