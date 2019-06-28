from twisted.internet import threads
from config import config
from enigma import eDBoxLCD, eTimer, iPlayableService, pNavigation, iServiceInformation
import NavigationInstance
from Tools.Directories import fileExists
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo
from boxbranding import getBoxType, getMachineBuild
from time import time
import Components.RecordingConfig

POLLTIME = 5 # seconds

def SymbolsCheck(session, **kwargs):
		global symbolspoller, POLLTIME
		if getBoxType() in ('alien5','osninopro','osnino','osninoplus','tmtwin4k','mbmicrov2','revo4k','force3uhd','wetekplay', 'wetekplay2', 'wetekhub', 'ixussone', 'ixusszero', 'mbmicro', 'e4hd', 'e4hdhybrid', 'dm7020hd', 'dm7020hdv2', '9910lx', '9911lx', '9920lx') or getMachineBuild() in ('dags7362' , 'dags73625', 'dags5','ustym4kpro','beyonwizv2','viper4k','sf8008','gbmv200','cc1'):
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
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
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
		if getMachineBuild() == 'u41':
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
		if fileExists("/proc/stb/lcd/symbol_circle"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			if recordings > 0:
				open("/proc/stb/lcd/symbol_circle", "w").write("3")
			else:
				open("/proc/stb/lcd/symbol_circle", "w").write("0")
		elif getBoxType() in ('alphatriple','mixosf5', 'mixoslumi', 'mixosf7', 'gi9196m', 'sf3038') and fileExists("/proc/stb/lcd/symbol_recording"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			if recordings > 0:
				open("/proc/stb/lcd/symbol_recording", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_recording", "w").write("0")
		elif getMachineBuild() == 'u41' and fileExists("/proc/stb/lcd/symbol_pvr2"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			if recordings > 0:
				open("/proc/stb/lcd/symbol_pvr2", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_pvr2", "w").write("0")
		elif getBoxType() in ('alien5','osninopro','wetekplay', 'wetekplay2', 'wetekhub', 'ixussone', 'ixusszero', '9910lx', '9911lx', 'osnino', 'osninoplus', '9920lx') and fileExists("/proc/stb/lcd/powerled"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("0")
		elif getBoxType() in ('mbmicrov2','mbmicro', 'e4hd', 'e4hdhybrid') and fileExists("/proc/stb/lcd/powerled"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/powerled", "w").write("0")
					self.led = "1"
				else:
					open("/proc/stb/lcd/powerled", "w").write("1")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/powerled", "w").write("1")
		elif getBoxType() in ('dm7020hd', 'dm7020hdv2') and fileExists("/proc/stb/fp/led_set"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/fp/led_set", "w").write("0x00000000")
					self.led = "1"
				else:
					open("/proc/stb/fp/led_set", "w").write("0xffffffff")
					self.led = "0"
			else:
				open("/proc/stb/fp/led_set", "w").write("0xffffffff")
		elif getMachineBuild() in ('dags7362' , 'dags73625', 'dags5') or getBoxType() in ('tmtwin4k','revo4k','force3uhd') and fileExists("/proc/stb/lcd/symbol_rec"):
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/lcd/symbol_rec", "w").write("1")
					self.led = "1"
				else:
					open("/proc/stb/lcd/symbol_rec", "w").write("0")
					self.led = "0"
			elif self.led == "1":
				open("/proc/stb/lcd/symbol_rec", "w").write("0")
		elif getMachineBuild() in ('sf8008','cc1','ustym4kpro','beyonwizv2','viper4k') and fileExists("/proc/stb/fp/ledpowercolor"):
			import Screens.Standby
			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
			self.blink = not self.blink
			if recordings > 0:
				if self.blink:
					open("/proc/stb/fp/ledpowercolor", "w").write("0")
					self.led = "1"
				else:
					if Screens.Standby.inStandby:
						open("/proc/stb/fp/ledpowercolor", "w").write(config.usage.lcd_ledstandbycolor.value)
					else:
						open("/proc/stb/fp/ledpowercolor", "w").write(config.usage.lcd_ledpowercolor.value)
					self.led = "0"
			elif self.led == "1":
				if Screens.Standby.inStandby:
					open("/proc/stb/fp/ledpowercolor", "w").write(config.usage.lcd_ledstandbycolor.value)
				else:
					open("/proc/stb/fp/ledpowercolor", "w").write(config.usage.lcd_ledpowercolor.value)
		else:
			if not fileExists("/proc/stb/lcd/symbol_recording") or not fileExists("/proc/stb/lcd/symbol_record_1") or not fileExists("/proc/stb/lcd/symbol_record_2"):
				return

			recordings = len(NavigationInstance.instance.getRecordings(False,Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue())))

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
		if not fileExists("/proc/stb/lcd/symbol_smartcard") and not fileExists("/proc/stb/lcd/symbol_subtitle"):
			return

		subtitle = self.service and self.service.subtitle()
		subtitlelist = subtitle and subtitle.getSubtitleList()

		if subtitlelist:
			subtitles = len(subtitlelist)
			if fileExists("/proc/stb/lcd/symbol_subtitle"):
				if subtitles > 0:
					f = open("/proc/stb/lcd/symbol_subtitle", "w")
					f.write("1")
					f.close()
				else:
					f = open("/proc/stb/lcd/symbol_subtitle", "w")
					f.write("0")
					f.close()
			else:
				if subtitles > 0:
					f = open("/proc/stb/lcd/symbol_smartcard", "w")
					f.write("1")
					f.close()
				else:
					f = open("/proc/stb/lcd/symbol_smartcard", "w")
					f.write("0")
					f.close()
		else:
			if fileExists("/proc/stb/lcd/symbol_subtitle"):
				f = open("/proc/stb/lcd/symbol_subtitle", "w")
				f.write("0")
				f.close()
			else:
				f = open("/proc/stb/lcd/symbol_smartcard", "w")
				f.write("0")
				f.close()

	def ParentalControl(self):
		if not fileExists("/proc/stb/lcd/symbol_parent_rating"):
			return

		service = self.session.nav.getCurrentlyPlayingServiceReference()

		if service:
			if parentalControl.getProtectionLevel(service.toCompareString()) == -1:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")
			else:
				open("/proc/stb/lcd/symbol_parent_rating", "w").write("1")
		else:
			open("/proc/stb/lcd/symbol_parent_rating", "w").write("0")

	def PlaySymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_play"):
			return

		if SystemInfo["SeekStatePlay"]:
			file = open("/proc/stb/lcd/symbol_play", "w")
			file.write('1')
			file.close()
		else:
			file = open("/proc/stb/lcd/symbol_play", "w")
			file.write('0')
			file.close() 

	def PauseSymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_pause"):
			return

		if SystemInfo["StatePlayPause"]:
			file = open("/proc/stb/lcd/symbol_pause", "w")
			file.write('1')
			file.close()
		else:
			file = open("/proc/stb/lcd/symbol_pause", "w")
			file.write('0')
			file.close()

	def PowerSymbol(self):
		if not fileExists("/proc/stb/lcd/symbol_power"):
			return

		if SystemInfo["StandbyState"]:
			file = open("/proc/stb/lcd/symbol_power", "w")
			file.write('0')
			file.close()
		else:
			file = open("/proc/stb/lcd/symbol_power", "w")
			file.write('1')
			file.close()

	def Resolution(self):
		if not fileExists("/proc/stb/lcd/symbol_hd"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		videosize = int(info.getInfo(iServiceInformation.sVideoWidth))

		if videosize >= 1280:
			f = open("/proc/stb/lcd/symbol_hd", "w")
			f.write("1")
			f.close()
		else:
			f = open("/proc/stb/lcd/symbol_hd", "w")
			f.write("0")
			f.close()

	def Crypted(self):
		if not fileExists("/proc/stb/lcd/symbol_scrambled"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		crypted = info.getInfo(iServiceInformation.sIsCrypted)

		if crypted == 1:
			f = open("/proc/stb/lcd/symbol_scrambled", "w")
			f.write("1")
			f.close()
		else:
			f = open("/proc/stb/lcd/symbol_scrambled", "w")
			f.write("0")
			f.close()

	def Teletext(self):
		if not fileExists("/proc/stb/lcd/symbol_teletext"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		tpid = int(info.getInfo(iServiceInformation.sTXTPID))

		if tpid != -1:
			f = open("/proc/stb/lcd/symbol_teletext", "w")
			f.write("1")
			f.close()
		else:
			f = open("/proc/stb/lcd/symbol_teletext", "w")
			f.write("0")
			f.close()

	def Hbbtv(self):
		if not fileExists("/proc/stb/lcd/symbol_epg"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		hbbtv = info.getInfoString(iServiceInformation.sHBBTVUrl)

		if hbbtv != "":
			f = open("/proc/stb/lcd/symbol_epg", "w")
			f.write("1")
			f.close()
		else:
			f = open("/proc/stb/lcd/symbol_epg", "w")
			f.write("0")
			f.close()

	def Audio(self):
		if not fileExists("/proc/stb/lcd/symbol_dolby_audio"):
			return
		      
		audio = self.service.audioTracks()
		if audio:
			n = audio.getNumberOfTracks()
			idx = 0
			while idx < n:
				i = audio.getTrackInfo(idx)
				description = i.getDescription();
				if "AC3" in description or "AC-3" in description or "DTS" in description:
					f = open("/proc/stb/lcd/symbol_dolby_audio", "w")
					f.write("1")
					f.close()
					return
				idx += 1
		f = open("/proc/stb/lcd/symbol_dolby_audio", "w")
		f.write("0")
		f.close()

	def Timer(self):
		if fileExists("/proc/stb/lcd/symbol_timer"):
			timer = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			if timer > 0:
				open("/proc/stb/lcd/symbol_timer", "w").write("1")
			else:
				open("/proc/stb/lcd/symbol_timer", "w").write("0")
