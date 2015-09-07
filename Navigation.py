from os import path
from enigma import eServiceCenter, eServiceReference, eTimer, pNavigation, getBestPlayableServiceReference, iPlayableService
from Components.ParentalControl import parentalControl
from Components.config import config
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.StbHardware import getFPWasTimerWakeup
from time import time, ctime
import RecordTimer
import PowerTimer
import Screens.Standby
import NavigationInstance
import ServiceReference
from Screens.InfoBar import InfoBar, MoviePlayer
from boxbranding import getBoxType, getBrandOEM

# TODO: remove pNavgation, eNavigation and rewrite this stuff in python.
class Navigation:
	def __init__(self, wakeupData=None):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance

		NavigationInstance.instance = self
		self.ServiceHandler = eServiceCenter.getInstance()

		import Navigation as Nav
		Nav.navcore = self

		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		self.event = [ ]
		self.record_event = [ ]
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None

		self.RecordTimer = None
		self.isRecordTimerImageStandard = False
		for p in plugins.getPlugins(PluginDescriptor.WHERE_RECORDTIMER):
			self.RecordTimer = p()
			if self.RecordTimer:
				break
		if not self.RecordTimer:
			self.RecordTimer = RecordTimer.RecordTimer()
			self.isRecordTimerImageStandard = True

		self.PowerTimer = None
		self.PowerTimer = PowerTimer.PowerTimer()
		self.__wasTimerWakeup = False
		self.__wasRecTimerWakeup = False
		self.__wasPowerTimerWakeup = False

		#wakeup data
		try:
			self.wakeuptime, self.timertime, self.wakeuptyp, self.getstandby, self.recordtime, self.forcerecord = [int(n) for n in wakeupData.split(',')]
		except:
			print "="*100
			print "[NAVIGATION] ERROR: can't read wakeup data"
			self.wakeuptime, self.timertime, self.wakeuptyp, self.getstandby, self.recordtime, self.forcerecord = -1,-1,0,0,-1,0
		#print ctime(self.wakeuptime), ctime(self.timertime), self.wakeuptyp, self.getstandby, ctime(self.recordtime), self.forcerecord
		now = time()
		timediff_wakeup = self.wakeuptime - now
		timediff_timer = self.timertime - now
		self.syncCount = 0

		wasTimerWakeup = getFPWasTimerWakeup()
		#TODO: verify wakeup-state for boxes where only after shutdown removed the wakeup-state (for boxes where "/proc/stb/fp/was_timer_wakeup" is not writable (clearFPWasTimerWakeup() in StbHardware.py has no effect -> after x hours and restart/reboot is wasTimerWakeup = True)

		print "="*100
		thisBox = getBoxType()
		if not config.workaround.deeprecord.value and (thisBox in ('ixussone', 'uniboxhd1', 'uniboxhd2', 'uniboxhd3', 'sezam5000hd', 'mbtwin', 'beyonwizt3') or getBrandOEM() in ('ebox', 'azbox', 'xp', 'ini', 'dags', 'fulan', 'entwopia')):
			print"[NAVIGATION] FORCED DEEPSTANDBY-WORKAROUND FOR THIS BOXTYPE (%s)" %thisBox
			config.workaround.deeprecord.setValue(True)
			config.workaround.deeprecord.save()
			config.save()

		if config.workaround.deeprecord.value: #work-around for boxes where driver not sent was_timer_wakeup signal to e2
			wasTimerWakeup = False
			print "[NAVIGATION] starting deepstandby-workaround"
			if now <= 31536000: # check for NTP-time sync, if no sync, wait for transponder time
				self.timesynctimer = eTimer()
				self.timesynctimer.callback.append(self.TimeSynctimer)
				self.timesynctimer.start(5000, True)
				print"[NAVIGATION] wait for time sync"
				print "~"*100
			elif abs(timediff_wakeup) <= 600 or abs(timediff_timer) <= 600: # if there is a recording sheduled in the next 10 mins or starting before 10 mins, set the wasTimerWakeup flag (wakeup time is 5 min before timer starts, some boxes starts but earlier than is set)
				wasTimerWakeup = True
				f = open("/tmp/was_timer_wakeup_workaround.txt", "w")
				file = f.write(str(wasTimerWakeup))
				f.close()

		print "[NAVIGATION] was timer wakeup = %s" % wasTimerWakeup
		print "[NAVIGATION] current time is %s" % ctime(now)

		if wasTimerWakeup:
			self.__wasTimerWakeup = True
			print "-"*100
			if self.wakeuptime > 0:
				print "[NAVIGATION] wakeup time was %s" % ctime(self.wakeuptime)
			else:
				print "[NAVIGATION] wakeup time was not set"
			if now <= 31536000:
				self.timesynctimer = eTimer()
				self.timesynctimer.callback.append(self.TimeSynctimer)
				self.timesynctimer.start(5000, True)
				print"[NAVIGATION] wait for time sync"
				print "~"*100
			else:
				self.wakeupCheck()
		else:
			if now > 31536000:
				if self.timertime > 0:
					print "[NAVIGATION] next '%s' starts at %s" % ({0:"record-timer",1:"zap-timer",2:"power-timer",3:"plugin-timer"}[self.wakeuptyp], ctime(self.timertime))
				else:
					print "[NAVIGATION] no next timers"
				print "="*100

	def wakeupCheck(self):
		now = time()
		timediff_wakeup = self.wakeuptime - now
		timediff_timer = self.timertime - now
		stbytimer = 5 # original was 15

		if abs(timediff_wakeup) <= 600 or abs(timediff_timer) <= 600:
			if self.syncCount > 0:
				stbytimer = 0
				if not self.__wasTimerWakeup:
					self.__wasTimerWakeup = True
					print "-"*100
					print "[NAVIGATION] was timer wakeup after time sync is = True"
					print "[NAVIGATION] wakeup time was %s" % ctime(self.wakeuptime)
			print "[NAVIGATION] wakeup type is '%s' %s" % ({0:"record-timer",1:"zap-timer",2:"power-timer",3:"plugin-timer"}[self.wakeuptyp],{0:"and starts normal",1:"and starts in standby",2:"and starts not in standby"}[self.getstandby])
			#record timer, zap timer, some plugin timer or next record timer begins in 15 mins
			if self.wakeuptyp < 2 or self.forcerecord:
				print "[NAVIGATION] timer starts at %s" % ctime(self.timertime)
				if self.forcerecord:
					print "[NAVIGATION] timer is set from 'vps-plugin' or just before a 'record-timer' starts at %s" % ctime(self.recordtime)
				print "[NAVIGATION] was rectimer wakeup = True"
				self.__wasRecTimerWakeup = True
				f = open("/tmp/was_rectimer_wakeup", "w")
				f.write('1')
				f.close()
			#power timer
			if self.wakeuptyp == 2:
				if not self.forcerecord:
					print "[NAVIGATION] timer starts at %s" % ctime(self.timertime)
				print "[NAVIGATION] was powertimer wakeup = True"
				self.__wasPowerTimerWakeup = True
				f = open("/tmp/was_powertimer_wakeup", "w")
				f.write('1')
				f.close()
			#plugin timer
			elif self.wakeuptyp == 3:
				if not self.forcerecord:
					print "[NAVIGATION] timer starts at %s" % ctime(self.timertime)
			#check for standby
			if not self.getstandby and self.wakeuptyp < 3 and timediff_timer > 60 + stbytimer:
				self.getstandby = 1
				print "[NAVIGATION] more than 60 seconds to wakeup - go in standby"
			print "="*100
			#go in standby
			if self.getstandby == 1:
				if stbytimer:
					self.standbytimer = eTimer()
					self.standbytimer.callback.append(self.gotostandby)
					self.standbytimer.start(stbytimer * 1000, True)
				else:
					self.gotostandby()
		else:
			if self.timertime > 0:
				print "[NAVIGATION] no timers in the time window, next '%s' starts at %s" % ({0:"record-timer",1:"zap-timer",2:"power-timer",3:"plugin-timer"}[self.wakeuptyp], ctime(self.timertime))
				if self.recordtime > 0 and self.timertime != self.recordtime:
					print "[NAVIGATION] next 'record-timer' starts at %s" % ctime(self.recordtime)
				else:
					print "[NAVIGATION] no next 'record-timer'"
			print "="*100
			self.getstandby = 0

		#workaround for normal operation if no time sync after e2 start - box is in standby
		if self.getstandby != 1:
			self.gotopower()

	def wasTimerWakeup(self):
		return self.__wasTimerWakeup

	def wasRecTimerWakeup(self):
		return self.__wasRecTimerWakeup

	def wasPowerTimerWakeup(self):
		return self.__wasPowerTimerWakeup

	def TimeSynctimer(self):
		now = time()
		self.syncCount += 1

		if now <= 31536000:
			if self.syncCount <= 24 and now <= 31536000: # max 2 mins or when time is in sync
				self.timesynctimer.start(5000, True)
			else:
				print "~"*100
				print "[NAVIGATION] time sync failure, current time is %s, sync time is %s sec." % (ctime(now),(self.syncCount * 5))
				if self.timertime > 0:
					print "[NAVIGATION] next '%s' starts at %s" % ({0:"record-timer",1:"zap-timer",2:"power-timer",3:"plugin-timer"}[self.wakeuptyp], ctime(self.timertime))
				else:
					print "[NAVIGATION] no next timers"
				print "="*100
				#workaround for normal operation if no time sync after e2 start - box is in standby
				self.gotopower()
		else:
			print "~"*100
			print "[NAVIGATION] time sync successful, current time is %s, sync time is %s sec." % (ctime(now),(self.syncCount * 5))
			self.wakeupCheck()

	def gotopower(self):
		if Screens.Standby.inStandby:
			print '[NAVIGATION] now entering normal operation'
			Screens.Standby.inStandby.Power()

	def gotostandby(self):
		if not Screens.Standby.inStandby:
			from Tools import Notifications
			print '[NAVIGATION] now entering standby'
			Notifications.AddNotification(Screens.Standby.Standby)

	def dispatchEvent(self, i):
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			self.currentlyPlayingServiceReference = None
			self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def dispatchRecordEvent(self, rec_service, event):
#		print "record_event", rec_service, event
		for x in self.record_event:
			x(rec_service, event)

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True):
		oldref = self.currentlyPlayingServiceOrGroup
		if ref and oldref and ref == oldref and not forceRestart:
			print "ignore request to play already running service(1)"
			return 1
		print "playing", ref and ref.toString()
		if path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '1':
			try:
				if '0:0:0:0:0:0:0:0:0' not in ref.toString():
					signal = 1
				else:
					signal = 0
				f = open("/proc/stb/lcd/symbol_signal", "w")
				f.write(str(signal))
				f.close()
			except:
				f = open("/proc/stb/lcd/symbol_signal", "w")
				f.write("0")
				f.close()
		elif path.exists("/proc/stb/lcd/symbol_signal") and config.lcd.mode.value == '0':
			f = open("/proc/stb/lcd/symbol_signal", "w")
			f.write("0")
			f.close()

		if ref is None:
			self.stopService()
			return 0
		from Components.ServiceEventTracker import InfoBarCount
		InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=adjust)):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
				print "playref", playref
				if playref and oldref and playref == oldref and not forceRestart:
					print "ignore request to play already running service(2)"
					return 1
				if not playref:
					alternativeref = getBestPlayableServiceReference(ref, eServiceReference(), True)
					self.stopService()
					if alternativeref and self.pnav and self.pnav.playService(alternativeref):
						print "Failed to start", alternativeref
					return 0
				elif checkParentalControl and not parentalControl.isServicePlayable(playref, boundFunction(self.playService, checkParentalControl = False)):
					if self.currentlyPlayingServiceOrGroup and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(self.currentlyPlayingServiceOrGroup, adjust):
						self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
					return 1
			else:
				playref = ref
			if self.pnav:
				self.pnav.stopService()
				self.currentlyPlayingServiceReference = playref
				self.currentlyPlayingServiceOrGroup = ref
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				if self.pnav.playService(playref):
					print "Failed to start", playref
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

	def isMovieplayerActive(self):
		MoviePlayerInstance = MoviePlayer.instance
		if MoviePlayerInstance is not None and '0:0:0:0:0:0:0:0:0' in self.currentlyPlayingServiceReference.toString():
			from Screens.InfoBarGenerics import setResumePoint
			setResumePoint(MoviePlayer.instance.session)
			MoviePlayerInstance.close()

	def recordService(self, ref, simulate=False, type=pNavigation.isUnknownRecording):
		service = None
		if not simulate: print "recording service: %s" % (str(ref))
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			service = ref and self.pnav and self.pnav.recordService(ref, simulate, type)
			if service is None:
				print "record returned non-zero"
		return service

	def stopRecordService(self, service):
		ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def getRecordings(self, simulate=False, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordings(simulate, type)

	def getRecordingsServices(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServices(type)

	def getRecordingsServicesOnly(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServicesOnly(type)

	def getRecordingsTypesOnly(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsTypesOnly(type)

	def getRecordingsServicesAndTypes(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServicesAndTypes(type)

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def stopService(self):
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		if path.exists("/proc/stb/lcd/symbol_signal"):
			f = open("/proc/stb/lcd/symbol_signal", "w")
			f.write("0")
			f.close()

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.RecordTimer.shutdown()
		self.PowerTimer.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()
