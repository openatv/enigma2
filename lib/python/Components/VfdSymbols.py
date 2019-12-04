from config import config
from enigma import iPlayableService, iRecordableService, iServiceInformation
from boxbranding import getMachineProcModel
from Tools.Directories import fileExists
from Components.ParentalControl import parentalControl
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import SystemInfo

def SymbolsCheck(session, **kwargs):
	global symbolspoller
	symbolspoller = SymbolsCheckPoller(session)
	symbolspoller.start()

class SymbolsCheckPoller:
	def __init__(self, session):
		self.session = session
		self.onClose = []
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				#iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
				iPlayableService.evVideoSizeChanged: self.__evUpdatedInfo,
			})
		self.recordings = 0

	def start(self):
		self.recordings = len(self.session.nav.getRecordings())
		self.session.nav.record_event.append(self.gotRecordEvent)
		config.misc.standbyCounter.addNotifier(self.standbyCounterChanged, initial_call=False)
		self.Recording()

	def stop(self):
		self.session.nav.record_event.remove(self.gotRecordEvent)
		config.misc.standbyCounter.removeNotifier(self.standbyCounterChanged)

	def __evUpdatedInfo(self):
		self.service = self.session.nav.getCurrentService()
		if getMachineProcModel() in ('ini-7012', 'ini-7012au'):
			self.Resolution()
			self.Audio()
		self.Subtitle()
		self.ParentalControl()
		del self.service

	def gotRecordEvent(self, service, event):
		if event in (iRecordableService.evEnd, iRecordableService.evStart):
			prev_recordings = self.recordings
			self.recordings = len(self.session.nav.getRecordings())
			if self.recordings != prev_recordings:
				self.Recording()

	def standbyCounterChanged(self, dummy):
		if config.usage.lcd_ledpowerrec:
			from Screens.Standby import inStandby
			inStandby.onClose.append(self.Recording)

	def Recording(self):
		if fileExists("/proc/stb/lcd/symbol_circle") or fileExists("/proc/stb/lcd/symbol_record"):
			if self.recordings > 0:
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
		elif fileExists("/proc/stb/lcd/symbol_recording") and fileExists("/proc/stb/lcd/symbol_record_1") and fileExists("/proc/stb/lcd/symbol_record_2"):
			if self.recordings > 0:
				f = open("/proc/stb/lcd/symbol_recording", "w")
				f.write("1")
				f.close()
				if self.recordings == 1:
					f = open("/proc/stb/lcd/symbol_record_1", "w")
					f.write("1")
					f.close()
					f = open("/proc/stb/lcd/symbol_record_2", "w")
					f.write("0")
					f.close()
				elif self.recordings >= 2:
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
		elif config.usage.lcd_ledpowerrec.value:
			led = self.recordings and 2 or 0
			if SystemInfo["LedStandbyColor"]:
				f = open("/proc/stb/fp/ledstandbycolor", "w")
				f.write(str(led))
				f.close()
			if not self.session.screen["Standby"].boolean:
				led |= 1
			f = open("/proc/stb/fp/ledpowercolor", "w")
			f.write(str(led))
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
