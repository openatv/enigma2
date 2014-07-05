from twisted.internet import threads
from config import config
from enigma import eDBoxLCD, eTimer, iPlayableService, iServiceInformation
from boxbranding import getMachineProcModel
import NavigationInstance
from Tools.Directories import fileExists
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker

POLLTIME = 5 # seconds

def SymbolsCheck(session, **kwargs):
		global symbolspoller
		symbolspoller = SymbolsCheckPoller(session)
		symbolspoller.start()

class SymbolsCheckPoller:
	def __init__(self, session):
		self.session = session
		self.timer = eTimer()
		self.onClose = []
		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				#iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
				iPlayableService.evVideoSizeChanged: self.__evUpdatedInfo,
			})

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
		self.timer.startLongTimer(POLLTIME)

	def __evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		if getMachineProcModel() in ('ini-7012', 'ini-7012au'):
			self.Resolution()
			self.Audio()
		self.Subtitle()
		self.ParentalControl()
		del self.service

	def Recording(self):
		if fileExists("/proc/stb/lcd/symbol_circle") or fileExists("/proc/stb/lcd/symbol_record"):
			recordings = len(NavigationInstance.instance.getRecordings())
			if recordings > 0:
				f = open("/proc/stb/lcd/symbol_circle", "w")
				f.write("3")
				f.close()
				f= open("/proc/stb/lcd/symbol_record", "w")
				f.write("1")
				f.close()
			else:
				f = open("/proc/stb/lcd/symbol_circle", "w")
				f.write("0")
				f.close()
				f =open("/proc/stb/lcd/symbol_record", "w")
				f.write("0")
				f.close()
		else:
			if not fileExists("/proc/stb/lcd/symbol_recording") or not fileExists("/proc/stb/lcd/symbol_record_1") or not fileExists("/proc/stb/lcd/symbol_record_2"):
				return
	
			recordings = len(NavigationInstance.instance.getRecordings())
		
			if recordings > 0:
				f = open("/proc/stb/lcd/symbol_recording", "w")
				f.write("1")
				f.close()
				if recordings == 1:
					f = open("/proc/stb/lcd/symbol_record_1", "w")
					f.write("1")
					f.close()
					f = open("/proc/stb/lcd/symbol_record_2", "w")
					f.write("0")
					f.close()
				elif recordings >= 2:
					f = open("/proc/stb/lcd/symbol_record_1", "w")
					f.write("1")
					f.close()
					f =open("/proc/stb/lcd/symbol_record_2", "w")
					f.write("1")
					f.close()
			else:
				f = open("/proc/stb/lcd/symbol_recording", "w")
				f.write("0")
				f.close()
				f = open("/proc/stb/lcd/symbol_record_1", "w")
				f.write("0")
				f.close()
				f = open("/proc/stb/lcd/symbol_record_2", "w")
				f.write("0")
				f.close()

	def Subtitle(self):
		if not fileExists("/proc/stb/lcd/symbol_smartcard") or not fileExists("/proc/stb/lcd/symbol_subtitle"):
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
			f = open("/proc/stb/lcd/symbol_smartcard", "w")
			f.write("0")
			f.close()
			
	def ParentalControl(self):
		if not fileExists("/proc/stb/lcd/symbol_parent_rating"):
			return

		service = self.session.nav.getCurrentlyPlayingServiceReference()

		if service:
			if parentalControl.getProtectionLevel(service.toCompareString()) == -1:
				f = open("/proc/stb/lcd/symbol_parent_rating", "w")
				f.write("0")
				f.close()
			else:
				f = open("/proc/stb/lcd/symbol_parent_rating", "w")
				f.write("1")
				f.close()
		else:
			f = open("/proc/stb/lcd/symbol_parent_rating", "w")
			f.write("0")
			f.close()
			
	def Resolution(self):
		if not fileExists("/proc/stb/lcd/symbol_1080i") or not fileExists("/proc/stb/lcd/symbol_720p") or not fileExists("/proc/stb/lcd/symbol_576i") or not fileExists("/proc/stb/lcd/symbol_hd"):
			return

		info = self.service and self.service.info()
		if not info:
			return ""

		videosize = int(info.getInfo(iServiceInformation.sVideoWidth))

		if videosize == 65535 or videosize == -1:
			# lets clear all symbols before turn on which are needed
			f = open("/proc/stb/lcd/symbol_1080p", "w")
			f.write("0")
			f.close()
			f = open("/proc/stb/lcd/symbol_1080i", "w")
			f.write("0")
			f.close()
			f = open("/proc/stb/lcd/symbol_720p", "w")
			f.write("0")
			f.close()
			f = open("/proc/stb/lcd/symbol_576p", "w")
			f.write("0")
			f.close()
			f = open("/proc/stb/lcd/symbol_576i", "w")
			f.write("0")
			f.close()
			f = open("/proc/stb/lcd/symbol_hd", "w")
			f.write("0")
			f.close()
			return ""
		
		if videosize >= 1280:
			f = open("/proc/stb/lcd/symbol_1080i", "w")
			f.write("1")
			f.close()
			f = open("/proc/stb/lcd/symbol_hd", "w")
			f.write("1")
			f.close()
		elif videosize < 1280 and videosize > 720:
			f = open("/proc/stb/lcd/symbol_720p", "w")
			f.write("1")
			f.close()
			f = open("/proc/stb/lcd/symbol_hd", "w")
			f.write("1")
			f.close()
		elif videosize <= 720:
			f = open("/proc/stb/lcd/symbol_576i", "w")
			f.write("1")
			f.close()
			f = open("/proc/stb/lcd/symbol_hd", "w")
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
		